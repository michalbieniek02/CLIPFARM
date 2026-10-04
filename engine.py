"""Local media pipeline. Only transcript text is sent to the selected model."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import threading
import time
import uuid
from highlight_selection import selection_prompt, verified_hook, choose_distinct

ROOT = Path(__file__).resolve().parent
os.environ.setdefault('HF_HOME', str(ROOT / 'models'))
# Keep optional NVIDIA runtimes inside this application's environment.
_dll_handles = []
if os.name == 'nt':
    import sys
    for folder in (Path(sys.prefix) / 'Lib/site-packages/nvidia').glob('*/bin'):
        os.environ['PATH'] = str(folder) + os.pathsep + os.environ.get('PATH', '')
        _dll_handles.append(os.add_dll_directory(str(folder)))
MODEL = 'gpt-6.1-sol'
CLAUDE_MODEL = 'sonnet'
HIDDEN = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'properties': {'clips': {'type': 'array', 'items': {
        'type': 'object', 'additionalProperties': False,
        'properties': {'start': {'type': 'number'}, 'end': {'type': 'number'},
                       'title': {'type': 'string'}, 'reason': {'type': 'string'},
                       'score': {'type': 'integer', 'minimum': 1, 'maximum': 10},
                       'hook_sentence': {'type': 'string'}, 'hook_cut_start': {'type': 'string'},
                       'hook_text': {'type': 'string'}, 'hook_alternatives': {'type': 'array', 'items': {'type': 'string'}},
                       'structure': {'type': 'string'}, 'loop': {'type': 'string'},
                       'captions': {'type': 'array', 'items': {'type': 'string'}},
                       'montage': {'type': 'string'}, 'titles': {'type': 'array', 'items': {'type': 'string'}},
                       'description': {'type': 'string'}, 'hashtags': {'type': 'array', 'items': {'type': 'string'}},
                       'risks': {'type': 'string'}},
        'required': ['start', 'end', 'title', 'reason', 'score', 'hook_sentence', 'hook_cut_start',
                     'hook_text', 'hook_alternatives', 'structure', 'loop', 'captions', 'montage',
                     'titles', 'description', 'hashtags', 'risks']}}},
    'required': ['clips']
}


class Cancelled(Exception):
    pass


class Pipeline:
    def __init__(self, log=lambda message: None):
        self.log = log
        self.cancel = threading.Event()

    def check(self):
        if self.cancel.is_set():
            raise Cancelled('Przerwano zadanie.')

    def run(self, args, cwd=None, input_text=None, timeout=3600):
        self.check()
        proc = subprocess.Popen(args, cwd=cwd, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, encoding='utf-8', errors='replace',
                                creationflags=HIDDEN)
        deadline = time.monotonic() + timeout
        sent = False
        try:
            while True:
                self.check()
                if time.monotonic() > deadline:
                    raise RuntimeError('Przekroczono czas zadania. Spróbuj ponownie.')
                try:
                    out, err = proc.communicate(input_text if not sent else None, timeout=.3)
                    break
                except subprocess.TimeoutExpired:
                    sent = True
            if proc.returncode:
                # Claude may put diagnostics on stderr and the actual JSON error on stdout.
                details = '\n'.join(value[-3000:] for value in (err, out) if value.strip())
                raise RuntimeError(details or 'Proces zakończył się błędem.')
            return out, err
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.communicate()

    @staticmethod
    def ffmpeg():
        import imageio_ffmpeg
        return shutil.which('ffmpeg') or imageio_ffmpeg.get_ffmpeg_exe()

    @staticmethod
    def probe(source):
        import av
        with av.open(str(source)) as container:
            video = next((s for s in container.streams if s.type == 'video'), None)
            if video is None:
                raise ValueError('Plik nie zawiera obrazu wideo.')
            if container.duration:
                duration = container.duration / av.time_base
            elif video.duration and video.time_base:
                duration = float(video.duration * video.time_base)
            else:
                raise ValueError('Nie udało się odczytać długości filmu.')
            return {'duration': duration, 'width': video.width, 'height': video.height,
                    'audio': any(s.type == 'audio' for s in container.streams)}

    def transcribe(self, source, work, model_size='small', device='auto'):
        work = Path(work)
        work.mkdir(parents=True, exist_ok=True)
        stat = Path(source).stat()
        identity = {'source': str(Path(source).resolve()), 'size': stat.st_size,
                    'mtime': stat.st_mtime_ns, 'model': model_size}
        cache = work / 'transcript.json'
        if cache.exists():
            data = json.loads(cache.read_text(encoding='utf-8'))
            if data.get('identity') == identity:
                self.log('Wczytano zapisaną transkrypcję.')
                return data['segments']
        self.log('Wyodrębnianie dźwięku na komputerze…')
        audio = work / 'audio.wav'
        self.run([self.ffmpeg(), '-y', '-i', str(source), '-vn', '-ac', '1',
                  '-ar', '16000', str(audio)])
        from faster_whisper import WhisperModel
        import ctranslate2
        use_gpu = device == 'cuda' or (device == 'auto' and ctranslate2.get_cuda_device_count() > 0)

        def recognize(gpu):
            self.log(f"Transkrypcja Whisper {model_size}: {'GPU' if gpu else 'CPU'}. Pierwszy start może pobrać model.")
            whisper = WhisperModel(model_size, device='cuda' if gpu else 'cpu',
                                   compute_type='float16' if gpu else 'int8',
                                   download_root=str(ROOT / 'models'))
            iterator, info = whisper.transcribe(str(audio), vad_filter=True, beam_size=5, word_timestamps=True)
            rows, next_report = [], 0
            for segment in iterator:
                self.check()
                rows.append({'start': segment.start, 'end': segment.end, 'text': segment.text.strip(),
                             'words': [{'start': w.start, 'end': w.end, 'text': w.word.strip()}
                                       for w in (segment.words or []) if w.word.strip() and w.end > w.start]})
                if segment.end >= next_report:
                    self.log(f'Transkrypcja: {segment.end:.0f} / {info.duration:.0f} s')
                    next_report = segment.end + 30
            return rows

        try:
            try:
                rows = recognize(use_gpu)
            except (RuntimeError, OSError) as exc:
                if not use_gpu or device == 'cuda':
                    raise
                self.log(f'GPU Whisper niedostępne ({exc}). Przechodzę na CPU.')
                rows = recognize(False)
            if not rows:
                raise ValueError('Nie wykryto mowy. Wybór klipów w tej wersji wymaga dialogu lub narracji.')
            cache.write_text(json.dumps({'identity': identity, 'segments': rows}, ensure_ascii=False), encoding='utf-8')
            return rows
        finally:
            audio.unlink(missing_ok=True)

    def model_request(self, prompt, work):
        self.check()
        codex = find_codex()
        claude = find_claude()
        if not codex and not claude:
            raise ValueError('Nie znaleziono Codex CLI ani Claude Code. Zainstaluj jedno z nich i zaloguj konto.')
        work = Path(work)
        work.mkdir(parents=True, exist_ok=True)
        schema = work / 'selection-schema.json'
        schema.write_text(json.dumps(SCHEMA), encoding='utf-8')
        output = work / f'selection-{uuid.uuid4().hex}.json'
        errors = []
        if codex:
            try:
                self.log('AI: znaleziono Codex CLI — używam zalogowanego konta.')
                self.run(codex + ['exec', '--ignore-user-config', '--ephemeral', '--skip-git-repo-check',
                    '--sandbox', 'read-only', '--model', MODEL, '--output-schema', str(schema),
                    '--output-last-message', str(output), '--color', 'never', '-'],
                    cwd=work, input_text=prompt, timeout=600)
                return json.loads(output.read_text(encoding='utf-8'))
            except (RuntimeError, OSError, ValueError) as exc:
                errors.append(f'Codex: {exc}')
            finally:
                output.unlink(missing_ok=True)
        if claude:
            try:
                self.log('AI: Codex niedostępny — znaleziono Claude Code, używam zalogowanego konta · Sonnet.')
                # Keep the transcript out of Windows' bounded command line.
                raw, _ = self.run(claude + ['-p', '--model', CLAUDE_MODEL, '--output-format', 'json'],
                                  cwd=work, input_text=prompt, timeout=600)
                return parse_agent_json(raw)
            except (RuntimeError, OSError, ValueError) as exc:
                errors.append(f'Claude Code: {exc}')
        raise ValueError('Nie udało się użyć zalogowanego AI. ' + ' | '.join(errors)[-1800:])

    def select(self, segments, duration, count, minimum, maximum, brief, work):
        validate_options(count, minimum, maximum)
        # Every transcript segment is considered; long films are split into bounded text batches.
        batches, batch, length = [], [], 0
        for segment in segments:
            line = f"[{segment['start']:.2f}–{segment['end']:.2f}] {segment['text']}"
            if batch and length + len(line) > 28000:
                batches.append(batch)
                # A short overlap preserves potential clips across batch boundaries.
                edge = batch[-1]['end'] - maximum
                batch = [s for s in batch if s['end'] > edge]
                length = sum(len(s['text']) + 30 for s in batch)
            batch.append(segment)
            length += len(line)
        if batch:
            batches.append(batch)
        candidates = []
        for index, batch in enumerate(batches):
            self.log(f'AI: wybór fragmentów, część {index + 1}/{len(batches)}…')
            prompt = selection_prompt(batch, count, minimum, maximum, brief)
            data = self.model_request(prompt, work)
            valid = validate_clips(data.get('clips'), duration, minimum, maximum)
            for clip in valid:
                if clip['start'] >= batch[0]['start'] - .1 and clip['end'] <= batch[-1]['end'] + .1:
                    clip['hook_sentence'] = verified_hook(clip, batch) or 'brak'
                    cut = clip.get('hook_cut_start', 'brak')
                    if isinstance(cut, float):
                        boundaries = [s['start'] for s in batch] + [s['end'] for s in batch]
                        if not any(abs(cut - boundary) <= .05 for boundary in boundaries):
                            clip['hook_cut_start'] = 'brak'
                    candidates.append(clip)
        selected = choose_distinct(candidates, count)
        if not selected:
            raise ValueError('Model nie zwrócił poprawnych klipów. Zmień zakres długości lub opis wyboru.')
        return selected

    def export(self, source, clips, segments, destination, vertical=True, burn=False, encoder='auto', framing='fit', timing_work=None,
               light_color=False, speed_up=False, mirror=False, caption_font='Anton', caption_size=84,
               caption_position=None, fit_zoom=1, fit_focus=(.5, .5), canvas_size=(1080, 1920)):
        from framing import fit_filter, face_filter
        from captions import phrases, ass_text, progressive_cues, retime_cues, FONT_DIR
        from video_layout import canvas_dimensions, frame_layout, letterbox_filter
        if framing not in ('fit', 'center', 'face'):
            raise ValueError('Nieznany tryb kadrowania.')
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=True)
        metadata = self.probe(source)
        output_size = list(canvas_dimensions(canvas_size)) if vertical else [
            metadata['width'] // 2 * 2, metadata['height'] // 2 * 2]
        face_frame_duration = None
        if vertical and framing == 'face':
            import av
            with av.open(str(source)) as container:
                stream = container.streams.video[0]
                rate = stream.average_rate or stream.guessed_rate
                face_frame_duration = 1 / float(rate) if rate and rate > 0 else 1 / 30
        has_audio = bool(metadata.get('audio'))
        validate_clips(clips, metadata['duration'], 1, metadata['duration'], strict=True)
        if burn and segments:
            from word_timing import align_saved_text
            segments = align_saved_text(self, source, segments, clips, timing_work or destination / '.timings')
            if timing_work:
                from transcripts import remember_transcript
                remember_transcript(source, timing_work, segments)
        self.caption_segments = segments
        ffmpeg = self.ffmpeg()
        gpu = encoder in ('auto', 'nvenc')
        written = []
        for i, clip in enumerate(clips):
            self.check()
            stem = f"{i + 1:02d}-{safe_name(clip['title'])}-{uuid.uuid4().hex[:6]}"
            # Do not let players automatically overlay a second subtitle track
            # on the captions already burned into the image.
            srt = destination / f"{stem}{'.captions' if burn else ''}.srt"
            speed = 1.1 if speed_up else 1.0
            duration = clip['end'] - clip['start']
            cues = retime_cues(phrases(segments, clip['start'], clip['end']), speed)
            subtitle = subtitle_text(progressive_cues(cues), 0, duration / speed)
            srt.write_text(subtitle, encoding='utf-8')
            final = destination / f'{stem}.mp4'
            partial = destination / f'{stem}.partial.mp4'
            command_file = destination / f'{stem}.crop.txt'
            filters = []
            if light_color:
                filters.append('eq=contrast=1.03:brightness=0.02:saturation=1.05')
            fitted = vertical and framing == 'fit'
            manual_framing = vertical and framing in ('fit', 'center')
            if mirror and manual_framing:
                filters.append('hflip')
            if vertical:
                if framing == 'face':
                    follow = face_filter(source, clip['start'], clip['end'], command_file,
                                         self.check, self.log, canvas_size)
                    fitted = follow == fit_filter(canvas_size)
                    filters.append(follow)
                else:
                    filters.append(fit_filter(canvas_size))
            else:
                filters.append('scale=trunc(iw/2)*2:trunc(ih/2)*2,setsar=1')
            layout = frame_layout(metadata['width'], metadata['height'], vertical, fitted,
                                  fit_zoom if manual_framing else 1,
                                  *(fit_focus if manual_framing else (.5, .5)),
                                  caption_position=caption_position, reserve_captions=burn and bool(subtitle),
                                  canvas_size=canvas_size)
            if fitted or manual_framing:
                filters[-1] = letterbox_filter(layout)
            # Apply requested transforms before ASS subtitles so captions stay readable.
            if speed_up:
                filters.append('setpts=(PTS-STARTPTS)/1.1')
            if mirror and not manual_framing:
                filters.append('hflip')
            if burn and subtitle:
                width, height = layout['canvas_width'], layout['canvas_height']
                styled = destination / f'{stem}.captions.ass'
                styled.write_text(ass_text(cues, width, height, layout['caption_y'], layout['caption_x'],
                                           caption_font, caption_size), encoding='utf-8')
                fonts = FONT_DIR.as_posix().replace(':', '\\:')
                filters.append(f"ass=filename='{styled.name}':fontsdir='{fonts}'")

            def encode(hardware):
                # Limit input in source time, before the video/audio speed filters.
                # Output -t would otherwise include footage beyond the selected end.
                args = [ffmpeg, '-y', '-ss', str(clip['start']), '-t', str(duration), '-i', str(source),
                        '-map', '0:v:0', '-map', '0:a:0?',
                        '-vf', ','.join(filters), '-c:v', 'h264_nvenc' if hardware else 'libx264']
                args += ['-preset', 'p4', '-cq', '21'] if hardware else ['-preset', 'fast', '-crf', '21']
                args += ['-pix_fmt', 'yuv420p']
                if vertical and framing == 'face' and not fitted:
                    # sendcmd/setpts can leave encoded packet duration unset.
                    # Keep each original timestamp (including VFR), but give
                    # such packets a nominal duration so MP4 keeps the last frame.
                    nominal = face_frame_duration / speed
                    args += ['-fps_mode', 'passthrough', '-bsf:v',
                             rf'setts=pts=PTS:dts=DTS:duration=if(eq(DURATION\,0)\,{nominal:.12f}/TB\,DURATION)']
                if speed_up and has_audio:
                    args += ['-af', 'asetpts=PTS-STARTPTS,atempo=1.1']
                args += ['-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', str(partial)]
                self.run(args, cwd=destination)

            self.log(f"Eksport {i + 1}/{len(clips)}: {clip['title']} ({'NVENC' if gpu else 'CPU'})")
            try:
                try:
                    encode(gpu)
                except RuntimeError:
                    if not gpu or encoder == 'nvenc':
                        raise
                    self.log('NVENC niedostępny — ponawiam eksport na CPU.')
                    gpu = False
                    encode(False)
                self.check()
                partial.replace(final)
                written.append(str(final))
            finally:
                partial.unlink(missing_ok=True)
                command_file.unlink(missing_ok=True)
        (destination / 'clips.json').write_text(json.dumps({'source': str(source), 'clips': clips,
            'files': written, 'vertical': vertical, 'framing': framing, 'burn': burn,
            'light_color': light_color, 'speed_up': speed_up, 'mirror': mirror,
            'caption_font': caption_font, 'caption_size': caption_size, 'caption_position': caption_position,
            'fit_zoom': fit_zoom, 'fit_focus': fit_focus,
            'canvas_size': output_size}, ensure_ascii=False, indent=2), encoding='utf-8')
        return written


def minute_clips(duration, seconds=60):
    """Return contiguous source ranges covering the whole film."""
    if not math.isfinite(duration) or duration <= 0 or seconds <= 0:
        raise ValueError('Film musi mieć dodatnią długość.')
    clips = []
    start = 0.0
    index = 1
    while start < duration - .01:
        end = min(duration, start + seconds)
        clips.append({'start': round(start, 3), 'end': round(end, 3), 'score': 0,
                      'title': f'Część {index:02d}', 'reason': 'Kolejna minuta filmu.',
                      'hook_sentence': ''})
        start = end
        index += 1
    return clips


def find_codex():
    found = shutil.which('codex.exe')
    if found:
        return [found]
    base = Path(os.environ.get('APPDATA', '')) / 'npm/node_modules/@openai/codex'
    matches = list(base.glob('node_modules/@openai/codex-win32-*/vendor/*/bin/codex.exe'))
    if matches:
        return [str(matches[0])]
    script = base / 'bin/codex.js'
    node = shutil.which('node')
    return [node, str(script)] if node and script.exists() else None


def find_claude():
    """Find Claude Code without requiring an API key or a provider setting."""
    found = shutil.which('claude.exe') or shutil.which('claude')
    return [found] if found else None


def parse_agent_json(raw):
    """Claude Code can wrap its answer in a JSON result or a markdown fence."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = None
    if isinstance(data, dict) and isinstance(data.get('result'), str):
        raw = data['result']
    if isinstance(data, dict) and 'clips' in data:
        return data
    match = re.search(r'\{\s*"clips"\s*:\s*\[.*\]\s*\}', raw, re.S)
    if not match:
        raise ValueError('Claude Code nie zwrócił poprawnego JSON klipów.')
    return json.loads(match.group(0))


def validate_options(count, minimum, maximum):
    if not 1 <= count <= 20 or not 5 <= minimum <= maximum <= 180:
        raise ValueError('Wybierz 1–20 klipów i długość 5–180 s; minimum nie może przekraczać maksimum.')


def validate_clips(clips, duration, minimum, maximum, strict=False):
    if not isinstance(clips, list):
        raise ValueError('Niepoprawny format listy klipów.')
    valid = []
    for clip in clips:
        try:
            start, end = float(clip['start']), float(clip['end'])
            if not all(math.isfinite(v) for v in (start, end)):
                raise ValueError('Nieprawidłowy czas.')
            if not 0 <= start < end <= duration + .01 or not minimum - .01 <= end - start <= maximum + .01:
                raise ValueError('Fragment wykracza poza film lub dozwoloną długość.')
            score = int(clip.get('score', 0))
            valid.append({'start': start, 'end': min(end, duration), 'score': max(0, min(100, score)),
                          'title': str(clip.get('title', 'Klip'))[:150],
                          'reason': str(clip.get('reason', ''))[:1000],
                          'hook_sentence': str(clip.get('hook_sentence', ''))[:500]})
            if any(key in clip for key in ('hook_cut_start', 'hook_text', 'hook_alternatives',
                                           'structure', 'loop', 'captions', 'montage', 'titles',
                                           'description', 'hashtags', 'risks')):
                try:
                    cut = clip.get('hook_cut_start', 'brak')
                    cut = float(cut) if str(cut).strip().lower() != 'brak' else 'brak'
                    if isinstance(cut, float) and not start - .01 <= cut <= end + .01:
                        cut = 'brak'
                except (TypeError, ValueError):
                    cut = 'brak'
                row = valid[-1]
                row.update({'hook_cut_start': cut, 'hook_text': str(clip.get('hook_text', 'brak'))[:300],
                    'hook_alternatives': [str(x)[:120] for x in clip.get('hook_alternatives', [])[:2]],
                    'structure': str(clip.get('structure', 'brak'))[:500],
                    'loop': str(clip.get('loop', 'brak'))[:500],
                    'captions': [str(x)[:160] for x in clip.get('captions', [])[:12]],
                    'montage': str(clip.get('montage', 'brak'))[:1000],
                    'titles': [str(x)[:60] for x in clip.get('titles', [])[:3]],
                    'description': str(clip.get('description', 'brak'))[:500],
                    'hashtags': [str(x)[:40] for x in clip.get('hashtags', [])[:5]],
                    'risks': str(clip.get('risks', 'brak'))[:500]})
        except (KeyError, ValueError, TypeError, OverflowError):
            if strict:
                raise ValueError('Niepoprawne czasy klipu. Sprawdź początek i koniec.') from None
    return valid


def safe_name(value):
    return re.sub(r'[^\w-]+', '-', value, flags=re.UNICODE).strip('-')[:60] or 'klip'


def timestamp(seconds):
    millis = max(0, round(seconds * 1000))
    hours, rest = divmod(millis, 3600000)
    minutes, rest = divmod(rest, 60000)
    secs, ms = divmod(rest, 1000)
    return f'{hours:02}:{minutes:02}:{secs:02},{ms:03}'


def subtitle_text(segments, start, end):
    rows = []
    for segment in segments:
        left, right = max(segment['start'], start), min(segment['end'], end)
        if right > left:
            text = str(segment['text']).replace('\n', ' ').strip()
            rows.append(f'{len(rows)+1}\n{timestamp(left-start)} --> {timestamp(right-start)}\n{text}\n')
    return '\n'.join(rows)

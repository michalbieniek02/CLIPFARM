"""Resume video downloads from Kick, Twitch, YouTube and X, with optional compression."""
import hashlib
from collections import deque
import json
import math
from pathlib import Path
import re
import queue
import shutil
import subprocess
import threading
import time
from urllib.parse import urlparse

CHUNK = 300
PROVIDERS = ('Auto', 'Kick', 'Twitch', 'YouTube', 'X')
QUALITIES = {
    'Oryginał': None,
    '720p60': (720, 60, 4000, 128),
    '720p30': (720, 30, 2500, 128),
    '480p60': (480, 60, 2000, 96),
    '480p30': (480, 30, 1200, 96),
}


def remaining_time(seconds):
    seconds = max(0, math.ceil(seconds))
    hours, rest = divmod(seconds, 3600)
    minutes, seconds = divmod(rest, 60)
    return f'{hours} godz. {minutes:02d} min' if hours else f'{minutes} min {seconds:02d} s'


class DownloadProgress:
    """Use recent actual media progress; startup has no invented ETA."""
    def __init__(self, pipeline, total, completed, quality, saved_bytes=0):
        self.pipeline, self.total, self.completed, self.quality = pipeline, total, completed, quality
        self.saved_bytes = saved_bytes
        self.samples = deque()
        self.last_log = -math.inf

    def __call__(self, media_time, size, speed):
        now = time.monotonic()
        self.samples.append((now, media_time))
        while len(self.samples) > 2 and self.samples[1][0] < now - 30:
            self.samples.popleft()
        elapsed = now - self.samples[0][0]
        advanced = media_time - self.samples[0][1]
        rate = advanced / elapsed if elapsed >= 2 and advanced > 0 else 0
        if now - self.last_log < .25:
            return
        self.last_log = now
        done = min(self.total, self.completed + media_time)
        estimate = f'pozostało około {remaining_time((self.total - done) / rate)}' if rate else 'szacuję czas po rozpoczęciu pobierania'
        pace = f' · {rate:.1f}×' if rate else ''
        self.pipeline.log(f'VOD: {done:.1f} / {self.total:.1f} s · {self.quality}{pace} · zapisano {(self.saved_bytes + size) / 1e6:.1f} MB · {estimate}')


def run_media(pipeline, args, progress, timeout=43200, stall_timeout=90):
    """Stream FFmpeg progress without blocking cancellation or filling its pipes."""
    from engine import HIDDEN
    pipeline.check()
    command = [args[0], '-progress', 'pipe:1', '-nostats', '-stats_period', '0.25', *args[1:]]
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            stdin=subprocess.DEVNULL, text=True, encoding='utf-8', errors='replace',
                            creationflags=HIDDEN)
    events = queue.Queue()
    errors = deque(maxlen=40)
    def read_progress():
        for line in proc.stdout:
            events.put(line.rstrip())
        events.put(None)
    def read_errors():
        for line in proc.stderr:
            errors.append(line.rstrip())
    readers = [threading.Thread(target=read_progress, daemon=True), threading.Thread(target=read_errors, daemon=True)]
    for reader in readers:
        reader.start()
    started = last_advance = time.monotonic()
    last_media = last_size = 0
    record = {}
    try:
        while True:
            pipeline.check()
            now = time.monotonic()
            if now - started > timeout:
                raise RuntimeError('Przekroczono czas pobierania tej części.')
            if stall_timeout is not None and now - last_advance > stall_timeout:
                raise RuntimeError(f'Brak postępu przez {stall_timeout:g} s. Sprawdzam połączenie i ponawiam pobieranie.')
            try:
                line = events.get(timeout=.2)
            except queue.Empty:
                continue
            if line is None:
                break
            name, sep, value = line.partition('=')
            if sep:
                record[name] = value
            if name == 'progress':
                try:
                    media = max(0.0, float(record.get('out_time_us', '0')) / 1e6)
                except ValueError:
                    media = 0.0
                size = int(record.get('total_size', '0')) if record.get('total_size', '0').isdigit() else 0
                if media > last_media + .01 or size > last_size:
                    last_advance = time.monotonic()
                    last_media, last_size = media, size
                progress(media, size, record.get('speed', ''))
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError('FFmpeg nie zakończył zapisu pliku.') from exc
        readers[1].join(timeout=2)
        if proc.returncode:
            raise RuntimeError('\n'.join(errors)[-3000:] or 'FFmpeg zakończył pobieranie błędem.')
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.wait()
        for reader in readers:
            reader.join(timeout=2)
        proc.stdout.close()
        proc.stderr.close()


def timestamp(value):
    value = value.strip()
    if not value:
        return 0.0
    parts = value.split(':')
    if len(parts) > 3:
        raise ValueError('Czas podaj jako HH:MM:SS lub liczbę sekund.')
    numbers = [float(p) for p in parts]
    if any(not math.isfinite(n) or n < 0 for n in numbers) or any(n >= 60 for n in numbers[1:]):
        raise ValueError('Nieprawidłowy czas.')
    return sum(n * 60 ** i for i, n in enumerate(reversed(numbers)))


def video_url(value, provider='Auto'):
    parsed = urlparse(value.strip())
    if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError('Wklej adres HTTPS filmu z Kicka, Twitcha, YouTube lub X.')
    hosts = {'kick.com': 'Kick', 'www.kick.com': 'Kick',
             'twitch.tv': 'Twitch', 'www.twitch.tv': 'Twitch', 'm.twitch.tv': 'Twitch', 'clips.twitch.tv': 'Twitch',
             'youtube.com': 'YouTube', 'www.youtube.com': 'YouTube', 'm.youtube.com': 'YouTube', 'youtu.be': 'YouTube',
             'x.com': 'X', 'www.x.com': 'X', 'twitter.com': 'X', 'www.twitter.com': 'X', 'mobile.twitter.com': 'X'}
    detected = hosts.get(parsed.hostname)
    if not detected:
        raise ValueError('Obsługiwane strony: Kick, Twitch, YouTube i X (także twitter.com).')
    if provider not in PROVIDERS or provider not in ('Auto', detected):
        raise ValueError(f'Link pochodzi z {detected}. Wybierz {detected} albo Auto.')
    if detected == 'Kick' and '/videos/' not in parsed.path and '/video/' not in parsed.path:
        raise ValueError('Wklej link do nagrania Kicka, nie do transmisji live.')
    if detected == 'Twitch' and not ('/videos/' in parsed.path or '/clip/' in parsed.path or parsed.hostname == 'clips.twitch.tv'):
        raise ValueError('Wklej link do VOD-a albo klipu Twitcha.')
    if detected == 'X' and not re.search(r'/status/\d+', parsed.path):
        raise ValueError('Wklej link do wpisu X zawierającego film.')
    if detected == 'YouTube' and not (parsed.hostname == 'youtu.be' and parsed.path.strip('/') or
            parsed.path == '/watch' or parsed.path.startswith(('/shorts/', '/live/', '/embed/'))):
        raise ValueError('Wklej link do jednego filmu YouTube, nie do kanału lub playlisty.')
    return value.strip(), detected


def kick_url(value):
    return video_url(value, 'Kick')[0]


def format_selector(quality):
    if quality not in QUALITIES:
        raise ValueError('Wybierz prawidłową jakość pobierania.')
    profile = QUALITIES[quality]
    if profile is None:
        return 'bv+ba/b'
    height, fps, _, _ = profile
    limit = f'[height<={height}][fps<=?{fps}]'
    return f'bv{limit}+ba/b{limit}/bv+ba/b'


def downloader_options(quality):
    options = {'quiet': True, 'no_warnings': True, 'noplaylist': True, 'cachedir': False,
               'socket_timeout': 30, 'retries': 5, 'fragment_retries': 5,
               'format': format_selector(quality)}
    node = shutil.which('node')
    if node:
        options['js_runtimes'] = {'node': {'path': node}}
    if quality == 'Oryginał':
        options['merge_output_format'] = 'mkv'
    return options


def resolve_vod(url, quality='480p30'):
    import yt_dlp
    options = {**downloader_options(quality), 'skip_download': True}
    # Kick also shares /video/UUID links; its extractor calls the same UUID API.
    if urlparse(url).hostname in ('kick.com', 'www.kick.com') and urlparse(url).path.startswith('/video/'):
        url = 'https://kick.com/vod/videos/' + urlparse(url).path.split('/')[2]
    kick = urlparse(url).hostname in ('kick.com', 'www.kick.com')
    if kick:
        from yt_dlp.networking.impersonate import ImpersonateTarget
        options['impersonate'] = ImpersonateTarget.from_str('chrome')
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            if kick:
                from kick_vod import ClipfarmKickVODIE
                ydl.add_info_extractor(ClipfarmKickVODIE())
                info = ydl.extract_info(url, ie_key=ClipfarmKickVODIE.ie_key(), download=False)
            else:
                info = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as exc:
        raise RuntimeError('Nie udało się odczytać filmu. Sprawdź dostępność linku i ewentualny wymóg logowania. ' + str(exc)) from exc
    if info.get('_type') in ('playlist', 'multi_video'):
        entries = [entry for entry in info.get('entries', []) if entry]
        if len(entries) != 1:
            raise ValueError('Link zawiera kilka filmów. Wklej link do pojedynczego nagrania.')
        info = entries[0]
    if info.get('is_live') or not info.get('duration') or not (info.get('url') or info.get('requested_formats')):
        raise ValueError('Potrzebny jest zakończony, dostępny film z podaną długością.')
    return info


def transcode_args(ffmpeg, info, start, length, output, gpu, quality='480p30'):
    height, fps, bitrate, audio = QUALITIES[quality]
    args = [ffmpeg, '-hide_banner', '-y']
    inputs = info.get('requested_formats') or [info]
    for stream in inputs:
        headers = {**info.get('http_headers', {}), **stream.get('http_headers', {})}
        args += ['-rw_timeout', '30000000', '-reconnect', '1', '-reconnect_streamed', '1', '-reconnect_delay_max', '5']
        if headers:
            args += ['-headers', ''.join(f'{k}: {v}\r\n' for k, v in headers.items())]
        args += ['-ss', str(start), '-i', stream['url']]
    video = next(i for i, stream in enumerate(inputs) if stream.get('vcodec') != 'none')
    audio_input = next((i for i, stream in enumerate(inputs) if stream.get('acodec') != 'none'), None)
    args += ['-t', str(length), '-map', f'{video}:v:0']
    if audio_input is not None:
        args += ['-map', f'{audio_input}:a:0?']
    args += ['-vf',
             f"scale=-2:'min(ih,{height})':force_original_aspect_ratio=decrease:force_divisible_by=2,fps={fps}:start_time=0,setsar=1",
             '-c:v', 'h264_nvenc' if gpu else 'libx264', '-preset', 'p4' if gpu else 'fast',
             '-b:v', f'{bitrate}k', '-maxrate', f'{round(bitrate * 1.25)}k', '-bufsize', f'{round(bitrate * 2.5)}k',
             '-bf', '0', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', f'{audio}k', '-ar', '48000',
             '-f', 'mpegts', str(output)]
    return args


def download_original(pipeline, info, cache, output, start, end, duration):
    """Native yt-dlp resume and lossless MKV merge; preserve source codecs and FPS."""
    import yt_dlp
    last_log = [0.0]
    completed = set()
    downloaded = {}
    stream_count = max(1, len(info.get('requested_formats', [])))
    def progress(data):
        pipeline.check()
        if data['status'] == 'finished':
            completed.add(data.get('filename', ''))
        now = time.monotonic()
        if now - last_log[0] < .25 and data['status'] != 'finished':
            return
        last_log[0] = now
        downloaded[data.get('filename', '')] = data.get('downloaded_bytes', 0)
        size = data.get('total_bytes') or data.get('total_bytes_estimate')
        fraction = (data.get('downloaded_bytes', 0) / size) if size else 0
        value = min(.98, (len(completed) + (fraction if data['status'] != 'finished' else 0)) / stream_count)
        eta = data.get('eta')
        estimate = 'szacuję czas po rozpoczęciu pobierania'
        if isinstance(eta, (int, float)) and math.isfinite(eta) and data['status'] != 'finished':
            scope = 'pozostało około' if stream_count == 1 else 'bieżąca ścieżka: około'
            estimate = f'{scope} {remaining_time(eta)}'
        if data['status'] == 'finished':
            estimate = 'ścieżka pobrana; przygotowuję plik'
        pipeline.log(f'VOD: {value * duration:.1f} / {duration:.1f} s · Oryginał · pobrano {sum(downloaded.values()) / 1e6:.1f} MB · {estimate}')
    class Logger:
        def debug(self, message):
            pass
        def warning(self, message):
            pipeline.log(message)
        def error(self, message):
            pipeline.log(message)
    options = {**downloader_options('Oryginał'), 'ffmpeg_location': pipeline.ffmpeg(),
               'outtmpl': str(cache / 'source.%(ext)s'), 'merge_output_format': 'mkv',
               'continuedl': True, 'overwrites': False, 'progress_hooks': [progress], 'logger': Logger(),
               'concurrent_fragment_downloads': 4, 'skip_unavailable_fragments': False}
    pipeline.log('Pobieram oryginalne ścieżki obrazu i dźwięku, bez zmiany jakości…')
    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.process_info(info)
        source = Path(info.get('filepath') or ydl.prepare_filename(info))
    pipeline.check()
    if not source.is_file():
        raise RuntimeError('Nie znaleziono ukończonego pliku oryginału. Zachowano dane do wznowienia.')
    if start == 0 and end == duration:
        # Move instead of recompressing or keeping a second full-sized copy.
        output = output.with_suffix(source.suffix)
        source.replace(output)
    else:
        pipeline.log('Zapisuję zakres oryginału bez ponownego kodowania…')
        partial = cache / 'range.partial.mkv'
        pipeline.run([pipeline.ffmpeg(), '-hide_banner', '-y', '-ss', str(start), '-i', str(source),
                      '-t', str(end - start), '-map', '0:v:0', '-map', '0:a:0?', '-c', 'copy', str(partial)], timeout=43200)
        pipeline.probe(partial)
        partial.replace(output)
        source.unlink()
    pipeline.log(f'VOD gotowy: {output.name}')
    return output


def download_vod(pipeline, url, folder, start=0, end=0, gpu=True, resolver=None, quality='480p30', provider='Auto'):
    url, detected = video_url(url, provider)
    format_selector(quality)
    get_info = (lambda value: resolve_vod(value, quality)) if resolver is None else resolver
    pipeline.log(f'Odczytuję film z {detected} · {quality}…')
    info = get_info(url)
    pipeline.check()
    duration = float(info['duration'])
    end = end or duration
    if not all(math.isfinite(x) for x in (duration, start, end)) or not 0 <= start < end <= duration + .1:
        raise ValueError('Zakres musi mieścić się w długości VOD-a; koniec musi być później niż początek.')
    total = end - start
    identity = json.dumps([url, start, end, quality, 'video-download-v3'])
    key = hashlib.sha256(identity.encode()).hexdigest()[:16]
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    cache = folder / ('.vod-' + key)
    cache.mkdir(exist_ok=True)
    safe_title = re.sub(r'[^\w .-]', '_', info.get('title') or f'{detected} video')[:90].strip(' .') or 'Video'
    output = folder / f'{safe_title}-{quality}-{key}{".mkv" if quality == "Oryginał" else ".mp4"}'
    (cache / 'job.json').write_text(json.dumps({'url': url, 'start': start, 'end': end, 'title': safe_title,
                                             'quality': quality, 'provider': detected}), encoding='utf-8')
    if quality == 'Oryginał':
        return download_original(pipeline, info, cache, output, start, end, duration)
    count = math.ceil(total / CHUNK)
    parts = []
    started = time.monotonic()
    processed = 0.0
    saved_bytes = 0
    for index in range(count):
        pipeline.check()
        length = min(CHUNK, total - index * CHUNK)
        part = cache / f'{index:05d}.ts'
        valid = False
        if part.exists():
            try:
                valid = abs(pipeline.probe(part)['duration'] - length) < 2
            except Exception:
                valid = False
        if not valid:
            partial = cache / f'{index:05d}.partial.ts'
            pipeline.log(f'VOD: {index * CHUNK:.1f} / {total:.1f} s · pobieram część {index + 1}/{count} · {quality}')
            for attempt in range(3):
                pipeline.check()
                try:
                    if attempt:
                        info = get_info(url)
                    progress = DownloadProgress(pipeline, total, index * CHUNK, quality, saved_bytes)
                    run_media(pipeline, transcode_args(pipeline.ffmpeg(), info, start + index * CHUNK,
                              length, partial, gpu, quality), progress)
                    pipeline.check()
                    if abs(pipeline.probe(partial)['duration'] - length) >= 2:
                        raise RuntimeError('Odebrana część VOD-a jest niekompletna.')
                except RuntimeError as exc:
                    pipeline.check()
                    if attempt == 2:
                        raise RuntimeError('Nie udało się pobrać tej części po 3 próbach. Zachowano ukończone części do wznowienia.\n' + str(exc)) from exc
                    encoder_error = re.search(r'cannot load.*(?:nv|cuda)|no (?:nvenc )?capable devices|openencodesessionex|initializeencoder|driver does not support.*nvenc|error while opening encoder', str(exc), re.I)
                    if gpu and encoder_error:
                        gpu = False
                        pipeline.log('NVENC nie jest dostępny. Ponawiam kompresję na CPU…')
                    else:
                        pipeline.log(f'Ponawiam część {index + 1}/{count} · próba {attempt + 2}/3 · odświeżam adres filmu…')
                else:
                    break
            partial.replace(part)
            processed += length
        else:
            pipeline.log(f'Wznawianie: zachowuję część {index + 1}/{count}.')
        parts.append(part)
        saved_bytes += part.stat().st_size
        completed = min(total, (index + 1) * CHUNK)
        rate = processed / max(.01, time.monotonic() - started)
        estimate = f' · {rate:.1f}× · pozostało około {remaining_time((total - completed) / rate)}' if rate and completed < total else ''
        pipeline.log(f'VOD: {completed:.1f} / {total:.1f} s · zapisano część {index + 1}/{count}{estimate}')
    pipeline.check()
    pipeline.log('Łączę pobrane części w MP4…')
    manifest = cache / 'concat.txt'
    manifest.write_text(''.join(f"file '{p.name}'\nduration {min(CHUNK, total - i * CHUNK)}\n" for i, p in enumerate(parts)), encoding='utf-8')
    partial_mp4 = cache / 'complete.partial.mp4'
    merge_log = [0.0]
    def merge_progress(media, size, speed):
        now = time.monotonic()
        if now - merge_log[0] >= 1:
            merge_log[0] = now
            pipeline.log(f'Łączenie MP4: {min(100, media / total * 100):.0f}% · zapisano {size / 1e6:.1f} MB · finalizuję pobrany film…')
    run_media(pipeline, [pipeline.ffmpeg(), '-hide_banner', '-y', '-f', 'concat', '-safe', '0',
              '-i', str(manifest), '-c', 'copy', '-movflags', '+faststart', str(partial_mp4)],
              merge_progress, stall_timeout=None)
    if abs(pipeline.probe(partial_mp4)['duration'] - total) > max(2, count * .15):
        raise RuntimeError('Końcowy plik ma nieprawidłową długość. Zachowano części do ponownej próby.')
    partial_mp4.replace(output)
    # Completed parts are no longer needed; interrupted jobs keep their cache.
    for part in parts:
        part.unlink()
    pipeline.log(f'VOD gotowy: {output.name}')
    return output

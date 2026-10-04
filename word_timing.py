"""Align saved text to local audio. No transcript generation or cloud request."""
import hashlib
import json
import math
from pathlib import Path
import uuid


def align_saved_text(pipeline, source, segments, clips, work):
    from transcripts import source_identity
    cache = Path(work) / 'word-timings.json'
    identity = source_identity(source)
    saved = {}
    if cache.exists():
        try:
            data = json.loads(cache.read_text(encoding='utf-8'))
            if data.get('identity') == identity:
                saved = data.get('timings', {})
        except (ValueError, OSError):
            pass
    result = [dict(row) for row in segments]
    pending = []
    for row in result:
        if row.get('words') or not any(row['start'] < c['end'] and row['end'] > c['start'] for c in clips):
            continue
        key = hashlib.sha256(json.dumps([row['start'], row['end'], row['text']],
                                       ensure_ascii=False).encode()).hexdigest()
        if saved.get(key):
            row['words'] = saved[key]
        else:
            pending.append((row, key))
    if not pending:
        return result
    pipeline.log('Synchronizacja słów z dźwiękiem lokalnie — bez ponownego wyboru klipów…')
    from engine import ROOT
    from faster_whisper import WhisperModel
    from faster_whisper.audio import decode_audio
    from faster_whisper.tokenizer import Tokenizer
    from faster_whisper.audio import pad_or_trim
    import ctranslate2
    gpu = ctranslate2.get_cuda_device_count() > 0
    def load(use_gpu):
        return WhisperModel('small', device='cuda' if use_gpu else 'cpu',
                            compute_type='float16' if use_gpu else 'int8',
                            download_root=str(ROOT / 'models'))
    try:
        model = load(gpu)
    except (RuntimeError, OSError):
        if not gpu:
            raise
        pipeline.log('Synchronizacja GPU niedostępna — używam CPU.')
        gpu = False
        model = load(False)
    Path(work).mkdir(parents=True, exist_ok=True)
    audio_file = Path(work) / f'align-{uuid.uuid4().hex}.wav'
    language = None
    try:
        for index, (row, key) in enumerate(pending):
            pipeline.check()
            # Whisper aligns windows up to 30 seconds. Long imported paragraphs
            # are split into bounded windows; audio alignment supplies final times.
            tokens = row['text'].split()
            parts = max(1, math.ceil((row['end'] - row['start']) / 28), math.ceil(len(tokens) / 80))
            words = []
            for part in range(parts):
                text = ' '.join(tokens[len(tokens) * part // parts:len(tokens) * (part + 1) // parts])
                if not text:
                    continue
                left = row['start'] + (row['end'] - row['start']) * part / parts
                right = row['start'] + (row['end'] - row['start']) * (part + 1) / parts
                offset = max(0, left - .2)
                pipeline.run([pipeline.ffmpeg(), '-y', '-ss', str(offset), '-i', str(source),
                              '-t', str(right - offset + .2), '-vn', '-ac', '1', '-ar', '16000', str(audio_file)])
                audio = decode_audio(str(audio_file), sampling_rate=16000)
                if language is None:
                    language = model.detect_language(audio=audio)[0]
                tokenizer = Tokenizer(model.hf_tokenizer, model.model.is_multilingual,
                                      task='transcribe', language=language)
                features = model.feature_extractor(audio)
                pipeline.check()
                def align():
                    return model.find_alignment(tokenizer, [tokenizer.encode(' ' + text)],
                                                model.encode(pad_or_trim(features)),
                                                min(features.shape[-1], 3000))[0]
                try:
                    aligned = align()
                except (RuntimeError, OSError):
                    if not gpu:
                        raise
                    pipeline.log('Synchronizacja GPU niedostępna — ponawiam na CPU.')
                    gpu = False
                    model = load(False)
                    aligned = align()
                # Tokenizer may separate punctuation; fold it into original words.
                target = text.split()
                position, buffer, first, last = 0, '', None, None
                for item in aligned:
                    content = item['word'].strip()
                    if not content:
                        continue
                    buffer += content
                    first = float(item['start']) if first is None else first
                    last = float(item['end'])
                    if position < len(target) and buffer == target[position]:
                        start = max(row['start'], offset + first)
                        end = min(row['end'], offset + last)
                        if end <= start:
                            end = min(row['end'], start + .02)
                        if end > start:
                            words.append({'start': round(start, 3), 'end': round(end, 3), 'text': target[position]})
                        position += 1
                        buffer, first = '', None
                if position != len(target):
                    raise ValueError('Nie udało się dopasować wszystkich słów do dźwięku. Sprawdź tekst transkrypcji.')
            if not words:
                raise ValueError('Brak czasów słów. Sprawdź, czy transkrypcja odpowiada nagraniu.')
            row['words'] = words
            saved[key] = words
            temporary = cache.with_suffix('.tmp')
            temporary.write_text(json.dumps({'identity': identity, 'timings': saved}, ensure_ascii=False), encoding='utf-8')
            temporary.replace(cache)
            pipeline.log(f'Synchronizacja słów: {index + 1}/{len(pending)} segmentów.')
    finally:
        audio_file.unlink(missing_ok=True)
    return result

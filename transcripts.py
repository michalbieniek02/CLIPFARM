"""Portable transcript sidecars and validation, independent of model selection."""
import json
import math
from pathlib import Path
import re


def validate_segments(rows, duration):
    if not isinstance(rows, list) or not rows:
        raise ValueError('Transkrypcja jest pusta lub nie zawiera listy segmentów.')
    result = []
    for row in rows:
        try:
            start, end = float(row['start']), float(row['end'])
            text = row['text']
            if (not isinstance(text, str) or not text.strip()
                or not all(math.isfinite(v) for v in (start, end))
                or not 0 <= start < end <= duration + .5 or start >= duration):
                raise ValueError()
            cleaned = {'start': start, 'end': min(end, duration), 'text': text.strip()}
            if row.get('words'):
                words = []
                for word in row['words']:
                    left, right = float(word['start']), float(word['end'])
                    content = word['text']
                    if (not isinstance(content, str) or not content.strip()
                        or not all(math.isfinite(v) for v in (left, right))
                        or not start - .05 <= left < right <= end + .05):
                        raise ValueError()
                    if left < duration:
                        words.append({'start': max(start, left), 'end': min(right, end, duration),
                                      'text': content.strip()})
                if words:
                    cleaned['words'] = sorted(words, key=lambda word: word['start'])
            result.append(cleaned)
        except (KeyError, TypeError, ValueError):
            raise ValueError('Transkrypcja ma niepoprawne czasy lub wykracza poza wybrany film.') from None
    return sorted(result, key=lambda row: row['start'])


def read_transcript(path, duration):
    text = Path(path).read_text(encoding='utf-8-sig')
    if Path(path).suffix.lower() == '.json':
        data = json.loads(text)
        return validate_segments(data if isinstance(data, list) else data.get('segments'), duration)
    pattern = re.compile(r'(?:(\d+):)?(\d{2}):(\d{2})[,.](\d{3})')
    def seconds(value):
        match = pattern.search(value)
        if not match:
            raise ValueError('Niepoprawny czas w pliku napisów.')
        h, m, s, ms = match.groups()
        return int(h or 0) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
    rows = []
    for block in re.split(r'\n\s*\n', text.replace('\r\n', '\n').strip()):
        lines = block.splitlines()
        timing = next((i for i, line in enumerate(lines) if '-->' in line), None)
        if timing is None:
            continue
        left, right = lines[timing].split('-->', 1)
        content = re.sub(r'<[^>]+>', '', ' '.join(lines[timing + 1:])).strip()
        if content:
            rows.append({'start': seconds(left), 'end': seconds(right), 'text': content})
    return validate_segments(rows, duration)


def source_identity(source):
    source = Path(source).resolve()
    stat = source.stat()
    return {'source': str(source), 'size': stat.st_size, 'mtime': stat.st_mtime_ns}


def remember_transcript(source, work, segments):
    data = {'identity': {**source_identity(source), 'model': 'imported'}, 'segments': segments}
    Path(work, 'transcript.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def existing_transcript(source, work, duration):
    cached = Path(work, 'transcript.json')
    if cached.exists():
        try:
            data = json.loads(cached.read_text(encoding='utf-8'))
            identity = source_identity(source)
            if all(data.get('identity', {}).get(k) == v for k, v in identity.items()):
                return validate_segments(data['segments'], duration), 'zapisana lokalnie'
        except (ValueError, KeyError, TypeError, OSError):
            pass
    source = Path(source)
    for path in (source.with_suffix('.srt'), source.with_suffix('.vtt'), source.with_suffix('.transcript.json'), source.with_suffix('.json')):
        if path.exists():
            try:
                rows = read_transcript(path, duration)
                remember_transcript(source, work, rows)
                return rows, path.name
            except (ValueError, TypeError, OSError):
                pass
    return [], ''

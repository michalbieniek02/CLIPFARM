"""Short, local captions with explicit canvas sizing and safe letterbox placement."""
from pathlib import Path
import re
from PIL import ImageFont
from font_catalog import font_path, resolve_font

FONT_DIR = Path(__file__).resolve().parent / 'assets' / 'fonts'
FONT_SIZE = 84  # 20% larger than the previous 70px default at 1080px width.


def retime_cues(cues, speed):
    """Map clip-relative caption and word timestamps to the exported playback rate."""
    return [{**cue, 'start': cue['start'] / speed, 'end': cue['end'] / speed,
             'words': [{**word, 'start': word['start'] / speed, 'end': word['end'] / speed}
                       for word in cue.get('words', [])]} for cue in cues]


def phrases(segments, start, end):
    cues = []
    for segment in segments:
        words = segment.get('words')
        if not words:
            tokens = segment['text'].split()
            weight = sum(max(1, len(t)) for t in tokens)
            cursor = segment['start']
            words = []
            for token in tokens:
                finish = cursor + (segment['end'] - segment['start']) * len(token) / weight
                words.append({'start': cursor, 'end': finish, 'text': token})
                cursor = finish
        group = []
        def flush():
            if group:
                left = max(start, group[0]['start']) - start
                right = min(end, group[-1]['end']) - start
                if right > left:
                    cues.append({'start': left, 'end': right,
                                 'text': ' '.join(w['text'].strip() for w in group),
                                 'words': [{'start': max(start, w['start']) - start,
                                            'end': min(end, w['end']) - start,
                                            'text': w['text'].strip()} for w in group]})
                group.clear()
        for word in words:
            if word['end'] <= start or word['start'] >= end:
                continue
            if group and (len(group) >= 4 or word['start'] - group[-1]['end'] > .75):
                flush()
            group.append(word)
            if re.search(r'[.!?]["\u201d\u2019]*$', word['text']):
                flush()
        flush()
    # Overlapping imported segments must not produce simultaneous blocks of text.
    cues.sort(key=lambda cue: cue['start'])
    for cue in cues:
        cue['end'] = min(end - start, cue['end'] + .2)
    for previous, following in zip(cues, cues[1:]):
        previous['end'] = min(previous['end'], following['start'])
    return [cue for cue in cues if cue['end'] - cue['start'] >= .02]


def progressive_cues(cues):
    """Portable SRT also reveals only the words already spoken."""
    result = []
    for cue in cues:
        words = cue.get('words', [])
        if not words:
            result.append(cue)
        for i, word in enumerate(words):
            finish = words[i + 1]['start'] if i + 1 < len(words) else cue['end']
            if finish > word['start']:
                result.append({'start': word['start'], 'end': finish,
                               'text': ' '.join(w['text'] for w in words[:i + 1])})
    return result


def placement(width, height, vertical, fitted):
    """Return canvas, caption centre and optional fit filter reserving a black strip."""
    if not vertical:
        return width // 2 * 2, height // 2 * 2, height * .84, None
    if fitted:
        displayed_height = min(1920, height * 1080 / width)
        bottom = (1920 - displayed_height) / 2
        if bottom >= 180:
            return 1080, 1920, 1920 - bottom + min(140, bottom / 2), None
        return 1080, 1920, 1790, (
            'scale=1080:1656:force_original_aspect_ratio=decrease:force_divisible_by=2,'
            'pad=1080:1920:(ow-iw)/2:(1656-ih)/2:color=black,setsar=1')
    return 1080, 1920, 1620, None


def ass_text(cues, width, height, y, x=None, font='Anton', font_size=FONT_SIZE):
    font = resolve_font(font)
    font_size = min(160, max(24, float(font_size)))
    def stamp(seconds):
        total = round(seconds * 100)
        return f'{total // 360000}:{total // 6000 % 60:02}:{total // 100 % 60:02}.{total % 100:02}'
    header = f'''[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Short,{font},{font_size:g},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,3,1,5,40,40,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    lines = []
    for cue in cues:
        def safe(text):
            return text.upper().replace('\\', '').replace('{', '(').replace('}', ')')
        text = safe(cue['text'])
        size = max(12, round(width * font_size / 1080))
        while size > 12 and ImageFont.truetype(str(font_path(font)), size).getlength(text) > width * .84:
            size -= 1
        measured = ImageFont.truetype(str(font_path(font)), size).getlength(text)
        centre_x = width / 2 if x is None else max(measured / 2 + 8, min(width - measured / 2 - 8, x))
        centre_y = max(size * .8, min(height - size * .8, y))
        tag = f'{{\\an5\\pos({centre_x:.0f},{centre_y:.0f})\\fs{size}}}'
        words = cue.get('words')
        if not words:
            lines.append(f"Dialogue: 0,{stamp(cue['start'])},{stamp(cue['end'])},Short,,0,0,0,,{tag}{text}")
            continue
        for i, word in enumerate(words):
            finish = words[i + 1]['start'] if i + 1 < len(words) else cue['end']
            if finish - word['start'] < .01:
                continue
            # Invisible future words reserve their space, keeping the line still.
            parts = []
            for j, item in enumerate(words):
                style = ('{\\alpha&HFF&}' if j > i else
                         '{\\alpha&H00&\\c&H00D7FF&}' if j == i else
                         '{\\alpha&H00&\\c&HFFFFFF&}')
                parts.append(style + safe(item['text']))
            lines.append(f"Dialogue: 0,{stamp(word['start'])},{stamp(finish)},Short,,0,0,0,,{tag}{' '.join(parts)}")
    return header + '\n'.join(lines) + '\n'

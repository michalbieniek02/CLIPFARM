"""Real FFmpeg regression: retimed ASS/SRT, audio/video duration and exact source cut."""
import copy
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import av
from captions import FONT_SIZE, ass_text, phrases, progressive_cues, retime_cues
from engine import Pipeline, ROOT, subtitle_text

work = ROOT / 'checks/caption-speed'
work.mkdir(parents=True, exist_ok=True)
p = Pipeline(print)
source = work / 'source.mp4'
# Blue footage begins at the selected end: it must never enter either export.
p.run([p.ffmpeg(), '-y', '-f', 'lavfi', '-i',
       "color=c=red:s=320x180:r=30:d=12,drawbox=x=0:y=0:w=iw:h=ih:color=blue:t=fill:enable='gte(t,8)'",
       '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000:duration=12',
       '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', str(source)])
words = [{'start': 2.4, 'end': 2.8, 'text': 'ONE'},
         {'start': 3.3, 'end': 3.8, 'text': 'TWO'},
         {'start': 6.8, 'end': 7.2, 'text': 'THREE'},
         {'start': 7.6, 'end': 8.0, 'text': 'FOUR'}]
rows = [{'start': 2.4, 'end': 8., 'text': 'ONE TWO THREE FOUR', 'words': words}]
original = copy.deepcopy(rows)
raw = phrases(rows, 2., 8.)
raw_copy = copy.deepcopy(raw)
fast = retime_cues(raw, 1.1)
assert raw == raw_copy
assert fast[0]['start'] == raw[0]['start'] / 1.1
assert fast[-1]['words'][-1]['start'] == (7.6 - 2) / 1.1
assert FONT_SIZE == round(70 * 1.2)
assert 'Style: Short,Anton,84,' in ass_text(fast, 1080, 1920, 1440)
assert '\\fs84' in ass_text(fast, 1080, 1920, 1440)
clip = [{'start': 2., 'end': 8., 'title': 'Synchronizacja', 'score': 8, 'reason': ''}]

for speed_up in (False, True):
    speed = 1.1 if speed_up else 1.
    destination = work / ('fast' if speed_up else 'normal')
    files = p.export(source, clip, rows, destination, burn=True, speed_up=speed_up)
    assert rows == original, 'Do not alter saved source transcript timestamps'
    stem = Path(files[0]).stem
    cues = retime_cues(raw, speed)
    assert (destination / (stem + '.captions.srt')).read_text(encoding='utf-8') == subtitle_text(progressive_cues(cues), 0, 6 / speed)
    ass = (destination / (stem + '.captions.ass')).read_text(encoding='utf-8')
    assert ass == ass_text(cues, 1080, 1920, 1403.75)
    with av.open(files[0]) as container:
        durations = [float(s.duration * s.time_base) for s in container.streams]
        assert all(abs(d - 6 / speed) < .12 for d in durations), durations
        assert max(durations) - min(durations) < .12, durations
        before = after = late = False
        for frame in container.decode(video=0):
            image = frame.to_image()
            # The displayed film centre must remain red, including the final frame.
            red, green, blue = image.getpixel((540, 960))
            assert red > 180 and blue < 50, ('Source end leaked', frame.time)
            band = image.crop((80, 1375, 1000, 1510))
            bright = band.getextrema()[0][1] > 180
            if .20 / speed <= frame.time <= .30 / speed:
                assert not bright, 'Caption precedes the first spoken word'
                before = True
            if .50 / speed <= frame.time <= .65 / speed:
                assert bright, 'First word is missing at its speech timestamp'
                after = True
            if 5.70 / speed <= frame.time <= 5.85 / speed:
                assert bright, 'Last word has drifted beyond its speech timestamp'
                late = True
                image.save(destination / 'last-word.png')
        assert before and after and late
print('PASS: 1x/1.1x ASS and SRT word timing, unchanged source transcript, AV duration, no footage beyond clip end, burned first/last words, font +20%.')

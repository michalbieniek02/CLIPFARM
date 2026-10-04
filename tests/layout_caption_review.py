"""Offline, real CPU exports: focus geometry, padding, editable caption styling.

The source encodes horizontal position in red and vertical position in green,
so rendered output independently reveals which source location was selected.
"""
import copy
import json
import math
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch

import av
import numpy as np
from PIL import Image
from PySide6.QtGui import QGuiApplication

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend import Backend
from engine import Pipeline

app = QGuiApplication.instance() or QGuiApplication([])
pipeline = Pipeline()
clips = [{'start': 0, 'end': 1, 'title': 'Deterministic test', 'reason': 'QA', 'score': 8}]
segments = [{'start': 0, 'end': 1, 'text': 'TEST ŻÓŁW', 'words': [
    {'start': 0, 'end': .4, 'text': 'TEST'}, {'start': .4, 'end': .95, 'text': 'ŻÓŁW'}]}]


def source(path, width, height):
    rgb = np.empty((height, width, 3), dtype=np.uint8)
    rgb[:, :, 0] = np.linspace(0, 255, width, dtype=np.uint8)[None, :]
    rgb[:, :, 1] = np.linspace(0, 255, height, dtype=np.uint8)[:, None]
    rgb[:, :, 2] = 40
    image = path.with_suffix('.png')
    Image.fromarray(rgb).save(image)
    pipeline.run([pipeline.ffmpeg(), '-y', '-loop', '1', '-i', str(image), '-t', '2',
                  '-r', '2', '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '0',
                  '-pix_fmt', 'yuv420p', str(path)])
    return path


def read_frame(path):
    with av.open(str(path)) as container:
        frames = list(container.decode(video=0))
    assert len(frames) >= 2
    return frames[1].to_ndarray(format='rgb24')


def export(source_path, folder, **options):
    paths = pipeline.export(source_path, clips, copy.deepcopy(segments), folder,
                            encoder='cpu', framing='fit', **options)
    assert len(paths) == 1
    return read_frame(paths[0]), Path(paths[0])


def pixel(rgb, x, y):
    return np.median(rgb[y - 4:y + 5, x - 4:x + 5], axis=(0, 1))


def focus(rgb, x_fraction, y_fraction, x=540, y=960):
    actual = pixel(rgb, x, y)[:2]
    expected = np.array([x_fraction, y_fraction]) * 255
    assert np.max(np.abs(actual - expected)) < 9, (actual, expected)


def black(rgb, x, y):
    actual = pixel(rgb, x, y)
    assert actual.max() <= 4, (x, y, actual)


def caption_mask(rgb):
    # Captions are in the otherwise black top bar, away from source pixels.
    crop = rgb[:560]
    return (crop[:, :, 0] > 160) & (crop[:, :, 1] > 160)


def bounds(mask):
    yy, xx = np.nonzero(mask)
    assert len(xx) > 30, 'No burned caption pixels'
    return xx.min(), yy.min(), xx.max() + 1, yy.max() + 1


def done(backend, seconds=30):
    deadline = time.monotonic() + seconds
    while backend.busy:
        app.processEvents()
        if time.monotonic() > deadline:
            raise AssertionError(backend.status + '\n' + backend.logs)
        time.sleep(.005)
    app.processEvents()
    assert not backend.errorMessage, backend.errorMessage


(ROOT / 'checks').mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='layout-caption-', dir=ROOT / 'checks') as temp:
    out = Path(temp)
    landscape = source(out / 'landscape.mp4', 320, 180)
    tall = source(out / 'tall.mp4', 160, 320)
    with patch.object(Pipeline, 'transcribe', side_effect=AssertionError('No Whisper request')), \
         patch.object(Pipeline, 'select', side_effect=AssertionError('No AI selection')):
        fitted, _ = export(landscape, out / 'default', burn=False)
        assert fitted.shape == (1920, 1080, 3)
        focus(fitted, .5, .5)
        black(fitted, 540, 100); black(fitted, 540, 1820)

        zoomed, _ = export(landscape, out / 'zoomed', burn=False,
                           fit_zoom=2, fit_focus=(.75, .25))
        focus(zoomed, .75, .25)
        black(zoomed, 540, 200); black(zoomed, 540, 1900)
        # Moving focus changes the sampled source area rather than stretching it.
        panned, _ = export(landscape, out / 'panned', burn=False,
                           fit_zoom=2, fit_focus=(.25, .25))
        focus(panned, .25, .25)
        assert abs(int(pixel(zoomed, 650, 960)[0]) - int(pixel(zoomed, 540, 960)[0]) - 13) < 4

        tinted, _ = export(landscape, out / 'tinted', burn=False, light_color=True,
                           fit_zoom=2, fit_focus=(.75, .25))
        # Color adjustments must happen before filling uncovered canvas pixels.
        black(tinted, 540, 200); black(tinted, 540, 1900)
        assert np.abs(pixel(tinted, 540, 960) - pixel(zoomed, 540, 960)).max() >= 3

        styled = dict(burn=True, fit_zoom=2, fit_focus=(.75, .25),
                      caption_font='Montserrat', caption_size=60,
                      caption_position=(.35, .2))
        captioned, caption_path = export(landscape, out / 'captioned', **styled)
        mirrored, mirror_path = export(landscape, out / 'mirrored', mirror=True, **styled)
        focus(captioned, .75, .25); focus(mirrored, .25, .25)
        first_mask, mirror_mask = caption_mask(captioned), caption_mask(mirrored)
        intersection = np.count_nonzero(first_mask & mirror_mask)
        union = np.count_nonzero(first_mask | mirror_mask)
        assert intersection / union > .98, 'Caption pixels were mirrored or displaced with footage'
        left, top, right, bottom = bounds(first_mask)
        assert abs((left + right) / 2 - .35 * 1080) < 10
        assert abs((top + bottom) / 2 - .2 * 1920) < 12
        ass = next(caption_path.parent.glob('*.ass')).read_text(encoding='utf-8')
        assert 'Style: Short,Montserrat,60,' in ass and '\\pos(378,384)' in ass
        assert '0:00:00.40' in ass and 'ŻÓŁW' in ass
        assert (caption_path.with_suffix('.captions.srt')).is_file()
        assert 'ŻÓŁW' in caption_path.with_suffix('.captions.srt').read_text(encoding='utf-8')
        mirror_ass = next(mirror_path.parent.glob('*.ass')).read_text(encoding='utf-8')
        assert mirror_ass == ass

        larger, _ = export(landscape, out / 'larger', **{**styled, 'caption_size': 120})
        large_bounds = bounds(caption_mask(larger))
        assert 1.8 < (large_bounds[2] - large_bounds[0]) / (right - left) < 2.2
        assert 1.7 < (large_bounds[3] - large_bounds[1]) / (bottom - top) < 2.3
        alternative, _ = export(landscape, out / 'alternative', **{**styled, 'caption_font': 'Anton'})
        alternative_width = bounds(caption_mask(alternative))
        assert abs((alternative_width[2] - alternative_width[0]) - (right - left)) > 15

        # A narrow/tall source keeps the established 264px caption strip by default.
        tall_fit, tall_path = export(tall, out / 'tall-default', burn=True)
        focus(tall_fit, .5, .5, y=828)
        black(tall_fit, 20, 600); black(tall_fit, 540, 1880)
        assert pixel(tall_fit, 540, 1640).max() > 100
        black(tall_fit, 540, 1690)
        tall_ass = next(tall_path.parent.glob('*.ass')).read_text(encoding='utf-8')
        assert '\\pos(540,1790)' in tall_ass
        custom_tall, _ = export(tall, out / 'tall-custom', burn=True,
                                caption_position=(.5, .7))
        focus(custom_tall, .5, .5)
        assert pixel(custom_tall, 540, 1880).max() > 100

        original, _ = export(landscape, out / 'original', burn=False, vertical=False,
                             fit_zoom=4, fit_focus=(0, 0))
        assert original.shape == (180, 320, 3)
        focus(original, .5, .5, x=160, y=90)

        backend = Backend()
        with patch('backend.ROOT', out):
            backend.source = landscape
            backend.metadata = pipeline.probe(landscape)
            backend.work = out / 'work'; backend.work.mkdir()
            backend.segments = copy.deepcopy(segments)
            backend.model.replace(backend.clip_rows(clips, landscape, backend.work))
            baseline = copy.deepcopy(backend.settings)
            for key in ('caption_size', 'caption_x', 'caption_y', 'fit_zoom', 'fit_x', 'fit_y'):
                for invalid in (float('nan'), float('inf'), '-inf', 'not a number', None):
                    old = backend.settings[key]
                    backend.setSetting(key, invalid)
                    assert backend.settings[key] == old, (key, invalid)
            backend.setSetting('caption_size', 200); assert backend.captionSize == 160
            backend.setSetting('caption_size', -4); assert backend.captionSize == 24
            backend.setSetting('caption_size', 104)
            backend.setSetting('caption_font', 'poppins'); assert backend.captionFont == 'Poppins'
            for key, value in {'caption_custom': True, 'caption_x': .31, 'caption_y': .22,
                               'fit_zoom': 2.3, 'fit_x': .8, 'fit_y': .15}.items():
                backend.setSetting(key, value)
            initial_words = copy.deepcopy(backend.segments[0]['words'])
            assert backend.editCaption(0, 'NOWY NAPIS')
            assert [(w['start'], w['end']) for w in backend.segments[0]['words']] == [
                (w['start'], w['end']) for w in initial_words]
            assert [w['text'] for w in backend.segments[0]['words']] == ['NOWY', 'NAPIS']
            assert not backend.editCaption(0, '   ')
            backend.dismissError()
            assert backend.editCaption(0, 'NOWY POPRAWIONY NAPIS')
            edited = backend.segments[0]
            assert len(edited['words']) == 3 and edited['words'][0]['start'] == initial_words[0]['start']
            assert math.isclose(edited['words'][-1]['end'], initial_words[-1]['end'])
            assert all(a['end'] <= b['start'] + 1e-8 for a, b in zip(edited['words'], edited['words'][1:]))
            assert 'synchronizację' in backend.status
            persisted = json.loads((backend.work / 'transcript.json').read_text(encoding='utf-8'))
            assert persisted['segments'] == backend.segments

            expected_settings = copy.deepcopy(backend.settings)
            expected_segments = copy.deepcopy(backend.segments)
            project = out / 'project.json'
            backend.saveProjectTo(str(project)); done(backend)
            for key, value in baseline.items():
                backend.setSetting(key, value)
            backend.segments = []
            backend.openProjectFrom(str(project)); done(backend)
            assert backend.settings == expected_settings and backend.segments == expected_segments
            assert backend.clipCount == 1
            # Malformed numeric fields must not enter active settings when opening.
            malformed = json.loads(project.read_text(encoding='utf-8'))
            malformed['settings'].update(caption_size=float('nan'), fit_x='nonsense',
                                          fit_zoom=float('inf'), caption_font='../not-a-font.ttf')
            project.write_text(json.dumps(malformed), encoding='utf-8')
            backend.openProjectFrom(str(project)); done(backend)
            assert backend.captionFont == 'Anton'
            assert backend.captionSize == expected_settings['caption_size']
            assert backend.settings['fit_x'] == .8 and backend.settings['fit_zoom'] == 2.3
            assert all(math.isfinite(backend.settings[key]) for key in (
                'caption_size', 'caption_x', 'caption_y', 'fit_zoom', 'fit_x', 'fit_y'))
        backend._motion_timer.stop()

print('PASS: real CPU zoom/focus, mirror, black padding, caption fonts/sizes/positions, '
      'tall/original formats, editable timings, typed settings and project round-trip without AI')

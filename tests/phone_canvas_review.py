"""Offline encoded phone output: real crop geometry, fill, captions and face fallback."""
import json
from fractions import Fraction
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

import av
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import Pipeline
from framing import face_filter, face_track, fit_filter
from video_layout import (FORMAT_CHOICES, FORMAT_ORIGINAL, FORMAT_PHONE, FORMAT_VERTICAL,
                          canvas_for_format, frame_layout)

pipeline = Pipeline()
phone = canvas_for_format(FORMAT_PHONE)
assert phone == (1080, 2340)
assert canvas_for_format(FORMAT_VERTICAL) == (1080, 1920)
assert FORMAT_ORIGINAL in FORMAT_CHOICES
clips = [{'start': 0, 'end': 1, 'title': 'Phone output', 'reason': 'QA', 'score': 8}]
segments = [{'start': 0, 'end': 1, 'text': 'TEST', 'words': [
    {'start': 0, 'end': .95, 'text': 'TEST'}]}]


def source(path, width=320, height=180):
    rgb = np.empty((height, width, 3), dtype=np.uint8)
    rgb[:, :, 0] = np.linspace(32, 224, width, dtype=np.uint8)[None, :]
    rgb[:, :, 1] = np.linspace(32, 224, height, dtype=np.uint8)[:, None]
    rgb[:, :, 2] = 50
    with av.open(str(path), 'w') as container:
        stream = container.add_stream('ffv1', rate=2)
        stream.width, stream.height, stream.pix_fmt = width, height, 'bgr0'
        for n in range(4):
            frame = av.VideoFrame.from_ndarray(rgb, format='rgb24')
            frame.pts = n
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    return path


def export(path, folder, **options):
    files = pipeline.export(path, clips, segments, folder, encoder='cpu',
                            canvas_size=phone, **options)
    with av.open(files[0]) as container:
        frames = list(container.decode(video=0))
    assert len(frames) == 2, (path.name, pipeline.probe(path), pipeline.probe(files[0]),
                              [frame.time for frame in frames])
    return frames[1].to_ndarray(format='rgb24'), Path(files[0])


def pixel(rgb, x, y):
    return np.median(rgb[y - 4:y + 5, x - 4:x + 5], axis=(0, 1))


def focus(rgb, x, y, output_x=540, output_y=1170):
    expected = np.array([x, y]) * 192 + 32
    assert np.max(np.abs(pixel(rgb, output_x, output_y)[:2] - expected)) < 7


def fills(rgb):
    # Every source pixel has a blue channel of 50. Black padding is therefore
    # distinguishable even at the image corners and under extreme crop pans.
    assert rgb.shape == (2340, 1080, 3)
    assert np.min(np.max(rgb, axis=2)) > 20, 'The cover export contains an empty pixel'


(ROOT / 'checks').mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='phone-canvas-', dir=ROOT / 'checks') as temp:
    folder = Path(temp)
    landscape = source(folder / 'gradient.mkv')
    empty_folder = folder / 'empty-export'
    assert pipeline.export(landscape, [], [], empty_folder, encoder='cpu', canvas_size=phone) == []
    assert json.loads((empty_folder / 'clips.json').read_text())['canvas_size'] == [1080, 2340]
    centered, _ = export(landscape, folder / 'center', framing='center')
    fills(centered)
    focus(centered, .5, .5)
    # Independently infer the scale on each axis from the encoded gradients.
    red_delta = pixel(centered, 1000, 1170)[0] - pixel(centered, 80, 1170)[0]
    green_delta = pixel(centered, 540, 2200)[1] - pixel(centered, 540, 140)[1]
    x_scale = 920 / (red_delta * 319 / 192)
    y_scale = 2060 / (green_delta * 179 / 192)
    assert abs(x_scale - 13) < 1 and abs(y_scale - 13) < .5, (x_scale, y_scale)
    assert abs(x_scale - y_scale) / y_scale < .08, 'The source was stretched'

    panned, _ = export(landscape, folder / 'panned', framing='center',
                       fit_focus=(.25, .05))
    fills(panned)
    focus(panned, .25, .5)  # No vertical travel is available at base cover scale.
    zoomed, _ = export(landscape, folder / 'zoomed', framing='center',
                       fit_zoom=3, fit_focus=(.7, .2))
    fills(zoomed)
    focus(zoomed, .7, .2)
    clamped, _ = export(landscape, folder / 'clamped', framing='center',
                        fit_focus=(0, 1))
    fills(clamped)
    focus(clamped, 1080 / 2 / 4160, .5)
    mirrored, _ = export(landscape, folder / 'mirror', framing='center',
                         fit_focus=(.25, .5), mirror=True, light_color=False)
    fills(mirrored)
    focus(mirrored, .75, .5)

    captioned, caption_path = export(landscape, folder / 'captions', framing='center',
        burn=True, caption_font='Montserrat', caption_size=80, caption_position=(.35, .2))
    ass = next(caption_path.parent.glob('*.ass')).read_text(encoding='utf-8')
    assert 'PlayResX: 1080' in ass and 'PlayResY: 2340' in ass
    assert '\\pos(378,468)' in ass
    yy, xx = np.nonzero((captioned[:, :, 0] > 240) & (captioned[:, :, 1] > 150))
    assert len(xx) > 100 and abs((xx.min() + xx.max()) / 2 - 378) < 12
    assert abs((yy.min() + yy.max()) / 2 - 468) < 12
    manifest = json.loads((caption_path.parent / 'clips.json').read_text(encoding='utf-8'))
    assert manifest['canvas_size'] == [1080, 2340]

    fitted, _ = export(landscape, folder / 'fit', framing='fit')
    assert fitted.shape == (2340, 1080, 3)
    focus(fitted, .5, .5)
    assert pixel(fitted, 540, 80).max() < 5 and pixel(fitted, 540, 2260).max() < 5
    original, original_path = export(landscape, folder / 'original', vertical=False,
                                    framing='center', fit_zoom=4, fit_focus=(0, 1))
    assert original.shape == (180, 320, 3)
    focus(original, .5, .5, output_x=160, output_y=90)
    assert json.loads((original_path.parent / 'clips.json').read_text())['canvas_size'] == [320, 180]

    # The actual detector sees no face in a gradient; fallback retains the
    # selected canvas rather than reverting to a standard 9:16 crop.
    assert face_track(landscape, 0, 1, pipeline.check, lambda _: None, phone) is None
    assert face_filter(landscape, 0, 1, folder / 'none.txt', pipeline.check,
                       lambda _: None, phone) == fit_filter(phone)
    fallback, _ = export(landscape, folder / 'face-fallback', framing='face')
    assert fallback.shape == (2340, 1080, 3)
    assert pixel(fallback, 540, 80).max() < 5

    # Exercise a real detected face and inspect its source crop dimensions.
    portrait = np.array(Image.open(ROOT / 'assets' / 'settings-preview-person.png')
                        .convert('RGB').resize((640, 360)))
    person = folder / 'person.mkv'
    with av.open(str(person), 'w') as container:
        stream = container.add_stream('ffv1', rate=2)
        stream.width, stream.height, stream.pix_fmt = 640, 360, 'bgr0'
        for n in range(4):
            frame = av.VideoFrame.from_ndarray(portrait, format='rgb24'); frame.pts = n
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    track = face_track(person, 0, 1, pipeline.check, lambda _: None, phone)
    assert track is not None and track[:2] == (166, 360), track
    assert abs(track[0] / track[1] - 1080 / 2340) < .002
    followed, _ = export(person, folder / 'face', framing='face')
    assert followed.shape == (2340, 1080, 3)
    followed_path = next((folder / 'face').glob('*.mp4'))
    assert abs(pipeline.probe(followed_path)['duration'] - 1) < .002

    # Verify Pipeline's actual MP4 muxing, which must retain the final frame
    # after the face filter, and preserve the input's VFR timestamps too.
    for label, selected, speed in (
            ('60fps', list(range(120)), False),
            ('vfr', [n for n in range(120) if n % 3 == 0 or n % 5 == 0], False),
            ('speed', list(range(120)), True)):
        movie = folder / f'{label}.mkv'
        with av.open(str(movie), 'w') as container:
            stream = container.add_stream('ffv1', rate=60)
            stream.width, stream.height, stream.pix_fmt = 640, 360, 'bgr0'
            for n in selected:
                frame = av.VideoFrame.from_ndarray(portrait, format='rgb24')
                frame.pts, frame.time_base = n, Fraction(1, 60)
                for packet in stream.encode(frame):
                    container.mux(packet)
            for packet in stream.encode():
                container.mux(packet)
        with av.open(str(movie)) as container:
            wanted = [frame.time for frame in container.decode(video=0) if frame.time < 1]
        tracked = (166, 360, [(0, 240, 0), (.5, 250, 0), (1, 260, 0)])
        with patch('framing.face_track', return_value=tracked):
            files = pipeline.export(movie, clips, [], folder / f'{label}-output',
                encoder='cpu', framing='face', canvas_size=(180, 390), speed_up=speed)
        with av.open(files[0]) as container:
            observed = [frame.time for frame in container.decode(video=0)]
        assert len(observed) == len(wanted), (label, len(observed), len(wanted),
                                            observed[-8:], wanted[-8:], pipeline.probe(files[0]))
        divisor = 1.1 if speed else 1
        assert np.max(np.abs(np.array(observed) - np.array(wanted) / divisor)) < .002

    # Geometry clamps extreme center focus even with zoom, independently of
    # filter encoding. Fit still intentionally permits uncovered black space.
    for fx in (0, .5, 1):
        for fy in (0, .5, 1):
            layout = frame_layout(320, 180, fitted=False, zoom=4,
                                  focus_x=fx, focus_y=fy, canvas_size=phone)
            assert layout['image_x'] <= 0 and layout['image_y'] <= 0
            assert layout['image_x'] + layout['image_width'] >= 1080
            assert layout['image_y'] + layout['image_height'] >= 2340

print('PASS: encoded 1080x2340 fill, unstretched crop, source pan/zoom and clamp, mirror, '
      'caption placement, fit/original, manifest, real face crop/fallback and 60fps/VFR/speed timestamps')

"""Continuous face crop curves and real 60 fps/VFR FFmpeg output; offline."""
from bisect import bisect_right
from pathlib import Path
import json
import subprocess
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import av
import numpy as np
from PIL import Image
from engine import Pipeline, Cancelled
from framing import FIT_FILTER, _axis_curve, face_filter, face_track


def evaluate(times, curves, when):
    i = max(0, min(len(curves) - 1, bisect_right(times, when) - 1))
    s = max(0, min(1, (when - times[i]) / (times[i + 1] - times[i])))
    a, b, c, d = curves[i]
    return a + s * (b + s * (c + s * d))


times = [0, .5, 1, 1.5, 2, 2.5, 3]
xs = [40, 40, 150, 280, 390, 390, 390]
curve = _axis_curve(times, xs)
for i, coefficients in enumerate(curve):
    a, b, c, d = coefficients
    assert abs(a - xs[i]) < 1e-8
    assert abs(a + b + c + d - xs[i + 1]) < 1e-8
    values = [evaluate(times, curve, t) for t in np.linspace(times[i], times[i + 1], 101)]
    assert min(values) >= min(xs[i:i + 2]) - 1e-8
    assert max(values) <= max(xs[i:i + 2]) + 1e-8
    if i:
        old = curve[i - 1]
        left_speed = (old[1] + 2 * old[2] + 3 * old[3]) / (times[i] - times[i - 1])
        assert abs(left_speed - b / (times[i + 1] - times[i])) < 1e-8
assert abs(curve[0][1]) < 1e-8
assert abs(curve[-1][1] + 2 * curve[-1][2] + 3 * curve[-1][3]) < 1e-8
for values in ([5, 20, 5, 20, 5, 5, 0], [0, 0, 0, 0, 0, 0, 0]):
    bounded = _axis_curve(times, values)
    for i in range(len(bounded)):
        segment = [evaluate(times, bounded, t) for t in np.linspace(times[i], times[i + 1], 101)]
        assert min(segment) >= min(values[i:i + 2]) - 1e-8
        assert max(segment) <= max(values[i:i + 2]) + 1e-8

pipeline = Pipeline()
checks = Path(__file__).resolve().parents[1] / 'checks'
checks.mkdir(exist_ok=True)
evidence = []
with tempfile.TemporaryDirectory(dir=checks) as temporary:
    folder = Path(temporary)
    source = folder / 'gradient.mkv'
    # A source x coordinate is encoded directly in each pixel's luminance.
    # FFV1 keeps the gradient lossless, so the output reveals the actual crop
    # on every frame, rather than merely testing the generated command text.
    rows = np.broadcast_to((np.arange(640) // 3).astype(np.uint8), (360, 640)).copy()
    with av.open(str(source), 'w') as container:
        stream = container.add_stream('ffv1', rate=60)
        stream.width, stream.height, stream.pix_fmt = 640, 360, 'gray'
        for frame_number in range(180):
            frame = av.VideoFrame.from_ndarray(rows, format='gray')
            frame.pts = frame_number
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    track = (202, 360, list(zip(times, xs, [0] * len(times))))
    with patch('framing.face_track', return_value=track):
        filtered = face_filter(source, 0, 3, folder / 'follow.txt', pipeline.check, lambda _: None)
    assert len((folder / 'follow.txt').read_text().splitlines()) == len(times) - 1
    assert 'st(0,clip((t-' in (folder / 'follow.txt').read_text()
    for label, extra in [('60fps', ''), ('vfr', "select='not(mod(n,3))+not(mod(n,5))',")]:
        output = folder / f'{label}.mkv'
        result = subprocess.run([pipeline.ffmpeg(), '-hide_banner', '-loglevel', 'error',
            '-y', '-i', str(source), '-vf', extra + filtered + ',scale=202:360',
            '-fps_mode', 'passthrough', '-c:v', 'ffv1', '-pix_fmt', 'gray', str(output)],
            cwd=folder, capture_output=True, text=True, timeout=40)
        assert result.returncode == 0, result.stderr
        observed, positions, stamps = [], [], []
        with av.open(str(output)) as container:
            for frame in container.decode(video=0):
                position = float(np.median(frame.to_ndarray(format='gray')[:, 0])) * 3
                target = evaluate(times, curve, frame.time)
                observed.append(abs(position - target))
                positions.append(position)
                stamps.append(frame.time)
        assert len(positions) == (180 if label == '60fps' else 84), len(positions)
        assert max(observed) < 7, (label, max(observed))
        # Fixed 30 Hz integer commands repeat every other position on 60 Hz
        # footage. During this pan each actual frame should advance instead.
        active = [p for p, t in zip(positions, stamps) if 1.04 < t < 1.43]
        assert all(b > a for a, b in zip(active, active[1:])), (label, active)
        jumps = [abs(b - a) for a, b in zip(positions, positions[1:])]
        assert max(jumps) < (9 if label == '60fps' else 21), (label, max(jumps))
        evidence.append({'rate': label, 'frames': len(positions),
                         'max_coordinate_error_px': round(max(observed), 3),
                         'max_frame_motion_px': max(jumps)})
    with patch('framing.face_track', return_value=None):
        assert face_filter(source, 0, 3, folder / 'none.txt', pipeline.check, lambda _: None) == FIT_FILTER
        assert not (folder / 'none.txt').exists()
    # Exercise the bundled detector too, using the fictional preview portrait.
    # The person moves across the landscape; missing detections keep the prior
    # target instead of resetting the crop to center.
    portrait = np.array(Image.open(checks.parent / 'assets' / 'settings-preview-person.png')
                        .convert('RGB').resize((640, 360)))
    person_source = folder / 'person.mkv'
    with av.open(str(person_source), 'w') as container:
        stream = container.add_stream('ffv1', rate=30)
        stream.width, stream.height, stream.pix_fmt = 800, 360, 'bgr0'
        for frame_number in range(60):
            image = np.zeros((360, 800, 3), dtype=np.uint8)
            offset = round(frame_number * 100 / 59)
            image[:, offset:offset + 640] = portrait
            frame = av.VideoFrame.from_ndarray(image, format='rgb24')
            frame.pts = frame_number
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    detected = face_track(person_source, 0, 2, pipeline.check, lambda _: None)
    assert detected is not None, 'The bundled detector must recognize the sample person'
    crop_w, crop_h, detected_points = detected
    assert crop_w == 202 and crop_h == 360
    assert len(detected_points) >= 15, 'Detection should sample around 8 times per second'
    assert max(b[0] - a[0] for a, b in zip(detected_points, detected_points[1:])) <= .14
    assert detected_points[-1][1] - detected_points[0][1] > 30, detected_points
    assert all(0 <= x <= 800 - crop_w and 0 <= y <= 360 - crop_h
               for _, x, y in detected_points)
    assert face_track(source, 0, 3, pipeline.check, lambda _: None) is None
    def cancelled():
        raise Cancelled()
    with patch('framing.face_track', return_value=track):
        try:
            face_filter(source, 0, 3, folder / 'cancel.txt', cancelled, lambda _: None)
        except Cancelled:
            pass
        else:
            raise AssertionError('Crop command generation must remain cancellable')
        assert not (folder / 'cancel.txt').exists()
    try:
        face_track(person_source, 0, 2, cancelled, lambda _: None)
    except Cancelled:
        pass
    else:
        raise AssertionError('Actual face decoding must remain cancellable')

print(json.dumps({'face_smoothing': 'PASS', 'rendered': evidence}))

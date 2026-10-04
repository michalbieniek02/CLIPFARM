"""Local 9:16 layouts and YuNet face-following crop paths."""
from pathlib import Path
import math

FRAMING_LABELS = {
    'Cały obraz · czarne pasy': 'fit',
    'Wypełnij · środek': 'center',
    'Podążaj za twarzą': 'face',
}
FRAMING_HELP = {
    'fit': 'Cały film mieści się w pionie. Wolne miejsce wypełnią czarne pasy.',
    'center': 'Obraz wypełni pion. Boki filmu zostaną przycięte.',
    'face': 'Kadr podąża za widoczną twarzą. Bez twarzy: cały obraz z pasami.',
}
FIT_FILTER = 'scale=1080:1920:force_original_aspect_ratio=decrease:force_divisible_by=2,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1'
CENTER_FILTER = 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1'


def face_track(source, start, end, check, log):
    import av
    import cv2
    model = Path(__file__).with_name('assets') / 'face' / 'yunet.onnx'
    if not model.exists():
        raise ValueError('Brak lokalnego modelu twarzy w assets/face/yunet.onnx.')
    detector = cv2.FaceDetectorYN.create(str(model), '', (640, 360), .75, .3, 5000)
    points, found, previous = [], 0, None
    previous_time = None
    next_sample = start
    log('Lokalne wykrywanie twarzy i dopasowanie kadru…')
    with av.open(str(source)) as container:
        stream = container.streams.video[0]
        width, height = stream.width, stream.height
        crop_w = max(2, int(min(width, height * 9 / 16)) // 2 * 2)
        crop_h = max(2, int(min(height, width * 16 / 9)) // 2 * 2)
        container.seek(int(start * av.time_base), backward=True)
        for frame in container.decode(stream):
            check()
            when = frame.time
            if when is None or when < next_sample - .001:
                continue
            if when >= end:
                break
            next_sample = start + (math.floor((when - start) / .125) + 1) * .125
            small = frame.reformat(width=max(32, round(width * min(1, 640 / width, 640 / height))),
                                   height=max(32, round(height * min(1, 640 / width, 640 / height))),
                                   format='bgr24').to_ndarray()
            sh, sw = small.shape[:2]
            detector.setInputSize((sw, sh))
            _, faces = detector.detect(small)
            first_face = False
            if faces is not None and len(faces):
                # Favor a large face, with continuity when several people are visible.
                def priority(face):
                    cx = (face[0] + face[2] / 2) * width / sw
                    cy = (face[1] + face[3] / 2) * height / sh
                    distance = 0 if previous is None else math.hypot(
                        (cx - previous[0]) / width, (cy - previous[1]) / height)
                    return face[2] * face[3] * face[-1] / (1 + 3 * distance)
                face = max(faces, key=priority)
                center = ((face[0] + face[2] / 2) * width / sw,
                          (face[1] + face[3] / 2) * height / sh)
                first_face = previous is None
                if previous is not None:
                    # Use the same smoothing for a large move as for a small one.
                    # The old cutoff made a newly selected face snap the camera.
                    elapsed = max(.001, when - previous_time)
                    alpha = 1 - math.exp(-elapsed / .48)
                    center = tuple(alpha * new + (1 - alpha) * old
                                   for new, old in zip(center, previous))
                previous = center
                previous_time = when
                found += 1
            center = previous or (width / 2, height / 2)
            x = max(0, min(width - crop_w, center[0] - crop_w / 2))
            y = max(0, min(height - crop_h, center[1] - crop_h / 2))
            if first_face:
                # If the first face appears after a few empty samples, start the
                # clip at that position instead of panning from a guessed center.
                points = [(t, x, y) for t, _, _ in points]
            points.append((max(0, when - start), x, y))
    if not found:
        log('Nie wykryto twarzy — zachowuję cały obraz z czarnymi pasami.')
        return None
    # Avoid a center-to-face camera move at the beginning if detection starts later.
    points.insert(0, (0, points[0][1], points[0][2]))
    points.append((end - start, points[-1][1], points[-1][2]))
    log(f'Twarz wykryta w {found} próbkach. Wygładzam ruch kadru.')
    return crop_w, crop_h, points


def _axis_curve(times, values):
    """Bounded cubic segments with continuous velocity and no target overshoot."""
    spans = [b - a for a, b in zip(times, times[1:])]
    slopes = [(b - a) / span for a, b, span in zip(values, values[1:], spans)]
    tangents = [0.0] * len(values)
    for i in range(1, len(values) - 1):
        before, after = slopes[i - 1], slopes[i]
        if before * after > 0:
            left, right = spans[i - 1], spans[i]
            w1, w2 = 2 * right + left, right + 2 * left
            tangents[i] = (w1 + w2) / (w1 / before + w2 / after)
    result = []
    for i, span in enumerate(spans):
        delta = values[i + 1] - values[i]
        m0, m1 = tangents[i] * span, tangents[i + 1] * span
        result.append((values[i], m0, 3 * delta - 2 * m0 - m1,
                       -2 * delta + m0 + m1))
    return result


def _curve_expression(start, duration, coefficients):
    # crop evaluates x/y for every input frame. Keep interpolation in its
    # expression, rather than sending integer positions at a fixed 30 Hz.
    a, b, c, d = coefficients
    return (f'st(0,clip((t-{start:.9f})/{duration:.9f},0,1));'
            f'{a:.9f}+ld(0)*({b:.9f}+ld(0)*({c:.9f}+ld(0)*{d:.9f}))')


def face_filter(source, start, end, command_file, check, log):
    track = face_track(source, start, end, check, log)
    if track is None:
        return FIT_FILTER
    width, height, points = track
    # Coalesce the duplicate zero-time anchor and any rounded decoder times.
    unique = {}
    for t, x, y in points:
        unique[round(t, 9)] = (x, y)
    points = [(t, *unique[t]) for t in sorted(unique)]
    knots, xs, ys = zip(*points)
    x_curve, y_curve = _axis_curve(knots, xs), _axis_curve(knots, ys)
    commands = []
    for i, (x, y) in enumerate(zip(x_curve, y_curve)):
        check()
        t, duration = knots[i], knots[i + 1] - knots[i]
        commands.append(f"{t:.9f} [enter] crop@follow x '{_curve_expression(t, duration, x)}', "
                        f"[enter] crop@follow y '{_curve_expression(t, duration, y)}';")
    Path(command_file).write_text('\n'.join(commands), encoding='utf-8')
    return (f"setpts=PTS-STARTPTS,sendcmd=f='{Path(command_file).name}',"
            f'crop@follow={width}:{height}:{int(points[0][1])}:{int(points[0][2])}:exact=1,'
            'scale=1080:1920,setsar=1')

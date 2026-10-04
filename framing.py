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
            next_sample = when + .5
            small = frame.reformat(width=max(32, round(width * min(1, 640 / width, 640 / height))),
                                   height=max(32, round(height * min(1, 640 / width, 640 / height))),
                                   format='bgr24').to_ndarray()
            sh, sw = small.shape[:2]
            detector.setInputSize((sw, sh))
            _, faces = detector.detect(small)
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
                if previous is not None and abs(center[0] - previous[0]) < crop_w * .75:
                    center = tuple(.65 * new + .35 * old for new, old in zip(center, previous))
                previous = center
                found += 1
            center = previous or (width / 2, height / 2)
            x = max(0, min(width - crop_w, center[0] - crop_w / 2))
            y = max(0, min(height - crop_h, center[1] - crop_h / 2))
            points.append((max(0, when - start), x, y))
    if not found:
        log('Nie wykryto twarzy — zachowuję cały obraz z czarnymi pasami.')
        return None
    # Avoid a center-to-face camera move at the beginning if detection starts later.
    points.insert(0, (0, points[0][1], points[0][2]))
    points.append((end - start, points[-1][1], points[-1][2]))
    log(f'Twarz wykryta w {found} próbkach. Wygładzam ruch kadru.')
    return crop_w, crop_h, points


def face_filter(source, start, end, command_file, check, log):
    import numpy as np
    track = face_track(source, start, end, check, log)
    if track is None:
        return FIT_FILTER
    width, height, points = track
    times = np.arange(0, end - start + .0001, 1 / 30)
    knots, xs, ys = zip(*points)
    x_values, y_values = np.interp(times, knots, xs), np.interp(times, knots, ys)
    commands = []
    for t, x, y in zip(times, x_values, y_values):
        check()
        commands.append(f'{t:.6f} crop@follow x {int(x)//2*2}, crop@follow y {int(y)//2*2};')
    Path(command_file).write_text('\n'.join(commands), encoding='utf-8')
    return (f"setpts=PTS-STARTPTS,sendcmd=f='{Path(command_file).name}',"
            f'crop@follow={width}:{height}:{int(points[0][1])//2*2}:{int(points[0][2])//2*2},'
            'scale=1080:1920,setsar=1')

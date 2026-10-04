"""Local thumbnails and a small, consistent line icon set."""
from PIL import Image, ImageDraw, ImageOps
import av


def thumbnail(source, seconds=0, size=(220, 124)):
    with av.open(str(source)) as container:
        stream = container.streams.video[0]
        if seconds > 0:
            container.seek(int(seconds * av.time_base), backward=True)
        frame = None
        for index, candidate in enumerate(container.decode(stream)):
            frame = candidate
            if candidate.time is None or candidate.time >= seconds or index > 300:
                break
        if frame is None:
            raise ValueError('Brak klatki podglądu.')
        image = ImageOps.fit(frame.to_image().convert('RGB'), size, method=Image.Resampling.LANCZOS)
    mask = Image.new('L', size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0]-1, size[1]-1), radius=12, fill=255)
    image = image.convert('RGBA')
    image.putalpha(mask)
    return image


def icon(name, color='#0071e3', size=24):
    scale = 4
    image = Image.new('RGBA', (size * scale, size * scale))
    draw = ImageDraw.Draw(image)
    def line(points, width=1.7):
        draw.line([(int(x * size * scale / 24), int(y * size * scale / 24)) for x, y in points],
                  fill=color, width=int(width * size * scale / 24), joint='curve')
    def rect(box, radius=3):
        draw.rounded_rectangle(tuple(int(v * size * scale / 24) for v in box),
            radius=int(radius * size * scale / 24), outline=color, width=int(1.7 * size * scale / 24))
    if name == 'film':
        rect((3, 3, 21, 21), 3)
        line([(7, 3), (7, 21)])
        line([(17, 3), (17, 21)])
        for y in (8, 12, 16):
            line([(3, y), (7, y)])
            line([(17, y), (21, y)])
    elif name == 'plus':
        line([(12, 5), (12, 19)])
        line([(5, 12), (19, 12)])
    elif name == 'play':
        line([(8, 5), (19, 12), (8, 19), (8, 5)])
    elif name == 'folder':
        line([(3, 8), (3, 5), (9, 5), (12, 8), (21, 8), (21, 20), (3, 20), (3, 8), (21, 8)])
    elif name == 'export':
        line([(5, 12), (5, 20), (19, 20), (19, 12)])
        line([(12, 15), (12, 3), (8, 7)])
        line([(12, 3), (16, 7)])
    return image.resize((size, size), Image.Resampling.LANCZOS)

"""Shared preview/export geometry: source focus, letterboxing and caption centres."""
import math

FORMAT_PHONE = 'Telefon 9:19,5'
FORMAT_VERTICAL = 'Pionowy 9:16'
FORMAT_ORIGINAL = 'Oryginalny'
FORMAT_CHOICES = (FORMAT_VERTICAL, FORMAT_PHONE, FORMAT_ORIGINAL)


def canvas_for_format(format):
    return (1080, 2340) if format == FORMAT_PHONE else (1080, 1920)


def canvas_dimensions(canvas_size):
    """An even output canvas usable by H.264 and the preview alike."""
    if len(canvas_size) != 2:
        raise ValueError('Kadr wymaga dwóch wymiarów.')
    dimensions = tuple(float(value) for value in canvas_size)
    if any(not math.isfinite(value) or value < 2 for value in dimensions):
        raise ValueError('Wymiary kadru muszą być dodatnimi liczbami.')
    return tuple(int(value) // 2 * 2 for value in dimensions)

SETTING_RANGES = {'caption_size': (24, 160), 'caption_x': (0, 1), 'caption_y': (0, 1),
                  'fit_zoom': (1, 4), 'fit_x': (0, 1), 'fit_y': (0, 1)}


def number(value, low, high):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError('Ustawienie musi być skończoną liczbą.')
    return min(high, max(low, value))


def frame_layout(width, height, vertical=True, fitted=True, zoom=1, focus_x=.5, focus_y=.5,
                 caption_position=None, reserve_captions=True, canvas_size=(1080, 1920)):
    from captions import placement
    width, height = max(2, width), max(2, height)
    zoom, focus_x, focus_y = number(zoom, 1, 4), number(focus_x, 0, 1), number(focus_y, 0, 1)
    canvas_w, canvas_h, caption_y, reserved = placement(width, height, vertical, fitted, canvas_size)
    default_fit = zoom == 1 and focus_x == .5 and focus_y == .5
    available_h = int(canvas_h * .8625) // 2 * 2 if vertical and fitted and reserved and reserve_captions and default_fit and caption_position is None else canvas_h
    if vertical and fitted:
        scale = min(canvas_w / width, available_h / height) * zoom
        image_w, image_h = max(2, round(width * scale / 2) * 2), max(2, round(height * scale / 2) * 2)
        image_x, image_y = round((canvas_w / 2 - image_w * focus_x) / 2) * 2, round((available_h / 2 - image_h * focus_y) / 2) * 2
        if not default_fit or caption_position is not None:
            bottom = image_y + image_h
            caption_y = bottom + min(canvas_h * 140 / 1920, (canvas_h - bottom) / 2) if canvas_h - bottom >= canvas_h * 180 / 1920 else canvas_h * .84375
    else:
        scale = max(canvas_w / width, canvas_h / height) * zoom if vertical else 1
        if vertical:
            # Cover must never leave an empty edge. Source focus is limited to
            # the crop's available travel instead of exposing black padding.
            image_w, image_h = math.ceil(width * scale / 2) * 2, math.ceil(height * scale / 2) * 2
            image_x = round(max(canvas_w - image_w, min(0, canvas_w / 2 - image_w * focus_x)) / 2) * 2
            image_y = round(max(canvas_h - image_h, min(0, canvas_h / 2 - image_h * focus_y)) / 2) * 2
        else:
            image_w, image_h = canvas_w, canvas_h
            image_x, image_y = 0, 0
    caption_x = canvas_w / 2
    if caption_position is not None:
        caption_x = number(caption_position[0], 0, 1) * canvas_w
        caption_y = number(caption_position[1], 0, 1) * canvas_h
    return {'canvas_width': canvas_w, 'canvas_height': canvas_h,
            'image_x': image_x, 'image_y': image_y, 'image_width': image_w, 'image_height': image_h,
            'caption_x': caption_x, 'caption_y': caption_y}


def letterbox_filter(layout):
    """Scale, crop the intersection and fill every uncovered pixel with black."""
    cw, ch = layout['canvas_width'], layout['canvas_height']
    iw, ih = layout['image_width'], layout['image_height']
    left, top = layout['image_x'], layout['image_y']
    x, y = max(0, -left), max(0, -top)
    visible_w = int(min(cw, left + iw) - max(0, left)) // 2 * 2
    visible_h = int(min(ch, top + ih) - max(0, top)) // 2 * 2
    return (f'scale={iw}:{ih},crop={visible_w}:{visible_h}:{int(x)}:{int(y)},'
            f'pad={cw}:{ch}:{int(max(0, left))}:{int(max(0, top))}:color=black,setsar=1')

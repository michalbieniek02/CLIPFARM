"""Package the supplied brand asset for UI and Windows icon formats."""
from pathlib import Path
from PIL import Image

assets = Path(__file__).with_name('assets')
image = Image.open(assets / 'clipfarm-logo.png').convert('RGBA')
# Separate mark and wordmark for small icons and the horizontal application header.
split = round(image.height * .83)
mark = image.crop((0, 0, image.width, split))
mark = mark.crop(mark.getbbox())
wordmark = image.crop((0, split, image.width, image.height))
wordmark = wordmark.crop(wordmark.getbbox())
mark.save(assets / 'clipfarm-mark.png')
wordmark.save(assets / 'clipfarm-wordmark.png')
image.crop(image.getbbox()).save(assets / 'clipfarm-lockup.png')
canvas = Image.new('RGBA', (256, 256))
mark.thumbnail((220, 220), Image.Resampling.LANCZOS)
canvas.alpha_composite(mark, ((256 - mark.width) // 2, (256 - mark.height) // 2))
canvas.save(assets / 'clipfarm.ico', sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print('Brand assets packaged:', image.size)

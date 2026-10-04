from functools import lru_cache
from pathlib import Path
from PIL import Image
import customtkinter as ctk

ASSETS = Path(__file__).with_name('assets')

@lru_cache(maxsize=3)
def asset(name):
    with Image.open(ASSETS / f'clipfarm-{name}.png') as image:
        return image.convert('RGBA')

def brand_image(name='mark', width=48, height=48):
    image = asset(name)
    scale = min(width / image.width, height / image.height)
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    return ctk.CTkImage(light_image=image, dark_image=image, size=size)

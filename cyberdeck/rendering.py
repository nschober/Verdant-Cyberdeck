"""Shared font cache; no repeated font-file loads during repaint."""
from functools import lru_cache
from PIL import ImageFont

@lru_cache(maxsize=64)
def font(path,size):return ImageFont.truetype(path,size)

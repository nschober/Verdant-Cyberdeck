"""ILI9488 DRM framebuffer backend for the complete Pwnagotchi UI."""
import fcntl
import logging
import mmap
import os
from pathlib import Path
import struct

from PIL import Image, ImageDraw
import sys
sys.path.insert(0, '/opt/tft-terminal')
from tft_view import draw_pointer
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.hw.base import DisplayImpl


class ILI9488(DisplayImpl):
    def __init__(self, config):
        super().__init__(config, 'ili9488')
        self._fd = None
        self._memory = None

    def layout(self):
        fonts.setup(16, 14, 16, 64, 28, 14)
        self._layout.update({
            'width': 480, 'height': 320,
            'face': (70, 65), 'name': (8, 36),
            'channel': (8, 4), 'aps': (100, 4), 'uptime': (320, 4),
            'line1': (0, 29, 479, 29), 'line2': (0, 289, 479, 289),
            'friend_face': (8, 257), 'friend_name': (80, 259),
            'shakes': (8, 296), 'mode': (425, 296),
            'status': {'pos': (8, 171), 'font': fonts.status_font(fonts.Medium), 'max': 46},
        })
        return self._layout

    def initialize(self):
        # Framebuffer numbers change when HDMI probes before/after the TFT.
        matches = [line.split()[0] for line in Path('/proc/fb').read_text().splitlines()
                   if 'ili9488' in line.lower()]
        if not matches:
            raise RuntimeError('ILI9488 framebuffer not found')
        device = '/dev/fb' + matches[0]
        logging.info('initializing ILI9488 TFT: %s', device)
        try:
            self._fd = os.open(device, os.O_RDWR)
            info = bytearray(160)
            fcntl.ioctl(self._fd, 0x4600, info, True)
            width, height, _, _, xoff, yoff, bpp = struct.unpack_from('7I', info)
            colors = tuple(struct.unpack_from('3I', info, offset) for offset in (32, 44, 56))
            if (width, height, xoff, yoff, bpp) != (480, 320, 0, 0, 32):
                raise RuntimeError('ILI9488 requires 480x320, zero offsets, 32 bits per pixel')
            if colors != ((16, 8, 0), (8, 8, 0), (0, 8, 0)):
                raise RuntimeError('ILI9488 requires BGRX pixel format')
            self._stride = int((Path('/sys/class/graphics') / Path(device).name / 'stride').read_text())
            if self._stride < width * 4:
                raise RuntimeError('Invalid framebuffer stride')
            self._memory = mmap.mmap(self._fd, self._stride * height)
            fcntl.ioctl(self._fd, 0x4611, 0)
        except BaseException:
            self.close()
            raise

    def render(self, canvas):
        if self._memory is None:
            raise RuntimeError('ILI9488 framebuffer is not initialized')
        if canvas.size != (480, 320):
            raise ValueError('ILI9488 requires a 480x320 canvas; use rotation 0 or 180')
        frame = canvas.convert('RGB')
        draw_pointer(ImageDraw.Draw(frame))
        raw = frame.tobytes('raw', 'BGRX')
        for row in range(320):
            offset = row * self._stride
            self._memory[offset:offset + 1920] = raw[row * 1920:(row + 1) * 1920]

    def clear(self):
        self.render(Image.new('RGB', (480, 320), 'white'))

    def close(self):
        if self._memory is not None:
            self._memory.close()
            self._memory = None
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None

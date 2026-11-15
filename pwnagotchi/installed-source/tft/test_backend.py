"""Hardware-independent checks for the full-engine framebuffer backend."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image
from pwnagotchi.ui.hw import display_for
from pwnagotchi.ui.hw.ili9488 import ILI9488
import pwnagotchi.ui.fonts as fonts


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.config = {'ui': {'display': {'type': 'ili9488'},
                              'font': {'name': 'DejaVuSansMono', 'size_offset': 0}}}
        fonts.init(self.config)

    def test_factory_and_full_ui_layout(self):
        backend = display_for(self.config)
        self.assertIsInstance(backend, ILI9488)
        layout = backend.layout()
        self.assertEqual((layout['width'], layout['height']), (480, 320))
        for key in ('face', 'name', 'channel', 'aps', 'uptime', 'friend_face',
                    'friend_name', 'shakes', 'mode', 'status'):
            self.assertIn(key, layout)

    def test_bgrx_and_padding(self):
        backend = ILI9488(self.config)
        backend._stride = 1936
        backend._memory = bytearray(b'\x7f' * (1936 * 320))
        backend.render(Image.new('RGB', (480, 320), (255, 64, 8)))
        self.assertEqual(backend._memory[:3], bytes((8, 64, 255)))
        self.assertEqual(backend._memory[1920:1936], b'\x7f' * 16)
        self.assertEqual(backend._memory[1936:1939], bytes((8, 64, 255)))
        self.assertEqual(backend._memory[-1936:-1933], bytes((8, 64, 255)))
        backend.clear()
        self.assertEqual(backend._memory[:3], b'\xff' * 3)

    def test_rejects_bad_canvas(self):
        backend = ILI9488(self.config)
        backend._memory = bytearray(1920 * 320)
        with self.assertRaises(ValueError):
            backend.render(Image.new('RGB', (320, 480)))


if __name__ == '__main__':
    unittest.main()

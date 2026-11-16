import hashlib
import json
import os
from pathlib import Path
import select
import subprocess
import tempfile
import time
import types
import unittest
from unittest.mock import patch
import zipfile
from PIL import Image
from cyberdeck.native import NativeDeck
from cyberdeck.alerts import AlertReader
from cyberdeck.file_events import FileEvents
from cyberdeck.mayhem import decode_screen,Remote
from cyberdeck.rendering import font
from cyberdeck.dashboard import Dashboard
from scripts import prepare_mayhem_update as update
ROOT=Path(__file__).resolve().parents[1]

class BatteryTests(unittest.TestCase):
    def test_idle_frame_is_reused_and_changes_invalidate(self):
        with tempfile.TemporaryDirectory() as directory:
            deck=NativeDeck(lambda _:None,lambda _:None,log_path=Path(directory)/'log',alert_reader=AlertReader(Path(directory)/'missing'))
            try:
                deck.enter_menu();deck.render()
                with patch.object(deck,'render',wraps=deck.render) as render:
                    for _ in range(120):
                        if deck.needs_redraw():deck.render()
                    self.assertEqual(render.call_count,0)
                    deck.status='Changed status';self.assertTrue(deck.needs_redraw())
                    deck.render();self.assertFalse(deck.needs_redraw())
                    deck.wifi();self.assertTrue(deck.needs_redraw())
            finally:deck.close_runtime()
    def test_font_objects_are_cached(self):
        path='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
        self.assertIs(font(path,15),font(path,15))
        self.assertIsNot(font(path,15),font(path,16))
    def test_pointer_atomic_rename_wakes_terminal(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'pointer.json';watch=FileEvents([path])
            try:
                if watch.fd is None:self.skipTest('inotify unavailable')
                tmp=path.with_suffix('.tmp');tmp.write_text('{}');tmp.replace(path)
                self.assertTrue(select.select([watch.fd],[],[],1)[0]);self.assertTrue(watch.drain())
                self.assertFalse(watch.drain())
            finally:watch.close()
    def test_stats_font_bridge_adds_three_points(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);package=base/'pwnagotchi/ui/hw';package.mkdir(parents=True)
            for p in (base/'pwnagotchi/__init__.py',base/'pwnagotchi/ui/__init__.py',package/'__init__.py'):p.write_text('')
            (base/'pwnagotchi/ui/fonts.py').write_text('calls=[]\ndef setup(*sizes):calls.append(sizes)\n')
            (package/'ili9488.py').write_text('from pwnagotchi.ui import fonts\nclass ILI9488:\n def layout(self):\n  fonts.setup(16,14,16,64,28,14)\n  return {"width":480,"height":320}\n')
            env=dict(os.environ,VERDANT_PWN_SCREEN='1',PYTHONPATH=str(ROOT/'bridge')+os.pathsep+str(base))
            code='from pwnagotchi.ui.hw.ili9488 import ILI9488; from pwnagotchi.ui import fonts; assert ILI9488().layout()["width"]==480; assert fonts.calls[-1]==(19,17,19,64,28,17)'
            r=subprocess.run(['/usr/bin/python3','-c',code],env=env,capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)

class RFTests(unittest.TestCase):
    def test_rf_navigation_is_bounded_and_contains_tx(self):
        app=Dashboard();app.enter_menu()
        try:
            self.assertIn('RF TOOLS',[b.label for b in app.buttons]);app.rf_menu()
            self.assertIn('DEVICE / RX / TX',[b.label for b in app.buttons])
            for group in ('RF SPECTRUM','RF PROTOCOLS','RF GSM','RF DEVICES'):
                app.tools(group);self.assertEqual(app.render().size,(480,320))
                for b in app.buttons:self.assertTrue(0<=b.rect[0]<b.rect[2]<=480 and 0<=b.rect[1]<b.rect[3]<=320)
        finally:app.shutdown()
    def test_user_gui_launch_goes_through_kali_terminal(self):
        with tempfile.TemporaryDirectory() as directory:
            calls=[];deck=NativeDeck(calls.append,lambda _:None,log_path=Path(directory)/'log')
            try:
                with patch('cyberdeck.native.installed',return_value=None),patch('cyberdeck.rf.user_tool_path',return_value='/home/kali/.local/bin/urh'):
                    deck.launch('urh')
                self.assertEqual(calls[0][-2:],['--gui','urh'])
                self.assertEqual(calls[0][0],'/usr/bin/env')
            finally:deck.close_runtime()

class MayhemTests(unittest.TestCase):
    def test_screen_protocol_both_dimensions_and_invalid_frame(self):
        for width,height in ((240,320),(320,480)):
            frame=decode_screen(b'screenframeshort\r\n'+(b'P'*width+b'\r\n')*height+b'ch> ')
            self.assertEqual(frame.size,(width,height));self.assertEqual(frame.getpixel((0,0)),(192,0,0))
        with self.assertRaises(ValueError):decode_screen(b'screenframeshort\r\nunsupported\r\nch> ')
    def test_remote_initialization_sends_only_info_and_screen_until_input(self):
        calls=[]
        class Fake:
            def __init__(self,path):pass
            def command(self,text):
                calls.append(text)
                return b'Mayhem Version: synthetic-test\r\nch> ' if text=='info' else (b' '*240+b'\r\n')*320+b'ch> '
            def close(self):calls.append('closed')
        remote=Remote('/dev/synthetic',Fake,interval=100)
        try:
            deadline=time.monotonic()+2
            while remote.frame is None and time.monotonic()<deadline:time.sleep(0.01)
            self.assertIsNotNone(remote.frame);self.assertEqual(calls,['info','screenframeshort'])
            with self.assertRaises(ValueError):remote.button(6)
            remote.button(5)
            deadline=time.monotonic()+2
            while 'button 5' not in calls and time.monotonic()<deadline:time.sleep(0.01)
            self.assertIn('button 5',calls)
        finally:remote.close();remote.thread.join(timeout=2)
        self.assertIn('closed',calls)
    def test_firmware_prepare_checks_archive_and_never_flashes(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);archive=base/'FIRMWARE_mayhem_v2.4.0.zip'
            with zipfile.ZipFile(archive,'w') as z:z.writestr(update.MEMBER,b'SYNTHETIC TEST FIRMWARE')
            data=archive.read_bytes()
            with patch.object(update,'SIZE',len(data)),patch.object(update,'SHA256',hashlib.sha256(data).hexdigest()),patch('urllib.request.urlopen') as network:
                result=update.download(base);network.assert_not_called()
            self.assertFalse(result['flashed']);self.assertFalse(result['sd_card_updated'])
            self.assertEqual((base/'firmware_hackrf.bin').read_bytes(),b'SYNTHETIC TEST FIRMWARE')
            with self.assertRaises(ValueError):update.verify(archive)

if __name__=='__main__':unittest.main()

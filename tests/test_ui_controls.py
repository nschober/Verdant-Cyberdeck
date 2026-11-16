import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch
from PIL import Image
from cyberdeck.dashboard import Dashboard
from cyberdeck.pointer import PointerMotion,key_character
from cyberdeck.pwn_screen import draw_screen
from cyberdeck.authentication import authenticate
from evdev import ecodes as E
from scripts.integrate_tft import patch_launcher
ROOT=Path(__file__).resolve().parents[1]

class UIControlTests(unittest.TestCase):
    def setUp(self):self.app=Dashboard();self.app.enter_menu();self.app.next_status=float('inf')
    def tearDown(self):self.app.shutdown()
    def test_no_exit_and_main_menu_navigation(self):
        for page in (self.app.home,self.app.pwn,self.app.system):
            with patch('cyberdeck.pwnagotchi.running',return_value=True):page()
            labels=[b.label for b in self.app.buttons]
            self.assertEqual('MAIN MENU' in labels,self.app.title!='VERDANT CYBERDECK');self.assertNotIn('EXIT',labels);self.assertNotIn('HOME',labels)
    def test_main_menu_has_no_back_button_but_subpages_do(self):
        self.app.home();self.assertNotIn('BACK',[b.label for b in self.app.buttons]);self.assertNotIn('MAIN MENU',[b.label for b in self.app.buttons])
        self.app.wifi();self.assertIn('BACK',[b.label for b in self.app.buttons]);self.assertIn('MAIN MENU',[b.label for b in self.app.buttons])
    def test_settings_and_config_open_without_password(self):
        self.app.home();next(b for b in self.app.buttons if b.label=='SYSTEM').action()
        self.assertEqual(self.app.title,'SYSTEM');self.assertIsNone(self.app.auth_target)
        with patch('cyberdeck.pwnagotchi.running',return_value=True):self.app.pwn()
        with patch('cyberdeck.pwnagotchi.configuration',return_value='Configuration information') as config:
            next(b for b in self.app.buttons if b.label=='CONFIGURATION').action()
            config.assert_called_once();self.assertEqual(self.app.title,'PWNAGOTCHI CONFIG')
            self.assertIsNone(self.app.auth_target)
    def test_back_restores_previous_screen_and_scroll(self):
        self.app.rf_menu()
        self.app.tools('RF SPECTRUM')
        self.app.text('DETAILS', '\n'.join(str(i) for i in range(40)))
        self.app.scroll(7)
        self.app.text('HELP', 'help')
        for title in ('DETAILS', 'RF SPECTRUM', 'RF TOOLS', 'VERDANT CYBERDECK'):
            next(b for b in self.app.buttons if b.label == 'BACK').action()
            self.assertEqual(self.app.title, title)
            if title == 'DETAILS':
                self.assertEqual(self.app.offset, 7)
        self.assertEqual(self.app.history, [])

    def test_refresh_does_not_add_history_and_main_menu_clears_it(self):
        self.app.wifi()
        self.app.text('ACCESS POINTS', 'first')
        self.app.text('ACCESS POINTS', 'refreshed')
        self.app.back()
        self.assertEqual(self.app.title, 'WI-FI RECON')
        self.app.rf_menu()
        next(b for b in self.app.buttons if b.label == 'MAIN MENU').action()
        self.assertEqual(self.app.history, [])
    def test_reduced_motion_keeps_subpixel_movement_and_clamps(self):
        m=PointerMotion(0,0)
        for _ in range(10):m.move('x',1)
        self.assertAlmostEqual(m.x,2.8);self.assertEqual(m.move('x',10)[0],6)
        self.assertEqual(m.move('x',99999)[0],479)
        self.assertEqual(m.move('y',-99999)[1],0)
        self.assertEqual(key_character(E.KEY_1,{E.KEY_LEFTSHIFT}),'!')
        self.assertEqual(key_character(E.KEY_A,set()),'a')
    def test_screen_frame_renders_and_stale_or_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'frame.png';Image.new('RGB',(480,320),'red').save(path)
            frame=Image.new('RGB',(480,320));self.assertTrue(draw_screen(frame,path,os.getuid()))
            self.assertEqual(frame.getpixel((60,60)),(255,0,0))
            os.utime(path,(1,1));self.assertFalse(draw_screen(frame,path,os.getuid()))
            link=Path(directory)/'link';link.symlink_to(path)
            self.assertFalse(draw_screen(frame,link,os.getuid()))
    def test_pam_checks_authentication_and_account_and_closes_transaction(self):
        from unittest.mock import MagicMock
        import ctypes
        pam=MagicMock();pam.pam_start.return_value=0
        pam.pam_authenticate.return_value=0;pam.pam_acct_mgmt.return_value=0
        real=ctypes.CDLL
        def library(name):return pam if name=='mock-pam' else real(name)
        with patch('cyberdeck.authentication.ctypes_path',side_effect=lambda n:'mock-pam' if n=='pam' else 'libc.so.6'),patch('cyberdeck.authentication.C.CDLL',side_effect=library):
            self.assertTrue(authenticate('kali','synthetic-test-value'))
            self.assertEqual(pam.pam_start.call_args.args[:2],(b'login',b'kali'))
            pam.pam_acct_mgmt.assert_called_once();pam.pam_end.assert_called_once()
            pam.pam_acct_mgmt.reset_mock();pam.pam_authenticate.return_value=7
            self.assertFalse(authenticate('kali','synthetic-test-value'))
            pam.pam_acct_mgmt.assert_not_called()
    def test_password_empty_wrong_account_fail_closed(self):
        self.assertFalse(authenticate('root','example'))
        self.assertFalse(authenticate('kali',''))
        self.assertFalse(authenticate('kali','abc\x00def'))
    def test_launcher_batches_motion_and_retains_protected_legacy_settings(self):
        source=patch_launcher((ROOT/'pwnagotchi/host-snapshot/tft/launcher.py').read_text(),True)
        self.assertIn('PointerMotion',source);self.assertIn('pointer_dirty=True',source)
        self.assertIn('1/30',source);self.assertIn('native.needs_redraw()',source);self.assertIn('else 0.25)',source)
        self.assertNotIn('native.pwn()',source)
        self.assertEqual(patch_launcher(source,True),source)

class BridgeTests(unittest.TestCase):
    def test_real_canvas_is_published_without_touching_framebuffer_or_original_source(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);package=base/'pwnagotchi/ui';package.mkdir(parents=True)
            (base/'pwnagotchi/__init__.py').write_text('')
            (package/'__init__.py').write_text('')
            display=package/'display.py'
            source='class Display:\n def _on_view_rendered(self,image):self.called=True\n'
            display.write_text(source)
            script='''from pwnagotchi.ui.display import Display
from PIL import Image
from pathlib import Path
from unittest.mock import patch
import os
base=Path(os.environ['BRIDGE_TEST_DIR'])
real=Path
os.umask(0o077)
with patch('pathlib.Path',side_effect=lambda p:base/'state' if str(p)=='/run/verdant-cyberdeck' else real(p)),patch('os.chown'),patch('os.fchown'),patch('grp.getgrnam',return_value=type('Group',(),{'gr_gid':os.getgid()})()):
 d=Display();d._on_view_rendered(Image.new('RGB',(480,320),'green'))
 assert d.called
 assert (base/'state').stat().st_mode & 0o777 == 0o750
 with Image.open(base/'state/pwn-screen.png') as frame:assert frame.getpixel((50,50))==(0,128,0)
'''
            env=dict(os.environ,VERDANT_PWN_SCREEN='1',BRIDGE_TEST_DIR=str(base),PYTHONPATH=str(ROOT/'bridge')+os.pathsep+str(base))
            result=subprocess.run(['/usr/bin/python3','-c',script],env=env,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(display.read_text(),source)

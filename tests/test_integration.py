import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from PIL import ImageFont
from cyberdeck.dashboard import Dashboard,FONT
from cyberdeck.backend import Result
from cyberdeck import pwnagotchi,wifi_recon,launchers

ROOT=Path(__file__).resolve().parents[1]

class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.app=Dashboard()
        self.app.splash_until=0
    def tearDown(self):
        self.app.shutdown()
    def test_all_menu_actions_and_bounds(self):
        for page in (self.app.home,self.app.pwn,self.app.wifi,self.app.bt,self.app.system,
                     lambda:self.app.tools('NETWORK'),lambda:self.app.tools('WIRELESS'),lambda:self.app.tools('TRAFFIC / WEB')):
            page()
            self.assertEqual(self.app.render().size,(480,320))
            for b in self.app.buttons:
                x,y,x2,y2=b.rect
                self.assertTrue(0<=x<x2<=480 and 0<=y<y2<=320,b)
                self.assertGreaterEqual(y2-y,35)
                self.assertTrue(callable(b.action))
        self.app.home()
        self.app.tap(250,100)
        self.assertEqual(self.app.title,'PWNAGOTCHI')
        self.app.tap(20,300)
        self.assertEqual(self.app.title,'VERDANT CYBERDECK')
    def test_passive_startup(self):
        with patch('cyberdeck.dashboard.run') as run, patch('cyberdeck.launchers.subprocess.Popen') as popen,patch('cyberdeck.wifi_recon.scan') as scan:
            self.app.home();self.app.pwn();self.app.wifi();self.app.bt()
            run.assert_not_called();popen.assert_not_called();scan.assert_not_called()
    def test_service_requires_confirmation(self):
        self.app.pwn()
        with patch.object(self.app,'control') as control:
            self.app.tap(20,100)
            self.assertIn('START',self.app.title)
            control.assert_not_called()
            self.app.tap(20,90)
            control.assert_called_once_with('start')
    def test_long_text_is_inside_view(self):
        self.app.text('test','W'*400)
        font=ImageFont.truetype(FONT,12)
        self.assertTrue(all(font.getlength(line)<=366 for line in self.app.lines))
        self.app.scroll(999)
        self.assertEqual(self.app.offset,len(self.app.lines)-10 if len(self.app.lines)>10 else 0)
    def test_stale_async_results_ignored(self):
        old=self.app.generation
        self.app.home()
        self.app.events.put((old,'stale'))
        self.app.next_status=float('inf')
        self.app.tick()
        self.assertNotEqual(self.app.body,'stale')

class IntegrationTests(unittest.TestCase):
    def test_wifi_escaping_sort_fields(self):
        output=r'*:My\:SSID:aa\:bb\:cc\:dd\:ee\:ff:6:2437 MHz:90:WPA2:wlan0'+'\n'+r':Other:11\:22\:33\:44\:55\:66:1:2412 MHz:12:WPA2:wlan1'
        with patch('cyberdeck.wifi_recon.run',return_value=Result(0,output)) as call:
            result=wifi_recon.scan()
            self.assertIn('My:SSID',result)
            self.assertIn('aa:bb:cc:dd:ee:ff',result)
            self.assertIn('2437 MHz',result)
            self.assertLess(result.index('My:SSID'),result.index('Other'))
            self.assertNotIn('disconnect',call.call_args.args[0])
    def test_scan_failure_is_reported(self):
        with patch('cyberdeck.wifi_recon.run',return_value=Result(10,'No adapter')):
            with self.assertRaisesRegex(RuntimeError,'No adapter'):wifi_recon.scan()
    def test_service_control_targets_existing_unit(self):
        with patch('cyberdeck.pwnagotchi.UNIT',ROOT/'tests/fixtures/pwnagotchi.service'):
            self.assertEqual(pwnagotchi.control_args('restart'),['systemctl','restart','pwnagotchi.service'])
        with self.assertRaises(ValueError):pwnagotchi.control_args('enable')
    def test_status_denied_is_unknown(self):
        with patch('cyberdeck.pwnagotchi.run',return_value=Result(1,'denied')):
            self.assertIn('unknown',pwnagotchi.state())
    def test_configuration_redacts_credentials(self):
        with patch('cyberdeck.pwnagotchi.CONFIG',ROOT/'tests/fixtures/pwnagotchi.toml'):
            text=pwnagotchi.configuration()
        self.assertIn('ili9488',text)
        self.assertNotIn('password',text)
        self.assertNotIn('changeme',text)
    def test_launcher_preserves_argument_boundaries(self):
        argv=launchers.terminal_command(['/usr/bin/printf','$(touch /tmp/no)'])
        self.assertEqual(argv[-1],'$(touch /tmp/no)')
        self.assertIn('"$@"',argv[-4])
    def test_missing_tool_error(self):
        with patch('cyberdeck.launchers.installed',return_value=None):
            with self.assertRaises(RuntimeError):launchers.launch('no-such-executable')
    def test_no_new_pwnagotchi_copy_launcher(self):
        self.assertNotIn('pwnagotchi',[exe for group in launchers.TOOLS.values() for _,exe,_ in group])
    def test_preserved_files(self):
        evidence=ROOT/'logs/preserved-sha256.json'
        if not evidence.exists():
            self.skipTest('Host-local preservation manifest is not included in a fresh clone')
        for path,digest in json.loads(evidence.read_text()).items():
            self.assertEqual(hashlib.sha256(Path(path).read_bytes()).hexdigest(),digest,path)
    def test_imports(self):
        for module in ('backend','dashboard','main','pwnagotchi','wifi_recon','bluetooth','system_status','launchers','framebuffer'):
            importlib.import_module('cyberdeck.'+module)
    def test_framebuffer_refuses_unknown_owner(self):
        from cyberdeck.framebuffer import available_framebuffer
        with patch('cyberdeck.framebuffer.command',return_value=Result(1,'denied')):
            with self.assertRaisesRegex(RuntimeError,'Refusing'):available_framebuffer()
    def test_lifecycle_restore_previous_entries(self):
        with tempfile.TemporaryDirectory() as temp:
            home=Path(temp)/'home';root=Path(temp)/'project'
            (root/'logs').mkdir(parents=True)
            entry=home/'.config/autostart/kali-cyberdeck.desktop'
            entry.parent.mkdir(parents=True)
            entry.write_text('previous entry\n')
            env=dict(os.environ,HOME=str(home),CYBERDECK_MANAGEMENT_ROOT=str(root))
            def manage(action):
                subprocess.run(['/usr/bin/python3',str(ROOT/'manage.py'),action],env=env,check=True,capture_output=True)
            manage('install');manage('disable')
            self.assertIn('Hidden=true',entry.read_text())
            manage('enable')
            self.assertNotIn('Hidden=true',entry.read_text())
            manage('uninstall')
            self.assertEqual(entry.read_text(),'previous entry\n')
            self.assertFalse((home/'.local/bin/kali-cyberdeck').exists())

if __name__=='__main__':unittest.main()

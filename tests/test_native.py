import errno
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from evdev import ecodes as E
from cyberdeck.native import NativeDeck,write_terminal_input
from cyberdeck.alerts import AlertReader

class NativeTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.terminal=[];self.actions=[]
        self.deck=NativeDeck(self.terminal.append,self.actions.append,log_path=Path(self.directory.name)/'native.log',alert_reader=AlertReader(Path(self.directory.name)/'no-alert'))
    def tearDown(self):
        self.deck.close_runtime();self.directory.cleanup()
    def test_real_six_button_menu_persists_after_splash(self):
        self.deck.splash_until=0;self.deck.home()
        labels=[b.label for b in self.deck.buttons]
        for label in ('WI-FI RECON','PWNAGOTCHI','NETWORK','WIRELESS','BLUETOOTH','TRAFFIC / WEB'):
            self.assertIn(label,labels)
        self.assertEqual(self.deck.render().size,(480,320))
        self.assertEqual(self.actions,[]);self.assertEqual(self.terminal,[])
    def test_touch_held_through_splash_does_not_launch_any_action(self):
        self.deck.touch_down(9)
        self.deck.splash_until=0
        self.deck.touch_up(9,250,100)
        self.assertEqual(self.deck.title,'VERDANT CYBERDECK')
        self.deck.touch_down(9);self.deck.touch_up(9,250,100)
        self.assertEqual(self.deck.title,'PWNAGOTCHI')
        self.assertEqual(self.actions,[])
    def test_touch_mapping_clamps_edges(self):
        self.assertEqual(self.deck.coordinate(4095,0,4095,480),479)
        self.assertEqual(self.deck.coordinate(-5,0,4095,320),0)
        self.assertEqual(self.deck.coordinate(9000,0,4095,320),319)
    def test_interactive_tool_uses_existing_terminal_callback(self):
        with patch('cyberdeck.native.installed',return_value='/usr/bin/nmap'):
            self.deck.launch('nmap',['--help'])
        self.assertEqual(self.terminal,[['/usr/bin/nmap','--help']])
        self.deck.shutdown();self.assertIsNone(self.terminal[-1])
    def test_pwn_controls_keep_runtime_and_call_only_explicit_action(self):
        self.deck.control('restart');self.assertEqual(self.actions,['restart'])
        self.assertFalse(self.deck._closed)
    def test_keyboard_navigation_and_preview_do_not_auto_start_radios(self):
        self.deck.splash_until=0
        self.deck.key(E.KEY_2,1);self.assertEqual(self.deck.title,'PWNAGOTCHI')
        self.deck.key(E.KEY_F3,1)
        self.assertGreater(self.deck.splash_until,time.monotonic())
        self.deck.key(E.KEY_1,1);self.assertEqual(self.actions,[])
    def test_splash_duration_is_four_seconds_from_first_ready_frame(self):
        clock=[100.0]
        with patch('cyberdeck.native.time.monotonic',side_effect=lambda:clock[0]):
            first=self.deck.render()
            self.assertEqual(self.deck.splash_until,104.0)
            self.assertGreaterEqual(self.deck.splash_until-clock[0],3.0)
            self.assertLessEqual(self.deck.splash_until-clock[0],5.0)
            clock[0]=103.9
            self.deck.render()
            self.assertGreater(self.deck.splash_until,clock[0])
            clock[0]=104.1
            home=self.deck.render()
            self.assertNotEqual(first.tobytes(),home.tobytes())
            self.assertEqual(self.deck.splash_until,104.0)
            clock[0]=200.0
            self.deck.preview_splash();self.deck.render()
            self.assertEqual(self.deck.splash_until,204.0)
    def test_popup_click_dismisses_without_activating_hidden_menu(self):
        from cyberdeck.alerts import EventStore,AlertReader
        path=Path(self.directory.name)/'popup.json'
        EventStore(path,os.getgid()).publish({'version':1,'kind':'test','id':'demo','timestamp':time.time(),'detail':'Synthetic'})
        self.deck.alerts=AlertReader(path,os.getuid());self.deck.splash_until=0
        self.deck.tap(250,100)
        self.assertEqual(self.deck.title,'VERDANT CYBERDECK')
        self.assertIsNone(self.deck.alerts.current());self.assertEqual(self.actions,[])
    def test_fifo_rejects_regular_file_and_symlink(self):
        base=Path(self.directory.name);real=base/'regular';real.write_bytes(b'preserve')
        with self.assertRaises(OSError):write_terminal_input(b'overwrite',real,os.getuid())
        self.assertEqual(real.read_bytes(),b'preserve')
        link=base/'link';link.symlink_to(real)
        with self.assertRaises(OSError):write_terminal_input(b'overwrite',link,os.getuid())
        self.assertEqual(real.read_bytes(),b'preserve')
    def test_valid_terminal_fifo_gets_exact_argument_bytes(self):
        path=Path(self.directory.name)/'input';os.mkfifo(path,0o600)
        reader=os.open(path,os.O_RDONLY|os.O_NONBLOCK)
        try:
            write_terminal_input(b'nmap --help\n',path,os.getuid())
            self.assertEqual(os.read(reader,100),b'nmap --help\n')
        finally:os.close(reader)

if __name__=='__main__':unittest.main()

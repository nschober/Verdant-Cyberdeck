import ast
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from PIL import Image
from cyberdeck.alerts import capture_event,EventStore,AlertReader,JournalMonitor,CARD
from scripts import integrate_tft as integration

ROOT=Path(__file__).resolve().parents[1]
EVENT={'__CURSOR':'synthetic-cursor-1','MESSAGE':'[2026-11-15 10:00:00] [WARNING] !!! captured new handshake: aa:bb:cc:dd:ee:01 -> aa:bb:cc:dd:ee:02 !!!'}

class CaptureAlertTests(unittest.TestCase):
    def test_only_actual_capture_log_marker_is_accepted(self):
        event=capture_event(EVENT,now=100)
        self.assertEqual(event['kind'],'handshake');self.assertEqual(event['timestamp'],100)
        for message in ('loaded 10 handshakes','file.pcap created','normal prefix !!! captured new handshake: fake !!!','!!! captured new handshake: fake !!! trailing content'):
            self.assertIsNone(capture_event({'MESSAGE':message,'__CURSOR':'x'}))
        self.assertIsNone(capture_event({'MESSAGE':EVENT['MESSAGE']}))
        self.assertIsNone(capture_event([]))
    def test_cursor_deduplication_and_new_events(self):
        class Store:
            events=[]
            def publish(self,event):self.events.append(event)
        store=Store();monitor=JournalMonitor(store)
        self.assertTrue(monitor.accept(EVENT));self.assertFalse(monitor.accept(EVENT))
        self.assertTrue(monitor.accept({**EVENT,'__CURSOR':'synthetic-cursor-2'}))
        self.assertEqual(len(store.events),2)
    def test_atomic_state_expiry_dismissal_and_visible_overlay(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'state/handshake.json';store=EventStore(path,os.getgid());reader=AlertReader(path,os.getuid())
            event=capture_event(EVENT);store.publish(event)
            image=Image.new('RGB',(480,320),'black')
            self.assertTrue(reader.draw(image));self.assertNotEqual(image.getpixel((30,90)),(0,0,0))
            self.assertIsNone(reader.current(now=event['timestamp']+8.01))
            reader.dismiss();self.assertIsNone(reader.current())
            self.assertEqual(json.loads(path.read_text())['id'],event['id'])
    def test_symlink_or_untrusted_state_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);real=base/'real';real.write_text(json.dumps(capture_event(EVENT)))
            link=base/'link';link.symlink_to(real)
            self.assertIsNone(AlertReader(link,os.getuid()).current())
            self.assertIsNone(AlertReader(real,os.getuid()+100).current())
    def test_synthetic_alerts_are_visually_distinct(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'alert.json';store=EventStore(path,os.getgid());reader=AlertReader(path,os.getuid())
            event={'version':1,'kind':'test','id':'synthetic','timestamp':time.time(),'detail':'No handshake captured'};store.publish(event)
            self.assertEqual(reader.current()['kind'],'test')
            im=Image.new('RGB',(480,320));self.assertTrue(reader.draw(im))

class BackgroundIntegrationTests(unittest.TestCase):
    def test_unit_patch_removes_only_terminal_conflict(self):
        original=(ROOT/'pwnagotchi/host-snapshot/systemd/pwnagotchi.service').read_text()
        updated=integration.patch_pwn_unit(original)
        self.assertNotIn('Conflicts=tft-terminal.service',updated)
        self.assertIn('Requires=pwnagotchi-bettercap.service pwngrid-peer.service',updated)
        self.assertIn('ExecStart=/root/pwnagotchi-modern/tft/launch.sh',updated)
        self.assertEqual(integration.patch_pwn_unit(updated),updated)
    def test_background_launcher_keeps_pwn_out_of_display_owners(self):
        source=integration.patch_launcher((ROOT/'pwnagotchi/host-snapshot/tft/launcher.py').read_text(),background=True)
        tree=ast.parse(source)
        loops=[n for n in ast.walk(tree) if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='candidate']
        self.assertTrue(loops)
        for loop in loops:self.assertNotIn('pwnagotchi.service',ast.literal_eval(loop.iter))
        callback=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='pwn_action')
        self.assertFalse(any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='choose' for n in ast.walk(callback)))
        self.assertIn("other != 'pwnagotchi.service'",source)
    def test_terminal_composites_alert_last_without_changing_pty_start(self):
        original=(ROOT/'pwnagotchi/host-snapshot/tft/terminal.py').read_text();updated=integration.patch_terminal(original)
        self.assertLess(updated.index('verdant_alerts.draw(image)'),updated.index('fb.write(image.tobytes'))
        def popen(source):
            return ast.dump(next(n for n in ast.walk(ast.parse(source)) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='Popen'))
        self.assertEqual(popen(original),popen(updated))
        self.assertEqual(integration.patch_terminal(updated),updated)
    def test_background_plan_preserves_main_config_and_rolls_back(self):
        from contextlib import ExitStack
        with tempfile.TemporaryDirectory() as directory,ExitStack() as stack:
            base=Path(directory);names=('LAUNCHER','ARTWORK','MODE','AUTO_FLAG','RUNTIME','PWN_UNIT','PWN_CONFIG','PWN_DEFAULTS','TERMINAL','MONITOR_UNIT','BRIDGE_UNIT','BRIDGE_RUNTIME')
            paths={key:base/key for key in names};paths['PWN_DROPIN']=base/'conf.d/zzzz-verdant-background.toml';paths['PWN_DROPIN'].parent.mkdir()
            for key,value in paths.items():stack.enter_context(patch.object(integration,key,value))
            stack.enter_context(patch.object(integration,'launch_desktop_alerts',return_value='mocked desktop'))
            paths['LAUNCHER'].write_bytes((ROOT/'pwnagotchi/host-snapshot/tft/launcher.py').read_bytes())
            paths['TERMINAL'].write_bytes((ROOT/'pwnagotchi/host-snapshot/tft/terminal.py').read_bytes())
            original_unit=(ROOT/'pwnagotchi/host-snapshot/systemd/pwnagotchi.service').read_bytes();paths['PWN_UNIT'].write_bytes(original_unit)
            config=f'main.confd = {json.dumps(str(paths["PWN_DROPIN"].parent))}\n'
            paths['PWN_CONFIG'].write_text(config);paths['PWN_DEFAULTS'].write_text(config);paths['MODE'].write_text('auto\n')
            image=ROOT/'assets/splash.png';calls=[]
            def control(*args):
                calls.append(args)
                if '--property=User' in args:return 'kali'
                if args[-1]=='tft-terminal.service':return 'inactive'
                return 'active'
            plan=integration.make_plan(launcher=paths['LAUNCHER'],artwork=paths['ARTWORK'],mode=paths['MODE'],auto_flag=paths['AUTO_FLAG'],runtime_root=paths['RUNTIME'],image_source=image,background_pwn=True)
            report=integration.install(plan,backup_root=base/'backups',control=control)
            self.assertEqual(paths['PWN_CONFIG'].read_text(),config)
            self.assertFalse(report['pwn_boot_enablement_changed'])
            self.assertIn(('restart','pwnagotchi.service'),calls)
            self.assertNotIn(('start','pwnagotchi.service'),calls)
            self.assertIn(('enable',integration.MONITOR_SERVICE),calls)
            self.assertNotIn('Requires=pwnagotchi',paths['MONITOR_UNIT'].read_text())
            manifest=next((base/'backups').glob('*/manifest.json'));integration.restore(manifest,control=control)
            self.assertEqual(paths['PWN_UNIT'].read_bytes(),original_unit)
            self.assertFalse(paths['PWN_DROPIN'].exists())

class DesktopPopupTests(unittest.TestCase):
    def test_desktop_requests_topmost_and_closes_expired_popup(self):
        import types
        from cyberdeck.alerts import desktop_notifications
        calls=[];widgets=[]
        class Widget:
            def __init__(self,kind):self.kind=kind;self.callbacks=[];self.destroyed=False;widgets.append(self)
            def withdraw(self):pass
            def overrideredirect(self,value):calls.append(('override',value))
            def attributes(self,*args):calls.append(('attributes',*args))
            def winfo_screenwidth(self):return 480
            def winfo_screenheight(self):return 320
            def geometry(self,value):calls.append(('geometry',value))
            def configure(self,**kwargs):pass
            def pack(self,**kwargs):pass
            def lift(self):calls.append(('lift',))
            def destroy(self):self.destroyed=True
            def after(self,delay,fn):self.callbacks.append(fn)
            def mainloop(self):self.callbacks.pop(0)()
        fake=types.SimpleNamespace(Tk=lambda:Widget('root'),Toplevel=lambda parent:Widget('popup'),Label=lambda *a,**kw:Widget('label'),Button=lambda *a,**kw:Widget('button'))
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{'DISPLAY':':synthetic','XDG_RUNTIME_DIR':directory}),patch.dict('sys.modules',{'tkinter':fake}),patch('cyberdeck.alerts.AlertReader') as reader:
            reader.return_value.current.side_effect=[{'id':'synthetic','kind':'test','detail':'No capture'},None]
            desktop_notifications()
        self.assertIn(('attributes','-topmost',True),calls)
        self.assertIn(('geometry','440x190+20+65'),calls)
        self.assertIn(('lift',),calls)
        self.assertTrue(next(w for w in widgets if w.kind=='popup').destroyed)

if __name__=='__main__':unittest.main()

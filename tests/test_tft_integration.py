import ast
import os
from contextlib import ExitStack
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
from cyberdeck.splash import render_splash
from scripts import integrate_tft as integration

ROOT=Path(__file__).resolve().parents[1]
ORIGINAL=ROOT/'pwnagotchi/host-snapshot/tft/launcher.py'

class TFTIntegrationTests(unittest.TestCase):
    def test_splash_dimensions_progress_and_no_shared_image_mutation(self):
        start=render_splash(0);end=render_splash(1)
        self.assertEqual(start.size,(480,320));self.assertEqual(start.mode,'RGB')
        self.assertNotEqual(start.tobytes(),end.tobytes())
        self.assertEqual(render_splash(0).tobytes(),start.tobytes())
    def test_native_launcher_patch_preserves_existing_service_selection(self):
        source=ORIGINAL.read_text();updated=integration.patch_launcher(source)
        before=next(n for n in ast.walk(ast.parse(source)) if isinstance(n,ast.FunctionDef) and n.name=='choose')
        after=next(n for n in ast.walk(ast.parse(updated)) if isinstance(n,ast.FunctionDef) and n.name=='choose')
        self.assertEqual(ast.dump(before),ast.dump(after))
        self.assertIn('splash_held',updated)
        self.assertIn('native = NativeDeck',updated)
        self.assertIn("'ili9488' in line.lower()",updated)
        self.assertNotIn("/dev/fb0",updated)
        self.assertEqual(integration.patch_launcher(updated),updated)
    def test_unknown_native_launcher_is_not_overwritten(self):
        with self.assertRaises(ValueError):integration.patch_launcher('print("different software")\n')
    def fixture(self, base):
        paths={name:base/name for name in ('LAUNCHER','ARTWORK','MODE','AUTO_FLAG','RUNTIME','PWN_DROPIN','PWN_UNIT','PWN_CONFIG','PWN_DEFAULTS','TERMINAL','MONITOR_UNIT')}
        paths['LAUNCHER'].write_bytes(ORIGINAL.read_bytes());paths['LAUNCHER'].chmod(0o755)
        paths['MODE'].write_text('manual\n')
        image=base/'source.png';render_splash().save(image)
        return paths,image
    def test_inactive_pwn_stays_inactive_and_verified_rollback_restores_files(self):
        with tempfile.TemporaryDirectory() as directory,ExitStack() as stack:
            base=Path(directory);paths,image=self.fixture(base)
            for key,value in paths.items():stack.enter_context(patch.object(integration,key,value))
            calls=[]
            def control(*args):
                calls.append(args)
                if '--property=User' in args:return 'kali'
                return 'inactive' if args[-1]=='pwnagotchi.service' else 'active'
            plans=integration.make_plan(launcher=paths['LAUNCHER'],artwork=paths['ARTWORK'],mode=paths['MODE'],auto_flag=paths['AUTO_FLAG'],image_source=image,requested_mode='auto')
            report=integration.install(plans,backup_root=base/'backups',control=control)
            self.assertTrue(report['applied'])
            self.assertEqual(paths['MODE'].read_text(),'auto\n')
            self.assertEqual(stat.S_IMODE(paths['LAUNCHER'].stat().st_mode),0o755)
            self.assertFalse(any(c[0] in ('start','restart') and c[-1]=='pwnagotchi.service' for c in calls))
            manifest=next((base/'backups').glob('*/manifest.json'))
            integration.restore(manifest,control=control)
            self.assertEqual(paths['LAUNCHER'].read_bytes(),ORIGINAL.read_bytes())
            self.assertEqual(paths['MODE'].read_text(),'manual\n')
            self.assertFalse(paths['ARTWORK'].exists())
    def test_auto_request_restarts_only_an_already_running_pwn(self):
        with tempfile.TemporaryDirectory() as directory,ExitStack() as stack:
            base=Path(directory);paths,image=self.fixture(base)
            for key,value in paths.items():stack.enter_context(patch.object(integration,key,value))
            calls=[]
            def control(*args):
                calls.append(args)
                return 'kali' if '--property=User' in args else 'active'
            plans=integration.make_plan(launcher=paths['LAUNCHER'],artwork=paths['ARTWORK'],mode=paths['MODE'],auto_flag=paths['AUTO_FLAG'],image_source=image,requested_mode='auto')
            integration.install(plans,backup_root=base/'backup',control=control)
            self.assertIn(('restart','pwnagotchi.service'),calls)
            self.assertNotIn(('start','pwnagotchi.service'),calls)
    def test_bad_mode_is_rejected_without_writing_it(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);paths,image=self.fixture(base)
            paths['MODE'].write_text('unexpected\n')
            with self.assertRaises(ValueError):
                integration.make_plan(launcher=paths['LAUNCHER'],artwork=paths['ARTWORK'],mode=paths['MODE'],auto_flag=paths['AUTO_FLAG'],image_source=image,requested_mode='auto')
            self.assertEqual(paths['MODE'].read_text(),'unexpected\n')
    def test_atomic_writer_refuses_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);real=base/'real';real.write_text('preserve')
            link=base/'link';link.symlink_to(real)
            with self.assertRaises(ValueError):integration.atomic_write(link,b'replace')
            self.assertEqual(real.read_text(),'preserve')

class NativeSupervisorTests(unittest.TestCase):
    def test_patched_supervisor_paints_actual_dashboard_and_queues_real_newline(self):
        import contextlib
        import io
        import types
        import sys
        from cyberdeck.native import NativeDeck as RealDeck
        class StopLoop(Exception):pass
        class Memory:
            frames=[]
            def __setitem__(self,key,value):self.frames.append(value)
            def close(self):pass
        memory=Memory();decks=[];clock=[100.0];external_active=[False];select_calls=[0]
        source=integration.patch_launcher(ORIGINAL.read_text())
        with tempfile.TemporaryDirectory() as directory,ExitStack() as stack:
            base=Path(directory)
            original_read=Path.read_text
            def read(path,*args,**kwargs):
                if str(path)=='/proc/fb':return '0 ili9488drmfb\n'
                if str(path)=='/sys/class/graphics/fb0/stride':return '1920\n'
                return original_read(path,*args,**kwargs)
            def factory(*args):
                from cyberdeck.alerts import AlertReader
                deck=RealDeck(*args,log_path=base/'native.log',alert_reader=AlertReader(base/'no-alert'));deck.splash_until=0
                deck.tick=lambda:None;decks.append(deck);return deck
            real_open=os.open;real_close=os.close
            stack.enter_context(patch.object(Path,'read_text',read))
            stack.enter_context(patch.dict(sys.modules,{'tft_view':types.SimpleNamespace(POINTER=base/'pointer.json',draw_pointer=lambda *args:None)}))
            stack.enter_context(patch.object(sys,'path',list(sys.path)))
            stack.enter_context(patch('cyberdeck.native.NativeDeck',side_effect=factory))
            stack.enter_context(patch('cyberdeck.native.installed',return_value='/usr/bin/nmap'))
            stack.enter_context(patch('evdev.list_devices',return_value=[]))
            stack.enter_context(patch('atexit.register'))
            stack.enter_context(patch('os.open',side_effect=lambda path,*a,**kw:99999 if str(path)=='/dev/fb0' else real_open(path,*a,**kw)))
            stack.enter_context(patch('os.close',side_effect=lambda fd:None if fd==99999 else real_close(fd)))
            stack.enter_context(patch('fcntl.ioctl',return_value=0))
            stack.enter_context(patch('mmap.mmap',return_value=memory))
            def select_events(*args):
                select_calls[0]+=1
                if select_calls[0]>1:raise StopLoop()
                external_active[0]=True;clock[0]=102.0
                return [],[],[]
            def host_command(args,**kwargs):
                state='active' if external_active[0] and args[-1]=='pwnagotchi.service' else 'inactive'
                return types.SimpleNamespace(returncode=0,stdout=state+'\n',stderr='')
            stack.enter_context(patch('time.monotonic',side_effect=lambda:clock[0]))
            stack.enter_context(patch('select.select',side_effect=select_events))
            stack.enter_context(patch('subprocess.run',side_effect=host_command))
            namespace={'__name__':'native_supervisor_test'}
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    exec(compile(source,'native-supervisor','exec'),namespace)
                    with self.assertRaises(StopLoop):namespace['main']()
                    deck=decks[0]
                    self.assertGreaterEqual(len(memory.frames),1)
                    self.assertEqual(len(memory.frames[-1]),480*320*4)
                    self.assertEqual(memory.frames[-1],deck.render().tobytes('raw','BGRX'))
                    supervisor_state=dict(zip(deck._terminal.__code__.co_freevars,[c.cell_contents for c in deck._terminal.__closure__]))
                    self.assertEqual(supervisor_state['mode'],'pwnagotchi.service')
                    deck.launch('nmap',['--help'])
                    pending=dict(zip(deck._terminal.__code__.co_freevars,[c.cell_contents for c in deck._terminal.__closure__]))['pending_command']
                    self.assertTrue(pending.endswith(b'\n'))
                    self.assertFalse(pending.endswith(b'\\n'))
            finally:
                for deck in decks:deck.close_runtime()

if __name__=='__main__':unittest.main()

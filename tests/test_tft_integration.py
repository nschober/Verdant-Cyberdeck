import ast
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
        self.assertIn('draw(splash=True)',updated)
        self.assertIn("'ili9488' in line.lower()",updated)
        self.assertNotIn("/dev/fb0",updated)
        self.assertEqual(integration.patch_launcher(updated),updated)
    def test_unknown_native_launcher_is_not_overwritten(self):
        with self.assertRaises(ValueError):integration.patch_launcher('print("different software")\n')
    def fixture(self, base):
        paths={name:base/name for name in ('LAUNCHER','ARTWORK','MODE','AUTO_FLAG')}
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
            def control(*args):calls.append(args);return 'active'
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

if __name__=='__main__':unittest.main()

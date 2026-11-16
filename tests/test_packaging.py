import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import tomllib
from scripts.materialize_pwnagotchi import overlay,COMMIT
from scripts.install_pwnagotchi_fresh import install,configuration
from scripts.setup_package import plan
import argparse
ROOT=Path(__file__).resolve().parents[1]

class PackagingTests(unittest.TestCase):
    def test_fresh_install_refuses_existing_before_any_mutation(self):
        with patch('scripts.install_pwnagotchi_fresh.existing',return_value=True),patch('subprocess.run') as command:
            with self.assertRaisesRegex(ValueError,'Existing Pwnagotchi'):install('wlan1')
            command.assert_not_called()
    def test_overlay_preserves_upstream_entry_assets_and_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);source=base/'snapshot';target=base/'upstream'
            (source/'pwnagotchi').mkdir(parents=True);(source/'tft').mkdir()
            (source/'pwnagotchi/modified.py').write_text('VALUE=1\n')
            (source/'pwnagotchi/defaults.toml').write_text('password="[REDACTED]"\n')
            for name in ('requirements-modern.txt','test_backend.py','smoke-ai.py','launch.sh','radio-start.sh','radio-stop.sh'):(source/'tft'/name).write_text('# synthetic test\n')
            (target/'bin').mkdir(parents=True);(target/'pwnagotchi/ui/web/static').mkdir(parents=True)
            (target/'bin/pwnagotchi').write_text('upstream entry')
            (target/'pwnagotchi/defaults.toml').write_text('upstream defaults')
            (target/'pwnagotchi/ui/web/static/logo.svg').write_text('upstream asset')
            applied=overlay(source,target)
            self.assertTrue(applied);self.assertEqual((target/'bin/pwnagotchi').read_text(),'upstream entry')
            self.assertEqual((target/'pwnagotchi/defaults.toml').read_text(),'upstream defaults')
            self.assertTrue((target/'pwnagotchi/ui/web/static/logo.svg').exists())
    def test_fresh_config_is_complete_private_and_separate_from_redacted_snapshot(self):
        text=configuration('wlan1','SYNTHETIC_TEST_SECRET')
        data=tomllib.loads(text)
        self.assertNotIn('[REDACTED]',text)
        self.assertEqual(data['main']['iface'],'wlan1')
        self.assertFalse(data['ui']['display']['enabled'])
        self.assertEqual(data['ui']['web']['address'],'127.0.0.1')
        self.assertEqual(data['bettercap']['password'],data['ui']['web']['password'])
        self.assertEqual(COMMIT,'6cdc89226478fd42d7bcca6a9faa05d9f3280701')
    def test_installer_plan_is_read_only_and_preserves_existing(self):
        args=argparse.Namespace(fresh_pwn=False,complete=False,desktop=False)
        with patch('scripts.setup_package.existing',return_value=True):data=plan(args)
        self.assertTrue(data['check_only']);self.assertEqual(data['pwnagotchi_action'],'preserve and integrate existing')
    def test_python_package_entrypoint_and_runtime_dependencies(self):
        data=tomllib.loads((ROOT/'pyproject.toml').read_text())
        self.assertEqual(data['project']['scripts']['verdant-cyberdeck'],'cyberdeck.main:main')
        self.assertIn('Pillow>=9.1',data['project']['dependencies'])
        lock=(ROOT/'pwnagotchi/installer/requirements-pi400.txt').read_text()
        self.assertIn('torch==2.5.1',lock);self.assertIn('torchvision==0.20.1',lock)
        self.assertNotIn('cuda-toolkit',lock)

if __name__=='__main__':unittest.main()

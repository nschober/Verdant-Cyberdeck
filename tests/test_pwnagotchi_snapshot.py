from pathlib import Path
import tempfile
import tomllib
import unittest
from scripts.snapshot_pwnagotchi import collect,redact_configuration

class SnapshotTests(unittest.TestCase):
    def test_configuration_redacts_unknown_strings_and_nested_secrets(self):
        original='''main.iface = "wlan1"
main.name = "private-host"
main.whitelist = ["private-ssid", "aa:bb:cc:dd:ee:ff"]
ui.web.password = "secret-test-password"
main.plugins.example.api_key = "secret-test-key"
main.plugins.example.enabled = true
main.plugins.example.port = 1234
main.plugins.example.unknown = "unrecognized-private-value"
'''
        result=redact_configuration(original)
        for secret in ('private-host','private-ssid','aa:bb:cc:dd:ee:ff','secret-test-password','secret-test-key','unrecognized-private-value'):
            self.assertNotIn(secret,result)
        data=tomllib.loads(result)
        self.assertEqual(data['main']['iface'],'wlan1')
        self.assertTrue(data['main']['plugins']['example']['enabled'])
        self.assertEqual(data['main']['plugins']['example']['port'],1234)
    def test_export_preserves_source_and_excludes_runtime_material(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);source=base/'installed';source.mkdir()
            code=source/'plugin.py';content=b'# synthetic test code\nVALUE = 1\n';code.write_bytes(content)
            (source/'id_rsa').write_text('synthetic-key-never-export')
            (source/'capture.pcap').write_bytes(b'synthetic-capture')
            (source/'data').mkdir();(source/'data/learned.py').write_text('do not export runtime data')
            (source/'.venv').mkdir();(source/'.venv/library.py').write_text('do not export virtualenv')
            (source/'LICENSE').write_text('Synthetic fixture license text')
            (source/'bettercap.cap').write_text('set wifi.interface wlan-test\n')
            report=collect(base/'review',{'source':source},{})
            self.assertEqual(code.read_bytes(),content)
            self.assertEqual((base/'review/source/plugin.py').read_bytes(),content)
            paths={record['path'] for record in report['files']}
            self.assertEqual(paths,{'source/plugin.py','source/LICENSE','source/bettercap.cap.txt'})
    def test_missing_source_is_explicit_and_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory)
            report=collect(base/'review',{'source':base/'not-installed'}, {})
            self.assertEqual(len(report['unavailable']),1)
            with self.assertRaises(ValueError):collect(base/'review',{}, {})
    def test_symlinks_are_not_followed(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);source=base/'source';source.mkdir()
            private=base/'private.py';private.write_text('private content')
            (source/'linked.py').symlink_to(private)
            report=collect(base/'review',{'source':source},{})
            self.assertFalse(report['files'])
            self.assertTrue(report['excluded'])

if __name__=='__main__':unittest.main()

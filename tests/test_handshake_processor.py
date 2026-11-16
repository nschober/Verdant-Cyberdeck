import csv
import datetime as dt
import io
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import time
import types
import unittest
from cyberdeck.handshake_processor import Processor,parse_record,spreadsheet_cell,COLUMNS
from scripts.install_handshake_processor import unit,quote

RECORD='WPA*01*'+'a'*32+'*001122334455*66778899aabb*54657374204e6574***'
OTHER=RECORD.replace('a'*32,'b'*32)

class ProcessorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name)
        self.source=self.base/'captures';self.source.mkdir();self.output=self.base/'output';self.calls=[]
        def convert(argv,**kwargs):
            self.calls.append(argv)
            Path(argv[2]).write_text(RECORD+'\n'+RECORD+'\n')
            return types.SimpleNamespace(returncode=0)
        self.processor=Processor(self.source,self.output,converter='/usr/bin/hcxpcapngtool',runner=convert,settle=0)
    def tearDown(self):self.processor.close();self.temp.cleanup()
    def capture(self,name='first.pcap',stamp=None):
        path=self.source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'SYNTHETIC TEST CAPTURE')
        stamp=stamp or time.time()-60;os.utime(path,(stamp,stamp));return path
    def process(self):self.processor.scan();self.processor.scan()
    def ledger(self):
        with (self.output/'handshakes.csv').open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
    def test_daily_file_aggregation_deduplication_and_full_inventory(self):
        first=self.capture();self.capture('second.pcap');self.process()
        date=dt.datetime.fromtimestamp(first.stat().st_mtime).astimezone().date().isoformat()
        self.assertEqual((self.output/(date+'.22000')).read_text(),RECORD+'\n')
        rows=self.ledger();self.assertEqual(len(rows),2)
        self.assertEqual(set(rows[0]),set(COLUMNS))
        self.assertEqual(rows[0]['ssid'],'Test Net');self.assertEqual(rows[0]['access_point_mac'],'00:11:22:33:44:55')
        self.assertEqual(rows[0]['client_mac'],'66:77:88:99:aa:bb');self.assertEqual(rows[0]['handshake_type'],'PMKID')
        self.assertEqual(first.read_bytes(),b'SYNTHETIC TEST CAPTURE')
        self.assertEqual(len(list(self.output.glob('*.22000'))),1)
        self.processor.scan();self.assertEqual(len(self.calls),2)
    def test_different_days_create_distinct_files(self):
        now=time.time()-60;self.capture('today.pcap',now);self.capture('older.pcap',now-86400*2)
        self.process();self.assertEqual(len(list(self.output.glob('*.22000'))),2)
    def test_restart_recovers_without_duplicate_conversion(self):
        self.capture();self.process();self.processor.close()
        self.processor=Processor(self.source,self.output,converter='/usr/bin/hcxpcapngtool',runner=lambda *a,**kw:self.fail('Unexpected conversion'),settle=0)
        (self.output/'handshakes.csv').unlink();self.processor.scan()
        self.assertEqual(len(self.ledger()),1)
    def test_wait_for_stable_file_and_reprocess_changed_file_without_losing_history(self):
        path=self.capture();self.processor.scan();self.assertEqual(self.calls,[])
        path.write_bytes(b'CHANGED TEST CAPTURE');self.processor.scan();self.assertEqual(self.calls,[])
        self.processor.scan();self.assertEqual(len(self.calls),1)
        path.write_bytes(b'ANOTHER TEST CAPTURE');self.process()
        self.assertEqual(len(self.ledger()),2)
    def test_nested_captures_and_symlink_rejection(self):
        self.capture('nested/one.cap');outside=self.base/'outside.pcap';outside.write_bytes(b'test')
        (self.source/'link.pcap').symlink_to(outside);(self.source/'linked-directory').symlink_to(self.base)
        self.process();self.assertEqual(len(self.calls),1)
        self.assertEqual(self.ledger()[0]['source_capture'],'nested/one.cap')
    def test_failure_is_recorded_and_no_usable_hash_is_distinct(self):
        self.capture()
        self.processor.runner=lambda *a,**kw:types.SimpleNamespace(returncode=1)
        self.process();self.assertEqual(self.ledger()[0]['status'],'error');self.assertFalse(list(self.output.glob('*.22000')))
        self.capture('empty.pcap');self.processor.runner=lambda *a,**kw:types.SimpleNamespace(returncode=0)
        self.process();self.assertIn('no_usable_hash',[r['status'] for r in self.ledger()])
    def test_spreadsheet_formula_injection_is_neutralized(self):
        for value in ('=cmd()', '+1+1','-5','@test','  =value','\tvalue'):
            self.assertTrue(spreadsheet_cell(value).startswith("'"))
        self.assertEqual(spreadsheet_cell('safe'),'safe')
    def test_eapol_and_pmkid_record_validation(self):
        _,fields=parse_record(RECORD);self.assertEqual(fields['handshake_type'],'PMKID')
        eapol='WPA*02*'+'a'*32+'*001122334455*66778899aabb*54657374*'+'b'*64+'*01020304*00'
        self.assertEqual(parse_record(eapol)[1]['message_pair_hex'],'00')
        for invalid in ('garbage',RECORD+'bad',RECORD.replace('001122334455','0011')):
            with self.assertRaises(ValueError):parse_record(invalid)
    def test_single_instance_lock(self):
        with self.assertRaisesRegex(RuntimeError,'Another processor'):Processor(self.source,self.output,converter='/usr/bin/hcxpcapngtool')
    def test_service_has_no_wireless_or_cracking_dependency(self):
        data=unit(Path('/var/lib/pwnagotchi/handshakes')).decode()
        self.assertIn('PrivateNetwork=yes',data);self.assertNotIn('Requires=pwnagotchi',data)
        self.assertNotIn('ExecStart=/usr/bin/hashcat',data);self.assertIn('--watch --input',data)
        self.assertEqual(quote('/path/100%'), '"/path/100%%"')
    @unittest.skipUnless(shutil.which('hcxpcapngtool'),'hcxtools not installed on this test host')
    def test_installed_converter_handles_synthetic_empty_pcap_without_false_hash(self):
        self.capture().write_bytes(struct.pack('<IHHIIII',0xa1b2c3d4,2,4,0,0,65535,105))
        self.processor.runner=subprocess.run;self.process()
        self.assertEqual(self.ledger()[0]['status'],'no_usable_hash')
        self.assertFalse(list(self.output.glob('*.22000')))

if __name__=='__main__':unittest.main()

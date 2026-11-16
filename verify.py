"""Repeatable verification; radio scans are opt-in and never start Pwnagotchi."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from cyberdeck.backend import run
from cyberdeck.paths import log_directory

ROOT=Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--hardware',action='store_true',help='Explicitly test Wi-Fi scan and Bluetooth discovery')
    args=parser.parse_args()
    results={}
    def record(name,argv,timeout=40):
        outcome=run(argv,timeout)
        results[name]={'passed':outcome.code==0,'exit':outcome.code,'output':outcome.output}
    record('syntax',['/usr/bin/python3','-m','compileall','-q','cyberdeck','manage.py','verify.py'])
    for script in ROOT.glob('*.sh'):
        record('shell '+script.name,['bash','-n',str(script)])
    record('unit tests',['/usr/bin/python3','-m','unittest','discover','-s','tests','-v'])
    record('offscreen startup',[str(ROOT/'run.sh'),'--self-test'])
    record('packages',['bash','install-tools.sh','--check'])
    record('autostart',['bash','autostart.sh','status'])
    record('live service status',['systemctl','status','--no-pager','pwnagotchi.service'])
    record('wireless detection',['iw','dev'])
    record('Bluetooth detection',['bluetoothctl','list'])
    if args.hardware:
        record('Wi-Fi scan',['nmcli','-f','IN-USE,SSID,BSSID,CHAN,FREQ,SIGNAL,SECURITY,DEVICE','device','wifi','list','--rescan','yes'])
        record('Bluetooth discovery',['bluetoothctl','--timeout','8','scan','on'])
    else:
        results['active discovery']={'passed':None,'output':'Not run: requires --hardware; startup remains passive.'}
    if os.environ.get('DISPLAY'):
        record('graphical startup',[str(ROOT/'run.sh'),'--smoke-test'])
    else:
        results['graphical startup']={'passed':None,'output':'Unavailable: no accessible graphical session. Xvfb also cannot bind a socket in this sandbox.'}
    results['physical TFT and touch']={'passed':None,'output':'Unverified. Device nodes unavailable in the execution sandbox; existing TFT owners preserved.'}
    results['Pwnagotchi independence']={'passed':None,'output':'Service launch has no dashboard dependency; runtime health cannot be confirmed without host system bus access. Service was not started/stopped for tests.'}
    evidence=ROOT/'logs/preserved-sha256.json'
    if evidence.exists():
        preserved=json.loads(evidence.read_text())
        results['preservation']={'passed':all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in preserved.items()),'output':'SHA-256 of existing Pwnagotchi configuration and service units.'}
    else:
        results['preservation']={'passed':None,'output':'No host-local preservation manifest in this checkout; no preservation claim can be made.'}
    destination=log_directory();destination.mkdir(parents=True,exist_ok=True)
    (destination/'test-results.json').write_text(json.dumps(results,indent=2))
    for name,result in results.items():
        state='PASS' if result['passed'] is True else 'UNAVAILABLE/FAIL' if result['passed'] is False else 'UNVERIFIED'
        print(f'{state}: {name}')
    # Keep unavailable host checks visible in the process result.
    return 1 if any(r['passed'] is False for r in results.values()) else 0

if __name__=='__main__':
    os.chdir(ROOT)
    sys.exit(main())

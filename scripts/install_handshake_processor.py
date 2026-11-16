#!/usr/bin/env python3
"""Install only Verdant's offline capture converter and daily CSV ledger service."""
import argparse
import datetime
import grp
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tomllib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.integrate_tft import atomic_write,systemctl

ROOT=Path(__file__).resolve().parents[1]
RUNTIME=Path('/usr/local/lib/verdant-cyberdeck')
MODULE=RUNTIME/'cyberdeck/handshake_processor.py'
UNIT=Path('/etc/systemd/system/verdant-handshake-processor.service')
OUTPUT=Path('/var/lib/verdant-cyberdeck/hashcat')
SERVICE=UNIT.name
BACKUPS=Path('/var/backups/verdant-cyberdeck')

def merge(base,new):
    for key,value in new.items():
        if isinstance(value,dict) and isinstance(base.get(key),dict):merge(base[key],value)
        else:base[key]=value
    return base

def capture_directory():
    config={}
    for path in (Path('/etc/pwnagotchi/default.toml'),Path('/etc/pwnagotchi/config.toml')):
        if path.exists():merge(config,tomllib.loads(path.read_text()))
    confd=config.get('main',{}).get('confd')
    if confd:
        for path in sorted(Path(confd).glob('*.toml')):merge(config,tomllib.loads(path.read_text()))
    source=Path(config['bettercap']['handshakes'])
    if not source.is_absolute():raise ValueError('Capture directory must be absolute')
    return source

def quote(value):
    value=str(value)
    if '\n' in value or '\r' in value:raise ValueError('Invalid unit argument')
    return '"'+value.replace('\\','\\\\').replace('"','\\"').replace('%','%%')+'"'

def unit(source):
    return ('[Unit]\nDescription=Verdant offline handshake conversion and daily spreadsheet\nAfter=local-fs.target\n\n'
            '[Service]\nType=simple\nUser=root\nGroup=kali\nEnvironment=PYTHONPATH='+str(RUNTIME)+'\n'
            'ExecStart=/usr/bin/python3 -m cyberdeck.handshake_processor --watch --input '+quote(source)+' --output '+quote(OUTPUT)+'\n'
            'Restart=on-failure\nRestartSec=10\nTimeoutStopSec=150\nUMask=0027\nNoNewPrivileges=yes\n'
            'PrivateTmp=yes\nPrivateNetwork=yes\nProtectSystem=strict\nProtectHome=read-only\n'
            'ReadOnlyPaths='+quote(source)+'\nReadWritePaths='+quote(OUTPUT)+'\n'
            '\n[Install]\nWantedBy=multi-user.target\n').encode()

def apply(source):
    if os.geteuid()!=0:raise PermissionError('Apply requires host sudo')
    if not source.is_dir():raise ValueError('Configured capture directory is unavailable')
    if not shutil.which('hcxpcapngtool'):raise RuntimeError('hcxpcapngtool is missing; hcxtools is required')
    for path in (RUNTIME,RUNTIME/'cyberdeck',OUTPUT.parent,OUTPUT):
        if path.is_symlink():raise ValueError('Refusing symlink destination '+str(path))
        if path.exists() and (path.stat().st_uid!=0 or path.stat().st_mode&0o022):raise ValueError('Destination must be root-owned and not group/world writable: '+str(path))
    plans=[(MODULE,(ROOT/'cyberdeck/handshake_processor.py').read_bytes()),(UNIT,unit(source))]
    compile(plans[0][1],str(MODULE),'exec')
    enabled=systemctl('show','--property=UnitFileState','--value',SERVICE) if UNIT.exists() else 'absent'
    active=systemctl('show','--property=ActiveState','--value',SERVICE) if UNIT.exists() else 'inactive'
    backup=BACKUPS/('processor-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'));backup.mkdir(parents=True,mode=0o700)
    report={'applied':False,'service':SERVICE,'enabled_before':enabled,'active_before':active,'files':[],'source':str(source),'output':str(OUTPUT)}
    manifest=backup/'manifest.json'
    for i,(path,data) in enumerate(plans):
        if path.is_symlink():raise ValueError('Refusing symlink '+str(path))
        record={'path':str(path),'existed':path.exists(),'after_sha256':hashlib.sha256(data).hexdigest()}
        if path.exists():
            info=path.stat();original=path.read_bytes();saved=backup/str(i);saved.write_bytes(original);saved.chmod(0o600)
            record.update(backup=str(saved),before_sha256=hashlib.sha256(original).hexdigest(),mode=stat.S_IMODE(info.st_mode),uid=info.st_uid,gid=info.st_gid)
        report['files'].append(record)
    manifest.write_text(json.dumps(report,indent=2)+'\n');manifest.chmod(0o600)
    print('Backup and rollback manifest: '+str(manifest),flush=True)
    try:
        for path in (RUNTIME,RUNTIME/'cyberdeck'):path.mkdir(parents=True,exist_ok=True,mode=0o755)
        OUTPUT.mkdir(parents=True,exist_ok=True,mode=0o750);os.chown(OUTPUT,0,grp.getgrnam('kali').gr_gid);OUTPUT.chmod(0o750)
        for (path,data),record in zip(plans,report['files']):atomic_write(path,data,record if record['existed'] else None)
        systemctl('daemon-reload');systemctl('enable',SERVICE);systemctl('restart',SERVICE)
        report.update(applied=True,service_state=systemctl('show','--property=ActiveState','--value',SERVICE),pwnagotchi_changed=False)
    finally:manifest.write_text(json.dumps(report,indent=2)+'\n')
    return report

def restore(manifest):
    if os.geteuid()!=0:raise PermissionError('Restore requires host sudo')
    report=json.loads(Path(manifest).read_text())
    for record in report['files']:
        path=Path(record['path'])
        if path not in (MODULE,UNIT) or path.is_symlink():raise ValueError('Unexpected rollback destination')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=record['after_sha256']:raise ValueError('Installed file changed since apply')
        if record['existed'] and hashlib.sha256(Path(record['backup']).read_bytes()).hexdigest()!=record['before_sha256']:raise ValueError('Backup checksum mismatch')
    systemctl('stop',SERVICE)
    if report['enabled_before']!='enabled':systemctl('disable',SERVICE)
    for record in report['files']:
        path=Path(record['path'])
        if record['existed']:atomic_write(path,Path(record['backup']).read_bytes(),record)
        else:path.unlink()
    systemctl('daemon-reload')
    if report['active_before']=='active':systemctl('start',SERVICE)
    print('Processor files restored. Daily hash files, CSV and capture originals preserved.')

def main():
    parser=argparse.ArgumentParser(description=__doc__);group=parser.add_mutually_exclusive_group()
    group.add_argument('--apply',action='store_true');group.add_argument('--restore',type=Path)
    args=parser.parse_args()
    try:
        if args.restore:restore(args.restore);return
        source=capture_directory()
        if args.apply:print(json.dumps(apply(source),indent=2))
        else:print(json.dumps({'read_only_plan':True,'capture_source':str(source),'daily_hashes':str(OUTPUT/'YYYY-MM-DD.22000'),'spreadsheet':str(OUTPUT/'handshakes.csv'),'converter':shutil.which('hcxpcapngtool'),'network_operations':False,'automatic_cracking':False},indent=2))
    except (OSError,ValueError,KeyError,RuntimeError,subprocess.SubprocessError) as exc:parser.exit(1,'Processor integration failed: '+str(exc)+'\n')

if __name__=='__main__':main()

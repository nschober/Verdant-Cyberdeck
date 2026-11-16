#!/usr/bin/env python3
"""Reconstruct complete pinned Pwnagotchi source plus reviewed TFT/Pi modifications."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1]
UPSTREAM='https://github.com/jayofelony/pwnagotchi.git'
COMMIT='6cdc89226478fd42d7bcca6a9faa05d9f3280701'

def overlay(source,destination):
    source=Path(source);destination=Path(destination)
    applied=[]
    # Never deploy redacted TOML, host snapshots, an image-level installer or a virtualenv.
    for file in sorted((source/'pwnagotchi').rglob('*.py')):
        if file.is_symlink():raise ValueError('Unexpected source symlink')
        relative=file.relative_to(source);target=destination/relative
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,target)
        applied.append({'path':str(relative),'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
    for name in ('requirements-modern.txt','test_backend.py','smoke-ai.py','launch.sh','radio-start.sh','radio-stop.sh'):
        file=source/'tft'/name
        if file.is_symlink():raise ValueError('Unexpected TFT source symlink')
        target=destination/'tft'/name;target.parent.mkdir(exist_ok=True);shutil.copy2(file,target)
        if file.suffix=='.sh':target.chmod(0o755)
        applied.append({'path':'tft/'+name,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
    return applied

def materialize(destination):
    destination=Path(destination)
    if destination.exists() or destination.is_symlink():raise ValueError('Destination already exists; existing installations are never overwritten')
    subprocess.run(['git','clone','--no-checkout',UPSTREAM,str(destination)],check=True)
    subprocess.run(['git','-C',str(destination),'checkout','--detach',COMMIT],check=True)
    actual=subprocess.check_output(['git','-C',str(destination),'rev-parse','HEAD'],text=True).strip()
    if actual!=COMMIT:raise ValueError('Pinned source commit mismatch')
    applied=overlay(ROOT/'pwnagotchi/installed-source',destination)
    for relative in ('bin/pwnagotchi','pwnagotchi/defaults.toml','LICENSE.md','pwnagotchi/ui/web/static'):
        if not (destination/relative).exists():raise ValueError('Upstream runtime asset missing: '+relative)
    record={'upstream':UPSTREAM,'commit':COMMIT,'overlay':applied,'configuration_installed':False}
    (destination/'VERDANT-SOURCE.json').write_text(json.dumps(record,indent=2)+'\n')
    return record

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--destination',type=Path,required=True)
    args=parser.parse_args();record=materialize(args.destination)
    print(json.dumps({'destination':str(args.destination),'upstream_commit':record['commit'],'overlay_files':len(record['overlay']),'installed_or_started':False},indent=2))

if __name__=='__main__':main()

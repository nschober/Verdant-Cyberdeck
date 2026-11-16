#!/usr/bin/env python3
"""Prepare the verified official Mayhem firmware archive; never flash implicitly."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request
import zipfile

VERSION='v2.4.0'
URL='https://github.com/portapack-mayhem/mayhem-firmware/releases/download/v2.4.0/FIRMWARE_mayhem_v2.4.0.zip'
SHA256='62cb7f579423ae64414c70548361dd239a4afc7adbd288ae41fbbbfa14be96bd'
SIZE=8434462
MEMBER='firmware/firmware_hackrf.bin'

def verify(path):
    if path.is_symlink():raise ValueError('Refusing symlink archive')
    if path.stat().st_size!=SIZE or hashlib.sha256(path.read_bytes()).hexdigest()!=SHA256:raise ValueError('Official archive size/checksum mismatch')

def download(folder):
    folder=Path(folder)
    if folder.is_symlink():raise ValueError('Refusing symlink destination')
    folder.mkdir(parents=True,exist_ok=True)
    archive=folder/'FIRMWARE_mayhem_v2.4.0.zip'
    if not archive.exists():
        temporary=folder/'.firmware-download'
        if temporary.exists() or temporary.is_symlink():raise ValueError('Existing partial download preserved; inspect it before retrying')
        try:
            with urllib.request.urlopen(URL,timeout=30) as response,temporary.open('xb') as stream:
                total=0
                while True:
                    chunk=response.read(1024*1024)
                    if not chunk:break
                    total+=len(chunk)
                    if total>SIZE:raise ValueError('Archive exceeds published size')
                    stream.write(chunk)
            verify(temporary);temporary.replace(archive)
        finally:
            if temporary.exists():temporary.unlink()
    verify(archive)
    target=folder/'firmware_hackrf.bin'
    with zipfile.ZipFile(archive) as bundle:
        info=bundle.getinfo(MEMBER)
        if info.file_size>4*1024*1024:raise ValueError('Unexpected firmware size')
        data=bundle.read(MEMBER)
    if target.is_symlink():raise ValueError('Refusing symlink firmware output')
    if target.exists() and target.read_bytes()!=data:raise ValueError('Existing different firmware preserved')
    if not target.exists():target.write_bytes(data)
    manifest={'version':VERSION,'archive':URL,'archive_sha256':SHA256,'target':'HackRF One + PortaPack','firmware_sha256':hashlib.sha256(data).hexdigest(),'flashed':False,'sd_card_updated':False}
    (folder/'verified-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--download',action='store_true');parser.add_argument('--output',type=Path,default=Path.home()/'Downloads/mayhem-v2.4.0')
    args=parser.parse_args()
    if args.download:print(json.dumps(download(args.output),indent=2))
    else:print(json.dumps({'version':VERSION,'official_release':'https://github.com/portapack-mayhem/mayhem-firmware/releases/tag/v2.4.0','firmware_archive':URL,'sha256':SHA256,'download_bytes':SIZE,'reported_current_version':'v1.3.0','usb_products':[p.read_text().strip() for p in Path('/sys/bus/usb/devices').glob('*/product') if any(tag in p.read_text().lower() for tag in ('hackrf','portapack','mayhem'))],'flash_performed':False,'required_next_steps':['Connect HackRF One/PortaPack USB data cable','Verify board with hackrf_info in HackRF mode','Back up flash and SD card before writes','Update matching SD apps from official HackRF One SD payload','Flash verified HackRF One image and verify reboot version']},indent=2))

if __name__=='__main__':main()

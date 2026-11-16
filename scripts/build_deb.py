#!/usr/bin/env python3
"""Build the complete repository as a Debian package, without installing it."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile
ROOT=Path(__file__).resolve().parents[1]
VERSION='0.5.0'

def build(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    if (ROOT/'.git').exists():files=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    else:
        excluded={'.git','.github','logs','backups','dist','build','__pycache__'}
        files=[str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file() and not (set(p.relative_to(ROOT).parts)&excluded)]
    with tempfile.TemporaryDirectory(prefix='verdant-deb-') as directory:
        base=Path(directory);app=base/'opt/verdant-cyberdeck';app.mkdir(parents=True)
        for name in filter(None,files):
            if name.startswith(('.git/','.github/','logs/','backups/')) or name.endswith(('.pyc','.pcap','.pcapng','.cap','.22000','.csv','.pem','.key')):continue
            source=ROOT/name
            if source.is_symlink():raise ValueError('Unexpected source symlink: '+name)
            target=app/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        control=base/'DEBIAN';control.mkdir()
        (control/'control').write_text('Package: verdant-cyberdeck\nVersion: '+VERSION+'\nSection: utils\nPriority: optional\nArchitecture: all\nMaintainer: Verdant Cyberdeck contributors <37641650+nschober@users.noreply.github.com>\nDepends: python3 (>= 3.11), python3-pil, python3-pil.imagetk, python3-tk, python3-evdev, python3-pyte, fonts-dejavu-core, xterm\nRecommends: hcxtools, rtl-sdr, hackrf, gqrx-sdr, gnuradio, inspectrum, bluez, iw\nDescription: Touchscreen cyberdeck, tool launchers and native TFT integrations\n Includes source, templates and explicit setup workflows for RF, Pwnagotchi,\n offline daily capture conversion and Mayhem remote display.\n Firmware flashing and wireless activation never run from package hooks.\n')
        binary=base/'usr/bin';binary.mkdir(parents=True)
        for name,target in [('verdant-cyberdeck','run.sh'),('verdant-setup','install.sh')]:
            path=binary/name;path.write_text('#!/bin/sh\nexec /opt/verdant-cyberdeck/'+target+' "$@"\n');path.chmod(0o755)
        desktop=base/'usr/share/applications';desktop.mkdir(parents=True)
        (desktop/'verdant-cyberdeck.desktop').write_text('[Desktop Entry]\nType=Application\nName=Verdant Cyberdeck\nExec=verdant-cyberdeck\nTerminal=false\nCategories=System;Utility;\n')
        licenses=base/'usr/share/doc/verdant-cyberdeck';licenses.mkdir(parents=True)
        (licenses/'copyright').write_text('Verdant application: MIT (see /opt/verdant-cyberdeck/LICENSE).\nIncluded Pwnagotchi snapshot: GPL-3.0 and nested LGPL notices; see /opt/verdant-cyberdeck/NOTICE.md and pwnagotchi/installed-source/LICENSE.md.\n')
        result=output/f'verdant-cyberdeck_{VERSION}_all.deb'
        subprocess.run(['dpkg-deb','--root-owner-group','--build',str(base),str(result)],check=True)
        return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=ROOT/'dist');args=parser.parse_args();print(build(args.output))

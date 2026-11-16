#!/usr/bin/env python3
"""Create the native supervisor on fresh hosts, without starting it or changing drivers."""
import argparse
import os
from pathlib import Path
import shutil
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.integrate_tft import atomic_write,systemctl
ROOT=Path(__file__).resolve().parents[1]

def bootstrap():
    if os.geteuid()!=0:raise PermissionError('Native bootstrap requires host sudo')
    if Path('/opt/tft-terminal/launcher.py').exists():
        print('Existing native supervisor preserved; integration will inspect it separately.');return
    if Path('/opt/tft-terminal').exists() or Path('/etc/systemd/system/tft-launcher.service').exists():raise ValueError('Unrecognized existing native files; preserving them')
    if 'ili9488' not in Path('/proc/fb').read_text().lower():raise ValueError('Working ILI9488 framebuffer required; drivers are never installed by this package')
    destination=Path('/opt/tft-terminal');destination.mkdir(mode=0o755)
    for name in ('launcher.py','terminal.py','tft_view.py'):
        data=(ROOT/'pwnagotchi/host-snapshot/tft'/name).read_bytes();compile(data,name,'exec');atomic_write(destination/name,data)
    launcher='[Unit]\nDescription=Verdant native TFT supervisor\nAfter=multi-user.target\n\n[Service]\nType=simple\nExecStart=/usr/bin/python3 /opt/tft-terminal/launcher.py\nRestart=on-failure\nRestartSec=3\n\n[Install]\nWantedBy=multi-user.target\n'
    terminal='[Unit]\nDescription=Verdant existing-user TFT terminal\n\n[Service]\nType=simple\nUser=kali\nGroup=kali\nSupplementaryGroups=video\nExecStart=/usr/bin/python3 /opt/tft-terminal/terminal.py\nRestart=no\n'
    atomic_write('/etc/systemd/system/tft-launcher.service',launcher.encode());atomic_write('/etc/systemd/system/tft-terminal.service',terminal.encode())
    systemctl('daemon-reload');print('Native files installed, services remain stopped and disabled.')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    if args.apply:bootstrap()
    else:print('Read-only: would create missing native files only; existing supervisor is preserved.')

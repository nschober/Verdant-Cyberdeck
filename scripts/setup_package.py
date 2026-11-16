#!/usr/bin/env python3
"""Single entry point for source and Debian-package installation."""
import argparse
import json
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
def existing():
    return any(p.exists() or p.is_symlink() for p in (Path('/root/pwnagotchi-modern'),Path('/etc/pwnagotchi'),Path('/etc/systemd/system/pwnagotchi.service'),Path('/usr/local/bin/pwnagotchi'),Path('/etc/systemd/system/pwnagotchi-bettercap.service'),Path('/etc/systemd/system/pwngrid-peer.service'),Path('/var/lib/pwnagotchi'))) or shutil.which('pwnagotchi') is not None


def plan(args):
    return {'project':str(ROOT),'os':Path('/etc/os-release').read_text().splitlines()[:3],
            'architecture':os.uname().machine,'existing_pwnagotchi':existing(),
            'pwnagotchi_action':'fresh install explicitly requested' if args.fresh_pwn else 'preserve and integrate existing' if existing() else 'not installed; supply --fresh-pwn --interface for a fresh host',
            'native_supervisor_exists':Path('/opt/tft-terminal/launcher.py').exists(),
            'ili9488_present':'ili9488' in Path('/proc/fb').read_text().lower() if Path('/proc/fb').exists() else False,
            'rf':'repository tools plus isolated URH/gr-gsm source builds' if args.complete else 'optional; --complete enables the full profile',
            'firmware_flash':'separate verified device-specific workflow; never automatic',
            'wireless_activation':'none during install; existing running Pwnagotchi may reload its requested display bridge',
            'check_only':not args.complete and not args.desktop}


def install(args):
    data=plan(args)
    if os.uname().machine!='aarch64' or 'ID=kali' not in Path('/etc/os-release').read_text():raise RuntimeError('Full installation targets Kali ARM64')
    if args.fresh_pwn and existing():raise RuntimeError('Existing Pwnagotchi detected; --fresh-pwn is refused before installation changes')
    if args.fresh_pwn and not args.interface:raise RuntimeError('--fresh-pwn requires an explicitly selected dedicated --interface')
    username=os.environ.get('SUDO_USER','kali') if os.geteuid()==0 else pwd.getpwuid(os.getuid()).pw_name
    if username=='root':raise RuntimeError('Run from the normal desktop account using sudo, not an unidentified root login')
    if args.complete and username!='kali':raise RuntimeError('The native full profile targets the default kali account; use --desktop for another account')
    user=pwd.getpwnam(username)
    def root(argv):subprocess.run(argv if os.geteuid()==0 else ['sudo',*argv],cwd=ROOT,check=True)
    def normal(argv):subprocess.run(['runuser','-u',username,'--',*argv] if os.geteuid()==0 else argv,cwd=ROOT,check=True)
    report={'profile':'complete' if args.complete else 'desktop','steps':[],'pwnagotchi_preserved':not args.fresh_pwn}
    def step(name,action):
        print('\nINSTALL STEP: '+name,flush=True);action();report['steps'].append(name)
    try:
        step('Refresh repository package metadata',lambda:root(['apt-get','update']))
        step('Repository dependency installation',lambda:root(['bash',str(ROOT/'install-tools.sh'),'--install']))
        step('User launchers and autostart entries',lambda:normal(['/usr/bin/python3',str(ROOT/'manage.py'),'install']))
        step('Offscreen application validation',lambda:normal([str(ROOT/'run.sh'),'--self-test']))
        if args.complete:
            if args.fresh_pwn:
                step('Fresh native prerequisites (services stopped)',lambda:root(['/usr/bin/python3',str(ROOT/'scripts/bootstrap_native.py'),'--apply']))
                step('Fresh isolated Pwnagotchi runtime',lambda:root(['/usr/bin/python3',str(ROOT/'scripts/install_pwnagotchi_fresh.py'),'--apply','--interface',args.interface]))
            if Path('/opt/tft-terminal/launcher.py').exists() and existing():
                step('Native TFT battery/UI integration',lambda:root(['/usr/bin/python3',str(ROOT/'scripts/integrate_tft.py'),'--apply','--background-pwn','--restart-terminal']))
                if args.fresh_pwn:step('Native menu boot enablement',lambda:root(['systemctl','enable','tft-launcher.service']))
                step('Daily handshake converter and spreadsheet service',lambda:root(['/usr/bin/python3',str(ROOT/'scripts/install_handshake_processor.py'),'--apply']))
            else:report['native_deferred']='Existing compatible native supervisor and Pwnagotchi required; use --fresh-pwn --interface on a fresh ILI9488 host'
            step('RF packages and isolated missing-tool builds',lambda:root(['bash',str(ROOT/'install-rf-tools.sh'),'--complete']))
        report['installed']=True
    finally:
        destination=Path(user.pw_dir)/'.local/state/verdant-cyberdeck';destination.mkdir(parents=True,exist_ok=True)
        path=destination/'installation-report.json';path.write_text(json.dumps(report,indent=2)+'\n')
        if os.geteuid()==0:os.chown(destination,user.pw_uid,user.pw_gid);os.chown(path,user.pw_uid,user.pw_gid)
        print(json.dumps(report,indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group();group.add_argument('--check',action='store_true');group.add_argument('--desktop',action='store_true');group.add_argument('--complete',action='store_true')
    parser.add_argument('--fresh-pwn',action='store_true');parser.add_argument('--interface');args=parser.parse_args()
    if args.complete or args.desktop:install(args)
    else:print(json.dumps(plan(args),indent=2))

if __name__=='__main__':main()

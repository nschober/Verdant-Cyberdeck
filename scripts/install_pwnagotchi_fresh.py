#!/usr/bin/env python3
"""Explicit fresh-host Pwnagotchi installation; refuses all existing installations."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess
import sys
import urllib.request
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.materialize_pwnagotchi import materialize,COMMIT
ROOT=Path(__file__).resolve().parents[1]
DEST=Path('/root/pwnagotchi-modern');CONFIG=Path('/etc/pwnagotchi')
GRID_URL='https://github.com/jayofelony/pwngrid/releases/download/v1.11.6/pwngrid-1.11.6-aarch64.zip'
GRID_SHA='6795afedc3e7ea49c04b5e9f12b778db165db00a29d93606b77dd1f8124dff17'


def existing():
    return any(path.exists() or path.is_symlink() for path in (DEST,CONFIG,Path('/etc/systemd/system/pwnagotchi.service'),Path('/usr/local/bin/pwnagotchi'),Path('/etc/systemd/system/pwnagotchi-bettercap.service'),Path('/etc/systemd/system/pwngrid-peer.service'),Path('/var/lib/pwnagotchi'),Path('/root/.pwnagotchi-auto'),Path('/root/.pwnagotchi-manual'))) or shutil.which('pwnagotchi') is not None


def configuration(interface,password):
    quote=json.dumps
    return ('main.name = '+quote(socket.gethostname())+'\nmain.iface = '+quote(interface)+'\n'
      'main.confd = "/etc/pwnagotchi/conf.d/"\nmain.mon_start_cmd = ""\nmain.mon_stop_cmd = ""\n'
      'main.plugins.auto-update.enabled = false\nmain.plugins.fix_services.enabled = false\nmain.plugins.led.enabled = false\n'
      'main.plugins.grid.enabled = true\nmain.plugins.grid.report = false\n'
      'ai.path = "/var/lib/pwnagotchi/brain.json"\nai.params.device = "cpu"\nfs.memory.enabled = false\n'
      'bettercap.hostname = "127.0.0.1"\nbettercap.port = 8081\nbettercap.username = "verdant"\nbettercap.password = '+quote(password)+'\n'
      'bettercap.handshakes = "/var/lib/pwnagotchi/handshakes"\nui.display.enabled = false\nui.display.type = "ili9488"\nui.display.rotation = 0\nui.fps = 1.0\n'
      'ui.web.enabled = true\nui.web.address = "127.0.0.1"\nui.web.port = 8080\nui.web.username = "verdant"\nui.web.password = '+quote(password)+'\n')


def install(interface):
    from scripts.integrate_tft import atomic_write,systemctl
    if existing():raise ValueError('Existing Pwnagotchi detected. Fresh installer refuses to modify, remove, upgrade or reinstall it.')
    if os.geteuid()!=0:raise PermissionError('Fresh installation requires host sudo')
    if os.uname().machine!='aarch64':raise ValueError('This runtime targets Kali ARM64 / Cortex-A72')
    if not re.fullmatch(r'[a-zA-Z0-9_.:-]{1,15}',interface):raise ValueError('Invalid dedicated interface name')
    if not (Path('/sys/class/net')/interface/'wireless').exists():raise ValueError('Explicit wireless interface not detected')
    if not Path('/opt/tft-terminal/tft_view.py').exists():raise ValueError('Run native bootstrap first; no driver changes are needed')
    subprocess.run(['apt-get','install','--no-remove','--no-install-recommends','-y','git','python3-venv','build-essential','pkg-config','swig','libdbus-1-dev','libglib2.0-dev','libcap-dev','libffi-dev','libssl-dev','fonts-dejavu-core','bettercap','iw','network-manager'],check=True)
    materialize(DEST)
    subprocess.run(['/usr/bin/python3','-m','venv',str(DEST/'.bootstrap')],check=True)
    pip=DEST/'.bootstrap/bin/python'
    subprocess.run([str(pip),'-m','pip','install','uv'],check=True)
    uv=DEST/'.bootstrap/bin/uv'
    subprocess.run([str(uv),'python','install','3.11'],check=True)
    subprocess.run([str(uv),'venv','--python','3.11',str(DEST/'.venv')],check=True)
    subprocess.run([str(uv),'pip','install','--python',str(DEST/'.venv/bin/python'),'--only-binary','torch','--only-binary','torchvision','-r',str(ROOT/'pwnagotchi/installer/requirements-pi400.txt')],check=True)
    env=dict(os.environ,PYTHONPATH=str(DEST))
    for argv in ([str(DEST/'.venv/bin/python'),'tft/test_backend.py'],[str(DEST/'.venv/bin/python'),'tft/smoke-ai.py'],[str(DEST/'.venv/bin/python'),'bin/pwnagotchi','--help']):subprocess.run(argv,cwd=DEST,env=env,check=True)
    password=secrets.token_hex(24)
    CONFIG.mkdir(mode=0o700);(CONFIG/'conf.d').mkdir(mode=0o700)
    atomic_write(CONFIG/'config.toml',configuration(interface,password).encode(),{'mode':0o600,'uid':0,'gid':0})
    shutil.copy2(DEST/'pwnagotchi/defaults.toml',CONFIG/'default.toml')
    atomic_write(CONFIG/'mode',b'manual\n')
    for directory in ('/var/lib/pwnagotchi/handshakes','/var/lib/pwnagotchi/peers','/var/tmp/pwnagotchi/sessions','/etc/pwnagotchi/log'):Path(directory).mkdir(parents=True,exist_ok=True,mode=0o700)
    # Existing service templates retain the complete runtime dependencies, but are never started here.
    for name in ('pwnagotchi.service','pwnagotchi-bettercap.service','pwngrid-peer.service'):
        target=Path('/etc/systemd/system')/name
        if target.exists():raise ValueError('Existing service preserved: '+str(target))
        data=(ROOT/'pwnagotchi/host-snapshot/systemd'/name).read_text().replace('wlan1',interface).replace('/usr/local/bin/pwngrid','/root/pwnagotchi-modern/tft/pwngrid')
        if name=='pwnagotchi.service':data=data.replace('[Service]','[Service]\nEnvironment=PATH=/root/pwnagotchi-modern/tft:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',1)
        data='\n'.join(line for line in data.splitlines() if not line.startswith('Conflicts='))+'\n'
        atomic_write(target,data.encode())
    for name in ('radio-start.sh','radio-stop.sh'):
        path=DEST/'tft'/name;data=path.read_text().replace('wlan1',interface)
        if name=='radio-start.sh':
            guard='if LC_ALL=C nmcli -g GENERAL.STATE device show '+interface+' | grep -q \'^100\'; then echo \'Refusing to disconnect an active connection\' >&2; exit 1; fi\n'
            data=data.replace('set -euo pipefail\n','set -euo pipefail\n'+guard,1)
        path.write_text(data);path.chmod(0o755)
    caplet=('set api.rest.address 127.0.0.1\nset api.rest.port 8081\nset api.rest.username verdant\nset api.rest.password '+password+'\nset wifi.handshakes.file /var/lib/pwnagotchi/handshakes\napi.rest on\n')
    atomic_write(DEST/'tft/bettercap.cap',caplet.encode(),{'mode':0o600,'uid':0,'gid':0})
    cache=Path('/var/cache/verdant-cyberdeck');cache.mkdir(parents=True,exist_ok=True)
    archive=cache/'pwngrid-1.11.6-aarch64.zip'
    if not archive.exists():
        with urllib.request.urlopen(GRID_URL,timeout=60) as response:atomic_write(archive,response.read(10000000))
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=GRID_SHA:raise ValueError('Pwngrid archive digest mismatch')
    with zipfile.ZipFile(archive) as bundle:
        names=[n for n in bundle.namelist() if Path(n).name=='pwngrid' and not n.endswith('/')]
        if len(names)!=1:raise ValueError('Ambiguous peer binary')
        atomic_write(DEST/'tft/pwngrid',bundle.read(names[0]),{'mode':0o755,'uid':0,'gid':0})
    wrapper='#!/usr/bin/env bash\nset -euo pipefail\ncd /root/pwnagotchi-modern\nexport PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"\nexport PATH="$PWD/tft:$PATH"\nexec .venv/bin/python bin/pwnagotchi "$@"\n'
    atomic_write('/usr/local/bin/pwnagotchi',wrapper.encode(),{'mode':0o755,'uid':0,'gid':0})
    systemctl('daemon-reload')
    record={'upstream_commit':COMMIT,'fresh_install':True,'interface':interface,'mode':'manual','services_started':False,'services_enabled':False,'configuration':str(CONFIG/'config.toml'),'peer_archive_sha256':GRID_SHA}
    atomic_write(DEST/'VERDANT-INSTALL.json',(json.dumps(record,indent=2)+'\n').encode())
    print(json.dumps(record,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply',action='store_true');parser.add_argument('--interface');args=parser.parse_args()
    if args.apply:
        if not args.interface:parser.error('--interface is required for a fresh installation')
        install(args.interface)
    else:print(json.dumps({'existing_installation':existing(),'pinned_source':COMMIT,'would_overwrite_existing':False,'default_services_started':False,'requires_explicit_interface':True},indent=2))

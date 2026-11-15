"""Own only project launcher/desktop entries, with backups and exact-content removal."""
from pathlib import Path
import datetime
import json
import os
import shlex
import shutil
import subprocess
import sys
ROOT=Path(os.environ.get('CYBERDECK_MANAGEMENT_ROOT',Path(__file__).resolve().parent))
HOME=Path.home()
MANIFEST=ROOT/'logs/installed-files.json'
MARKER='# Managed by kali-cyberdeck-35'

def desktop():
    # Desktop Exec quoting is distinct from shell quoting.
    exe=str(HOME/'.local/bin/kali-cyberdeck').replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$')
    return f'[Desktop Entry]\n{MARKER}\nType=Application\nName=VERDANT CYBERDECK\nExec="{exe}"\nTerminal=false\nCategories=System;Utility;\n'

def install_alerts():
    write_owned(HOME/'.local/bin/verdant-alerts',f'#!/usr/bin/env bash\n{MARKER}\nexec {shlex.quote(str(ROOT/"run.sh"))} --alerts-only\n',True)
    exe=str(HOME/'.local/bin/verdant-alerts').replace('\\','\\\\').replace('"','\\"')
    content=f'[Desktop Entry]\n{MARKER}\nType=Application\nName=Verdant Handshake Alerts\nExec="{exe}"\nTerminal=false\n'
    write_owned(HOME/'.config/autostart/verdant-alerts.desktop',content)

def write_owned(path,content,executable=False):
    manifest=json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    key=str(path)
    if path.exists() and path.read_text()!=content:
        backup=ROOT/'backups'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        backup.mkdir(parents=True)
        dest=backup/path.name
        shutil.copy2(path,dest)
        if key not in manifest:
            manifest[key]={'backup':str(dest)}
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(content)
    path.chmod(0o755 if executable else 0o644)
    manifest.setdefault(key,{})['content']=content
    MANIFEST.write_text(json.dumps(manifest,indent=2))

def remove_owned(path):
    manifest=json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    info=manifest.get(str(path))
    if not info:
        return
    if path.exists() and path.read_text()!=info['content']:
        raise RuntimeError(f'{path} changed since installation; preserving it')
    if path.exists():
        path.unlink()
    if info.get('backup'):
        shutil.copy2(info['backup'],path)
    manifest.pop(str(path))
    MANIFEST.write_text(json.dumps(manifest,indent=2))

if __name__=='__main__':
    command=sys.argv[1]
    autostart=HOME/'.config/autostart/kali-cyberdeck.desktop'
    if command=='install':
        write_owned(HOME/'.local/bin/kali-cyberdeck',f'#!/usr/bin/env bash\n{MARKER}\nexec {shlex.quote(str(ROOT/"run.sh"))} "$@"\n',True)
        write_owned(HOME/'.local/bin/verdant-cyberdeck',f'#!/usr/bin/env bash\n{MARKER}\nexec {shlex.quote(str(ROOT/"run.sh"))} "$@"\n',True)
        write_owned(HOME/'.local/share/applications/kali-cyberdeck.desktop',desktop())
        # Adopt the previous project's entry, backing it up first.
        write_owned(autostart,desktop())
        install_alerts()
    elif command=='install-alerts':
        install_alerts()
    elif command=='enable':
        write_owned(autostart,desktop())
    elif command=='disable':
        if autostart.exists() and MARKER in autostart.read_text():
            write_owned(autostart,desktop()+'Hidden=true\n')
        else:
            raise RuntimeError('No managed autostart entry; refusing to change another entry')
    elif command=='status':
        print('enabled' if autostart.exists() and MARKER in autostart.read_text() and 'Hidden=true' not in autostart.read_text() else 'disabled / not managed')
    elif command=='uninstall':
        for path in list(json.loads(MANIFEST.read_text())) if MANIFEST.exists() else []:
            remove_owned(Path(path))
        print('Project launcher entries removed; previous entries restored. Source, logs and backups retained.')
    else:
        raise SystemExit('Unsupported command')

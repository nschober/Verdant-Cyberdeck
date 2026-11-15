#!/usr/bin/env python3
"""Export existing Pwnagotchi files for review; never install or change the source.

Protected source requires running this from a host terminal with normal sudo
access. Output is a local review bundle, not an automatic GitHub upload.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
REDACTED = '[REDACTED]'
SAFE_STRING_KEYS = {'main.iface', 'main.mode', 'main.lang', 'ui.display.type', 'ui.display.device'}
SECRET_KEYS = re.compile(r'password|passwd|secret|token|api.?key|private.?key|username|email|fingerprint|whitelist|blacklist|ssid|bssid|(^|\.)mac($|\.)', re.I)
SOURCE_ROOTS = {'source': Path('/root/pwnagotchi-modern'), 'custom-plugins': Path('/usr/local/share/pwnagotchi/custom-plugins')}
EXCLUDED_DIRS = {'.git', '.venv', 'venv', '.bootstrap', '.idea', 'site-packages', '__pycache__', 'node_modules', '.cache', 'logs', 'log', 'handshakes', 'captures', 'data', 'peers', 'sessions', 'models'}
SOURCE_SUFFIXES = {'.py', '.sh', '.md', '.rst', '.txt', '.toml', '.yml', '.yaml', '.service', '.go', '.mod', '.sum', '.html', '.css', '.js', '.svg', '.po', '.pot', '.mo', '.png', '.bmp', '.gif', '.ttf', '.hcl', '.example', '.ps1', '.stork', '.map'}
SPECIAL_NAMES = {'LICENSE', 'LICENCE', 'COPYING', 'NOTICE', 'AUTHORS', 'Makefile', 'MANIFEST.in', '.gitignore', 'package.json', 'package-lock.json', 'CODEOWNERS', 'Dockerfile', 'pwngrid-source.json'}
HOST_FILES = {
    'bin/pwnagotchi': Path('/usr/local/bin/pwnagotchi'),
    **{f'systemd/{name}.service': Path('/etc/systemd/system') / f'{name}.service' for name in ('pwnagotchi', 'pwnagotchi-bettercap', 'pwngrid-peer', 'tft-launcher', 'tft-terminal', 'tft-recon', 'tft-console')},
    **{f'tft/{name}': Path('/opt/tft-terminal') / name for name in ('launcher.py', 'terminal.py', 'tft_view.py')},
    'configuration/config.redacted.toml': Path('/etc/pwnagotchi/config.toml'),
    'configuration/default.redacted.toml': Path('/etc/pwnagotchi/default.toml'),
    'configuration/mode.txt': Path('/etc/pwnagotchi/mode'),
}

def redact_configuration(text):
    data = tomllib.loads(text)
    rows = ['# Review-only snapshot. All unapproved strings and sensitive fields are redacted.',
            '# Not a deployment or restoration configuration; do not install over a working setup.']
    def sanitize(value, path):
        key = '.'.join(path)
        if SECRET_KEYS.search(key):
            return REDACTED
        if isinstance(value, str):
            return value if key in SAFE_STRING_KEYS else REDACTED
        if isinstance(value, list):
            return [sanitize(item, path) if not isinstance(item, dict) else REDACTED for item in value]
        if isinstance(value, (bool, int, float)):
            return value
        return REDACTED
    def emit(obj, path=()):
        for key, value in obj.items():
            current = (*path, key)
            if isinstance(value, dict):
                emit(value, current)
            else:
                label = '.'.join(json.dumps(part) for part in current)
                rows.append(label + ' = ' + json.dumps(sanitize(value, current), ensure_ascii=False))
    emit(data)
    result = '\n'.join(rows) + '\n'
    tomllib.loads(result)
    return result

def collect(output, source_roots=None, host_files=None):
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError('Output must be a new directory; existing exports are never overwritten')
    output.mkdir(parents=True, mode=0o700)
    report = {'purpose': 'Read-only inspection snapshot, not an installer or complete restoration backup',
              'files': [], 'unavailable': [], 'excluded': [],
              'source_review': 'Exported application/plugin code needs manual credential and license review before publication.'}
    def save(relative, source, redact=False):
        if source.is_symlink():
            report['excluded'].append({'source': str(source), 'reason': 'symlink not followed'})
            return
        try:
            if not stat.S_ISREG(source.stat().st_mode):
                raise ValueError('not a regular file')
            content = source.read_bytes()
            if redact:
                content = redact_configuration(content.decode('utf-8')).encode('utf-8')
            destination = output / relative
            destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            destination.write_bytes(content)
            destination.chmod(0o600)
            report['files'].append({'path': str(relative), 'source': str(source), 'redacted': redact,
                                    'sha256': hashlib.sha256(content).hexdigest()})
        except (OSError, ValueError) as exc:
            report['unavailable'].append({'source': str(source), 'reason': str(exc)})
    for relative, source in (HOST_FILES if host_files is None else host_files).items():
        save(Path('host-snapshot') / relative, source, source.suffix == '.toml')
    for label, source in (SOURCE_ROOTS if source_roots is None else source_roots).items():
        try:
            if source.is_symlink():
                raise ValueError('Source root is a symlink; explicit review required')
            # iterdir raises on a protected root instead of silently claiming it is empty.
            list(source.iterdir())
            def failed(error):
                report['unavailable'].append({'source': str(error.filename), 'reason': str(error)})
            for current, directories, names in os.walk(source, followlinks=False, onerror=failed):
                here = Path(current)
                directories[:] = [name for name in directories if name not in EXCLUDED_DIRS and not (here / name).is_symlink()]
                for name in names:
                    item = here / name
                    caplet = name == 'bettercap.cap'
                    if caplet:
                        try:
                            text = item.read_text(encoding='utf-8')
                            if '\x00' in text:
                                raise ValueError('binary caplet candidate')
                        except (OSError, UnicodeError, ValueError):
                            report['excluded'].append({'source': str(item), 'reason': 'not a readable text caplet'})
                            continue
                    entrypoint = item.relative_to(source).as_posix() == 'bin/pwnagotchi'
                    if item.suffix not in SOURCE_SUFFIXES and name not in SPECIAL_NAMES and not name.startswith(('LICENSE.', 'LICENCE.', 'COPYING.')) and not caplet and not entrypoint:
                        report['excluded'].append({'source': str(item), 'reason': 'not allowlisted source or license text'})
                        continue
                    relative = Path(label) / item.relative_to(source)
                    if caplet:
                        relative = relative.with_suffix('.cap.txt')
                    save(relative, item, item.suffix == '.toml' and name != 'pyproject.toml')
        except (OSError, ValueError) as exc:
            report['unavailable'].append({'source': str(source), 'reason': str(exc)})
    (output / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    (output / 'manifest.json').chmod(0o600)
    # Make only newly exported files usable by the invoking user after host sudo.
    if os.geteuid() == 0 and os.environ.get('SUDO_UID'):
        uid, gid = int(os.environ['SUDO_UID']), int(os.environ['SUDO_GID'])
        for directory, _, names in os.walk(output):
            os.chown(directory, uid, gid)
            for name in names:
                os.chown(Path(directory) / name, uid, gid)
    return report

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'backups' / ('pwnagotchi-review-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S')))
    args = parser.parse_args()
    try:
        report = collect(args.output)
    except (OSError, ValueError) as exc:
        parser.exit(1, str(exc) + '\n')
    print(f"Exported {len(report['files'])} files for local review to {args.output}")
    print(f"Unavailable locations: {len(report['unavailable'])}; see manifest.json. Installed files were not changed.")
    return 2 if report['unavailable'] else 0

if __name__ == '__main__':
    sys.exit(main())

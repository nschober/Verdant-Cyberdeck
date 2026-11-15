#!/usr/bin/env python3
"""Install artwork into the EXISTING TFT chooser; optionally select Pwnagotchi mode.

Default is a read-only plan. --apply requires host sudo; no drivers, boot overlays,
service enablement, network configuration or Pwnagotchi source are changed.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = Path('/opt/tft-terminal/launcher.py')
ARTWORK = Path('/usr/local/share/verdant-cyberdeck/splash.png')
MODE = Path('/etc/pwnagotchi/mode')
AUTO_FLAG = Path('/root/.pwnagotchi-auto')
BACKUPS = Path('/var/backups/verdant-cyberdeck')
MARKER = '# VERDANT TFT SPLASH v1'


def patch_launcher(source):
    if MARKER in source:
        compile(source, str(LAUNCHER), 'exec')
        return source
    draw = '    def draw():\n'
    image = "        im = Image.new('RGB', (480, 320), '#101823')\n"
    startup = '    draw()\n    last_check = time.monotonic()\n'
    if any(source.count(token) != 1 for token in (draw, image, startup)):
        raise ValueError('TFT launcher differs from the inspected implementation; refusing an unsafe patch')
    source = source.replace(draw, '    def draw(splash=False):\n', 1)
    injected = '''        # VERDANT TFT SPLASH v1
        if splash:
            with Image.open('/usr/local/share/verdant-cyberdeck/splash.png') as artwork:
                frame = artwork.convert('RGB')
            if frame.size != (480, 320):
                raise RuntimeError('Verdant splash must be 480x320')
            memory[:] = frame.tobytes('raw', 'BGRX')
            return
'''
    source = source.replace(image, injected + image, 1)
    # Adopt an already-running owner instead of drawing over its interface.
    native_startup = '''    # VERDANT: retain existing display/input owner after a chooser restart.
    for candidate in ('pwnagotchi.service', 'tft-terminal.service', 'tft-recon.service'):
        owner = subprocess.run(
            ['systemctl', 'show', '--property=ActiveState', '--value', candidate],
            capture_output=True, text=True, timeout=5)
        if owner.returncode:
            raise RuntimeError('Cannot verify existing TFT ownership: ' + candidate)
        if owner.stdout.strip() in ('active', 'activating', 'reloading'):
            mode = candidate
            break
    if mode is None:
        draw(splash=True)
        time.sleep(1.0)
        # Ignore splash-time input so a tap cannot select a radio operation later.
        for device in devices:
            try:
                while list(device.read()):
                    pass
            except BlockingIOError:
                pass
        draw()
    splash_held = {(device.fd, key) for device in devices for key in device.active_keys()}
    last_check = time.monotonic()
'''
    source = source.replace(startup, native_startup, 1)
    event_loop = '            for event in dev.read():\n'
    if source.count(event_loop) != 1:
        raise ValueError('Cannot identify existing input loop safely')
    input_guard = '''                # Discard held splash-time keys through their matching release.
                if event.type == E.EV_KEY and (dev.fd, event.code) in splash_held:
                    if event.value == 0:
                        splash_held.discard((dev.fd, event.code))
                    continue
'''
    source = source.replace(event_loop, event_loop + input_guard, 1)
    source = source.replace("'KALI TFT'", "'VERDANT CYBERDECK'")
    source = source.replace("'#101823'", "'#050c0a'").replace("'#243247'", "'#10291f'").replace("'#225b65'", "'#17563a'")
    compile(source, str(LAUNCHER), 'exec')
    return source


def systemctl(*arguments):
    result = subprocess.run(['systemctl', *arguments], capture_output=True, text=True, timeout=90)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or f'systemctl returned {result.returncode}')
    return result.stdout.strip()


def atomic_write(path, data, metadata=None):
    path = Path(path)
    if path.is_symlink():
        raise ValueError(f'Refusing symlink destination: {path}')
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.verdant-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), metadata['mode'] if metadata else 0o644)
            if metadata and os.geteuid() == 0:
                os.fchown(stream.fileno(), metadata['uid'], metadata['gid'])
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def make_plan(launcher=LAUNCHER, artwork=ARTWORK, mode=MODE, auto_flag=AUTO_FLAG,
              image_source=None, requested_mode=None):
    image_source = Path(image_source or ROOT / 'assets/splash.png')
    with Image.open(image_source) as image:
        if image.size != (480, 320):
            raise ValueError('Expected 480x320 splash artwork')
        image.verify()
    plans = [(Path(launcher), patch_launcher(Path(launcher).read_text()).encode()),
             (Path(artwork), image_source.read_bytes())]
    if requested_mode is not None:
        if requested_mode != 'auto':
            raise ValueError('Only the explicitly requested AUTO mode is supported by this integration')
        if Path(mode).read_text().strip() not in ('manual', 'auto'):
            raise ValueError('Unrecognized existing Pwnagotchi mode; refusing to replace it')
        plans += [(Path(mode), b'auto\n'), (Path(auto_flag), b'')]
    return plans


def install(plans, backup_root=BACKUPS, control=systemctl):
    # Establish actual host service state before writing anything.
    pwn_before = control('show', '--property=ActiveState', '--value', 'pwnagotchi.service')
    tft_before = control('show', '--property=ActiveState', '--value', 'tft-launcher.service')
    mode_requested = any(path == MODE for path, _ in plans)
    backup = Path(backup_root) / datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup.mkdir(parents=True, mode=0o700)
    records = []
    for index, (path, data) in enumerate(plans):
        if path.is_symlink():
            raise ValueError(f'Refusing symlink destination: {path}')
        info = {'path': str(path), 'after_sha256': hashlib.sha256(data).hexdigest(), 'existed': path.exists()}
        if path.exists():
            details = path.stat()
            if not stat.S_ISREG(details.st_mode):
                raise ValueError(f'Expected regular file: {path}')
            original = path.read_bytes()
            saved = backup / str(index)
            saved.write_bytes(original)
            saved.chmod(0o600)
            info.update(backup=str(saved), before_sha256=hashlib.sha256(original).hexdigest(),
                        mode=stat.S_IMODE(details.st_mode), uid=details.st_uid, gid=details.st_gid)
        records.append(info)
    report = {'files': records, 'pwn_before': pwn_before, 'tft_before': tft_before,
              'applied': False, 'boot_enablement_changed': False}
    manifest = backup / 'manifest.json'
    manifest.write_text(json.dumps(report, indent=2) + '\n')
    manifest.chmod(0o600)
    print(f'Backup and rollback manifest: {manifest}', flush=True)
    try:
        for (path, data), info in zip(plans, records):
            atomic_write(path, data, info if info['existed'] else None)
        # User requested AUTO operation. Restart only an already-running Pwnagotchi.
        if pwn_before in ('active', 'activating', 'reloading') and mode_requested:
            control('restart', 'pwnagotchi.service')
            report['pwn_action'] = 'restarted existing active service for AUTO mode'
        else:
            report['pwn_action'] = 'no service start; selected mode applies on next explicit launch'
        control('restart' if tft_before in ('active', 'activating', 'reloading') else 'start', 'tft-launcher.service')
        report['tft_after'] = control('show', '--property=ActiveState', '--value', 'tft-launcher.service')
        report['pwn_after'] = control('show', '--property=ActiveState', '--value', 'pwnagotchi.service')
        report['mode_after'] = MODE.read_text().strip() if MODE.exists() else 'unavailable'
        report['applied'] = True
    except Exception as exc:
        report['error'] = str(exc)
        raise
    finally:
        manifest.write_text(json.dumps(report, indent=2) + '\n')
    return report


def restore(manifest, control=systemctl):
    report = json.loads(Path(manifest).read_text())
    allowed = {str(LAUNCHER), str(ARTWORK), str(MODE), str(AUTO_FLAG)}
    for record in report['files']:
        path = Path(record['path'])
        if str(path) not in allowed or path.is_symlink():
            raise ValueError('Unexpected rollback path')
        if record['existed'] and hashlib.sha256(Path(record['backup']).read_bytes()).hexdigest() != record['before_sha256']:
            raise ValueError('Backup checksum mismatch')
        # The existing launch script consumes its mode flag normally.
        if path == AUTO_FLAG and not path.exists():
            continue
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != record['after_sha256']:
            raise ValueError(f'{path} changed since apply; refusing to overwrite a later change')
    for record in report['files']:
        path = Path(record['path'])
        if record['existed']:
            data = Path(record['backup']).read_bytes()
            if hashlib.sha256(data).hexdigest() != record['before_sha256']:
                raise ValueError('Backup checksum mismatch')
            atomic_write(path, data, record)
        elif path.exists():
            path.unlink()
    if control('show', '--property=ActiveState', '--value', 'pwnagotchi.service') == 'active':
        control('restart', 'pwnagotchi.service')
    control('restart', 'tft-launcher.service')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--apply', action='store_true')
    action.add_argument('--restore', type=Path, metavar='MANIFEST')
    parser.add_argument('--pwn-mode', choices=['auto'])
    args = parser.parse_args()
    if (args.apply or args.restore) and os.geteuid() != 0:
        parser.exit(1, 'Run apply/restore from a normal Pi terminal using existing sudo access.\n')
    try:
        if args.restore:
            restore(args.restore)
            print('Original TFT artwork/launcher and mode restored from verified backups.')
            return
        plans = make_plan(requested_mode=args.pwn_mode)
        if not args.apply:
            print('Read-only plan; installed files have NOT been changed:')
            for path, data in plans:
                print(f'  {path}: {len(data)} bytes')
            print('AUTO is selected only when --pwn-mode auto is explicitly supplied.')
            return
        report = install(plans)
        print(json.dumps(report, indent=2))
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        parser.exit(1, f'Integration failed: {exc}\nReview the reported backup manifest before retrying.\n')

if __name__ == '__main__':
    main()

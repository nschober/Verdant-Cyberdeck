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
SPLASH_MARKER = '# VERDANT TFT SPLASH v1'
MARKER = '# VERDANT NATIVE UI v2'
RUNTIME = Path('/usr/local/lib/verdant-cyberdeck')


def _patch_splash_v1(source):
    if SPLASH_MARKER in source:
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


def patch_launcher(source):
    """Upgrade original/v1 chooser to the actual six-button native dashboard."""
    if MARKER in source:
        compile(source,str(LAUNCHER),'exec')
        return source
    source=_patch_splash_v1(source)
    imports='from PIL import Image, ImageDraw, ImageFont\n'
    native_imports="""import sys
import shlex
sys.path.insert(0, '/usr/local/lib/verdant-cyberdeck')
from cyberdeck.native import NativeDeck, write_terminal_input
# VERDANT NATIVE UI v2
"""
    if source.count(imports)!=1:
        raise ValueError('Cannot identify native imports safely')
    source=source.replace(imports,imports+native_imports,1)
    start=source.index("        im = Image.new('RGB', (480, 320), '#050c0a')\n")
    end=source.index('    def choose(index):',start)
    source=source[:start]+"""        im = native.render()
        if time.monotonic() >= native.splash_until:
            draw_pointer(ImageDraw.Draw(im), pointer)
        memory[:] = im.tobytes('raw', 'BGRX')

"""+source[end:]
    startup='    # VERDANT: retain existing display/input owner after a chooser restart.\n'
    callbacks="""    pending_command = None
    pending_deadline = 0.0
    last_owner_scan = 0.0

    def open_terminal(argv):
        nonlocal pending_command, pending_deadline
        choose(0)
        if mode != 'tft-terminal.service':
            raise RuntimeError('Existing terminal service failed to start')
        pending_command = (shlex.join(argv) + '\\n').encode() if argv else None
        pending_deadline = time.monotonic() + 12
        print('VERDANT display owner: terminal (kali user)', flush=True)

    def pwn_action(action):
        nonlocal memory, fd, mode
        if action == 'stop':
            service('stop', 'pwnagotchi.service')
            return
        if action == 'start':
            choose(1)
            if mode != 'pwnagotchi.service':
                raise RuntimeError('Existing Pwnagotchi service failed to start')
        elif action == 'restart':
            if memory is not None:
                memory.close()
                os.close(fd)
                memory = fd = None
            service('restart', 'pwnagotchi.service')
            mode = 'pwnagotchi.service'
        else:
            raise ValueError('Unsupported service action')
        print('VERDANT display owner: Pwnagotchi; F1 returns to dashboard', flush=True)

    native = NativeDeck(open_terminal, pwn_action)
    atexit.register(native.close_runtime)
"""
    if source.count(startup)!=1:
        raise ValueError('Cannot identify ownership handoff safely')
    source=source.replace(startup,callbacks+'\n'+startup,1)
    first=source.index('    if mode is None:\n        draw(splash=True)',source.index(callbacks))
    last=source.index('    splash_held = ',first)
    source=source[:first]+"""    if mode is None:
        print('VERDANT display owner: native six-button dashboard', flush=True)
        draw()
    else:
        print('VERDANT adopting existing owner: ' + mode + '; F1 returns to dashboard', flush=True)
"""+source[last:]
    source=source.replace("            mode = candidate\n            break", "            mode = candidate\n            break",1)
    loop='    while True:\n        ready, _, _ = select.select(devices, [], [], 0.3)\n'
    new_loop="""    while True:
        native.tick()
        if mode is None and time.monotonic() - last_owner_scan > 0.6:
            last_owner_scan = time.monotonic()
            for candidate in ('pwnagotchi.service', 'tft-terminal.service', 'tft-recon.service'):
                external = subprocess.run(
                    ['systemctl', 'show', '--property=ActiveState', '--value', candidate],
                    capture_output=True, text=True, timeout=5)
                if external.returncode == 0 and external.stdout.strip() in ('active', 'activating', 'reloading'):
                    if memory is not None:
                        memory.close()
                        os.close(fd)
                        memory = fd = None
                    mode = candidate
                    print('VERDANT adopting external owner: ' + mode, flush=True)
                    break
        if mode is None:
            draw()
        if pending_command is not None and mode == 'tft-terminal.service':
            try:
                write_terminal_input(pending_command)
                pending_command = None
            except OSError as error:
                if time.monotonic() > pending_deadline:
                    print('VERDANT terminal input failed: ' + str(error), flush=True)
                    pending_command = None
        ready, _, _ = select.select(devices, [], [], 0.3)
"""
    if source.count(loop)!=1:
        raise ValueError('Cannot identify native event loop safely')
    source=source.replace(loop,new_loop,1)
    mouse="""                            for index in range(3):
                                if 18 <= pointer['x'] <= 462 and 62 + index * 64 <= pointer['y'] <= 118 + index * 64:
                                    choose(index)
                                    break
"""
    if source.count(mouse)!=1:
        raise ValueError('Cannot identify legacy mouse menu safely')
    source=source.replace(mouse,"                            native.tap(pointer['x'], pointer['y'])\n",1)
    touch="""                        info = dev.absinfo(E.ABS_Y)
                        value = touch.get((dev.fd, E.ABS_Y), info.min)
                        y = (value - info.min) * 319 / max(1, info.max - info.min)
                        for index in range(3):
                            if 62 + index * 64 <= y <= 118 + index * 64:
                                choose(index)
                                break
"""
    new_touch="""                        coordinates = []
                        for axis, pixels in ((E.ABS_X, 480), (E.ABS_Y, 320)):
                            info = dev.absinfo(axis)
                            value = touch.get((dev.fd, axis), info.min)
                            coordinates.append(native.coordinate(value, info.min, info.max, pixels))
                        pointer['x'], pointer['y'] = coordinates
                        publish_pointer(pointer)
                        native.touch_up(dev.fd, *coordinates)
"""
    if source.count(touch)!=1:
        raise ValueError('Cannot identify legacy touch menu safely')
    source=source.replace(touch,new_touch,1)
    key="""                elif mode is None:
                    if event.code in (E.KEY_1, E.KEY_KP1):
"""
    first=source.index(key);last=source.index("                elif mode in ('tft-terminal.service', 'tft-recon.service'):",first)
    source=source[:first]+"""                elif mode is None:
                    native.key(event.code, event.value)
"""+source[last:]
    source=source.replace("                pressed.add(event.code)\n", "                if event.code == E.BTN_TOUCH and event.value == 1 and mode is None:\n                    native.touch_down(dev.fd)\n                pressed.add(event.code)\n",1)
    source=source.replace("                    elif event.code == E.REL_WHEEL and mode == 'tft-recon.service':", "                    elif event.code == E.REL_WHEEL and mode is None:\n                        native.scroll(-event.value * 3)\n                    elif event.code == E.REL_WHEEL and mode == 'tft-recon.service':",1)
    old_fifo="""                            out = os.open('/tmp/kali-tft-input', os.O_WRONLY | os.O_NONBLOCK)
                            try:
                                os.write(out, char.encode())
                            finally:
                                os.close(out)
"""
    if source.count(old_fifo)!=1:
        raise ValueError('Cannot identify existing terminal input safely')
    source=source.replace(old_fifo,"                            write_terminal_input(char.encode())\n",1)
    # Returning from a native owner always returns to the persistent home menu.
    cut=source.index(startup)
    before,events=source[:cut],source[cut:]
    for spaces in (16,20,24,28):
        pad=' '*spaces
        events=events.replace(pad+'mode = None\n'+pad+'draw()\n',pad+'mode = None\n'+pad+'native.home()\n'+pad+"print('VERDANT display owner: native dashboard', flush=True)\n"+pad+'draw()\n')
    source=before+events
    compile(source,str(LAUNCHER),'exec')
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
              image_source=None, requested_mode=None, runtime_root=None):
    image_source = Path(image_source or ROOT / 'assets/splash.png')
    with Image.open(image_source) as image:
        if image.size != (480, 320):
            raise ValueError('Expected 480x320 splash artwork')
        image.verify()
    runtime_root=Path(runtime_root or RUNTIME)
    if runtime_root.is_symlink() or (runtime_root/'cyberdeck').is_symlink():
        raise ValueError('Native runtime directories must not be symlinks')
    plans=[]
    for module in sorted((ROOT/'cyberdeck').glob('*.py')):
        content=module.read_bytes()
        compile(content,str(module),'exec')
        plans.append((runtime_root/'cyberdeck'/module.name,content))
    plans += [(Path(artwork),image_source.read_bytes()),
              (Path(launcher),patch_launcher(Path(launcher).read_text()).encode())]
    if requested_mode is not None:
        if requested_mode != 'auto':
            raise ValueError('Only the explicitly requested AUTO mode is supported by this integration')
        if Path(mode).read_text().strip() not in ('manual', 'auto'):
            raise ValueError('Unrecognized existing Pwnagotchi mode; refusing to replace it')
        plans += [(Path(mode), b'auto\n'), (Path(auto_flag), b'')]
    return plans


def install(plans, backup_root=BACKUPS, control=systemctl):
    # Establish actual host service state before writing anything.
    terminal_user=control('show','--property=User','--value','tft-terminal.service')
    if terminal_user!='kali':
        raise ValueError('Native terminal handoff requires the existing service to run as kali')
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
            if path.is_relative_to(RUNTIME) and os.geteuid()==0 and (details.st_uid!=0 or stat.S_IMODE(details.st_mode)&0o022):
                raise ValueError('Refusing user-writable code in root native runtime')
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
        if any(path.is_relative_to(RUNTIME) for path,_ in plans):
            for directory in (RUNTIME,RUNTIME/'cyberdeck'):
                directory.mkdir(parents=True,exist_ok=True,mode=0o755)
                if os.geteuid()==0:
                    os.chown(directory,0,0)
                    directory.chmod(0o755)
        for (path, data), info in zip(plans, records):
            atomic_write(path, data, info if info['existed'] else None)
        # User requested AUTO operation. Restart only an already-running Pwnagotchi.
        if pwn_before in ('active', 'activating', 'reloading') and mode_requested:
            control('restart', 'pwnagotchi.service')
            report['pwn_action'] = 'restarted existing active service for AUTO mode'
        elif mode_requested:
            report['pwn_action'] = 'no service start; selected mode applies on next explicit launch'
        else:
            report['pwn_action'] = 'no Pwnagotchi service change; existing mode retained'
        control('restart' if tft_before in ('active', 'activating', 'reloading') else 'start', 'tft-launcher.service')
        report['tft_after'] = control('show', '--property=ActiveState', '--value', 'tft-launcher.service')
        report['pwn_after'] = control('show', '--property=ActiveState', '--value', 'pwnagotchi.service')
        owners={name:control('show','--property=ActiveState','--value',name) for name in ('pwnagotchi.service','tft-terminal.service','tft-recon.service')}
        report['display_owner']=next((name for name,state in owners.items() if state in ('active','activating','reloading')),'Verdant native dashboard')
        report['return_to_dashboard']='Press F1 if an existing application currently owns the TFT'
        report['native_runtime_installed']=str(RUNTIME)
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
    allowed.update(str(RUNTIME/'cyberdeck'/p.name) for p in (ROOT/'cyberdeck').glob('*.py'))
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
    except (OSError, ValueError, RuntimeError, SyntaxError, subprocess.TimeoutExpired) as exc:
        parser.exit(1, f'Integration failed: {exc}\nReview the reported backup manifest before retrying.\n')

if __name__ == '__main__':
    main()

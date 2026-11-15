"""Integration with the existing system service; never execute a second copy."""
from pathlib import Path
import tomllib
from .backend import run, installed

SERVICE = 'pwnagotchi.service'
CONFIG = Path('/etc/pwnagotchi/config.toml')
UNIT = Path('/etc/systemd/system') / SERVICE

def state():
    result = run(['systemctl', 'show', SERVICE, '--property=ActiveState,SubState,MainPID,Result'])
    if result.code:
        return 'unknown (system bus inaccessible)'
    values = dict(line.split('=', 1) for line in result.output.splitlines() if '=' in line)
    return f"{values.get('ActiveState', 'unknown')} / {values.get('SubState', '?')} PID {values.get('MainPID', '?')}"

def status():
    results = [f'Executable: {installed("pwnagotchi") or "missing"}', f'State: {state()}',
               '\nInstalled unit:', UNIT.read_text() if UNIT.exists() else 'Unit not found']
    for service in (SERVICE, 'pwnagotchi-bettercap.service', 'pwngrid-peer.service'):
        results.append(run(['systemctl', 'status', '--no-pager', '--full', service]).output)
    results += ['\nCompatibility: custom ILI9488 service detected; runtime operation must be confirmed on the host.',
                'Service uses /root/pwnagotchi-modern/tft/launch.sh; this path is not readable by kali.',
                'Starting the service runs its existing radio dependencies and may replace tft-terminal.',
                'Dashboard exit does not stop or modify Pwnagotchi. No mode changes are performed.']
    return '\n'.join(results)

def configuration():
    try:
        config = tomllib.loads(CONFIG.read_text())
        rows = [f'Configuration: {CONFIG}', 'Read only; credentials omitted.']
        for section, keys in [('main', ['iface', 'mode', 'custom_plugins']), ('ai', ['enabled']),
                              ('ui.display', ['enabled', 'type', 'device', 'rotation']),
                              ('ui.web', ['enabled', 'address', 'port'])]:
            obj = config
            for part in section.split('.'):
                obj = obj.get(part, {})
            for key in keys:
                rows.append(f'{section}.{key}: {obj.get(key, "not explicitly set")}')
        plugins = config.get('main', {}).get('plugins', {})
        rows += ['\nEnabled plugins: ' + ', '.join(k for k,v in plugins.items() if isinstance(v,dict) and v.get('enabled'))]
        mode = Path('/etc/pwnagotchi/mode')
        rows += ['Mode file: ' + (mode.read_text().strip() if mode.exists() else 'absent'),
                 'Captured host launcher supports manual and auto. Mode is shown above; runtime health must be checked separately.',
                 'Learned data, plugins, keys, and network settings remain managed by the existing installation.']
        return '\n'.join(rows)
    except (OSError, ValueError) as exc:
        return str(exc)

def logs():
    return run(['journalctl', '-u', SERVICE, '-u', 'pwnagotchi-bettercap.service', '-u', 'pwngrid-peer.service', '-n', '100', '--no-pager']).output

def control_args(action):
    if action not in ('start', 'stop', 'restart'):
        raise ValueError('Unsupported service action')
    if not UNIT.exists():
        raise RuntimeError('Existing Pwnagotchi unit not detected; refusing to launch another copy.')
    return ['systemctl', action, SERVICE]

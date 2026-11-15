from .backend import run

def status():
    return '\n'.join(run(['bluetoothctl', *args]).output for args in (['list'], ['show'], ['devices']))

def discover():
    scan = run(['bluetoothctl', '--timeout', '8', 'scan', 'on'], timeout=12)
    return scan.output + '\n\n' + run(['bluetoothctl', 'devices']).output

def details():
    devices=run(['bluetoothctl','devices'])
    if devices.code:
        return devices.output
    rows=[]
    for line in devices.output.splitlines()[:8]:
        parts=line.split(maxsplit=2)
        if len(parts)>=2 and parts[0]=='Device':
            rows.append(run(['bluetoothctl','info',parts[1]],timeout=3).output)
    return '\n\n'.join(rows) or 'No known devices. Use Discover first; Bluetooth power is not changed automatically.'

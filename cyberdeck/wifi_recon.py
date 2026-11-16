from .backend import run

SSID_COLOR = '#67fa9f'
MAC_COLOR = '#79cfff'
SIGNAL_COLOR = '#ffd166'

class ScanText(str):
    """Plain scan output with optional per-character display colors."""
    def __new__(cls, segments):
        value = super().__new__(cls, ''.join(text for text, _ in segments))
        value.colors = [color for text, color in segments for _ in text]
        return value

def fields(line):
    parts, current, escaped = [], '', False
    for char in line:
        if escaped:
            current += char
            escaped = False
        elif char == '\\':
            escaped = True
        elif char == ':':
            parts.append(current)
            current = ''
        else:
            current += char
    parts.append(current)
    return parts

def adapters():
    return run(['nmcli', '-f', 'DEVICE,TYPE,STATE,CONNECTION', 'device', 'status']).output + '\n\n' + run(['iw', 'dev']).output

def scan(sort='signal'):
    result = run(['nmcli', '--terse', '--escape', 'yes', '-f', 'IN-USE,SSID,BSSID,CHAN,FREQ,SIGNAL,SECURITY,DEVICE', 'device', 'wifi', 'list', '--rescan', 'yes'], timeout=30)
    if result.code:
        raise RuntimeError(result.output)
    rows = []
    for line in result.output.splitlines():
        values = fields(line)
        if len(values) == 8:
            rows.append(dict(zip(('active','ssid','bssid','channel','frequency','signal','security','device'), values)))
    rows.sort(key=(lambda r:r['ssid'].casefold()) if sort == 'ssid' else (lambda r:-int(r['signal'] or 0)))
    segments = []
    for r in rows:
        if segments:
            segments.append(('\n\n', None))
        segments.extend([
            (f"{'* ' if r['active'] else ''}{r['ssid'] or '<hidden>'}", SSID_COLOR),
            ('  ', None), (f"{r['signal']}%", SIGNAL_COLOR), ('\n', None),
            (r['bssid'], MAC_COLOR),
            (f"  {r['security']}\nCh {r['channel']}  {r['frequency']}  {r['device']}", None)])
    return ScanText(segments) if segments else 'No access points found.'

def capabilities():
    return adapters() + '\n\nMonitor mode capabilities (no modes changed):\n' + run(['iw', 'list']).output

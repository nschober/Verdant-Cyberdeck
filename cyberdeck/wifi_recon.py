from .backend import run

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
    return '\n\n'.join(f"{'* ' if r['active'] else ''}{r['ssid'] or '<hidden>'}  {r['signal']}%\n{r['bssid']}  {r['security']}\nCh {r['channel']}  {r['frequency']}  {r['device']}" for r in rows) or 'No access points found.'

def capabilities():
    return adapters() + '\n\nMonitor mode capabilities (no modes changed):\n' + run(['iw', 'list']).output

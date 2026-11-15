import datetime
import platform
from pathlib import Path
from .backend import run

def summary():
    ip = run(['hostname', '-I']).output
    adapters = run(['nmcli', '-t', '-f', 'DEVICE,TYPE,STATE', 'device']).output
    return f"{datetime.datetime.now():%m/%d %H:%M} | IP {ip or 'unavailable'}\n{adapters}"

def information():
    return '\n'.join([platform.platform(), summary(), run(['ip', '-brief', 'address']).output,
                       run(['free', '-h']).output, run(['lscpu']).output])

def graphics():
    rows = []
    for fb in Path('/sys/class/graphics').glob('fb[0-9]*'):
        rows.append(f"{fb.name}: {(fb/'name').read_text().strip()} {(fb/'virtual_size').read_text().strip()}")
    return '\n'.join(rows)

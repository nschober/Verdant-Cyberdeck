"""Shared TFT pointer and readable, wrapped WiFi Recon output."""
import json
import re
import textwrap
from pathlib import Path

POINTER = Path('/tmp/kali-tft-pointer.json')
TEXT = '#d8e2ef'
SSID = '#63f5ba'
MAC = '#65cfff'
CHANNEL = '#ffda73'
SECURITY = '#d5a0ff'
WARNING = '#ff8585'


def colored_line(line):
    colors = [TEXT] * len(line)
    rules = [
        (r'\b(?:warn(?:ing)?|error|failed|lost)\b.*', WARNING, 0),
        (r'\b(?:[0-9a-f]{2}:){5}[0-9a-f]{2}\b', MAC, 0),
        (r'\b(?:ch(?:annel)?\s*[:=]?\s*\d+|[-−]?\d+\s*dBm)\b', CHANNEL, 0),
        (r'\b(?:WPA[123]?(?:[-/][A-Z0-9]+)*|WEP|OPEN|RSN)\b', SECURITY, 0),
        (r'\b(?:SSID|ESSID)\s*[:=]\s*("[^"]*"|\'[^\']*\'|[^,;|]+)', SSID, 1),
        (r'\b(?:access point|station)\s+(.+?)\s*\((?:[0-9a-f]{2}:){5}[0-9a-f]{2}\)', SSID, 1),
    ]
    for pattern, color, group in rules:
        for match in re.finditer(pattern, line, re.I):
            start, end = match.span(group)
            colors[start:end] = [color] * (end - start)
    return list(zip(line, colors))


def recon_rows(lines, columns, rows, scroll=0):
    """Wrap at words, split oversized tokens, and preserve token colors."""
    wrapped = []
    wrapper = textwrap.TextWrapper(width=columns, expand_tabs=False,
                                   replace_whitespace=False, break_on_hyphens=False)
    for line in lines:
        line = line.rstrip()
        if not line:
            continue
        colored = colored_line(line)
        offset = 0
        for chunk in wrapper.wrap(line):
            start = line.find(chunk, offset)
            wrapped.append(colored[start:start + len(chunk)])
            offset = start + len(chunk)
    end = max(rows, len(wrapped) - max(0, scroll))
    return wrapped[max(0, end - rows):end]


def draw_pointer(draw, state=None):
    if state is None:
        try:
            state = json.loads(POINTER.read_text())
        except (OSError, ValueError):
            return
    if not state.get('active'):
        return
    x, y = int(state['x']), int(state['y'])
    draw.polygon([(x, y), (x, y + 15), (x + 4, y + 11), (x + 8, y + 18),
                  (x + 11, y + 16), (x + 7, y + 9), (x + 13, y + 9)],
                 fill='white', outline='#101823')

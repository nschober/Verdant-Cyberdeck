#!/usr/bin/env python3
from pathlib import Path

import os
import pty
import pwd
import stat
import mmap
import fcntl
import struct
import select
import subprocess
import time
import signal
import codecs
import json
from tft_view import recon_rows, draw_pointer, SSID, MAC, CHANNEL, SECURITY

from PIL import Image, ImageDraw, ImageFont
import pyte

WIDTH = 480
HEIGHT = 320
COLS = 60
ROWS = 18
FONT_SIZE = 14

FB = "/dev/fb" + next(
    line.split()[0]
    for line in Path("/proc/fb").read_text().splitlines()
    if "ili9488" in line.lower()
)
FIFO = "/tmp/kali-tft-input"

running = True

def stop(sig, frame):
    global running
    running = False

signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)

font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
font = ImageFont.truetype(font_path, FONT_SIZE)

RECON = os.environ.get("TFT_WIFI_RECON") == "1"
CELL = font.getlength("M")
COLS = int((WIDTH - 6) / CELL)
# Capture full log lines before wrapping them to the physical display width.
screen = pyte.HistoryScreen(512, ROWS, history=200) if RECON else pyte.Screen(COLS, ROWS)
decoder = codecs.getincrementaldecoder("utf-8")("replace")
scroll = 0
stream = pyte.Stream(screen)

master, slave = pty.openpty()

winsize = struct.pack("HHHH", ROWS, 512 if RECON else COLS, 0, 0)
fcntl.ioctl(slave, 0x5414, winsize)

shell = subprocess.Popen(
    (["/usr/bin/bettercap", "-no-colors", "-iface", "wlan1",
      "-eval", "wifi.recon on"] if os.environ.get("TFT_WIFI_RECON") == "1"
     else ["/bin/bash", "--login"]),
    stdin=slave,
    stdout=slave,
    stderr=slave,
    start_new_session=True,
    env={
        **os.environ,
        "TERM": "linux",
        "COLUMNS": str(COLS),
        "LINES": str(ROWS)
    }
)

os.close(slave)

if not os.path.exists(FIFO):
    os.mkfifo(FIFO, 0o600)

fifo_fd = os.open(FIFO, os.O_RDWR | os.O_NONBLOCK | os.O_NOFOLLOW)
if not stat.S_ISFIFO(os.fstat(fifo_fd).st_mode):
    raise RuntimeError("TFT input path must be a FIFO")
if os.geteuid() == 0:
    owner = pwd.getpwnam("kali")
    os.fchown(fifo_fd, owner.pw_uid, owner.pw_gid)

fb_fd = os.open(FB, os.O_RDWR)

# Restore framebuffer scanout when starting after a DRM handoff.
fcntl.ioctl(fb_fd, 0x4611, 0)  # FBIOBLANK, FB_BLANK_UNBLANK

size = WIDTH * HEIGHT * 4
fb = mmap.mmap(
    fb_fd,
    size,
    flags=mmap.MAP_SHARED,
    prot=mmap.PROT_READ | mmap.PROT_WRITE
)

def render():
    image = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(image)

    draw.rectangle((0, 0, WIDTH, 23), fill=(20, 60, 30))
    draw.text((8, 4), ("WIFI RECON | F1: MENU" if os.environ.get("TFT_WIFI_RECON") == "1"
               else "TFT TERMINAL | F1: MENU / F2: DESKTOP"),
              font=font, fill=(255, 255, 255))

    if RECON:
        history = [''.join(row[x].data for x in range(screen.columns))
                   for row in screen.history.top]
        lines = history + list(screen.display)
        for y, row in enumerate(recon_rows(lines, COLS, 16, scroll)):
            for x, (char, color) in enumerate(row):
                draw.text((3 + x * CELL, 27 + y * 16), char, font=font, fill=color)
        draw.rectangle((0, 299, WIDTH, HEIGHT), fill='#182435')
        for x, label, color in [(4, 'SSID', SSID), (55, 'MAC', MAC),
                                 (102, 'CH/dBm', CHANNEL), (180, 'SECURITY', SECURITY)]:
            draw.text((x, 302), label, font=font, fill=color)
        draw.text((280, 302), 'Scroll: wheel', font=font, fill='white')
    else:
        for y, line in enumerate(screen.display):
            draw.text((3, 27 + y * 16), line, font=font, fill=(100, 255, 120))

    if not RECON and screen.cursor.hidden is False:
        x = 3 + screen.cursor.x * CELL
        y = 27 + screen.cursor.y * 16
        if 0 <= x < WIDTH and 0 <= y < HEIGHT:
            draw.rectangle(
                (x, y + 13, min(x + 7, WIDTH - 1), y + 14),
                fill=(100, 255, 120)
            )

    draw_pointer(draw)
    fb.seek(0)
    fb.write(image.tobytes("raw", "BGRX"))

try:
    while running and shell.poll() is None:
        ready, _, _ = select.select(
            [master, fifo_fd], [], [], 0.15
        )

        for fd in ready:
            try:
                data = os.read(fd, 4096)
            except OSError:
                data = b""

            if not data:
                continue

            if fd == master:
                stream.feed(decoder.decode(data))
            else:
                os.write(master, data)

        if RECON:
            try:
                requested = json.loads(Path('/tmp/kali-tft-pointer.json').read_text())
                scroll = max(0, min(3000, int(requested.get('scroll', 0))))
            except (OSError, ValueError, TypeError):
                pass
        render()

finally:
    shell.terminate()
    fb.close()
    os.close(fb_fd)
    os.close(fifo_fd)
    os.close(master)

#!/usr/bin/python3
"""Persistent TFT chooser. F1 returns from either application."""
import atexit
import fcntl
import json
from tft_view import POINTER, draw_pointer
import mmap
import os
from pathlib import Path
import select
import subprocess
import time
from evdev import InputDevice, list_devices, ecodes as E
from PIL import Image, ImageDraw, ImageFont


def service(action, name):
    subprocess.run(['systemctl', action, name], check=True, timeout=45)


def publish_pointer(pointer):
    temporary = POINTER.with_suffix('.tmp')
    temporary.write_text(json.dumps(pointer))
    temporary.chmod(0o644)
    temporary.replace(POINTER)


def main():
    devices = []
    for path in list_devices():
        dev = InputDevice(path)
        caps = dev.capabilities()
        if E.ABS_X in dict(caps.get(E.EV_ABS, [])) or E.KEY_A in caps.get(E.EV_KEY, []) or E.REL_X in caps.get(E.EV_REL, []):
            dev.grab()
            devices.append(dev)
        else:
            dev.close()
    atexit.register(lambda: [dev.close() for dev in devices])
    keyboard_owned = True
    pending_handoff = False
    pointer = dict(x=240, y=150, active=True, scroll=0)
    publish_pointer(pointer)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf', 24)
    small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf', 14)
    mode = None
    message = 'Choose 1 / 2 / 3. F2: mouse + keys to desktop'
    selected = 0
    touch = {}
    pressed = set()
    memory = None
    fd = None

    def draw():
        nonlocal memory, fd
        if memory is None:
            number = next(line.split()[0] for line in Path('/proc/fb').read_text().splitlines() if 'ili9488' in line.lower())
            fd = os.open('/dev/fb' + number, os.O_RDWR)
            fcntl.ioctl(fd, 0x4611, 0)
            stride = int(Path('/sys/class/graphics/fb' + number + '/stride').read_text())
            if stride != 1920:
                raise RuntimeError('Unexpected TFT stride')
            memory = mmap.mmap(fd, stride * 320)
        im = Image.new('RGB', (480, 320), '#101823')
        d = ImageDraw.Draw(im)
        d.text((22, 16), 'KALI TFT', font=font, fill='#59e4bf')
        for index, label in enumerate(('1  TERMINAL  >_', '2  PWNAGOTCHI  (o_o)', '3  WIFI RECON')):
            y = 62 + index * 64
            d.rounded_rectangle((18, y, 462, y + 56), radius=12, fill=('#225b65' if selected == index else '#243247'))
            d.text((34, y + 16), label, font=font, fill='white')
        d.text((20, 264), message[:50], font=small, fill='#d4dce7')
        d.text((20, 291), 'F1: menu | Pwnagotchi: tap for menu', font=small, fill='#59e4bf')
        draw_pointer(d, pointer)
        memory[:] = im.tobytes('raw', 'BGRX')

    def choose(index):
        nonlocal mode, message, memory, fd
        target = ('tft-terminal.service', 'pwnagotchi.service', 'tft-recon.service')[index]
        try:
            if memory is not None:
                memory.close()
                os.close(fd)
                memory = fd = None
            for other in ('tft-terminal.service', 'pwnagotchi.service', 'tft-recon.service'):
                if other != target:
                    service('stop', other)
            service('start', target)
            mode = target
            pointer['scroll'] = 0
            publish_pointer(pointer)
        except Exception as exc:
            message = 'Launch failed; check journalctl'
            print(str(exc), flush=True)
            mode = None
            draw()

    draw()
    last_check = time.monotonic()
    while True:
        ready, _, _ = select.select(devices, [], [], 0.3)
        for dev in ready:
            for event in dev.read():
                if event.type == E.EV_REL:
                    if not keyboard_owned:
                        continue
                    if event.code == E.REL_X:
                        pointer['x'] = max(0, min(466, pointer['x'] + event.value))
                    elif event.code == E.REL_Y:
                        pointer['y'] = max(0, min(301, pointer['y'] + event.value))
                    elif event.code == E.REL_WHEEL and mode == 'tft-recon.service':
                        pointer['scroll'] = max(0, min(3000, pointer['scroll'] + event.value * 3))
                    publish_pointer(pointer)
                    if mode is None:
                        draw()
                    continue
                if event.type == E.EV_KEY and event.code == E.BTN_LEFT:
                    if keyboard_owned and event.value == 1:
                        if mode is None:
                            for index in range(3):
                                if 18 <= pointer['x'] <= 462 and 62 + index * 64 <= pointer['y'] <= 118 + index * 64:
                                    choose(index)
                                    break
                        elif mode == 'pwnagotchi.service' or pointer['y'] < 24:
                            service('stop', mode)
                            mode = None
                            draw()
                    continue
                if event.type == E.EV_ABS:
                    touch[(dev.fd, event.code)] = event.value
                if event.type != E.EV_KEY:
                    continue
                if event.value == 0:
                    pressed.discard(event.code)
                    if event.code == E.BTN_TOUCH and mode is None:
                        info = dev.absinfo(E.ABS_Y)
                        value = touch.get((dev.fd, E.ABS_Y), info.min)
                        y = (value - info.min) * 319 / max(1, info.max - info.min)
                        for index in range(3):
                            if 62 + index * 64 <= y <= 118 + index * 64:
                                choose(index)
                                break
                    elif event.code == E.BTN_TOUCH and mode == 'pwnagotchi.service':
                        service('stop', mode)
                        mode = None
                        draw()
                    continue
                pressed.add(event.code)
                if event.code == E.KEY_F2 and event.value == 1:
                    modifiers = {
                        E.KEY_LEFTSHIFT, E.KEY_RIGHTSHIFT,
                        E.KEY_LEFTCTRL, E.KEY_RIGHTCTRL,
                        E.KEY_LEFTALT, E.KEY_RIGHTALT,
                        E.KEY_LEFTMETA, E.KEY_RIGHTMETA,
                    }
                    active = set().union(*(set(device.active_keys()) for device in devices))
                    if not active & modifiers:
                        pending_handoff = True
                    continue
                if event.code == E.KEY_F1 and event.value == 1:
                    pending_handoff = False
                    if not keyboard_owned:
                        for keyboard in devices:
                            if (E.KEY_A in keyboard.capabilities().get(E.EV_KEY, [])
                                or E.REL_X in keyboard.capabilities().get(E.EV_REL, [])):
                                keyboard.grab()
                        keyboard_owned = True
                        pointer['active'] = True
                        publish_pointer(pointer)
                    pressed.clear()
                    if mode:
                        service('stop', mode)
                    mode = None
                    draw()
                elif not keyboard_owned:
                    continue
                elif mode is None:
                    if event.code in (E.KEY_1, E.KEY_KP1):
                        choose(0)
                    elif event.code in (E.KEY_2, E.KEY_KP2):
                        choose(1)
                    elif event.code in (E.KEY_3, E.KEY_KP3):
                        choose(2)
                    elif event.code in (E.KEY_UP, E.KEY_DOWN, E.KEY_TAB):
                        selected = (selected + (-1 if event.code == E.KEY_UP else 1)) % 3
                        draw()
                    elif event.code == E.KEY_ENTER:
                        choose(selected)
                elif mode in ('tft-terminal.service', 'tft-recon.service'):
                    key = E.KEY.get(event.code, '')
                    shift = bool(pressed & {E.KEY_LEFTSHIFT, E.KEY_RIGHTSHIFT})
                    special = {E.KEY_ENTER:'\r', E.KEY_BACKSPACE:'\x7f', E.KEY_SPACE:' ', E.KEY_TAB:'\t', E.KEY_ESC:'\x1b', E.KEY_UP:'\x1b[A', E.KEY_DOWN:'\x1b[B', E.KEY_RIGHT:'\x1b[C', E.KEY_LEFT:'\x1b[D'}
                    char = special.get(event.code, '')
                    if isinstance(key, str) and key.startswith('KEY_') and len(key) == 5:
                        char = key[-1] if shift else key[-1].lower()
                        if pressed & {E.KEY_LEFTCTRL, E.KEY_RIGHTCTRL} and char.isalpha():
                            char = chr(ord(char.lower()) - 96)
                    punctuation = {E.KEY_MINUS:('-','_'), E.KEY_EQUAL:('=','+'), E.KEY_LEFTBRACE:('[','{'), E.KEY_RIGHTBRACE:(']','}'), E.KEY_SEMICOLON:(';',':'), E.KEY_APOSTROPHE:("'",'"'), E.KEY_COMMA:(',','<'), E.KEY_DOT:('.', '>'), E.KEY_SLASH:('/','?'), E.KEY_BACKSLASH:('\\','|'), E.KEY_GRAVE:('`','~')}
                    if event.code in punctuation:
                        char = punctuation[event.code][shift]
                    if shift and char in '1234567890' and char:
                        char = '!@#$%^&*()'['1234567890'.index(char)]
                    if char:
                        try:
                            out = os.open('/tmp/kali-tft-input', os.O_WRONLY | os.O_NONBLOCK)
                            try:
                                os.write(out, char.encode())
                            finally:
                                os.close(out)
                        except OSError:
                            pass
        # Finish the handoff only after every physical key/button is up.
        # This keeps press/release pairs on the same side of the input grab.
        if pending_handoff and not any(device.active_keys() for device in devices):
            keyboard_owned = not keyboard_owned
            for device in devices:
                caps = device.capabilities().get(E.EV_KEY, [])
                if E.KEY_A in caps or E.REL_X in device.capabilities().get(E.EV_REL, []):
                    if keyboard_owned:
                        device.grab()
                    else:
                        device.ungrab()
            pending_handoff = False
            pointer['active'] = keyboard_owned
            publish_pointer(pointer)
            pressed.clear()
            message = ('Mouse + keys: TFT. F2: desktop' if keyboard_owned
                       else 'Mouse + keys: desktop. F2: TFT')
            if mode is None:
                draw()
        if mode and time.monotonic() - last_check > 3:
            last_check = time.monotonic()
            state = subprocess.run(['systemctl', 'is-active', '--quiet', mode]).returncode
            if state:
                mode = None
                message = 'App exited. Choose an option.'
                draw()


if __name__ == '__main__':
    main()

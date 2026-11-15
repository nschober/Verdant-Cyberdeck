"""Verdant UI adapter for the existing native TFT/input supervisor.

Runs from root-owned copied code on the Pi. Interactive commands are handed to
its EXISTING kali-user terminal service, not executed in the root UI process.
"""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import time
from PIL import ImageDraw
from .dashboard import Dashboard
from .splash import render_splash, SPLASH_SECONDS
from .backend import installed
from . import system_status
from .alerts import AlertReader, CARD

class NativeDeck(Dashboard):
    def __init__(self, terminal, pwn_action, log_path=None, alert_reader=None):
        self.alerts = alert_reader or AlertReader()
        self._terminal = terminal
        self._pwn_action = pwn_action
        self._selection = None
        self._blocked_touches = set()
        self._closed = False
        self.native_log = Path(log_path or '/var/log/verdant-cyberdeck/native.log')
        self.native_log.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._handler = RotatingFileHandler(self.native_log,maxBytes=500000,backupCount=2)
        self._handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        self._logger = logging.getLogger()
        self._prior_level = self._logger.level
        self._logger.setLevel(logging.INFO)
        self._logger.addHandler(self._handler)
        super().__init__(framebuffer=True, log_path=self.native_log)
        self._splash_pending = True
        self.splash_until = float('inf')
        logging.info('Native six-button dashboard initialized; no radio operation requested')

    def reset(self, title):
        self._selection = None
        super().reset(title)

    def home(self):
        super().home()
        self.next_status=0

    def shutdown(self):
        # Exit the visible dashboard to the existing kali-user console. The old
        # supervisor remains available for F1, as it did before this integration.
        self._terminal(None)

    def close_runtime(self):
        if self._closed:
            return
        self._closed = True
        self.pool.shutdown(wait=False,cancel_futures=True)
        self._logger.removeHandler(self._handler)
        self._handler.close()
        self._logger.setLevel(self._prior_level)

    def control(self, action):
        try:
            if action not in ('start','stop','restart'):
                raise ValueError('Unsupported Pwnagotchi action')
            self._pwn_action(action)
            if action == 'stop':
                self.pwn()
        except Exception as exc:
            logging.exception('Native Pwnagotchi action failed')
            self.text('SERVICE ERROR',str(exc))

    def launch(self, executable, args=()):
        path=installed(executable)
        if not path:
            self.text('NOT INSTALLED',executable+' is not installed')
            return
        self._terminal([path,*args])

    @staticmethod
    def coordinate(value,minimum,maximum,pixels):
        return max(0,min(pixels-1,round((value-minimum)*(pixels-1)/max(1,maximum-minimum))))

    def tap(self,x,y):
        if self.alerts.current() and CARD[0]<=x<=CARD[2] and CARD[1]<=y<=CARD[3]:
            self.alerts.dismiss();return
        super().tap(x,y)

    def touch_down(self,device_id):
        if time.monotonic()<self.splash_until:
            self._blocked_touches.add(device_id)
        else:
            self._blocked_touches.discard(device_id)

    def touch_up(self,device_id,x,y):
        if device_id in self._blocked_touches:
            self._blocked_touches.discard(device_id)
            return
        self.tap(x,y)

    def preview_splash(self):
        self._splash_pending=True
        self.splash_until=float('inf')
        logging.info('Native splash preview requested')

    def display_information(self):
        self.text('TFT DISPLAY',system_status.graphics()+'\nF1 returns from a native tool. F3 previews the splash.',
                  [('SHOW SPLASH',self.preview_splash),('SYSTEM',self.system)])

    def system(self):
        super().system()
        for button in self.buttons:
            if button.label=='DISPLAY INFO':
                button.label='DISPLAY / SPLASH'
                button.action=self.display_information

    def key(self,code,value):
        from evdev import ecodes as E
        if value != 1:
            return
        if code==E.KEY_F3:
            self.preview_splash()
            return
        if time.monotonic()<self.splash_until:
            return
        if code in (E.KEY_UP,E.KEY_DOWN):
            self.scroll(-3 if code==E.KEY_UP else 3)
        elif code==E.KEY_TAB:
            self._selection=0 if self._selection is None else (self._selection+1)%len(self.buttons)
        elif code==E.KEY_ENTER and self._selection is not None:
            b=self.buttons[self._selection]
            self.tap((b.rect[0]+b.rect[2])/2,(b.rect[1]+b.rect[3])/2)
        elif code==E.KEY_ESC:
            self.home()
        else:
            codes=(E.KEY_1,E.KEY_2,E.KEY_3,E.KEY_4,E.KEY_5,E.KEY_6)
            if code in codes:
                items=[b for b in self.buttons if b.rect[1]>=70 and b.rect[3]<280 and b.rect[3]-b.rect[1]>50]
                index=codes.index(code)
                if index<len(items):
                    b=items[index]
                    self.tap((b.rect[0]+b.rect[2])/2,(b.rect[1]+b.rect[3])/2)

    def render(self):
        if self._splash_pending and self.splash_until!=0:
            frame=render_splash(0)
            self.splash_until=time.monotonic()+SPLASH_SECONDS
            self._splash_pending=False
            logging.info('Native splash phase started: %.1f seconds',SPLASH_SECONDS)
            self.alerts.draw(frame)
            return frame
        frame=super().render()
        if self._selection is not None and time.monotonic()>=self.splash_until and self._selection<len(self.buttons):
            ImageDraw.Draw(frame).rounded_rectangle(self.buttons[self._selection].rect,radius=6,outline='#eaffee',width=2)
        self.alerts.draw(frame)
        return frame


def write_terminal_input(data, fifo='/tmp/kali-tft-input', expected_uid=None):
    """Write only to the existing kali-owned FIFO, never a symlink/regular file."""
    import errno
    import os
    import pwd
    import stat
    expected_uid=pwd.getpwnam('kali').pw_uid if expected_uid is None else expected_uid
    descriptor=os.open(fifo,os.O_WRONLY|os.O_NONBLOCK|os.O_NOFOLLOW)
    try:
        info=os.fstat(descriptor)
        if not stat.S_ISFIFO(info.st_mode) or info.st_uid!=expected_uid:
            raise OSError(errno.EPERM,'Terminal input is not the expected user-owned FIFO')
        os.write(descriptor,data)
    finally:
        os.close(descriptor)

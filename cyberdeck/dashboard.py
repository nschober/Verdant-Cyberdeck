"""Shared 480x320 touch UI rendered through desktop or explicit framebuffer backend."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
import logging
import queue
import textwrap
import time
from PIL import Image, ImageDraw, ImageFont
from . import pwnagotchi, wifi_recon, bluetooth, system_status, launchers
from .backend import run, installed
from .splash import render_splash, SPLASH_SECONDS

BG, PANEL, GREEN, WHITE = '#07140f', '#133326', '#67fa9f', '#ebfff2'
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD_FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
TITLE_SIZE = 19
BUTTON_SIZE = 15
SMALL_BUTTON_SIZE = 12

@dataclass
class Button:
    label: str
    rect: tuple
    action: object

class Dashboard:
    def __init__(self, close=lambda:None, framebuffer=False, log_path=None):
        self.log_path = Path(log_path) if log_path else Path(__file__).resolve().parents[1]/'logs/cyberdeck.log'
        self.close = close
        self.framebuffer = framebuffer
        self.pool = ThreadPoolExecutor(max_workers=3)
        self.events = queue.Queue()
        self.generation = 0
        self.buttons = []
        self.lines = []
        self.offset = 0
        self.title = 'VERDANT CYBERDECK'
        self.status = 'Checking network and Pwnagotchi…'
        self.next_status = 0
        self.status_busy = False
        self.busy = False
        self.splash_until = time.monotonic() + SPLASH_SECONDS
        self.items = None
        self.body = ''
        self.home()

    def shutdown(self):
        self.pool.shutdown(wait=False, cancel_futures=True)
        logging.info('Clean dashboard exit; no services stopped')
        self.close()

    def reset(self, title):
        self.generation += 1
        self.title = title
        self.buttons = [Button('BACK', (6,281,108,316), self.home),
                        Button('HOME',(114,281,216,316),self.home),
                        Button('EXIT',(372,281,474,316),self.shutdown)]
        self.lines = []
        self.items = None
        self.offset = 0
        self.busy = False

    def grid(self, title, items):
        self.reset(title)
        self.items = items
        for i,(label,callback) in enumerate(items[:6]):
            x,y = 6+(i%2)*237, 75+(i//2)*65
            self.buttons.append(Button(label,(x,y,x+231,y+58),callback))

    def home(self):
        self.grid('VERDANT CYBERDECK',[
            ('WI-FI RECON',self.wifi),('PWNAGOTCHI',self.pwn),
            ('NETWORK',lambda:self.tools('NETWORK')),('WIRELESS',lambda:self.tools('WIRELESS')),
            ('BLUETOOTH',self.bt),('TRAFFIC / WEB',lambda:self.tools('TRAFFIC / WEB'))])
        self.buttons.append(Button('SYSTEM',(222,281,366,316),self.system))

    def text(self, title, content, controls=()):
        self.reset(title)
        self.set_content(content)
        for i,(label,action) in enumerate(controls[:2]):
            x = 6+i*237
            self.buttons.append(Button(label,(x,72,x+231,107),action))
        self.buttons += [Button('UP',(384,111,474,148),lambda:self.scroll(-7)),
                         Button('DOWN',(384,232,474,273),lambda:self.scroll(7))]

    def set_content(self, content):
        self.body = str(content)
        self.lines = []
        font=ImageFont.truetype(FONT,12)
        for line in self.body.expandtabs(2).splitlines():
            current=''
            for char in line:
                if font.getlength(current+char)>366:
                    self.lines.append(current)
                    current=''
                current+=char
            self.lines.append(current)
        self.offset = 0

    def scroll(self, amount):
        self.offset = max(0,min(max(0,len(self.lines)-10),self.offset+amount))

    def job(self, title, function, controls=()):
        self.text(title,'Working…',controls)
        token = self.generation
        self.busy = True
        def work():
            try:
                content = function()
            except Exception as exc:
                logging.exception('Action failed: %s',title)
                content = 'ERROR: '+str(exc)
            self.events.put((token,str(content)))
        self.pool.submit(work)

    def pwn(self):
        self.grid('PWNAGOTCHI',[(action.upper(),lambda a=action:self.confirm_service(a)) for action in ('start','stop','restart')]+[
            ('STATUS',lambda:self.job('PWNAGOTCHI STATUS',pwnagotchi.status)),
            ('LOGS',lambda:self.job('PWNAGOTCHI LOGS',pwnagotchi.logs)),
            ('CONFIGURATION',lambda:self.text('PWNAGOTCHI CONFIG',pwnagotchi.configuration()))])

    def confirm_service(self, action):
        warning = ('The existing service starts its radio dependencies. Wireless operations may begin and its TFT renderer may take the screen.' if action != 'stop' else 'Stops the existing Pwnagotchi service and its PartOf dependencies. Configuration and learned data are preserved.')
        if action!='stop' and pwnagotchi.background_enabled():
            warning='Starts the existing Pwnagotchi service in the background using its current radio/AI settings. Wireless operations may begin. Other dashboard and terminal windows stay open.'
        self.text(action.upper()+' PWNAGOTCHI?',warning,[('CONFIRM '+action.upper(),lambda:self.control(action)),('CANCEL',self.pwn)])

    def control(self, action):
        if self.framebuffer:
            self.handoff = pwnagotchi.control_args(action)
            self.shutdown()
            return
        try:
            launchers.service(action)
            self.text('SERVICE CONTROL','Authentication and command result are shown in the terminal. Use Status to verify the result.',[('STATUS',lambda:self.job('PWNAGOTCHI STATUS',pwnagotchi.status))])
        except Exception as exc:
            self.text('SERVICE ERROR',str(exc))

    def wifi(self):
        self.grid('WI-FI RECON',[
            ('ADAPTERS',lambda:self.job('WIRELESS ADAPTERS',wifi_recon.adapters)),
            ('SCAN / SIGNAL',lambda:self.wifi_scan('signal')),
            ('SCAN / SSID',lambda:self.wifi_scan('ssid')),
            ('CAPABILITIES',lambda:self.job('RADIO CAPABILITIES',wifi_recon.capabilities))])

    def wifi_scan(self, order):
        self.job('ACCESS POINTS',lambda:wifi_recon.scan(order),[('REFRESH',lambda:self.wifi_scan(order)),('SORT '+('SSID' if order=='signal' else 'SIGNAL'),lambda:self.wifi_scan('ssid' if order=='signal' else 'signal'))])

    def tools(self, group):
        items = [(name+(' [OK]' if installed(exe) else ' [MISSING]'), lambda n=name,e=exe,a=args:self.tool(n,e,a)) for name,exe,args in launchers.TOOLS[group]]
        if group=='WIRELESS':
            items.append(('ADAPTER STATUS',lambda:self.job('WIRELESS STATUS',wifi_recon.capabilities)))
        self.grid(group,items)

    def tool(self, name, exe, args):
        self.text(name,f"Executable: {installed(exe) or 'NOT INSTALLED'}\nLaunch opens the normal interface or useful help. No targets or radio changes are selected automatically.\nDesktop terminals use the current graphical session.\nFor authorized testing only.",[
            ('OPEN TERMINAL',lambda:self.launch(exe,args)),
            ('HELP ON SCREEN',lambda:self.job(name+' HELP',lambda:run([exe, *(args or ['--help'])],timeout=20).output))])

    def launch(self, exe, args):
        try:
            launchers.launch(exe,args)
        except Exception as exc:
            self.text('LAUNCH ERROR',str(exc))

    def bt(self):
        self.grid('BLUETOOTH',[
            ('CONTROLLERS',lambda:self.job('BLUETOOTH STATUS',bluetooth.status)),
            ('DISCOVER (8s)',lambda:self.job('BLUETOOTH DISCOVERY',bluetooth.discover)),
            ('DEVICE INFO',lambda:self.job('BLUETOOTH DEVICE INFO',bluetooth.details)),
            ('BLUETOOTHCTL',lambda:self.launch('bluetoothctl',[]))])

    def system(self):
        self.grid('SYSTEM',[
            ('TERMINAL / TOOLS',lambda:self.tools('SYSTEM')),
            ('SYSTEM INFO',lambda:self.job('SYSTEM INFORMATION',system_status.information)),
            ('INTERFACES / IP',lambda:self.job('NETWORK INTERFACES',lambda:run(['ip','address']).output)),
            ('DISPLAY INFO',lambda:self.text('DISPLAY INFORMATION',system_status.graphics()+'\nDesktop output and framebuffer are separate. No display configuration is changed.')),
            ('APP LOGS',lambda:self.text('APPLICATION LOG',self.log_path.read_text()[-20000:])),
            ('TOOL STATUS',lambda:self.text('INSTALLED TOOLS','\n'.join(f'{name}: {installed(exe) or "MISSING"}' for group in launchers.TOOLS.values() for name,exe,_ in group)))])

    def tick(self):
        while not self.events.empty():
            token,content = self.events.get()
            if token=='status':
                self.status=content
                self.status_busy=False
            elif token==self.generation:
                self.busy=False
                self.set_content(content)
        if time.monotonic()>=self.next_status and not self.status_busy:
            self.next_status=time.monotonic()+15
            self.status_busy=True
            def update():
                try:
                    network=system_status.summary().splitlines()
                    content=network[0]+'\n'+(' / '.join(network[1:])[:75])+'\nPwn: '+pwnagotchi.state()
                except Exception as exc:
                    content='Status unavailable: '+str(exc)
                self.events.put(('status',content))
            self.pool.submit(update)

    def tap(self,x,y):
        if time.monotonic()<self.splash_until:
            return
        for button in self.buttons:
            a,b,c,d=button.rect
            if a<=x<=c and b<=y<=d:
                try:
                    button.action()
                except Exception as exc:
                    logging.exception('Button failed')
                    self.text('ERROR',str(exc))
                return

    def render(self):
        im=Image.new('RGB',(480,320),BG)
        draw=ImageDraw.Draw(im)
        fonts={size:ImageFont.truetype(FONT,size) for size in (11,12,14,17)}
        if time.monotonic()<self.splash_until:
            remaining=self.splash_until-time.monotonic()
            return render_splash(1.0 if remaining>10 else 1.0-remaining/SPLASH_SECONDS)
        title_font=ImageFont.truetype(BOLD_FONT,TITLE_SIZE)
        title=self.title
        while title_font.getlength(title)>460:
            title=title[:-2]+'…' if title.endswith('…') else title[:-1]+'…'
        bounds=draw.textbbox((0,0),title,font=title_font)
        draw.text(((480-(bounds[2]-bounds[0]))/2-bounds[0],2),title,font=title_font,fill=GREEN)
        # Keep three short status lines inside the header.
        status=self.status.splitlines()
        for i,line in enumerate(status[:3]):
            while fonts[11].getlength(line)>461:
                line=line[:-1]
            draw.text((8,28+i*13),line,font=fonts[11],fill=WHITE)
        for button in self.buttons:
            draw.rounded_rectangle(button.rect,radius=6,fill=PANEL,outline='#28513c')
            x1,y1,x2,y2=button.rect
            label=button.label
            size=BUTTON_SIZE if len(label)<23 else SMALL_BUTTON_SIZE
            button_font=ImageFont.truetype(BOLD_FONT,size)
            box=draw.textbbox((0,0),label,font=button_font)
            draw.text(((x1+x2-(box[2]-box[0]))/2-box[0],(y1+y2-(box[3]-box[1]))/2-box[1]),label,font=button_font,fill=GREEN)
        if self.items is None:
            for i,line in enumerate(self.lines[self.offset:self.offset+10]):
                draw.text((8,112+i*16),line,font=fonts[12],fill=WHITE)
            draw.text((387,168),f'{self.offset+1}/{len(self.lines)}',font=fonts[11],fill=GREEN)
        return im

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
from .rendering import font as cached_font
from . import rf
from .paths import log_directory
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
        self.log_path = Path(log_path) if log_path else log_directory()/'cyberdeck.log'
        self.close = close
        self.framebuffer = framebuffer
        self.pool = ThreadPoolExecutor(max_workers=3)
        self.events = queue.Queue()
        self.generation = 0
        self.buttons = []
        self.lines = []
        self.line_colors = []
        self.offset = 0
        self.title = 'VERDANT CYBERDECK'
        self.status = 'Checking network and Pwnagotchi…'
        self.next_status = 0
        self.status_busy = False
        self.busy = False
        self.splash_until = float("inf")
        self.auth_target = None
        self.password = ""
        self.auth_shift = False
        self.auth_busy = False
        self.auth_message = "Kali login password"
        self.items = None
        self.body = ''
        self.history = []
        self.restoring = False
        self.home()

    def shutdown(self):
        if self.mayhem_remote:self.mayhem_remote.close()
        self.pool.shutdown(wait=False, cancel_futures=True)
        logging.info('Clean dashboard exit; no services stopped')
        self.close()

    def reset(self, title):
        if self.buttons and title != self.title and not self.restoring:
            self.history.append({key: getattr(self, key) for key in
                                 ('title', 'buttons', 'lines', 'line_colors', 'items', 'offset', 'body', 'pwn_screen')})
        remote=getattr(self,'mayhem_remote',None)
        if remote is not None:remote.close()
        self.mayhem_remote=None
        self.pwn_screen = False
        self.password = ''
        self.auth_target = None
        self.auth_busy = False
        self.generation += 1
        self.title = title
        self.buttons = [Button('BACK', (6,281,108,316), self.back),
                        Button('MAIN MENU',(114,281,279,316),self.home)]
        self.lines = []
        self.items = None
        self.offset = 0
        self.busy = False

    def back(self):
        if not self.history:
            return self.home()
        previous = self.history.pop()
        self.restoring = True
        try:
            self.reset(previous['title'])
            if previous['title'] == 'MAYHEM LIVE':
                # A live remote is closed when leaving its page; reconnect on return.
                self.open_mayhem()
            else:
                for key, value in previous.items():
                    setattr(self, key, value)
        finally:
            self.restoring = False

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
        self.buttons=[button for button in self.buttons if button.label not in ('BACK','MAIN MENU')]
        self.buttons.append(Button('RF TOOLS',(6,281,279,316),self.rf_menu))
        self.buttons.append(Button('SYSTEM',(285,281,474,316),lambda:self.protect(self.system)))
        self.history.clear()

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
        self.line_colors = []
        colors = getattr(content, 'colors', [])
        position = 0
        font=cached_font(FONT,12)
        for raw_line in self.body.splitlines(keepends=True):
            line = raw_line.rstrip('\r\n')
            current=''
            current_colors=[]
            column=0
            for index, char in enumerate(line):
                color=colors[position+index] if position+index<len(colors) else None
                expanded=' '*(2-column%2) if char=='\t' else char
                column+=len(expanded)
                for glyph in expanded:
                    if font.getlength(current+glyph)>366:
                        self.lines.append(current)
                        self.line_colors.append(current_colors)
                        current=''
                        current_colors=[]
                    current+=glyph
                    current_colors.append(color or WHITE)
            self.lines.append(current)
            self.line_colors.append(current_colors)
            position+=len(raw_line)
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
            self.events.put((token,content))
        self.pool.submit(work)

    def pwn(self):
        running=pwnagotchi.running()
        self.grid('PWNAGOTCHI',[(('OPEN' if running else 'START'),self.open_pwn_screen if running else lambda:self.control('start'))]+[(action.upper(),lambda a=action:self.control(a)) for action in ('stop','restart')]+[
            ('STATUS',lambda:self.job('PWNAGOTCHI STATUS',pwnagotchi.status)),
            ('LOGS',lambda:self.job('PWNAGOTCHI LOGS',pwnagotchi.logs)),
            ('CONFIGURATION',lambda:self.protect(lambda:self.text('PWNAGOTCHI CONFIG',pwnagotchi.configuration())))])

    def open_pwn_screen(self):
        self.reset('PWNAGOTCHI LIVE')
        self.pwn_screen = True
        self.buttons = [Button('MAIN MENU',(6,281,172,316),self.home),
                        Button('PWN MENU',(178,281,322,316),self.pwn),
                        Button('SETTINGS',(328,281,474,316),lambda:self.protect(lambda:self.text('PWNAGOTCHI CONFIG',pwnagotchi.configuration())))]

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

    def rf_menu(self):
        self.grid('RF TOOLS',[
            ('RF HARDWARE',lambda:self.job('RF HARDWARE',rf.hardware)),
            ('SDR / SPECTRUM',lambda:self.tools('RF SPECTRUM')),
            ('SUB-GHZ / PROTOCOLS',lambda:self.tools('RF PROTOCOLS')),
            ('GSM TOOLS',lambda:self.tools('RF GSM')),
            ('DEVICE / RX / TX',lambda:self.tools('RF DEVICES')),
            ('MAYHEM / PORTAPACK',self.mayhem_menu)])

    def mayhem_menu(self):
        from .mayhem import devices
        found=devices()
        self.text('MAYHEM / PORTAPACK',('Detected: '+', '.join(found)) if found else 'No Mayhem USB serial device detected. Connect the powered PortaPack with a data USB cable and keep it in normal Mayhem mode. Firmware must support info and screenframeshort.',[
            ('CONNECT / OPEN',self.open_mayhem),('REFRESH DEVICES',self.mayhem_menu)])

    def open_mayhem(self):
        from .mayhem import devices,Remote
        found=devices()
        if len(found)!=1:
            self.text('MAYHEM USB','Connect exactly one Mayhem PortaPack USB device, then Refresh Devices.',[('REFRESH DEVICES',self.mayhem_menu)])
            return
        self.reset('MAYHEM LIVE')
        self.mayhem_remote=Remote(found[0])
        remote=self.mayhem_remote
        self.buttons=[Button('MAIN MENU',(6,281,210,316),self.home),Button('RF TOOLS',(216,281,474,316),self.rf_menu)]
        for label,rect,code in [('UP',(318,45,394,85),4),('LEFT',(240,90,314,130),2),('OK',(320,90,394,130),5),('RIGHT',(400,90,474,130),1),('DOWN',(318,135,394,175),3),('ROTATE -',(240,185,354,225),7),('ROTATE +',(360,185,474,225),8)]:
            self.buttons.append(Button(label,rect,lambda c=code:remote.button(c)))
        self.buttons.append(Button('REFRESH SCREEN',(240,235,474,273),lambda:remote.enqueue('refresh')))

    def wifi(self):
        self.grid('WI-FI RECON',[
            ('ADAPTERS',lambda:self.job('WIRELESS ADAPTERS',wifi_recon.adapters)),
            ('SCAN / SIGNAL',lambda:self.wifi_scan('signal')),
            ('SCAN / SSID',lambda:self.wifi_scan('ssid')),
            ('CAPABILITIES',lambda:self.job('RADIO CAPABILITIES',wifi_recon.capabilities))])

    def wifi_scan(self, order):
        self.job('ACCESS POINTS',lambda:wifi_recon.scan(order),[('REFRESH',lambda:self.wifi_scan(order)),('SORT '+('SSID' if order=='signal' else 'SIGNAL'),lambda:self.wifi_scan('ssid' if order=='signal' else 'signal'))])

    def tools(self, group):
        items = [(name+(' [OK]' if (rf.tool_path(exe) if group.startswith('RF ') else installed(exe)) else ' [MISSING]'), lambda n=name,e=exe,a=args:self.tool(n,e,a)) for name,exe,args in launchers.TOOLS[group]]
        if group=='WIRELESS':
            items.append(('ADAPTER STATUS',lambda:self.job('WIRELESS STATUS',wifi_recon.capabilities)))
        self.grid(group,items)

    def tool(self, name, exe, args):
        self.text(name,f"Executable: {rf.tool_path(exe) or 'NOT INSTALLED'}\nLaunch opens the normal interface or useful help. No targets or radio changes are selected automatically.\nDesktop terminals use the current graphical session.\nFor authorized testing only.",[
            ('OPEN DESKTOP GUI' if exe in rf.GUI else 'OPEN TERMINAL',lambda:self.launch(exe,args)),
            ('HARDWARE INFO' if exe in rf.GUI else 'HELP IN TERMINAL' if self.framebuffer and rf.user_tool_path(exe) else 'HELP ON SCREEN',lambda:self.job('RF HARDWARE',rf.hardware) if exe in rf.GUI else self.launch(exe,args or ['--help']) if self.framebuffer and rf.user_tool_path(exe) else self.job(name+' HELP',lambda:run([rf.tool_path(exe) or exe, *(args or ['--help'])],timeout=20).output))])

    def launch(self, exe, args):
        try:
            if exe in rf.GUI:rf.launch_gui(exe)
            else:launchers.launch(exe,args)
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

    def protect(self, callback):
        # Compatibility hook: settings/configuration no longer require a password.
        return callback()

    def auth_keyboard(self):
        self.buttons = [Button('CANCEL',(6,281,150,316),self.home),
                        Button('UNLOCK',(330,281,474,316),self.submit_password),
                        Button('SHIFT',(156,281,240,316),self.toggle_shift),
                        Button('DELETE',(246,281,324,316),lambda:self.password_key('BACKSPACE'))]
        rows = ['1234567890','qwertyuiop','asdfghjkl;','zxcvbnm,./']
        shifted = ['!@#$%^&*()','QWERTYUIOP','ASDFGHJKL:','ZXCVBNM<>?']
        import string
        symbols=[string.punctuation[i:i+10] for i in range(0,40,10)]
        for row,keys in enumerate(symbols if self.auth_symbols else shifted if self.auth_shift else rows):
            for col,key in enumerate(keys):
                x,y=6+col*47,133+row*35
                self.buttons.append(Button(key,(x,y,x+44,y+32),lambda k=key:self.password_key(k)))
        self.buttons.append(Button('SPACE',(6,100,118,130),lambda:self.password_key(' ')))
        self.buttons.append(Button("QUOTE",(124,100,236,130),lambda:self.password_key(chr(34) if self.auth_shift else chr(39))))
        self.buttons.append(Button('SYMBOLS',(242,100,354,130),self.toggle_symbols))
        self.buttons.append(Button('- / _',(360,100,474,130),lambda:self.password_key('_' if self.auth_shift else '-')))

    def toggle_symbols(self):
        self.auth_symbols=not self.auth_symbols
        self.auth_keyboard()

    def toggle_shift(self):
        self.auth_shift=not self.auth_shift
        self.auth_keyboard()

    def password_key(self, key):
        if self.auth_busy:return
        if key=='BACKSPACE':self.password=self.password[:-1]
        elif len(self.password)<256:self.password+=key

    def submit_password(self):
        if self.auth_busy or not self.password:return
        from .authentication import authenticate
        secret=self.password;self.password=''
        self.auth_busy=True;self.auth_message='Checking login password…'
        token=self.generation
        def work():
            try:ok=authenticate('kali',secret)
            except Exception:ok=False
            self.events.put((('auth',token),ok))
        self.pool.submit(work)

    def enter_menu(self):
        self.splash_until=0
        self.home()

    def tick(self):
        while not self.events.empty():
            token,content = self.events.get()
            if isinstance(token,tuple) and token[0]=='auth':
                if token[1]==self.generation and self.auth_target:
                    self.auth_busy=False
                    callback=self.auth_target
                    if content:
                        self.auth_target=None
                        callback()
                    else:self.auth_message='Authentication failed. Try again.'
            elif isinstance(token,tuple) and token[0]=='service':
                if token[1]==self.generation:
                    self.busy=False
                    self.next_status=0
                    if token[3] and token[2] in ('start','restart'):self.open_pwn_screen()
                    else:self.set_content(content)
            elif token=='status':
                self.status=content
                self.status_busy=False
                if self.title=='PWNAGOTCHI':
                    for button in self.buttons:
                        if button.label in ('OPEN','START'):
                            running='Pwn: active /' in content or 'Pwn: activating /' in content
                            button.label='OPEN' if running else 'START'
                            button.action=self.open_pwn_screen if running else lambda:self.control('start')
            elif token==self.generation:
                self.busy=False
                self.set_content(content)
        if time.monotonic()>=self.splash_until and time.monotonic()>=self.next_status and not self.status_busy:
            self.next_status=time.monotonic()+30
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
        if self.mayhem_remote and x<230 and y<280:
            self.mayhem_remote.map_touch(x,y)
            return
        if time.monotonic()<self.splash_until:
            if 95<=x<=385 and 275<=y<=311:self.enter_menu()
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

    def visual_key(self):
        return (self.generation,self.title,self.status,self.body,self.offset,self.busy,
                self.splash_until,self.password,self.auth_message,self.auth_busy,
                (self.mayhem_remote.revision,self.mayhem_remote.status) if self.mayhem_remote else None,
                tuple((b.label,b.rect) for b in self.buttons))

    def render(self):
        im=Image.new('RGB',(480,320),BG)
        draw=ImageDraw.Draw(im)
        fonts={size:cached_font(FONT,size) for size in (11,12)}
        if time.monotonic()<self.splash_until:
            remaining=self.splash_until-time.monotonic()
            return render_splash(1.0 if remaining>10 else 1.0-remaining/SPLASH_SECONDS)
        if self.mayhem_remote:self.mayhem_remote.draw(im)
        if getattr(self,'pwn_screen',False):
            from .pwn_screen import draw_screen
            draw_screen(im)
        title_font=cached_font(BOLD_FONT,TITLE_SIZE)
        title=self.title
        while title_font.getlength(title)>460:
            title=title[:-2]+'…' if title.endswith('…') else title[:-1]+'…'
        bounds=draw.textbbox((0,0),title,font=title_font)
        if not getattr(self,'pwn_screen',False) and not self.mayhem_remote:draw.text(((480-(bounds[2]-bounds[0]))/2-bounds[0],2),title,font=title_font,fill=GREEN)
        # Keep three short status lines inside the header.
        status=self.status.splitlines()
        for i,line in enumerate([] if getattr(self,'pwn_screen',False) or self.mayhem_remote else status[:3]):
            while fonts[11].getlength(line)>461:
                line=line[:-1]
            draw.text((8,28+i*13),line,font=fonts[11],fill=WHITE)
        for button in self.buttons:
            draw.rounded_rectangle(button.rect,radius=6,fill=PANEL,outline='#28513c')
            x1,y1,x2,y2=button.rect
            label=button.label
            size=BUTTON_SIZE if len(label)<23 else SMALL_BUTTON_SIZE
            button_font=cached_font(BOLD_FONT,size)
            box=draw.textbbox((0,0),label,font=button_font)
            draw.text(((x1+x2-(box[2]-box[0]))/2-box[0],(y1+y2-(box[3]-box[1]))/2-box[1]),label,font=button_font,fill=GREEN)
        if self.auth_target:
            draw.rectangle((6,69,474,97),fill=BG)
            draw.text((10,70),self.auth_message,font=fonts[12],fill=WHITE)
            draw.text((260,70),'*'*min(22,len(self.password)),font=fonts[12],fill=GREEN)
        elif self.items is None and not getattr(self,'pwn_screen',False) and not self.mayhem_remote:
            for i,line in enumerate(self.lines[self.offset:self.offset+10]):
                colors=self.line_colors[self.offset+i]
                start=0
                while start<len(line):
                    end=start+1
                    while end<len(line) and colors[end]==colors[start]:end+=1
                    draw.text((8+fonts[12].getlength(line[:start]),112+i*16),line[start:end],font=fonts[12],fill=colors[start])
                    start=end
            draw.text((387,168),f'{self.offset+1}/{len(self.lines)}',font=fonts[11],fill=GREEN)
        return im

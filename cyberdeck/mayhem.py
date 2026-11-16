"""Mayhem USB remote display and explicit UI input; firmware stays on PortaPack.

Protocol reference: official portapack-mayhem MayhemHub and Mayhem v2.4.0
usb_serial_shell.cpp. No third-party application code is bundled here.
"""
import fcntl
import os
from pathlib import Path
import queue
import select
import stat
import termios
import threading
import time
import tty
from PIL import Image,ImageOps,ImageDraw
from .rendering import font


def devices(root=Path('/sys/class/tty')):
    found=[]
    for node in root.glob('ttyACM*'):
        try:
            for parent in (node/'device').resolve().parents:
                if (parent/'idVendor').exists():
                    if (parent/'idVendor').read_text().strip().lower()=='1d50' and (parent/'idProduct').read_text().strip().lower()=='6018':found.append('/dev/'+node.name)
                    break
        except OSError:continue
    return found


def decode_screen(data):
    lines=data.split(b'\r\n')
    for width,height in ((240,320),(320,480)):
        rows=[line for line in lines if len(line)==width and all(32<=value<=95 for value in line)]
        if len(rows)!=height:continue
        rgb=bytearray(width*height*3);offset=0
        for row in rows:
            for pixel in row:
                value=pixel-32
                rgb[offset]=((value>>4)&3)*64;rgb[offset+1]=((value>>2)&3)*64;rgb[offset+2]=(value&3)*64;offset+=3
        return Image.frombytes('RGB',(width,height),bytes(rgb))
    raise ValueError('Firmware did not return a supported 240x320 or 320x480 screen frame')


class SerialLink:
    def __init__(self,path):
        if path not in devices():raise RuntimeError('Select a detected Mayhem USB device')
        self.fd=os.open(path,os.O_RDWR|os.O_NOCTTY|os.O_NONBLOCK|os.O_NOFOLLOW)
        try:
            if not stat.S_ISCHR(os.fstat(self.fd).st_mode):raise ValueError('Expected serial device')
            self.saved=termios.tcgetattr(self.fd)
            fcntl.ioctl(self.fd,termios.TIOCEXCL)
            tty.setraw(self.fd)
            settings=termios.tcgetattr(self.fd);settings[4]=settings[5]=termios.B115200
            termios.tcsetattr(self.fd,termios.TCSANOW,settings)
        except Exception:os.close(self.fd);raise
    def command(self,text):
        if '\n' in text or '\r' in text or len(text)>80:raise ValueError('Invalid serial command')
        termios.tcflush(self.fd,termios.TCIFLUSH)
        payload=(text+'\r').encode('ascii');sent=0;deadline=time.monotonic()+3
        while sent<len(payload):
            if time.monotonic()>deadline:raise TimeoutError('Mayhem serial write timeout')
            if select.select([], [self.fd], [],0.2)[1]:
                try:sent+=os.write(self.fd,payload[sent:])
                except BlockingIOError:pass
        data=bytearray();deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            if not select.select([self.fd],[],[],0.2)[0]:continue
            try:part=os.read(self.fd,16384)
            except BlockingIOError:continue
            if not part:raise RuntimeError('Mayhem USB disconnected')
            data.extend(part)
            if len(data)>256000:raise ValueError('Mayhem response exceeds limit')
            if data.endswith(b'ch> '):return bytes(data)
        raise TimeoutError('Mayhem did not respond; check firmware version and USB mode')
    def close(self):
        try:termios.tcsetattr(self.fd,termios.TCSANOW,self.saved)
        except OSError:pass
        try:fcntl.ioctl(self.fd,termios.TIOCNXCL)
        finally:os.close(self.fd)


class Remote:
    def __init__(self,path,link_factory=SerialLink,interval=2):
        self.path=path;self.factory=link_factory;self.interval=interval
        self.commands=queue.Queue(maxsize=32);self.stop=threading.Event()
        self.frame=None;self.revision=0;self.status='Connecting to Mayhem…'
        self.thread=threading.Thread(target=self.run,daemon=True,name='Mayhem USB');self.thread.start()
    def button(self,value):
        if value not in (1,2,3,4,5,7,8):raise ValueError('Unsupported UI button')
        self.enqueue('button '+str(value))
    def touch(self,x,y):
        if self.frame is None:return
        if not 0<=x<self.frame.width or not 0<=y<self.frame.height:return
        self.enqueue(f'touch {int(x)} {int(y)}')
    def enqueue(self,text):
        try:self.commands.put_nowait(text)
        except queue.Full:self.status='Input queue full; wait for the device'
    def close(self):self.stop.set()
    def run(self):
        link=None
        try:
            link=self.factory(self.path)
            info=link.command('info').decode(errors='replace')
            if 'mayhem' not in info.lower():raise RuntimeError('Connected device did not identify as Mayhem')
            self.status=next((line.strip() for line in info.splitlines() if 'Mayhem Version:' in line),'Mayhem USB connected')
            next_frame=0
            while not self.stop.is_set():
                try:
                    command=self.commands.get(timeout=max(0,min(0.2,next_frame-time.monotonic())))
                    if command!='refresh':link.command(command)
                    next_frame=0
                except queue.Empty:pass
                if time.monotonic()>=next_frame and not self.stop.is_set():
                    image=decode_screen(link.command('screenframeshort'))
                    if self.frame is None or self.frame.size!=image.size or self.frame.tobytes()!=image.tobytes():
                        self.frame=image;self.revision+=1
                    next_frame=time.monotonic()+self.interval
        except Exception as exc:self.status=str(exc);self.revision+=1
        finally:
            if link is not None:link.close()
    def draw(self,frame):
        draw=ImageDraw.Draw(frame);label=font('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',19)
        draw.text((270,4),'MAYHEM',font=label,fill='#67fa9f')
        if self.frame:
            fitted=ImageOps.contain(self.frame,(224,280));frame.paste(fitted,((230-fitted.width)//2,0))
        else:
            import textwrap
            small=font('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',13)
            for i,line in enumerate(textwrap.wrap(self.status,28)[:10]):draw.text((8,40+i*18),line,font=small,fill='#ebfff2')
    def map_touch(self,x,y):
        if self.frame is None:return
        fitted=ImageOps.contain(self.frame,(224,280));left=(230-fitted.width)//2
        if left<=x<left+fitted.width and 0<=y<fitted.height:self.touch((x-left)*self.frame.width/fitted.width,y*self.frame.height/fitted.height)

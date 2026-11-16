"""Read-only capture-event monitor and shared TFT/desktop notification rendering."""
import argparse
from collections import deque
import fcntl
import grp
import hashlib
import json
import logging
import math
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import tempfile
import time
from PIL import ImageDraw, ImageFont
from .rendering import font as cached_font

STATE = Path('/run/verdant-cyberdeck/handshake.json')
LIFETIME = 8.0
CARD = (20, 73, 460, 257)
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
REGULAR = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
ANSI = re.compile(r'\x1b\[[0-?]*[ -/]*[@-~]')
CAPTURE = re.compile(r'^(?:\[[^\]\r\n]{1,100}\]\s*)*(?::\s*)?(!!! captured new handshake(?: on channel|:).+?!!!)\s*$',re.I)

def clean(text, limit=260):
    return ''.join(c for c in ANSI.sub('',str(text)) if c.isprintable())[:limit]

def capture_event(record, now=None):
    if not isinstance(record,dict):return None
    message=record.get('MESSAGE','')
    if not isinstance(message,str) or len(message)>4096:return None
    match=CAPTURE.match(' '.join(ANSI.sub('',message).splitlines()).strip())
    if not match:return None
    cursor=record.get('__CURSOR')
    if not isinstance(cursor,str) or not cursor or len(cursor)>4096:return None
    timestamp=time.time() if now is None else now
    return {'version':1,'kind':'handshake','id':hashlib.sha256(cursor.encode()).hexdigest(),
            'timestamp':timestamp,'title':'HANDSHAKE CAPTURED',
            'detail':clean(match.group(1).strip('! ')),
            'source':'Capture event reported by Pwnagotchi'}

class EventStore:
    def __init__(self,path=STATE,group_id=None):
        self.path=Path(path)
        self.group_id=group_id
    def publish(self,event):
        parent=self.path.parent
        if parent.is_symlink() or self.path.is_symlink():raise ValueError('Alert state must not use symlinks')
        parent.mkdir(parents=True,exist_ok=True,mode=0o750)
        if os.geteuid()==0:
            gid=self.group_id if self.group_id is not None else grp.getgrnam('kali').gr_gid
            os.chown(parent,0,gid);parent.chmod(0o750)
        else:gid=os.getgid()
        fd,temporary=tempfile.mkstemp(prefix='.handshake-',dir=parent)
        try:
            with os.fdopen(fd,'w') as stream:
                json.dump(event,stream);stream.flush();os.fsync(stream.fileno())
                os.fchmod(stream.fileno(),0o640)
                if os.geteuid()==0:os.fchown(stream.fileno(),0,gid)
            os.replace(temporary,self.path)
        finally:
            if os.path.exists(temporary):os.unlink(temporary)

class AlertReader:
    def __init__(self,path=STATE,expected_uid=0):
        self.path=Path(path);self.expected_uid=expected_uid;self.dismissed=None
    def current(self,now=None):
        try:
            fd=os.open(self.path,os.O_RDONLY|os.O_NOFOLLOW)
            try:
                info=os.fstat(fd)
                if not stat.S_ISREG(info.st_mode) or info.st_uid!=self.expected_uid or info.st_size>8192:return None
                event=json.loads(os.read(fd,8192))
            finally:os.close(fd)
            age=(time.time() if now is None else now)-float(event['timestamp'])
            if not math.isfinite(age) or not -2<=age<LIFETIME:return None
            if event.get('version')!=1 or event.get('kind') not in ('handshake','test'):return None
            if not isinstance(event.get('id'),str) or len(event['id'])>128 or event['id']==self.dismissed:return None
            return event
        except (OSError,ValueError,KeyError,TypeError):return None
    def dismiss(self):
        event=self.current()
        if event:self.dismissed=event['id']
    def draw(self,image):
        event=self.current()
        if not event:return False
        draw=ImageDraw.Draw(image)
        draw.rectangle((14,67,466,263),fill='#020705')
        draw.rounded_rectangle(CARD,radius=12,fill='#123324',outline='#91ffb4',width=3)
        title='TEST NOTIFICATION' if event['kind']=='test' else 'HANDSHAKE CAPTURED'
        font=cached_font(BOLD,19);body=cached_font(REGULAR,13)
        box=draw.textbbox((0,0),title,font=font)
        draw.text(((480-(box[2]-box[0]))/2,88),title,font=font,fill='#a0ffc1')
        text=clean(event.get('detail',''));lines=[];line=''
        for char in text:
            if body.getlength(line+char)>398:lines.append(line);line=''
            line+=char
        lines.append(line)
        for i,line in enumerate(lines[:4]):draw.text((39,126+i*18),line,font=body,fill='#f0fff4')
        footer=('Display test • no capture' if event['kind']=='test' else 'Reported by Pwnagotchi')
        draw.text((39,229),footer,font=cached_font(REGULAR,11),fill='#a9c8b4')
        return True

class JournalMonitor:
    def __init__(self,store=None):
        self.store=store or EventStore();self.ids=deque(maxlen=512);self.running=True;self.process=None
    def accept(self,record):
        event=capture_event(record)
        if not event or event['id'] in self.ids:return False
        self.store.publish(event);self.ids.append(event['id'])
        logging.info('Published Pwnagotchi capture notification %s',event['id'][:12])
        return True
    def stop(self,*_):
        self.running=False
        if self.process and self.process.poll() is None:self.process.terminate()
    def run(self):
        signal.signal(signal.SIGTERM,self.stop);signal.signal(signal.SIGINT,self.stop)
        self.process=subprocess.Popen(['journalctl','--follow','--lines=0','--unit=pwnagotchi.service','--output=json','--no-pager'],stdout=subprocess.PIPE,text=True)
        if not self.running:self.stop()
        try:
            for line in self.process.stdout:
                if not self.running:break
                try:self.accept(json.loads(line))
                except (ValueError,TypeError,OSError) as exc:logging.warning('Alert event rejected: %s',type(exc).__name__)
        finally:
            self.stop()
            try:self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait()
            self.process.stdout.close()
        if self.running:raise RuntimeError('Journal event stream exited unexpectedly')

def desktop_notifications():
    import tkinter as tk
    if not os.environ.get('DISPLAY'):raise RuntimeError('Desktop notifications require the existing graphical session DISPLAY')
    lockroot=Path(os.environ.get('XDG_RUNTIME_DIR',str(Path.home()/'.cache')))
    lockroot.mkdir(parents=True,exist_ok=True)
    lock=(lockroot/'verdant-alerts.lock').open('w')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close();return
    try:root=tk.Tk()
    except Exception:
        lock.close();raise
    root.withdraw();reader=AlertReader();popup=None;last_id=None
    def poll():
        nonlocal popup,last_id
        event=reader.current()
        if event and event['id']!=last_id:
            last_id=event['id']
            if popup is not None:popup.destroy()
            popup=tk.Toplevel(root);popup.overrideredirect(True);popup.attributes('-topmost',True)
            width,height=440,190
            x=(root.winfo_screenwidth()-width)//2;y=(root.winfo_screenheight()-height)//2
            popup.geometry(f'{width}x{height}+{x}+{y}');popup.configure(bg='#123324',highlightbackground='#91ffb4',highlightthickness=3)
            title='TEST NOTIFICATION' if event['kind']=='test' else 'HANDSHAKE CAPTURED'
            tk.Label(popup,text=title,bg='#123324',fg='#a0ffc1',font=('DejaVu Sans',16,'bold')).pack(pady=(15,8))
            tk.Label(popup,text=clean(event.get('detail','')),wraplength=400,bg='#123324',fg='#f0fff4',font=('DejaVu Sans',11)).pack(fill='both',expand=True,padx=12)
            def dismiss():
                nonlocal popup
                reader.dismiss()
                if popup is not None:popup.destroy();popup=None
            tk.Button(popup,text='DISMISS',command=dismiss,font=('DejaVu Sans',15,'bold'),bg='#22543a',fg='#f0fff4').pack(pady=8)
            popup.lift()
        elif not event and popup is not None:popup.destroy();popup=None
        root.after(250,poll)
    try:
        poll();root.mainloop()
    finally:lock.close()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    action=parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--monitor',action='store_true');action.add_argument('--desktop',action='store_true');action.add_argument('--test-alert',action='store_true')
    args=parser.parse_args()
    if args.desktop:desktop_notifications()
    elif args.monitor:
        logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
        JournalMonitor().run()
    else:
        if os.geteuid()!=0:parser.error('Synthetic alert publishing requires host sudo')
        EventStore().publish({'version':1,'kind':'test','id':'test-'+str(time.time_ns()),'timestamp':time.time(),'detail':'Synthetic display test. No handshake was captured.'})

if __name__=='__main__':main()

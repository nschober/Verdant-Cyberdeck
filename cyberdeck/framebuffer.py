"""Optional direct TFT backend. Does not change modes, drivers, VTs or input grabs."""
import fcntl
import mmap
import os
from pathlib import Path
import select
import signal
import struct
import time
from .backend import run as command
from .dashboard import Dashboard

OWNERS=('tft-launcher.service','tft-terminal.service','tft-recon.service','pwnagotchi.service')

def available_framebuffer():
    for service in OWNERS:
        state=command(['systemctl','show',service,'--property=ActiveState','--value'])
        if state.code or state.output not in ('inactive','failed'):
            raise RuntimeError(f'Refusing framebuffer access: {service} is active or its state is unknown. Existing TFT services are never stopped automatically.')
    for fb in Path('/sys/class/graphics').glob('fb[0-9]*'):
        if 'ili9488' in (fb/'name').read_text().lower():
            return Path('/dev')/fb.name
    raise RuntimeError('ILI9488 framebuffer not detected')

def run():
    from evdev import InputDevice,list_devices,ecodes as E
    device=available_framebuffer()
    fd=os.open(device,os.O_RDWR)
    memory=None
    devices=[]
    app=None
    try:
        # fb_var_screeninfo: xres,yres,xres_virtual,yres_virtual,xoffset,yoffset,bpp,...
        var=bytearray(160)
        fcntl.ioctl(fd,0x4600,var,True)
        values=struct.unpack_from('10I',var)
        if values[:2]!=(480,320) or values[4:7]!=(0,0,32):
            raise RuntimeError('TFT must already be 480x320, zero offset, 32 bits. No display settings changed.')
        red=struct.unpack_from('3I',var,32)
        green=struct.unpack_from('3I',var,44)
        blue=struct.unpack_from('3I',var,56)
        if (red,green,blue)!=((16,8,0),(8,8,0),(0,8,0)):
            raise RuntimeError('Unsupported framebuffer pixel format')
        stride=int((Path('/sys/class/graphics')/device.name/'stride').read_text())
        if stride!=1920:
            raise RuntimeError('Unexpected framebuffer stride; refusing to draw')
        for path in list_devices():
            dev=InputDevice(path)
            caps=dev.capabilities()
            abs_codes=dict(caps.get(E.EV_ABS,[]))
            if E.ABS_X in abs_codes and E.ABS_Y in abs_codes:
                devices.append(dev)
            else:
                dev.close()
        if not devices:
            raise RuntimeError('No accessible ABS_X/ABS_Y touchscreen. No inputs were grabbed or remapped.')
        memory=mmap.mmap(fd,stride*320)
        active=True
        def stop(*_):
            nonlocal active
            active=False
        previous={sig:signal.signal(sig,stop) for sig in (signal.SIGTERM,signal.SIGINT)}
        app=Dashboard(stop,framebuffer=True)
        points={dev.fd:[0,0,False] for dev in devices}
        while active:
            app.tick()
            memory[:]=app.render().tobytes('raw','BGRX')
            ready,_,_=select.select(devices,[],[],.1)
            for dev in ready:
                point=points[dev.fd]
                for event in dev.read():
                    if event.type==E.EV_ABS and event.code in (E.ABS_X,E.ABS_Y):
                        axis=0 if event.code==E.ABS_X else 1
                        info=dev.absinfo(event.code)
                        point[axis]=max(0,min((479,319)[axis],round((event.value-info.min)*(479,319)[axis]/max(1,info.max-info.min))))
                    elif event.type==E.EV_KEY and event.code==E.BTN_TOUCH:
                        if event.value==1:
                            point[2]=True
                        elif point[2]:
                            point[2]=False
                            app.tap(*point[:2])
        for sig,handler in previous.items():
            signal.signal(sig,handler)
    finally:
        if app:
            app.pool.shutdown(wait=False,cancel_futures=True)
        for dev in devices:
            dev.close()
        if memory is not None:
            memory.close()
        os.close(fd)
    if app and getattr(app,'handoff',None):
        result=command(['systemctl','--no-ask-password',*app.handoff[1:]],timeout=45)
        if result.code:
            raise RuntimeError('Service handoff failed: '+result.output)

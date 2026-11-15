"""Render the real Pwnagotchi canvas published by its runtime display bridge."""
import os
import stat
import time
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
PATH=Path('/run/verdant-cyberdeck/pwn-screen.png')
def draw_screen(frame,path=PATH,expected_uid=0):
    try:
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        with os.fdopen(fd,'rb') as stream:
            info=os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid!=expected_uid or info.st_size>2000000:raise ValueError('Untrusted screen frame')
            if time.time()-info.st_mtime>30:raise ValueError('Live screen has not updated in 30 seconds')
            with Image.open(stream) as image:
                if image.size!=(480,320):raise ValueError('Unexpected screen resolution')
                frame.paste(image.convert('RGB').resize((420,280)),(30,0))
        return True
    except (OSError,ValueError):
        draw=ImageDraw.Draw(frame);font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',15)
        draw.text((25,70),'PWNAGOTCHI LIVE SCREEN',font=font,fill='#67fa9f')
        draw.text((25,120),'Waiting for a live frame…',font=font,fill='#ebfff2')
        return False

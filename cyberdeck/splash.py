"""Original, code-rendered Verdant artwork; no third-party logos or fake telemetry."""
from functools import lru_cache
import math
from PIL import Image, ImageDraw, ImageFont

FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
MONO = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
SPLASH_SECONDS = 4.0

@lru_cache(maxsize=1)
def _artwork():
    scale = 3
    im = Image.new('RGB', (480*scale,320*scale), '#040b09')
    d = ImageDraw.Draw(im)
    def xy(points): return [(round(x*scale),round(y*scale)) for x,y in points]
    def line(points,fill,width=1): d.line(xy(points),fill=fill,width=round(width*scale),joint='curve')
    def text(point,value,size=12,fill='#edfdf3',font=FONT):
        d.text(xy([point])[0],value,font=ImageFont.truetype(font,size*scale),fill=fill)
    def box(bounds,fill=None,outline=None,width=1):
        d.rectangle(tuple(round(v*scale) for v in bounds),fill=fill,outline=outline,width=width*scale)
    def dot(x,y,r,fill):d.ellipse(tuple(round(v*scale) for v in (x-r,y-r,x+r,y+r)),fill=fill)
    for y in range(0,320,24):
        for x in range(0,480,24):dot(x,y,.55,'#153025')
    for x in range(280,490,28):line([(x,0),(x-130,170)],'#0b1b14')
    box((12,12,467,307),outline='#214033')
    for x,y,sx,sy in ((12,12,1,1),(467,12,-1,1),(12,307,1,-1),(467,307,-1,-1)):
        line([(x,y+14*sy),(x,y),(x+22*sx,y)],'#77f7a6',2)
    text((25,23),'V / FIELD SYSTEMS',10,'#8baf9a',MONO)
    text((345,23),'LOCAL CONTROL',9,'#77f7a6',MONO)
    text((22,61),'VERDANT',43,'#eefcf3',BOLD)
    text((25,111),'C Y B E R D E C K',15,'#77f7a6',BOLD)
    line([(25,146),(282,146)],'#29503c')
    line([(25,146),(92,146)],'#77f7a6',2)
    text((25,157),'NETWORK SECURITY DASHBOARD',11,'#8baf9a',MONO)
    cx,cy,r=392,99,51
    outer=[(cx+math.cos(math.radians(30+60*i))*r,cy+math.sin(math.radians(30+60*i))*r) for i in range(6)]
    d.polygon(xy(outer),fill='#0b2117',outline='#376a4c',width=scale)
    inner=[(cx+math.cos(math.radians(30+60*i))*(r-6),cy+math.sin(math.radians(30+60*i))*(r-6)) for i in range(6)]
    line(inner+[inner[0]],'#19422b')
    line([(367,77),(392,120),(417,77)],'#173c28',10)
    line([(367,77),(392,120),(417,77)],'#82ffa9',4)
    line([(374,77),(392,108),(410,77)],'#3b8754',1)
    for x,y in ((367,77),(417,77),(392,120)):dot(x,y,2.2,'#d5ffe0')
    line([(348,122),(333,132),(333,157),(312,157)],'#376a4c')
    dot(312,157,2,'#77f7a6')
    line([(436,78),(451,67),(451,49)],'#376a4c')
    dot(451,49,2,'#77f7a6')
    labels=[('PWNAGOTCHI','WI-FI RECON'),('NETWORK RECON','WIRELESS AUDITING'),('BLUETOOTH','PACKET ANALYSIS'),('WEB SECURITY','METASPLOIT')]
    for row,pair in enumerate(labels):
        y=191+20*row
        for column,label in enumerate(pair):
            x=25+column*224
            box((x,y+4,x+4,y+8),fill='#65d98b')
            text((x+12,y),label,11,'#d0e8d7',MONO)
    line([(25,280),(455,280)],'#214033')
    d.rounded_rectangle(tuple(round(v*scale) for v in (95,275,385,311)),radius=6*scale,fill='#143926',outline='#77f7a6',width=scale)
    text((150,283),'ENTER MAIN MENU',16,'#ebfff2',BOLD)
    return im.resize((480,320),Image.Resampling.LANCZOS)

def render_splash(progress=1.0):
    """Persistent welcome screen; progress retained for API compatibility."""
    return _artwork().copy()

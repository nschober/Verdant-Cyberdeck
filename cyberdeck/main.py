import argparse
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
from .dashboard import Dashboard

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description='Passive 480x320 Cyberdeck dashboard')
    parser.add_argument('--framebuffer',action='store_true',help='Explicit TFT backend; refuses existing TFT owners')
    parser.add_argument('--self-test',action='store_true',help='Exercise pages offscreen; never touch radios or services')
    parser.add_argument('--smoke-test',action='store_true',help='Open existing desktop display and exit after two seconds')
    args=parser.parse_args()
    (ROOT/'logs').mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO,handlers=[RotatingFileHandler(ROOT/'logs/cyberdeck.log',maxBytes=500000,backupCount=2)],format='%(asctime)s %(levelname)s %(message)s')
    logging.info('Starting dashboard: %s',args)
    if args.self_test:
        app=Dashboard()
        app.splash_until=0
        for page in (app.home,app.pwn,app.wifi,app.bt,app.system,lambda:app.tools('TRAFFIC / WEB')):
            page()
            assert app.render().size==(480,320)
        app.home()
        app.render().save(ROOT/'assets/dashboard.png')
        app.splash_until=float('inf')
        app.render().save(ROOT/'assets/splash.png')
        app.shutdown()
        print('Offscreen page rendering passed; hardware not exercised.')
        return
    try:
        if args.framebuffer:
            from .framebuffer import run
            run()
        else:
            desktop(args.smoke_test)
    except Exception as exc:
        logging.exception('Startup failed')
        print(f'Cyberdeck startup failed: {exc}\nSee {ROOT}/logs/cyberdeck.log',file=sys.stderr)
        raise SystemExit(1)

def desktop(smoke=False):
    import tkinter as tk
    from PIL import ImageTk
    # Inherit the actual login session. Never guess DISPLAY or start an X server.
    if not os.environ.get('DISPLAY'):
        raise RuntimeError('No DISPLAY in this session. Start after graphical login; the separate TFT requires --framebuffer and a free device.')
    root=tk.Tk()
    root.title('VERDANT CYBERDECK')
    root.geometry('480x320+0+0')
    root.resizable(False,False)
    if root.winfo_screenwidth()==480 and root.winfo_screenheight()==320:
        root.overrideredirect(True)
    canvas=tk.Canvas(root,width=480,height=320,highlightthickness=0)
    canvas.pack()
    app=Dashboard(root.destroy)
    root.protocol('WM_DELETE_WINDOW',app.shutdown)
    root.bind('<Escape>',lambda e:app.shutdown())
    canvas.bind('<Button-1>',lambda e:app.tap(e.x,e.y))
    canvas.bind('<Button-4>',lambda e:app.scroll(-3))
    canvas.bind('<Button-5>',lambda e:app.scroll(3))
    image_id=canvas.create_image(0,0,anchor='nw')
    def refresh():
        app.tick()
        canvas.photo=ImageTk.PhotoImage(app.render())
        canvas.itemconfigure(image_id,image=canvas.photo)
        root.after(100,refresh)
    refresh()
    if smoke:
        root.after(2000,app.shutdown)
    root.mainloop()

if __name__=='__main__':
    main()

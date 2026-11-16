import argparse
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
from . import __version__
from .dashboard import Dashboard
from .paths import log_directory,asset_directory

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description='Network Security Dashboard')
    parser.add_argument('--version',action='version',version='Verdant Cyberdeck '+__version__)
    parser.add_argument('--framebuffer',action='store_true',help='Explicit TFT backend; refuses existing TFT owners')
    parser.add_argument('--self-test',action='store_true',help='Exercise pages offscreen; never touch radios or services')
    parser.add_argument('--smoke-test',action='store_true',help='Open existing desktop display and exit after two seconds')
    parser.add_argument('--alerts-only',action='store_true',help='Hidden always-on-top desktop capture notifications')
    args=parser.parse_args()
    if args.alerts_only:
        from .alerts import desktop_notifications
        desktop_notifications()
        return
    logs=log_directory()
    logs.mkdir(parents=True,exist_ok=True)
    logging.basicConfig(level=logging.INFO,handlers=[RotatingFileHandler(logs/'cyberdeck.log',maxBytes=500000,backupCount=2)],format='%(asctime)s %(levelname)s %(message)s')
    logging.info('Starting dashboard: %s',args)
    if args.self_test:
        app=Dashboard()
        app.splash_until=0
        for page in (app.home,app.pwn,app.wifi,app.bt,app.system,lambda:app.tools('TRAFFIC / WEB')):
            page()
            assert app.render().size==(480,320)
        app.home()
        app.render().save(asset_directory(ROOT)/'dashboard.png')
        app.splash_until=float('inf')
        app.render().save(asset_directory(ROOT)/'splash.png')
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
        print(f'Cyberdeck startup failed: {exc}\nSee {logs}/cyberdeck.log',file=sys.stderr)
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
    def keyboard(event):
        if app.auth_target:
            if event.keysym=='Return':app.submit_password()
            elif event.keysym=='BackSpace':app.password_key('BACKSPACE')
            elif event.keysym=='Escape':app.home()
            elif event.char and event.char.isprintable():app.password_key(event.char)
        elif event.keysym=='Return' and app.splash_until:app.enter_menu()
        elif event.keysym=='Escape':app.home()
    root.bind('<Key>',keyboard)
    canvas.bind('<Button-1>',lambda e:app.tap(e.x,e.y))
    canvas.bind('<Button-4>',lambda e:app.scroll(-3))
    canvas.bind('<Button-5>',lambda e:app.scroll(3))
    image_id=canvas.create_image(0,0,anchor='nw')
    painted=[None]
    def refresh():
        app.tick()
        key=app.visual_key()
        if key!=painted[0]:
            canvas.photo=ImageTk.PhotoImage(app.render())
            canvas.itemconfigure(image_id,image=canvas.photo)
            painted[0]=app.visual_key()
        root.after(100,refresh)
    refresh()
    if smoke:
        root.after(2000,app.shutdown)
    root.mainloop()

if __name__=='__main__':
    main()

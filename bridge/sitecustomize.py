"""Service-scoped runtime canvas tap; does not edit installed Pwnagotchi code."""
import os
if os.environ.get('VERDANT_PWN_SCREEN')=='1':
    import importlib.abc
    import importlib.machinery
    import sys
    import time
    class CanvasLoader(importlib.abc.Loader):
        def __init__(self,original):self.original=original
        def create_module(self,spec):return self.original.create_module(spec)
        def exec_module(self,module):
            self.original.exec_module(module)
            if module.__name__=='pwnagotchi.ui.hw.ili9488':
                original_layout=module.ILI9488.layout
                def layout(display):
                    result=original_layout(display)
                    from pwnagotchi.ui import fonts
                    fonts.setup(19,17,19,64,28,17)
                    return result
                module.ILI9488.layout=layout
                return
            original=module.Display._on_view_rendered
            last=[0.0]
            def rendered(display,image):
                original(display,image)
                if time.monotonic()-last[0]<0.25:return
                last[0]=time.monotonic()
                try:
                    import grp
                    import tempfile
                    from pathlib import Path
                    directory=Path('/run/verdant-cyberdeck')
                    directory.mkdir(mode=0o750,exist_ok=True)
                    os.chown(directory,0,grp.getgrnam('kali').gr_gid)
                    directory.chmod(0o750)
                    fd,name=tempfile.mkstemp(prefix='.pwn-frame-',dir=directory)
                    try:
                        with os.fdopen(fd,'wb') as stream:
                            image.save(stream,format='PNG')
                            os.fchmod(stream.fileno(),0o640)
                            os.fchown(stream.fileno(),0,grp.getgrnam('kali').gr_gid)
                        os.replace(name,directory/'pwn-screen.png')
                    finally:
                        if os.path.exists(name):os.unlink(name)
                except Exception:
                    import logging
                    logging.exception('Verdant live-screen publication failed')
            module.Display._on_view_rendered=rendered
    class CanvasFinder(importlib.abc.MetaPathFinder):
        def find_spec(self,fullname,path=None,target=None):
            if fullname not in ('pwnagotchi.ui.display','pwnagotchi.ui.hw.ili9488'):return None
            spec=importlib.machinery.PathFinder.find_spec(fullname,path)
            if spec and spec.loader:spec.loader=CanvasLoader(spec.loader)
            return spec
    sys.meta_path.insert(0,CanvasFinder())

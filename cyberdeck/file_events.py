"""Optional Linux filesystem wakeup for native pointer updates."""
import ctypes
import os
from pathlib import Path
import struct

class FileEvents:
    def __init__(self,paths):
        self.fd=None;self.names={}
        libc=ctypes.CDLL(None,use_errno=True)
        try:
            libc.inotify_init1.argtypes=[ctypes.c_int];libc.inotify_init1.restype=ctypes.c_int
            libc.inotify_add_watch.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_uint32];libc.inotify_add_watch.restype=ctypes.c_int
            fd=libc.inotify_init1(os.O_NONBLOCK|os.O_CLOEXEC)
            if fd<0:return
            self.fd=fd
            for path in map(Path,paths):
                wd=libc.inotify_add_watch(fd,os.fsencode(path.parent),0x2|0x80|0x100|0x200)
                if wd>=0:self.names.setdefault(wd,set()).add(path.name)
            if not self.names:self.close()
        except (AttributeError,OSError):self.close()
    def drain(self):
        changed=False
        if self.fd is None:return False
        while True:
            try:data=os.read(self.fd,65536)
            except BlockingIOError:break
            if not data:break
            offset=0
            while offset+16<=len(data):
                wd,mask,cookie,length=struct.unpack_from('iIII',data,offset)
                name=os.fsdecode(data[offset+16:offset+16+length].split(b'\0',1)[0]);offset+=16+length
                if name in self.names.get(wd,set()):changed=True
        return changed
    def close(self):
        if self.fd is not None:os.close(self.fd);self.fd=None

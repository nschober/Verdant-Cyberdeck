"""Validate a supplied password against existing PAM login policy; never store it."""
import ctypes as C
import ctypes.util

class Message(C.Structure):
    _fields_=[('style',C.c_int),('text',C.c_char_p)]
class Response(C.Structure):
    _fields_=[('response',C.c_void_p),('code',C.c_int)]
Conversation=C.CFUNCTYPE(C.c_int,C.c_int,C.POINTER(C.POINTER(Message)),C.POINTER(C.POINTER(Response)),C.c_void_p)
class Conv(C.Structure):
    _fields_=[('callback',Conversation),('data',C.c_void_p)]

def authenticate(username,password):
    if username!='kali' or not password or '\x00' in password:return False
    pam=C.CDLL(ctypes_path('pam'));libc=C.CDLL(ctypes_path('c'))
    libc.calloc.argtypes=[C.c_size_t,C.c_size_t];libc.calloc.restype=C.c_void_p
    libc.strdup.argtypes=[C.c_char_p];libc.strdup.restype=C.c_void_p
    libc.free.argtypes=[C.c_void_p]
    @Conversation
    def converse(count,messages,reply,data):
        if not 0<count<=16:return 19
        memory=libc.calloc(count,C.sizeof(Response))
        if not memory:return 5
        result=C.cast(memory,C.POINTER(Response))
        for i in range(count):
            style=messages[i].contents.style
            if style in (1,2):
                result[i].response=libc.strdup((password if style==1 else username).encode())
                if not result[i].response:
                    for j in range(i):libc.free(result[j].response)
                    libc.free(memory);return 5
            elif style not in (3,4):
                for j in range(i):libc.free(result[j].response)
                libc.free(memory);return 19
        reply[0]=result
        return 0
    conv=Conv(converse,None);handle=C.c_void_p()
    pam.pam_start.argtypes=[C.c_char_p,C.c_char_p,C.POINTER(Conv),C.POINTER(C.c_void_p)]
    for name in ('pam_authenticate','pam_acct_mgmt','pam_end'):
        getattr(pam,name).argtypes=[C.c_void_p,C.c_int]
    code=pam.pam_start(b'login',username.encode(),C.byref(conv),C.byref(handle))
    if code:return False
    try:
        code=pam.pam_authenticate(handle,0)
        if code==0:code=pam.pam_acct_mgmt(handle,0)
        return code==0
    finally:pam.pam_end(handle,code)

def ctypes_path(name):
    path=C.util.find_library(name)
    if not path:raise RuntimeError('System authentication library unavailable')
    return path

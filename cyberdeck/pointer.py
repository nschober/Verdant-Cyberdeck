"""Small-screen relative mouse scaling, preserving subpixel motion."""
class PointerMotion:
    def __init__(self,x=240,y=150,gain=0.28):self.x=float(x);self.y=float(y);self.gain=gain
    def move(self,axis,value):
        if axis=='x':self.x=max(0,min(479,self.x+value*self.gain))
        else:self.y=max(0,min(319,self.y+value*self.gain))
        return round(self.x),round(self.y)
    def sync(self,x,y):self.x=float(x);self.y=float(y)

def key_character(code,held):
    from evdev import ecodes as E
    shifted=bool(set(held)&{E.KEY_LEFTSHIFT,E.KEY_RIGHTSHIFT})
    pairs={E.KEY_SPACE:(' ',' '),E.KEY_MINUS:('-','_'),E.KEY_EQUAL:('=','+'),E.KEY_LEFTBRACE:('[','{'),E.KEY_RIGHTBRACE:(']','}'),E.KEY_BACKSLASH:('\\','|'),E.KEY_SEMICOLON:(';',':'),E.KEY_APOSTROPHE:("'",'"'),E.KEY_COMMA:(',','<'),E.KEY_DOT:('.', '>'),E.KEY_SLASH:('/','?'),E.KEY_GRAVE:('`','~')}
    if code in pairs:return pairs[code][shifted]
    name=E.KEY.get(code,'')
    if isinstance(name,str) and name.startswith('KEY_') and len(name)==5:
        char=name[-1]
        if char.isalpha():return char if shifted else char.lower()
        if char in '1234567890':return '!@#$%^&*()'['1234567890'.index(char)] if shifted else char
    return ''

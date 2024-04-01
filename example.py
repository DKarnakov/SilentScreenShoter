import tkinter
class HoldKeyDetect(object):
    def __init__(self, widget, keys, handler=None):
        """Detect holding `keys` in `widget`"""
        self.widget = widget
        self.handler = handler
        self.binds = {}
        for key in keys:
            evid = '<KeyPress-%s>'%key
            self.binds[evid] = widget.bind(evid,self.keypress)
    def __del__(self):
        try: self.unbind()
        except tkinter.TclError: pass   #app has been destroyed
    def unbind(self):
        while True:
            try: evid,fid = self.binds.popitem()
            except KeyError: break
            self.widget.unbind(evid, fid)
    def keypress(self,e):
        try:
            if self.handler:
                self.handler(e)
        finally:
            self.unbind()
class App(object):
    def __init__(self,root):
        self.root = root
        root.focus_force()
        self.h = HoldKeyDetect(root,("Shift_L","Shift_R"),self.set_mode)
        root.after(1000,   # larger than keypress repeat interval + code overhead
                        self.continue_)
        self.mode = False
    def go(self):
        self.root.mainloop()
    def set_mode(self,_):
        print("Shift mode set")
        self.mode = True
    def continue_(self):
        del self.h
        print ("Mode=", self.mode)
        self.root.destroy()
if __name__ == '__main__':
    App(tkinter.Tk()).go()
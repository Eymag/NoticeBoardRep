import tkinter
import time

class PasswordEntry():
    '''Creates a tkinter entry box that shows stars

    instead of password in clear'''
    def __init__(self, master, center=True):
        self.master = master
        self.top = tkinter.Toplevel(master=master)
        self.top.transient(master)
        self.top.grab_set()
        self.top.title = 'Password required'
        tkinter.Label(self.top, text='Email Password is required').pack()
        self.e = tkinter.Entry(self.top, show='*')
        self.e.pack(fill=tkinter.X)
        self.e.bind('<Return>', self.ok)
        self.e.bind('<Escape>', self.cancel)
        f = tkinter.Frame(self.top)
        f.pack(fill=tkinter.X)
        tkinter.Button(f, text='OK', command=self.ok).pack(side='left',
                                                           expand=1,
                                                           fill=tkinter.X)
        tkinter.Button(f, text='Cancel', command=self.cancel).pack(side='left',
                                                                   expand=1,
                                                                   fill=tkinter.X)
        self.result = None
        if center:self.center()

    def ok(self, *args):
        '''Handling of OK button press (and enter)'''
        self.result = self.e.get()
        self.top.destroy()
        return 'break'

    def cancel(self, *args):
        '''Handling of Cancel button press (and esc)'''
        self.top.destroy()
        return 'break'

    def center(self):
        '''Centers box on masters window'''
        #To be sure that we have updated posisions
        self.master.update_idletasks()
        #Finding masters center
        master_center_x = self.master.winfo_x() + (self.master.winfo_width()/2)
        master_center_y = self.master.winfo_y() + (self.master.winfo_height()/2)
        #Own size
        w = self.top.winfo_width()
        h = self.top.winfo_height()
        #Making sure that we place within limits
        x = int(max(0, master_center_x - w/2))
        y = int(max(0, master_center_y - h/2))
        self.top.geometry('{}x{}+{}+{}'.format(w, h, x, y))
        
def password_entry(master, center=True):
    '''Password entry function

    creates a password entry instance and handles password entry
    returns when password entry window has closed'''
    entry = PasswordEntry(master, center)
    entry.e.focus_force()
    entry.master.wait_window(entry.top)
    return entry.result

if __name__ == '__main__':
    tk = tkinter.Tk()
    password_entry(tk)
    tk.mainloop()

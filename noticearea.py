import tkinter

import displayrow

class NoticeArea():
    def __init__(self, master, config, *args, **kwargs):
        self.f = tkinter.Frame(master, *args, **kwargs)
        self.master = master
        self.config = config
        self.events = []
        bg = self.config.get('general', 'background_color')
        t,b,l,r = [int(x) for x in self.config.get('noticeboard', 'padding').split(',')]

                #bg = 'red'
        tkinter.Frame(self.f,
                      bg=bg,
                      width=l).pack(side='left',fill=tkinter.Y)
        #bg = 'green'
        middle = tkinter.Frame(self.f, bg=bg)
        middle.pack(side='left',fill=tkinter.BOTH, expand=1)
        
        #bg = 'red'
        tkinter.Frame(self.f,
                      bg=bg,
                      width=r).pack(side='right',fill=tkinter.Y)
        #bg = 'blue'
        tkinter.Frame(middle,
                      bg=bg,
                      height=t).pack(side='top',
                                     fill=tkinter.X)
        #bg = 'yellow'
        content_window = tkinter.Frame(middle, bg=bg)
        content_window.pack(side='top', fill=tkinter.BOTH, expand=1)
        #bg = 'blue'
        tkinter.Frame(middle,
                      bg=bg,
                      height=b).pack(side='bottom', fill=tkinter.X)

        self.rows = []
        max_row = self.config.getint('noticeboard', 'max_row')
        #bg = 'green'
        for index in range(max_row):
            #Y-Padd all except last row
            padd = not(index == max_row-1)
            row = displayrow.DisplayRow(content_window, self.config, padd, bg=bg)
            row.pack(fill=tkinter.X)
            self.rows.append(row)

    def pack(self, *args, **kwargs):
        self.f.pack(*args, **kwargs)

    def display_events(self, valid_events):
        self.events = valid_events
        for row in self.rows:
            valid_events = row.display_events(valid_events)

from tkinter import *
from time import sleep

import busstop

master = Tk()
master.title('BusTimeTable')
vartext = StringVar()

busstop = busstop.Busstop('b8cd9b05-c511-402a-926d-818f11d5048b',
                          'b02c6fc7-128d-428d-9912-dfec421b9a70',
                          '58.394116', '15.560780', 15)
label = Label(master,
              justify='left',
              anchor='nw',
              bg='#EFEFEF',
              fg='#464646',
              font=('Semcon_Mono', 12),
              textvariable=vartext)

def update_timetable():
    while 1:
        vartext.set('\n'.join(busstop.get_output_string()))
        master.update()
        sleep(1)

label.pack()
update_timetable()
    
master.mainloop()

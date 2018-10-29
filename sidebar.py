import tkinter
import datetime
import re
import PIL
import textwrap
import logging
import os
from math import ceil

import weather
import busstop
import geodata
import calendarevents

class SideBar():
    '''Class to handle extra information like weather and time'''
    def __init__(self, master, config, *args, **kwargs):
        self.config = config
        self.f = tkinter.Frame(master, *args, **kwargs)
        self.make_month_table()
        self.make_day_table()
        lat,lon = self.config.get('general', 'weather_location').split(',')
        self.w = weather.Weather(lat, lon,
                                 self.config.getint('general', 'weather_update_interval'))
        self.city = geodata.get_town(lat, lon)
        self.c = calendarevents.CalendarEvents('calendar.csv')
        ok_widgets = ('time', 'date', 'week', 'temp', 'weekday', 'spacer',
                      'percipitation', 'wind', 'weather', 'smhi', 'headline', 'calendar', 'sunrise', 'sunset')
        widgets = [w.strip() for w in self.config.get('sidebar', 'widget_order').split(',')]
        self.atributes = [{'name':w,
                           'text_size':self.config.get(w,'fontsize'),
                           'font':self.config.get(w, 'font'),
                           'orientation':self.config.get(w, 'orientation'),
                           'anchor':self.config.get(w, 'anchor', fallback='center')} for w in widgets if w in ok_widgets]
    
        self.build_content_window()
        l = logging.getLogger(__name__)
        l.debug('INIT DONE')

    def build_content_window(self):
        #Sidebar width is given in percent
        width = int(self.f.winfo_screenwidth() * self.config.getint('sidebar', 'width')/100)
        self.bg = self.config.get('general', 'sidebar_color')
        n,s,w,e = self.config.get('sidebar', 'sidebar_padding').split(',')
        tkinter.Frame(self.f, width=int(w), bg=self.bg).pack(side='left',fill=tkinter.Y)
        content = tkinter.Frame(self.f, bg=self.bg)
        content.pack(side='left',fill=tkinter.BOTH)
        tkinter.Frame(self.f, width=int(e), bg=self.bg).pack(side='left', fill=tkinter.Y)
        #Use top padding to force width to correct size
        tkinter.Frame(content, height=int(n), width=width, bg=self.bg).pack(side='top', fill=tkinter.X)
        tkinter.Frame(content, height=int(s), bg=self.bg).pack(side='bottom', fill=tkinter.X)
        for atr in self.atributes:
            label = tkinter.Label(content, bg=self.bg, bd=0, anchor=atr['anchor'])
            label.pack(side=atr['orientation'], fill=tkinter.X)
            setattr(self, atr['name'], label)

    def pack(self, *args, **kwargs):
        self.f.pack(*args, **kwargs)
        return self
    def pack_forget(self):
        self.f.pack_forget()

    def make_string(self, text, font, max_width):
        '''Creates a list of strings that fits within max_with boundaries'''
        def check_length(rows, font,  max_width, img):
            '''Helper function to check if all rows fit'''
            row_length = max([len(row) for row in rows])
            for row in rows:
                row_size = PIL.ImageDraw.Draw(img).textsize(row.rjust(row_length), font)
                if row_size[0] > max_width:
                    return
            return row_length

        img=PIL.Image.new("RGBA", (1, 1), self.bg)
        #Check that text is not empty string
        wrapper = textwrap.TextWrapper(drop_whitespace=True)
        if text:
            for length in range(len(text), -1, -1):
                split_text = []
                for t in text.splitlines():
                    wrapper.width = length
                    split_text.extend(wrapper.wrap(t))
                if check_length(split_text, font, max_width, img):
                    return [x.rstrip().rjust(length) for x in split_text]
        #Emtpy string case
        else:
            return ['']

    def create_entry(self, name, text, font, size):
        '''Creates the actual entry'''
        text = text if text else 'empty'
        #Calculates the max width for a row screenwidth * width in percent
        max_width = int(self.f.winfo_screenwidth() * self.config.getint('sidebar', 'width')/100)
        font = PIL.ImageFont.truetype(font, size)
        text = self.make_string(text, font, max_width)
        textcolor = self.config.get('general', 'text_color')
        #Rowspace is in percent of font size
        rowspace = int(size * self.config.getint(name, 'rowspace')/100)
        img=PIL.Image.new("RGBA", (1, 1), self.bg)
        x = 0
        y = 0
        #calculate total space for widget
        for row in text:
            row_size = PIL.ImageDraw.Draw(img).textsize(row, font)
            x = row_size[0] if row_size[0] > x else x
            #PIL misses with 1 pixel for some reason
            y += row_size[1] + rowspace + 1
        img=PIL.Image.new("RGBA", (x, y), self.bg)
        draw = PIL.ImageDraw.Draw(img)
        current_row = 0 
        for row in text:
            current_row += int(rowspace/2)
            draw.text((0, current_row), row, textcolor, font=font)
            current_row += ceil(rowspace/2) + size
            
        return PIL.ImageTk.PhotoImage(img)

    def data_update(self):
        '''Updates data'''
        return self.w.update_weather()
                
    def update(self, now):
        '''Updates GUI with data'''
        strings = {'time':now.strftime('%H:%M'),
                   'date':str(now.date().day) + ' ' + self.months[now.date().month],
                   'weekday':self.days[now.weekday()],
                   'week':now.strftime('Vecka %W'),
                   'temp':str(round(float(self.w.get('t')))) + ' \u00B0' + 'C',
                   'percipitation':self.w.get('pmean') + ' mm/h',
                   'wind':str(round(float(self.w.get('ws')))) + ' ['+ str(round(float(self.w.get('gust'))))+'] m/s ' + self.w.parse_windir(self.w.get('wd')),
                   'weather':self.w.parse_weather(self.w.get('Wsymb')),
                   'smhi':str(self.city) + ' ' + str(self.w.change_timezone(self.w.utctime).strftime('%H:%M')) + ' (SMHI)',
                   'headline':'\n' + '\nHänder idag:',
                   'calendar':self.c.get_todays_events(),
                   'sunrise':'Upp: ' + str(self.w.change_timezone(self.w.sunrise).strftime('%H:%M')),
                   'sunset':'Ned: ' + str(self.w.change_timezone(self.w.sunset).strftime('%H:%M'))}
        for atr in self.atributes:
            if atr['name'] == 'weather':
                #Try to get a weather icon to use, else use text
                img = self.weather_icon(strings[atr['name']])
                if img:
                    getattr(self, atr['name']).image=img
                    getattr(self, atr['name']).configure(image=img)
                    #Important so that we do not run next if
                    continue
            if atr['name'] in strings:
                img = self.create_entry(atr['name'], strings[atr['name']],
                                        atr['font'], int(atr['text_size']))
                getattr(self, atr['name']).image=img
                getattr(self, atr['name']).configure(image=img)

    def weather_icon(self, name):
        if self.config.getboolean('sidebar', 'use_weather_icons'):
            resolution = str(self.f.winfo_screenwidth()) + 'x' + str(self.f.winfo_screenheight())
            name = name + '_natt' if self.w.night() else name 
            name = name + '_jul' if self.w.christmas() else name
            path = os.path.join(os.path.dirname(__file__), 'icons', 'Vädersymboler', resolution, name + '.png')
            try:
                img = PIL.Image.open(path)
                return PIL.ImageTk.PhotoImage(img)
            except Exception:
                logging.getLogger(__name__).error('Weather Icon FAIL:', exc_info=True)

    def make_month_table(self):
        '''Translation table for months'''
        self.months = {1:'januari',
                       2:'februari',
                       3:'mars',
                       4:'april',
                       5:'maj',
                       6:'juni',
                       7:'juli',
                       8:'augusti',
                       9:'september',
                       10:'oktober',
                       11:'november',
                       12:'december'}
        
    def make_day_table(self):
        '''Translation table for days'''
        self.days = {0:'Måndag',
                     1:'Tisdag',
                     2:'Onsdag',
                     3:'Torsdag',
                     4:'Fredag',
                     5:'Lördag',
                     6:'Söndag'}

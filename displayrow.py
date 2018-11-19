import tkinter
import PIL 
from PIL import Image, ImageTk, ImageDraw
import random
import io
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


class DisplayRow():
    '''Class to controll one row of notices'''
    def __init__(self, master, config, padd=True, *args, **kwargs):
        self.master = master
        self.config = config
        self.rows = self.config.getint('noticeboard', 'max_row')
        self.cols = self.config.getint('noticeboard', 'max_col')
        
        self.padd_y = padd
        self.bg = kwargs['bg'] if 'bg' in kwargs else master.cget('bg')
        self.f = tkinter.Frame(master, *args, **kwargs)
        self.content = tkinter.Frame(self.f, bg=self.bg, bd=0)
        self.content.pack(side='top', fill=tkinter.X)
        self.widgets = []
            
    def pack(self, *args, **kwargs):
        self.f.pack(*args, **kwargs)
        return self

    def make_widgets(self):
        '''Makes container widgets for notices'''
        width, padd_width, height, padd_height = self.get_size()
        for index in range(self.cols):
            l = tkinter.Label(self.content, bg=self.bg, bd=0)
            l.pack(side='left')
            l.name = index
            self.widgets.append(l)
            #Put padd element to all elements except last element
            if not index == self.cols - 1:
                tkinter.Frame(self.content, bg=self.bg, width=padd_width, bd=0).pack(side='left')
        if self.padd_y:
            self.padding = tkinter.Frame(self.f, height=padd_height, bg=self.bg, bd=0)
            self.padding.pack(side='top')
            

    def get_size(self):
        '''Calculate size of a note'''
        window_width = self.master.winfo_width()
        window_height = self.master.winfo_height()

        if self.cols > 1:
            width = ((window_width/self.cols)*0.90)
            padd_width = (window_width - width*self.cols)/(self.cols - 1)
        else:
            width = window_width
            padd_width = 0
        if self.rows > 1:
            height = ((window_height/self.rows)*0.90)
            padd_height = (window_height - height*self.rows)/(self.rows - 1)
        else:
            height = window_height
            padd_height = 0
        return int(width), int(padd_width), int(height), int(padd_height)

    def get_font_size(self, width, height):
        '''Calculate text sizes'''
        header_size = int(min(height*0.15, width*0.1))
        date_size = int(min(height*0.08, width*0.05))
        text_size = int(min(height*0.6, width*0.06))
        return header_size, date_size, text_size
    
    def display_events(self, events):
        '''Display events

        returns remaining events that does not fit on row'''
        
        if not self.widgets:self.make_widgets()
        num = min(len(self.widgets), len(events))
        for index in range(self.cols):
            if index < num:
                note = self.create_note(events[index])
                self.widgets[index].configure(image=note)
                self.widgets[index].image = note
            else:
                #Unused note spaces are set to ''
                self.widgets[index].configure(image='')
                self.widgets[index].image = None
        return events[num:]

    def format_row(self, text, font, width, draw):
        '''Format text string so that it fits with note width'''
        result = []
        text = text.split()
        current_row = ''
        while text:
            word = text.pop(0)
            if draw.textsize(current_row+word, font)[0] > width:
                result.append(current_row)
                current_row = word
            else:
                current_row += ' ' + word if current_row else word
        result.append(current_row)
        return result
                  
    def create_note(self, event):
        '''Creates a single note'''
        
        width, padd_width, height, padd_height = self.get_size()
        
     
        header_font_size, timestamp_font_size, text_font_size = self.get_font_size(width, height)
        header_row_space = int((header_font_size*0.93 - header_font_size)/2)
        timestamp_row_space = int(timestamp_font_size*0.7/2)
        text_row_space = int(text_font_size*0.7/2)    

        text_color = self.config.get('general', 'text_color')
        color = random.choice(self.config.get('general', 'colors').split(','))
        
        header_font = self.config.get('general', 'headline_font')
        heading_font = PIL.ImageFont.truetype(header_font, header_font_size)
        
        text_font = self.config.get('general', 'text_font')
        time_font = PIL.ImageFont.truetype(text_font, timestamp_font_size)
        
        pic_font = self.config.get('general', 'headline_font')
        picture_font = PIL.ImageFont.truetype(pic_font, timestamp_font_size)

        text_font = PIL.ImageFont.truetype(text_font, text_font_size)
           #If mail have attachement and image returns thumbnail
        if event.email.attachments:
           for attach in event.email.attachments:    
                    if 'image' in attach.content_type:
                        try:
                            #Load image, crop and make thumbnail
                            img = attach.content
                            attImg = Image.open(io.BytesIO(img))
                            w,h = attImg.size

                            if(not((w or h)<(width or height))): #If image smaller than notice no crop needed
                                minlength = min(w,h)                 
                                left = (w - minlength)/2
                                top = (h - minlength)/2
                                right = (w + minlength)/2
                                bottom = (h + minlength)/2
                                attImg = attImg.crop((left, top, right, bottom))

                            attImg.thumbnail((width,height), PIL.Image.ANTIALIAS)
                            image = ImageTk.PhotoImage(attImg)

                        except Exception as ex:
                            print('AttachmentError:' , ex)
                            break
                        return image
                    else:
                        print('Attachment is not an image.')
                        break
                    
        img=PIL.Image.new("RGBA", (width, height),color)
        draw = PIL.ImageDraw.Draw(img)
        
        #Heading
        col = self.config.getint('noticeboard', 'start_col')
        row = self.config.getint('noticeboard', 'start_row')
        draw.text((col,row), event.user, text_color, font=heading_font)
        row += header_font_size + header_row_space

        ts, text = event.display_msg()
        
        #Timestamp
        ts = self.format_row(ts, time_font, width, draw)
        for line in ts:
            row += timestamp_row_space
            draw.text((col, row), line, text_color, font=time_font)
            row += timestamp_row_space + timestamp_font_size
        
        #Message
        text = self.format_row(text, text_font, width - (col*2), draw)
        for line in text:
            row += text_row_space
            draw.text((col, row), line, text_color, font=text_font)
            row += text_font_size + text_row_space
        return PIL.ImageTk.PhotoImage(img)

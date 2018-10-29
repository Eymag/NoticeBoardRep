import PIL, PIL.ImageTk, PIL.Image, PIL.ImageFont, PIL.ImageDraw
import tkinter
import datetime
import textwrap
import re
import os
import configparser
import queue
import threading
import time
import logging

import password_entry
import exchange_email as Email
import sidebar
import noticearea

class NoticeBoard():
    def __init__(self, master):
        '''Main GUI-Class to handle the notice board'''
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.logger.info('Starting GUI at: ' + time.strftime('%Y-%m-%d %H:%M:%S'))
        self.master = master
        self.config = configparser.ConfigParser()
        self.command_queue = queue.Queue()
        self.event_server = None
        self.running=True
        self.update_threads = []
        
        with open(os.path.join('config', 'NoticeBoard.ini')) as fh:
                  self.config.read_file(fh)
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()

        with open(os.path.join('config', 'default.ini')) as fh:
            self.config.read_file(fh)
        #Try to get specialized config
        #will overwrite parts of default if it exsist
        try:
            size = str(screen_width) + 'x' + str(screen_height)
            with open(os.path.join('config',  size + '.ini')) as fh:
                self.config.read_file(fh)
        except FileNotFoundError:
            pass
        sb = self.config.getboolean('sidebar', 'sidebar_enabled')
        self.build_main_gui(sb)
        self.master.update_idletasks()
        #Start Sidebar update thread
        if sb:
            self.logger.debug('Starting Sidebar update thread at: ' + time.strftime('%Y-%m-%d %H:%M:%S'))
            t = threading.Thread(target=self.update_sidebar)
            t.start()
            self.update_threads.append(t)
            self.logger.debug('Sidebar update started')
        
        self.master.config(cursor='none')
        self.read_loop()
        password = password_entry.password_entry(self.master)
        #Starting mailbox update thread and event_server
        if password:
            self.logger.debug('Password received enabling Exchange functionality')
            username = self.config.get('general', 'username')
            mailbox = self.config.get('general', 'mailbox')
            smtp_host = self.config.get('general', 'smtp_host')
            poll_time = float(self.config.get('general', 'poll_time')) * 60
            self.event_server = Email.Email(smtp_host=smtp_host,
                                            mailbox=mailbox,
                                            username=username,
                                            password=password,
                                            poll_time=poll_time)
            self.logger.debug('Starting noticeboard update thread at: ' + time.strftime('%Y-%m-%d %H:%M:%S'))
            t = threading.Thread(target=self.update_notices)
            t.start()
            self.update_threads.append(t)
            self.logger.debug('Update thread started')

    def build_main_gui(self, sb):
        '''Creates main gui areas'''
        self.master.bind('<Button-1>', self._exit)
        self.set_fullscreen(True)
        bg = self.config.get('general', 'background_color')
        self.notice_area = noticearea.NoticeArea(self.master, self.config, bg=bg, bd=0)
        self.notice_area.pack(expand=1, fill=tkinter.BOTH, side='left')
        if sb:
            self.sidebar = sidebar.SideBar(self.master,
                                           self.config,
                                           bg=self.config.get('general',
                                                              'sidebar_color'),
                                           bd=0)
            self.sidebar.pack(side='right', fill=tkinter.Y)
        else:
            self.sidebar=False
        
    def set_fullscreen(self, state):
        '''Sets display fullscreen on/of (True/False)'''
        self._fullscreen_state = state
        self.master.attributes('-fullscreen', state)
        
    def toggle_fullscreen(self):
        '''Toggle fullscreen'''
        self.set_fullscreen(not self._fullscreen_state)
        
    def update_board(self, events, commands):
        '''Updates the notice bord and removes inactive events'''
        valid_events = [x for x in events if x.valid() and x.visible()]
        invalid_events = [x for x in events if not x.valid()]
        valid_events.sort()
        self.event_server.remove_events(invalid_events)
        valid_commands = {'list':self.list,
                          'delete':self.delete}
        for command in commands:
            if not command[0]:
                self.logger.warning('Failed to run command: ', command)
            elif command[1] in valid_commands:
                self.logger.info('Command: ' + str(command) + ' is run')
                valid_commands[command[1]](valid_events, *command[2])
                self.logger.debug('Command successfull')
        self.notice_area.display_events(valid_events)

    def update_sidebar(self):
        '''Updates the sidebar area

        Runs in separete thread'''
        while self.running:
            if self.sidebar:
                try:
                    now = self.sidebar.data_update()
                    #Put a update reueqst on queue for GUI thread to act on
                    self.command_queue.put([self.sidebar.update, now])
                finally:
                    pass
            time.sleep(5)
            
    def update_notices(self):
        '''Update notices in notice area'''
        while self.running:
            if self.event_server and self.event_server.is_time_to_update():
                try:
                    events, commands = self.event_server.get_events()
                #Accept all errors and log it
                except Exception:
                    logging.getLogger(__name__).error('Failed to get Notices', exc_info=True)
                else:
                    if events is not None:
                        self.command_queue.put([self.update_board, events, commands])
            time.sleep(5)
                                        
    def read_loop(self):
        '''Check if new data has arrived'''
        try:
            command = self.command_queue.get_nowait()
            self.logger.debug('Handling command: ' + str(command))
            command[0](*command[1:])
        except queue.Empty:
            #Nothing to get, so just ignore it
            pass
        self.master.after(1000, self.read_loop)
        
    def _exit(self, *event):
        self.running=False
        self.master.destroy()

    def list(self, events, to, *args):
        subject = 'Current Events on NoticeBoard'
        msg = []
        for event in events:
            msg.append(str(event))
        msg = '\n'.join(msg)
        self.event_server.send(to, subject, msg)

    def delete(self, events, message, *args):
        '''Deletes message from mailbox'''
        item_id = re.match(r'\s?<delete>\s?(.*)', message.subject)
        if item_id:
            item_id = item_id.group(1)
            for event in events:
                if event.email.item_id == item_id:
                    self.event_server.remove_events([event])
                    to = event.user_address
                    subject = 'Message removed'
                    msg = 'Message with subject: ' + event.email.subject + ' has been removed'
                    self.event_server.send(to,
                                           subject,
                                           msg)
                       
if __name__ == '__main__':
    tk = tkinter.Tk()
    NoticeBoard(tk)
    tk.mainloop()

import tkinter

import password_entry
import exchange_email as Email


class AdminGUI():
    def __init__(self, master):
        self.master = master
        self.master.bind('<Return>', self.get_emails)
        self.master.title('NoticeBoard Admin')
        self.master.geometry('{}x{}'.format(500,500))
        self.master.update_idletasks()
        toolbar = tkinter.Frame(self.master)
        toolbar.pack(fill=tkinter.X)
        tkinter.Button(toolbar, text='Set password', command=self.set_password).pack(side='right')
        tkinter.Button(toolbar, text='Get Emails', command=self.get_emails).pack(side='right')
        self.mail_frame = tkinter.Frame(self.master)
        self.mail_frame.pack(fill=tkinter.BOTH, expand=1)
        self.mails = []
        self.set_password()

    def set_password(self):
        self._password = password_entry.password_entry(self.master)
        self.event_server = Email.Email(password=self._password) if self._password else None

    def get_emails(self, *args):
        folder, nr_of_mails = self.event_server.select_mailbox(self.event_server.smtp_host)
        mails = self.event_server.fetch(folder, nr_of_mails)
        self.display_mails(mails)

    def display_mails(self, mails):
        for mail in self.mails:
            mail.destroy()
        for mail in mails:
            self.mails.append(Mail(self.mail_frame, mail, self.delete).pack(fill=tkinter.X))

    def delete(self, mail):
        self.event_server.remove_events([mail], send_error=False)

class Mail():
    def __init__(self, master, mail, delete):
        self.email = mail
        self.master = master
        self.delete_fn = delete
        self.f = tkinter.Frame(self.master)
        tkinter.Label(self.f, text=mail.subject, anchor='w').pack(side='left', fill=tkinter.X, expand=1)
        tkinter.Button(self.f, text='Delete', command=self.delete).pack(side='left')

    def delete(self):
        self.delete_fn(self)
        self.destroy()

    def destroy(self):
        self.f.destroy()

    def pack(self, *args, **kwargs):
        self.f.pack(*args, **kwargs)
        return self

    def pack_forget(self):
        self.f.pack_forget()


tk = tkinter.Tk()
AdminGUI(tk)
tk.mainloop()

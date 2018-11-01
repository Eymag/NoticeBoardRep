import getpass
import exchangelib
import email, email.policy, email.header
import re
import os
import datetime
import logging
import configparser

import event

with open(os.path.join('texts', 'error_header.txt')) as fh:
    ERROR_HEADER = fh.readlines()
with open(os.path.join('texts', 'help_text.txt')) as fh:
    HELP_TEXT = fh.readlines()

class Email():
    def __init__(self,
                 smtp_host,
                 mailbox,
                 username,
                 password=None,
                 poll_time=60):
        '''Class to handle connections with a Exchange Server'''
        self.username = username
        self.set_password(password)
        self.mailbox = mailbox
        self.ews_url = None
        self.ews_auth_type = None
        self.smtp_host = smtp_host
        self.poll_time = poll_time
        self.last_update_time = None
        logging.getLogger(__name__).debug('Email initiated')

    def is_time_to_update(self):
        '''Check if its time to update'''
        if not self.last_update_time:
            return True
        logging.getLogger(__name__).debug('Time to update')
        return self.last_update_time + datetime.timedelta(seconds=self.poll_time) < datetime.datetime.now() 
        

    def set_password(self, password=None):
        '''If password is not set, use getpass to get it in a protected way

        WARNING, IDLE does not hide password.'''
        self._password = password if password else getpass.getpass()

    def fetch(self, server, nr_of_mails, what='', max_amount=50):
        '''Fetch the last max_amount(50) mails from server

        server is a folder instance, nr_of_mails is the number of mails in mailbox
        what is not used'''
        amount = min(nr_of_mails, max_amount)
        logging.getLogger(__name__).debug('Fetching: {} of mails'.format(amount))
        mails = server.all().order_by('-datetime_received')[:amount]
        return mails

    def select_mailbox(self, server, mailbox='Inbox'):
        '''Returns folder instance'''
        account = self.login(server)
        folder = account.root.get_folder_by_name(mailbox)
        return folder, folder.total_count

    def get_events(self, max_amount=50):
        '''Gets the last 50 events'''
        new_messages = False
        try:
            l = logging.getLogger(__name__)
            l.debug('Get events')
            mailbox, nr_of_mails = self.select_mailbox(self.smtp_host, self.mailbox)
            if not nr_of_mails:
                l.debug('No mails to get')
                return []
            events = []
            commands = []
            
            if mailbox:
                for message in self.fetch(mailbox, nr_of_mails, '', max_amount):
                    #Only certain mail addresses is OK
                    if not self.valid_email_address(message) or self.erica(message):
                        try:
                            l.info('Invalid mail address: {}'.format(message.sender.email_address))
                        except Exception:
                            pass
                        #Adding a event that only contains the mail message
                        #will trigger removal of it.
                        e = event.Event()
                        e.email = message
                        events.append(e)
                        continue
                    #Check if its a command and if its valid
                    result =  self.parse_command(message)
                    if result:
                        #Its a command, process it
                        l.debug('Proccessing: {}'.format(result))
                        if result[0]:
                            commands.append(result)
                        else:
                            print(result[1], result[2])
                    else:
                        #parse message
                        e = event.Event(message)
                        events.append(e)
                        if e.valid() and not (message.is_read or self.isreply(message)):
                            new_messages = True
                            l.debug('Sending confirmation email')
                            to = message.sender.email_address
                            subject = 'Message added to notice board'
                            msg = ['Message with subject: ', message.subject,
                                   ' has been added to NoticeBoard', '\n\n',
                                   'Send a mail with the following subject'
                                   ' line to delete:','\n', '<delete>',
                                   message.item_id]
                            message.is_read = True
                            message.save()
                            self.send(to, subject, ''.join(msg))
        except exchangelib.errors.ErrorInternalServerTransientError:
            l.warning('Get events failed', exc_info=True)
            return None,None

        self.last_update_time = datetime.datetime.now()
        self.send_subscriptions(events, new_messages)
        return events, commands

    def parse_command(self, message):
        '''Parse a email message to see if it is a valid command'''
        valid_commands = {'list':self.list,
                          'help':self.help,
                          'delete':self.delete,
                          'subscribe':self.subscribe}
        command_string = '.?<(.+)>'
        l = logging.getLogger(__name__)
        if not isinstance(message, exchangelib.items.Message):
            l.warning('Message not a correct message {}'.format(message))
            return     

        if not message.subject:
            l.warning('Message does not contain a subject')
            return
        match = re.match(command_string, message.subject)
        if not match:
            return
        command = match.group(1)
        command = command.lower().split(',')
        command[0] = command[0].strip()
        if command[0] in valid_commands:
            result = valid_commands[command[0]](message, *command[1:])
            return result
        else:
            return self.help(message)

    def valid_email_address(self, message):
        '''Check if message has a valid address'''
        try:
            return  message.sender.email_address.lower().endswith('@semcon.com')
        except Exception:
            logging.getLogger(__name__).error('Error in checking for valid mail address', exc_info=True)

    def isreply(self, message):
        return ('SE-GOT-EX02.semcon.se' in message.message_id) or 'Message added to notice board' in message.subject

    def create_mailbox(self, server, name):
        '''Create a new folder on server

        Not implemented in module yet'''
        pass
    
    def remove_events(self, events, send_error=True):
        '''Removes event from mailbox
        Call with events that are to be removed'''
        try:
            account = self.login(self.smtp_host)
        except exchangelib.errors.ErrorInternalServerTransientError:
            return
        items = []
        for event in events:
            items.append(event.email)
            if send_error and event.fail_reasons:
                subject = 'Något gick tyvärr fel'
                text = ['FEL: ']
                text.extend(event.fail_reasons)
                text.extend(['\n','Ditt meddelande: ', str(event.email.subject), ' '])
                text.extend(ERROR_HEADER)
                text.extend(HELP_TEXT)
                text = ''.join(text)
                self.send(event.user_address, subject, text)
        account.bulk_move(items, account.trash)
        
    def send(self, to, subject, msg):
        '''send function

        Sends an email <to> <subject> <msg>'''
        account = self.login(self.smtp_host)
        email = exchangelib.Message(account=account,
                                    subject=subject,
                                    body=msg,
                                    to_recipients=[to])
        email.send()
        print('Email sent to:', to)

    def send_subscriptions(self, events, new_events):
        subscriptions = configparser.ConfigParser()
        result = subscriptions.read('subscriptions/user_subscriptions.ini')
        if not result:
            logging.getLogger(__name__).warn('No subscription file found')
        to_send = []
        #Order maters
        for section in ('each', 'daily', 'weekley'):
            if subscriptions.has_section(section):
                for option in subscriptions.options(section):
                    #Special handling of each section so not to send if there are no new
                    if section == 'each' and not new_events:
                        break
                    if option in to_send:
                        #If we already have decided to send because of another section, just update last send time
                        subscriptions.set(section, option, datetime.datetime.now().strftime('%Y%m%d%H%M'))
                    else:
                        date = subscriptions.get(section, option)
                        if date == 'None':
                            diff = None
                        else:
                            date = datetime.datetime(date, '%Y%m%d%H%M')
                            now = datetime.datetime.now()
                            diff = now - date
                        if section == 'daily':
                            if not diff or diff > datetime.datetime.timedelta(hours=24):
                                to_send.append(option)
                                subscription.set(section, option, date)
                        elif section == 'weekley':
                            if not diff or diff > datetime.datetime.timedelta(days=7):
                                to_send.append(option)
                                subscription.set(section, option, date)
                        else:
                            to_send.append(option)
                            subscriptions.set(section, option, date)

        subject = 'Current Events on NoticeBoard'
        msg = []
        for event in events:
            msg.append(str(event))
        msg = '\n'.join(msg)                            
        for address in to_send:
            self.send(address, subject, msg)
            
    def login(self, server):
        '''Login to server, return account instance'''
        
        credentials = exchangelib.ServiceAccount(username=self.username,
                                                 password=self._password)
        if self.ews_url and self.ews_auth_type and self.smtp_host:
            config = exchangelib.Configuration(service_endpoint=self.ews_url,
                                               credentials=credentials,
                                               auth_type=self.ews_auth_type)

            account = exchangelib.Account(primary_smtp_address = server,
                                          config=config, autodiscover=False,
                                          access_type=exchangelib.DELEGATE)
        else:
            account = exchangelib.Account(primary_smtp_address=server,
                                          credentials=credentials,
                                          autodiscover=True,
                                          access_type=exchangelib.DELEGATE)
        
        self.ews_url = account.protocol.service_endpoint
        self.ews_auth_type = account.protocol.auth_type
        self.smtp_host = account.primary_smtp_address

        return account

    #Usercommands
    def delete(self, message, *args):
        '''Removes a message from mailbox'''
        try:
            account = self.login(self.smtp_host)
            account.bulk_move([message], account.trash)
        except Exception as err:
            return (False, 'delete', [err, message])
        else:
            return (True, 'delete', [message])
            
    
    def help(self, message, *args):
        '''Sends help text'''
        try:
            self.send(message.sender.email_address, 'Instruktion till Tavlan i Linköping', ''.join(HELP_TEXT))
            account = self.login(self.smtp_host)
            account.bulk_move([message], account.trash)
        except Exception as err:
            return (False, 'help', [err, message])
        else:
            return (True, 'help', [])

    def list(self, message, *args):
        '''Sends current messages to user'''
        try:
            account = self.login(self.smtp_host)
            account.bulk_move([message], account.trash)
        except Exception as err:
            return (False, 'list', [err, message])
        else:
            return (True, 'list', [message.sender.email_address])
    def subscribe(self, message, *args):
        def handle_subscription(address, subscription, subscription_type):
            if subscription_type == 'unsubscribe':
                for section in subscription.sections():
                    subscription.remove_option(section, address)
            else:
                try:
                    subscription.add_section(subscription_type)
                except configparser.DuplicateSectionError:
                    pass
                subscription.set(subscription_type, address, 'None')

        os.makedirs('subscriptions', exist_ok=True)    
        subscriptions = configparser.ConfigParser()
        subscriptions.read('subscriptions/user_subscriptions.ini')
        if not args:
            handle_subscription(message.sender.email_address, subscriptions, 'each')
        else:
            args = [x.strip().lower() for x in args if x.strip() in ('daily', 'weekley', 'each', 'unsubscribe')]
            for arg in args:
                handle_subscription(message.sender.email_address, subscriptions, arg)
        
        with open('subscriptions/user_subscriptions.ini', 'w') as fh:
            subscriptions.write(fh)

        return (True, 'subscribe', [])
                    
    #Taking care of childish behavior
    def erica(self, message):
        try:
            subject = message.subject.strip()
            match = re.match('(\[.*\])', subject)
            if match and 'bajskorv' in match.group(1).lower():
                self.send('erica.nilsbacken@semcon.com', 'Erica step away from the computer', 'Sluta larva dig och använd <help> istället')
                return True
        except Exception:
            pass

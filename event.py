import datetime
import re
import email
import exchangelib
import textwrap

class Event():
    '''Class to hold a Event

    Takes a email object'''
    def __init__(self, email=None):
        self.start = None
        self.end = None
        self.message = None
        self.user = None
        self.user_address = None
        self.email = email
        self.fail_reasons = []

        if email:
            self.parse_message(email)

    def __lt__(self, other):
        if not isinstance(other, type(self)):raise TypeError
        return self.start.nearest_date() < other.start.nearest_date()

    def __eq__(self, other):
        if not isinstance(other, type(self)):raise TypeError
        return self.start.nearest_date() == other.start.nearest_date()

    def __str__(self):
        if self.start == self.end:
            ts = str(self.start)
        else:
            ts = str(self.start) + ' - ' + str(self.end)

        return self.user + ' ' + ts + ': ' + self.message        

    @property
    def whole_day(self):
        return self.start.whole_day and self.end.whole_day

    def display_msg(self):
        if self.start == self.end:
            ts = str(self.start)
        else:
            ts = str(self.start) + ' - ' + str(self.end)
        
        return ts, self.message

    def valid(self):
        '''Returns True if Event is valid

        Event is valid if it has valid entries and has a end time
        later than now'''
        return bool(self.user and
                    self.message and
                    self.start and
                    self.start.valid and
                    self.end and
                    self.end.valid and
                    not self.end.expired)
    def visible(self):
        '''Reocurring messages are only shown on the day
        before and on the day they occur'''
        if self.start.weekday and self.start.reocuring:
            now = datetime.datetime.now().date()
            next_date = self.start.nearest_date().date()
            return now - next_date == datetime.timedelta()
        else:
            return True
        
    def parse_message(self, message):
        '''Parse message to get: Date, From, Message'''

        ts_msg = '\[(?P<TimeStamp>.+)\]\\s?(?P<Message>.+)'
            
        if isinstance(message, exchangelib.items.Message):
            self.user = message.sender.name
            self.user_address = message.sender.email_address
            date = message.datetime_sent
            if not message.subject:
                error = 'Empty header'
                print(error)
                self.fail_reasons.append(error)
                return
            match = re.match(ts_msg, message.subject)
            self.message = match.group('Message') if match else message.subject

            if match:
                self.parse_time(match.group('TimeStamp'), date)
            elif self.message.strip().startswith('['):
                self.fail_reasons.append('Faulty timestamp:' + self.message)
            else:
                self.parse_time('', date)
        
    def parse_time(self, timestamp, date):
        '''Parse a timestamp

        expand with year,month day if needed and validate that
        timestamp is a validdate acording to format
        uses timestamp from date to expand'''

        #Splitting on -, removing white space and make lower case.
        timestamp = [x.strip().lower() for x in timestamp.split(';')]
        #Valid timestamps has either len 0, 1 or 2 (empty TS will use date)
        if not (len(timestamp) in (0, 1, 2)):
            error = 'Faulty timestamp:', timestamp
            print(error)
            self.fail_reasons.append(error)
            return
        if len(timestamp) in (0, 1):
            start = Timestamp(timestamp[0], date)
            end = Timestamp(timestamp[0], date, False)
            if not (start.valid and end.valid):
                self.fail_reasons.append('Failed to parse timestamp')
                return
            self.start = start
            self.end = end
            
        elif len(timestamp) == 2:
            start = Timestamp(timestamp[0], date)
            end = Timestamp(timestamp[1], date, False)
            if not (start.valid and end.valid):
                self.fail_reasons.append('Failed to parse timestamp')
                return
            self.start = start
            self.end = end
            
        else:
            error = 'Timestamp1: {} and Timestamp2: {} has different lenght'.format(timestamp[0], timestamp[1])
            print(error)
            self.fail_reasons.append(error)
            return

class Timestamp():
    def __init__(self, timestamp, email_date, floor=True):
        self._weekdays = ({'day_nr':0, 'name':'Måndag', 'reoccuring':('måndagar', 'mondays'), 'once':('mån', 'måndag', 'mon', 'monday')},
                          {'day_nr':1, 'name':'Tisdag', 'reoccuring':('tisdagar', 'tuesdays'), 'once':('tis', 'tue', 'tisdag', 'tuesday')},
                          {'day_nr':2, 'name':'Onsdag', 'reoccuring':('onsdagar', 'wednesdays'), 'once':('ons', 'wed', 'onsdag', 'wednesday')},
                          {'day_nr':3, 'name':'Torsdag', 'reoccuring':('torsdagar', 'thursdays'), 'once':('tor', 'thu', 'torsdag', 'thursday')},
                          {'day_nr':4, 'name':'Fredag', 'reoccuring':('fredagar', 'fridays'), 'once':('fre', 'fri', 'fredag', 'friday')},
                          {'day_nr':5, 'name':'Lördag', 'reoccuring':('lördagar', 'saturdays'), 'once':('lör', 'sat', 'lördag', 'saturday')},
                          {'day_nr':6, 'name':'Söndag', 'reoccuring':('söndagar', 'sundays'), 'once':('sön', 'sun', 'söndag', 'sunday')})

        self.floor = floor
        if self.validate_time_format(timestamp):
            self.timestamp = self.expand(timestamp, email_date)
        else:
            self.timestamp = None  

    def __lt__(self, other):
        if not isinstance(other, type(self)):raise TypeError
        return self.nearest_date(self.timestamp) < other.nearest_date(other.timestamp)

    def __eq__(self, other):
        if not isinstance(other, type(self)):raise TypeError
        ts1 = self.nearest_date(self.timestamp)
        ts2 = other.nearest_date(other.timestamp)
        if ts1.date() == ts2.date() and self.whole_day and other.whole_day:
            return True
        return ts1 == ts2

    def __str__(self):
        wd = self.weekday
        ts=''
        if not self.whole_day:
            ts = self.timestamp.strftime(' %H:%M')
        if wd: return wd['reoccuring'][0].capitalize() + ts
        if (self.timestamp.date() - datetime.datetime.now().date()).days > 7:
            return str(int(self.timestamp.strftime('%d'))) + '/' + str(int(self.timestamp.strftime('%m'))) + ts
        if (datetime.datetime.now().date() - self.timestamp.date()).days < 7:
            return self._weekdays[self.timestamp.weekday()]['name'] + ts
        return str(int(self.timestamp.strftime('%d'))) + '/' + str(int(self.timestamp.strftime('%m'))) + ts
        

    @property
    def whole_day(self):
        return self.nearest_date(self.timestamp).strftime('%H:%M:%S.%f') in ('00:00:00.000000', '23:59:59.999999')
    
    @property
    def weekday(self):
        return self._weekday(self.timestamp)

    @property
    def expired(self):
        if not self.valid:return True
        if self.reocuring: return False
        return self.timestamp.date() < datetime.datetime.now().date()

    @property
    def valid(self):
        return self.timestamp

    @property
    def reocuring(self):
        wd = self._weekday(self.timestamp)
        return wd and self.timestamp in wd['reoccuring']

    def validate_time_format(self, timestamp):
        ts = timestamp
        year =  '(\d{4}|\d{2})'
        month = '(\d{2})'
        day =   '(\d{2})'
        hour=   '(\d{2})'
        minute= '(\d{2})'
        timeformat1 = '(' + year + '-)+(' + month + '-)+(' + day + ')+( ' + hour + ':' + minute + ')\Z'
        timeformat2 = time_format = '(' + year + '-)+(' + month + '-)+(' + day + ')+\Z'
        timeformat3 = hour + ':' + minute
        time_formats = (timeformat1, timeformat2, timeformat3)
        if self._weekday(timestamp):
            timestamp = timestamp.strip()
            timestamp = timestamp.split()
            if len(timestamp) == 1:
                return True
            timestamp = ''.join(timestamp[1:])
        timestamp = timestamp.strip()
        #Emtpy Timestamp is OK
        if not timestamp:
            return True
        for frmt in time_formats:
            if re.match(frmt, timestamp):
                return True
        print('Invalid timestamp:', ts, timestamp)
    
    def _weekday(self, timestamp):
        if not timestamp:return
        if not isinstance(timestamp, str):return
        date = timestamp.split()[0].lower()
        for day in self._weekdays:
            if date in day['reoccuring'] or date in day['once']:
                return day

    def nearest_date(self, timestamp=None, date=None):
        '''Converts a weekday to next date it occurs

        Returns datetime object'''
        timestamp = timestamp if timestamp else self.timestamp
        hour,minute,second,microsecond = (0,0,0,0) if self.floor else (23,59,59,999999)

        if isinstance(timestamp, datetime.datetime):
            return timestamp

        elif self._weekday(timestamp) and date:
            limit = date.date() + datetime.timedelta(days=6)
            now = datetime.datetime.now().date()
            diff = (self._weekday(timestamp)['day_nr'] - now.weekday())%7
            next_day = now + datetime.timedelta(days=diff)
            if limit < next_day:
                next_day = next_day - datetime.timedelta(days=7)
            if ':' in timestamp: hour, minute = timestamp.split()[1].split(':')
            t = datetime.time(int(hour),
                              int(minute),
                              second,
                              microsecond,
                              datetime.timezone(datetime.timedelta(hours=-1)))
            ts = datetime.datetime.combine(next_day, t)
            return ts
            
        elif self._weekday(timestamp):
            
            now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-1)))
            diff = (self._weekday(timestamp)['day_nr'] - now.weekday())%7
            ts = now + datetime.timedelta(days=diff)
            if ':' in timestamp:hour, minute = timestamp.split()[1].split(':')
            ts = ts.replace(hour=int(hour), minute=int(minute), second=second, microsecond=microsecond)
            return ts
        else:
            raise RuntimeError('Timestamp.nearest date() should not get here!')

    def expand(self, timestamp, date):
        '''Expands a timestamp to a full datetime object'''

        self.timestamp = None
        timestamp = timestamp.lower()
        day = self._weekday(timestamp)
        if day and timestamp.split()[0].lower() in day['once']:
            return self.nearest_date(timestamp, date)
        elif day:
            return timestamp
        else:
            hour,minute,second,microsecond = (0,0,0,0) if self.floor else (23,59,59,999999)
            timestamp = timestamp.split()
            if not len(timestamp) in (0,1,2):
                print('Faulty timestamp ' + timestamp)
                return
            if len(timestamp) == 0:
                return date.replace(hour=hour, minute=minute, second=second, microsecond=microsecond)
            elif ':' in timestamp[0]:
                try:
                    hour,minute = timestamp[0].split(':')
                    return date.replace(hour=int(hour), minute=int(minute), second=second, microsecond=microsecond)
                except Exception:
                    print('Faulty timestamp ' + timestamp[0])
                    return

            d = timestamp[0].split('-')
            if len(d) == 3:
                year, month, day = d
            elif len(d) == 2:
                year = date.year
                month, day = d
            elif len(d) == 1:
                year = date.year
                month = date.month
                day = d[0]
            
            if isinstance(year, str) and len(year) == 2:year = '20'+year
            if len(timestamp) == 2:
                hour,minute = timestamp[1].split(':')
            try:
                return datetime.datetime(*[int(x) for x in (year, month, day, hour, minute,second, microsecond)], tzinfo=datetime.timezone(datetime.timedelta(hours=-1)))
            except Exception:
                return 

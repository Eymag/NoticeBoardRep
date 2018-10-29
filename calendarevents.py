import csv
import datetime

class CalendarEvents():
    def __init__(self, calendar):
        self.calendar = calendar

    def get_todays_events(self):
        with open(self.calendar) as csvfile:
            events = csv.reader(csvfile, delimiter=',')
            today = datetime.date.today()
            result = []
            for event in events:
                if str(event[0]) == str(today.day) and str(event[1]) == str(today.month):
                    result.append(event[2])
            if len(result) == 0:
                result.append('Inget speciellt')
            return '\n'.join(result)
            

if __name__ == '__main__':
    e = CalendarEvents('calendar.csv')
    print(e.get_todays_events())

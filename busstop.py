import urllib.request
import json
import datetime
import time
import os
import logging
from tkinter import *


class Busstop():
    def __init__(self, stop_key, plan_key, lat, lon, dep_limit):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.stop_key = stop_key
        self.plan_key = plan_key
        self.lat = lat
        self.lon = lon
        self.stop, self.stopname = self.find_closest_stop() #'740056608', 'Mjärdevi Center' #
        self.timetable = {}
        self.filename = 'timetable_' + self.stop + '.txt'
        self.limit = dep_limit
        self.output_string = []
        #Asuming that if we have a timetable already downloaded its fresh enough
        #If its set to false update will always be run on startup
        self.fresh_data = True
        #Make sure that we has read it so user does not have to think of it
        self.read_timetable()

    def find_closest_stop(self):
        api = 'https://api.resrobot.se/v2/location.nearbystops'
        url = '{api}?key={plan_key}&originCoordLat={lat}&originCoordLong={lon}&r=1000&format=json'.format(api=api,plan_key=self.plan_key,lat=self.lat,lon=self.lon)
        apiurl = urllib.request.urlopen(url)
        data = json.loads(apiurl.read().decode('utf-8'))
        entry = data['StopLocation'][0]
        return entry['id'], entry['name']

    def parse_busstop(self, number, direction):
        '''Translation table so we gets more human readable destinations'''
        busstops = {
            '2_Linköping Centralstation':'Resecentrum via US',
            '4_Linköping Centralstation':'Resecentrum via US',
            '12_Linköping Centralstation':'Resecentrum',
            '12_Landbogatan (Linköping kn)':'Lambohov',
            '20_Linköping Centralstation':'Resecentrum',
            '20_Linköping Mjärdevi':'Mjärdevi\t',
            '22_Ekhaga Linköping':'Ekholmen',
            '22_Linköping Mjärdevi':'Mjärdevi\t',
            '38_Industrivägen (Kinda kn)':'Kisa\t',
            '39_Industrivägen (Kinda kn)':'Kisa\t',
            '39_Kisa station (Kinda kn)':'Kisa\t',
            '52_Mariebergs gård (Motala kn)':'Motala\t',
            '59_Bävervägen (Finspång kn)':'Finspång\t',
            '65_Vadstena station':'Vadstena\t',
            '73_Linköping US Norra entrén':'Linköping\t',
            '73_Norrköping Söder Tull':'Norrköping',
            '75_Östra station (Norrköping kn)':'Norrköping',
            '526_Vreta kloster kyrka (Linköping kn)':'Berg via Ljungsbro',
            '526_Linköping Centralstation':'Resecentrum',
            '540_Kisa station (Kinda kn)':'Kisa\t',
            '540_Linköping Centralstation':'Resecentrum',
            '543_Linköping Centralstation':'Resecentrum',
            '577_Vikingstad station (Linköping kn)':'Vikingstad',
            '577_Linköping US Norra entrén':'US Norra entrén',
            '577_Linköping Centralstation':'Resecentrum',
            }
        if str(number + '_' + direction) in busstops:
            return(busstops[number + '_' + direction])
        else:
            return direction

    def parse_departure(self, dt):
        '''Create a timedelta to departure'''
        now = datetime.datetime.now().replace(microsecond=0)
        departure = int((dt - now).seconds/60)
        return departure

    def parse_timetable(self, retry=True):
        result = []
        #Make sure that self.timetable has been updated
        if 'Departure' in self.timetable:
            for entry in self.timetable['Departure']:
                dt = datetime.datetime.strptime(entry['date'] + ' ' + entry['time'], '%Y-%m-%d %H:%M:%S')
                if dt >= datetime.datetime.now():
                    result.append([entry['transportNumber'],
                                   self.parse_busstop(entry['transportNumber'],
                                                      entry['direction']),
                                   self.parse_departure(dt),
                                   entry['time']])
                #code added by Nils (small optimization)
                #No need to check rest of departures if we already are at limit
                if len(result) >= self.limit:
                    break
        if len(result) < self.limit:
            self.fresh_data = False
            self.read_timetable()
            #Added by Nils
            if retry:
                result = self.parse_timetable(False)
        return result
    
    def print_timetable(self, buslist):
        print(self.create_output_string(buslist))

    def create_output_string(self, buslist):
        r = []
        r.append('\t'.join([self.stopname, datetime.datetime.now().strftime('%H:%M')]))
        for item in buslist:
            if not item[2]:
                departure = 'Nu'
            else:
                if item[2] > 30:
                    departure = str(item[3])[:5]
                else:
                    departure = str(item[2]) + ' min'
            r.append('\t'.join([item[0],item[1],departure]))
        return r
                
    def get_output_string(self):
        '''Convinience function to parse and output string'''
        return self.create_output_string(self.parse_timetable())
    
    def update_timetable(self):
        with open(self.filename, 'w') as fh:
            data = self.get_timetable()
            json.dump(data, fh)
            fh.close()
            self.logger.info('Timetable updated for ' + self.stopname + ' at: ' + time.strftime('%Y-%m-%d %H:%M:%S'))
            
    def read_timetable(self):
        files = [f for f in os.listdir(os.curdir) if os.path.isfile(f)]
        if not (self.filename in files and self.fresh_data):
            self.update_timetable()
            self.fresh_data = True
        with open(self.filename, 'r') as fh:
            self.timetable = json.load(fh)

    def get_timetable(self):
        api = 'https://api.resrobot.se/v2/departureBoard'
        url = '{api}?key={stop_key}&id={stop}&maxJourneys=50&format=json'.format(api=api,stop=self.stop,stop_key=self.stop_key)
        apiurl = urllib.request.urlopen(url)
        data = json.loads(apiurl.read().decode('utf-8'))
        return data

#Do not run if imported from other modules
if __name__ == '__main__':
    stop_key = 'b8cd9b05-c511-402a-926d-818f11d5048b'
    plan_key = 'b02c6fc7-128d-428d-9912-dfec421b9a70'
    w = Busstop(stop_key, plan_key, '58.394119', '15.560682', 10)
    print(w.get_output_string())

        
    

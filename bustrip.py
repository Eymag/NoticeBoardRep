import urllib.request
import json
import datetime


class Bustrip():
    def __init__(self, origin_lat, origin_lon, dest_lat, dest_lon, key):
        self.key = key
        self.origin_lat = origin_lat
        self.origin_lon = origin_lon
        self.dest_lat = dest_lat
        self.dest_lon = dest_lon
        
    def find_closest_stop(self, lat, lon):
            api = 'https://api.resrobot.se/v2/location.nearbystops'
            url = '{api}?key={key}&originCoordLat={lat}&originCoordLong={lon}&r=1000&format=json'.format(api=api,key=self.key,lat=lat,lon=lon)
            print(url)
            apiurl = urllib.request.urlopen(url)
            data = json.loads(apiurl.read().decode('utf-8'))
            return data['StopLocation'][0]['id']

    def parse_time(self, string):
        return datetime.datetime.strptime(string, '%H:%M:%S').strftime('%H:%M')

    def time_delta(self, start, stop):
        delta = str(datetime.datetime.strptime(stop, '%H:%M') - datetime.datetime.strptime(start, '%H:%M')).split(':')
        return str(str(int(delta[0]))+'h '+str(int(delta[1]))+'m ')

    def parse_product(self, leg):
        if  leg['Product']['catOutS'] in ['BLT', 'ULT', 'JLT', 'SLT', 'FLT']:
            cat = {'BLT':'Buss','ULT':'Tunnelbana','JLT':'Lokaltåg','SLT':'Spårvagn','FLT':'Färja'}[leg['Product']['catOutS']]
            return str(cat+' '+leg['Product']['num'])
        elif leg['Product']['catOutS'] == 'BAX':
            return leg['Product']['operator']
        elif leg['Product']['catOutS'] in ['JAX', 'JRE', 'JIC', 'JPT', 'JEX', 'JST']:
            return str(leg['Product']['catOutL']+' '+leg['Product']['num'])
        else:
            return leg['Product']['name']
                    
    def get_bustrip(self):
            origin_stop = self.find_closest_stop(self.origin_lat, self.origin_lon)
            dest_stop = self.find_closest_stop(self.dest_lat, self.dest_lon)
            api = 'https://api.resrobot.se/v2/trip'
            url = '{api}?key={key}&passlist=0&originId={origin}&destCoordLat={dest_lat}&destCoordLong={dest_lon}&destCoordName=dest&numF=4&format=json'.format(api=api,
                                                                                                                                                               key=self.key,
                                                                                                                                                               origin=origin_stop,
                                                                                                                                                               origin_lon=self.origin_lon,
                                                                                                                                                               dest_lat=self.dest_lat,
                                                                                                                                                               dest_lon=self.dest_lon)
            apiurl = urllib.request.urlopen(url)
            data = json.loads(apiurl.read().decode('utf-8'))
            start = {}
            stop = {}
            
            for entry in data['Trip']:
                start_time = self.parse_time(entry['LegList']['Leg'][0]['Origin']['time'])
                start_name = entry['LegList']['Leg'][0]['Origin']['name']
                trip = []
                for leg in entry['LegList']['Leg']:
                    if leg['name']:
                        trip.append(' '.join([self.parse_time(leg['Origin']['time']),'\t',leg['Origin']['name']]))
                        trip.append(' '.join(['\t',self.parse_product(leg),'-',leg['Destination']['name']]))
                        trip.append(self.parse_time(leg['Destination']['time']))
                        
                    elif leg['name'] == 'WALK' or 'TRSF':
                        trip.append(' '.join([self.parse_time(leg['Origin']['time']),'\t',leg['Origin']['name']]))
                        trip.append(' '.join(['\t','Gå',str(leg['dist']),'m -',leg['Destination']['name']]))
                        trip.append(' '.join([self.parse_time(leg['Destination']['time'])]))
                        
                    stop_time = self.parse_time(leg['Destination']['time'])
                    stop_name = leg['Destination']['name']
                trip = '\n'.join(trip)
                print(str(start_time+'-'+stop_time+' '+self.time_delta(start_time, stop_time)))
                print(trip, '\n')

if __name__ == '__main__':
    key = 'b02c6fc7-128d-428d-9912-dfec421b9a70'
    origin_lat, origin_lon = '58.394119', '15.560682'
    dest_lat, dest_lon = '58.203316', '16.001994'
    b = Bustrip(origin_lat, origin_lon, dest_lat, dest_lon, key)
    b.get_bustrip()
        

import urllib.request
import json
import datetime
import logging
import time


smhi_forecast = 'http://opendata-download-metfcst.smhi.se/api'
forecast_version = 2

class Weather():
    '''Weather handling class'''
    def __init__(self, lat, lon, update_interval):
        '''SMHI puts restrictions on how offen you are allowed to update weather from the API

        Use 15 mins to be sure'''
        self.lat = lat
        self.lon = lon
        self._last_update = None
        self._weather = {}
        self.update_interval = datetime.timedelta(minutes=update_interval)
        self.utctime = datetime.datetime
        self.sunrise = datetime.datetime
        self.sunset = datetime.datetime
        self.suntime_last_update = None

        self.get_suntime()

    def update_weather(self):
        '''Updates weather data if update_interval time has gone
        since last time'''
        now = datetime.datetime.now()
        if not self._last_update or (now - self._last_update) > self.update_interval:
            self._last_update = now
            self._weather = self.get_forecast(self.lat, self.lon)
        return now

    def get(self, name):
        '''Returns a parameters value'''
        if not name in self._weather:
            logging.getLogger(__name__).warning('get:{} is not a valid field'.format(name))
            return ''
        return str(self._weather[name]['values'][0])
            
    def parse_windir(self, data):
        '''Converts winddirection fromd degrees to readable format'''
        wind_dirs = {0:'N',22.5:'NO', 67.5:'O', 112.5:'SO',
                     157.5:'S', 202.5:'SV', 247.5:'V',
                     292.5:'NV', 337.5:'N'}
        current_min = 0
    
        for key in wind_dirs:
            if key < int(data):
                current_min = key
        return wind_dirs[current_min]

    def parse_weather(self, weather_number):
        '''Converts a weather int to readable format'''
        #Weather numbers start at 1 and not 0
        result =  ['Klart', 'Mest klart', 'Växlande molnighet',
                   'Halvklart', 'Molnigt', 'Mulet', 'Dimma', 'Regnskurar',
                   'Åskskurar', 'Byar av snöblandat regn',
                   'Snöbyar', 'Regn', 'Åska',
                   'Snöblandat regn', 'Snöfall'][int(weather_number)-1]
        return result

    def night(self, ts=None):
        '''Checks if the sun is up'''
        if not self.suntime_last_update == datetime.datetime.utcnow().date():
            self.get_suntime()
        #If suntime is unavaliable
        if not (self.sunrise and self.sunset):
            return
        ts = ts.time() if ts else datetime.datetime.utcnow().time()
        return not(self.sunrise.time() < ts < self.sunset.time())

    def christmas(self):
        '''Check if christmas is near'''
        d = datetime.date.today()
        return d.month == 12

    def get_suntime(self):
        url = 'https://api.sunrise-sunset.org/json?lat={lat}&lng={lon}&formatted=0'.format(lat=self.lat,
                                                                                           lon=self.lon)
        try:
            apiurl = urllib.request.urlopen(url)
        except urllib.error.URLError:
            logging.getLogger(__name__).info('Failed to update suntimes')
            return
        data = json.loads(apiurl.read().decode('utf-8'))
        self.sunrise = datetime.datetime.strptime(data['results']['sunrise'][:19], '%Y-%m-%dT%H:%M:%S')
        self.sunset = datetime.datetime.strptime(data['results']['sunset'][:19], '%Y-%m-%dT%H:%M:%S')
        logging.getLogger(__name__).info('Sunrise and sunset times updated at: ' + time.strftime('%Y-%m-%d %H:%M:%S'))
        self.suntime_last_update = datetime.datetime.utcnow().date()

    def change_timezone(self, utctime):
        return utctime.replace(tzinfo=datetime.timezone.utc).astimezone()
        
    def get_forecast(self, lat, lon):
        '''Gets forcast for lat long from SMHI'''
        url = '/category/pmp2g/version/{version}/geotype/point/lon/{lon}/lat/{lat}/data.json'.format(version=forecast_version,
                                                                                                     lon=lon,
                                                                                                     lat=lat)
        try:
            data = json.loads(str(urllib.request.urlopen(smhi_forecast + url).readlines()[0], 'utf-8'))
        except Exception as error:
            l = logging.getLogger(__name__)
            l.error('Failed to update weather', exc_info=True)
            return self._weather
        else:
            now = datetime.datetime.utcnow()
            for entry in data['timeSeries']:
                current_time = datetime.datetime.strptime(entry['validTime'], '%Y-%m-%dT%H:%M:%SZ')
                if (current_time - now) > datetime.timedelta():
                    result = {}
                    for dictionary in entry['parameters']:
                        result[dictionary['name']] = dictionary
                    self.utctime = current_time
                    return result

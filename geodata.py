import urllib.request
import json

#API_key = 'AIzaSyB1B7wcA2HbaQsqg41oL16DKAJ598ZTYJ8'
#url = 'https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lon}&key={API_key}'.format(lat=lat,
                                                                                                 #lon=lon,
                                                                                               #API_key=API_key) 

API_key = 'UDnYEPsSp9aDPq3AtyzTz60y0GCdptSR'


def get_town(lat, lon):
    
   
    url = 'http://open.mapquestapi.com/nominatim/v1/reverse.php?key={API_key}&format=json&lat={lat}&lon={lon}'.format(lat=lat,lon=lon,API_key=API_key)
   
    try:
        webURL = urllib.request.urlopen(url)
        data = json.loads(webURL.read().decode('utf-8'))
        return(data['address']['city'])
          
    except Exception:
        return 'No city'


    {"place_id":"80860641","licence":"Data © OpenStreetMap contributors, ODbL 1.0. https:\/\/osm.org\/copyright","osm_type":"way","osm_id":"24933727","lat":"58.3940269","lon":"15.5607903506734","display_name":"Science Park Mjärdevi, Slaka, Linköping, Linköpings kommun, Landskapet Östergötland, Östergötlands län, Götaland, Sverige","address":{"industrial":"Science Park Mjärdevi","city_district":"Slaka","city":"Linköping","county":"Linköpings kommun","state_district":"Landskapet Östergötland","state":"Östergötlands län","country":"Sverige","country_code":"se"},"boundingbox":["58.3937908","58.3942584","15.5603101","15.5612727"]}
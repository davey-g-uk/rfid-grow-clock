from pyowm.owm import OWM
import configparser

class weather(object):
    def __init__(self):
        #load weather config
        self._config = configparser.ConfigParser()
        self._config.read("./db/weather.ini")
        self._api = self._config['config']['api']
        self._location = self._config['config']['location']
    def getweather(self):
        try:
            owm = OWM(self._api)
            mgr = owm.weather_manager()
            obs = mgr.weather_at_place(self._location)
            weather = obs.weather
            return self._config['weathercodes'][str(weather.weather_code)]
        except:
            return self._config['weathercodes'][str(000)]
#!/usr/bin/python3

import sys
import RPi.GPIO as GPIO
from libs.pirc522 import RFID
import threading
import time
from .threadcontrol import threadcontrol
import configparser
from .displayhandler import displayfonts, displayupdate
from datetime import datetime, timedelta
import cherrypy
from jinja2 import Environment, FileSystemLoader


class iocontrol(object):
	def __init__(self):
		GPIO.setmode(GPIO.BCM)
		#Define GPIO for buttons
		self.button_voldown = 2
		self.button_volup = 3
		self.button_next = 14
		self.button_play = 15
		self.button_previous = 4
		self.button_cd = 17
		self.button_eject = 27
		self.button_alarm = 20
		self.red_LED = 6
		self.yellow_LED = 12
		self.green_LED = 13
		
		#setup GPIO for input with inbuilt resistors
		GPIO.setup(self.button_volup, GPIO.IN)
		GPIO.setup(self.button_voldown, GPIO.IN)
		GPIO.setup(self.button_next, GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.setup(self.button_play, GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.setup(self.button_previous, GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.setup(self.button_cd, GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.setup(self.button_eject, GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.setup(self.button_alarm, GPIO.IN, pull_up_down=GPIO.PUD_UP)
		
		#Setup GPIO for LED driver
		GPIO.setup(self.red_LED, GPIO.OUT, initial=GPIO.HIGH)
		GPIO.setup(self.yellow_LED, GPIO.OUT, initial=GPIO.HIGH)
		GPIO.setup(self.green_LED, GPIO.OUT, initial=GPIO.HIGH)
		
		#setup call back events
		GPIO.add_event_detect(self.button_voldown, GPIO.FALLING, callback=self._callback_voldown, bouncetime=200 ) # need to pass vlc instance to the call back function
		GPIO.add_event_detect(self.button_volup, GPIO.FALLING, callback=self._callback_volup, bouncetime=200 )
		GPIO.add_event_detect(self.button_next, GPIO.RISING, callback=self._callback_next, bouncetime=400 )
		GPIO.add_event_detect(self.button_play, GPIO.RISING, callback=self._callback_play, bouncetime=400 )
		GPIO.add_event_detect(self.button_previous, GPIO.RISING, callback=self._callback_previous, bouncetime=400 )
		GPIO.add_event_detect(self.button_cd, GPIO.RISING, callback=self._callback_cd, bouncetime=400 )
		GPIO.add_event_detect(self.button_eject, GPIO.RISING, callback=self._callback_eject, bouncetime=400 )
		GPIO.add_event_detect(self.button_alarm, GPIO.FALLING, callback=self._callback_alarm, bouncetime=400 )
		
		#create config object
		self.config = configparser.ConfigParser()
		self.config.read("./db/card.ini")
		print(self.config.sections())
		

		#setup NFC Reader
		self._rdr = RFID()
		self._thread_NFC_IO = threading.Thread(target=self._thread_Handler_NFC, args =("nfc",))
		threadcontrol.threads.append(self._thread_NFC_IO)
		self._thread_NFC_IO.start()
		
		self._thread_Alarm_Monitor = threading.Thread(target=self._thread_handler_alarm, args =("alarm",))
		threadcontrol.threads.append(self._thread_Alarm_Monitor)
		self._thread_Alarm_Monitor.start()
		
		#Setup Webinterface
		startwebadmin()
		
	def _callback_voldown(self,channel):
		print("Volume Down")
		threadcontrol.hifi.volumedown()
	
	
	def _callback_volup(self,channel):
		print("Volume UP")
		threadcontrol.hifi.volumeup()
	
	def _callback_next(self,channel):
		print("Next")
		threadcontrol.hifi.next()
	
	def _callback_play(self,channel):
		threadcontrol.hifi.playbutton()
		time.sleep(3)
		if GPIO.input(self.button_play) == 0 :
			print("Stopping Player")
			threadcontrol.hifi.stopplayer()
	
	def _callback_previous(self,channel):
		print("previous")
		threadcontrol.hifi.previous()
	
	def _callback_cd(self,channel):
		print("CD Mode")
		threadcontrol.hifi.playcdplaylist()
	
	def _callback_eject(self,channel):
		threadcontrol.hifi.cd_eject()
		print("Eject")
	
	def _callback_alarm(self,channel):

		if int(threadcontrol.alarmconfig['alarm']['alarmset']) == 0:
			print("Alarm Set")
			self._set_red_LED()
			threadcontrol.alarmconfig.set('alarm','alarmset','1')
			threadcontrol.lock.acquire()
			with open(threadcontrol.alarmfile,'w') as f:
				threadcontrol.alarmconfig.write(f)
			threadcontrol.lock.release()
		else:
			#time.sleep(3)
			print("Alarm turned off")
			#if GPIO.input(self.button_alarm) == 0 :
			threadcontrol.alarmconfig.set('alarm','alarmset','0')
			threadcontrol.lock.acquire()
			self._clear_LED()
			with open(threadcontrol.alarmfile,'w') as f:
				threadcontrol.alarmconfig.write(f)
			threadcontrol.lock.release()		
	
		
	def _set_red_LED(self):
		GPIO.output(self.red_LED, GPIO.LOW)
		GPIO.output(self.yellow_LED, GPIO.HIGH)
		GPIO.output(self.green_LED, GPIO.HIGH)
		threadcontrol.alarmstate = 1
	
	def _set_yellow_LED(self):
		GPIO.output(self.red_LED, GPIO.HIGH)
		GPIO.output(self.yellow_LED, GPIO.LOW)
		GPIO.output(self.green_LED, GPIO.HIGH)
		threadcontrol.alarmstate = 2

	def _set_green_LED(self):
		GPIO.output(self.red_LED, GPIO.HIGH)
		GPIO.output(self.yellow_LED, GPIO.HIGH)
		GPIO.output(self.green_LED, GPIO.LOW)
		threadcontrol.alarmstate = 3
	
	def _clear_LED(self):
		GPIO.output(self.red_LED, GPIO.HIGH)
		GPIO.output(self.yellow_LED, GPIO.HIGH)
		GPIO.output(self.green_LED, GPIO.HIGH)
		threadcontrol.alarmstate = 0

	def _thread_Handler_NFC(self, id):
		print("Starting NFC Reader")

		while threadcontrol.controlsig:
			print("waiting for tag")
			self._rdr.wait_for_tag()
			print("tag detected")
			(error, data) = self._rdr.request()
			(error, uid) = self._rdr.anticoll()
			if not error:
				card_id = str(uid[0])+str(uid[1])+str(uid[2])+str(uid[3])
				print("Card ID: " + card_id)
				cardmatch = self.config['cardid'][card_id]
				print("Card Match = " + cardmatch)
				print ("Card Dir:" + self.config[cardmatch]['dir'])
				print("Playing MP3")
				threadcontrol.hifi.playmp3playlist(self.config[cardmatch]['dir'],self.config[cardmatch]['title'])
				time.sleep(1)
	
	def _thread_handler_alarm(self,id):
		print("starting Alarm Monitor")
		alarmactive = -1
		playtimeactive = -1
		alarmtriggered = 0
		while threadcontrol.controlsig:
			threadcontrol.alarmconfig.read("./db/alarm.ini")
			if int(threadcontrol.alarmconfig['alarm']['alarmset']) == 1:
				now = datetime.now()
				current_hours = now.strftime("%-H")	
				current_minutes = now.strftime("%-M")
				current_year = now.strftime("%Y")
				current_month = now.strftime("%-m")
				current_day = now.strftime("%-d")
				alarm_hr = threadcontrol.alarmconfig['alarm']['alarm_hour']
				alarm_min = threadcontrol.alarmconfig['alarm']['alarm_minute']
				alarm_playtime = threadcontrol.alarmconfig['alarm']['playtime']
				alarm_greentime = threadcontrol.alarmconfig['alarm']['greentime']
				alarm_dt = datetime(year=int(current_year), month=int(current_month), day=int(current_day), hour=int(alarm_hr), minute=int(alarm_min))
				playtime_dt = alarm_dt - timedelta(minutes=int(alarm_playtime))
				greentime_dt = alarm_dt + timedelta(minutes=int(alarm_greentime)) 
				if now > playtime_dt and now < alarm_dt :
					#Orange Time
					self._set_yellow_LED()
					alarmtriggered = 1
				elif now > alarm_dt and now < greentime_dt :
					#Green Time
					self._set_green_LED()
				elif now > greentime_dt and alarmtriggered == 1:
					#No Light
					self._clear_LED()
					threadcontrol.alarmconfig.set('alarm','alarmset','0')
					threadcontrol.lock.acquire()
					with open(threadcontrol.alarmfile,'w') as f:
						threadcontrol.alarmconfig.write(f)
					threadcontrol.lock.release()
					alarmtriggered = 0
				else:
					#Red Light
					self._set_red_LED()
					
					
			else:
				self._clear_LED()
			time.sleep(2)

	def cleanup(self):
		self._rdr.cleanup()
		GPIO.cleanup()
		threadcontrol.controlsig = False

class WebAdmin(object):
	@cherrypy.expose
	def index(self, **formdata):
		if len(formdata) > 0:
			#If data posted back to the page
			resp = {}
			for option in formdata:
				print ("submitted option: " + str(option) + " Value: " + str(formdata[option]))
				resp[option] = formdata[str(option)]
				if option == 'status':
					threadcontrol.alarmconfig.set('alarm','alarmset',resp[option])
				elif option == 'alarm_time_hour':
					threadcontrol.alarmconfig.set('alarm','alarm_hour',resp[option])
				elif option == 'alarm_time_min':
					threadcontrol.alarmconfig.set('alarm','alarm_minute',resp[option])
				elif option == 'quiet_time_min':
					threadcontrol.alarmconfig.set('alarm','playtime',resp[option])    
					#write changes out to ini file
				threadcontrol.lock.acquire()
				with open(threadcontrol.alarmfile,'w') as f:
					threadcontrol.alarmconfig.write(f)
				threadcontrol.lock.release()
			time.sleep(2)
			resp['state'] = threadcontrol.alarmstate
			tmpl = env.get_template('config.html')
			return tmpl.render(config=resp, result="updated")
		else : # if no data submitted
			results = {}
			results['status'] = threadcontrol.alarmconfig['alarm']['alarmset'] #used to determine if alarm is enabled
			results['alarm_time_hour'] = threadcontrol.alarmconfig['alarm']['alarm_hour']
			results['alarm_time_min'] = threadcontrol.alarmconfig['alarm']['alarm_minute']
			results['quiet_time_min'] = threadcontrol.alarmconfig['alarm']['playtime']
			results['state'] = threadcontrol.alarmstate
			tmpl = env.get_template('config.html')
			return tmpl.render(config=results)

def format_2digitnumber(value):
	value = str(value).zfill(2)
	return value

def startwebadmin():
	#Start Web Admin
	cherrypy.quickstart(WebAdmin(),'/','/mnt/development/python/aclock/clock/web/webapp.config')

def stopwebadmin():
	cherrypy.engine.exit()

#Define Web Admin Environment
env = Environment(loader=FileSystemLoader('/mnt/development/python/aclock/clock/web/templates'))
env.filters['f2digit'] = format_2digitnumber

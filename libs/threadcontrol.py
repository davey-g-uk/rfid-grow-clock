#!/usr/bin/python3

import threading
from .audiohandler import audiohandler, displayhandler, displayupdate
import configparser


class threadcontrol(object):
    threads = list()
    lock = threading.Lock()
    controlsig = True
    hifi = audiohandler()
    displayhandler = displayhandler()
    displayupdate = displayupdate()
    alarmconfig = configparser.ConfigParser()
    alarmfile = "./db/alarm.ini"
    alarmconfig.read(alarmfile)
    alarmstate = 0
    



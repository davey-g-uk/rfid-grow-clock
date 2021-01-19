import os
import sys
import vlc
import eyed3
import subprocess
import pathlib
import time
import configparser
import threading
from .oled.oled_pi import OLED
from .oled.oled_window import OLEDWindow
from datetime import datetime
from .displayfonts import displayfonts
from .weather import weather

playmode = 0 #(0 - notset, 1 - MP3, 2 - CD)

class audiohandler(object):
    def __init__(self):
        self.instance = vlc.Instance('--quiet', '--aout=alsa')
        self.player = self.instance.media_player_new()
        self.listplayer = self.instance.media_list_player_new()
        self.listplayer.set_media_player(self.player)
        self.playlist = {}
        self.player.audio_set_volume(30)
        self.volume = self.player.audio_get_volume()
        self.currenttrack = 0
        self.status = 0 #(0 - stopped, 1 - playing, 2 - paused, 3 - ended)
        #self.playmode = 0 #(0 - notset, 1 - MP3, 2 - CD)
        self.playlistready = 0
        self.trackdbconfig = "./db/tracks.ini"
        self.trackdb = configparser.ConfigParser()
        self.trackdb.read(self.trackdbconfig)
        self._displayupdate = displayupdate()
        
        _mediaplayer_events = self.player.event_manager()
        _listplayer_events = self.listplayer.event_manager()
        _listplayer_events.event_attach(vlc.EventType.MediaListPlayerNextItemSet, self. _handler_nextitem)
        _listplayer_events.event_attach(vlc.EventType.MediaListEndReached, self._handler_playlistend)
        _listplayer_events.event_attach(vlc.EventType.MediaListPlayerStopped , self._handler_playerstopped)
        _mediaplayer_events.event_attach(vlc.EventType.MediaPlayerEndReached, self._handler_playlistend)
        _mediaplayer_events.event_attach(vlc.EventType.MediaPlayerStopped , self._handler_playerstopped)

        
    def playmp3playlist(self, folder,cardtitle):
        global playmode
        self._displayupdate.showtext(2,"Loading " + cardtitle)
        playlist = {}
        filelist = []
        self.stopplayer()
        print("playmode:" + str(playmode))
        if playmode > 0:
            print("Player already playing, stopping")
            self.stopplayer()
        medialist = self.instance.media_list_new()
        for r, d, f in os.walk(folder):
            for file in f:
                if file.endswith(".mp3"):
                    filelist.append(os.path.join(r,file))
        for track in sorted(filelist):
            medialist.add_media(self.instance.media_new(track))
        self.listplayer.set_media_list(medialist)
        self.currenttrack = 0
        self._play()
        self.status = 1
        playmode = 1
        for track in sorted(filelist):
            print("Adding details to playlist for MP3: " + track)
            trackdetails = self.gettrackdetails(track)
            print("Track:" + str(trackdetails['trackno']))
            playlist[trackdetails['trackno']] = {
                "file" : track,
                "title" : trackdetails['title'],
                "album" : trackdetails['album'],
                }
        self.playlist = playlist
        self.playlistready = 1
        print ("player playing?" + str(self.listplayer.is_playing()))
        while not self.listplayer.is_playing():
            print("waiting for player")
            time.sleep(0.5)
        displaytxt = str(self.currenttrack) + "-" + self.playlist[str(self.currenttrack)]['title']
        self._displayupdate.showtext(1,self.playlist[str(self.currenttrack)]['album'])
        self._displayupdate.showtext(2,displaytxt)
        

    def playcdplaylist(self):
        global playmode
        if playmode != 2:
            if self.status == 1 or self.status == 2:
                self.stopplayer()
            self._displayupdate.cleartext(1)
            self._displayupdate.cleartext(2)
            self._displayupdate.showtext(2,"Loading CD")
            playlist = {}
            subprocess.call(["eject","-x","4","/dev/cdrom"])
            cdtrack_count = self.checkcd()
            if cdtrack_count > 0:
                medialist = self.instance.media_list_new()
                cdtracks = self.instance.media_new('cdda:///dev/cdrom')
                medialist.add_media(cdtracks)
                self.listplayer.set_media_list(medialist)
                for x in range(1,cdtrack_count+1):
                    print("Adding cd track to playlist :" + str(x))
                    file_str = "CD Track" + str(x)
                    playlist[str(x)] = {
                        "file" : file_str,
                        "title" : file_str,
                        "album" : "CD Audio",
                        }
                playlist["0"] = {
                    "file" : "CD Loading",
                    "title" : "CD Loading",
                    "album" : "CD Loading",
                    }
                self.playlist = playlist
                self.playlistready = 1
                displaytxt = str(self.currenttrack) + "-" + self.playlist[str(self.currenttrack)]['title']
                self.currenttrack = -1
                self._play()
                self.status = 1
                playmode = 2
                self._displayupdate.showtext(2,displaytxt)
                print("playing CD playmode :" + str(playmode))
            else:
                print("No CD in Drive")
        else:
            print("CD Already playing")
  
    def _play(self):
        self._displayupdate.showsymbol("play")
        volume = self.player.audio_get_volume()
        self.player.audio_set_volume(volume)
        self.listplayer.play()
        self.status = 1
    
    def _pause(self):
        self._displayupdate.showsymbol("pause")
        self.listplayer.pause()
        self.status = 2
    
    def stopplayer(self):
        global playmode
        print("Stop")
        self.listplayer.stop()
        self.currenttrack = 0
        self.status = 0
        playmode = 0
        self.playlistready = 0
    
    def playbutton(self):
        if self.status == 2:
            self._play()
            print("Play")
        elif self.status == 1:
            self._pause()
            print("Pause")

    def next(self):
        if self.status == 1 and self.playlistready == 1:
            if self.currenttrack < int(max(self.playlist, key=int)):
                self.listplayer.next()
        print("track" + str(self.currenttrack))
            
    def previous(self):
        if self.status == 1 and self.playlistready == 1:
            if self.currenttrack > 1:
                self.currenttrack = self.currenttrack - 2
                self.listplayer.previous()
        print("previouse method : track" + str(self.currenttrack))
        
    def volumeup(self):
        self.volume = self.player.audio_get_volume()
        if self.volume <= 95: 
            new_vol = self.volume + 5
            self.player.audio_set_volume(new_vol)
            self.volume = self.player.audio_get_volume()
            self._displayupdate.showvol(str(new_vol))
    
    def volumedown(self):
        self.volume = self.player.audio_get_volume()
        if self.volume >= 5:
            new_vol = self.volume - 5
            self.player.audio_set_volume(self.volume - 5)
            self.volume = self.player.audio_get_volume()
            self._displayupdate.showvol(str(new_vol))
        
    def current_volume(self):
        current_volume = self.player.audio_get_volume()
        print("audiohandler current volume" + str(current_volume)) 
        return current_volume
    
    def cd_eject(self):
        self.stopplayer()
        subprocess.call(["eject"])
        
    def _handler_nextitem(self, event):
        global playmode
        self.currenttrack = self.currenttrack + 1
        #update to call display update when class written
        time.sleep(0.3)
        if self.playlistready == 0 and playmode == 1:
            self._displayupdate.showtext(2,"Loading MP3 Playlist")
        elif self.playlistready == 0 and playmode == 2:
            self._displayupdate.showtext(2,"Playing CD")
        elif self.playlistready == 1:
            displaytxt = str(self.currenttrack) + "-" + self.playlist[str(self.currenttrack)]['title']
            print("Display update: " + displaytxt)
            self._displayupdate.showtext(2,displaytxt)
        print ("playing next track")
        print("track" + str(self.currenttrack))
    
    def _handler_playlistend(self, event):
        global playmode
        self.currenttrack = 0
        self.status = 3
        playmode = 0
        print("end of playlist")
        self._displayupdate.cleartext(1)
        self._displayupdate.cleartext(2)
        #update to clear display
    
    def _handler_playerstopped(self, event):
        global playmode
        self.currenttrack = 0
        self.status = 0
        playmode = 0
        print("player stopped")
        self._displayupdate.cleartext(1)
        self._displayupdate.cleartext(2)
        self._displayupdate.showsymbol("clear")
        #update to clear display

    def checkcd(self):
        output = str(subprocess.check_output(["setcd","-i"]), 'utf-8')
        lines =  output.splitlines()
        if lines[1].find("not ready") > 0:
            print("Not Ready")
            time.sleep(1)
            return self.checkcd()
        if lines[1].find("open") > 0:
            print("No CD")
            return -1
        if lines[1].find("Disc found") > 0:
            tracks = int(lines[2].split()[0])
            print("CD Found Tracks: " + str(tracks))
            return tracks

    def gettrackdetails(self,trackfile):
        returndata = {}
        self.trackdb.read(self.trackdbconfig)
        if not self.trackdb.has_section(trackfile):
            audiofile = eyed3.load(trackfile)
            returndata['trackno'] =  str(audiofile.tag.track_num[0])
            returndata['title'] = str(audiofile.tag.title)
            returndata['album'] = str(audiofile.tag.album)
            self.trackdb.add_section(trackfile)
            self.trackdb.set(trackfile,'trackno',returndata['trackno'])
            self.trackdb.set(trackfile,'title',returndata['title'])
            self.trackdb.set(trackfile,'album',returndata['album'])
            with open(self.trackdbconfig,'w') as f:
                self.trackdb.write(f)
        else:
            returndata['trackno'] =  self.trackdb[trackfile]['trackno']
            returndata['title'] = self.trackdb[trackfile]['title']
            returndata['album'] = self.trackdb[trackfile]['album']
        return returndata
                        
class displayhandler(object):
    threads = list()
    lock = threading.Lock()
    oled = OLED()
    oled_win = OLEDWindow(oled,0,0,256,64)
    _volclear = -1
    def __init__(self):
        print("Setting up clock thread")
        self.clock = threading.Thread(target=self._thread_clock, args=("clock",))
        displayhandler.threads.append(self.clock)
        print("Starting clock threads")
        self.clock.start()
        self.weatherupdater = threading.Thread(target=self._thread_weather, args=("weather",))
        displayhandler.threads.append(self.weatherupdater)
        print("Starting Weather Thread")
        self.weatherupdater.start()

    def _thread_clock(self,id):
        lastrun_timelength = 4
        lastrun_time = ""
        while True:
            now = datetime.now()
            current_time = now.strftime("%-I:%M")
            if current_time != lastrun_time:
                currentrun_timelength = len(current_time)
                if currentrun_timelength < lastrun_timelength :
                    clrclkdisplay = True
                else:
                    clrclkdisplay = False
                if len(current_time) == 5:
                    xstart = 68
                else:
                    xstart = 80
                displayhandler.lock.acquire()
                if clrclkdisplay:
                    displayhandler.oled_win.draw_bw_image(68,0,24,48,8,displayfonts.CLK[" "],0)
                    displayhandler.oled_win.draw_bw_image(164,0,24,48,8,displayfonts.CLK[" "],0)
                try:
                    for c in range(len(current_time)):
                        displayhandler.oled_win.draw_bw_image(xstart,0,24,48,8,displayfonts.CLK[current_time[c]],0)
                        xstart = xstart + 24 
                    displayhandler.oled_win.draw_screen_buffer()
                    displayhandler.lock.release()
                finally:
                    lastrun_timelength = currentrun_timelength
                if displayhandler._volclear == 0:
                    displayhandler.lock.acquire()
                    displayhandler.oled_win.draw_text(200,32,"       ",8)
                    displayhandler.oled_win.draw_screen_buffer()
                    displayhandler.lock.release()
                    displayhandler._volclear = -1
                elif displayhandler._volclear > 0:
                    displayhandler._volclear = displayhandler._volclear - 1
            lastrun_time = current_time
            time.sleep(2)

    def _thread_weather(self,id):
        while True:
            print("Checking Weather")
            myweather = weather()
            symbol = myweather.getweather()
            displayhandler.lock.acquire()
            displayhandler.oled_win.draw_bw_image(4,4,32,32,8,displayfonts.WEATHER[symbol],0)
            displayhandler.oled_win.draw_screen_buffer()
            displayhandler.lock.release()
            time.sleep(900)
            



class displayupdate(object):
    lcount = 0
    def __init__(self):
        pass
    
    def _getlinestart(self,line):
        if line == 1:
            return 47
        elif line == 2:
            return 55
        else:
            return 47
        
    def showtext(self,line,text):
        clearstr = "                                "
        displaytext = text[0:32]
        displayhandler.lock.acquire()
        displayhandler.oled_win.draw_text(2,self._getlinestart(line),clearstr,8)
        displayhandler.oled_win.draw_text(2,self._getlinestart(line),displaytext,8)
        displayhandler.oled_win.draw_screen_buffer()
        displayhandler.lock.release()
    def cleartext(self,line):
        clearstr = "                                "
        displayhandler.lock.acquire()
        displayhandler.oled_win.draw_text(2,self._getlinestart(line),clearstr,8)
        displayhandler.oled_win.draw_screen_buffer()
        displayhandler.lock.release()

    def showsymbol(self,symbol):
        displayhandler.lock.acquire()
        displayhandler.oled_win.draw_bw_image(239,0,16,16,8,displayfonts.SYM[symbol],0)
        displayhandler.oled_win.draw_screen_buffer()
        displayhandler.lock.release()

    def showvol(self,volume):
        if int(volume) < 10:
            volume = "0"+str(volume)
        elif int(volume) == 100:
            volume = "MAX"
        if len(str(volume)) < 3:
            volume = volume + " "
        displayhandler.lock.acquire()
        displayhandler.oled_win.draw_text(200,32,"Vol:"+str(volume),8)
        displayhandler.oled_win.draw_screen_buffer()
        displayhandler._volclear = 3
        displayhandler.lock.release()    



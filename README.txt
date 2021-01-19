Author - David Gardner

Credits - 
topherCantrell - for creating the OLED drivers I have utilised on this project, 
I have made a number of changes to his drivers (including inverting the display)
original drivers can be found here :https://github.com/topherCantrell/ER-OLEDM032-1

ondryaso - for creating the pirc522 drivers I used for my RFID reader, these
were the only drivers I could find with interrupt support, the other widely 
available drivers used a while True loop to pick up state change, this used 
up too much CPU resource on the Pi

Other Modules - 
In order to directly re-use my code you would need to install some other python packages
these were:

cherrypy
jinja2
configparser
vlc (this also needs the vlc application to be installed)
eyed3
pyowm

Other notes - 
If trying to run my code you will need to do a couple of things:

1. Set the root directory in the libs/webapp.py file
2. Create your Open Weather Map weather API key (openweathermap.org) and update this in the db/weather.ini file
3. Check the logs and update your CardID's in the db/cards.ini file
4. tracks.ini is basically a local cache DB that gets created when MP3 files are read for the first time and populated from the ID3 tags
	this process is slow hence the ini cache file, but you dont need to manually populate

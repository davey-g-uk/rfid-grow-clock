import cherrypy
from jinja2 import Environment, FileSystemLoader
from .threadcontrol import threadcontrol

class WebAdmin(object):
    @cherrypy.expose
    def index(self, **formdata):
        if len(formdata) > 0:
            #If data posted back to the page
            resp = {}
            for option in formdata:
                print "submitted option: " + str(option) + " Value: " + str(formdata[option])
                resp[option] = formdata[str(option)]
                if option == 'status':
                    threadcontrol.alarmconfig['alarm']['alarmset'] = resp[option]
                elif option == 'alarm_time_hour':
                    threadcontrol.alarmconfig['alarm']['alarm_hour'] = resp[option]
                elif option == 'alarm_time_min':
                    threadcontrol.alarmconfig['alarm']['alarm_min'] = resp[option]
                elif option == 'quiet_time_min':
                    threadcontrol.alarmconfig['alarm']['playtime'] = resp[option]    
                #write changes out to ini file
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
    cherrypy.quickstart(WebAdmin(),'/','/mnt/development/python/aclock/clock/web') #Need to updated to absolute file path of code, cherrypy doesnt like relative addressing

def stopwebadmin():
    cherrypy.engine.exit()
    
#Define Web Admin Environment
env = Environment(loader=FileSystemLoader('/mnt/development/python/aclock/clock/web/templates')) #Need to updated to absolute file path of tempalates directory, cherrypy doesnt like relative addressing
env.filters['f2digit'] = format_2digitnumber

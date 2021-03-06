# This is Retort, a thing to boil iKettles in Flask.
# It is built on the shoulders of giants.
#
# This is the kettle access library. Most of it is from 
# Mark J Cox's GUI project (https://github.com/iamamoose/moosekettle) because 
# it does the socket stuff, and I'm a web guy who doesn't understand sockets.
# 
# I've added the Find Kettle function, although currently it has no memory. Brute force
# appears to be the only way

# protocol: http://www.awe.com/mark/blog/20140223.html
#
# things to do: 
#    Remove the hardcoding to my IP range
#    Apologise to a lot of networking engineers
#    Keep better state
#    Work more proper.
#
# Nicholas 'Aquarion' Avenell 2015

import socket
import sys
import ConfigParser
import logging

from events import Events

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit


class Kettle():

    config = False

    kettleconnected = 0
    current_temp = False
    is_boiling = False
    was_boiling = False
    is_warm = False
    ip = False

    ip_range = False

    is_boiling = False

    events = False

    def __init__(self):
        self.events = Events()


        import atexit
        scheduler = BackgroundScheduler()
        scheduler.start()
        scheduler.add_job(
            func=self.update_status,
            trigger=IntervalTrigger(seconds=5),
            id='checking_status',
            name='Check kettle status (keepalive)',
            replace_existing=True)

        atexit.register(lambda: scheduler.shutdown())

        return self.initialise()



    def initialise(self):

        self.config = ConfigParser.ConfigParser()
        sucess = self.config.read('ikettle.conf')

        logger = logging.getLogger("Kettle")
        logging.basicConfig(level=logging.DEBUG)

        try:
            items = self.config.items("Logging")
            try:
                logfile =  self.config.get('Logging', 'filename')
            except ConfigParser.NoOptionError:
                logfile = False

            try:
                levelname =  self.config.get('Logging', 'level')
                level = logging.getLevelName('INFO')
            except ConfigParser.NoOptionError:
                level = "WARNING"

            logging.info("Logging to %s @ %s" % (logfile, level))
            logging.basicConfig(filename=logfile, level=level)

        except ConfigParser.NoSectionError:
            logging.basicConfig(level=logging.DEBUG)


        try:
            self.ip = self.config.get('Network', 'kettleip')
            self.ip_range = self.config.get('Network', 'ip_range')
        except ConfigParser.NoSectionError:
            self.config.add_section('Network')
        except ConfigParser.NoOptionError:
            pass

        if not self.ip_range:
            self.ip_range = "192.168.0.%d"
            self.config.set('Network', 'ip_range', self.ip_range)
            self.save_config()

        self.kettleconnected = 0

        if not self.ip or not self.ask_if_kettle(self.ip):
            self.ip = self.find(self.ip_range)
            self.config.set('Network', 'kettleip', self.ip)
            self.save_config()

        if self.ip:
            logging.info("Found kettle on %s" % self.ip)
        else:
            raise Exception("Kettle Not Found")

        self.kconnect()
        self.update_status()

    def save_config(self):
        # Writing our configuration file to 'example.cfg'
        with open('ikettle.conf', 'wb') as configfile:
            self.config.write(configfile)


    def set_temp(self, temp):
        
        if not self.is_boiling:
            self.kettlesend("set sys output 0x4")

        temperatures = {
            '100' : '0x80',
            '95'  : '0x2',
            '80'  : '0x4000',
            '65'  : '0x200'
        }

        if not self.is_boiling:
            logging.info("Won't set temperature until it's boiling")
            return False

        if temp in temperatures:
            self.kettlesend("set sys output %s" % temperatures[temp])

        self.events.temp_changed(temp)

        return True
        #self.bwarm.connect("clicked", self.clicksend, "set sys output 0x8")
        


    def clickboil(self):
        if not self.is_boiling:
            self.kettlesend("set sys output 0x4")
        else:
            self.kettlesend("set sys output 0x0")

    def togglewarm(self):
        self.events.kettle_warm()
        self.kettlesend("set sys output 0x8")

    def stopboil(self):
        self.events.kettle_stop()
        self.kettlesend("set sys output 0x0")

    def kettlesend(self, data, retry=False):
        try:
            logging.info(">>> %s " % data)

            self.sock.send(data+"\n")
            line = self.sock.recv(4096)
            self.handler(line)
        except (socket.error, IOError), e:
            logging.error(">>> %s: %s " % (e.__class__.__name__, e ) )

            if retry:
                logging.error(">>> Failed again. Fool me once...")
                raise
            else:
                logging.info(">>> Attempting to reinit")
                self.initialise()
                self.kettlesend(data, True)


    def gotofail(self):
        logging.info("Closing")
        try:
            self.sock.close()
        except:
            pass

    def kconnect(self):
        if (not self.ip):
            self.ip = self.get_ip("Enter IP Address of Kettle","127.0.0.1")
            if (not self.ip):
                return
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # self.sock.settimeout(500)
            self.sock.connect((self.ip,2000))
            self.sock.send("HELLOKETTLE\n")
            self.events.kettle_connected()
            return True
        except:
            self.ip=""  # the one given didnt work
            return False

    def update_status(self):
        self.kettlesend("get sys status")
        return self.current_status()

    def latest_status(self):
        return self.current_status()

    def check_connected(self):
        if (self.kettleconnected == 0):
            try:
                self.sock.close()
            except:
                pass

    def handler(self, line):

        logging.info(line)
        if not len(line):  # "Connection closed."
            self.kconnect()
            return False
        else:
            for myline in line.splitlines():
                logging.info("<<< %s " % myline)
                if (myline.startswith("HELLOAPP")):
                    self.kettleconnected = 1
                    self.update_status()
                if (myline.startswith("sys status key=")):
                    if (len(myline)<16):
                        key = 0
                    else:
                        key = ord(myline[15]) & 0x3f

                        logging.info("100:  %s " % (key))

                        # logging.info("100:  %s " % (key&0x20))
                        # logging.info("95:   %s " % (key&0x10))
                        # logging.info("80:   %s " % (key&0x8))
                        # logging.info("65:   %s " % (key&0x4))
                        # logging.info("Warm: %s " % (key&0x2))
                        # logging.info("Boil: %s " % (key&0x1))

                        self.current_temp = 100

                        if key&0x20:
                            self.current_temp = 100
                        elif key&0x10:
                            self.current_temp = 95
                        elif key&0x8:
                            self.current_temp = 80
                        elif key&0x4:
                            self.current_temp = 65

                        if key&0x2:
                            self.is_warm = True
                        else:
                            self.is_warm = False

                        if key&0x1:
                            self.is_boiling = True
                            if self.was_boiling == False:
                                self.events.kettle_start()
                            self.was_boiling = True

                        else:
                            self.is_boiling = False
                            if self.was_boiling == True:
                                self.events.kettle_stop()
                            self.was_boiling = False

                if (myline == "sys status 0x100"):
                    logging.info("<<<   Temp is 100")
                    self.current_temp = '100'
                elif (myline == "sys status 0x95"):
                    logging.info("<<<   Temp is 95")
                    self.current_temp = '95'
                elif (myline == "sys status 0x80"):
                    logging.info("<<<   Temp is 80")
                    self.current_temp = '80'
                elif (myline == "sys status 0x65"):
                    logging.info("<<<   Temp is 65")
                    self.current_temp = '65'
                elif (myline == "sys status 0x8"):
                    logging.info("<<<   Warming toggled")
                    #self.is_warm = True ## Rely on status update for this
                elif (myline == "sys status 0x5"):
                    logging.info("<<<   Boiling? True")
                    self.is_boiling = True
                elif (myline == "sys status 0x0"):
                    logging.info("<<<   RESET")
                    self.is_boiling = False
                    self.is_warm = False
                    self.current_temp = False
                elif (myline == "sys status 0x3"):
                    logging.info("<<<   Recently finished boiling")
                    self.is_boiling = False
                    self.has_boiled = True
                elif (myline == "sys status 0x1"):
                    logging.info("<<<   Standby")
                    self.is_boiling = False
                    self.has_boiled = False

            return True

    def print_status(self):
        logging.info(self.current_status())

    def current_status(self):
        return {
            'is_boiling' : self.is_boiling,
            'temperature' : self.current_temp,
            'is_warming' : self.is_warm

        }

    def find(self, ip_range):
        logging.info("Looking for iKettle in range %s" % ip_range)


        for n in range(1,255):
            ip = ip_range % n
            
            if self.ask_if_kettle(ip):
                return ip

        return False

    def ask_if_kettle(self, ip):
        logging.info(ip,)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(.2)
            sock.connect((ip, 2000))
            logging.info(" - Responded")
            logging.info(" - Are you a kettle?")

            try:
                sock.settimeout(30)
                sock.send("HELLOKETTLE\n")
                response = sock.recv(4096)
                if response.startswith("HELLOAPP"):
                    logging.info(" - Yes!")
                    return True
                else:
                    logging.info("No! %s" % response)
            except socket.timeout:
                logging.info(" - No, you are not.")


        except socket.timeout:
            logging.info(" - Timeout" )
        except socket.error:
            logging.info(" - Refused")
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logging.info(exc_type, exc_obj)
        sock.close()

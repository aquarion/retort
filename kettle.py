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


class Kettle():

    config = False

    kettleconnected = 0
    current_temp = False
    is_boiling = False
    is_warm = False
    configip = 0
    ip = False

    ip_range = False

    is_boiling = False

    def __init__(self, configip, argip):
	logger = logging.getLogger("Kettle")

        self.config = ConfigParser.ConfigParser()
        sucess = self.config.read('ikettle.conf')

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
        #self.configip = configip
        #self.ip = configip

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

        return True
        #self.bwarm.connect("clicked", self.clicksend, "set sys output 0x8")
        


    def clickboil(self):
        if not self.is_boiling:
            self.kettlesend("set sys output 0x4")
        else:
            self.kettlesend("set sys output 0x0")

    def togglewarm(self):
        self.kettlesend("set sys output 0x8")

    def stopboil(self):
        self.kettlesend("set sys output 0x0")

    def kettlesend(self, data):
        logging.info(">>> %s " % data)
        self.sock.send(data+"\n")
        line = self.sock.recv(4096)
        self.handler(line)


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
            return True
        except:
            self.ip=""  # the one given didnt work
            return False

    def update_status(self):
        self.kettlesend("get sys status")
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
                        else:
                            self.is_boiling = False

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

            self.print_status()
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

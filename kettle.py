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

class Kettle():

    kettleconnected = 0
    current_temp = False
    is_boiling = False
    is_warm = False
    configip = 0
    ip = 0

    ip_range = "192.168.0.%d"

    is_boiling = False

    def __init__(self, configip, argip):
        self.kettleconnected = 0
        self.configip = configip
        self.ip = configip
        if (argip):
            self.ip = argip

        if not self.ip:
            self.ip = self.find(self.ip_range)

        if not self.ip:
            raise Exception("Kettle Not Found")

        self.kconnect()
        self.update_status()


    def set_temp(self, temp):

        temperatures = {
            '100' : '0x80',
            '95'  : '0x2',
            '80'  : '0x4000',
            '65'  : '0x200'
        }

        if temp in temperatures:
            self.kettlesend("set sys output %s" % temperatures[temp])

        self.bwarm.connect("clicked", self.clicksend, "set sys output 0x8")
        


    def clickboil(self):
        if not self.is_boiling:
            self.kettlesend("set sys output 0x4")
        else:
            self.kettlesend("set sys output 0x0")

    def stopboil(self):
        self.kettlesend("set sys output 0x0")

    def kettlesend(self, data):
        print ">>> %s " % data
        self.sock.send(data+"\n")
        line = self.sock.recv(4096)
        self.handler(line)


    def gotofail(self):
        print "Closing"
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
            self.sock.connect((self.ip,2000))
            self.sock.send("HELLOKETTLE\n")
            return True
        except:
            self.ip=""  # the one given didnt work
            return False

    def update_status(self):
        self.kettlesend("get sys status")

    def check_connected(self):
        if (self.kettleconnected == 0):
            try:
                self.sock.close()
            except:
                pass

    def handler(self, line):

        print line
        if not len(line):  # "Connection closed."
            self.kconnect()
            return False
        else:
            for myline in line.splitlines():
                print "<<< %s " % myline
                if (myline.startswith("HELLOAPP")):
                    self.kettleconnected = 1
                    self.update_status()
                if (myline.startswith("sys status key=")):
                    if (len(myline)<16):
                        key = 0
                    else:
                        key = ord(myline[15]) & 0x3f
                if (myline == "sys status 0x100"):
                    self.current_temp = '100'
                elif (myline == "sys status 0x95"):
                    self.current_temp = '95'
                elif (myline == "sys status 0x80"):
                    self.current_temp = '80'
                elif (myline == "sys status 0x65"):
                    self.current_temp = '65'
                elif (myline == "sys status 0x11"):
                    self.is_warm = False
                elif (myline == "sys status 0x10"):
                    self.is_warm = True
                elif (myline == "sys status 0x5"):
                    self.is_boiling = True
                elif (myline == "sys status 0x0"):
                    self.is_boiling = False
                    self.is_warm = False
                    self.current_temp = False
                elif (myline == "sys status 0x3"):
                    self.is_boiling = False
                    self.has_boiled = True
                elif (myline == "sys status 0x1"):
                    self.is_boiling = False
                    self.has_boiled = False

            self.print_status()
            return True

    def print_status(self):
        print self.current_status()

    def current_status(self):
        return {
            'is_boiling' : self.is_boiling,
            'temperature' : self.current_temp,
            'is_warming' : self.is_warm

        }

    def find(self, ip_range):
        print "Looking for iKettle in range %s" % ip_range


        for n in range(1,255):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            ip = ip_range % n
            
            print ip
            try:
                sock.connect((ip, 2000))
                print " - Responded"
                print " - Are you a kettle?"

                try:
                    sock.settimeout(30)
                    sock.send("HELLOKETTLE\n")
                    response = sock.recv(4096)
                    if response.startswith("HELLOAPP"):
                        print " - Yes!"
                        return ip
                    else:
                        print "No! %s" % response
                except socket.timeout:
                    print " - No, you are not."


            except socket.timeout:
                print " - Timeout" 
            except socket.error:
                print " - Refused"
            except Exception as e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                print exc_type, exc_obj
            sock.close()

        return False
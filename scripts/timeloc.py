from BeautifulSoup import BeautifulSoup
import urllib2
import re

import sys
import argparse

sys.path.append("~/project")

_CMD_NAME = "Tm"
_CMD_LONG_NAME = "Timeloc"

class ArgumentParser(argparse.ArgumentParser):
    def error(self, message=None):
        raise

class Timeloc(object):
    def __init__(self, options, sm, number, signature):
        self.flag=1
        self.privilaged = False
        self.msg = ""
        self.to_no = number
        self.sm = sm
        self.options = options
        self.sig = signature
        self.parser = ArgumentParser(description = "Argument parser get current date and time of a specific Location")
        self.parser.add_argument("location",help="the location whose date and time is required",action="store")
        try:
            self.arguments = self.parser.parse_args(self.options)
        except:
            self.msg='usage:Datetime location"'
            self.flag=0
            return
        
        
    def getdatetime(self):
        self.arguments.location=self.arguments.location.replace(" ","_")

        self.url = "http://www.time.is/"+self.arguments.location

        try:
            page = urllib2.urlopen(self.url)
        except:
            self.msg="Internet connection error or Location not found"
            return

        try:            
            soup = BeautifulSoup(page.read())
            
            time = "Time(HH: MM: SS): "+soup.find('div', {'id' : 'clock0_bg'}).find(id="twd").contents[0]          
            locname = soup.find('a',href=re.compile('/facts/*')).contents[0]
          #  date = soup.find('h2',id="dd").contents[0]
        except Exception,e:
            print e
            
            self.msg="Location not found"
            return

        a = [locname,time]
        for i in range(len(a)):
            self.msg+= a[i]+"\n"


    def send_sms(self):
        if self.flag==1:
            self.getdatetime()
        msg = {
                'Text' : self.msg,
                'SMSC' : {'Location' : 1},
                'Number' : self.to_no,
                }
        self.sm.SendSMS(msg)
        print self.msg
       
#a=Datetimemod(["new york"],"123","123","123")
#a.send_sms()



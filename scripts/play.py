
import os
import sys
import argparse
import subprocess

sys.path.append("~/project")

_CMD_NAME = "Pl"
_CMD_LONG_NAME = "Play"

class ArgumentParser(argparse.ArgumentParser):
    def error(self, message=None):
        raise

class Play(object):
    def __init__(self, options, sm, number, signature):
        self.flag=1      
        self.privilaged =True
        self.msg = ""
        self.to_no = number
        self.sm = sm
        self.options = options
        self.sig = signature
        self.parser = argparse.ArgumentParser(description = "Argument parser for playing a video")
        self.parser.add_argument("fname",help="specify the file name",action="store")
        self.parser.add_argument("partialpath",help="specify partial path",action="store")
        try:
            self.arguments = self.parser.parse_args(self.options)
        except:
            self.msg="usage: Play fname path"
            self.flag=0
            return

            
    def searchFile(self):
        flag=0
        for i in os.walk(self.arguments.partialpath):
            for j in i[2]:
                # print j
                if j.endswith(self.arguments.fname):
                   # print j.endswith(self.arguments.filename)
                    base=os.path.abspath(i[0])
                    m=os.name
                  #  print m
                    if m=="posix":
                        self.fullpath=base+"/" + self.arguments.fname
                    else:
                        self.fullpath=base+"\\" + self.arguments.fname
                    flag=1
                    break
            if flag==1:
                break
        if flag==1:
            self.playVid()
        else:
            self.msg="Invalid file name or path !"
            return

    def playVid(self):
        try: #this is for windows
            os.startfile(self.fullpath)
            self.msg="Video successfully Played"
        except: #this is for linux
            subprocess.Popen(['xdg-open',self.fullpath])
            self.msg="Video successfully Played"

    def send_sms(self):
        if self.flag==1:            
            self.searchFile()
            msg = {
                    'Text' : self.msg,
                    'SMSC' : {'Location' : 1},
                    'Number' : self.to_no,
                    }
            print self.msg
            self.sm.SendSMS(msg)
               

#a=Play(['video.mp4','/home'],"asdf","adsf","adsf")
#a.send_sms()


import os
import sys
import argparse
import subprocess

sys.path.append("~/project")

_CMD_NAME = "Fprnt"
_CMD_LONG_NAME = "Fprint"

class ArgumentParser(argparse.ArgumentParser):
    def error(self, message=None):
        raise


class Fprint(object):
    def __init__(self, options, sm, number, signature):
        self.flag=1
        self.privilaged = False
        self.msg = ""
        self.to_no = number
        self.sm = sm
        self.options = options
        self.sig = signature
        self.parser = ArgumentParser(description = "Argument parser for printing a file")
        self.parser.add_argument("-f","--filename",help="Name of the file to be printed",action="store")
        self.parser.add_argument("-p","--fpath",help="Path of the file",action="store")
        self.parser.add_argument("-n","--ncopies",help="number of copies",action="store",default="1")
        try:
            self.arguments = self.parser.parse_args(self.options)
        except:
            self.msg='usage:fprint -f filename -p path -n ncopies'
            self.flag=0
            return

            
    def printfile(self):
        if int(self.arguments.ncopies)>5:
            self.msg="Only 5 copies at a time"
            return
        cmd="lp -n "
        cmd+=self.arguments.ncopies+" "+self.fullpath
        try:
            os.system(cmd)
            self.msg="print successful"
        except:
            self.msg="error! Try again later "

                    
    def searchfile(self):
        flag=0
        for i in os.walk(self.arguments.fpath):
            for j in i[2]:
            #    print j
                if j.endswith(self.arguments.filename):
            #        print j.endswith(self.arguments.filename)
                    try:
                        base=os.path.abspath(i[0])
            #            print base
                    except:
                          self.msg="error .. try again later"
                    m=os.name
            #        print m
                    if m=="posix":
                        self.fullpath=base+"/"+self.arguments.filename
            #            print self.fullpath
                    else:
                        self.fullpath=base+"\\"+self.arguments.filename
            #            print self.fullpath
                    flag=1
                    break
            if flag==1:
                break
        if flag==1:
            self.printfile()
        else:
            self.msg="Invalid file name or path "
            return

    def send_sms(self):
        if self.flag==1:
            self.searchfile()
        msg = {
                'Text' : self.msg,
                'SMSC' : {'Location' : 1},
                'Number' : self.to_no,
                }
        self.sm.SendSMS(msg)
        print self.msg


        
#a=Fprint(['-f','a.txt','-p','/home'],"123","123","123")
#a.send_sms()

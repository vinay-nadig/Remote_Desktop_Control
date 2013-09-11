"""

CONSTRAINTS:    1) Can send messages to max 5 numbers at a time.
                2) Every valid number has 10 digits.
                3) No special characters allowed.
                4) The set of numbers should be enclosed within double quotes.
                5) The text message should also be enclosed within a seperate pair of double quotes.
                6) Even if one of the specified set of numbers is invalid, the entire message has to be sent again.
"""

import sys
import argparse

sys.path.append("~/project")

_CMD_NAME = "Blksms"
_CMD_LONG_NAME = "Bulksms"

class ArgumentParser(argparse.ArgumentParser):
    def error(self, message=None):
        raise

class Bulksms(object):
    def __init__(self, options, sm, number, signature):
        self.flag=1
        self.privilaged = False
        self.msg = ""
        self.to_no = number
        self.sm = sm
        self.options = options
        self.sig = signature
        self.parser = ArgumentParser(description = "Argument parser for sending sms to the specified list of numbers")
        self.parser.add_argument("-n","--numberlist",help="the list of numbers to which sms has to be sent",action="store")
        self.parser.add_argument("-t","--text",help="the common text message to be sent",action="store")
        try:
            self.arguments = self.parser.parse_args(self.options)
        except:
            self.msg='usage:Bulksms -t text -n "numbers(max 5)"'
            self.flag=0
            return
        
    def extract(self):
        self.num = self.arguments.numberlist.split('_')
        if(len(self.num)>5):
            self.msg="Enter only 5 nums"
            return
        
        for i in range(len(self.num)):
            if len(self.num[i])!=10:
                self.msg="Invalid number: "+self.num[i]
                return
            try:
                self.num[i]=int(self.num[i])
            except:
                self.msg="Invaid number: "+self.num[i]
                return
            
            msg = {
                'Text' : self.arguments.text,
                'SMSC' : {'Location' : 1},
                'Number' : self.num[i],
                }
            self.sm.SendSMS(msg)  
        self.msg="Message delivered"
            
    def send_sms(self):
        if self.flag==1:
            self.extract()
        msg = {
                'Text' : self.msg,
                'SMSC' : {'Location' : 1},
                'Number' : self.to_no,
                }
        print self.msg
        self.sm.SendSMS(msg)


#a=Bulksms(['-n','1234523452 1234123453 5121234534 3454343434 3333333333','-t','afaeth wr dhf hsd'],"123","123","123")
#a.send_sms()
       



import sys
import argparse

sys.path.append("~/project")

_CMD_NAME = "@Put your command name here@"
_CMD_LONG_NAME = "@Put your command long name here@"

class ArgumentParser(argparse.ArgumentParser):
    def error(self, message=None):
        pass

class <Class_Name>(object):
    def __init__(self, options, sm, number, signature):
        self.privilaged = <Enter True of False>         # Does this service need special privilages?
        self.parser = ArgumentParser()
        self.msg = ""                                   # The final msg that is sent
        self.to_no = number
        self.sm = sm
        self.options = options
        self.sig = signature
        self.arguments = self.parser.parse_args(self.options)

    def send_sms(self):
        # Call the generic function here
        msg = {
                'Text' : self.msg,
                'SMSC' : {'Location' : 1},
                'Number' : self.to_no,
                }
        self.sm.SendSMS(msg)

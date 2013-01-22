

class Base(object):
    def __init__(self, cmd_name, cmd_long_name, options):
        self.cmd_name = cmd_name
        self.cmd_short_name = cmd_short_name
        self.options = options

    def check(self):
        pass
    
    def send_sms(self):
        pass


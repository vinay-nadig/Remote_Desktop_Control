import os
import sys
import argparse
from core.base import Base

# Add the root folder of project to path
sys.path.append("~/project")

class Test(Base):
    def __init__(self, cmd_name, cmd_long_name, options):
        self.parser = argparse.ArgumentParser(description = "A Test argument parser.")
        self.parser.add_argument("-t1")
        # options should be in the form of string
        # that excludes the keyword
        self.arguments = self.parser.parse_arguments(options.split())
        super(Test, self).__init__(cmd_name, cmd_long_name, options)

    def do_something(self):
        pass


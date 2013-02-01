#!/usr/bin/env python

# Import all libraries
import os
import sys
import ConfigParser
import pygtk
import gtk
import sqlite3
import inspect
import threading

# Testing imports
# Remove after completion
from time import sleep

# Get the root directory and add to sys path
main_file = inspect.getfile(inspect.currentframe())
par_dir = os.path.abspath(os.path.join(main_file, os.pardir))
par_dir = os.path.abspath(os.path.join(par_dir, os.pardir))
sys.path.append(par_dir)


# Check for dependencies
try:
    import gammu
except ImportError:
    print "Install gammu module please"
    exit()

try:
    import bluetooth
except ImportError:
    print "Install bluetooth module please"
    exit()

# Make sure pygtk version > 2.0
pygtk.require('2.0')

# Check for super user permission
if(os.getuid() != 0):
    raise EnvironmentError, "Run as root please"
    exit()

# Other imports
from core import base

# Initialize gtk thread engine
gtk.gdk.threads_init()

# Global data
_WINDOWS = False
_LINUX = True
_GLADE_FILE = ''


class SMSGateway:
    """ Main GUI Class """
    def __init__(self, xml_file):
        
        # Get all widgets
        self.builder = gtk.Builder()
        self.builder.add_from_file(xml_file)
        self.main_window = self.builder.get_object("window1")
        self.dialog1 = self.builder.get_object("dialog1")
        self.selection_dialog1 = self.builder.get_object("dialog1")
        self.rb1 = self.builder.get_object("radiobutton1")
        self.rb2 = self.builder.get_object("radiobutton2")
        self.rb3 = self.builder.get_object("radiobutton3")
        self.err_dialog = self.builder.get_object("error_dialog")
        self.exp1 = self.builder.get_object("expander1")
        self.exp2 = self.builder.get_object("expander2")
        self.exp3 = self.builder.get_object("expander3")
        self.stat_bar = self.builder.get_object("statusbar1")
        self.spinner1 = self.builder.get_object("spinner1")
        self.l_imei = self.builder.get_object("l_IMEI")
        self.l_sm = self.builder.get_object("l_SM")
        self.l_df = self.builder.get_object("l_DF")
        self.l_ct = self.builder.get_object("l_CT")
        self.l_mf = self.builder.get_object("l_MF")
        self.l_mn = self.builder.get_object("l_MN")

        # 3 Vboxes for 3 expanders
        self.vb1 = gtk.VBox(False, 0)
        self.vb2 = gtk.VBox(False, 0)
        self.vb3 = gtk.VBox(False, 0)

        # Misc Data
        # A list of dictionaries, each dic containing the statemachine
        # object and the IMEI of the connected phone
        self.list_of_usb_connections = []
        self.list_of_bluetooth_connections = []

        self.stat_counter = 0
        self.list_of_usb_buttons = []
        self.list_of_bluetooth_buttons = []

        # Declare stray widgets
        self.fcdialog1 = gtk.FileChooserDialog("Open..", None, gtk.FILE_CHOOSER_ACTION_OPEN, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        self.fcbutton1 = gtk.FileChooserButton(self.fcdialog1)
        self.dummy_rad = gtk.RadioButton()

        # Set properties
        self.fcdialog1.set_default_response(gtk.RESPONSE_OK) 

        # Pack stray widgets
        pass

        # Connect signals defined in glade file.
        self.builder.connect_signals(self)

        # Connect stray widget signals
        pass

    # All the callbacks
    def on_main_window_destroy(self, widget, data=None):
        gtk.main_quit()

    # On pressing button1
    def add_new_device(self, widget, data=None):
        self.run_dialog(self.selection_dialog1)

    # For getting the gammurc files for usb and bluetooth
    def choose_config_file(self, widget, data=None):
        if(self.rb1.get_active()):
            self.fcdialog1.show()
            res = self.fcdialog1.run()
            if(res == gtk.RESPONSE_OK):
                self.usb_config_file = self.fcdialog1.get_filename()
                self.launch_new_connection(self.usb_config_file)
        elif(self.rb2.get_active()):
            self.fcdialog1.show()
            res = self.fcdialog1.run()
            if(res == gtk.RESPONSE_OK):
                self.bluetooth_config_file = self.fcdialog1.get_filename()
                self.launch_new_connection(self.bluetooth_config_file)
        elif(self.rb3.get_active()):
            self.fcdialog1.show()

    # Generic function to display any dialog
    def run_dialog(self, widget, data=None):
        widget.show()
        res = widget.run()
        if(res != 1):
            widget.hide()

    def update_status_bar(self, data, push):
        gtk.gdk.threads_enter()
        if(push):
            self.spinner1.start()
            self.stat_counter += 1
            self.stat_bar.push(self.stat_counter, data)
        else:
            self.stat_bar.pop(self.stat_counter)
            self.stat_counter -= 1
            self.spinner1.stop()
        gtk.gdk.threads_leave()

    def create_new_connection(self, config_file):
        self.update_status_bar("Initializing Device, Please wait", True)
        init_successful = False
        conn = ''
        sm = gammu.StateMachine()

        # Have to add other exceptions
        # TODO
        try:
            sm.ReadConfig(0, 0, config_file)
        except gammu.ERR_FILENOTSUPPORTED:
            sys.stderr.write("Gammu could not understand the config file!")
            self.err_dialog.set_markup("Gammu could not understand the config file!")
            gtk.gdk.threads_enter()
            self.run_dialog(self.err_dialog)
            gtk.gdk.threads_leave()
            self.update_status_bar('', False)
            return
        except Exception, e:
            print sys.exc_info(), 
            self.err_dialog.set_markup("Unknown error! 1")
            gtk.gdk.threads_enter()
            self.run_dialog(self.err_dialog)
            gtk.gdk.threads_leave()
            self.update_status_bar('', False)
            return

        try:
            sm.Init()
            init_successful = True
        except gammu.ERR_DEVICENOTEXIST:
            sys.stderr.write("Device not connected!")
            self.err_dialog.set_markup("Device Not Connected!")
            gtk.gdk.threads_enter()
            self.run_dialog(self.err_dialog)
            gtk.gdk.threads_leave()
            self.update_status_bar('', False)
            return
        except Exception, e:
            print sys.exc_info()
            self.err_dialog.set_markup("Unknown Error! 2")
            gtk.gdk.threads_enter()
            self.run_dialog(self.err_dialog)
            gtk.gdk.threads_leave()
            self.update_status_bar('', False)
            return
        finally:
            # Check if the phone is already connected
            if(sm.GetIMEI() in [conn["IMEI"] for conn in self.list_of_usb_connections]):
                self.err_dialog.set_markup("Phone already connected!")
                gtk.gdk.threads_enter()
                self.run_dialog(self.err_dialog)
                gtk.gdk.threads_leave()
                return
            if(sm.GetIMEI() in [conn["IMEI"] for conn in self.list_of_bluetooth_connections]):
                self.err_dialog.set_markup("Phone already connected!")
                gtk.gdk.threads_enter()
                self.run_dialog(self.err_dialog)
                gtk.gdk.threads_leave()
                return

        # Parse the config file
        config = ConfigParser.ConfigParser()
        config.read(config_file)
        try:
            conn = config.get(config.sections()[0], option="connection")
        except:
            sys.stderr.write("File is incomplete!")
            sys.stderr.write("Make sure connection section is defined!")

        if(conn.startswith("a") and init_successful):
            self.list_of_usb_connections.append({"SM_Obj" : sm, "IMEI" : sm.GetIMEI()})
            gtk.gdk.threads_enter()
            self.update_list_of_connection("usb")
            gtk.gdk.threads_leave()
            self.update_status_bar('', False)
            return

        if(conn.startswith("b") and init_successful):
            self.list_of_bluetooth_connections.append({"SM_Obj" : sm, "IMEI" : sm.GetIMEI()})
            gtk.gdk.threads_enter()
            self.update_list_of_connection("bluetooth")
            gtk.gdk.threads_leave()
            self.update_status_bar('', False)
            return

    def remove_connection(self, widget, data=None):
        to_del_button = [button for button in self.list_of_usb_buttons if(button.get_active())]
        if(to_del_button):

            to_del_button[0].destroy()
        self.reset_phone_info()


    def update_phone_info(self, widget, conn):
        # l_<any_name> = name of a label

        try:
            self.l_imei.set_text(conn["SM_Obj"].GetIMEI())
        except:
            self.l_imei.set_text("Unknown")

        self.l_sm.set_text("#TODO")

        try:
            self.l_df.set_text(conn["SM_Obj"].GetConfig()["Device"])
        except:
            self.l_df.set_text("Unknown")

        try:
            temp_conn_name = conn["SM_Obj"].GetConfig()["Connection"]
        except:
            temp_conn_name = "Unknown"
        if(temp_conn_name.lower().startswith("a")):
            self.l_ct.set_text("USB")
        elif(temp_conn_name.lower().startswith("b")):
            self.l_ct.set_text("Bluetooth")
        else:
        # TODO
            self.l_ct.set_text("Unknown")

        try:
            self.l_mf.set_text(conn["SM_Obj"].GetManufacturer())
        except:
            self.l_mf.set_text("Unknown")

        try:
            self.l_mn.set_text(conn["SM_Obj"].GetModel()[1])
        except:
            self.l_mn.set_text("Unknown")

        # Set alignment
        self.l_imei.set_alignment(0.0, 0.50)
        self.l_sm.set_alignment(0.0, 0.50)
        self.l_df.set_alignment(0.0, 0.50)
        self.l_ct.set_alignment(0.0, 0.50)
        self.l_mf.set_alignment(0.0, 0.50)
        self.l_mn.set_alignment(0.0, 0.50)

        self.l_imei.show_all()
        self.l_sm.show_all()
        self.l_df.show_all()
        self.l_ct.show_all()
        self.l_mf.show_all()
        self.l_mn.show_all()

        # Launch a new thread to set the Phone picture
        # TODO


    def update_list_of_connection(self, type):

        # Dummy RadioButton(self.dummy_rad) will be the head of the group
        # Will not be displayed, but will unify the usb and
        # Bluetooth buttons.
        if(type == "usb"):
            # Clean up the expander and vbox before adding widgets
            self.exp1.remove(self.vb1)
            for child in self.vb1.get_children():
                self.vb1.remove(child)

            # Empty the List of USB buttons
#            self.list_of_usb_buttons = []

            for connection, index in zip(self.list_of_usb_connections, range(0, len(self.list_of_usb_connections))):
                # If the phone is not recognized, take model name
                l = connection["SM_Obj"].GetModel()[1] if(connection["SM_Obj"].GetModel()[0] == "unknown") else connection["SM_Obj"].GetModel()[0]

                temp_button = gtk.RadioButton(group=self.dummy_rad, label=l)
                self.vb1.pack_start(temp_button, False, False, 0)
#                self.list_of_usb_buttons.append(temp_button)
#                self.list_of_usb_buttons[index].connect("clicked", self.update_phone_info, self.list_of_usb_connections[index])
                self.list_of_usb_connections[index]["button_obj"] = temp_button
                self.list_of_usb_connections[index]["button_obj"].connect("clicked", self.update_phone_info, self.list_of_usb_connections[index])
            self.exp1.add(self.vb1)
            self.exp1.show_all()
            return

        if(type == "bluetooth"):
            # Clean up the expander and vbox before adding widgets
            self.exp2.remove(self.vb2)
            for child in self.vb2.get_children():
                self.vb2.remove(child)

            # Empty the list of bluetooth buttons
            self.list_of_bluetooth_buttons = []

            for connection, index in zip(self.list_of_bluetooth_connections, range(0, len(self.list_of_usb_connections))):
                # If the phone name is not recognized, then take model name
                l = connection["SM_Obj"].GetModel()[1] if(connection["SM_Obj"].GetModel()[0] == "unknown") else connection["SM_Obj"].GetModel()[0]

                temp_button = gtk.RadioButton(group=self.dummy_rad, label=l)
                self.vb2.pack_start(temp_button, False, False, 0)
#                self.list_of_bluetooth_buttons.append(temp_button)
#                self.list_of_bluetooth_buttons[index].connect("clicked", self.update_phone_info, self.list_of_usb_connections[incex])
                self.list_of_bluetooth_connections[index]["button_obj"] = temp_button
                self.list_of_usb_connections[index]["button_obj"].connect("clicked", self.update_phone_info, self.list_of_usb_connections[index])
            self.exp2.add(self.vb2)
            self.exp2.show_all()
            return

        if(type == "fbus"):
            # TODO
            pass

    def launch_new_connection(self, config_file):
        t = threading.Thread(target=self.create_new_connection, args=(config_file,))
        t.daemon = True
        t.start()

    def hide_widget(self, widget, data=None):
        widget.hide()

def main():
    _GLADE_FILE = os.path.join(par_dir, "ui", "sms_gateway.xml")
    sms_gateway = SMSGateway((_GLADE_FILE))
    sms_gateway.main_window.show_all()
    gtk.main()

if __name__ == "__main__":
    main()


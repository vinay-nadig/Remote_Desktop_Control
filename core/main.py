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
import Queue
import pkgutil
import copy
from datetime import datetime as dt
import time

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
from preferences import Preference as pref
import scripts
from scripts import *

# Initialize gtk thread engine
gtk.gdk.threads_init()

# Global data
_WINDOWS = False
_LINUX = True
_GLADE_FILE = ''
_DATABASE = os.path.join(par_dir,"database/pref.db")
_SCHEMA = os.path.join(par_dir, "database/schema")
_LIST_OF_MODULES = [name for _, name, _ in pkgutil.iter_modules([os.path.dirname(scripts.__file__)])]
_LIST_OF_CMD_NAMES = []
_LIST_OF_CMD_LONG_NAMES = []
_CONFIG_FILE = "data/numbers.ini"

for mod in _LIST_OF_MODULES:
    _LIST_OF_CMD_NAMES.append(getattr(scripts, mod)._CMD_NAME)
    _LIST_OF_CMD_LONG_NAMES.append(getattr(scripts, mod)._CMD_LONG_NAME)

# Convert all members to lower
_LIST_OF_CMD_NAMES = [x.lower() for x in _LIST_OF_CMD_NAMES]
_LIST_OF_CMD_LONG_NAMES = [x.lower() for x in _LIST_OF_CMD_LONG_NAMES]

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
        self.pref_window = self.builder.get_object("dialog2")
        self.pref_vbox = self.builder.get_object("vbox5")
        self.pref_main_box = self.builder.get_object("dialog-vbox4")

        # 3 Vboxes for 3 expanders
        self.vb1 = gtk.VBox(False, 0)
        self.vb2 = gtk.VBox(False, 0)
        self.vb3 = gtk.VBox(False, 0)

        # Misc Data

        # A list of dictionaries, each dic containing the statemachine
        # object, IMEI of the phone and the radiobutton object corresponding
        # to each phone.
        self.list_of_usb_connections = []
        self.list_of_bluetooth_connections = []
        self.list_of_preferences_objs = []
        self.stat_counter = 0
        self.msg_in = Queue.Queue()
        self.perm_msg_in = Queue.Queue()
        self.list_of_threads = []

        # Database to store preferences.
        self.conn = sqlite3.connect(_DATABASE)
        self.cur = self.conn.cursor()
        self.cur.executescript(open(_SCHEMA, "r").read())

        # Declare stray widgets
        self.fcdialog1 = gtk.FileChooserDialog("Open..", None, gtk.FILE_CHOOSER_ACTION_OPEN,            \
                (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        self.fcbutton1 = gtk.FileChooserButton(self.fcdialog1)
        self.dummy_rad = gtk.RadioButton()
        self.notebook = gtk.Notebook()

        # Set properties
        self.fcdialog1.set_default_response(gtk.RESPONSE_OK) 
        self.notebook.set_tab_pos(gtk.POS_LEFT)

        # Connect signals defined in glade file.
        self.builder.connect_signals(self)

        # Pack stray widgets
        self.pref_main_box.pack_start(self.notebook, False, False, 0)

    # All the callbacks
    def on_main_window_destroy(self, widget, data=None):
        gtk.main_quit()

    # On pressing new button 
    def add_new_device(self, widget, data=None):
        self.fcdialog1.show()
        res = self.fcdialog1.run()
        if(res == gtk.RESPONSE_OK):
            self.config_file = self.fcdialog1.get_filename()
            self.launch_new_connection(self.config_file)

    # On pressing Apply in preferences
    def save_preferences(self, widget, data=None):
        for i in range(0, len(self.list_of_preferences_objs)):
            imei = self.list_of_preferences_objs[i]["imei"]
            max_msg = self.list_of_preferences_objs[i]["max_msg_spin_button"].get_value()
            sig = self.list_of_preferences_objs[i]["signature_entry"].get_text()
            save_sent = self.list_of_preferences_objs[i]["save_sent_msg_cb"].get_active()
            number = ''
            print imei, max_msg, sig, save_sent, number
            try:
                self.cur.execute("INSERT INTO Preferences VALUES(?, ?, ?, ?, ?, ?)", (imei, number, max_msg, sig,  \
                        save_sent, 0))
            except sqlite3.IntegrityError:
                self.cur.execute("UPDATE Preferences SET number=?, max_msg_day=?, signature=?, save_sent_msg=?   \
                        WHERE imei=?", (number, max_msg, sig, save_sent, imei))
            finally:
                self.conn.commit()

    # On pressing preferences button
    def launch_preferences(self, widget, data=None):

        # TODO
        # Set the preferences from the database
        con = sqlite3.connect(_DATABASE)
        cur = con.cursor()

        # Clean up the notebook
        for child in self.notebook.get_children():
            self.notebook.remove(child)

        # Clean up the list
        self.list_of_preferences_objs = []

        no_of_con = len(self.list_of_usb_connections) + len(self.list_of_bluetooth_connections)
        if(no_of_con > 0):
            list_of_conn = self.list_of_usb_connections + self.list_of_bluetooth_connections
            for index in range(0, no_of_con):
                l = list_of_conn[index]["button_obj"].get_label()
                v, s, e, c1 = self.preferences_factory()
                self.list_of_preferences_objs.append({"imei" : list_of_conn[index]["IMEI"],             \
                        "max_msg_spin_button" : s, "signature_entry" : e, "save_sent_msg_cb" : c1})
                self.notebook.append_page(v, tab_label=gtk.Label(l))

        for obj in self.list_of_preferences_objs:
            res1 = cur.execute("select max_msg_day, signature, save_sent_msg from Preferences where imei=?", (obj["imei"],))
            res1 = res1.fetchall()
            max_msg = res1[0][0] if res1[0][0] else 0
            sig = res1[0][1] if res1[0][1] else ""
            save_msg = res1[0][2] if res1[0][2] else False
            obj["max_msg_spin_button"].set_value(max_msg)
            obj["signature_entry"].set_text(sig)
            obj["save_sent_msg_cb"].set_active(save_msg)

        self.run_dialog(self.pref_window)
        con.close()

    def preferences_factory(self):
        # Declare
        vbox = gtk.VBox(False, 5)
        l4 = gtk.Label()
        l5 = gtk.Label()
        frame1 = gtk.Frame()
        frame2 = gtk.Frame()
        sep = gtk.HSeparator()
        vbox1 = gtk.VBox(False, 0)
        vbox2 = gtk.VBox(False, 5)
        hbox1 = gtk.HBox(False, 0)
        adj = gtk.Adjustment(value=0, lower=0, upper=1000, step_incr=1, page_incr=10, page_size=0)
        l1 = gtk.Label("Max")
        s1 = gtk.SpinButton(adj, 1.0)
        l3 = gtk.Label("messages")
        l2 = gtk.Label("Signature")
        entry1 = gtk.Entry(max=10)
        cb1 = gtk.CheckButton(label="Save Messages")
        hbox2 = gtk.HBox(False, 0)

        # Set properties
        frame1.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        frame2.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        l4.set_markup("<b>Messages</b>")
        l5.set_markup("<b>Miscellaneous</b>")
        frame1.set_label_widget(l4)
        frame2.set_label_widget(l5)

        # Pack widgets
        vbox.pack_start(frame1, False, False, 0)
        vbox.pack_start(sep, False, False, 0)
        vbox.pack_start(frame2, False, False, 0)
        hbox2.pack_start(l1)
        hbox2.pack_start(s1)
        hbox2.pack_start(l3)
        hbox1.pack_start(l2)
        hbox1.pack_start(entry1)
        vbox1.pack_start(hbox1,False, False, 0)
        vbox1.pack_start(cb1)
        frame1.add(hbox2)
        frame2.add(vbox1)
        return vbox, s1, entry1, cb1

    # For getting the gammurc files for usb and bluetooth

    # Generic function to display any dialog
    def run_dialog(self, widget, data=None):
        widget.show_all()
        res = widget.run()
        if(res != 1):
            widget.hide()

    # data = string to be displayed
    # op = string "push" or "pop"
    # based on which data is written to
    # or removed from status bar
    def update_status_bar(self, data, op):
        gtk.gdk.threads_enter()
        if(op):
            self.spinner1.start()
            self.stat_counter += 1
            self.stat_bar.push(self.stat_counter, data)
        else:
            self.stat_bar.pop(self.stat_counter)
            self.stat_counter -= 1
            self.spinner1.stop()
        gtk.gdk.threads_leave()

    # Initializes phone and checks if the phone is already
    # connected, parses the config file and updates the
    # 2 lists of connections
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


        t = Poll_SMS(self, self.msg_in, self.perm_msg_in, sm)
        t.setDaemon(True)
        t.start()
        self.list_of_threads.append(t)


        # Parse the config file
        config = ConfigParser.ConfigParser()
        config.read(config_file)
        conn = config.get("gammu", "connection")
        if(conn.startswith("a")):
            self.list_of_usb_connections.append({"SM_Obj" : sm, "IMEI" : sm.GetIMEI()})
            gtk.gdk.threads_enter()
            self.update_list_of_connection("usb")
            gtk.gdk.threads_leave()
            self.update_status_bar('', False)
            return

        if(conn.startswith("b")):
            self.list_of_bluetooth_connections.append({"SM_Obj" : sm, "IMEI" : sm.GetIMEI()})
            gtk.gdk.threads_enter()
            self.update_list_of_connection("bluetooth")
            gtk.gdk.threads_leave()
            self.update_status_bar('', False)
            return

    # Called when the "Delete" button is pressed
    # Destroys the radio button obj and deletes the 
    # Record in the 2 list of connections, and 
    # updates the phone info in the display panel.
    def remove_connection(self, widget, data=None):
        # Checking for the active radio button

        list_of_con = self.list_of_usb_connections + self.list_of_bluetooth_connections
        for con, thread in zip(list_of_con, self.list_of_threads):
            if con["SM_Obj"] ==  thread.sm:
                thread.join()

        record_to_del= [dic for dic in self.list_of_usb_connections if(dic["button_obj"].get_active())]
        if(record_to_del):
            to_del = [dic for dic in self.list_of_usb_connections if(dic["button_obj"] == record_to_del[0]["button_obj"])]
            index = self.list_of_usb_connections.index(to_del[0])
            to_del[0]["button_obj"].destroy()
            del self.list_of_usb_connections[index]
            self.reset_screen_info()
        
        record_to_del = [dic for dic in self.list_of_bluetooth_connections if(dic["button_obj"].get_active())]
        if(record_to_del):
            to_del = [dic for dic in self.list_of_bluetooth_connections if(dic["button_obj"] == record_to_del[0]["button_obj"])]
            index = self.list_of_bluetooth_connections.index(to_del[0])
            to_del[0]["button_obj"].destroy()
            del self.list_of_bluetooth_connections[index]
            self.reset_screen_info()

    def reset_screen_info(self):
        self.l_imei.set_text('')
        self.l_sm.set_text('')
        self.l_df.set_text('')
        self.l_ct.set_text('')
        self.l_mf.set_text('')
        self.l_mn.set_text('')

        # TODO
        # Reset the phone image

    # Called when the radiobutton corresponding to
    # the phone is clicked. updates the info in the main
    # info display area.
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


    # Creates button objects for the phones, and
    # adds them to a container(vb1 or vb2) and
    # adds the container to the expanders.
    # Also adds the button objects to the dictionary
    # in the 2 list of connections
    def update_list_of_connection(self, type):

        # Dummy RadioButton(self.dummy_rad) will be the head of the group
        # Will not be displayed, but will unify the usb and
        # Bluetooth buttons.
        if(type == "usb"):
            # Clean up the expander and vbox before adding widgets
            self.exp1.remove(self.vb1)
            for child in self.vb1.get_children():
                self.vb1.remove(child)

            for connection, index in zip(self.list_of_usb_connections, range(0, len(self.list_of_usb_connections))):
                # If the phone is not recognized, take model name
                l = connection["SM_Obj"].GetModel()[1] if(connection["SM_Obj"].GetModel()[0] == "unknown") else connection["SM_Obj"].GetModel()[0]

                temp_button = gtk.RadioButton(group=self.dummy_rad, label=l)
                self.vb1.pack_start(temp_button, False, False, 0)
                self.list_of_usb_connections[index]["button_obj"] = temp_button
                self.list_of_usb_connections[index]["button_obj"].connect("clicked", self.update_phone_info, self.list_of_usb_connections[index])
            self.exp1.add(self.vb1)
            self.exp1.show_all()

        if(type == "bluetooth"):
            # Clean up the expander and vbox before adding widgets
            self.exp2.remove(self.vb2)
            for child in self.vb2.get_children():
                self.vb2.remove(child)

            for connection, index in zip(self.list_of_bluetooth_connections, range(0, len(self.list_of_bluetooth_connections))):
                # If the phone name is not recognized, then take model name
                l = connection["SM_Obj"].GetModel()[1] if(connection["SM_Obj"].GetModel()[0] == "unknown") else connection["SM_Obj"].GetModel()[0]

                temp_button = gtk.RadioButton(group=self.dummy_rad, label=l)
                self.vb2.pack_start(temp_button, False, False, 0)
                self.list_of_bluetooth_connections[index]["button_obj"] = temp_button
                self.list_of_bluetooth_connections[index]["button_obj"].connect("clicked", self.update_phone_info, self.list_of_bluetooth_connections[index])
            self.exp2.add(self.vb2)
            self.exp2.show_all()

        if(type == "fbus"):
            # TODO
            pass

        self.initialize_dateinfo(self.list_of_usb_connections + self.list_of_bluetooth_connections)
        self.launch_preferences(None, None)

#    def update_history(self, type):
#        if(type == "Recieved"):
#            l = self.perm_msg_in.qsize()
#            vbox = pygtk.VBox(False, 0)
#            for i in range(0, l):
                

    def initialize_dateinfo(self, list_of_con):
        con = sqlite3.connect(_DATABASE)
        cur = con.cursor()
        for i in list_of_con:
            try:
                cur.execute("INSERT INTO DateInfo VALUES(?, ?, ?)", (i["IMEI"], 0, 0))
            except sqlite3.IntegrityError:
                cur.execute("UPDATE DateInfo SET msg_cntr=?, last_used=? WHERE imei=?", (0, 0, i["IMEI"]))
            finally:
                con.commit()
        con.close()


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

    poll_queue(sms_gateway)

    gtk.main()


def poll_queue(sms_gateway):
    ps = Process_SMS(sms_gateway.msg_in, sms_gateway)
    ps.setDaemon(True)
    ps.start()

class Process_SMS(threading.Thread):
    def __init__(self, sms_q, sms_gateway):
        self.sms_q = sms_q
        self.sms_gw = sms_gateway
        super(Process_SMS, self).__init__()

    def run(self):
        while True:
            sleep(5)
            if(not self.sms_q.empty()):
                list_of_con = self.sms_gw.list_of_usb_connections + self.sms_gw.list_of_bluetooth_connections
                sms = self.sms_q.get()
                text = sms["Text"]
                to_no = sms["From_no"]
                options = text.split()[1:]
                command = text.split()[0].lower()
                if(command in _LIST_OF_CMD_NAMES or command in _LIST_OF_CMD_LONG_NAMES):
                    avail_conn, imei = self.get_available_connection()
                    if(avail_conn):
                        con = sqlite3.connect(_DATABASE)
                        cur = con.cursor()

                        sig = cur.execute("SELECT signature FROM Preferences where imei=?", (imei,)).fetchall()[0][0]
                        sig  = sig if (sig) else ""
                        s = getattr(scripts, command)
                        cmd_name = getattr(s, "_CMD_LONG_NAME")
                        cls = getattr(s, cmd_name)
                        obj = cls(options, avail_conn, to_no, sig)
                        obj.send_sms()
                        cur_cntr = cur.execute("SELECT msg_cntr from DateInfo where imei=?", (imei,)).fetchall()[0][0]
                        now = int(time.time())
                        cur.execute("UPDATE DateInfo SET msg_cntr=?, last_used=? where imei=?", (cur_cntr+1, now, imei))

                        con.commit()
                        con.close()
                    else:
                        print "Sorry No more sms available!"
                else:
                    # TODO
                    # Send a help message
                    pass

    def get_available_connection(self):
        con = sqlite3.connect(_DATABASE)
        cur = con.cursor()


        list_of_con = self.sms_gw.list_of_usb_connections + self.sms_gw.list_of_bluetooth_connections
        if(len(list_of_con) <= 0):
            return None, None
        # Checking if the msg limit has been exceeded
        row_count = cur.execute("select imei as im from DateInfo where msg_cntr < (select max_msg_day from Preferences where imei=im)")
        res1 = row_count.fetchall()

        # Remove those phones that are not connected
        for r in res1:
            if str(r[0]) not in [y["IMEI"] for y in list_of_con]:
                res1.remove(r)
        # Get the first available connection
        # TODO : Implement using list comprehensions
        if(len(res1)):
            for r in res1:
                for dic in list_of_con:
                    if(dic["IMEI"] == str(r[0])):
                        avail_con = dic["SM_Obj"]
                        imei = dic["IMEI"]


            # Reset msg counter if a phone is being used
            # for the first time in a day.
            now = time.time()
            last_used = cur.execute("select last_used from DateInfo where imei=?", (imei,))
            last_used = last_used.fetchall()[0][0]
            # 86400 = number of seconds in one day
            if(now - last_used > 86400):
                cur.execute("UPDATE DateInfo SET msg_cntr=0 where imei=?",(imei,))

            con.commit()
            con.close()
            if(avail_con):
                return avail_con, imei
            else:
                return None, None
        else:
            con.close()
            return None, None

class Poll_SMS(threading.Thread):
    def __init__(self, sms_gw, sms_q, perm_sms_q, sm):
        self.stoprequest = threading.Event()
        self.sms_q = sms_q
        self.perm_sms_q = perm_sms_q
        self.sm = sm
        self.stat = self.sm.GetSMSStatus()
        self.counter = self.stat["PhoneUsed"] + self.stat["SIMUsed"]
        self.tmp_counter1 = self.counter
        self.sms_list = []
        self.stoprequest = threading.Event()
        self.sms_gw = sms_gw
        super(Poll_SMS, self).__init__()

    def join(self):
        self.stoprequest.set()
        super(Poll_SMS, self).join()

    def run(self):
        while not self.stoprequest.isSet():
            sleep(5)
            self.stat = self.sm.GetSMSStatus()
            self.counter = self.stat["PhoneUsed"] + self.stat["SIMUsed"]
            self.tmp_counter2 = self.counter
            temp_sms = []
            start = True
            if self.counter > self.tmp_counter1:
                diff_in_msgs = self.counter - self.tmp_counter1
                while self.counter > 0:
                    if start:
                        cursms = self.sm.GetNextSMS(Start = True, Folder = 0)
                        start = False
                    else:
                        cursms = self.sm.GetNextSMS(Location = cursms[0]["Location"], Folder = 0)
                    self.counter -= len(cursms)
                    temp_sms.append(cursms)

                temp_sms.reverse()
                msg = temp_sms[0]
                self.sms_q.put({"Text" : msg[0]["Text"], "From_no" : msg[0]["Number"]})
                self.perm_sms_q.put({"Text" : msg[0]["Text"], "From_no" : msg[0]["Number"]})
                self.tmp_counter1 = self.tmp_counter2

if __name__ == "__main__":
    main()

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
import time
import textwrap
import webbrowser
from time import sleep
from datetime import datetime as dt
import re


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


# Make sure pygtk version > 2.0
pygtk.require('2.0')

# Check for super user permission
if(os.getuid() != 0):
    raise EnvironmentError, "Run as root please"
    exit()

# Other imports
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

_LIST_OF_MODULES = []
for mod1, mod2 in zip(_LIST_OF_CMD_NAMES, _LIST_OF_CMD_LONG_NAMES):
    _LIST_OF_MODULES.append({"Short_Name" : mod1, "Long_Name" : mod2})

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
        self.sent_frame_align = self.builder.get_object("alignment3")
        self.recieved_frame_align = self.builder.get_object("alignment4")
        self.about_window = self.builder.get_object("aboutdialog1")
        self.contact_button = self.builder.get_object("button9")
        self.contact_window = self.builder.get_object("dialog1")
        self.trusted_viewport = self.builder.get_object("viewport3")
        self.privilaged_viewport = self.builder.get_object("viewport4")
        self.trusted_vbox = gtk.VBox(False, 0)
        self.privilaged_vbox = gtk.VBox(False, 0)
        self.trusted_frame = self.builder.get_object("frame5")
        self.privilaged_frame = self.builder.get_object("frame6")
        self.add_number_window = self.builder.get_object("dialog3")
        self.add_entry = self.builder.get_object("entry1")

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
        self.msg_out = []
        self.wrapper = textwrap.TextWrapper(width=25)
        self.list_of_trusted_buttons = []
        self.list_of_privilaged_buttons = []
        self.pattern = re.compile("^n(a)+?(d)+?(i)+?(g)+?$")

        # Database to store preferences.
        self.con = sqlite3.connect(_DATABASE)
        self.cur = self.con.cursor()
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
        self.contact_button.set_label("Contacts")

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
            number = ''
            try:
                self.cur.execute("INSERT INTO Preferences VALUES(?, ?, ?, ?, ?)", (imei, number, max_msg, sig, 0))
            except sqlite3.IntegrityError:
                self.cur.execute("UPDATE Preferences SET number=?, max_msg_day=?, signature=?   \
                        WHERE imei=?", (number, max_msg, sig, imei))
            finally:
                self.con.commit()

    def launch_help(self, widget, data=None):
        # Set the uid to the first non privilaged user
        os.setuid(1000)
        webbrowser.open_new_tab("https://sites.google.com/site/smsgatewayhelp/")
        os.setuid(0)

    # On pressing preferences button
    def launch_preferences(self, widget, data=None):

        # If there are no active connections
        if(not len(self.list_of_usb_connections + self.list_of_bluetooth_connections)):
            return

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
                v, s, e = self.preferences_factory()
                self.list_of_preferences_objs.append({"imei" : list_of_conn[index]["IMEI"],             \
                        "max_msg_spin_button" : s, "signature_entry" : e})
                self.notebook.append_page(v, tab_label=gtk.Label(l))

        for obj in self.list_of_preferences_objs:
            res1 = cur.execute("select max_msg_day, signature from Preferences where imei=?", (obj["imei"],))
            res1 = res1.fetchall()
            max_msg = res1[0][0] if res1[0][0] else 0
            sig = res1[0][1] if res1[0][1] else ""
            obj["max_msg_spin_button"].set_value(max_msg)
            obj["signature_entry"].set_text(sig)

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
        frame1.add(hbox2)
        frame2.add(vbox1)
        return vbox, s1, entry1

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
    def update_status_bar(self, data, op, timeout=0):
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
        temp_res = None

        try:
            imei = conn["SM_Obj"].GetIMEI()
            self.l_imei.set_text(imei)
        except:
            self.l_imei.set_text("Unknown")

#        try:
#            temp_res = self.cur.execute("SELECT msg_cntr FROM DateInfo where imei = ?", (imei,)).fetchall()
#        except:
#            self.l_ms.set_text("UNKNOWN")

#        if(temp_res):
#            self.l_ms.set_text(temp_res[0][0])


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

    def launch_about(self, widget, data=None):
        # Has to be set here because glade interface for
        # about dialog does not allow entering authors. (Bug)
        self.about_window.set_authors(["Vinay Nadig", "Supreeth Akrura", "Sathya Sagar", "Shravan Suresh"])
        self.run_dialog(self.about_window)

    def add_number(self, widget, data=None):
        self.add_entry.grab_focus()
        self.add_entry.set_text('')
        self.run_dialog(self.add_number_window)
        no_to_add = self.add_entry.get_text()
        no_to_add = self.clean_number(no_to_add)
        if not no_to_add:
            return
        if widget.get_ancestor(gtk.Frame).get_label() == "Trusted":
            try:
                self.cur.execute("INSERT INTO Contacts VALUES(?, ?, ?, ?, ?)", (no_to_add, 0, 1, 0, 0))
            except sqlite3.IntegrityError, e:
                self.cur.execute("UPDATE Contacts SET Trusted=? WHERE Number=?", (1, no_to_add))

        if widget.get_ancestor(gtk.Frame).get_label() == "Privilaged":
            try:
                self.cur.execute("INSERT INTO Contacts VALUES(?, ?, ?, ?, ?)", (no_to_add, 1, 1, 0, 0))
            except sqlite3.IntegrityError, e:
                self.cur.execute("UPDATE Contacts SET Privilaged=? WHERE Number=?", (1, no_to_add))
        self.con.commit()

        # Relaunch the contacts window.
        self.launch_contacts(None, None)

    def remove_contacts(self, widget, data=None):
        if widget.get_ancestor(gtk.Frame).get_label() == "Trusted":
            for button in self.list_of_trusted_buttons:
                if button.get_active():
                    no_to_remove = button.get_label()
                    no_to_remove = self.clean_number(no_to_remove)
                    self.cur.execute("DELETE FROM Contacts WHERE Number=?", (no_to_remove,))

        if widget.get_ancestor(gtk.Frame).get_label() == "Privilaged":
            for button in self.list_of_privilaged_buttons:
                if button.get_active():
                    no_to_remove = button.get_label()
                    no_to_remove = self.clean_number(no_to_remove)
                    self.cur.execute("UPDATE Contacts SET Privilaged=0 WHERE Number=?", (no_to_remove,))
        self.con.commit()

        # Relaunch the contacts window.
        self.launch_contacts(None, None)

    # number type = string
    # return an int that has been reduced
    # to the standard 10 digit phone number format
    def clean_number(self, number):
        if len(number) >= 10:
            # Get the last 10 numbers
            number = number[len(number)-10:]
        else:
            return None
        if(number.isdigit()):
            number = int(number)
        else:
            return None
        return number

    def launch_contacts(self, widget, data=None):
        con = sqlite3.connect(_DATABASE)
        cur = con.cursor()
        trusted_res = cur.execute("SELECT Number FROM Contacts WHERE Trusted=?", (1,)).fetchall()
        privilaged_res = cur.execute("SELECT Number FROM Contacts WHERE Privilaged=?", (1,)).fetchall()
        con.close()

        for child in self.trusted_vbox.get_children():
            self.trusted_vbox.remove(child)

        for child in self.privilaged_vbox.get_children():
            self.privilaged_vbox.remove(child)

        for child in self.trusted_viewport.get_children():
            self.trusted_viewport.remove(child)

        for child in self.privilaged_viewport.get_children():
            self.privilaged_viewport.remove(child)

        if(trusted_res or privilaged_res):
            for number in trusted_res:
                tb = gtk.ToggleButton(str(number[0]))
                self.trusted_vbox.pack_start(tb, False, False, 0)
                self.list_of_trusted_buttons.append(tb)

            for number in privilaged_res:
                tb = gtk.ToggleButton(str(number[0]))
                self.privilaged_vbox.pack_start(tb, False, False,0)
                self.list_of_privilaged_buttons.append(tb)
        else:
            l1 = gtk.Label("No Trusted numbers \nin database")
            l2 = gtk.Label("No Privilaged numbers\nin database")
            self.trusted_vbox.pack_start(l1, False, False, 0)
            self.privilaged_vbox.pack_start(l2, False, False, 0)

        self.trusted_viewport.add(self.trusted_vbox)
        self.privilaged_viewport.add(self.privilaged_vbox)
        self.run_dialog(self.contact_window)


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

        self.initialize_database(self.list_of_usb_connections + self.list_of_bluetooth_connections)
#        self.launch_preferences(None, None)

    def update_history(self, type):
        if(type == "Recieved"):
            l = self.perm_msg_in.qsize()
            vbox = gtk.VBox(False, 0)
            scrolled_window = gtk.ScrolledWindow()
            viewport = gtk.Viewport()

            # Clean up the frame alignment
            for child in self.recieved_frame_align.get_children():
                self.recieved_frame_align.remove(child)

            for i in range(0, l):
                msg = self.perm_msg_in.get()
                self.perm_msg_in.put(msg)
                sep = gtk.HSeparator()
                label_text = msg["Text"]
                label_text = self.wrapper.fill(label_text)
                label1 = gtk.Label("Text\t:\t" + label_text)
                label1.set_alignment(0.0, 0.0)
                label2 = gtk.Label("From\t:\t" + msg["From_no"])
                label2.set_alignment(0.0, 0.0)
                label3 = gtk.Label("Time\t:\t" + time.asctime())
                label3.set_alignment(0.0, 0.0)
                vbox.pack_start(label2, False, False, 0)
                vbox.pack_start(label1, False, False, 0)
                vbox.pack_start(label3, False, False, 0)
                vbox.pack_start(sep, False, False, 0)
            self.recieved_frame_align.add(scrolled_window)
            scrolled_window.add(viewport)
            viewport.add(vbox)
            gtk.gdk.threads_enter()
            self.recieved_frame_align.show_all()
            gtk.gdk.threads_leave()

        if(type == "Sent"):
            l = len(self.msg_out)
            vbox = gtk.VBox(False, 0)
            scrolled_window = gtk.ScrolledWindow()
            viewport = gtk.Viewport()

            # Clean up the frame alignment
            for child in self.sent_frame_align.get_children():
                self.sent_frame_align.remove(child)

            for i in range(0, l):
                msg = self.msg_out[i]
                sep = gtk.HSeparator()
                label_text = msg["Text"]
                label_text = self.wrapper.fill(label_text)
                label1 = gtk.Label("Text\t:\t" + label_text)
                label1.set_alignment(0.0, 0.0)
                label2 = gtk.Label("To\t:\t" + msg["To_No"])
                label2.set_alignment(0.0, 0.0)
                label3 = gtk.Label("Time\t:\t" + time.asctime())
                label3.set_alignment(0.0, 0.0)
                vbox.pack_start(label2, False, False, 0)
                vbox.pack_start(label1, False, False, 0)
                vbox.pack_start(label3, False, False, 0)
                vbox.pack_start(sep, False, False, 0)
            self.sent_frame_align.add(scrolled_window)
            scrolled_window.add(viewport)
            viewport.add(vbox)
            gtk.gdk.threads_enter()
            self.sent_frame_align.show_all()
            gtk.gdk.threads_leave()


    def initialize_database(self, list_of_con):
        con = sqlite3.connect(_DATABASE)
        cur = con.cursor()
        for i in list_of_con:
            try:
                cur.execute("INSERT INTO DateInfo VALUES(?, ?, ?)", (i["IMEI"], 0, 0))
            except sqlite3.IntegrityError:
                cur.execute("UPDATE DateInfo SET msg_cntr=?, last_used=? WHERE imei=?", (0, 0, i["IMEI"]))
            finally:
                con.commit()
            try:
                cur.execute("INSERT INTO Preferences VALUES(?, ?, ?, ?, ?)", (i["IMEI"], 0, 0, "", 0))
            except sqlite3.IntegrityError:
                # Leave the preferences be if it already has values
                pass
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
                con = sqlite3.connect(_DATABASE)
                cur = con.cursor()
                temp_to_no = self.sms_gw.clean_number(to_no)
                is_trusted = cur.execute("select Trusted from Contacts where Number=?", (temp_to_no,)).fetchall()
                is_privilaged = cur.execute("select Privilaged from Contacts where Number=?", (temp_to_no,)).fetchall()
                con.close()
                options = text.split()[1:]
                command = text.split()[0].lower()

                # TODO
                # Remove the pattern match condition before demo
                print command
                print _LIST_OF_CMD_NAMES
                print _LIST_OF_CMD_LONG_NAMES
                if((command in _LIST_OF_CMD_NAMES or command in _LIST_OF_CMD_LONG_NAMES) and (is_trusted or is_privilaged)):
                    avail_conn, imei = self.get_available_connection()
                    print "within the if condition"

                    if(avail_conn):
                        print "got a connection"
                        con = sqlite3.connect(_DATABASE)
                        cur = con.cursor()

                        sig = cur.execute("SELECT signature FROM Preferences where imei=?", (imei,)).fetchall()[0][0]
                        sig  = sig if sig else ""
                        for dic in _LIST_OF_MODULES:
                            if(dic["Long_Name"] == command or dic["Short_Name"] == command):
                                s = getattr(scripts, dic["Long_Name"])
                        cmd_name = getattr(s, "_CMD_LONG_NAME")
                        cls = getattr(s, cmd_name)
                        obj = cls(options, avail_conn, to_no, sig)
                        if obj.privilaged:
                            if is_privilaged:
                                obj.send_sms()
                            else:
                                return
                        obj.send_sms()
                        self.sms_gw.msg_out.append({"Text" : obj.msg, "To_No" : to_no})
                        self.sms_gw.update_history("Sent")
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
            # TODO
            # Show an error dialog and ask
            # the user to reconnect the phone.

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
            try:
                self.stat = self.sm.GetSMSStatus()
            except gammu.ERR_TIMEOUT, e:
                continue
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
                self.sms_gw.update_history("Recieved")
                self.tmp_counter1 = self.tmp_counter2

if __name__ == "__main__":
    main()

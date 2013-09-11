#!/usr/bin/env bash

# Store the glade file in /tmp/test1.glade

cp test1.glade test2.glade
replace "<interface>" "<glade-interface>" -- test2.glade 
replace "</interface>" "</glade-interface>" -- test2.glade
gtk-builder-convert test2.glade test1.xml
cp test1.xml /home/vinay/project/ui/sms_gateway.xml
sudo /home/vinay/project/core/main.py


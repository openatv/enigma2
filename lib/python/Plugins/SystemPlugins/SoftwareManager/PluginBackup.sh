#!/bin/sh
clear
echo $LINE 
echo 'Backing up your installed plugins'
echo $LINE
echo 'Please wait...'
echo $LINE

opkg list-installed |cut -d " " -f1 | egrep 'enigma2-plugin-|task-base' > /etc/enigma2/installed-list.txt
opkg list-changed-conffiles > /etc/enigma2/changed-configfiles.txt

echo Please check the log with UP button!
echo $LINE
echo Press OK or EXIT to go back!


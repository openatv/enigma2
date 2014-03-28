#!/bin/sh
# created by Nobody28
#
# www.gigablue-support.com
clear
echo '############################'
echo '# www.gigablue-support.com #'
echo '#        by Nobody28       #'
echo '############################'
echo $LINE 
echo 'Backup your Plugins'
echo $LINE
echo 'Please Wait'
echo $LINE

opkg list-installed | egrep 'enigma2-plugin-|task-base' > /etc/enigma2/installed-list.txt
opkg list-changed-conffiles > /etc/enigma2/changed-configfiles.txt

echo Please check the LOG with UP Button!
echo $LINE
echo Press OK or EXIT to go back!


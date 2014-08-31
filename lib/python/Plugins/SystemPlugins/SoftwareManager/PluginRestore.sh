#!/bin/sh
clear
echo $LINE 
echo 'Restore your plugins'
echo $LINE
echo 'Please wait...'
echo $LINE

opkg update

cp -r /media/hdd/restore/files/* /
opkg install /tmp/*.ipk
rm /tmp/*.ipk

sed 's/enigma2-plugin-/opkg install enigma2-plugin-/g' /etc/enigma2/installed-list.txt > /tmp/install_plugin.sh
sed 's/task-base/opkg install task-base/g' /tmp/install_plugin.sh > /tmp/install_plugin1.sh
chmod 755 /tmp/install_plugin1.sh
rm /tmp/install_plugin.sh
sh /tmp/install_plugin1.sh > /dev/null

# opkg list-changed-conffiles > /etc/enigma2/changed-configfiles.txt

rm /tmp/install_plugin1.sh

echo Please check the log with UP button!
echo $LINE
echo Press OK or EXIT to go back!

init 4
sleep 5
init 3

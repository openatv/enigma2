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
echo 'Restore/Update your Plugins'
echo $LINE
echo 'Please Wait'
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

echo Please check the LOG with UP Button!
echo $LINE
echo Press OK or EXIT to go back!

init 4
sleep 5
init 3

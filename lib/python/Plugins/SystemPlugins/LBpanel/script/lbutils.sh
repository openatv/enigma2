#!/bin/sh
# Utils for LBPanel 
# GNU GPL2+

case $1 in
# Test updates for LBpanel and LBpanel Settings
testupdate)
        opkg update
        opkg list-upgradable > /tmp/.list-upgradable
        for arg in `awk '/enigma2-plugin-extensions-lbpanel/{print $1}' /tmp/.list-upgradable` ; do
             opkg install $arg;
             echo "." > /tmp/.lbpanel.update
             echo "Installing $arg";
        done;
        rm -f /tmp/list-upgradable
                                                                
	exit 0
	;;

testsettings)
	opkg update
        for arg in `awk '/enigma2-plugin-settings-sorys/{print $1}' /tmp/.list-upgradable` ; do
                echo "Installing $arg";
                opkg install $arg;
                echo "." > /tmp/.lbsettings.update
        done;
        rm -f /tmp/list-upgradable
                                                                
	exit 0
	;;
	
#Download epg
epgdown)
	wget -q http://appstore.linux-box.es/epg/epg.dat.gz -O $2epg.dat.gz
	cp $2epg.dat.gz $2epg.dat.gz.copia
	rm -f $2epg.dat
	gzip -df $2epg.dat.gz $2	
	exit 0
	;;
	
*)
	echo "Usage: lbutils.sh <util> [<option1>] [<option2>]" ;
	exit 1
	;;	
esac
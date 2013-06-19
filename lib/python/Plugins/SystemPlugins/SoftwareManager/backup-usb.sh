TARGET="XX"

for candidate in  /media/usb /media/sdb1 /media/sdc1 /media/sdd1 /media/sde1 /media/mmc1 
do
   if [ -f ${candidate}/*backupstick* ]
   then
     TARGET=${candidate}
   fi    
done

if [ $TARGET = "XX" ] ; then
    echo "There is NO valid USB-stick found, so I've got nothing to do"
	echo " "
    echo "0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0"
	echo " "
	echo "WARNING    WARNING    WARNING    WARNING    WARNING"
	echo "To back-up directly to the USB-stick, the USB-stick MUST "
	echo "contain a file with the name: "
	echo "backupstick or "
	echo "backupstick.txt "
	echo " "
	echo "0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0-0"
	echo " "
	echo "If you place an USB-stick containing this file then the "
    echo "back-up will be automatically made on the USB-stick and" 
    echo "can be used to restore the current image if necessary. "
    echo
    echo "The program will exit now. "
	echo " "
	echo "Bye. "
else
    echo "Full back-up directly to USB"
	##remove opkg lists
	rm -rf /var/lib/opkg/lists/
	rm -f /etc/enigma2/epg.dat
	sync
    /usr/lib/enigma2/python/Plugins/SystemPlugins/SoftwareManager/backup.sh $TARGET | tee /tmp/USB-Backup.log
	sync
	#sleep 8
	#umount $TARGET
	#sleep 3
fi

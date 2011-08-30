TARGET="XX"

for candidate in  /media/usb /media/sdb1 /media/sdc1 /media/sdd1 /media/sde1 /media/mmc1 
do
   if [ -f ${candidate}/vubackupstick -o -f ${candidate}/vubackupstick.txt -o -f ${candidate}/backupstick -o -f ${candidate}/backupstick.txt ]
   then
     TARGET=${candidate}
   fi    
done

if [ $TARGET = "XX" ] ; then
    echo "There is no valid USB-stick found, so I've got nothing to do"
	echo " "
    echo "If you place an USB-stick containing a file with the name: "
    echo "'backupstick' then the back-up will be automatically "
    echo "made on the USB-stick and can be used to restore the "
    echo "current image if necessary. "
    echo
    echo "The program will exit now. "
	echo " "
	echo "Bye. "
else
    echo "Full back-up directly to USB"
    build-combi.sh $TARGET | tee /tmp/USB-Backup.log
	sync
	#sleep 8
	#umount $TARGET
	#sleep 3
fi
	
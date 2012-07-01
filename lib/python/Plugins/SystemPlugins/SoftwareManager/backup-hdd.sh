echo "HDD-CHECK" > /hdd/hdd-check;

if [ -f /hdd/hdd-check ] ; then
	echo "Full back-up to the harddisk"
        /usr/lib/enigma2/python/Plugins/SystemPlugins/SoftwareManager/backup.sh /hdd | tee /tmp/HDD-Full-Backup.log 
	rm -f /hdd/hdd-check
        wait 3
else
	echo "---> I M A G E  C R E A T I O N  F A I L E D! <---"
    echo "\nProbable causes could be: "
	echo "--> No space left on device;"
	echo "--> No device present;"
	echo "--> No permission to write on medium"
	echo "\nPlease check your back-up medium"
	exit 0
fi 	

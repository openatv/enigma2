#################################################################
# FULL BACKUP UTILITY FOR ENIGMA2, SUPPORTS ALL GIGABLUE MODELS #
#  									   	        	            #
#            MAKES A FULLBACKUP READY FOR FLASHING.             #
#################################################################
#
#!/bin/sh
VERSION="Version 1.0"
START=$(date +%s)

##DECLARATION OF VARIABLES

DIRECTORY=$1
DATE=`date +%Y%m%d_%H%M`
IMAGEVERSION=`date +%Y%m%d`
if grep rootfs /proc/mounts | grep ubifs > /dev/null; then # TESTING FOR UBIFS
	ROOTFSTYPE=ubifs
else
	ROOTFSTYPE=jffs2									    # NO UBIFS THEN JFFS2
fi
MKFS=/usr/sbin/mkfs.$ROOTFSTYPE
UBINIZE=/usr/sbin/ubinize
NANDDUMP=/usr/sbin/nanddump
WORKDIR=$DIRECTORY/bi
TARGET="XX"
MTDKERNEL="mtd1"

## TESTING WHICH KIND OF SATELLITE RECEIVER IS USED
## TESTING THE Gigablue HD 800 SE Model
elif [ $MODEL = "gb800se" ] ; then
	TYPE=GIGABLUE
	MODEL="se"
	MKUBIFS_ARGS="-m 2048 -e 126976 -c 4096"
	UBINIZE_ARGS="-m 2048 -p 128KiB"
	SHOWNAME="GigaBlue $MODEL"
	MTDKERNEL="mtd2"
	MAINDESTOLD=$DIRECTORY/$MODEL
	MAINDEST=$DIRECTORY/gigablue/$MODEL
	EXTRA=$DIRECTORY/fullbackup_$TYPE/$DATE/gigablue
## TESTING THE Gigablue HD 800 UE Models
elif [ $MODEL = "gb800ue" ]; then
	TYPE=GIGABLUE
	MODEL="ue"
	MKUBIFS_ARGS="-m 2048 -e 126976 -c 4096"
	UBINIZE_ARGS="-m 2048 -p 128KiB"
	SHOWNAME="GigaBlue $MODEL"
	MTDKERNEL="mtd2"
	MAINDESTOLD=$DIRECTORY/$MODEL
	MAINDEST=$DIRECTORY/gigablue/$MODEL
	EXTRA=$DIRECTORY/fullbackup_$TYPE/$DATE/gigablue
## TESTING THE Gigablue HD 800 Solo Model
elif [ $MODEL = "gb800solo" ] ; then
	TYPE=GIGABLUE
	MODEL="solo"
	JFFS2OPTIONS="--eraseblock=0x20000 -n -l --pad=125829120"
	SHOWNAME="GigaBlue $MODEL"
	MTDKERNEL="mtd2"
	MAINDESTOLD=$DIRECTORY/$MODEL
	MAINDEST=$DIRECTORY/gigablue/$MODEL
	EXTRA=$DIRECTORY/fullbackup_$TYPE/$DATE/gigablue
## TESTING THE Gigablue HD Quad Model
elif [ $MODEL = "gbquad" ] ; then
	TYPE=GIGABLUE
	MODEL="quad"
	MKUBIFS_ARGS="-m 2048 -e 126976 -c 4000"
	UBINIZE_ARGS="-m 2048 -p 128KiB"
	SHOWNAME="GigaBlue $MODEL"
	MTDKERNEL="mtd2"
	MAINDESTOLD=$DIRECTORY/$MODEL
	MAINDEST=$DIRECTORY/gigablue/$MODEL
	EXTRA=$DIRECTORY/fullbackup_$TYPE/$DATE/gigablue

else
	echo "No supported receiver found!"
	exit 0
fi

echo "Back-up Tool for a $SHOWNAME" | tr  a-z A-Z
echo "$VERSION"
echo "_________________________________________________"
echo "Please be patient, a backup will now be made,"
if [ $ROOTFSTYPE = "ubifs" ] ; then
	echo "because of the used filesystem the back-up"
	echo "will take about 5-12 minutes for this system"
	echo " "
	echo " "
	echo "If you want to watch TV while backup is running "
	echo "press the yellow key to hide/show the screen"
	echo " "
else
	echo "this will take between 2 and 9 minutes "
fi
echo " "
echo "_________________________________________________"

## TESTING IF ALL THE TOOLS FOR THE BUILDING PROCESS ARE PRESENT
if [ ! -f $MKFS ] ; then
	echo $MKFS" not found"
	exit 0
fi
if [ ! -f $NANDDUMP ] ; then
	echo $NANDDUMP" not found"
	exit 0
fi
## PREPARING THE BUILDING ENVIRONMENT
rm -rf $WORKDIR
mkdir -p $WORKDIR
mkdir -p /tmp/bi/root

sync
mount --bind / /tmp/bi/root

echo "Create: root.$ROOTFSTYPE"
if [ $ROOTFSTYPE = "jffs2" ] ; then
	$MKFS --root=/tmp/bi/root --faketime --output=$WORKDIR/root.jffs2 $JFFS2OPTIONS
else
	echo \[ubifs\] > $WORKDIR/ubinize.cfg
	echo mode=ubi >> $WORKDIR/ubinize.cfg
	echo image=$WORKDIR/root.ubi >> $WORKDIR/ubinize.cfg
	echo vol_id=0 >> $WORKDIR/ubinize.cfg
	echo vol_type=dynamic >> $WORKDIR/ubinize.cfg
	echo vol_name=rootfs >> $WORKDIR/ubinize.cfg
	echo vol_flags=autoresize >> $WORKDIR/ubinize.cfg
	touch $WORKDIR/root.ubi
	chmod 644 $WORKDIR/root.ubi
	# mkfs.ubifs has the weird behaviour that it refuses to make an image from the current rootfs, even though we bind mounted it
	# So we have to copy everything to our workdir, and run mkfs.ubifs from there
	#cp -ar /tmp/bi/root $WORKDIR/root
	#$MKFS -r $WORKDIR/root -o $WORKDIR/root.ubi $MKUBIFS_ARGS
	$MKFS -r /tmp/bi/root -o $WORKDIR/root.ubi $MKUBIFS_ARGS
	$UBINIZE -o $WORKDIR/root.ubifs $UBINIZE_ARGS $WORKDIR/ubinize.cfg
fi
chmod 644 $WORKDIR/root.$ROOTFSTYPE

echo "Create: kerneldump"
nanddump -a -f $WORKDIR/vmlinux.gz /dev/$MTDKERNEL
echo "Check: kerneldump"
sync
gzip -d $WORKDIR/vmlinux.gz -c > /tmp/vmlinux.bin
RETURN=$?
if [ ! $RETURN = "0" ] ; then
   echo "Kernel dump error"
   echo "Please Flash your Kernel new and Backup again"
   rm -rf /tmp/vmlinux.bin
   exit 0
fi
echo "Kernel dump OK"
rm -rf /tmp/vmlinux.bin

echo "_________________________________________________"
echo " "
echo "Almost there... "
echo "Now building the USB-Image"


if [ $TYPE = "GIGABLUE" ] ; then
	rm -rf $MAINDEST
	mkdir -p $MAINDEST
	mkdir -p $EXTRA
	if [ $ROOTFSTYPE = "jffs2" ] ; then
		mv $WORKDIR/root.jffs2 $MAINDEST/rootfs.bin
	else
		mv $WORKDIR/root.ubifs $MAINDEST/rootfs.bin
	fi
	mv $WORKDIR/vmlinux.gz $MAINDEST/kernel.bin
	echo "rename this file to 'force' to force an update without confirmation" > $MAINDEST/noforce
	echo $MODEL-$IMAGEVERSION > $MAINDEST/imageversion
	macaddr=`ifconfig eth0 | awk '/HWaddr/ {print $5}' | tr -s : -`
	[ -f $MAINDEST/../../burn.bat ] && rm $MAINDEST/../../burn.bat
	if [ $MODEL = "solo" ]; then
		touch $MAINDEST/../../burn.bat
		echo "flash -noheader usbdisk0:gigablue/$MODEL/kernel.bin flash0.kernel " >> $MAINDEST/../../burn.bat
		echo "flash -noheader usbdisk0:gigablue/$MODEL/rootfs.bin flash0.rootfs " >> $MAINDEST/../../burn.bat
		echo 'setenv -p STARTUP "boot -z -elf flash0.kernel:"  ' >> $MAINDEST/../../burn.bat
		cp $MAINDEST/../../burn.bat $EXTRA/..
		mv $MAINDEST/../../burn.bat $MAINDEST/../../noburn.bat
	fi

	cp -r $MAINDEST $EXTRA #copy the made back-up to images
	if [ -f $MAINDEST/rootfs.bin -a -f $MAINDEST/kernel.bin -a -f $MAINDEST/imageversion -a -f $MAINDEST/noforce ]  ; then
		echo "_________________________________________________\n"
		echo "USB Image created on:" $MAINDEST
		echo "and there is made an extra copy on:"
		echo $EXTRA
		echo "_________________________________________________\n"
		echo " "
		echo "To restore the image: \n"
		echo "Place the USB-flash drive in the USB-port "
		echo "and power off the Gigablue. "
		echo "and power on the Gigablue. "
		echo "\nPlease wait...almost ready! "
	else
		echo "Image creation failed - "
		echo "Probable causes could be"
		echo "     wrong back-up destination "
		echo "     no space left on back-up device"
		echo "     no writing permission on back-up device"
		echo " "
	fi
fi
if [ $DIRECTORY == /hdd ]; then
	TARGET="XX"
	for candidate in  /media/usb /media/sdb1 /media/sdc1 /media/sdd1 /media/sde1 /media/mmc1
	do
		if [ -f ${candidate}/*backupstick* ]
		then
		TARGET=${candidate}
		fi
	done

	if [ $TARGET = "XX" ]
		then
		echo
	else
		echo _________________________________________________
		echo
		echo "There is a valid USB-flash drive detected in one "
		echo "of the USB-ports, therefor an extra copy of the "
		echo "back-up image will now be copied to that USB- "
		echo "flash drive. "
		echo "This only takes about 15 seconds"
		echo
		
		if [ $TYPE = "GIGABLUE" ] ; then				# Gigablue detected
			mkdir -p $TARGET/gigablue/$MODEL
			cp -r $MAINDEST $TARGET/gigablue/

		else
			echo
		fi
    sync
	echo "Backup finished and copied to your USB-flash drive"
	fi
fi
umount /tmp/bi/root
rmdir /tmp/bi/root
rmdir /tmp/bi
rm -rf $WORKDIR
sleep 5
END=$(date +%s)
DIFF=$(( $END - $START ))
MINUTES=$(( $DIFF/60 ))
SECONDS=$(( $DIFF-(( 60*$MINUTES ))))
if [ $SECONDS -le  9 ] ; then
	SECONDEN="0$SECONDS"
else
	SECONDEN=$SECONDS
fi
echo " Time required for this process: $MINUTES:$SECONDEN"
exit

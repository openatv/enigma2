###############################################################################
# FULL BACKUP UYILITY FOR ENIGMA2/OPENPLI, SUPPORTS THE MODELS ET-XX00 & VU+  #
#  							& Gigablue & Venton HD Models			   		  #
#                   MAKES A FULLBACK-UP READY FOR FLASHING.                   #
#                                                                             #
###############################################################################
#
#!/bin/sh
VERSION="Version 9.1 MOD"
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
## TESTING THE XTREND AND CLARK TECH MODELS
MODEL=$( cat /etc/model )
if [ $MODEL = "et9x00" ] || [ $MODEL = "et5x00" ] || [ $MODEL = "et6x00" ] || [ $MODEL = "et6500" ] || [ $MODEL = "et4x00" ]; then
	TYPE=ET
	MKUBIFS_ARGS="-m 2048 -e 126976 -c 4096"
	UBINIZE_ARGS="-m 2048 -p 128KiB"
	SHOWNAME="Xtrend $MODEL"
	MAINDESTOLD=$DIRECTORY/$MODEL
	MAINDEST=$DIRECTORY/${MODEL:0:3}x00
	EXTRAOLD=$DIRECTORY/fullbackup_$MODEL/$DATE/$MODEL
	EXTRA=$DIRECTORY/fullbackup_${MODEL:0:3}x00/$DATE
	if grep boot /proc/mtd > /dev/null ; then
		MTDROOT=3
		MTDBOOT=2
		JFFS2OPTIONS="--eraseblock=0x20000 -n -l"
		MAINDESTOLD=$DIRECTORY/$MODEL
		EXTRAOLD=$DIRECTORY/fullbackup_$MODEL/$DATE/$MODEL
	fi
## TESTING THE Odin M9 Model	
elif [ $MODEL = "odinm9" ] ; then
	TYPE=ODINM9
	MKUBIFS_ARGS="-m 2048 -e 126976 -c 4096"
	UBINIZE_ARGS="-m 2048 -p 128KiB"
	SHOWNAME="ODIN $MODEL"
	MTDKERNEL="mtd2"
	MAINDESTOLD=$DIRECTORY/$MODEL
	MAINDEST=$DIRECTORY/odinm9
	EXTRAOLD=$DIRECTORY/fullbackup_$MODEL/$DATE/$MODEL
	EXTRA=$DIRECTORY/fullbackup_odinm9/$DATE
## TESTING THE Odin M7 Model	
elif [ $MODEL = "odinm7" ] ; then
	TYPE=ODINM7
	MKUBIFS_ARGS="-m 2048 -e 126976 -c 4096"
	UBINIZE_ARGS="-m 2048 -p 128KiB"
	SHOWNAME="ODIN $MODEL"
	MTDKERNEL="mtd2"
	MAINDESTOLD=$DIRECTORY/$MODEL
	MAINDEST=$DIRECTORY/en2
	EXTRAOLD=$DIRECTORY/fullbackup_$MODEL/$DATE/$MODEL
	EXTRA=$DIRECTORY/fullbackup_odinm7/$DATE	
elif [ $MODEL = "xp1000" ] ; then
	TYPE=MAXDIGITAL
	MKUBIFS_ARGS="-m 2048 -e 126976 -c 4096"
	UBINIZE_ARGS="-m 2048 -p 128KiB"
	SHOWNAME="MaxDigital $MODEL"
	MTDKERNEL="mtd1"
	MAINDESTOLD=$DIRECTORY/$MODEL
	MAINDEST=$DIRECTORY/$MODEL
	EXTRA=$DIRECTORY/fullbackup_$TYPE/$DATE
## TESTING THE Venton HDx Models
elif [ $MODEL = "ixussone" ] ; then
	TYPE=IXUSS
	MKUBIFS_ARGS="-m 2048 -e 126976 -c 4096"
	UBINIZE_ARGS="-m 2048 -p 128KiB"
	SHOWNAME="Medialink $MODEL"
	MTDKERNEL="mtd2"
	MAINDESTOLD=$DIRECTORY/medialink/$MODEL
	MAINDEST=$DIRECTORY/medialink/$MODEL
	EXTRA=$DIRECTORY/fullbackup_$TYPE/$DATE
## TESTING THE Venton HDx Models
elif [ $MODEL = "ventonhdx" ] ; then
	TYPE=VENTON
	MODEL="venton-hdx"
	MKUBIFS_ARGS="-m 2048 -e 126976 -c 4096"
	UBINIZE_ARGS="-m 2048 -p 128KiB"
	SHOWNAME="$MODEL"
	MAINDESTOLD=$DIRECTORY/$MODEL
	MAINDEST=$DIRECTORY/venton/$MODEL
	EXTRA=$DIRECTORY/fullbackup_$MODEL/$DATE/venton
elif [ $MODEL = "tmtwin" ] ; then
	TYPE=TECHNO
	MODEL="tmtwinoe"
	MKUBIFS_ARGS="-m 2048 -e 126976 -c 4096 -F"
	UBINIZE_ARGS="-m 2048 -p 128KiB"
	SHOWNAME="$MODEL"
	MAINDESTOLD=$DIRECTORY/$MODEL
	MAINDEST=$DIRECTORY/update/$MODEL/cfe
	EXTRA=$DIRECTORY/fullbackup_TECHNO/$DATE/update/$MODEL/cfe
elif [ $MODEL = "tmsingle" ] ; then
	TYPE=TECHNO
	MODEL="tmsingle"
	MKUBIFS_ARGS="-m 2048 -e 126976 -c 4096 -F"
	UBINIZE_ARGS="-m 2048 -p 128KiB"
	SHOWNAME="$MODEL"
	MAINDESTOLD=$DIRECTORY/$MODEL
	MAINDEST=$DIRECTORY/update/$MODEL/cfe
	EXTRA=$DIRECTORY/fullbackup_TECHNO/$DATE/update/$MODEL/cfe
elif [ $MODEL = "tm2t" ] ; then
	TYPE=TECHNO
	MODEL="tm2toe"
	MKUBIFS_ARGS="-m 2048 -e 126976 -c 4096 -F"
	UBINIZE_ARGS="-m 2048 -p 128KiB"
	SHOWNAME="$MODEL"
	MAINDESTOLD=$DIRECTORY/$MODEL
	MAINDEST=$DIRECTORY/update/$MODEL/cfe
	EXTRA=$DIRECTORY/fullbackup_TECHNO/$DATE/update/$MODEL/cfe	
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
	
## TESTING THE VU+ MODELS
elif [ $MODEL = "vusolo" ] || [ $MODEL = "vuduo" ] || [ $MODEL = "vuuno" ] || [ $MODEL = "vuultimo" ] || [ $MODEL = "vusolo2" ] || [ $MODEL = "vuduo2" ]; then
	TYPE=VU
	if [ $MODEL = "vusolo2" ] || [ $MODEL = "vuduo2" ]; then
		MTDKERNEL="mtd2"
	fi
	SHOWNAME="VU+ ${MODEL:2}"
	MAINDEST=$DIRECTORY/vuplus_back/${MODEL:2}
	EXTRA=$DIRECTORY/fullbackup_${MODEL:2}/$DATE/vuplus 
	if [ $ROOTFSTYPE = "ubifs" ] ; then
		MKUBIFS_ARGS="-m 2048 -e 126976 -c 4096 -F"
		UBINIZE_ARGS="-m 2048 -p 128KiB"
	else
		MTDROOT=0
		MTDBOOT=2
		JFFS2OPTIONS="--eraseblock=0x20000 -n -l"
	fi
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
else 
	echo "this will take between 2 and 4 minutes "
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


if [ $TYPE = "ET" ] ; then
	rm -rf $MAINDEST
	mkdir -p $MAINDEST
	mkdir -p $EXTRA
	mv $WORKDIR/root.$ROOTFSTYPE $MAINDEST/rootfs.bin 
	mv $WORKDIR/vmlinux.gz $MAINDEST/kernel.bin
	echo "rename this file to 'force' to force an update without confirmation" > $MAINDEST/noforce;
	echo ${MODEL:0:3}x00-$IMAGEVERSION > $MAINDEST/imageversion
	cp -r $MAINDEST $EXTRA #copy the made back-up to images
	if [ -f $MAINDEST/rootfs.bin -a -f $MAINDEST/kernel.bin -a -f $MAINDEST/imageversion -a -f $MAINDEST/noforce ] ; then
		echo "_________________________________________________"
		echo " "
		echo "USB Image created on:  $MAINDEST "
		echo "and there is made an extra copy on:"
		echo $EXTRA
		echo "_________________________________________________"
		echo " "
		if [ ${MODEL:0:3}x00 = "et9x00" ] || [ $MODEL = "et6500" ]; then
			echo "To restore the image: "
			echo "Place the USB-flash drive in the (front) USB-port "
			echo "and switch the $MODEL off and on with the "
			echo "powerswitch on the back of the $MODEL"
			echo "Follow the instructions on the front-display."
			echo "Please wait....   almost ready"

		elif [ $MODEL = "et5x00" ] || [ $MODEL = "et6x00" ] || [ $MODEL = "et4x00" ] ; then
			echo "To restore the image:\n "
			echo "Place the USB-flash drive in the (front) USB-port "
			echo "and switch the $MODEL off and on with the "
			echo "powerswitch on the back of the $MODEL"
			echo "Press arrow up from frontpanel to start loading."
			echo " "
			echo "Please wait a little bit longer, almost ready "
	
		else
			echo "Please check te manual of the receiver "
			echo "on how to restore the image"
		fi
	else
		echo "Image creation failed - "
		echo "Probable causes could be"
		echo "     wrong back-up destination "
		echo "     no space left on back-up device"
		echo "     no writing permission on back-up device"
		echo " "
	fi
	if grep boot /proc/mtd > /dev/null ; then
		rm -rf $MAINDESTOLD
		mkdir -p $MAINDESTOLD
		mkdir -p $EXTRAOLD
		cp -r $MAINDEST/* $MAINDESTOLD		#copy when bootloader is not update
		cp -r $MAINDEST/* $EXTRAOLD		#copy extracopy to the old stucture
		echo "_________________________________________________"
		echo " Old version bootloader found"
		echo " For compatibility the image in placed on: "
		echo " $MAINDESTOLD "
		echo " and there is made an extra copy on:"
		echo " $EXTRAOLD "
		echo "_________________________________________________"
		echo " "
	fi
fi
if [ $TYPE = "VU" ] ; then
	rm -rf $MAINDEST
	mkdir -p $MAINDEST
	mkdir -p $EXTRA/${MODEL:2}
	if [ $ROOTFSTYPE = "ubifs" ] ; then
		if [ $MODEL = "vusolo2" ] || [ $MODEL = "vuduo2" ]; then
			mv $WORKDIR/root.ubifs $MAINDEST/root_cfe_auto.bin
		else
			mv $WORKDIR/root.ubifs $MAINDEST/root_cfe_auto.jffs2
		fi
		mv $WORKDIR/root.ubifs $MAINDEST/root_cfe_auto.jffs2
	else
		mv $WORKDIR/root.jffs2 $MAINDEST/root_cfe_auto.jffs2
	fi
	echo vuplus-reboot > $MAINDEST/reboot.update
	mv $WORKDIR/vmlinux.gz $MAINDEST/kernel_cfe_auto.bin
	cp -r $MAINDEST $EXTRA #copy the made back-up to images
	if [ -f $MAINDEST/root_cfe_auto.jffs2 -a -f $MAINDEST/kernel_cfe_auto.bin -a -f $MAINDEST/reboot.update ] ; then
		echo "_________________________________________________\n"
		echo "USB Image created on:" $MAINDEST
		echo "and there is made an extra copy on:"
		echo $EXTRA
		echo "_________________________________________________\n"
		echo " "
		echo "To restore the image: \n"
		echo "Place the USB-flash drive in the (front) USB-port "
		echo "and switch the VU+ off and on with the powerswitch "
		echo "on the back of the VU+. Follow the instructions "
		echo "on the front-display.\n"
		echo "\nPlease wait...almost ready! "
	elif [ -f $MAINDEST/root_cfe_auto.bin -a -f $MAINDEST/kernel_cfe_auto.bin -a -f $MAINDEST/reboot.update ] ; then
		echo "_________________________________________________\n"
		echo "USB Image created on:" $MAINDEST
		echo "and there is made an extra copy on:"
		echo $EXTRA
		echo "_________________________________________________\n"
		echo " "
		echo "To restore the image: \n"
		echo "Place the USB-flash drive in the (front) USB-port "
		echo "and switch the VU+ off and on with the powerswitch "
		echo "on the back of the VU+. Follow the instructions "
		echo "on the front-display.\n"
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
if [ $TYPE = "VENTON" ] ; then
	rm -rf $MAINDEST
	mkdir -p $MAINDEST
	mkdir -p $EXTRA/$MODEL
	mv $WORKDIR/root.ubifs $MAINDEST/rootfs.bin
	mv $WORKDIR/vmlinux.gz $MAINDEST/kernel.bin
	echo "rename this file to 'force' to force an update without confirmation" > $MAINDEST/noforce
	echo ${MODEL}-$IMAGEVERSION > $MAINDEST/imageversion
	cp -r $MAINDEST $EXTRA #copy the made back-up to images
	if [ -f $MAINDEST/rootfs.bin -a -f $MAINDEST/kernel.bin -a -f $MAINDEST/imageversion -a -f $MAINDEST/noforce ] ; then
		echo "_________________________________________________\n"
		echo "USB Image created on:" $MAINDEST
		echo "and there is made an extra copy on:"
		echo $EXTRA
		echo "_________________________________________________\n"
		echo " "
		echo "To restore the image: \n"
		echo "Place the USB-flash drive in the (back) USB-port "
		echo "and switch the Venton off and on with the powerswitch "
		echo "on the back of the Venton. Follow the instructions "
		echo "on the front-display.\n"
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

if [ $TYPE = "TECHNO" ] ; then
	rm -rf $MAINDEST
	mkdir -p $MAINDEST
	mkdir -p $EXTRA/$MODEL
	mv $WORKDIR/root.ubifs $MAINDEST/oe_rootfs.bin
	mv $WORKDIR/vmlinux.gz $MAINDEST/oe_kernel.bin
	echo ${MODEL}-$IMAGEVERSION > $MAINDEST/imageversion
	cp -r $MAINDEST $EXTRA #copy the made back-up to images
	if [ -f $MAINDEST/oe_rootfs.bin -a -f $MAINDEST/oe_kernel.bin -a -f $MAINDEST/imageversion] ; then
		echo "_________________________________________________\n"
		echo "USB Image created on:" $MAINDEST
		echo "and there is made an extra copy on:"
		echo $EXTRA
		echo "_________________________________________________\n"
		echo " "
		echo "To restore the image: \n"
		echo "Place the USB-flash drive in the (front) USB-port "
		echo "and switch the Technomate off and on with the powerswitch "
		echo "on the back of the Technomate. Follow the instructions "
		echo "on the front-display.\n"
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

if [ $TYPE = "ODINM9" ] ; then
	rm -rf $MAINDEST
	mkdir -p $MAINDEST
	mkdir -p $EXTRA
	mv $WORKDIR/root.$ROOTFSTYPE $MAINDEST/rootfs.bin 
	mv $WORKDIR/vmlinux.gz $MAINDEST/kernel.bin
	echo "rename this file to 'force' to force an update without confirmation" > $MAINDEST/noforce
	echo $MODEL-$IMAGEVERSION > $MAINDEST/imageversion
	cp -r $MAINDEST $EXTRA #copy the made back-up to images
	if [ -f $MAINDEST/rootfs.bin -a -f $MAINDEST/kernel.bin -a -f $MAINDEST/imageversion -a -f $MAINDEST/noforce ] ; then
		echo "_________________________________________________\n"
		echo "USB Image created on:" $MAINDEST
		echo "and there is made an extra copy on:"
		echo $EXTRA
		echo "_________________________________________________\n"
		echo " "
		echo "To restore the image: \n"
		echo "Place the USB-flash drive in the (front) USB-port "
		echo "and switch the Odin M9 off and on with the powerswitch "
		echo "on the back of the Odin M9. Follow the instructions "
		echo "on the front-display.\n"
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

if [ $TYPE = "ODINM7" ] ; then
	rm -rf $MAINDEST
	mkdir -p $MAINDEST
	mkdir -p $EXTRA
	mv $WORKDIR/root.$ROOTFSTYPE $MAINDEST/rootfs.bin 
	mv $WORKDIR/vmlinux.gz $MAINDEST/kernel.bin
	echo "rename this file to 'force' to force an update without confirmation" > $MAINDEST/noforce;
	echo $MODEL-$IMAGEVERSION > $MAINDEST/imageversion
	cp -r $MAINDEST $EXTRA #copy the made back-up to images
	if [ -f $MAINDEST/rootfs.bin -a -f $MAINDEST/kernel.bin -a -f $MAINDEST/imageversion -a -f $MAINDEST/noforce ] ; then
		echo "_________________________________________________\n"
		echo "USB Image created on:" $MAINDEST
		echo "and there is made an extra copy on:"
		echo $EXTRA
		echo "_________________________________________________\n"
		echo " "
		echo "To restore the image: \n"
		echo "Place the USB-flash drive in the (front) USB-port "
		echo "and switch the Odin M7 off and on with the powerswitch "
		echo "on the back of the Odin M7. Follow the instructions "
		echo "on the front-display.\n"
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

if [ $TYPE = "MAXDIGITAL" ] ; then
	rm -rf $MAINDEST
	mkdir -p $MAINDEST
	mkdir -p $EXTRA
	mv $WORKDIR/root.$ROOTFSTYPE $MAINDEST/rootfs.bin 
	mv $WORKDIR/vmlinux.gz $MAINDEST/kernel.bin
	echo "rename this file to 'force' to force an update without confirmation" > $MAINDEST/noforce
	echo $MODEL-$IMAGEVERSION > $MAINDEST/imageversion
	cp -r $MAINDEST $EXTRA #copy the made back-up to images
	if [ -f $MAINDEST/rootfs.bin -a -f $MAINDEST/kernel.bin -a -f $MAINDEST/imageversion -a -f $MAINDEST/noforce ] ; then
		echo "_________________________________________________\n"
		echo "USB Image created on:" $MAINDEST
		echo "and there is made an extra copy on:"
		echo $EXTRA
		echo "_________________________________________________\n"
		echo " "
		echo "To restore the image: \n"
		echo "Place the USB-flash drive in the (back) USB-port "
		echo "and switch the MaxDigital off and on with the powerswitch "
		echo "on the back of the MaxDigital."
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

if [ $TYPE = "IXUSS" ] ; then
	rm -rf $MAINDEST
	mkdir -p $MAINDEST
	mkdir -p $EXTRA
	mv $WORKDIR/root.$ROOTFSTYPE $MAINDEST/rootfs.bin 
	mv $WORKDIR/vmlinux.gz $MAINDEST/kernel.bin
	echo "rename this file to 'force' to force an update without confirmation" > $MAINDEST/noforce
	echo $MODEL-$IMAGEVERSION > $MAINDEST/imageversion
	cp -r $MAINDEST $EXTRA #copy the made back-up to images
	if [ -f $MAINDEST/rootfs.bin -a -f $MAINDEST/kernel.bin -a -f $MAINDEST/imageversion -a -f $MAINDEST/noforce ] ; then
		echo "_________________________________________________\n"
		echo "USB Image created on:" $MAINDEST
		echo "and there is made an extra copy on:"
		echo $EXTRA
		echo "_________________________________________________\n"
		echo " "
		echo "To restore the image: \n"
		echo "Place the USB-flash drive in the (back) USB-port "
		echo "and switch the Medialink off and on with the powerswitch "
		echo "on the back of the Medialink."
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
		if [ $TYPE = "ET" ] ; then
			if grep boot /proc/mtd > /dev/null ; then	# Old bootloader detected
				rm -rf $TARGET/${MODEL:0:3}x00
				rm -rf $TARGET/$MODEL
				mkdir -p $TARGET/${MODEL:0:3}x00
				mkdir -p $TARGET/$MODEL
				cp -r $MAINDEST $TARGET
				cp -r $MAINDESTOLD $TARGET
			else
				rm -rf $TARGET/${MODEL:0:3}x00			# New bootloader/image
				rm -rf $TARGET/$MODEL
				mkdir -p $TARGET/${MODEL:0:3}x00
				cp -r $MAINDEST $TARGET
			fi
		elif [ $TYPE = "VU" ] ; then					# VU+ detected
			mkdir -p $TARGET/vuplus_back/${MODEL:2}
			cp -r $MAINDEST $TARGET/vuplus_back/
		elif [ $TYPE = "VENTON" ] ; then				# Venton detected
			mkdir -p $TARGET/venton/$MODEL
			cp -r $MAINDEST $TARGET/venton/	
		elif [ $TYPE = "GIGABLUE" ] ; then				# Gigablue detected
			mkdir -p $TARGET/gigablue/$MODEL
			cp -r $MAINDEST $TARGET/gigablue/
		elif [ $TYPE = "ODINM9" ] ; then					# Odin M9 detected
			#mkdir -p $TARGET/odinm9/$MODEL
			cp -r $MAINDEST $TARGET/
		elif [ $TYPE = "ODINM7" ] ; then					# Odin M7 detected
			#mkdir -p $TARGET
			cp -r $MAINDEST $TARGET/		
		elif [ $TYPE = "MAXDIGITAL" ] ; then					# MaxDigital detected
			mkdir -p $TARGET/$MODEL
			cp -r $MAINDEST $TARGET
		elif [ $TYPE = "IXUSS" ] ; then					# Medialink detected
			mkdir -p $TARGET/$MODEL
			cp -r $MAINDEST $TARGET			
		elif [ $TYPE = "TECHNO" ] ; then					# Technomate detected
			mkdir -p $TARGET/update/$MODEL/cfe
			cp -r $MAINDEST $TARGET/update/$MODEL/cfe			
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
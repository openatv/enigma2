#################################################################################
# FULL BACKUP UYILITY FOR ENIGMA2, SUPPORTS THE MODELS OE-A 4.3     			#
#	                         						                            #
#					MAKES A FULLBACK-UP READY FOR FLASHING.						#
#																				#
#################################################################################
from enigma import getEnigmaVersionString
from Screens.Screen import Screen
from Components.Sources.StaticText import StaticText
from Components.SystemInfo import SystemInfo
from Components.Label import Label
from Components.ActionMap import ActionMap
from Components.About import about
from Components import Harddisk
from Screens.Console import Console
from Screens.MessageBox import MessageBox
from time import time, strftime, localtime
from os import path, system, makedirs, listdir, walk, statvfs, remove
import commands
import datetime
from boxbranding import getBoxType, getMachineBrand, getMachineName, getDriverDate, getImageVersion, getImageBuild, getBrandOEM, getMachineBuild, getImageFolder, getMachineUBINIZE, getMachineMKUBIFS, getMachineMtdKernel, getMachineMtdRoot, getMachineKernelFile, getMachineRootFile, getImageFileSystem

VERSION = _("Version") + " 6.3 openATV"

HaveGZkernel = True
if getMachineBuild() in ('gbmv200','multibox','vuduo4k','v8plus','ustym4kpro','hd60','hd61','i55plus','osmio4k','sf8008','cc1','dags72604', 'u41', 'u51','u52','u53','u54','u55','h9','h9combo','vuzero4k','u5','u5pvr','sf5008','et13000','et1x000',"vuuno4k","vuuno4kse", "vuultimo4k", "vusolo4k", "spark", "spark7162", "hd51", "hd52", "sf4008", "dags7252", "gb7252", "vs1500","h7",'xc7439','8100s'):
	HaveGZkernel = False

def Freespace(dev):
	statdev = statvfs(dev)
	space = (statdev.f_bavail * statdev.f_frsize) / 1024
	print "[FULL BACKUP] Free space on %s = %i kilobytes" %(dev, space)
	return space

class ImageBackup(Screen):
	skin = """
	<screen position="center,center" size="560,400" title="Image Backup">
		<ePixmap position="0,360"   zPosition="1" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
		<ePixmap position="140,360" zPosition="1" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />
		<ePixmap position="280,360" zPosition="1" size="140,40" pixmap="skin_default/buttons/yellow.png" transparent="1" alphatest="on" />
		<ePixmap position="420,360" zPosition="1" size="140,40" pixmap="skin_default/buttons/blue.png" transparent="1" alphatest="on" />
		<widget source="key_red" render="Label" position="0,360" zPosition="2" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
		<widget source="key_green" render="Label" position="140,360" zPosition="2" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
		<widget source="key_yellow" render="Label" position="280,360" zPosition="2" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
		<widget source="key_blue" render="Label" position="420,360" zPosition="2" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
		<widget name="info-hdd" position="10,30" zPosition="1" size="450,100" font="Regular;20" halign="left" valign="top" transparent="1" />
		<widget name="info-multi" position="10,80" zPosition="1" size="450,100" font="Regular;20" halign="left" valign="top" transparent="1" />
		<widget name="info-usb" position="10,150" zPosition="1" size="450,200" font="Regular;20" halign="left" valign="top" transparent="1" />
	</screen>"""

	def __init__(self, session, args = 0):
		Screen.__init__(self, session)
		self.session = session
		self.selection = 0
		self.MODEL = getBoxType()
		self.OEM = getBrandOEM()
		self.MACHINEBUILD = getMachineBuild()
		self.MACHINENAME = getMachineName()
		self.MACHINEBRAND = getMachineBrand()
		self.IMAGEFOLDER = getImageFolder()
		self.UBINIZE_ARGS = getMachineUBINIZE()
		self.MKUBIFS_ARGS = getMachineMKUBIFS()
		self.MTDKERNEL = getMachineMtdKernel()
		self.MTDROOTFS = getMachineMtdRoot()
		self.ROOTFSBIN = getMachineRootFile()
		self.KERNELBIN = getMachineKernelFile()
		self.ROOTFSTYPE = getImageFileSystem().strip()

		if self.MACHINEBUILD in ("hd51","vs1500","h7","8100s"):
			self.MTDBOOT = "mmcblk0p1"
			self.EMMCIMG = "disk.img"
		elif self.MACHINEBUILD in ("xc7439","osmio4k"):
			self.MTDBOOT = "mmcblk1p1"
			self.EMMCIMG = "emmc.img"
		elif self.MACHINEBUILD in ("gbmv200","cc1","sf8008","ustym4kpr"):
			self.MTDBOOT = "none"
			self.EMMCIMG = "usb_update.bin"
		elif self.MACHINEBUILD in ("h9combo","v8plus","multibox","hd60","hd61"):
			self.MTDBOOT = "none"
			self.EMMCIMG = "rootfs.fastboot.gz"
		else:
			self.MTDBOOT = "none"
			self.EMMCIMG = "none"

		print "[FULL BACKUP] BOX MACHINEBUILD = >%s<" %self.MACHINEBUILD
		print "[FULL BACKUP] BOX MACHINENAME = >%s<" %self.MACHINENAME
		print "[FULL BACKUP] BOX MACHINEBRAND = >%s<" %self.MACHINEBRAND
		print "[FULL BACKUP] BOX MODEL = >%s<" %self.MODEL
		print "[FULL BACKUP] OEM MODEL = >%s<" %self.OEM
		print "[FULL BACKUP] IMAGEFOLDER = >%s<" %self.IMAGEFOLDER
		print "[FULL BACKUP] UBINIZE = >%s<" %self.UBINIZE_ARGS
		print "[FULL BACKUP] MKUBIFS = >%s<" %self.MKUBIFS_ARGS
		print "[FULL BACKUP] MTDBOOT = >%s<" %self.MTDBOOT
		print "[FULL BACKUP] MTDKERNEL = >%s<" %self.MTDKERNEL
		print "[FULL BACKUP] MTDROOTFS = >%s<" %self.MTDROOTFS
		print "[FULL BACKUP] ROOTFSBIN = >%s<" %self.ROOTFSBIN
		print "[FULL BACKUP] KERNELBIN = >%s<" %self.KERNELBIN
		print "[FULL BACKUP] ROOTFSTYPE = >%s<" %self.ROOTFSTYPE
		print "[FULL BACKUP] EMMCIMG = >%s<" %self.EMMCIMG

		self.error_files = ''
		self.list = self.list_files("/boot")
		self["key_green"] = StaticText("USB")
		self["key_red"] = StaticText("HDD")
		self["key_blue"] = StaticText(_("Exit"))
		if SystemInfo["HaveMultiBoot"]:
			self["key_yellow"] = StaticText(_("STARTUP"))
			self["info-multi"] = Label(_("You can select with yellow the OnlineFlash Image\n or select Recovery to create a USB Disk Image for clean Install."))
			self.read_current_multiboot()
		else:
			self["key_yellow"] = StaticText("")
			self["info-multi"] = Label(" ")
		self["info-usb"] = Label(_("USB = Do you want to make a back-up on USB?\nThis will take between 3 and 15 minutes depending on the used filesystem and is fully automatic.\nMake sure you first insert a USB flash drive before you select USB."))
		self["info-hdd"] = Label(_("HDD = Do you want to make a USB-back-up image on HDD? \nThis only takes 1 or 10 minutes and is fully automatic."))
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], 
		{
			"blue": self.quit,
			"yellow": self.yellow,
			"green": self.green,
			"red": self.red,
			"cancel": self.quit,
		}, -2)
		self.onShown.append(self.show_Errors)

	def show_Errors(self):
		if self.error_files:
			self.session.open(MessageBox, _('Index Error in the following files: %s') %self.error_files[:-2], type = MessageBox.TYPE_ERROR)
			self.error_files = ''

	def check_hdd(self):
		if not path.exists("/media/hdd"):
			self.session.open(MessageBox, _("No /hdd found !!\nPlease make sure you have a HDD mounted.\n"), type = MessageBox.TYPE_ERROR)
			return False
		if Freespace('/media/hdd') < 300000:
			self.session.open(MessageBox, _("Not enough free space on /hdd !!\nYou need at least 300Mb free space.\n"), type = MessageBox.TYPE_ERROR)
			return False
		return True

	def check_usb(self, dev):
		if Freespace(dev) < 300000:
			self.session.open(MessageBox, _("Not enough free space on %s !!\nYou need at least 300Mb free space.\n" % dev), type = MessageBox.TYPE_ERROR)
			return False
		return True
		
	def quit(self):
		self.close()
		
	def red(self):
		if self.check_hdd():
			self.doFullBackup("/hdd")

	def green(self):
		USB_DEVICE = self.SearchUSBcanidate()
		if USB_DEVICE == 'XX':
			text = _("No USB-Device found for fullbackup !!\n\n\n")
			text += _("To back-up directly to the USB-stick, the USB-stick MUST\n")
			text += _("contain a file with the name: \n\n")
			text += _("backupstick or backupstick.txt")
			self.session.open(MessageBox, text, type = MessageBox.TYPE_ERROR)
		else:
			if self.check_usb(USB_DEVICE):
				self.doFullBackup(USB_DEVICE)

	def yellow(self):
		if SystemInfo["HaveMultiBoot"]:
			self.selection = self.selection + 1
			if self.selection == len(self.list):
				self.selection = 0
			self["key_yellow"].setText(_(self.list[self.selection]))
			self.read_current_multiboot()

	def read_current_multiboot(self):
		if self.MACHINEBUILD in ("hd51","vs1500","h7"):
			if self.list[self.selection] == "Recovery":
				cmdline = self.read_startup("/boot/STARTUP").split("=",3)[3].split(" ",1)[0]
			else:
				cmdline = self.read_startup("/boot/" + self.list[self.selection]).split("=",3)[3].split(" ",1)[0]
		elif self.MACHINEBUILD in ("8100s"):
			if self.list[self.selection] == "Recovery":
				cmdline = self.read_startup("/boot/STARTUP").split("=",4)[4].split(" ",1)[0]
			else:
				cmdline = self.read_startup("/boot/" + self.list[self.selection]).split("=",4)[4].split(" ",1)[0]
		elif self.MACHINEBUILD in ("gbmv200","cc1","sf8008","ustym4kpro"):
			if self.list[self.selection] == "Recovery":
				cmdline = self.read_startup("/boot/STARTUP").split("=",1)[1].split(" ",1)[0]
			else:
				cmdline = self.read_startup("/boot/" + self.list[self.selection]).split("=",1)[1].split(" ",1)[0]
		elif self.MACHINEBUILD in ("osmio4k"):
			if self.list[self.selection] == "Recovery":
				cmdline = self.read_startup("/boot/STARTUP").split("=",1)[1].split(" ",1)[0]
			else:
				cmdline = self.read_startup("/boot/" + self.list[self.selection]).split("=",1)[1].split(" ",1)[0]
		else:
			if self.list[self.selection] == "Recovery":
				cmdline = self.read_startup("/boot/cmdline.txt").split("=",1)[1].split(" ",1)[0]
			else:
				cmdline = self.read_startup("/boot/" + self.list[self.selection]).split("=",1)[1].split(" ",1)[0]
		cmdline = cmdline.lstrip("/dev/")
		self.MTDROOTFS = cmdline
		self.MTDKERNEL = cmdline[:-1] + str(int(cmdline[-1:]) -1)
		print "[FULL BACKUP] Multiboot rootfs ", self.MTDROOTFS
		print "[FULL BACKUP] Multiboot kernel ", self.MTDKERNEL

	def read_startup(self, FILE):
		self.file = FILE
		with open(self.file, 'r') as myfile:
			data=myfile.read().replace('\n', '')
		myfile.close()
		return data

	def list_files(self, PATH):
		files = []
		if SystemInfo["HaveMultiBoot"]:
			self.path = PATH
			for name in listdir(self.path):
				if path.isfile(path.join(self.path, name)):
					try:
						if self.MACHINEBUILD in ("hd51","vs1500","h7"):
							cmdline = self.read_startup("/boot/" + name).split("=",3)[3].split(" ",1)[0]
						elif self.MACHINEBUILD in ("8100s"):
							cmdline = self.read_startup("/boot/" + name).split("=",4)[4].split(" ",1)[0]
						else:
							cmdline = self.read_startup("/boot/" + name).split("=",1)[1].split(" ",1)[0]
						if cmdline in Harddisk.getextdevices("ext4"):
							files.append(name)
					except IndexError:
						print '[ImageBackup] - IndexError in file: %s' %name
						self.error_files += '/boot/' + name + ', ' 
			if getMachineBuild() not in ("gb7252"):
				files.append("Recovery")
		return files

	def SearchUSBcanidate(self):
		for paths, subdirs, files in walk("/media"):
			for dir in subdirs:
				if not dir == 'hdd' and not dir == 'net':
					for file in listdir("/media/" + dir):
						if file.find("backupstick") > -1:
							print "USB-DEVICE found on: /media/%s" % dir
							return "/media/" + dir
			break
		return "XX"

	def doFullBackup(self, DIRECTORY):
		self.DIRECTORY = DIRECTORY
		self.TITLE = _("Full back-up on %s") % (self.DIRECTORY)
		self.START = time()
		self.DATE = strftime("%Y%m%d_%H%M", localtime(self.START))
		self.IMAGEVERSION = self.imageInfo() #strftime("%Y%m%d", localtime(self.START))
		if "ubi" in self.ROOTFSTYPE.split():
			self.MKFS = "/usr/sbin/mkfs.ubifs"
		elif "tar.bz2" in self.ROOTFSTYPE.split() or SystemInfo["HaveMultiBoot"] or self.MACHINEBUILD in ("gbmv200","u51","u52","u53","u54","u5","u5pvr","cc1","sf8008","ustym4kpro","v8plus","multibox","h9combo","hd60","hd61"):
			self.MKFS = "/bin/tar"
			self.BZIP2 = "/usr/bin/bzip2"
		else:
			self.MKFS = "/usr/sbin/mkfs.jffs2"

		self.UBINIZE = "/usr/sbin/ubinize"
		self.NANDDUMP = "/usr/sbin/nanddump"
		self.FASTBOOT = "/usr/bin/ext2simg"
		self.WORKDIR= "%s/bi" %self.DIRECTORY
		self.TARGET="XX"

		## TESTING IF ALL THE TOOLS FOR THE BUILDING PROCESS ARE PRESENT
		if not path.exists(self.MKFS):
			text = "%s not found !!" %self.MKFS
			self.session.open(MessageBox, _(text), type = MessageBox.TYPE_ERROR)
			return
		if not path.exists(self.NANDDUMP):
			text = "%s not found !!" %self.NANDDUMP
			self.session.open(MessageBox, _(text), type = MessageBox.TYPE_ERROR)
			return

		self.SHOWNAME = "%s %s" %(self.MACHINEBRAND, self.MODEL)
		self.MAINDESTOLD = "%s/%s" %(self.DIRECTORY, self.MODEL)
		self.MAINDEST = "%s/%s" %(self.DIRECTORY,self.IMAGEFOLDER)
		self.EXTRA = "%s/fullbackup_%s/%s/%s" % (self.DIRECTORY, self.MODEL, self.DATE, self.IMAGEFOLDER)
		self.EXTRAROOT = "%s/fullbackup_%s/%s" % (self.DIRECTORY, self.MODEL, self.DATE)
		self.EXTRAOLD = "%s/fullbackup_%s/%s/%s" % (self.DIRECTORY, self.MODEL, self.DATE, self.MODEL)


		self.message = "echo -e '\n"
		if getMachineBrand().startswith('A') or getMachineBrand().startswith('E') or getMachineBrand().startswith('I') or getMachineBrand().startswith('O') or getMachineBrand().startswith('U') or getMachineBrand().startswith('Xt'):
			self.message += (_('Back-up Tool for an %s\n') % self.SHOWNAME).upper()
		else:
			self.message += (_('Back-up Tool for a %s\n') % self.SHOWNAME).upper()
		self.message += VERSION + '\n'
		self.message += "_________________________________________________\n\n"
		self.message += _("Please be patient, a backup will now be made,\n")
		self.message += _("because of the used filesystem the back-up\n")
		if SystemInfo["HaveMultiBoot"] and self.list[self.selection] == "Recovery":
			self.message += _("will take about 30 minutes for this system\n")
		else:
			self.message += _("will take about 1-15 minutes for this system\n")
		self.message += "_________________________________________________\n"
		self.message += "'"

		## PREPARING THE BUILDING ENVIRONMENT
		system("rm -rf %s" %self.WORKDIR)
		if not path.exists(self.WORKDIR):
			makedirs(self.WORKDIR)
		if not path.exists("/tmp/bi/root"):
			makedirs("/tmp/bi/root")
		system("sync")
		if SystemInfo["HaveMultiBoot"]:
			system("mount /dev/%s /tmp/bi/root" %self.MTDROOTFS)
		else:
			system("mount --bind / /tmp/bi/root")

		if "jffs2" in self.ROOTFSTYPE.split():
			cmd1 = "%s --root=/tmp/bi/root --faketime --output=%s/root.jffs2 %s" % (self.MKFS, self.WORKDIR, self.MKUBIFS_ARGS)
			cmd2 = None
			cmd3 = None
		elif "tar.bz2" in self.ROOTFSTYPE.split() or SystemInfo["HaveMultiBoot"] or self.MACHINEBUILD in ("gbmv200","u51","u52","u53","u54","u5","u5pvr","cc1","sf8008","ustym4kpro","v8plus","multibox","h9combo","hd60","hd61"):
			cmd1 = "%s -cf %s/rootfs.tar -C /tmp/bi/root --exclude ./var/nmbd --exclude ./var/lib/samba/private/msg.sock ." % (self.MKFS, self.WORKDIR)
			cmd2 = "%s %s/rootfs.tar" % (self.BZIP2, self.WORKDIR)
			cmd3 = None
		else:
			f = open("%s/ubinize.cfg" %self.WORKDIR, "w")
			f.write("[ubifs]\n")
			f.write("mode=ubi\n")
			f.write("image=%s/root.ubi\n" %self.WORKDIR)
			f.write("vol_id=0\n")
			f.write("vol_type=dynamic\n")
			f.write("vol_name=rootfs\n")
			f.write("vol_flags=autoresize\n")
			f.close()
			ff = open("%s/root.ubi" %self.WORKDIR, "w")
			ff.close()
			cmd1 = "%s -r /tmp/bi/root -o %s/root.ubi %s" % (self.MKFS, self.WORKDIR, self.MKUBIFS_ARGS)
			cmd2 = "%s -o %s/root.ubifs %s %s/ubinize.cfg" % (self.UBINIZE, self.WORKDIR, self.UBINIZE_ARGS, self.WORKDIR)
			cmd3 = "mv %s/root.ubifs %s/root.%s" %(self.WORKDIR, self.WORKDIR, self.ROOTFSTYPE)

		cmdlist = []
		cmdlist.append(self.message)
		cmdlist.append('echo "' + _("Create:") + ' %s\n"' %self.ROOTFSBIN)
		cmdlist.append(cmd1)
		if cmd2:
			cmdlist.append(cmd2)
		if cmd3:
			cmdlist.append(cmd3)
		cmdlist.append("chmod 644 %s/%s" %(self.WORKDIR, self.ROOTFSBIN))

		if self.MODEL in ("gbquad4k","gbue4k"):
			cmdlist.append('echo " "')
			cmdlist.append('echo "' + _("Create:") + " boot dump" + '"')
			cmdlist.append("dd if=/dev/mmcblk0p1 of=%s/boot.bin" % self.WORKDIR)
			cmdlist.append('echo "' + _("Create:") + " rescue dump" + '"')
			cmdlist.append("dd if=/dev/mmcblk0p3 of=%s/rescue.bin" % self.WORKDIR)

		if self.MACHINEBUILD  in ("h9","i55plus"):
			cmdlist.append('echo " "')
			cmdlist.append('echo "' + _("Create:") + " fastboot dump" + '"')
			cmdlist.append("dd if=/dev/mtd0 of=%s/fastboot.bin" % self.WORKDIR)
			cmdlist.append('echo "' + _("Create:") + " bootargs dump" + '"')
			cmdlist.append("dd if=/dev/mtd1 of=%s/bootargs.bin" % self.WORKDIR)
			cmdlist.append('echo "' + _("Create:") + " baseparam dump" + '"')
			cmdlist.append("dd if=/dev/mtd2 of=%s/baseparam.bin" % self.WORKDIR)
			cmdlist.append('echo "' + _("Create:") + " pq_param dump" + '"')
			cmdlist.append("dd if=/dev/mtd3 of=%s/pq_param.bin" % self.WORKDIR)
			cmdlist.append('echo "' + _("Create:") + " logo dump" + '"')
			cmdlist.append("dd if=/dev/mtd4 of=%s/logo.bin" % self.WORKDIR)

		if self.MACHINEBUILD  in ("v8plus","multibox","h9combo","hd60","hd61"):
			cmdlist.append('echo " "')
			cmdlist.append('echo "' + _("Create:") + " fastboot dump" + '"')
			cmdlist.append("dd if=/dev/mmcblk0p1 of=%s/fastboot.bin" % self.WORKDIR)
			cmdlist.append('echo "' + _("Create:") + " bootargs dump" + '"')
			cmdlist.append("dd if=/dev/mmcblk0p2 of=%s/bootargs.bin" % self.WORKDIR)
			cmdlist.append('echo "' + _("Create:") + " bootoptions dump" + '"')
			cmdlist.append("dd if=/dev/mmcblk0p5 of=%s/bootoptions.bin" % self.WORKDIR)
			cmdlist.append('echo "' + _("Create:") + " baseparam dump" + '"')
			cmdlist.append("dd if=/dev/mmcblk0p6 of=%s/baseparam.bin" % self.WORKDIR)
			cmdlist.append('echo "' + _("Create:") + " pq_param dump" + '"')
			cmdlist.append("dd if=/dev/mmcblk0p7 of=%s/pq_param.bin" % self.WORKDIR)
			cmdlist.append('echo "' + _("Create:") + " logo dump" + '"')
			cmdlist.append("dd if=/dev/mmcblk0p8 of=%s/logo.bin" % self.WORKDIR)
			cmdlist.append('echo "' + _("Create:") + " rootfs dump" + '"')
			cmdlist.append("dd if=/dev/zero of=%s/rootfs.ext4 seek=1048576 count=0 bs=1024" % (self.WORKDIR))
			cmdlist.append("mkfs.ext4 -F -i 4096 %s/rootfs.ext4 -d /tmp/bi/root" % (self.WORKDIR))

		if self.MACHINEBUILD  in ("gbmv200","cc1","sf8008","ustym4kpro"):
			cmdlist.append('echo " "')
			cmdlist.append('echo "' + _("Create:") + " fastboot dump" + '"')
			cmdlist.append("dd if=/dev/mmcblk0p1 of=%s/fastboot.bin" % self.WORKDIR)
			cmdlist.append('echo "' + _("Create:") + " bootargs dump" + '"')
			cmdlist.append("dd if=/dev/mmcblk0p2 of=%s/bootargs.bin" % self.WORKDIR)
			cmdlist.append('echo "' + _("Create:") + " boot dump" + '"')
			cmdlist.append("dd if=/dev/mmcblk0p3 of=%s/boot.img" % self.WORKDIR)
			cmdlist.append('echo "' + _("Create:") + " baseparam dump" + '"')
			cmdlist.append("dd if=/dev/mmcblk0p4 of=%s/baseparam.img" % self.WORKDIR)
			cmdlist.append('echo "' + _("Create:") + " pq_param dump" + '"')
			cmdlist.append("dd if=/dev/mmcblk0p5 of=%s/pq_param.bin" % self.WORKDIR)
			cmdlist.append('echo "' + _("Create:") + " logo dump" + '"')
			cmdlist.append("dd if=/dev/mmcblk0p6 of=%s/logo.img" % self.WORKDIR)
			cmdlist.append('echo "' + _("Create:") + " deviceinfo dump" + '"')
			cmdlist.append("dd if=/dev/mmcblk0p7 of=%s/deviceinfo.bin" % self.WORKDIR)
			cmdlist.append('echo "' + _("Create:") + " apploader dump" + '"')
			cmdlist.append("dd if=/dev/mmcblk0p8 of=%s/apploader.bin" % self.WORKDIR)
			cmdlist.append('echo "' + _("Create:") + " rootfs dump" + '"')
			cmdlist.append("dd if=/dev/zero of=%s/rootfs.ext4 seek=524288 count=0 bs=1024" % (self.WORKDIR))
			cmdlist.append("mkfs.ext4 -F -i 4096 %s/rootfs.ext4 -d /tmp/bi/root" % (self.WORKDIR))

		cmdlist.append('echo " "')
		cmdlist.append('echo "' + _("Create:") + " kerneldump" + '"')
		cmdlist.append('echo " "')
		if SystemInfo["HaveMultiBoot"]:
			cmdlist.append("dd if=/dev/%s of=%s/kernel.bin" % (self.MTDKERNEL ,self.WORKDIR))
		elif self.MTDKERNEL.startswith('mmcblk0'):
			cmdlist.append("dd if=/dev/%s of=%s/%s" % (self.MTDKERNEL ,self.WORKDIR, self.KERNELBIN))
		else:
			cmdlist.append("nanddump -a -f %s/vmlinux.gz /dev/%s" % (self.WORKDIR, self.MTDKERNEL))
		cmdlist.append('echo " "')

		if HaveGZkernel:
			cmdlist.append('echo "' + _("Check:") + " kerneldump\n" + '"')
		cmdlist.append("sync")
		if ( SystemInfo["HaveMultiBootHD"] or SystemInfo["HaveMultiBootXC"] or SystemInfo["HaveMultiBootCY"] or SystemInfo["HaveMultiBootOS"]) and self.list[self.selection] == "Recovery":
			BLOCK_SIZE=512
			BLOCK_SECTOR=2
			IMAGE_ROOTFS_ALIGNMENT=1024
			BOOT_PARTITION_SIZE=3072
			KERNEL_PARTITION_OFFSET = int(IMAGE_ROOTFS_ALIGNMENT) + int(BOOT_PARTITION_SIZE)
			KERNEL_PARTITION_SIZE=8192
			ROOTFS_PARTITION_OFFSET = int(KERNEL_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
			ROOTFS_PARTITION_SIZE=819200
			SECOND_KERNEL_PARTITION_OFFSET = int(ROOTFS_PARTITION_OFFSET) + int(ROOTFS_PARTITION_SIZE)
			SECOND_ROOTFS_PARTITION_OFFSET = int(SECOND_KERNEL_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
			THRID_KERNEL_PARTITION_OFFSET = int(SECOND_ROOTFS_PARTITION_OFFSET) + int(ROOTFS_PARTITION_SIZE)
			THRID_ROOTFS_PARTITION_OFFSET = int(THRID_KERNEL_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
			FOURTH_KERNEL_PARTITION_OFFSET = int(THRID_ROOTFS_PARTITION_OFFSET) + int(ROOTFS_PARTITION_SIZE)
			FOURTH_ROOTFS_PARTITION_OFFSET = int(FOURTH_KERNEL_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
			SWAP_PARTITION_OFFSET = int(FOURTH_ROOTFS_PARTITION_OFFSET) + int(ROOTFS_PARTITION_SIZE)
			EMMC_IMAGE = "%s/%s"% (self.WORKDIR,self.EMMCIMG)
			EMMC_IMAGE_SIZE=3817472
			EMMC_IMAGE_SEEK = int(EMMC_IMAGE_SIZE) * int(BLOCK_SECTOR)
			cmdlist.append('echo " "')
			cmdlist.append('echo "' + _("Create: Recovery Fullbackup %s")% (self.EMMCIMG) + '"')
			cmdlist.append('echo " "')
			cmdlist.append('dd if=/dev/zero of=%s bs=%s count=0 seek=%s' % (EMMC_IMAGE, BLOCK_SIZE , EMMC_IMAGE_SEEK))
			cmdlist.append('parted -s %s mklabel gpt' %EMMC_IMAGE)
			PARTED_END_BOOT = int(IMAGE_ROOTFS_ALIGNMENT) + int(BOOT_PARTITION_SIZE)
			cmdlist.append('parted -s %s unit KiB mkpart boot fat16 %s %s' % (EMMC_IMAGE, IMAGE_ROOTFS_ALIGNMENT, PARTED_END_BOOT ))
			PARTED_END_KERNEL1 = int(KERNEL_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
			cmdlist.append('parted -s %s unit KiB mkpart kernel1 %s %s' % (EMMC_IMAGE, KERNEL_PARTITION_OFFSET, PARTED_END_KERNEL1 ))
			PARTED_END_ROOTFS1 = int(ROOTFS_PARTITION_OFFSET) + int(ROOTFS_PARTITION_SIZE)
			cmdlist.append('parted -s %s unit KiB mkpart rootfs1 ext4 %s %s' % (EMMC_IMAGE, ROOTFS_PARTITION_OFFSET, PARTED_END_ROOTFS1 ))
			PARTED_END_KERNEL2 = int(SECOND_KERNEL_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
			cmdlist.append('parted -s %s unit KiB mkpart kernel2 %s %s' % (EMMC_IMAGE, SECOND_KERNEL_PARTITION_OFFSET, PARTED_END_KERNEL2 ))
			PARTED_END_ROOTFS2 = int(SECOND_ROOTFS_PARTITION_OFFSET) + int(ROOTFS_PARTITION_SIZE)
			cmdlist.append('parted -s %s unit KiB mkpart rootfs2 ext4 %s %s' % (EMMC_IMAGE, SECOND_ROOTFS_PARTITION_OFFSET, PARTED_END_ROOTFS2 ))
			PARTED_END_KERNEL3 = int(THRID_KERNEL_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
			cmdlist.append('parted -s %s unit KiB mkpart kernel3 %s %s' % (EMMC_IMAGE, THRID_KERNEL_PARTITION_OFFSET, PARTED_END_KERNEL3 ))
			PARTED_END_ROOTFS3 = int(THRID_ROOTFS_PARTITION_OFFSET) + int(ROOTFS_PARTITION_SIZE)
			cmdlist.append('parted -s %s unit KiB mkpart rootfs3 ext4 %s %s' % (EMMC_IMAGE, THRID_ROOTFS_PARTITION_OFFSET, PARTED_END_ROOTFS3 ))
			PARTED_END_KERNEL4 = int(FOURTH_KERNEL_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
			cmdlist.append('parted -s %s unit KiB mkpart kernel4 %s %s' % (EMMC_IMAGE, FOURTH_KERNEL_PARTITION_OFFSET, PARTED_END_KERNEL4 ))
			PARTED_END_ROOTFS4 = int(FOURTH_ROOTFS_PARTITION_OFFSET) + int(ROOTFS_PARTITION_SIZE)
			cmdlist.append('parted -s %s unit KiB mkpart rootfs4 ext4 %s %s' % (EMMC_IMAGE, FOURTH_ROOTFS_PARTITION_OFFSET, PARTED_END_ROOTFS4 ))
			cmdlist.append('parted -s %s unit KiB mkpart swap linux-swap %s 100%%' % (EMMC_IMAGE, SWAP_PARTITION_OFFSET))
			BOOT_IMAGE_SEEK = int(IMAGE_ROOTFS_ALIGNMENT) * int(BLOCK_SECTOR)
			cmdlist.append('dd if=/dev/%s of=%s seek=%s' % (self.MTDBOOT, EMMC_IMAGE, BOOT_IMAGE_SEEK ))
			KERNAL_IMAGE_SEEK = int(KERNEL_PARTITION_OFFSET) * int(BLOCK_SECTOR)
			cmdlist.append('dd if=/dev/%s of=%s seek=%s' % (self.MTDKERNEL, EMMC_IMAGE, KERNAL_IMAGE_SEEK ))
			ROOTFS_IMAGE_SEEK = int(ROOTFS_PARTITION_OFFSET) * int(BLOCK_SECTOR)
			cmdlist.append('dd if=/dev/%s of=%s seek=%s ' % (self.MTDROOTFS, EMMC_IMAGE, ROOTFS_IMAGE_SEEK ))
		elif SystemInfo["HaveMultiBootDS"] and self.list[self.selection] == "Recovery":
			cmdlist.append('echo " "')
			cmdlist.append('echo "' + _("Create: Recovery Fullbackup %s")% (self.EMMCIMG) + '"')
			cmdlist.append('echo " "')
			f = open("%s/emmc_partitions.xml" %self.WORKDIR, "w")
			f.write('<?xml version="1.0" encoding="GB2312" ?>\n')
			f.write('<Partition_Info>\n')
			f.write('<Part Sel="1" PartitionName="fastboot" FlashType="emmc" FileSystem="none" Start="0" Length="1M" SelectFile="fastboot.bin"/>\n')
			f.write('<Part Sel="1" PartitionName="bootargs" FlashType="emmc" FileSystem="none" Start="1M" Length="1M" SelectFile="bootargs.bin"/>\n')
			f.write('<Part Sel="1" PartitionName="bootimg" FlashType="emmc" FileSystem="none" Start="2M" Length="1M" SelectFile="boot.img"/>\n')
			f.write('<Part Sel="1" PartitionName="baseparam" FlashType="emmc" FileSystem="none" Start="3M" Length="3M" SelectFile="baseparam.img"/>\n')
			f.write('<Part Sel="1" PartitionName="pqparam" FlashType="emmc" FileSystem="none" Start="6M" Length="4M" SelectFile="pq_param.bin"/>\n')
			f.write('<Part Sel="1" PartitionName="logo" FlashType="emmc" FileSystem="none" Start="10M" Length="4M" SelectFile="logo.img"/>\n')
			f.write('<Part Sel="1" PartitionName="deviceinfo" FlashType="emmc" FileSystem="none" Start="14M" Length="4M" SelectFile="deviceinfo.bin"/>\n')
			f.write('<Part Sel="1" PartitionName="loader" FlashType="emmc" FileSystem="none" Start="26M" Length="32M" SelectFile="apploader.bin"/>\n')
			f.write('<Part Sel="1" PartitionName="kernel" FlashType="emmc" FileSystem="none" Start="66M" Length="32M" SelectFile="kernel.bin"/>\n')
			f.write('<Part Sel="1" PartitionName="rootfs" FlashType="emmc" FileSystem="ext3/4" Start="98M" Length="7000M" SelectFile="rootfs.ext4"/>\n')
			f.write('</Partition_Info>\n')
			f.close()
			cmdlist.append('mkupdate -s 00000003-00000001-01010101 -f %s/emmc_partitions.xml -d %s/%s' % (self.WORKDIR,self.WORKDIR,self.EMMCIMG))
		elif self.MACHINEBUILD  in ("v8plus","multibox","h9combo","hd60","hd61"):
			cmdlist.append('echo " "')
			cmdlist.append('echo "' + _("Create: Recovery Fullbackup %s")% (self.EMMCIMG) + '"')
			cmdlist.append('echo " "')
			cmdlist.append('%s -zv %s/rootfs.ext4 %s/%s' % (self.FASTBOOT,self.WORKDIR,self.WORKDIR,self.EMMCIMG))
		self.session.open(Console, title = self.TITLE, cmdlist = cmdlist, finishedCallback = self.doFullBackupCB, closeOnSuccess = True)

	def doFullBackupCB(self):
		if HaveGZkernel:
			ret = commands.getoutput(' gzip -d %s/vmlinux.gz -c > /tmp/vmlinux.bin' % self.WORKDIR)
			if ret:
				text = _("Kernel dump error\n")
				text += _("Please Flash your Kernel new and Backup again")
				system('rm -rf /tmp/vmlinux.bin')
				self.session.open(MessageBox, _(text), type = MessageBox.TYPE_ERROR)
				return

		cmdlist = []
		cmdlist.append(self.message)
		if HaveGZkernel:
			cmdlist.append('echo "' + _("Kernel dump OK") + '"')
			cmdlist.append("rm -rf /tmp/vmlinux.bin")
			cmdlist.append('echo "_________________________________________________\n"')
		cmdlist.append('echo "' + _("Almost there... ") + '"')
		cmdlist.append('echo "' + _("Now building the USB-Image") + '"')

		system('rm -rf %s' %self.MAINDEST)
		if not path.exists(self.MAINDEST):
			makedirs(self.MAINDEST)
		if not path.exists(self.EXTRA):
			makedirs(self.EXTRA)

		f = open("%s/imageversion" %self.MAINDEST, "w")
		f.write(self.IMAGEVERSION)
		f.close()

		if self.ROOTFSBIN == "rootfs.tar.bz2":
			system('mv %s/rootfs.tar.bz2 %s/rootfs.tar.bz2' %(self.WORKDIR, self.MAINDEST))
		else:
			system('mv %s/root.%s %s/%s' %(self.WORKDIR, self.ROOTFSTYPE, self.MAINDEST, self.ROOTFSBIN))
		if SystemInfo["HaveMultiBoot"]:
			system('mv %s/kernel.bin %s/kernel.bin' %(self.WORKDIR, self.MAINDEST))
		elif self.MTDKERNEL.startswith('mmcblk0'):
			system('mv %s/%s %s/%s' %(self.WORKDIR, self.KERNELBIN, self.MAINDEST, self.KERNELBIN))
		else:
			system('mv %s/vmlinux.gz %s/%s' %(self.WORKDIR, self.MAINDEST, self.KERNELBIN))

		if SystemInfo["HaveMultiBoot"] and self.list[self.selection] == "Recovery" or self.MACHINEBUILD  in ("v8plus","multibox","h9combo","hd60","hd61"):
			system('mv %s/%s %s/%s' %(self.WORKDIR,self.EMMCIMG, self.MAINDEST,self.EMMCIMG))
		elif self.MODEL in ("vuultimo4k","vusolo4k", "vuduo2", "vusolo2", "vusolo", "vuduo", "vuultimo", "vuuno"):
			cmdlist.append('echo "This file forces a reboot after the update." > %s/reboot.update' %self.MAINDEST)
		elif self.MODEL in ("vuzero" , "vusolose", "vuuno4k", "vuzero4k"):
			cmdlist.append('echo "This file forces the update." > %s/force.update' %self.MAINDEST)
		elif self.MODEL in ('viperslim','evoslimse','evoslimt2c', "novaip" , "zgemmai55" , "sf98", "xpeedlxpro",'evoslim','vipert2c'):
			cmdlist.append('echo "This file forces the update." > %s/force' %self.MAINDEST)
		else:
			cmdlist.append('echo "rename this file to "force" to force an update without confirmation" > %s/noforce' %self.MAINDEST)

		if self.MODEL in ("gbquad4k","gbue4k"):
			system('mv %s/boot.bin %s/boot.bin' %(self.WORKDIR, self.MAINDEST))
			system('mv %s/rescue.bin %s/rescue.bin' %(self.WORKDIR, self.MAINDEST))
			system('cp -f /usr/share/gpt.bin %s/gpt.bin' %(self.MAINDEST))

		if self.MACHINEBUILD in ("h9","i55plus","h9combo","v8plus","multibox","hd60","hd61"):
			system('mv %s/fastboot.bin %s/fastboot.bin' %(self.WORKDIR, self.MAINDEST))
			system('mv %s/pq_param.bin %s/pq_param.bin' %(self.WORKDIR, self.MAINDEST))
			system('mv %s/bootargs.bin %s/bootargs.bin' %(self.WORKDIR, self.MAINDEST))
			system('mv %s/baseparam.bin %s/baseparam.bin' %(self.WORKDIR, self.MAINDEST))
			system('mv %s/logo.bin %s/logo.bin' %(self.WORKDIR, self.MAINDEST))

		if self.MACHINEBUILD in ("h9combo","v8plus","multibox","hd60","hd61"):
			system('mv %s/baseparam.bin %s/bootoptions.bin' %(self.WORKDIR, self.MAINDEST))

		if self.MODEL in ("gbquad", "gbquadplus", "gb800ue", "gb800ueplus", "gbultraue", "gbultraueh", "twinboxlcd", "twinboxlcdci", "singleboxlcd", "sf208", "sf228"):
			lcdwaitkey = '/usr/share/lcdwaitkey.bin'
			lcdwarning = '/usr/share/lcdwarning.bin'
			if path.exists(lcdwaitkey):
				system('cp %s %s/lcdwaitkey.bin' %(lcdwaitkey, self.MAINDEST))
			if path.exists(lcdwarning):
				system('cp %s %s/lcdwarning.bin' %(lcdwarning, self.MAINDEST))
		if self.MODEL in ("e4hdultra","protek4k"):
			lcdwarning = '/usr/share/lcdflashing.bmp'
			if path.exists(lcdwarning):
				system('cp %s %s/lcdflashing.bmp' %(lcdwarning, self.MAINDEST))
		if self.MODEL == "gb800solo":
			burnbat = "%s/fullbackup_%s/%s" % (self.DIRECTORY, self.MODEL, self.DATE)
			f = open("%s/burn.bat" % (burnbat), "w")
			f.write("flash -noheader usbdisk0:gigablue/solo/kernel.bin flash0.kernel\n")
			f.write("flash -noheader usbdisk0:gigablue/solo/rootfs.bin flash0.rootfs\n")
			f.write('setenv -p STARTUP "boot -z -elf flash0.kernel: ')
			f.write("'rootfstype=jffs2 bmem=106M@150M root=/dev/mtdblock6 rw '")
			f.write('"\n')
			f.close()

		cmdlist.append('cp -r %s/* %s/' % (self.MAINDEST, self.EXTRA))
		if self.MACHINEBUILD in ("h9","i55plus","hd60","hd61"):
			cmdlist.append('cp -f /usr/share/fastboot.bin %s/fastboot.bin' %(self.EXTRAROOT))
			cmdlist.append('cp -f /usr/share/bootargs.bin %s/bootargs.bin' %(self.EXTRAROOT))

		if self.MACHINEBUILD in ("multibox","v8plus","h9combo"):
			cmdlist.append('cp -f /usr/share/update_bootargs_%s.bin %s/update_bootargs_%s.bin' %(self.MACHINEBUILD,self.EXTRAROOT,self.MACHINEBUILD))

		cmdlist.append("sync")
		file_found = True

		if not path.exists("%s/%s" % (self.MAINDEST, self.ROOTFSBIN)):
			print 'ROOTFS bin file not found'
			file_found = False

		if not path.exists("%s/%s" % (self.MAINDEST, self.KERNELBIN)):
			print 'KERNEL bin file not found'
			file_found = False

		if path.exists("%s/noforce" % self.MAINDEST):
			print 'NOFORCE bin file not found'
			file_found = False

		if SystemInfo["HaveMultiBoot"] and not self.list[self.selection] == "Recovery":
			cmdlist.append('echo "_________________________________________________\n"')
			cmdlist.append('echo "' + _("Multiboot Image created on: %s") %self.MAINDEST + '"')
			cmdlist.append('echo "' + _("and there is made an extra copy on:") + '"')
			cmdlist.append('echo %s' %self.EXTRA)
			cmdlist.append('echo "_________________________________________________"')
			cmdlist.append('echo " "')
			cmdlist.append('echo "' + _("Please wait...almost ready! ") + '"')
			cmdlist.append('echo " "')
			cmdlist.append('echo "' + _("To restore the image:") + '"')
			cmdlist.append('echo "' + _("Use OnlineFlash in SoftwareManager") + '"')
		elif file_found:
			cmdlist.append('echo "_________________________________________________\n"')
			cmdlist.append('echo "' + _("USB Image created on: %s") %self.MAINDEST + '"')
			cmdlist.append('echo "' + _("and there is made an extra copy on:") + '"')
			cmdlist.append('echo %s' %self.EXTRA)
			cmdlist.append('echo "_________________________________________________"')
			cmdlist.append('echo " "')
			cmdlist.append('echo "' + _("Please wait...almost ready! ") + '"')
			cmdlist.append('echo " "')
			cmdlist.append('echo "' + _("To restore the image:") + '"')
			cmdlist.append('echo "' + _("Please check the manual of the receiver") + '"')
			cmdlist.append('echo "' + _("on how to restore the image") + '"')
		else:
			cmdlist.append('echo "_________________________________________________\n"')
			cmdlist.append('echo "' + _("Image creation failed - ") + '"')
			cmdlist.append('echo "' + _("Probable causes could be") + ':"')
			cmdlist.append('echo "' + _("     wrong back-up destination ") + '"')
			cmdlist.append('echo "' + _("     no space left on back-up device") + '"')
			cmdlist.append('echo "' + _("     no writing permission on back-up device") + '"')
			cmdlist.append('echo " "')

		if self.DIRECTORY == "/hdd":
			self.TARGET = self.SearchUSBcanidate()
			print "TARGET = %s" % self.TARGET
			if self.TARGET == 'XX':
				cmdlist.append('echo " "')
			else:
				cmdlist.append('echo "_________________________________________________\n"')
				cmdlist.append('echo " "')
				cmdlist.append('echo "' + _("There is a valid USB-flash drive detected in one ") + '"')
				cmdlist.append('echo "' + _("of the USB-ports, therefore an extra copy of the ") + '"')
				cmdlist.append('echo "' + _("back-up image will now be copied to that USB- ") + '"')
				cmdlist.append('echo "' + _("flash drive. ") + '"')
				cmdlist.append('echo "' + _("This only takes about 1 or 2 minutes") + '"')
				cmdlist.append('echo " "')

				cmdlist.append('mkdir -p %s/%s' % (self.TARGET, self.IMAGEFOLDER))
				cmdlist.append('cp -r %s %s/' % (self.MAINDEST, self.TARGET))
				if self.MACHINEBUILD in ("h9","i55plus","hd60","hd61"):
					cmdlist.append('cp -f /usr/share/fastboot.bin %s/fastboot.bin' %(self.TARGET))
					cmdlist.append('cp -f /usr/share/bootargs.bin %s/bootargs.bin' %(self.TARGET))
				if self.MACHINEBUILD in ("multibox","v8plus","h9combo"):
					cmdlist.append('cp -f /usr/share/update_bootargs_%s.bin %s/update_bootargs_%s.bin' %(self.MACHINEBUILD,self.TARGET,self.MACHINEBUILD))

				cmdlist.append("sync")
				cmdlist.append('echo "' + _("Backup finished and copied to your USB-flash drive") + '"')
			
		cmdlist.append("umount /tmp/bi/root")
		cmdlist.append("rmdir /tmp/bi/root")
		cmdlist.append("rmdir /tmp/bi")
		cmdlist.append("rm -rf %s" % self.WORKDIR)
		cmdlist.append("sleep 5")
		END = time()
		DIFF = int(END - self.START)
		TIMELAP = str(datetime.timedelta(seconds=DIFF))
		cmdlist.append('echo "' + _("Time required for this process: %s") %TIMELAP + '\n"')

		self.session.open(Console, title = self.TITLE, cmdlist = cmdlist, closeOnSuccess = False)

	def imageInfo(self):
		AboutText = _("Full Image Backup ")
		AboutText += _("By openATV Image Team") + "\n"
		AboutText += _("Support at") + " www.opena.tv\n\n"
		AboutText += _("[Image Info]\n")
		AboutText += _("Model: %s %s\n") % (getMachineBrand(), getMachineName())
		AboutText += _("Backup Date: %s\n") % strftime("%Y-%m-%d", localtime(self.START))

		if path.exists('/proc/stb/info/chipset'):
			AboutText += _("Chipset: BCM%s") % about.getChipSetString().lower().replace('\n','').replace('bcm','') + "\n"

		AboutText += _("CPU: %s") % about.getCPUString() + "\n"
		AboutText += _("Cores: %s") % about.getCpuCoresString() + "\n"

		AboutText += _("Version: %s") % getImageVersion() + "\n"
		AboutText += _("Build: %s") % getImageBuild() + "\n"
		AboutText += _("Kernel: %s") % about.getKernelVersionString() + "\n"

		string = getDriverDate()
		year = string[0:4]
		month = string[4:6]
		day = string[6:8]
		driversdate = '-'.join((year, month, day))
		AboutText += _("Drivers:\t%s") % driversdate + "\n"

		AboutText += _("Last update:\t%s") % getEnigmaVersionString() + "\n\n"

		AboutText += _("[Enigma2 Settings]\n")
		AboutText += commands.getoutput("cat /etc/enigma2/settings")
		AboutText += _("\n\n[User - bouquets (TV)]\n")
		try:
			f = open("/etc/enigma2/bouquets.tv","r")
			lines = f.readlines()
			f.close()
			for line in lines:
				if line.startswith("#SERVICE:"):
					bouqet = line.split()
					if len(bouqet) > 3:
						bouqet[3] = bouqet[3].replace('"','')
						f = open("/etc/enigma2/" + bouqet[3],"r")
						userbouqet = f.readline()
						AboutText += userbouqet.replace('#NAME ','')
						f.close()
		except:
			AboutText += _("Error reading bouquets.tv")
			
		AboutText += _("\n[User - bouquets (RADIO)]\n")
		try:
			f = open("/etc/enigma2/bouquets.radio","r")
			lines = f.readlines()
			f.close()
			for line in lines:
				if line.startswith("#SERVICE:"):
					bouqet = line.split()
					if len(bouqet) > 3:
						bouqet[3] = bouqet[3].replace('"','')
						f = open("/etc/enigma2/" + bouqet[3],"r")
						userbouqet = f.readline()
						AboutText += userbouqet.replace('#NAME ','')
						f.close()
		except:
			AboutText += _("Error reading bouquets.radio")

		AboutText += _("\n[Installed Plugins]\n")
		AboutText += commands.getoutput("opkg list_installed | grep enigma2-plugin-")

		return AboutText

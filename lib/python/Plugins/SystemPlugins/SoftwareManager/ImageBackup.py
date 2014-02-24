#################################################################################
# FULL BACKUP UYILITY FOR ENIGMA2, SUPPORTS THE MODELS ET-XX00 & VU+			#
#							& Gigablue & Venton HD Models						#
#					MAKES A FULLBACK-UP READY FOR FLASHING.						#
#																				#
#################################################################################
from enigma import getEnigmaVersionString
from Screens.Screen import Screen
from Components.Button import Button
from Components.Label import Label
from Components.ActionMap import ActionMap
from Components.About import about
from Screens.Console import Console
from Screens.MessageBox import MessageBox
from time import time, strftime, localtime
from os import path, system, makedirs, listdir, walk, statvfs
import commands
import datetime
from boxbranding import getBoxType, getMachineBrand, getMachineName, getDriverDate, getImageVersion, getImageBuild, getBrandOEM

VERSION = "Version 2.0 openATV"

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
		<widget name="key_red" position="0,360" zPosition="2" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
		<widget name="key_green" position="140,360" zPosition="2" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
		<widget name="key_yellow" position="280,360" zPosition="2" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
		<widget name="key_blue" position="420,360" zPosition="2" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
		<widget name="info-hdd" position="10,30" zPosition="1" size="450,100" font="Regular;20" halign="left" valign="top" transparent="1" />
		<widget name="info-usb" position="10,150" zPosition="1" size="450,200" font="Regular;20" halign="left" valign="top" transparent="1" />
	</screen>"""
		
	def __init__(self, session, args = 0):
		Screen.__init__(self, session)
		self.session = session
		self.MODEL = getBoxType()
		self.OEM = getBrandOEM()
		self.MACHINENAME = getMachineName()
		self.MACHINEBRAND = getMachineBrand()
		print "[FULL BACKUP] BOX MACHINENAME = >%s<" %self.MACHINENAME
		print "[FULL BACKUP] BOX MACHINEBRAND = >%s<" %self.MACHINEBRAND
		print "[FULL BACKUP] BOX MODEL = >%s<" %self.MODEL
		print "[FULL BACKUP] OEM MODEL = >%s<" %self.OEM
		
		self["key_green"] = Button("USB")
		self["key_red"] = Button("HDD")
		self["key_blue"] = Button(_("Exit"))
		self["key_yellow"] = Button("")
		self["info-usb"] = Label(_("USB = Do you want to make a back-up on USB?\nThis will take between 4 and 15 minutes depending on the used filesystem and is fully automatic.\nMake sure you first insert an USB flash drive before you select USB."))
		self["info-hdd"] = Label(_("HDD = Do you want to make an USB-back-up image on HDD? \nThis only takes 2 or 10 minutes and is fully automatic."))
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], 
		{
			"blue": self.quit,
			"yellow": self.yellow,
			"green": self.green,
			"red": self.red,
			"cancel": self.quit,
		}, -2)

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
		#// Not used
		pass	

	def testUBIFS(self):
		f = open("/proc/mounts", "r")
		mounts = f.readlines()
		f.close()
		for line in mounts:
			if "rootfs" in line and "ubifs" in line:
				return "ubifs"
		return "jffs2"

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
		self.ROOTFSTYPE = self.testUBIFS()
		self.MKFS = "/usr/sbin/mkfs.%s" %self.ROOTFSTYPE
		self.UBINIZE = "/usr/sbin/ubinize"
		self.NANDDUMP = "/usr/sbin/nanddump"
		self.WORKDIR= "%s/bi" %self.DIRECTORY
		self.TARGET="XX"
		self.MTDKERNEL="mtd1"
		self.ROOTFSBIN="rootfs.bin"
		self.KERNELBIN="kernel.bin"

		## TESTING IF ALL THE TOOLS FOR THE BUILDING PROCESS ARE PRESENT
		if not path.exists(self.MKFS):
			text = "%s not found !!" %self.MKFS
			self.session.open(MessageBox, _(text), type = MessageBox.TYPE_ERROR)
			return
		if not path.exists(self.NANDDUMP):
			text = "%s not found !!" %self.NANDDUMP
			self.session.open(MessageBox, _(text), type = MessageBox.TYPE_ERROR)
			return

		## TESTING WHICH KIND OF SATELLITE RECEIVER IS USED

		## TESTING THE XTREND AND CLARK TECH MODELS
		if self.MODEL.startswith("et") and not self.MODEL == "et10000":
			self.TYPE = "ET"
			self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 4096"
			self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			self.SHOWNAME = "%s %s" %(self.MACHINEBRAND, self.MODEL)
			self.MAINDESTOLD = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/%sx00" %(self.DIRECTORY, self.MODEL[:-3])
			self.EXTRA = "%s/fullbackup_%sx00/%s" % (self.DIRECTORY, self.MODEL[:-3], self.DATE)
			self.EXTRAOLD = "%s/fullbackup_%s/%s/%s" % (self.DIRECTORY, self.MODEL, self.DATE, self.MODEL)
		elif self.MODEL == "et10000":
			self.TYPE = "ET"
			self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 8192"
			self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			self.SHOWNAME = "%s %s" %(self.MACHINEBRAND, self.MODEL)
			self.MAINDESTOLD = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.EXTRA = "%s/fullbackup_%s/%s" % (self.DIRECTORY, self.MODEL, self.DATE)
			self.EXTRAOLD = "%s/fullbackup_%s/%s/%s" % (self.DIRECTORY, self.MODEL, self.DATE, self.MODEL)
		## TESTING THE Odin M9 Model 'maram9'
		elif self.MODEL == "odinm9":
			self.TYPE = "ODINM9"
			self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 4096"
			self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			self.SHOWNAME = "%s %s" %(self.MACHINEBRAND, self.MODEL)
			self.MTDKERNEL = "mtd2"	
			self.MAINDESTOLD = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/odinm9" % self.DIRECTORY
			self.EXTRAOLD = "%s/fullbackup_%s/%s/%s" % (self.DIRECTORY, self.MODEL, self.DATE, self.MODEL)
			self.EXTRA = "%s/fullbackup_odinm9/%s" % (self.DIRECTORY, self.DATE)
		elif self.MODEL == "maram9":
			self.TYPE = "MARAM9"
			self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 4096"
			self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			self.SHOWNAME = "%s %s" %(self.MACHINEBRAND, self.MODEL)
			self.MTDKERNEL = "mtd2"	
			self.MAINDESTOLD = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/maram9" % self.DIRECTORY
			self.EXTRAOLD = "%s/fullbackup_%s/%s/%s" % (self.DIRECTORY, self.MODEL, self.DATE, self.MODEL)
			self.EXTRA = "%s/fullbackup_maram9/%s" % (self.DIRECTORY, self.DATE)
		## TESTING THE Odin M7 Model
		elif self.OEM == "odinm7" or self.MODEL == "odinm7":
			self.TYPE = "ODINM7"
			self.MODEL = self.OEM
			self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 4096"
			self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			self.SHOWNAME = "%s %s" %(self.MACHINEBRAND, self.MODEL)
			self.MTDKERNEL = "mtd3"	
			self.MAINDESTOLD = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/en2" % self.DIRECTORY
			self.EXTRAOLD = "%s/fullbackup_%s/%s/%s" % (self.DIRECTORY, self.MODEL, self.DATE, self.MODEL)
			self.EXTRA = "%s/fullbackup_odinm7/%s" % (self.DIRECTORY, self.DATE)
		elif self.OEM == "odin" and self.MODEL == "axodin":
			self.TYPE = "ODINM7"
			self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 4096"
			self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			self.SHOWNAME = "%s %s" %(self.MACHINEBRAND, self.MODEL)
			self.MTDKERNEL = "mtd3"	
			self.MAINDESTOLD = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/en2" % self.DIRECTORY
			self.EXTRAOLD = "%s/fullbackup_%s/%s/%s" % (self.DIRECTORY, self.MODEL, self.DATE, self.MODEL)
			self.EXTRA = "%s/fullbackup_odinm7/%s" % (self.DIRECTORY, self.DATE)
		## TESTING THE E3 HD Model
		elif self.OEM == "e3hd":
			self.TYPE = "E3HD"
			self.MODEL = self.OEM
			self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 4096"
			self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			self.SHOWNAME = "%s %s" %(self.MACHINEBRAND, self.MODEL)
			self.MTDKERNEL = "mtd1"	
			self.MAINDESTOLD = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/e3hd" % self.DIRECTORY
			self.EXTRAOLD = "%s/fullbackup_%s/%s/%s" % (self.DIRECTORY, self.MODEL, self.DATE, self.MODEL)
			self.EXTRA = "%s/fullbackup_e3hd/%s" % (self.DIRECTORY, self.DATE)
		## TESTING THE ENFINITY Model
		elif self.MODEL == "enfinity":
			self.TYPE = "EVO"
			self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 4096"
			self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			self.SHOWNAME = "%s %s" %(self.MACHINEBRAND, self.MODEL)
			self.MTDKERNEL = "mtd1"	
			self.MAINDESTOLD = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/enfinity" % self.DIRECTORY
			self.EXTRAOLD = "%s/fullbackup_%s/%s/%s" % (self.DIRECTORY, self.MODEL, self.DATE, self.MODEL)
			self.EXTRA = "%s/fullbackup_enfinity/%s" % (self.DIRECTORY, self.DATE)
		## TESTING THE MK Digital Model
		elif self.OEM == "xp1000":
			self.TYPE = "MAXDIGITAL"
			self.MODEL = self.OEM
			self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 4096"
			self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			self.SHOWNAME = "%s %s" %(self.MACHINEBRAND, self.MODEL)
			self.MTDKERNEL = "mtd1"	
			self.MAINDESTOLD = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.EXTRA = "%s/fullbackup_%s/%s" % (self.DIRECTORY, self.TYPE, self.DATE)
		elif self.OEM == "xp" and self.MODEL == "xp1000mk":
			self.TYPE = "MAXDIGITAL"
			self.MODEL == "xp1000"
			self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 4096"
			self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			self.SHOWNAME = "%s %s" %(self.MACHINEBRAND, self.MODEL)
			self.MTDKERNEL = "mtd1"	
			self.MAINDESTOLD = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.EXTRA = "%s/fullbackup_%s/%s" % (self.DIRECTORY, self.TYPE, self.DATE)
		## TESTING THE Medialink Model
		elif self.MODEL == "ixussone" or self.MODEL == "ixusszero":
			self.TYPE = "IXUSS"
			self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 4096"
			self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			self.SHOWNAME = "%s %s" %(self.MACHINEBRAND, self.MODEL)
			self.MTDKERNEL = "mtd1"	
			self.MAINDESTOLD = "%s/medialink/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/medialink/%s" %(self.DIRECTORY, self.MODEL)
			self.EXTRA = "%s/fullbackup_%s/%s" % (self.DIRECTORY, self.TYPE, self.DATE)
		elif self.MODEL == "Ixuss Zero":
			self.TYPE = "IXUSS"
			self.MODEL = "ixusszero"
			self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 4096"
			self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			self.SHOWNAME = "%s %s" %(self.MACHINEBRAND, self.MODEL)
			self.MTDKERNEL = "mtd1"	
			self.MAINDESTOLD = "%s/medialink/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/medialink/%s" %(self.DIRECTORY, self.MODEL)
			self.EXTRA = "%s/fullbackup_%s/%s" % (self.DIRECTORY, self.TYPE, self.DATE)
		elif self.MODEL == "Ixuss One":
			self.TYPE = "IXUSS"
			self.MODEL = "ixussone"
			self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 4096"
			self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			self.SHOWNAME = "%s %s" %(self.MACHINEBRAND, self.MODEL)
			self.MTDKERNEL = "mtd1"	
			self.MAINDESTOLD = "%s/medialink/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/medialink/%s" %(self.DIRECTORY, self.MODEL)
			self.EXTRA = "%s/fullbackup_%s/%s" % (self.DIRECTORY, self.TYPE, self.DATE)
		## TESTING THE Mixos Model
		elif self.OEM == "ebox5000" or self.OEM == "ebox5100" or self.OEM == "eboxlumi":
			self.TYPE = "MIXOS"
			self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 1024 -F"
			self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			self.SHOWNAME = "%s %s" %(self.MACHINEBRAND, self.MODEL)
			self.MTDKERNEL = "mtd1"	
			self.MAINDESTOLD = "%s/ebox/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/ebox/7403/" % self.DIRECTORY
			self.EXTRA = "%s/fullbackup_%s/%s/ebox" % (self.DIRECTORY, self.TYPE, self.DATE)
		## TESTING THE Mixos Model
		elif self.OEM == "ebox7358":
			self.TYPE = "MIXOS"
			self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 1024 -F"
			self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			self.SHOWNAME = "%s %s" %(self.MACHINEBRAND, self.MODEL)
			self.MTDKERNEL = "mtd7"	
			self.MAINDESTOLD = "%s/ebox/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/ebox/7358/" % self.DIRECTORY
			self.EXTRA = "%s/fullbackup_%s/%s/ebox" % (self.DIRECTORY, self.TYPE, self.DATE)
		## TESTING Venton HDx Model
		elif self.MODEL == "ini-3000" or self.MODEL == "ini-5000" or self.MODEL == "ini-7000" or self.MODEL == "ini-7012" or self.MACHINEBRAND == "UNiBOX":
			self.TYPE = "VENTON"
			self.MODEL = "venton-hdx"
			self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 4096"
			self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			self.SHOWNAME = "%s" %self.MODEL
			self.MAINDESTOLD = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/%s" % (self.DIRECTORY, self.MODEL)
			self.EXTRA = "%s/fullbackup_%s/%s" % (self.DIRECTORY, self.MODEL, self.DATE)
		elif self.MODEL == "ini-5000ru":
			self.TYPE = "SEZAM"
			self.MODEL = "hdx"			
			self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 4096"
			self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			self.SHOWNAME = "SEZAM 5000HD"
			self.MAINDESTOLD = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/%s" % (self.DIRECTORY, self.MODEL)
			self.EXTRA = "%s/fullbackup_%s/%s" % (self.DIRECTORY, self.MODEL, self.DATE)
		elif self.MODEL == "ini-5000sv":
			self.TYPE = "MICRACLE"
			self.MODEL = "twin"			
			self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 4096"
			self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			self.SHOWNAME = "MICRACLE Primium Twin"
			self.MAINDESTOLD = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/miraclebox/%s" % (self.DIRECTORY, self.MODEL)
			self.EXTRA = "%s/fullbackup_%s/%s/miraclebox" % (self.DIRECTORY, self.MODEL, self.DATE)			
		## TESTING INI HDe Model
		elif self.MODEL == "ini-1000de" or self.MODEL == "xpeedlx2" or self.MODEL == "xpeedlx1":
			self.TYPE = "GI"
			self.MODEL = "xpeedlx"
			self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 4096"
			self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			self.SHOWNAME = "GI XpeedLX"
			self.MTDKERNEL = "mtd2"
			self.MAINDESTOLD = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/%s" % (self.DIRECTORY, self.MODEL)
			self.EXTRA = "%s/fullbackup_%s/%s" % (self.DIRECTORY, self.MODEL, self.DATE)
		elif self.MODEL == "ini-9000de":
			self.TYPE = "GI"
			self.MODEL = "xpeedlx3"
			self.MKUBIFS_ARGS = "-m 4096 -e 1040384 -c 1984"
			self.UBINIZE_ARGS = "-m 4096 -p 1024KiB"
			self.SHOWNAME = "GI XpeedLX3"
			self.MTDKERNEL = "mtd2"
			self.MAINDESTOLD = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/%s" % (self.DIRECTORY, self.MODEL)
			self.EXTRA = "%s/fullbackup_%s/%s" % (self.DIRECTORY, self.MODEL, self.DATE)			
		elif self.MODEL == "ini-1000ru":
			self.TYPE = "SEZAM"
			self.MODEL = "hde"
			self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 4096"
			self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			self.SHOWNAME = "SEZAM 1000HD"
			self.MTDKERNEL = "mtd2"
			self.MAINDESTOLD = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/%s" % (self.DIRECTORY, self.MODEL)
			self.EXTRA = "%s/fullbackup_%s/%s" % (self.DIRECTORY, self.MODEL, self.DATE)
		elif self.MODEL == "ini-9000ru":
			self.TYPE = "SEZAM"
			self.MODEL = "hdp"
			self.MKUBIFS_ARGS = "-m 4096 -e 1040384 -c 1984"
			self.UBINIZE_ARGS = "-m 4096 -p 1024KiB"
			self.SHOWNAME = "SEZAM Marvel"
			self.MTDKERNEL = "mtd2"
			self.MAINDESTOLD = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/%s" % (self.DIRECTORY, self.MODEL)
			self.EXTRA = "%s/fullbackup_%s/%s" % (self.DIRECTORY, self.MODEL, self.DATE)		
		elif self.MODEL == "ini-1000sv":
			self.TYPE = "MICRACLE"
			self.MODEL = "mini"
			self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 4096"
			self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			self.SHOWNAME = "MICRACLE Primium mini"
			self.MTDKERNEL = "mtd2"
			self.MAINDESTOLD = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/miraclebox/%s" % (self.DIRECTORY, self.MODEL)
			self.EXTRA = "%s/fullbackup_%s/%s/miraclebox" % (self.DIRECTORY, self.MODEL, self.DATE)			
		## TESTING Technomate Model
		elif self.MACHINENAME == "TM-TWIN-OE":
			self.TYPE = "TECHNO"
			self.MODEL = "tmtwinoe"
			self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 4096 -F"
			self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			self.SHOWNAME = "%s" %self.MODEL
			self.MTDKERNEL = "mtd6"
			self.MAINDESTOLD = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/update/%s/cfe" % (self.DIRECTORY, self.MODEL)
			self.EXTRA = "%s/fullbackup_TECHNO/%s/update/%s" % (self.DIRECTORY, self.DATE, self.MODEL)
		## TESTING Technomate Model
		elif self.MACHINENAME == "TM-SINGLE":
			self.TYPE = "TECHNO"
			self.MODEL = "tmsingle"
			self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 4096 -F"
			self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			self.SHOWNAME = "%s" %self.MODEL
			self.MTDKERNEL = "mtd6"
			self.MAINDESTOLD = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/update/%s/cfe" % (self.DIRECTORY, self.MODEL)
			self.EXTRA = "%s/fullbackup_TECHNO/%s/update/%s" % (self.DIRECTORY, self.DATE, self.MODEL)
		## TESTING Technomate Model
		elif self.MACHINENAME == "TM-NANO-OE":
			self.TYPE = "TECHNO"
			self.MODEL = "tmnanooe"
			self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 4096 -F"
			self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			self.SHOWNAME = "%s" %self.MODEL
			self.MTDKERNEL = "mtd6"
			self.MAINDESTOLD = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/update/%s/cfe" % (self.DIRECTORY, self.MODEL)
			self.EXTRA = "%s/fullbackup_TECHNO/%s/update/%s" % (self.DIRECTORY, self.DATE, self.MODEL)
		## TESTING Technomate Model
		elif self.MACHINENAME == "TM-2T-OE":
			self.TYPE = "TECHNO"
			self.MODEL = "tm2toe"
			self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 4096 -F"
			self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			self.SHOWNAME = "%s" %self.MODEL
			self.MTDKERNEL = "mtd6"
			self.MAINDESTOLD = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/update/%s/cfe" % (self.DIRECTORY, self.MODEL)
			self.EXTRA = "%s/fullbackup_TECHNO/%s/update/%s" % (self.DIRECTORY, self.DATE, self.MODEL)
		elif self.MACHINENAME == "TM-NANO-2T-OE":
			self.TYPE = "TECHNO"
			self.MODEL = "tmnano2t"
			self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 4096 -F"
			self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			self.SHOWNAME = "%s" %self.MODEL
			self.MTDKERNEL = "mtd6"
			self.MAINDESTOLD = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/update/%s/cfe" % (self.DIRECTORY, self.MODEL)
			self.EXTRA = "%s/fullbackup_TECHNO/%s/update/%s" % (self.DIRECTORY, self.DATE, self.MODEL)
		## TESTING Iqon Model
		elif self.MACHINENAME == "IOS-100HD" or self.MACHINENAME == "Optimuss-OS1":
			self.TYPE = "IQON"
			self.MODEL = "ios100"
			self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 4096 -F"
			self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			self.SHOWNAME = "%s" %self.MODEL
			self.MTDKERNEL = "mtd6"
			self.MAINDESTOLD = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/update/%s/cfe" % (self.DIRECTORY, self.MODEL)
			self.EXTRA = "%s/fullbackup_IQON/%s/update/%s" % (self.DIRECTORY, self.DATE, self.MODEL)
		## TESTING Iqon Model
		elif self.MACHINENAME == "IOS-200HD" or self.MACHINENAME == "Optimuss-OS2" or self.MACHINENAME == "Roxxs-200HD" or self.MACHINENAME == "MediaBox-HD-LX":
			self.TYPE = "IQON"
			self.MODEL = "ios200"
			self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 4096 -F"
			self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			self.SHOWNAME = "%s %s" %(self.MACHINEBRAND, self.MODEL)
			self.MTDKERNEL = "mtd6"
			self.MAINDESTOLD = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/update/%s/cfe" % (self.DIRECTORY, self.MODEL)
			self.EXTRA = "%s/fullbackup_%s/%s/update/%s" % (self.DIRECTORY,self.MACHINEBRAND , self.DATE, self.MODEL)
		## TESTING Iqon Model
		elif self.MACHINENAME == "IOS-300HD":
			self.TYPE = "IQON"
			self.MODEL = "ios300"
			self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 4096 -F"
			self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			self.SHOWNAME = "%s %s" %(self.MACHINEBRAND, self.MODEL)
			self.MTDKERNEL = "mtd6"
			self.MAINDESTOLD = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/update/%s/cfe" % (self.DIRECTORY, self.MODEL)
			self.EXTRA = "%s/fullbackup_%s/%s/update/%s" % (self.DIRECTORY,self.MACHINEBRAND, self.DATE, self.MODEL)
		## TESTING Iqon Model
		elif self.MACHINENAME == "force1":
			self.TYPE = "IQON"
			self.MODEL = "force1"
			self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 4096 -F"
			self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			self.SHOWNAME = "%s %s" %(self.MACHINEBRAND, self.MODEL)
			self.MTDKERNEL = "mtd6"
			self.MAINDESTOLD = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/update/%s/cfe" % (self.DIRECTORY, self.MODEL)
			self.EXTRA = "%s/fullbackup_%s/%s/update/%s" % (self.DIRECTORY,self.MACHINEBRAND, self.DATE, self.MODEL)			
		## TESTING THE Gigablue 800 Solo Model
		elif self.MODEL == "gb800solo":
			self.TYPE = "GIGABLUE"
			self.MODEL = "solo"
			self.JFFS2OPTIONS="--eraseblock=0x20000 -n -l --pad=125829120"
			self.SHOWNAME = "GigaBlue %s" %self.MODEL
			self.MTDKERNEL = "mtd2"	
			self.MAINDESTOLD = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/gigablue/%s" %(self.DIRECTORY, self.MODEL)
			self.EXTRA =  "%s/fullbackup_%s/%s/gigablue" % (self.DIRECTORY, self.TYPE, self.DATE)
		## TESTING THE Gigablue 800 SE Model
		elif self.MODEL == "gb800se":
			self.TYPE = "GIGABLUE"
			self.MODEL = "se"
			self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 4096"
			self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			self.SHOWNAME = "GigaBlue %s" %self.MODEL
			self.MTDKERNEL = "mtd2"	
			self.MAINDESTOLD = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/gigablue/%s" %(self.DIRECTORY, self.MODEL)
			self.EXTRA =  "%s/fullbackup_%s/%s/gigablue" % (self.DIRECTORY, self.TYPE, self.DATE)
		## TESTING THE Gigablue 800 UE Model
		elif self.MODEL == "gb800ue":
			self.TYPE = "GIGABLUE"
			self.MODEL = "ue"
			self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 4096"
			self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			self.SHOWNAME = "GigaBlue %s" %self.MODEL
			self.MTDKERNEL = "mtd2"	
			self.MAINDESTOLD = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/gigablue/%s" %(self.DIRECTORY, self.MODEL)
			self.EXTRA =  "%s/fullbackup_%s/%s/gigablue" % (self.DIRECTORY, self.TYPE, self.DATE)
		## TESTING THE Gigablue 800 SE Plus Model
		elif self.MODEL == "gb800seplus":
			self.TYPE = "GIGABLUE"
			self.MODEL = "seplus"
			self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 4096"
			self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			self.SHOWNAME = "GigaBlue %s" %self.MODEL
			self.MTDKERNEL = "mtd2"	
			self.MAINDESTOLD = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/gigablue/%s" %(self.DIRECTORY, self.MODEL)
			self.EXTRA =  "%s/fullbackup_%s/%s/gigablue" % (self.DIRECTORY, self.TYPE, self.DATE)
		## TESTING THE Gigablue 800 UE Plus Model
		elif self.MODEL == "gb800ueplus":
			self.TYPE = "GIGABLUE"
			self.MODEL = "ueplus"
			self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 4096"
			self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			self.SHOWNAME = "GigaBlue %s" %self.MODEL
			self.MTDKERNEL = "mtd2"	
			self.MAINDESTOLD = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/gigablue/%s" %(self.DIRECTORY, self.MODEL)
			self.EXTRA =  "%s/fullbackup_%s/%s/gigablue" % (self.DIRECTORY, self.TYPE, self.DATE)
		## TESTING THE Gigablue HD Quad Model
		elif self.MODEL == "gbquad":
			self.TYPE = "GIGABLUE"
			self.MODEL = "quad"
			self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 4000"
			self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			self.SHOWNAME = "GigaBlue %s" %self.MODEL
			self.MTDKERNEL = "mtd2"	
			self.MAINDESTOLD = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/gigablue/%s" %(self.DIRECTORY, self.MODEL)
			self.EXTRA =  "%s/fullbackup_%s/%s/gigablue" % (self.DIRECTORY, self.TYPE, self.DATE)
		## TESTING THE Gigablue HD Quad Plus Model
		elif self.MODEL == "gbquadplus":
			self.TYPE = "GIGABLUE"
			self.MODEL = "quadplus"
			self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 4000"
			self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			self.SHOWNAME = "GigaBlue %s" %self.MODEL
			self.MTDKERNEL = "mtd2"	
			self.MAINDESTOLD = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/gigablue/%s" %(self.DIRECTORY, self.MODEL)
			self.EXTRA =  "%s/fullbackup_%s/%s/gigablue" % (self.DIRECTORY, self.TYPE, self.DATE)			
		## TESTING THE VU+ MODELS
		elif self.MODEL == "vusolo" or self.MODEL == "vuduo" or self.MODEL == "vuuno" or self.MODEL == "vuultimo" or self.MODEL == "vusolo2" or self.MODEL == "vuduo2":
			self.TYPE = "VU"
			if self.MODEL == "vusolo2" or self.MODEL == "vuduo2":
				self.MTDKERNEL = "mtd2"
			self.SHOWNAME = "VU+ %s" %self.MODEL[2:]
			self.MAINDEST = "%s/vuplus/%s" %(self.DIRECTORY, self.MODEL[2:])
			self.EXTRA =  "%s/fullbackup_%s/%s/vuplus" % (self.DIRECTORY, self.MODEL[2:], self.DATE)
			if self.ROOTFSTYPE == "ubifs":
				self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 4096 -F"
				self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			else:
				self.MTDROOT = 0
				self.MTDBOOT = 2
				self.JFFS2OPTIONS = "--eraseblock=0x20000 -n -l"
		## TESTING THE SOGNO8800HD MODEL		
		elif self.MODEL == "sogno8800hd":
			self.TYPE = "SOGNO"
			self.MODEL = "8800hd"
			self.MKUBIFS_ARGS = "-m 2048 -e 126976 -c 4096 -F"
			self.UBINIZE_ARGS = "-m 2048 -p 128KiB"
			self.SHOWNAME = "Sogno %s" %self.MODEL
			self.MTDKERNEL = "mtd8"	
			self.MAINDESTOLD = "%s/%s" %(self.DIRECTORY, self.MODEL)
			self.MAINDEST = "%s/sogno/%s" %(self.DIRECTORY, self.MODEL)
			self.EXTRA =  "%s/fullbackup_%s/%s/sogno" % (self.DIRECTORY, self.TYPE, self.DATE)
		else:
			print "No supported receiver found!"
			return

		self.message = "echo -e '\n"
		self.message += (_("Back-up Tool for a %s\n" %self.SHOWNAME)).upper()
		self.message += VERSION + '\n'
		self.message += "_________________________________________________\n\n"
		self.message += _("Please be patient, a backup will now be made,\n")
		if self.ROOTFSTYPE == "ubifs":
			self.message += _("because of the used filesystem the back-up\n")
			self.message += _("will take about 3-12 minutes for this system\n")
		else:
			self.message += _("this will take between 2 and 9 minutes\n")
		self.message += "\n_________________________________________________\n\n"
		self.message += "'"

		## PREPARING THE BUILDING ENVIRONMENT
		system("rm -rf %s" %self.WORKDIR)
		if not path.exists(self.WORKDIR):
			makedirs(self.WORKDIR)
		if not path.exists("/tmp/bi/root"):
			makedirs("/tmp/bi/root")
		system("sync")
		system("mount --bind / /tmp/bi/root")

		if self.ROOTFSTYPE == "jffs2":
			cmd1 = "%s --root=/tmp/bi/root --faketime --output=%s/root.jffs2 %s" % (self.MKFS, self.WORKDIR, self.JFFS2OPTIONS)
			cmd2 = None
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


		cmdlist = []
		cmdlist.append(self.message)
		cmdlist.append('echo "Create: root.%s\n"' %self.ROOTFSTYPE)
		cmdlist.append(cmd1)
		if cmd2:
			cmdlist.append(cmd2)
		cmdlist.append("chmod 644 %s/root.%s" %(self.WORKDIR, self.ROOTFSTYPE))
		cmdlist.append('echo " "')
		cmdlist.append('echo "Create: kerneldump"')
		cmdlist.append('echo " "')
		cmdlist.append("nanddump -a -f %s/vmlinux.gz /dev/%s" % (self.WORKDIR, self.MTDKERNEL))
		cmdlist.append('echo " "')
		cmdlist.append('echo "Check: kerneldump"')
		cmdlist.append("sync")
				
		self.session.open(Console, title = self.TITLE, cmdlist = cmdlist, finishedCallback = self.doFullBackupCB, closeOnSuccess = True)

	def doFullBackupCB(self):
		ret = commands.getoutput(' gzip -d %s/vmlinux.gz -c > /tmp/vmlinux.bin' % self.WORKDIR)
		if ret:
			text = "Kernel dump error\n"
			text += "Please Flash your Kernel new and Backup again"
			system('rm -rf /tmp/vmlinux.bin')
			self.session.open(MessageBox, _(text), type = MessageBox.TYPE_ERROR)
			return

		cmdlist = []
		cmdlist.append(self.message)
		cmdlist.append('echo "Kernel dump OK"')
		cmdlist.append("rm -rf /tmp/vmlinux.bin")
		cmdlist.append('echo "_________________________________________________"')
		cmdlist.append('echo "Almost there... "')
		cmdlist.append('echo "Now building the USB-Image"')

		system('rm -rf %s' %self.MAINDEST)
		if not path.exists(self.MAINDEST):
			makedirs(self.MAINDEST)
		if not path.exists(self.EXTRA):
			makedirs(self.EXTRA)

		f = open("%s/imageversion" %self.MAINDEST, "w")
		f.write(self.IMAGEVERSION)
		f.close()

		if self.TYPE == "ET" or self.TYPE == "VENTON" or self.TYPE == "SEZAM" or self.TYPE == "MICRACLE" or self.TYPE == "GI" or self.TYPE == "ODINM9" or self.TYPE == "ODINM7" or self.TYPE == "MARAM9" or self.TYPE == "E3HD" or self.TYPE == "MAXDIGITAL" or self.TYPE == "OCTAGON" or self.TYPE == "IXUSS" or self.TYPE == "SOGNO" or self.TYPE == "EVO":
			system('mv %s/root.%s %s/%s' %(self.WORKDIR, self.ROOTFSTYPE, self.MAINDEST, self.ROOTFSBIN))
			system('mv %s/vmlinux.gz %s/%s' %(self.WORKDIR, self.MAINDEST, self.KERNELBIN))
			cmdlist.append('echo "rename this file to "force" to force an update without confirmation" > %s/noforce' %self.MAINDEST)
			cmdlist.append('cp -r %s %s' % (self.MAINDEST, self.EXTRA))
		elif self.TYPE == "VU":
			if self.MODEL == "vusolo2" or self.MODEL == "vuduo2":
				self.ROOTFSBIN = "root_cfe_auto.bin"
			else:
				self.ROOTFSBIN = "root_cfe_auto.jffs2"
			system('mv %s/root.%s %s/%s' %(self.WORKDIR, self.ROOTFSTYPE, self.MAINDEST, self.ROOTFSBIN))
			self.KERNELBIN = "kernel_cfe_auto.bin"
			system('mv %s/vmlinux.gz %s/%s' %(self.WORKDIR, self.MAINDEST, self.KERNELBIN))
			cmdlist.append('echo "rename this file to "force" to force an update without confirmation" > %s/noforce' %self.MAINDEST)
			cmdlist.append('cp -r %s %s' % (self.MAINDEST, self.EXTRA))
		elif self.TYPE == "TECHNO" or self.TYPE == "IQON" or self.TYPE == "EDISION":
			self.ROOTFSBIN = "oe_rootfs.bin"
			system('mv %s/root.%s %s/%s' %(self.WORKDIR, self.ROOTFSTYPE, self.MAINDEST, self.ROOTFSBIN))
			self.KERNELBIN = "oe_kernel.bin"
			system('mv %s/vmlinux.gz %s/%s' %(self.WORKDIR, self.MAINDEST, self.KERNELBIN))
			cmdlist.append('echo "rename this file to "force" to force an update without confirmation" > %s/noforce' %self.MAINDEST)
			cmdlist.append('cp -r %s %s' % (self.MAINDEST, self.EXTRA))
		elif self.TYPE == "MIXOS":
			self.ROOTFSBIN = "root_cfe_auto.bin"
			system('mv %s/root.%s %s/%s' %(self.WORKDIR, self.ROOTFSTYPE, self.MAINDEST, self.ROOTFSBIN))
			self.KERNELBIN = "kernel_cfe_auto.bin"
			system('mv %s/vmlinux.gz %s/%s' %(self.WORKDIR, self.MAINDEST, self.KERNELBIN))
			cmdlist.append('echo "rename this file to "force" to force an update without confirmation" > %s/noforce' %self.MAINDEST)
			cmdlist.append('cp -r %s %s' % (self.MAINDEST, self.EXTRA))
		elif self.TYPE == "GIGABLUE":
			if self.ROOTFSTYPE == "jffs2":
				system('mv %s/root.jffs2 %s/rootfs.bin' %(self.WORKDIR, self.MAINDEST))
			else:
				system('mv %s/root.ubifs %s/rootfs.bin' %(self.WORKDIR, self.MAINDEST))
			system('mv %s/vmlinux.gz %s/kernel.bin' %(self.WORKDIR, self.MAINDEST))
			cmdlist.append('echo "rename this file to "force" to force an update without confirmation" > %s/noforce' %self.MAINDEST)
			if self.MODEL == "quad" or self.MODEL == "quadplus" or self.MODEL == "ue" or self.MODEL == "ueplus":
				lcdwaitkey = '/usr/share/lcdwaitkey.bin'
				lcdwarning = '/usr/share/lcdwarning.bin'
				if path.exists(lcdwaitkey):
					system('cp %s %s/lcdwaitkey.bin' %(lcdwaitkey, self.MAINDEST))
				if path.exists(lcdwarning):
					system('cp %s %s/lcdwarning.bin' %(lcdwarning, self.MAINDEST))
			if self.MODEL == "solo":
				burnbat = "%s/fullbackup_%s/%s" % (self.DIRECTORY, self.TYPE, self.DATE)
				f = open("%s/burn.bat" % (burnbat), "w")
				f.write("flash -noheader usbdisk0:gigablue/solo/kernel.bin flash0.kernel\n")
				f.write("flash -noheader usbdisk0:gigablue/solo/rootfs.bin flash0.rootfs\n")
				f.write('setenv -p STARTUP "boot -z -elf flash0.kernel: ')
				f.write("'rootfstype=jffs2 bmem=106M@150M root=/dev/mtdblock6 rw '")
				f.write('"\n')
				f.close()
			cmdlist.append('cp -r %s %s' % (self.MAINDEST, self.EXTRA))

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

		if file_found:
			cmdlist.append('echo "_________________________________________________\n"')
			cmdlist.append('echo "USB Image created on:" %s' %self.MAINDEST)
			cmdlist.append('echo "and there is made an extra copy on:"')
			cmdlist.append('echo %s' %self.EXTRA)
			cmdlist.append('echo "_________________________________________________\n"')
			cmdlist.append('echo " "')
			cmdlist.append('echo "\nPlease wait...almost ready! "')
			cmdlist.append('echo " "')
			cmdlist.append('echo "To restore the image:"')
			cmdlist.append('echo "Please check the manual of the receiver"')
			cmdlist.append('echo "on how to restore the image"')
		else:
			cmdlist.append('echo "_________________________________________________\n"')
			cmdlist.append('echo "Image creation failed - "')
			cmdlist.append('echo "Probable causes could be"')
			cmdlist.append('echo "     wrong back-up destination "')
			cmdlist.append('echo "     no space left on back-up device"')
			cmdlist.append('echo "     no writing permission on back-up device"')
			cmdlist.append('echo " "')

		if self.DIRECTORY == "/hdd":
			self.TARGET = self.SearchUSBcanidate()
			print "TARGET = %s" % self.TARGET
			if self.TARGET == 'XX':
				cmdlist.append('echo " "')
			else:
				cmdlist.append('echo "_________________________________________________\n"')
				cmdlist.append('echo " "')
				cmdlist.append('echo "There is a valid USB-flash drive detected in one "')
				cmdlist.append('echo "of the USB-ports, therefor an extra copy of the "')
				cmdlist.append('echo "back-up image will now be copied to that USB- "')
				cmdlist.append('echo "flash drive. "')
				cmdlist.append('echo "This only takes about 1 or 2 minutes"')
				cmdlist.append('echo " "')

				if self.TYPE == 'ET':
					cmdlist.append('mkdir -p %s/%sx00' % (self.TARGET, self.MODEL[:-3]))
					cmdlist.append('cp -r %s %s' % (self.MAINDEST, self.TARGET))
				elif self.TYPE == 'VU':
					cmdlist.append('mkdir -p %s/vuplus_back/%s' % (self.TARGET, self.MODEL[2:]))
					cmdlist.append('cp -r %s %s/vuplus_back/' % (self.MAINDEST, self.TARGET))
				elif self.TYPE == 'VENTON':
					cmdlist.append('mkdir -p %s/venton/%s' % (self.TARGET, self.MODEL))
					cmdlist.append('cp -r %s %s/venton/' % (self.MAINDEST, self.TARGET))
				elif self.TYPE == 'SEZAM':
					cmdlist.append('mkdir -p %s/%s' % (self.TARGET, self.MODEL))
					cmdlist.append('cp -r %s %s/' % (self.MAINDEST, self.TARGET))
				elif self.TYPE == 'MICRACLE':
					cmdlist.append('mkdir -p %s/miraclebox/%s' % (self.TARGET, self.MODEL))
					cmdlist.append('cp -r %s %s/miraclebox/' % (self.MAINDEST, self.TARGET))					
				elif self.TYPE == 'GI':
					cmdlist.append('mkdir -p %s/%s' % (self.TARGET, self.MODEL))
					cmdlist.append('cp -r %s %s/' % (self.MAINDEST, self.TARGET))
				elif self.TYPE == 'GIGABLUE':
					cmdlist.append('mkdir -p %s/gigablue/%s' % (self.TARGET, self.MODEL))
					cmdlist.append('cp -r %s %s/gigablue/' % (self.MAINDEST, self.TARGET))
				elif self.TYPE == 'SOGNO':
					cmdlist.append('mkdir -p %s/sogno/%s' % (self.TARGET, self.MODEL))
					cmdlist.append('cp -r %s %s/sogno/' % (self.MAINDEST, self.TARGET))
				elif self.TYPE == 'ODINM9' or self.TYPE == 'MARAM9':
					#cmdlist.append('mkdir -p %s/odinm9/%s' % (self.TARGET, self.MODEL))
					cmdlist.append('cp -r %s %s/' % (self.MAINDEST, self.TARGET))
				elif self.TYPE == 'ODINM7':
					#cmdlist.append('mkdir -p %s/' % (self.TARGET))
					cmdlist.append('cp -r %s %s/' % (self.MAINDEST, self.TARGET))
				elif self.TYPE == 'E3HD':
					#cmdlist.append('mkdir -p %s/' % (self.TARGET))
					cmdlist.append('cp -r %s %s/' % (self.MAINDEST, self.TARGET))
				elif self.TYPE == 'MAXDIGITAL' or self.TYPE == 'OCTAGON':
					cmdlist.append('mkdir -p %s/%s' % (self.TARGET, self.MODEL))
					cmdlist.append('cp -r %s %s/' % (self.MAINDEST, self.TARGET))
				elif self.TYPE == 'IXUSS':
					cmdlist.append('mkdir -p %s/%s' % (self.TARGET, self.MODEL))
					cmdlist.append('cp -r %s %s/' % (self.MAINDEST, self.TARGET))
				elif self.TYPE == 'IXUSS':
					cmdlist.append('mkdir -p %s/%s' % (self.TARGET, self.MODEL))
					cmdlist.append('cp -r %s %s/' % (self.MAINDEST, self.TARGET))
				elif self.TYPE == 'MIXOS':
					cmdlist.append('mkdir -p %s/ebox/7403' % (self.TARGET))
					cmdlist.append('cp -r %s %s/' % (self.MAINDEST, self.TARGET))
				elif self.TYPE == 'MIXOS2':
					cmdlist.append('mkdir -p %s/ebox/7358' % (self.TARGET))
					cmdlist.append('cp -r %s %s/' % (self.MAINDEST, self.TARGET))
				elif self.TYPE == 'TECHNO':
					cmdlist.append('mkdir -p %s/update/%s/cfe' % (self.TARGET, self.MODEL))
					cmdlist.append('cp -r %s %s/update/%s/cfe' % (self.MAINDEST, self.TARGET, self.MODEL))
				elif self.TYPE == 'IQON':
					cmdlist.append('mkdir -p %s/update/%s/cfe' % (self.TARGET, self.MODEL))
					cmdlist.append('cp -r %s %s/update/%s/cfe' % (self.MAINDEST, self.TARGET, self.MODEL))
				elif self.TYPE == 'EDISION':
					cmdlist.append('mkdir -p %s/update/%s/cfe' % (self.TARGET, self.MODEL))
					cmdlist.append('cp -r %s %s/update/%s/cfe' % (self.MAINDEST, self.TARGET, self.MODEL))
				else:
					cmdlist.append('echo " "')

				cmdlist.append("sync")
				cmdlist.append('echo "Backup finished and copied to your USB-flash drive"')
			
		cmdlist.append("umount /tmp/bi/root")
		cmdlist.append("rmdir /tmp/bi/root")
		cmdlist.append("rmdir /tmp/bi")
		cmdlist.append("rm -rf %s" % self.WORKDIR)
		cmdlist.append("sleep 5")
		END = time()
		DIFF = int(END - self.START)
		TIMELAP = str(datetime.timedelta(seconds=DIFF))
		cmdlist.append('echo " Time required for this process: %s"' %TIMELAP)

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
			AboutText += "Error reading bouquets.tv"
			
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
			AboutText += "Error reading bouquets.radio"

		AboutText += _("\n[Installed Plugins]\n")
		AboutText += commands.getoutput("opkg list_installed | grep enigma2-plugin-")

		return AboutText

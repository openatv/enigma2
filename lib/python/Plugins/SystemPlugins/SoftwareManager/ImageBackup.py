from datetime import timedelta
from os import listdir, makedirs, system
from os.path import exists, isdir, isfile, join as pathjoin
from subprocess import getoutput
from time import localtime, strftime, time

from Components.About import getChipSetString, getCPUBrand, getCPUInfoString
from Components.ActionMap import ActionMap
from Components.ChoiceList import ChoiceList, ChoiceEntryComponent
from Components.Harddisk import Freespace, getFolderSize
from Components.Sources.StaticText import StaticText
from Components.SystemInfo import GetBoxName, BoxInfo
from Screens.Console import Console
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Tools.BoundFunction import boundFunction
from Tools.MultiBoot import MultiBoot
from Tools.Directories import fileReadLines

MODULE_NAME = __name__.split(".")[-1]

DISTRO = BoxInfo.getItem("distro")
DISPLAYDISTRO = BoxInfo.getItem("displaydistro")
DISTROVERSION = BoxInfo.getItem("imageversion")
MACHINEBRAND = BoxInfo.getItem("displaybrand")
MACHINENAME = BoxInfo.getItem("displaymodel")

USEP = "_________________________________________________"


class ImageBackup(Screen):

	skin = """
	<screen name="Image Backup" position="center,center" size="750,900" flags="wfNoBorder" backgroundColor="transparent">
		<eLabel name="b" position="0,0" size="750,700" backgroundColor="#00ffffff" zPosition="-2" />
		<eLabel name="a" position="1,1" size="748,698" backgroundColor="#00000000" zPosition="-1" />
		<widget source="Title" render="Label" position="60,10" foregroundColor="#00ffffff" size="480,50" halign="left" font="Regular; 28" backgroundColor="#00000000" />
		<eLabel name="line" position="1,60" size="748,1" backgroundColor="#00ffffff" zPosition="1" />
		<eLabel name="line2" position="1,250" size="748,4" backgroundColor="#00ffffff" zPosition="1" />
		<widget name="config" position="2,280" size="730,380" font="Regular; 22" backgroundColor="#00000000" foregroundColor="#00e5b243" />
		<widget source="description" render="Label" position="2,80" size="730,30" halign="center" font="Regular; 22" backgroundColor="#00000000" foregroundColor="#00ffffff" />
		<widget source="options" render="Label" position="2,130" size="730,60" halign="center" font="Regular; 22" backgroundColor="#00000000" foregroundColor="#00ffffff" />
		<widget source="key_red" render="Label" position="30,200" size="150,30" noWrap="1" zPosition="1" valign="center" font="Regular; 20" halign="left" backgroundColor="#00000000" foregroundColor="#00ffffff" />
		<widget source="key_green" render="Label" position="200,200" size="150,30" noWrap="1" zPosition="1" valign="center" font="Regular; 20" halign="left" backgroundColor="#00000000" foregroundColor="#00ffffff" />
		<eLabel position="20,200" size="6,40" backgroundColor="#00e61700" /> <!-- Should be a pixmap -->
		<eLabel position="190,200" size="6,40" backgroundColor="#0061e500" /> <!-- Should be a pixmap -->
	</screen>
	"""

	def __init__(self, session, *args):
		Screen.__init__(self, session)
		self.setTitle(_("Image Backup"))
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Start"))
		self["description"] = StaticText(_("Use the cursor keys to select an installed image and then Start button."))
		self["options"] = StaticText("")
		self["config"] = ChoiceList(list=[ChoiceEntryComponent("", ((_("Retrieving image slots - Please wait...")), "Queued"))])
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "KeyboardInputActions", "MenuActions"], {
			"red": boundFunction(self.close, None),
			"green": self.start,
			"ok": self.start,
			"cancel": boundFunction(self.close, None),
			"up": self.keyUp,
			"down": self.keyDown,
			"left": self.keyLeft,
			"right": self.keyRight,
			"upRepeated": self.keyUp,
			"downRepeated": self.keyDown,
			"leftRepeated": self.keyLeft,
			"rightRepeated": self.keyRight,
			"menu": boundFunction(self.close, True),
		}, prio=0)
		# imagedict = []
		# self.getImageList = None
		# self.startit()
		self.onLayoutFinish.append(self.layoutFinished)
		print("[ImageBackup] DEBUG: Now running '__init__'.")
		self.callLater(self.startit)

	def layoutFinished(self):
		self["config"].instance.enableAutoNavigation(False)
		self.setTitle(self.title)

	def startit(self):
		MultiBoot.getSlotImageList(self.ImageList)

	def ImageList(self, imagedict):
		self.saveImageList = imagedict
		imageList = []
		currentimageslot = MultiBoot.getCurrentSlotCode()
		currentimageslot = int(currentimageslot) if currentimageslot and currentimageslot.isdecimal() else 1
		print("[Image Backup] Current Image Slot %s, Imagelist %s" % (currentimageslot, imagedict))
		if imagedict:
			for slotCode in sorted(imagedict.keys()):
				if imagedict[slotCode]["status"] == "active":
					if slotCode == "1" and currentimageslot == 1 and BoxInfo.getItem("canRecovery"):
						imageList.append(ChoiceEntryComponent("", (_("Slot %s: %s as USB Recovery") % (slotCode, imagedict[slotCode]["imagename"]), slotCode, True)))
					imageList.append(ChoiceEntryComponent("", ((_("Slot %s: %s (Current image)") if slotCode == str(currentimageslot) else _("Slot %s: %s")) % (slotCode, imagedict[slotCode]["imagename"]), slotCode, False)))
		else:
			if BoxInfo.getItem("canRecovery"):
				imageList.append(ChoiceEntryComponent("", (_("Internal flash: %s %s as USB Recovery") % (DISTRO, DISTROVERSION), "slotCode", True)))
			imageList.append(ChoiceEntryComponent("", (_("Internal flash:  %s %s ") % (DISTRO, DISTROVERSION), "slotCode", False)))
		self["config"].setList(imageList)
		for index, item in enumerate(imageList):
			if item[0][1] == str(currentimageslot):
				break
		self["config"].moveToIndex(index)

	def start(self):
		self.currentSelected = self["config"].l.getCurrentSelection()
		title = _("Please select a backup destination")
		choices = []
		retval = []
		if self.currentSelected[0][1] != "Queued":
			for media in ["/media/%s" % x for x in listdir("/media")] + (["/media/net/%s" % x for x in listdir("/media/net")] if isdir("/media/net") else []):
				if Freespace(media) > 300000:
					choices.append((_("Backup to destination: %s") % (media), self.currentSelected[0][1], media, self.currentSelected[0][2]))
			choices.append((_("No, do not backup a image"), False))
			self.session.openWithCallback(self.doFullBackup, ChoiceBox, title=title, list=choices)

	def selectionChanged(self):
		currentSelected = self["config"].l.getCurrentSelection()

	def keyUp(self):
		self["config"].instance.moveSelection(self["config"].instance.moveUp)
		self.selectionChanged()

	def keyLeft(self):
		self["config"].instance.moveSelection(self["config"].instance.moveUp)
		self.selectionChanged()

	def keyRight(self):
		self["config"].instance.moveSelection(self["config"].instance.moveDown)
		self.selectionChanged()

	def keyDown(self):
		self["config"].instance.moveSelection(self["config"].instance.moveDown)
		self.selectionChanged()

	def doFullBackup(self, answer):
		if answer is not None:
			if answer[1]:
				self.RECOVERY = answer[3]
				self.DIRECTORY = "%s/images" % answer[2]
				if not exists(self.DIRECTORY):
					try:
						makedirs(self.DIRECTORY)
					except OSError:
						self.session.open(MessageBox, _("Cannot create backup directory"), MessageBox.TYPE_ERROR, timeout=10)
						return
				self.SLOT = str(answer[1])
				self.DISTRO = DISTRO
				self.DISPLAYDISTRO = DISPLAYDISTRO
				self.DISTROVERSION = DISTROVERSION
				self.IMAGETYPE = BoxInfo.getItem("imagetype")
				self.IMAGEDEVBUILD = "" if self.IMAGETYPE == "release" else BoxInfo.getItem("imagedevbuild")
				self.MODEL = GetBoxName()
				self.OEM = BoxInfo.getItem("brand")
				self.MACHINEBUILD = BoxInfo.getItem("model")
				self.IMAGEFOLDER = BoxInfo.getItem("imagedir")
				self.UBINIZE_ARGS = BoxInfo.getItem("ubinize")
				self.MKUBIFS_ARGS = BoxInfo.getItem("mkubifs")
				self.ROOTFSSUBDIR = "none"
				self.ROOTFSBIN = BoxInfo.getItem("rootfile")
				self.KERNELBIN = BoxInfo.getItem("kernelfile")
				self.ROOTFSTYPE = BoxInfo.getItem("imagefs").strip()
				self.IMAGEBUILD = BoxInfo.getItem("imagebuild")
				self.DRIVERSDATE = BoxInfo.getItem("driversdate")
				self.IMGREVISION = BoxInfo.getItem("imgrevision")
				self.IMGVERSION = BoxInfo.getItem("imgversion")
				self.KERNEL = BoxInfo.getItem("kernel")

				if BoxInfo.getItem("canRecovery"):
					self.EMMCIMG = BoxInfo.getItem("canRecovery")[0]
					self.MTDBOOT = BoxInfo.getItem("canRecovery")[1]
				else:
					self.EMMCIMG = "none"
					self.MTDBOOT = "none"
				self.hasMultiBootMDT = False
				self.ROOTFSSUBDIR = "none"
				if MultiBoot.canMultiBoot():
					bootSlots = MultiBoot.getBootSlots()
					self.hasMultiBootMDT = bootSlots[self.SLOT].get("ubi", False)
					self.ROOTFSSUBDIR = bootSlots[self.SLOT].get("rootsubdir", "none")
					self.MTDKERNEL = bootSlots[self.SLOT]["kernel"].split("/")[2]
					if self.hasMultiBootMDT:
						self.MTDROOTFS = bootSlots[self.SLOT]["device"]
					else:
						self.MTDROOTFS = bootSlots[self.SLOT]["device"].split("/")[2]
				else:
					self.MTDKERNEL = BoxInfo.getItem("mtdkernel")
					self.MTDROOTFS = BoxInfo.getItem("mtdrootfs")

				print("[Image Backup] BOX MACHINEBUILD = >%s<" % self.MACHINEBUILD)
				print("[Image Backup] BOX MACHINENAME = >%s<" % MACHINENAME)
				print("[Image Backup] BOX MACHINEBRAND = >%s<" % MACHINEBRAND)
				print("[Image Backup] BOX MODEL = >%s<" % self.MODEL)
				print("[Image Backup] OEM MODEL = >%s<" % self.OEM)
				print("[Image Backup] IMAGEFOLDER = >%s<" % self.IMAGEFOLDER)
				print("[Image Backup] UBINIZE = >%s<" % self.UBINIZE_ARGS)
				print("[Image Backup] MKUBIFS = >%s<" % self.MKUBIFS_ARGS)
				print("[Image Backup] MTDBOOT = >%s<" % self.MTDBOOT)
				print("[Image Backup] MTDKERNEL = >%s<" % self.MTDKERNEL)
				print("[Image Backup] MTDROOTFS = >%s<" % self.MTDROOTFS)
				print("[Image Backup] ROOTFSBIN = >%s<" % self.ROOTFSBIN)
				print("[Image Backup] KERNELBIN = >%s<" % self.KERNELBIN)
				print("[Image Backup] ROOTFSSUBDIR = >%s<" % self.ROOTFSSUBDIR)
				print("[Image Backup] ROOTFSTYPE = >%s<" % self.ROOTFSTYPE)
				print("[Image Backup] hasMultiBootMDT = >%s<" % self.hasMultiBootMDT)
				print("[Image Backup] EMMCIMG = >%s<" % self.EMMCIMG)
				print("[Image Backup] MTDBOOT = >%s<" % self.MTDBOOT)
				print("[Image Backup] USB RECOVERY = >%s< " % self.RECOVERY)
				print("[Image Backup] DESTINATION = >%s< " % self.DIRECTORY)
				print("[Image Backup] SLOT = >%s< " % self.SLOT)

				isNotCurrent = MultiBoot.getCurrentSlotCode() != answer[1]

				if self.RECOVERY and not isNotCurrent:
					print("[Image Backup] IMAGEDISTRO = >%s<" % self.DISTRO)
					print("[Image Backup] DISPLAYDISTRO = >%s<" % self.DISPLAYDISTRO)
					print("[Image Backup] DISTROVERSION = >%s<" % self.DISTROVERSION)
					print("[Image Backup] IMAGEBUILD = >%s<" % self.IMAGEBUILD)
					print("[Image Backup] IMGVERSION = >%s<" % self.IMGVERSION)
					print("[Image Backup] IMGREVISION = >%s<" % self.IMGREVISION)
					print("[Image Backup] DRIVERSDATE = >%s<" % self.DRIVERSDATE)
					print("[Image Backup] IMAGEDEVBUILD = >%s<" % self.IMAGEDEVBUILD)
					print("[Image Backup] IMAGETYPE = >%s<" % self.IMAGETYPE)

				self.TITLE = _("Full back-up on %s") % (self.DIRECTORY)
				self.START = time()
				self.DATE = strftime("%Y%m%d_%H%M", localtime(self.START))
				self.MKFS_UBI = "/usr/sbin/mkfs.ubifs"
				self.MKFS_TAR = "/bin/tar"
				self.BZIP2 = "/usr/bin/bzip2"
				self.MKFS_JFFS2 = "/usr/sbin/mkfs.jffs2"
				self.UBINIZE = "/usr/sbin/ubinize"
				self.NANDDUMP = "/usr/sbin/nanddump"
				self.FASTBOOT = "/usr/bin/ext2simg"
				self.WORKDIR = "%s/bi" % self.DIRECTORY

				self.SHOWNAME = "%s %s" % (MACHINEBRAND, self.MODEL)
				self.MAINDEST = "%s/build_%s/%s" % (self.DIRECTORY, self.MODEL, self.IMAGEFOLDER)
				self.MAINDESTROOT = "%s/build_%s" % (self.DIRECTORY, self.MODEL)

				## PREPARING THE BUILDING ENVIRONMENT
				system("rm -rf %s" % self.WORKDIR)
				self.backuproot = "/tmp/bi/RootSubdir" if self.ROOTFSSUBDIR != "none" else "/tmp/bi/root"
				if not exists(self.WORKDIR):
					makedirs(self.WORKDIR)
				if not exists(self.backuproot):
					makedirs(self.backuproot)
				system("sync")
				if MultiBoot.canMultiBoot():
					mountcmd = "/dev/%s %s" % (self.MTDROOTFS, self.backuproot)
					if self.ROOTFSSUBDIR != "none":
						if self.hasMultiBootMDT:
							mountcmd = "-t ubifs %s %s" % (self.MTDROOTFS, self.backuproot)
						self.backuproot = "%s/%s" % (self.backuproot, self.ROOTFSSUBDIR)
				else:
					mountcmd = "--bind / %s" % (self.backuproot)
				system("mount %s" % mountcmd)

				self.IMAGEVERSION = ""
				# Get real slot info if not current slot and not recovery
				if not self.RECOVERY:
					infoPath = "/"
					if MultiBoot.canMultiBoot() and isNotCurrent:
						infoPath = self.backuproot
					(enigmaInfo, info, settingsFile, bouquetsTV, bouquetsRadio) = self.getImageData(infoPath, isNotCurrent)

					if isNotCurrent:
						if "distro" in info:
							self.DISTRO = info["distro"]
						if "displaydistro" in info:
							self.DISPLAYDISTRO = info["displaydistro"]
						if "imageversion" in info:
							self.DISTROVERSION = info["imageversion"]
						if "imagetype" in info:
							self.IMAGETYPE = info["imagetype"]
						if "imagedevbuild" in info:
							self.IMAGEDEVBUILD = info["imagedevbuild"]
						if "imagebuild" in info:
							self.IMAGEBUILD = info["imagebuild"]
						if "driversdate" in info:
							self.DRIVERSDATE = info["driversdate"]
						if "imgrevision" in info:
							self.IMGREVISION = info["imgrevision"]
						if "imgversion" in info:
							self.IMGVERSION = info["imgversion"]
						if "kernel" in info:
							self.KERNEL = info["kernel"]
						if not enigmaInfo:
							self.IMGREVISION = info["compiledate"]
							self.DISTROVERSION = info["imgversion"]
							self.IMAGEBUILD = info["compiledate"]
							self.DRIVERSDATE = ""

						if self.IMAGETYPE != "release" and self.IMAGEDEVBUILD:
							self.DISTROVERSION = "%s.%s" % (self.DISTROVERSION, self.IMAGEDEVBUILD)

						print("[Image Backup] IMAGEDISTRO = >%s<" % self.DISTRO)
						print("[Image Backup] DISPLAYDISTRO = >%s<" % self.DISPLAYDISTRO)
						print("[Image Backup] DISTROVERSION = >%s<" % self.DISTROVERSION)
						print("[Image Backup] IMAGEBUILD = >%s<" % self.IMAGEBUILD)
						print("[Image Backup] IMGVERSION = >%s<" % self.IMGVERSION)
						print("[Image Backup] IMGREVISION = >%s<" % self.IMGREVISION)
						print("[Image Backup] DRIVERSDATE = >%s<" % self.DRIVERSDATE)
						print("[Image Backup] IMAGEDEVBUILD = >%s<" % self.IMAGEDEVBUILD)
						print("[Image Backup] IMAGETYPE = >%s<" % self.IMAGETYPE)

					self.IMAGEVERSION = self.imageInfo(settingsFile, bouquetsTV, bouquetsRadio, isNotCurrent)
				else:
					self.IMAGEVERSION = ""  # TODO TEST Recovery image

				self.message = "echo -e '\n"
				if MACHINEBRAND.startswith("A") or MACHINEBRAND.startswith("E") or MACHINEBRAND.startswith("I") or MACHINEBRAND.startswith("O") or MACHINEBRAND.startswith("U") or MACHINEBRAND.startswith("Xt"):
					self.message += (_("Back-up Tool for an %s\n") % self.SHOWNAME).upper()
				else:
					self.message += (_("Back-up Tool for a %s\n") % self.SHOWNAME).upper()
				self.message += _("Version %s %s") % (self.DISTRO, self.DISTROVERSION) + "\n"
				self.message += "%s\n\n" % USEP
				self.message += _("Please be patient, a backup will now be made,\n")
				self.message += _("because of the used file system the back-up\n")
				self.message += _("will take about 1-15 minutes for this system\n")
				self.message += "%s\n\n" % USEP
				if self.RECOVERY:
					self.message += _("Backup Mode: USB Recovery\n")
				else:
					self.message += _("Backup Mode: Flash Online\n")
				self.message += "%s\n" % USEP
				self.message += "'"

				cmd1 = None
				cmd2 = None
				cmd3 = None
				if "jffs2" in self.ROOTFSTYPE.split():
					cmd1 = "%s --root=%s --faketime --output=%s/root.jffs2 %s" % (self.MKFS_JFFS2, self.backuproot, self.WORKDIR, self.MKUBIFS_ARGS)
				elif "ubi" in self.ROOTFSTYPE.split():
					f = open("%s/ubinize.cfg" % self.WORKDIR, "w")
					f.write("[ubifs]\n")
					f.write("mode=ubi\n")
					f.write("image=%s/root.ubi\n" % self.WORKDIR)
					f.write("vol_id=0\n")
					f.write("vol_type=dynamic\n")
					f.write("vol_name=rootfs\n")
					f.write("vol_flags=autoresize\n")
					f.close()
					ff = open("%s/root.ubi" % self.WORKDIR, "w")
					ff.close()
					cmd1 = "%s -r %s -o %s/root.ubi %s" % (self.MKFS_UBI, self.backuproot, self.WORKDIR, self.MKUBIFS_ARGS)
					cmd2 = "%s -o %s/root.ubifs %s %s/ubinize.cfg" % (self.UBINIZE, self.WORKDIR, self.UBINIZE_ARGS, self.WORKDIR)
				elif not self.RECOVERY:
					cmd1 = "%s -cf %s/rootfs.tar -C %s --exclude ./var/nmbd --exclude ./.resizerootfs --exclude ./.resize-rootfs --exclude ./.resize-linuxrootfs --exclude ./.resize-userdata --exclude ./var/lib/samba/private/msg.sock --exclude ./var/lib/samba/msg.sock/* --exclude ./run/avahi-daemon/socket ." % (self.MKFS_TAR, self.WORKDIR, self.backuproot)
					cmd2 = "sync"
					cmd3 = "%s %s/rootfs.tar" % (self.BZIP2, self.WORKDIR)

				cmdlist = []
				cmdlist.append(self.message)
				if cmd1:
					cmdlist.append(self.makeEchoCreate(self.ROOTFSBIN))
					cmdlist.append(cmd1)
				if cmd2:
					cmdlist.append(cmd2)
				if cmd3:
					cmdlist.append(cmd3)

				if self.MODEL in ("gbquad4k", "gbue4k", "gbx34k"):
					cmdlist.append(self.makeEchoCreate("boot dump"))
					cmdlist.append("dd if=/dev/mmcblk0p1 of=%s/boot.bin" % self.WORKDIR)
					cmdlist.append(self.makeEchoCreate("rescue dump"))
					cmdlist.append("dd if=/dev/mmcblk0p3 of=%s/rescue.bin" % self.WORKDIR)

				if self.MACHINEBUILD in ("h9", "i55plus"):
					for index, value in enumerate(["fastboot", "bootargs", "baseparam", "pq_param", "logo"]):
						cmdlist.append(self.makeEchoCreate("%s dump" % value))
						cmdlist.append("dd if=/dev/mtd%d of=%s/%s.bin" % (index, self.WORKDIR, value))

				if self.EMMCIMG == "usb_update.bin" and self.RECOVERY:
					SEEK_CONT = int((getFolderSize(self.backuproot) / 1024) + 100000)

					cmdlist.append(self.makeEchoCreate("fastboot dump"))
					cmdlist.append(self.makeCopyBinFile("fastboot", self.WORKDIR))
					#cmdlist.append("dd if=/dev/mmcblk0p1 of=%s/fastboot.bin" % self.WORKDIR)

					cmdlist.append(self.makeEchoCreate("bootargs dump"))
					cmdlist.append(self.makeCopyBinFile("bootargs", self.WORKDIR))
					#cmdlist.append("dd if=/dev/mmcblk0p2 of=%s/bootargs.bin" % self.WORKDIR)

					cmdlist.append(self.makeEchoCreate("boot dump"))
					cmdlist.append("dd if=/dev/mmcblk0p3 of=%s/boot.img" % self.WORKDIR)

					cmdlist.append(self.makeEchoCreate("baseparam dump"))
					#cmdlist.append("cp -f /usr/share/bootargs.bin %s/baseparam.img" %(self.WORKDIR))
					cmdlist.append("dd if=/dev/mmcblk0p4 of=%s/baseparam.img" % self.WORKDIR)

					cmdlist.append(self.makeEchoCreate("pq_param dump"))
					#cmdlist.append("cp -f /usr/share/bootargs.bin %s/pq_param.bin" %(self.WORKDIR))
					cmdlist.append("dd if=/dev/mmcblk0p5 of=%s/pq_param.bin" % self.WORKDIR)

					cmdlist.append(self.makeEchoCreate("logo dump"))
					cmdlist.append("dd if=/dev/mmcblk0p6 of=%s/logo.img" % self.WORKDIR)

					cmdlist.append(self.makeEchoCreate("deviceinfo dump"))
					#cmdlist.append("cp -f /usr/share/bootargs.bin %s/deviceinfo.bin" %(self.WORKDIR))
					cmdlist.append("dd if=/dev/mmcblk0p7 of=%s/deviceinfo.bin" % self.WORKDIR)

					cmdlist.append(self.makeEchoCreate("apploader dump"))
					cmdlist.append(self.makeCopyBinFile("apploader", self.WORKDIR))
					#cmdlist.append("dd if=/dev/mmcblk0p10 of=%s/apploader.bin" % self.WORKDIR)

					cmdlist.append(self.makeEchoCreate("rootfs dump"))
					cmdlist.append("dd if=/dev/zero of=%s/rootfs.ext4 seek=%s count=60 bs=1024" % (self.WORKDIR, SEEK_CONT))
					cmdlist.append("mkfs.ext4 -F -i 4096 %s/rootfs.ext4" % (self.WORKDIR))
					cmdlist.append("mkdir -p %s/userdata" % self.WORKDIR)
					cmdlist.append("mount %s/rootfs.ext4 %s/userdata" % (self.WORKDIR, self.WORKDIR))
					for rootindex in range(1, 5):
						cmdlist.append("mkdir -p %s/userdata/linuxrootfs%d" % (self.WORKDIR, rootindex))

					cmdlist.append("rsync -aAX %s/ %s/userdata/linuxrootfs1/" % (self.backuproot, self.WORKDIR))
					cmdlist.append("umount %s/userdata" % (self.WORKDIR))

				cmdlist.append(self.makeEchoCreate("kerneldump"))
				if MultiBoot.canMultiBoot() or self.MTDKERNEL.startswith("mmcblk0") or self.MACHINEBUILD in ("h8", "hzero"):
					cmdlist.append("dd if=/dev/%s of=%s/%s" % (self.MTDKERNEL, self.WORKDIR, self.KERNELBIN))
				else:
					cmdlist.append("nanddump -a -f %s/vmlinux.gz /dev/%s" % (self.WORKDIR, self.MTDKERNEL))

				if self.EMMCIMG == "disk.img" and self.RECOVERY:
					EMMC_IMAGE = "%s/%s" % (self.WORKDIR, self.EMMCIMG)
					BLOCK_SIZE = 512
					BLOCK_SECTOR = 2
					IMAGE_ROOTFS_ALIGNMENT = 1024
					BOOT_PARTITION_SIZE = 3072
					KERNEL_PARTITION_SIZE = 8192
					ROOTFS_PARTITION_SIZE = 1048576
					EMMC_IMAGE_SIZE = 3817472
					KERNEL_PARTITION_OFFSET = int(IMAGE_ROOTFS_ALIGNMENT) + int(BOOT_PARTITION_SIZE)
					ROOTFS_PARTITION_OFFSET = int(KERNEL_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
					SECOND_KERNEL_PARTITION_OFFSET = int(ROOTFS_PARTITION_OFFSET) + int(ROOTFS_PARTITION_SIZE)
					THRID_KERNEL_PARTITION_OFFSET = int(SECOND_KERNEL_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
					FOURTH_KERNEL_PARTITION_OFFSET = int(THRID_KERNEL_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
					MULTI_ROOTFS_PARTITION_OFFSET = int(FOURTH_KERNEL_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
					EMMC_IMAGE_SEEK = int(EMMC_IMAGE_SIZE) * int(BLOCK_SECTOR)
					cmdlist.append(self.makeEcho(_("Create: Recovery Fullbackup %s") % (self.EMMCIMG)))
					cmdlist.append("dd if=/dev/zero of=%s bs=%s count=0 seek=%s" % (EMMC_IMAGE, BLOCK_SIZE, EMMC_IMAGE_SEEK))
					cmdlist.append("parted -s %s mklabel gpt" % EMMC_IMAGE)
					PARTED_END_BOOT = int(IMAGE_ROOTFS_ALIGNMENT) + int(BOOT_PARTITION_SIZE)
					cmdlist.append("parted -s %s unit KiB mkpart boot fat16 %s %s" % (EMMC_IMAGE, IMAGE_ROOTFS_ALIGNMENT, PARTED_END_BOOT))
					PARTED_END_KERNEL1 = int(KERNEL_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
					cmdlist.append("parted -s %s unit KiB mkpart linuxkernel %s %s" % (EMMC_IMAGE, KERNEL_PARTITION_OFFSET, PARTED_END_KERNEL1))
					PARTED_END_ROOTFS1 = int(ROOTFS_PARTITION_OFFSET) + int(ROOTFS_PARTITION_SIZE)
					cmdlist.append("parted -s %s unit KiB mkpart linuxrootfs ext4 %s %s" % (EMMC_IMAGE, ROOTFS_PARTITION_OFFSET, PARTED_END_ROOTFS1))
					PARTED_END_KERNEL2 = int(SECOND_KERNEL_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
					cmdlist.append("parted -s %s unit KiB mkpart linuxkernel2 %s %s" % (EMMC_IMAGE, SECOND_KERNEL_PARTITION_OFFSET, PARTED_END_KERNEL2))
					PARTED_END_KERNEL3 = int(THRID_KERNEL_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
					cmdlist.append("parted -s %s unit KiB mkpart linuxkernel3 %s %s" % (EMMC_IMAGE, THRID_KERNEL_PARTITION_OFFSET, PARTED_END_KERNEL3))
					PARTED_END_KERNEL4 = int(FOURTH_KERNEL_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
					cmdlist.append("parted -s %s unit KiB mkpart linuxkernel4 %s %s" % (EMMC_IMAGE, FOURTH_KERNEL_PARTITION_OFFSET, PARTED_END_KERNEL4))
					rd = open("/proc/swaps", "r").read()
					if "mmcblk0p7" in rd:
						SWAP_PARTITION_OFFSET = int(FOURTH_KERNEL_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
						SWAP_PARTITION_SIZE = int(262144)
						MULTI_ROOTFS_PARTITION_OFFSET = int(SWAP_PARTITION_OFFSET) + int(SWAP_PARTITION_SIZE)
						cmdlist.append("parted -s %s unit KiB mkpart swap linux-swap %s %s" % (EMMC_IMAGE, SWAP_PARTITION_OFFSET, SWAP_PARTITION_OFFSET + SWAP_PARTITION_SIZE))
						cmdlist.append("parted -s %s unit KiB mkpart userdata ext4 %s 100%%" % (EMMC_IMAGE, MULTI_ROOTFS_PARTITION_OFFSET))
					else:
						cmdlist.append("parted -s %s unit KiB mkpart userdata ext4 %s 100%%" % (EMMC_IMAGE, MULTI_ROOTFS_PARTITION_OFFSET))
					BOOT_IMAGE_SEEK = int(IMAGE_ROOTFS_ALIGNMENT) * int(BLOCK_SECTOR)
					cmdlist.append("dd if=/dev/%s of=%s seek=%s" % (self.MTDBOOT, EMMC_IMAGE, BOOT_IMAGE_SEEK))
					KERNAL_IMAGE_SEEK = int(KERNEL_PARTITION_OFFSET) * int(BLOCK_SECTOR)
					cmdlist.append("dd if=/dev/%s of=%s seek=%s" % (self.MTDKERNEL, EMMC_IMAGE, KERNAL_IMAGE_SEEK))
					ROOTFS_IMAGE_SEEK = int(ROOTFS_PARTITION_OFFSET) * int(BLOCK_SECTOR)
					cmdlist.append("dd if=/dev/%s of=%s seek=%s " % (self.MTDROOTFS, EMMC_IMAGE, ROOTFS_IMAGE_SEEK))
				elif self.EMMCIMG == "emmc.img" and self.RECOVERY:
					EMMC_IMAGE = "%s/%s" % (self.WORKDIR, self.EMMCIMG)
					BLOCK_SECTOR = 2
					IMAGE_ROOTFS_ALIGNMENT = 1024
					BOOT_PARTITION_SIZE = 3072
					KERNEL_PARTITION_SIZE = 8192
					ROOTFS_PARTITION_SIZE = 1898496
					EMMC_IMAGE_SIZE = 7634944
					BOOTDD_VOLUME_ID = "boot"
					KERNEL1_PARTITION_OFFSET = int(IMAGE_ROOTFS_ALIGNMENT) + int(BOOT_PARTITION_SIZE)
					ROOTFS1_PARTITION_OFFSET = int(KERNEL1_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
					KERNEL2_PARTITION_OFFSET = int(ROOTFS1_PARTITION_OFFSET) + int(ROOTFS_PARTITION_SIZE)
					ROOTFS2_PARTITION_OFFSET = int(KERNEL2_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
					KERNEL3_PARTITION_OFFSET = int(ROOTFS2_PARTITION_OFFSET) + int(ROOTFS_PARTITION_SIZE)
					ROOTFS3_PARTITION_OFFSET = int(KERNEL3_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
					KERNEL4_PARTITION_OFFSET = int(ROOTFS3_PARTITION_OFFSET) + int(ROOTFS_PARTITION_SIZE)
					ROOTFS4_PARTITION_OFFSET = int(KERNEL4_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
					EMMC_IMAGE_SEEK = int(EMMC_IMAGE_SIZE) * int(IMAGE_ROOTFS_ALIGNMENT)
					cmdlist.append(self.makeEcho(_("Create: Recovery Fullbackup %s") % (self.EMMCIMG)))
					cmdlist.append("dd if=/dev/zero of=%s bs=1 count=0 seek=%s" % (EMMC_IMAGE, EMMC_IMAGE_SEEK))
					cmdlist.append("parted -s %s mklabel gpt" % EMMC_IMAGE)
					PARTED_END_BOOT = int(IMAGE_ROOTFS_ALIGNMENT) + int(BOOT_PARTITION_SIZE)
					cmdlist.append("parted -s %s unit KiB mkpart boot fat16 %s %s" % (EMMC_IMAGE, IMAGE_ROOTFS_ALIGNMENT, PARTED_END_BOOT))
					cmdlist.append("parted -s %s set 1 boot on" % EMMC_IMAGE)
					PARTED_END_KERNEL1 = int(KERNEL1_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
					cmdlist.append("parted -s %s unit KiB mkpart kernel1 %s %s" % (EMMC_IMAGE, KERNEL1_PARTITION_OFFSET, PARTED_END_KERNEL1))
					PARTED_END_ROOTFS1 = int(ROOTFS1_PARTITION_OFFSET) + int(ROOTFS_PARTITION_SIZE)
					cmdlist.append("parted -s %s unit KiB mkpart rootfs1 ext4 %s %s" % (EMMC_IMAGE, ROOTFS1_PARTITION_OFFSET, PARTED_END_ROOTFS1))
					PARTED_END_KERNEL2 = int(KERNEL2_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
					cmdlist.append("parted -s %s unit KiB mkpart kernel2 %s %s" % (EMMC_IMAGE, KERNEL2_PARTITION_OFFSET, PARTED_END_KERNEL2))
					PARTED_END_ROOTFS2 = int(ROOTFS2_PARTITION_OFFSET) + int(ROOTFS_PARTITION_SIZE)
					cmdlist.append("parted -s %s unit KiB mkpart rootfs2 ext4 %s %s" % (EMMC_IMAGE, ROOTFS2_PARTITION_OFFSET, PARTED_END_ROOTFS2))
					PARTED_END_KERNEL3 = int(KERNEL3_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
					cmdlist.append("parted -s %s unit KiB mkpart kernel3 %s %s" % (EMMC_IMAGE, KERNEL3_PARTITION_OFFSET, PARTED_END_KERNEL3))
					PARTED_END_ROOTFS3 = int(ROOTFS3_PARTITION_OFFSET) + int(ROOTFS_PARTITION_SIZE)
					cmdlist.append("parted -s %s unit KiB mkpart rootfs3 ext4 %s %s" % (EMMC_IMAGE, ROOTFS3_PARTITION_OFFSET, PARTED_END_ROOTFS3))
					PARTED_END_KERNEL4 = int(KERNEL4_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
					cmdlist.append("parted -s %s unit KiB mkpart kernel4 %s %s" % (EMMC_IMAGE, KERNEL4_PARTITION_OFFSET, PARTED_END_KERNEL4))
					PARTED_END_ROOTFS4 = int(ROOTFS4_PARTITION_OFFSET) + int(ROOTFS_PARTITION_SIZE)
					cmdlist.append("parted -s %s unit KiB mkpart rootfs4 ext4 %s %s" % (EMMC_IMAGE, ROOTFS4_PARTITION_OFFSET, PARTED_END_ROOTFS4))
					BOOT_IMAGE_SEEK = int(IMAGE_ROOTFS_ALIGNMENT) * int(BLOCK_SECTOR)
					cmdlist.append("dd if=/dev/%s of=%s seek=%s" % (self.MTDBOOT, EMMC_IMAGE, BOOT_IMAGE_SEEK))
					KERNAL_IMAGE_SEEK = int(KERNEL1_PARTITION_OFFSET) * int(BLOCK_SECTOR)
					cmdlist.append("dd if=/dev/%s of=%s seek=%s" % (self.MTDKERNEL, EMMC_IMAGE, KERNAL_IMAGE_SEEK))
					ROOTFS_IMAGE_SEEK = int(ROOTFS1_PARTITION_OFFSET) * int(BLOCK_SECTOR)
					cmdlist.append("dd if=/dev/%s of=%s seek=%s " % (self.MTDROOTFS, EMMC_IMAGE, ROOTFS_IMAGE_SEEK))
				elif self.EMMCIMG == "usb_update.bin" and self.RECOVERY:
					cmdlist.append(self.makeEcho(_("Create: Recovery Fullbackup %s") % (self.EMMCIMG)))
					f = open("%s/emmc_partitions.xml" % self.WORKDIR, "w")
					f.write('<?xml version="1.0" encoding="GB2312" ?>\n')
					f.write("<Partition_Info>\n")
					f.write('<Part Sel="1" PartitionName="fastboot" FlashType="emmc" FileSystem="none" Start="0" Length="1M" SelectFile="fastboot.bin"/>\n')
					f.write('<Part Sel="1" PartitionName="bootargs" FlashType="emmc" FileSystem="none" Start="1M" Length="1M" SelectFile="bootargs.bin"/>\n')
					f.write('<Part Sel="1" PartitionName="bootoptions" FlashType="emmc" FileSystem="none" Start="2M" Length="1M" SelectFile="boot.img"/>\n')
					f.write('<Part Sel="1" PartitionName="baseparam" FlashType="emmc" FileSystem="none" Start="3M" Length="3M" SelectFile="baseparam.img"/>\n')
					f.write('<Part Sel="1" PartitionName="pqparam" FlashType="emmc" FileSystem="none" Start="6M" Length="4M" SelectFile="pq_param.bin"/>\n')
					f.write('<Part Sel="1" PartitionName="logo" FlashType="emmc" FileSystem="none" Start="10M" Length="4M" SelectFile="logo.img"/>\n')
					f.write('<Part Sel="1" PartitionName="deviceinfo" FlashType="emmc" FileSystem="none" Start="14M" Length="4M" SelectFile="deviceinfo.bin"/>\n')
					f.write('<Part Sel="1" PartitionName="loader" FlashType="emmc" FileSystem="none" Start="26M" Length="32M" SelectFile="apploader.bin"/>\n')
					f.write('<Part Sel="1" PartitionName="linuxkernel1" FlashType="emmc" FileSystem="none" Start="66M" Length="16M" SelectFile="kernel.bin"/>\n')
					if self.MACHINEBUILD in ("sf8008m"):
						f.write('<Part Sel="1" PartitionName="userdata" FlashType="emmc" FileSystem="ext3/4" Start="130M" Length="3580M" SelectFile="rootfs.ext4"/>\n')
					else:
						f.write('<Part Sel="1" PartitionName="userdata" FlashType="emmc" FileSystem="ext3/4" Start="130M" Length="7000M" SelectFile="rootfs.ext4"/>\n')
					f.write("</Partition_Info>\n")
					f.close()
					cmdlist.append("mkupdate -s 00000003-00000001-01010101 -f %s/emmc_partitions.xml -d %s/%s" % (self.WORKDIR, self.WORKDIR, self.EMMCIMG))
				self.session.open(Console, title=self.TITLE, cmdlist=cmdlist, finishedCallback=self.doFullBackupCB, closeOnSuccess=True)
			else:
				self.close()
		else:
			self.close()

	def makeEchoCreate(self, txt):
		return self.makeEcho("%s %s" % (_("Create:"), txt))

	def makeEcho(self, txt):
		return "echo \"%s\"" % txt

	def makeEchoLine(self, nocr=False):
		return "echo \"%s%s\"" % (USEP, "" if nocr else "\n")

	def makeSpace(self):
		return "echo \" \""

	def makeCopyBinFile(self, fileName, destination):
		return "cp -f /usr/share/%s.bin %s/%s.bin" % (fileName, destination, fileName)

	def doFullBackupCB(self):
		cmdlist = []
		cmdlist.append(self.message)
		cmdlist.append(self.makeEcho(_("Almost there... ")))
		cmdlist.append(self.makeEcho(_("Now building the Backup Image")))

		def initDestination(destination):
			system("rm -rf %s" % destination)
			if not exists(destination):
				makedirs(destination)
			with open("%s/imageversion" % destination, "w") as fd:
				fd.write(self.IMAGEVERSION)

		if self.EMMCIMG == "usb_update.bin" and self.RECOVERY:
			initDestination(self.MAINDESTROOT)
		else:
			initDestination(self.MAINDEST)
			if not self.RECOVERY:
				if self.ROOTFSBIN == "rootfs.tar.bz2":
					system("mv %s/%s %s/%s" % (self.WORKDIR, self.ROOTFSBIN, self.MAINDEST, self.ROOTFSBIN))
				else:
					system("mv %s/root.ubifs %s/%s" % (self.WORKDIR, self.MAINDEST, self.ROOTFSBIN))
				if MultiBoot.canMultiBoot() or self.MTDKERNEL.startswith("mmcblk0") or self.MACHINEBUILD in ("h8", "hzero"):
					system("mv %s/%s %s/%s" % (self.WORKDIR, self.KERNELBIN, self.MAINDEST, self.KERNELBIN))
				else:
					system("mv %s/vmlinux.gz %s/%s" % (self.WORKDIR, self.MAINDEST, self.KERNELBIN))

		if self.RECOVERY:
			if self.EMMCIMG == "usb_update.bin":
				system("mv %s/%s %s/%s" % (self.WORKDIR, self.EMMCIMG, self.MAINDESTROOT, self.EMMCIMG))
				cmdlist.append(self.makeCopyBinFile("fastboot", self.MAINDESTROOT))
				cmdlist.append(self.makeCopyBinFile("bootargs", self.MAINDESTROOT))
				cmdlist.append(self.makeCopyBinFile("apploader", self.MAINDESTROOT))
			else:
				system("mv %s/%s %s/%s" % (self.WORKDIR, self.EMMCIMG, self.MAINDEST, self.EMMCIMG))
			if self.EMMCIMG == "emmc.img":
				cmdlist.append('echo "rename this file to "force" to force an update without confirmation" > %s/noforce' % self.MAINDEST)
		elif self.MODEL in ("vuultimo4k", "vusolo4k", "vuduo2", "vusolo2", "vusolo", "vuduo", "vuultimo", "vuuno"):
			cmdlist.append('echo "This file forces a reboot after the update." > %s/reboot.update' % self.MAINDEST)
		elif self.MODEL in ("vuzero", "vusolose", "vuuno4k", "vuzero4k"):
			cmdlist.append('echo "This file forces the update." > %s/force.update' % self.MAINDEST)
		elif self.MODEL in ("viperslim", "evoslimse", "evoslimt2c", "novaip", "zgemmai55", "sf98", "xpeedlxpro", "evoslim", "vipert2c"):
			cmdlist.append('echo "This file forces the update." > %s/force' % self.MAINDEST)
		elif self.ROOTFSSUBDIR != "none":
			cmdlist.append('echo "Rename the unforce_%s.txt to force_%s.txt and move it to the root of your usb-stick" > %s/force_%s_READ.ME' % (self.MACHINEBUILD, self.MACHINEBUILD, self.MAINDEST, self.MACHINEBUILD))
			cmdlist.append('echo "When you enter the recovery menu then it will force to install the image in the linux1 selection" >> %s/force_%s_READ.ME' % (self.MAINDEST, self.MACHINEBUILD))
		else:
			cmdlist.append('echo "rename this file to "force" to force an update without confirmation" > %s/noforce' % self.MAINDEST)

		if self.MODEL in ("gbquad4k", "gbue4k", "gbx34k"):
			system("mv %s/boot.bin %s/boot.bin" % (self.WORKDIR, self.MAINDEST))
			system("mv %s/rescue.bin %s/rescue.bin" % (self.WORKDIR, self.MAINDEST))
			system("cp -f /usr/share/gpt.bin %s/gpt.bin" % (self.MAINDEST))

		if self.MACHINEBUILD in ("h9", "i55plus"):
			system("mv %s/fastboot.bin %s/fastboot.bin" % (self.WORKDIR, self.MAINDEST))
			system("mv %s/pq_param.bin %s/pq_param.bin" % (self.WORKDIR, self.MAINDEST))
			system("mv %s/bootargs.bin %s/bootargs.bin" % (self.WORKDIR, self.MAINDEST))
			system("mv %s/baseparam.bin %s/baseparam.bin" % (self.WORKDIR, self.MAINDEST))
			system("mv %s/logo.bin %s/logo.bin" % (self.WORKDIR, self.MAINDEST))

		if self.MODEL in ("gbquad", "gbquadplus", "gb800ue", "gb800ueplus", "gbultraue", "gbultraueh", "twinboxlcd", "twinboxlcdci", "singleboxlcd", "sf208", "sf228"):
			lcdwaitkey = "/usr/share/lcdwaitkey.bin"
			lcdwarning = "/usr/share/lcdwarning.bin"
			if isfile(lcdwaitkey):
				system("cp %s %s/lcdwaitkey.bin" % (lcdwaitkey, self.MAINDEST))
			if isfile(lcdwarning):
				system("cp %s %s/lcdwarning.bin" % (lcdwarning, self.MAINDEST))
		if self.MODEL in ("e4hdultra", "protek4k"):
			lcdwarning = "/usr/share/lcdflashing.bmp"
			if isfile(lcdwarning):
				system("cp %s %s/lcdflashing.bmp" % (lcdwarning, self.MAINDEST))
		if self.MODEL == "gb800solo":
			f = open("%s/burn.bat" % (self.MAINDESTROOT), "w")
			f.write("flash -noheader usbdisk0:gigablue/solo/kernel.bin flash0.kernel\n")
			f.write("flash -noheader usbdisk0:gigablue/solo/rootfs.bin flash0.rootfs\n")
			f.write('setenv -p STARTUP "boot -z -elf flash0.kernel: ')
			f.write("'rootfstype=jffs2 bmem=106M@150M root=/dev/mtdblock6 rw '")
			f.write('"\n')
			f.close()

		if self.MACHINEBUILD in ("h9", "i55plus"):
			cmdlist.append(self.makeCopyBinFile("fastboot", self.MAINDESTROOT))
			cmdlist.append(self.makeCopyBinFile("bootargs", self.MAINDESTROOT))

		iname = "recovery_emmc" if BoxInfo.getItem("canRecovery") and self.RECOVERY else "usb"

		cmdlist.append("7za a -r -bt -bd %s/%s-%s-%s-backup-%s_%s.zip %s/*" % (self.DIRECTORY, self.DISTRO, self.DISTROVERSION, self.MODEL, self.DATE, iname, self.MAINDESTROOT))

		cmdlist.append("sync")
		file_not_found = ""

		if self.RECOVERY:
			if self.EMMCIMG == "usb_update.bin":
				if not isfile("%s/%s" % (self.MAINDESTROOT, self.EMMCIMG)):
					file_not_found = self.EMMCIMG
			else:
				if not isfile("%s/%s" % (self.MAINDEST, self.EMMCIMG)):
					file_not_found = self.EMMCIMG
		else:
			if not isfile("%s/%s" % (self.MAINDEST, self.ROOTFSBIN)):
				file_not_found = self.ROOTFSBIN

			if not isfile("%s/%s" % (self.MAINDEST, self.KERNELBIN)):
				file_not_found = self.KERNELBIN

		if file_not_found:
			print("[Image Backup] %s file not found" % file_not_found)

		cmdlist.append(self.makeEchoLine())
		if MultiBoot.canMultiBoot() and not self.RECOVERY and self.ROOTFSSUBDIR == "none":
			cmdlist.append(self.makeEcho(_("Multiboot Image created on: %s/%s-%s-%s-backup-%s_usb.zip") % (self.DIRECTORY, self.DISTRO, self.DISTROVERSION, self.MODEL, self.DATE)))
			cmdlist.append(self.makeEchoLine(True))
			cmdlist.append(self.makeSpace())
			cmdlist.append(self.makeEcho(_("Please wait...almost ready! ")))
			cmdlist.append(self.makeSpace())
			cmdlist.append(self.makeEcho(_("To restore the image:")))
			cmdlist.append(self.makeEcho(_("Use OnlineFlash in SoftwareManager")))
		elif file_not_found == "":
			cmdlist.append(self.makeEcho(_("Image created on: %s/%s-%s-%s-backup-%s_%s.zip") % (self.DIRECTORY, self.DISTRO, self.DISTROVERSION, self.MODEL, self.DATE, iname)))
			cmdlist.append(self.makeEchoLine(True))
			cmdlist.append(self.makeSpace())
			cmdlist.append(self.makeEcho(_("Please wait...almost ready! ")))
			cmdlist.append(self.makeSpace())
			cmdlist.append(self.makeEcho(_("To restore the image:")))
			cmdlist.append(self.makeEcho(_("Please check the manual of the receiver")))
			cmdlist.append(self.makeEcho(_("on how to restore the image")))
		else:
			cmdlist.append(self.makeEcho(_("Image creation failed - ")))
			cmdlist.append(self.makeEcho(_("Probable causes could be") + ":"))
			cmdlist.append(self.makeEcho(_("     wrong back-up destination ")))
			cmdlist.append(self.makeEcho(_("     no space left on back-up device")))
			cmdlist.append(self.makeEcho(_("     no writing permission on back-up device")))
			cmdlist.append(self.makeSpace())

		cmdlist.append("rm -rf %s/build_%s" % (self.DIRECTORY, self.MODEL))
		rdir = "RootSubdir" if self.ROOTFSSUBDIR != "none" else "root"
		cmdlist.append("umount /tmp/bi/%s" % rdir)
		cmdlist.append("rmdir /tmp/bi/%s" % rdir)
		cmdlist.append("rmdir /tmp/bi")
		cmdlist.append("rm -rf %s" % self.WORKDIR)
		cmdlist.append("sleep 5")
		END = time()
		DIFF = int(END - self.START)
		TIMELAP = str(timedelta(seconds=DIFF))
		cmdlist.append(self.makeEcho(_("Time required for this process: %s") % TIMELAP + "\n"))

		self.session.open(Console, title=self.TITLE, cmdlist=cmdlist, closeOnSuccess=False)

	def imageInfo(self, settings, bouquetsTV, bouquetsRadio, isNotCurrent):
		AboutText = _("Full Image Backup ")
		AboutText += _("By openATV Image Team") + "\n"
		AboutText += _("Support at") + " www.opena.tv\n\n"
		AboutText += _("[Image Info]\n")
		AboutText += "%s: %s %s\n" % (_("Model"), MACHINEBRAND, MACHINENAME)
		AboutText += _("Backup Date: %s\n") % strftime("%Y-%m-%d", localtime(self.START))

		if exists("/proc/stb/info/chipset"):
			AboutText += _("Chipset: BCM%s") % getChipSetString().lower().replace("\n", "").replace("bcm", "") + "\n"

		cpu = getCPUInfoString()
		AboutText += "%s: %s\n" % (_("CPU"), cpu[0])
		AboutText += "%s: %s/%s\n" % (_("CPU speed/cores"), cpu[1], cpu[2])
		AboutText += "%s: %s\n" % (_("CPU brand"), getCPUBrand())
		socFamily = BoxInfo.getItem("socfamily")
		if socFamily:
			AboutText += "%s: %s\n" % (_("SoC family"), socFamily)

		AboutText += _("Version: %s") % self.DISTROVERSION + "\n"
		AboutText += _("Build: %s") % self.IMAGEBUILD + "\n"
		if self.KERNEL:  # TODO get slot info
			AboutText += "%s: %s\n" % (_("Kernel version"), self.KERNEL)

		if self.DRIVERSDATE:
			driversdate = str(self.DRIVERSDATE)
			year = driversdate[0:4]
			month = driversdate[4:6]
			day = driversdate[6:8]
			driversdate = "-".join((year, month, day))
			AboutText += "%s:\t%s\n" % (_("Drivers version"), driversdate)

		AboutText += "%s\t%s\n\n" % (_("Last update"), self.IMGREVISION)

		AboutText += _("[Enigma2 Settings]\n")
		for setting in settings:
			AboutText += "%s\n" % setting
		AboutText += _("\n\n[User - bouquets (TV)]\n")
		if bouquetsTV:
			for bouquet in bouquetsTV:
				AboutText += bouquet
		else:
			AboutText += _("Error reading bouquets.tv")
		AboutText += _("\n[User - bouquets (RADIO)]\n")
		if bouquetsRadio:
			for bouquet in bouquetsRadio:
				AboutText += bouquet
		else:
			AboutText += _("Error reading bouquets.radio")

		if not isNotCurrent:
			AboutText += _("\n[Installed Plugins]\n")
			AboutText += getoutput("opkg list_installed | grep enigma2-plugin-")  # TODO get slot info
		return AboutText

	def getImageData(self, imageDir, isNotCurrent):
		infoFile = pathjoin(imageDir, "usr/lib/enigma.info")
		info = {}
		enigmaInfo = False
		if isNotCurrent:
			if isfile(infoFile):
				info = MultiBoot.readSlotInfo(infoFile)
				enigmaInfo = True
			elif isfile(pathjoin(imageDir, "usr/bin/enigma2")):
				info = MultiBoot.deriveSlotInfo(imageDir)

		settingsFile = fileReadLines(pathjoin(imageDir, "etc/enigma2/settings"), source=MODULE_NAME) or []
		bouquetsTV = []
		bouquetsRadio = []
		lines = fileReadLines(pathjoin(imageDir, "etc/enigma2/bouquets.tv"), source=MODULE_NAME)
		if lines:
			for line in lines:
				if line.startswith("#SERVICE "):
					bouqet = line.split()
					if len(bouqet) > 3:
						bouqet[3] = bouqet[3].replace("\"", "")
						try:
							with open("/etc/enigma2/%s" % bouqet[3], "r") as fd:
								userbouqet = fd.readline()
							bouquetsTV.append(userbouqet.replace("#NAME ", ""))
						except UnicodeDecodeError:
							bouquetsTV.append("Error: %s / not UTF-8" % bouqet[3])
						except OSError:
							pass

		lines = fileReadLines(pathjoin(imageDir, "etc/enigma2/bouquets.radio"), source=MODULE_NAME)
		if lines:
			for line in lines:
				if line.startswith("#SERVICE "):
					bouqet = line.split()
					if len(bouqet) > 3:
						bouqet[3] = bouqet[3].replace("\"", "")
						try:
							with open("/etc/enigma2/%s" % bouqet[3], "r") as fd:
								userbouqet = fd.readline()
							bouquetsRadio.append(userbouqet.replace("#NAME ", ""))
						except UnicodeDecodeError:
							bouquetsRadio.append("Error: %s / not UTF-8" % bouqet[3])
						except OSError:
							pass

		return (enigmaInfo, info, settingsFile, bouquetsTV, bouquetsRadio)

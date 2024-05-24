from datetime import timedelta
from os import chmod, listdir, makedirs, remove, system
from os.path import exists, isdir, isfile, join
from subprocess import getoutput
from time import localtime, strftime, time

from Components.About import getCPUBrand, getCPUInfoString
from Components.ActionMap import ActionMap
from Components.ChoiceList import ChoiceList, ChoiceEntryComponent
from Components.config import config, configfile
from Components.Harddisk import Freespace, getFolderSize
from Components.Sources.StaticText import StaticText
from Components.SystemInfo import BoxInfo
from Screens.Console import Console
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Tools.BoundFunction import boundFunction
from Tools.MultiBoot import MultiBoot
from Tools.Directories import fileReadLines, fileWriteLine, fileWriteLines

MODULE_NAME = __name__.split(".")[-1]

DISTRO = BoxInfo.getItem("distro")
DISPLAYDISTRO = BoxInfo.getItem("displaydistro")
DISTROVERSION = BoxInfo.getItem("imageversion")
MACHINEBRAND = BoxInfo.getItem("displaybrand")
MACHINENAME = BoxInfo.getItem("displaymodel")

USEP = "_________________________________________________"


class ImageBackup(Screen):

	skin = """
	<screen name="Image Backup" position="center,center" size="750,900" flags="wfNoBorder" backgroundColor="transparent" resolution="1280,720">
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
			"up": self["config"].goLineUp,
			"down": self["config"].goLineDown,
			"left": self["config"].goLineUp,
			"right": self["config"].goLineDown,
			"menu": boundFunction(self.close, True),
		}, prio=0)
		# imagedict = []
		# self.getImageList = None
		# self.startit()
		self.runScript = "/tmp/imagebackup.sh"
		self.onLayoutFinish.append(self.layoutFinished)
		print("[ImageBackup] DEBUG: Now running '__init__'.")
		self.callLater(self.startit)

	def layoutFinished(self):
		self["config"].enableAutoNavigation(False)

	def startit(self):
		MultiBoot.getSlotImageList(self.ImageList)

	def ImageList(self, imagedict):
		self.saveImageList = imagedict
		imageList = []
		currentImageSlot = MultiBoot.getCurrentSlotCode()
		rootSlot = BoxInfo.getItem("HasKexecMultiboot") and currentImageSlot == "R"
		currentImageSlot = int(currentImageSlot) if currentImageSlot and currentImageSlot.isdecimal() else 1
		print(f"[Image Backup] Current Image Slot {currentImageSlot}, Imagelist {imagedict}, rootSlot={rootSlot}")
		if imagedict:
			for slotCode in sorted(imagedict.keys()):
				if imagedict[slotCode]["status"] == "active":
					slotText = f"{slotCode} {"eMMC" if "mmcblk" in imagedict[slotCode]["device"] else "USB"}"
					if slotCode == "1" and currentImageSlot == 1 and BoxInfo.getItem("canRecovery"):
						imageList.append(ChoiceEntryComponent("", (_("Slot %s: %s as USB Recovery") % (slotText, imagedict[slotCode]["imagename"]), slotCode, True)))
					if rootSlot:
						imageList.append(ChoiceEntryComponent("", ((_("Slot %s: %s")) % (slotText, imagedict[slotCode]["imagename"]), slotCode, False)))
					else:
						imageList.append(ChoiceEntryComponent("", ((_("Slot %s: %s (Current image)") if slotCode == str(currentImageSlot) else _("Slot %s: %s")) % (slotText, imagedict[slotCode]["imagename"]), slotCode, False)))
			if rootSlot:
				imageList.append(ChoiceEntryComponent("", (_("Slot R: Root Slot Full Backup (Current image)"), "R", False)))
		else:
			if BoxInfo.getItem("canRecovery"):
				imageList.append(ChoiceEntryComponent("", (_("Internal flash: %s %s as USB Recovery") % (DISTRO, DISTROVERSION), "slotCode", True)))
			imageList.append(ChoiceEntryComponent("", (_("Internal flash:  %s %s ") % (DISTRO, DISTROVERSION), "slotCode", False)))
		self["config"].setList(imageList)
		index = 0
		for index, item in enumerate(imageList):
			if item[0][1] == str(currentImageSlot):
				break
		self["config"].moveToIndex(index)

	def start(self):
		self.currentSelected = self["config"].l.getCurrentSelection()
		title = _("Please select a backup destination")
		choices = []
		if self.currentSelected[0][1] != "Queued":
			for media in [f"/media/{x}" for x in listdir("/media")] + ([f"/media/net/{x}" for x in listdir("/media/net")] if isdir("/media/net") else []):
				if Freespace(media) > 300000:
					choices.append((_("Backup to destination: %s") % (media), self.currentSelected[0][1], media, self.currentSelected[0][2]))
			choices.append((_("No, do not backup a image"), False))
			self.session.openWithCallback(self.doFullBackup, ChoiceBox, title=title, list=choices)

	def doFullBackup(self, answer):
		if answer is not None and answer[1]:
			self.save_shutdownOK = config.usage.shutdownOK.value
			config.usage.shutdownOK.setValue(True)
			config.usage.shutdownOK.save()
			configfile.save()
			fileWriteLine("/proc/sys/vm/drop_caches", "3")  # Clear Memory
			self.RECOVERY = answer[3]
			self.DIRECTORY = f"{answer[2]}/images"
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
			self.MODEL = BoxInfo.getItem("BoxName")
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
			self.HasKexecMultiboot = BoxInfo.getItem("HasKexecMultiboot")

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
				if BoxInfo.getItem("HasKexecMultiboot") and self.SLOT == "R":
					self.MTDKERNEL = bootSlots[self.SLOT]["kernel"]
					self.ROOTFSSUBDIR = "none"
				else:
					self.MTDKERNEL = bootSlots[self.SLOT]["kernel"].split("/")[2]
				if self.hasMultiBootMDT:
					self.MTDROOTFS = bootSlots[self.SLOT]["device"]
				else:
					self.MTDROOTFS = bootSlots[self.SLOT]["device"].split("/")[2]
			else:
				self.MTDKERNEL = BoxInfo.getItem("mtdkernel")
				self.MTDROOTFS = BoxInfo.getItem("mtdrootfs")

			print(f"[Image Backup] BOX MACHINEBUILD = >{self.MACHINEBUILD}<")
			print(f"[Image Backup] BOX MACHINENAME = >{MACHINENAME}<")
			print(f"[Image Backup] BOX MACHINEBRAND = >{MACHINEBRAND}<")
			print(f"[Image Backup] BOX MODEL = >{self.MODEL}<")
			print(f"[Image Backup] OEM MODEL = >{self.OEM}<")
			print(f"[Image Backup] IMAGEFOLDER = >{self.IMAGEFOLDER}<")
			print(f"[Image Backup] UBINIZE = >{self.UBINIZE_ARGS}<")
			print(f"[Image Backup] MKUBIFS = >{self.MKUBIFS_ARGS}<")
			print(f"[Image Backup] MTDBOOT = >{self.MTDBOOT}<")
			print(f"[Image Backup] MTDKERNEL = >{self.MTDKERNEL}<")
			print(f"[Image Backup] MTDROOTFS = >{self.MTDROOTFS}<")
			print(f"[Image Backup] ROOTFSBIN = >{self.ROOTFSBIN}<")
			print(f"[Image Backup] KERNELBIN = >{self.KERNELBIN}<")
			print(f"[Image Backup] ROOTFSSUBDIR = >{self.ROOTFSSUBDIR}<")
			print(f"[Image Backup] ROOTFSTYPE = >{self.ROOTFSTYPE}<")
			print(f"[Image Backup] hasMultiBootMDT = >{self.hasMultiBootMDT}<")
			print(f"[Image Backup] EMMCIMG = >{self.EMMCIMG}<")
			print(f"[Image Backup] MTDBOOT = >{self.MTDBOOT}<")
			print(f"[Image Backup] USB RECOVERY = >{self.RECOVERY}< ")
			print(f"[Image Backup] DESTINATION = >{self.DIRECTORY}< ")
			print(f"[Image Backup] SLOT = >{self.SLOT}< ")
			print(f"[Image Backup] HasKexecMultiboot = >{self.HasKexecMultiboot}< ")
			print(f"[Image Backup] canMultiBoot = >{MultiBoot.canMultiBoot()}< ")

			isNotCurrent = MultiBoot.getCurrentSlotCode() != answer[1]

			print(f"[Image Backup] isNotCurrent = >{isNotCurrent}< ")

			if self.RECOVERY and not isNotCurrent:
				print(f"[Image Backup] IMAGEDISTRO = >{self.DISTRO}<")
				print(f"[Image Backup] DISPLAYDISTRO = >{self.DISPLAYDISTRO}<")
				print(f"[Image Backup] DISTROVERSION = >{self.DISTROVERSION}<")
				print(f"[Image Backup] IMAGEBUILD = >{self.IMAGEBUILD}<")
				print(f"[Image Backup] IMGVERSION = >{self.IMGVERSION}<")
				print(f"[Image Backup] IMGREVISION = >{self.IMGREVISION}<")
				print(f"[Image Backup] DRIVERSDATE = >{self.DRIVERSDATE}<")
				print(f"[Image Backup] IMAGEDEVBUILD = >{self.IMAGEDEVBUILD}<")
				print(f"[Image Backup] IMAGETYPE = >{self.IMAGETYPE}<")

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
			self.WORKDIR = f"{self.DIRECTORY}/bi"

			self.SHOWNAME = f"{MACHINEBRAND} {self.MODEL}"
			self.MAINDEST = f"{self.DIRECTORY}/build_{self.MODEL}/{self.IMAGEFOLDER}"
			self.MAINDESTROOT = f"{self.DIRECTORY}/build_{self.MODEL}"

			## PREPARING THE BUILDING ENVIRONMENT
			system(f"rm -rf {self.WORKDIR}")
			self.backuproot = "/tmp/bi/RootSubdir" if self.ROOTFSSUBDIR != "none" else "/tmp/bi/root"
			if not exists(self.WORKDIR):
				makedirs(self.WORKDIR)
			if not exists(self.backuproot):
				makedirs(self.backuproot)
			system("sync")
			if MultiBoot.canMultiBoot():
				mountcmd = f"/dev/{self.MTDROOTFS} {self.backuproot}"
				if self.ROOTFSSUBDIR != "none":
					if self.hasMultiBootMDT:
						mountcmd = f"-t ubifs {self.MTDROOTFS} {self.backuproot}"
					self.backuproot = f"{self.backuproot}/{self.ROOTFSSUBDIR}"
			else:
				mountcmd = f"--bind / {self.backuproot}"
			system(f"mount {mountcmd}")

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
						self.DISTROVERSION = f"{self.DISTROVERSION}.{self.IMAGEDEVBUILD}"

					print(f"[Image Backup] IMAGEDISTRO = >{self.DISTRO}<")
					print(f"[Image Backup] DISPLAYDISTRO = >{self.DISPLAYDISTRO}<")
					print(f"[Image Backup] DISTROVERSION = >{self.DISTROVERSION}<")
					print(f"[Image Backup] IMAGEBUILD = >{self.IMAGEBUILD}<")
					print(f"[Image Backup] IMGVERSION = >{self.IMGVERSION}<")
					print(f"[Image Backup] IMGREVISION = >{self.IMGREVISION}<")
					print(f"[Image Backup] DRIVERSDATE = >{self.DRIVERSDATE}<")
					print(f"[Image Backup] IMAGEDEVBUILD = >{self.IMAGEDEVBUILD}<")
					print(f"[Image Backup] IMAGETYPE = >{self.IMAGETYPE}<")

				self.IMAGEVERSION = self.imageInfo(settingsFile, bouquetsTV, bouquetsRadio, isNotCurrent)
			else:
				self.IMAGEVERSION = ""  # TODO TEST Recovery image

			self.message = "echo -e '\n"
			if MACHINEBRAND.startswith("A") or MACHINEBRAND.startswith("E") or MACHINEBRAND.startswith("I") or MACHINEBRAND.startswith("O") or MACHINEBRAND.startswith("U") or MACHINEBRAND.startswith("Xt"):
				self.message += (_("Back-up Tool for an %s\n") % self.SHOWNAME).upper()
			else:
				self.message += (_("Back-up Tool for a %s\n") % self.SHOWNAME).upper()
			self.message += _("Version %s %s") % (self.DISTRO, self.DISTROVERSION) + "\n"
			self.message += f"{USEP}\n\n"
			self.message += _("Please be patient, a backup will now be made,\n")
			self.message += _("because of the used file system the back-up\n")
			self.message += _("will take about 1-15 minutes for this system\n")
			self.message += f"{USEP}\n\n"
			if self.RECOVERY:
				self.message += _("Backup Mode: USB Recovery\n")
			else:
				self.message += _("Backup Mode: Flash Online\n")
			self.message += f"{USEP}\n"
			self.message += "'"

			cmd1 = None
			cmd2 = None
			cmd3 = None
			if "jffs2" in self.ROOTFSTYPE.split():
				cmd1 = f"{self.MKFS_JFFS2} --root={self.backuproot} --faketime --output={self.WORKDIR}/root.jffs2 {self.MKUBIFS_ARGS}"
			elif "ubi" in self.ROOTFSTYPE.split():
				lines = []
				lines.append("[ubifs]")
				lines.append("mode=ubi")
				lines.append(f"image={self.WORKDIR}/root.ubi")
				lines.append(f"vol_id=0")
				lines.append(f"vol_type=dynamic")
				lines.append(f"vol_name=rootfs")
				lines.append(f"vol_flags=autoresize")
				fileWriteLines(f"{self.WORKDIR}/ubinize.cfg", lines, source=MODULE_NAME)
				fileWriteLine(f"{self.WORKDIR}/root.ubi", "", source=MODULE_NAME)
				cmd1 = f"{self.MKFS_UBI} -r {self.backuproot} -o {self.WORKDIR}/root.ubi {self.MKUBIFS_ARGS}"
				cmd2 = f"{self.UBINIZE} -o {self.WORKDIR}/root.ubifs {self.UBINIZE_ARGS} {self.WORKDIR}/ubinize.cfg"
			elif not self.RECOVERY:
				cmd1 = f"{self.MKFS_TAR} -cf {self.WORKDIR}/rootfs.tar -C {self.backuproot} --exclude ./boot/kernel.img --exclude ./var/nmbd --exclude ./.resizerootfs --exclude ./.resize-rootfs --exclude ./.resize-linuxrootfs --exclude ./.resize-userdata --exclude ./var/lib/samba/private/msg.sock --exclude ./var/lib/samba/msg.sock/* --exclude ./run/avahi-daemon/socket --exclude ./run/chrony/chronyd.sock ."
				cmd2 = "sync"
				cmd3 = f"{self.BZIP2} {self.WORKDIR}/rootfs.tar"

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
				cmdlist.append(f"dd if=/dev/mmcblk0p1 of={self.WORKDIR}/boot.bin")
				cmdlist.append(self.makeEchoCreate("rescue dump"))
				cmdlist.append(f"dd if=/dev/mmcblk0p3 of={self.WORKDIR}/rescue.bin")

			if self.MACHINEBUILD in ("h9", "i55plus"):
				for index, value in enumerate(["fastboot", "bootargs", "baseparam", "pq_param", "logo"]):
					cmdlist.append(self.makeEchoCreate(f"{value} dump"))
					cmdlist.append(f"dd if=/dev/mtd{index} of={self.WORKDIR}/{value}.bin")

			if self.EMMCIMG == "usb_update.bin" and self.RECOVERY:
				SEEK_CONT = int((getFolderSize(self.backuproot) / 1024) + 100000)

				cmdlist.append(self.makeEchoCreate("fastboot dump"))
				cmdlist.append(self.makeCopyBinFile("fastboot", self.WORKDIR))
				#cmdlist.append("dd if=/dev/mmcblk0p1 of=%s/fastboot.bin" % self.WORKDIR)

				cmdlist.append(self.makeEchoCreate("bootargs dump"))
				cmdlist.append(self.makeCopyBinFile("bootargs", self.WORKDIR))
				#cmdlist.append("dd if=/dev/mmcblk0p2 of=%s/bootargs.bin" % self.WORKDIR)

				cmdlist.append(self.makeEchoCreate("boot dump"))
				cmdlist.append(f"dd if=/dev/mmcblk0p3 of={self.WORKDIR}/boot.img")

				cmdlist.append(self.makeEchoCreate("baseparam dump"))
				#cmdlist.append("cp -f /usr/share/bootargs.bin %s/baseparam.img" %(self.WORKDIR))
				cmdlist.append(f"dd if=/dev/mmcblk0p4 of={self.WORKDIR}/baseparam.img")

				cmdlist.append(self.makeEchoCreate("pq_param dump"))
				#cmdlist.append("cp -f /usr/share/bootargs.bin %s/pq_param.bin" %(self.WORKDIR))
				cmdlist.append(f"dd if=/dev/mmcblk0p5 of={self.WORKDIR}/pq_param.bin")

				cmdlist.append(self.makeEchoCreate("logo dump"))
				cmdlist.append(f"dd if=/dev/mmcblk0p6 of={self.WORKDIR}/logo.img")

				cmdlist.append(self.makeEchoCreate("deviceinfo dump"))
				#cmdlist.append("cp -f /usr/share/bootargs.bin %s/deviceinfo.bin" %(self.WORKDIR))
				cmdlist.append(f"dd if=/dev/mmcblk0p7 of={self.WORKDIR}/deviceinfo.bin")

				cmdlist.append(self.makeEchoCreate("apploader dump"))
				cmdlist.append(self.makeCopyBinFile("apploader", self.WORKDIR))
				#cmdlist.append("dd if=/dev/mmcblk0p10 of=%s/apploader.bin" % self.WORKDIR)

				cmdlist.append(self.makeEchoCreate("rootfs dump"))
				cmdlist.append(f"dd if=/dev/zero of={self.WORKDIR}/rootfs.ext4 seek={SEEK_CONT} count=60 bs=1024")
				cmdlist.append(f"mkfs.ext4 -F -i 4096 {self.WORKDIR}/rootfs.ext4")
				cmdlist.append(f"mkdir -p {self.WORKDIR}/userdata")
				cmdlist.append(f"mount {self.WORKDIR}/rootfs.ext4 {self.WORKDIR}/userdata")
				for rootindex in range(1, 5):
					cmdlist.append(f"mkdir -p {self.WORKDIR}/userdata/linuxrootfs{rootindex}")

				cmdlist.append(f"rsync -aAX {self.backuproot}/ {self.WORKDIR}/userdata/linuxrootfs1/")
				cmdlist.append(f"umount {self.WORKDIR}/userdata")

			cmdlist.append(self.makeEchoCreate("kerneldump"))
			if MultiBoot.canMultiBoot() or self.MTDKERNEL.startswith("mmcblk0") or self.MACHINEBUILD in ("h8", "hzero"):
				if BoxInfo.getItem("HasKexecMultiboot") or BoxInfo.getItem("HasGPT"):
					cmdlist.append(f"cp /{self.MTDKERNEL} {self.WORKDIR}/{self.KERNELBIN}")
				else:
					cmdlist.append(f"dd if=/dev/{self.MTDKERNEL} of={self.WORKDIR}/{self.KERNELBIN}")
			else:
				cmdlist.append(f"nanddump -a -f {self.WORKDIR}/vmlinux.gz /dev/{self.MTDKERNEL}")

			if self.EMMCIMG == "disk.img" and self.RECOVERY:
				EMMC_IMAGE = f"{self.WORKDIR}/{self.EMMCIMG}"
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
				cmdlist.append(f"dd if=/dev/zero of={EMMC_IMAGE} bs={BLOCK_SIZE} count=0 seek={EMMC_IMAGE_SEEK}")
				cmdlist.append(f"parted -s {EMMC_IMAGE} mklabel gpt")
				PARTED_END_BOOT = int(IMAGE_ROOTFS_ALIGNMENT) + int(BOOT_PARTITION_SIZE)
				cmdlist.append(f"parted -s {EMMC_IMAGE} unit KiB mkpart boot fat16 {IMAGE_ROOTFS_ALIGNMENT} {PARTED_END_BOOT}")
				PARTED_END_KERNEL1 = int(KERNEL_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
				cmdlist.append(f"parted -s {EMMC_IMAGE} unit KiB mkpart linuxkernel {KERNEL_PARTITION_OFFSET} {PARTED_END_KERNEL1}")
				PARTED_END_ROOTFS1 = int(ROOTFS_PARTITION_OFFSET) + int(ROOTFS_PARTITION_SIZE)
				cmdlist.append(f"parted -s {EMMC_IMAGE} unit KiB mkpart linuxrootfs ext4 {ROOTFS_PARTITION_OFFSET} {PARTED_END_ROOTFS1}")
				PARTED_END_KERNEL2 = int(SECOND_KERNEL_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
				cmdlist.append(f"parted -s {EMMC_IMAGE} unit KiB mkpart linuxkernel2 {SECOND_KERNEL_PARTITION_OFFSET} {PARTED_END_KERNEL2}")
				PARTED_END_KERNEL3 = int(THRID_KERNEL_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
				cmdlist.append(f"parted -s {EMMC_IMAGE} unit KiB mkpart linuxkernel3 {THRID_KERNEL_PARTITION_OFFSET} {PARTED_END_KERNEL3}")
				PARTED_END_KERNEL4 = int(FOURTH_KERNEL_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
				cmdlist.append(f"parted -s {EMMC_IMAGE} unit KiB mkpart linuxkernel4 {FOURTH_KERNEL_PARTITION_OFFSET} {PARTED_END_KERNEL4}")
				rd = open("/proc/swaps").read()
				if "mmcblk0p7" in rd:
					SWAP_PARTITION_OFFSET = int(FOURTH_KERNEL_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
					SWAP_PARTITION_SIZE = int(262144)
					MULTI_ROOTFS_PARTITION_OFFSET = int(SWAP_PARTITION_OFFSET) + int(SWAP_PARTITION_SIZE)
					cmdlist.append(f"parted -s {EMMC_IMAGE} unit KiB mkpart swap linux-swap {SWAP_PARTITION_OFFSET} {SWAP_PARTITION_OFFSET + SWAP_PARTITION_SIZE}")
					cmdlist.append(f"parted -s {EMMC_IMAGE} unit KiB mkpart userdata ext4 {MULTI_ROOTFS_PARTITION_OFFSET} 100%")
				else:
					cmdlist.append(f"parted -s {EMMC_IMAGE} unit KiB mkpart userdata ext4 {MULTI_ROOTFS_PARTITION_OFFSET} 100%")
				BOOT_IMAGE_SEEK = int(IMAGE_ROOTFS_ALIGNMENT) * int(BLOCK_SECTOR)
				cmdlist.append(f"dd if=/dev/{self.MTDBOOT} of={EMMC_IMAGE} seek={BOOT_IMAGE_SEEK}")
				KERNAL_IMAGE_SEEK = int(KERNEL_PARTITION_OFFSET) * int(BLOCK_SECTOR)
				cmdlist.append(f"dd if=/dev/{self.MTDKERNEL} of={EMMC_IMAGE} seek={KERNAL_IMAGE_SEEK}")
				ROOTFS_IMAGE_SEEK = int(ROOTFS_PARTITION_OFFSET) * int(BLOCK_SECTOR)
				cmdlist.append(f"dd if=/dev/{self.MTDROOTFS} of={EMMC_IMAGE} seek={ROOTFS_IMAGE_SEEK} ")
			elif self.EMMCIMG == "emmc.img" and self.RECOVERY:
				EMMC_IMAGE = f"{self.WORKDIR}/{self.EMMCIMG}"
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
				cmdlist.append(f"dd if=/dev/zero of={EMMC_IMAGE} bs=1 count=0 seek={EMMC_IMAGE_SEEK}")
				cmdlist.append(f"parted -s {EMMC_IMAGE} mklabel gpt")
				PARTED_END_BOOT = int(IMAGE_ROOTFS_ALIGNMENT) + int(BOOT_PARTITION_SIZE)
				cmdlist.append(f"parted -s {EMMC_IMAGE} unit KiB mkpart boot fat16 {IMAGE_ROOTFS_ALIGNMENT} {PARTED_END_BOOT}")
				cmdlist.append(f"parted -s {EMMC_IMAGE} set 1 boot on")
				PARTED_END_KERNEL1 = int(KERNEL1_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
				cmdlist.append(f"parted -s {EMMC_IMAGE} unit KiB mkpart kernel1 {KERNEL1_PARTITION_OFFSET} {PARTED_END_KERNEL1}")
				PARTED_END_ROOTFS1 = int(ROOTFS1_PARTITION_OFFSET) + int(ROOTFS_PARTITION_SIZE)
				cmdlist.append(f"parted -s {EMMC_IMAGE} unit KiB mkpart rootfs1 ext4 {ROOTFS1_PARTITION_OFFSET} {PARTED_END_ROOTFS1}")
				PARTED_END_KERNEL2 = int(KERNEL2_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
				cmdlist.append(f"parted -s {EMMC_IMAGE} unit KiB mkpart kernel2 {KERNEL2_PARTITION_OFFSET} {PARTED_END_KERNEL2}")
				PARTED_END_ROOTFS2 = int(ROOTFS2_PARTITION_OFFSET) + int(ROOTFS_PARTITION_SIZE)
				cmdlist.append(f"parted -s {EMMC_IMAGE} unit KiB mkpart rootfs2 ext4 {ROOTFS2_PARTITION_OFFSET} {PARTED_END_ROOTFS2}")
				PARTED_END_KERNEL3 = int(KERNEL3_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
				cmdlist.append(f"parted -s {EMMC_IMAGE} unit KiB mkpart kernel3 {KERNEL3_PARTITION_OFFSET} {PARTED_END_KERNEL3}")
				PARTED_END_ROOTFS3 = int(ROOTFS3_PARTITION_OFFSET) + int(ROOTFS_PARTITION_SIZE)
				cmdlist.append(f"parted -s {EMMC_IMAGE} unit KiB mkpart rootfs3 ext4 {ROOTFS3_PARTITION_OFFSET} {PARTED_END_ROOTFS3}")
				PARTED_END_KERNEL4 = int(KERNEL4_PARTITION_OFFSET) + int(KERNEL_PARTITION_SIZE)
				cmdlist.append(f"parted -s {EMMC_IMAGE} unit KiB mkpart kernel4 {KERNEL4_PARTITION_OFFSET} {PARTED_END_KERNEL4}")
				PARTED_END_ROOTFS4 = int(ROOTFS4_PARTITION_OFFSET) + int(ROOTFS_PARTITION_SIZE)
				cmdlist.append(f"parted -s {EMMC_IMAGE} unit KiB mkpart rootfs4 ext4 {ROOTFS4_PARTITION_OFFSET} {PARTED_END_ROOTFS4}")
				BOOT_IMAGE_SEEK = int(IMAGE_ROOTFS_ALIGNMENT) * int(BLOCK_SECTOR)
				cmdlist.append(f"dd if=/dev/{self.MTDBOOT} of={EMMC_IMAGE} seek={BOOT_IMAGE_SEEK}")
				KERNAL_IMAGE_SEEK = int(KERNEL1_PARTITION_OFFSET) * int(BLOCK_SECTOR)
				cmdlist.append(f"dd if=/dev/{self.MTDKERNEL} of={EMMC_IMAGE} seek={KERNAL_IMAGE_SEEK}")
				ROOTFS_IMAGE_SEEK = int(ROOTFS1_PARTITION_OFFSET) * int(BLOCK_SECTOR)
				cmdlist.append(f"dd if=/dev/{self.MTDROOTFS} of={EMMC_IMAGE} seek={ROOTFS_IMAGE_SEEK} ")
			elif self.EMMCIMG == "usb_update.bin" and self.RECOVERY:
				cmdlist.append(self.makeEcho(_("Create: Recovery Fullbackup %s") % (self.EMMCIMG)))
				f = open(f"{self.WORKDIR}/emmc_partitions.xml", "w")
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
				cmdlist.append(f"mkupdate -s 00000003-00000001-01010101 -f {self.WORKDIR}/emmc_partitions.xml -d {self.WORKDIR}/{self.EMMCIMG}")

			fileWriteLines(self.runScript, cmdlist, source=MODULE_NAME)
			chmod(self.runScript, 0o755)
			cmdlist = [self.runScript]
			self.session.openWithCallback(self.doFullBackupCB, Console, title=self.TITLE, cmdlist=cmdlist, closeOnSuccess=True)
		else:
			self.close()

	def makeEchoCreate(self, txt):
		return self.makeEcho(f"{_("Create:")} {txt}")

	def makeEcho(self, txt):
		return f"echo \"{txt}\""

	def makeEchoLine(self, nocr=False):
		return "echo \"%s%s\"" % (USEP, "" if nocr else "\n")

	def makeSpace(self):
		return "echo \" \""

	def makeCopyBinFile(self, fileName, destination):
		return f"cp -f /usr/share/{fileName}.bin {destination}/{fileName}.bin"

	def doFullBackupCB(self):
		cmdlist = []
		cmdlist.append(self.message)
		cmdlist.append(self.makeEcho(_("Almost there... ")))
		cmdlist.append(self.makeEcho(_("Now building the Backup Image")))

		config.usage.shutdownOK.setValue(self.save_shutdownOK)
		config.usage.shutdownOK.save()
		configfile.save()

		def initDestination(destination):
			system(f"rm -rf {destination}")
			if not exists(destination):
				makedirs(destination)
			fileWriteLine(f"{destination}/imageversion", self.IMAGEVERSION, source=MODULE_NAME)

		if self.EMMCIMG == "usb_update.bin" and self.RECOVERY:
			initDestination(self.MAINDESTROOT)
		else:
			initDestination(self.MAINDEST)
			if not self.RECOVERY:
				if self.ROOTFSBIN in ("rootfs.tar.bz2", "rootfs-two.tar.bz2", "rootfs-one.tar.bz2"):
					if self.MACHINEBUILD in ("dreamone", "dreamtwo"):
						system(f"mv {self.WORKDIR}/rootfs.tar.bz2 {self.MAINDEST}/{self.ROOTFSBIN}")
					else:
						system(f"mv {self.WORKDIR}/{self.ROOTFSBIN} {self.MAINDEST}/{self.ROOTFSBIN}")
				else:
					system(f"mv {self.WORKDIR}/root.ubifs {self.MAINDEST}/{self.ROOTFSBIN}")
				if self.MACHINEBUILD in ("dm800se", "dm500hd", "dreamone", "dreamtwo"):
					system(f"touch {self.MAINDEST}/{self.KERNELBIN}")
				elif MultiBoot.canMultiBoot() or self.MTDKERNEL.startswith("mmcblk0") or self.MACHINEBUILD in ("h8", "hzero"):
					system(f"mv {self.WORKDIR}/{self.KERNELBIN} {self.MAINDEST}/{self.KERNELBIN}")
				else:
					system(f"mv {self.WORKDIR}/vmlinux.gz {self.MAINDEST}/{self.KERNELBIN}")

		if self.RECOVERY:
			if self.EMMCIMG == "usb_update.bin":
				system(f"mv {self.WORKDIR}/{self.EMMCIMG} {self.MAINDESTROOT}/{self.EMMCIMG}")
				cmdlist.append(self.makeCopyBinFile("fastboot", self.MAINDESTROOT))
				cmdlist.append(self.makeCopyBinFile("bootargs", self.MAINDESTROOT))
				cmdlist.append(self.makeCopyBinFile("apploader", self.MAINDESTROOT))
			else:
				system(f"mv {self.WORKDIR}/{self.EMMCIMG} {self.MAINDEST}/{self.EMMCIMG}")
			if self.EMMCIMG == "emmc.img":
				cmdlist.append(f'echo "rename this file to "force" to force an update without confirmation" > {self.MAINDEST}/noforce')
		elif self.MODEL in ("vuultimo4k", "vusolo4k", "vuduo2", "vusolo2", "vusolo", "vuduo", "vuultimo", "vuuno"):
			cmdlist.append(f'echo "This file forces a reboot after the update." > {self.MAINDEST}/reboot.update')
		elif self.MODEL in ("vuzero", "vusolose", "vuuno4k", "vuzero4k"):
			cmdlist.append(f'echo "This file forces the update." > {self.MAINDEST}/force.update')
		elif self.MODEL in ("viperslim", "evoslimse", "evoslimt2c", "novaip", "zgemmai55", "sf98", "xpeedlxpro", "evoslim", "vipert2c"):
			cmdlist.append(f'echo "This file forces the update." > {self.MAINDEST}/force')
		elif self.ROOTFSSUBDIR != "none":
			cmdlist.append(f'echo "Rename the unforce_{self.MACHINEBUILD}.txt to force_{self.MACHINEBUILD}.txt and move it to the root of your usb-stick" > {self.MAINDEST}/force_{self.MACHINEBUILD}_READ.ME')
			cmdlist.append(f'echo "When you enter the recovery menu then it will force to install the image in the linux1 selection" >> {self.MAINDEST}/force_{self.MACHINEBUILD}_READ.ME')
		else:
			cmdlist.append(f'echo "rename this file to "force" to force an update without confirmation" > {self.MAINDEST}/noforce')

		if self.MODEL in ("gbquad4k", "gbue4k", "gbx34k"):
			system(f"mv {self.WORKDIR}/boot.bin {self.MAINDEST}/boot.bin")
			system(f"mv {self.WORKDIR}/rescue.bin {self.MAINDEST}/rescue.bin")
			system(f"cp -f /usr/share/gpt.bin {self.MAINDEST}/gpt.bin")

		if self.MACHINEBUILD in ("h9", "i55plus"):
			system(f"mv {self.WORKDIR}/fastboot.bin {self.MAINDEST}/fastboot.bin")
			system(f"mv {self.WORKDIR}/pq_param.bin {self.MAINDEST}/pq_param.bin")
			system(f"mv {self.WORKDIR}/bootargs.bin {self.MAINDEST}/bootargs.bin")
			system(f"mv {self.WORKDIR}/baseparam.bin {self.MAINDEST}/baseparam.bin")
			system(f"mv {self.WORKDIR}/logo.bin {self.MAINDEST}/logo.bin")

		if self.MODEL in ("gbquad", "gbquadplus", "gb800ue", "gb800ueplus", "gbultraue", "gbultraueh", "twinboxlcd", "twinboxlcdci", "singleboxlcd", "sf208", "sf228"):
			lcdwaitkey = "/usr/share/lcdwaitkey.bin"
			lcdwarning = "/usr/share/lcdwarning.bin"
			if isfile(lcdwaitkey):
				system(f"cp {lcdwaitkey} {self.MAINDEST}/lcdwaitkey.bin")
			if isfile(lcdwarning):
				system(f"cp {lcdwarning} {self.MAINDEST}/lcdwarning.bin")
		if self.MODEL in ("e4hdultra", "protek4k"):
			lcdwarning = "/usr/share/lcdflashing.bmp"
			if isfile(lcdwarning):
				system(f"cp {lcdwarning} {self.MAINDEST}/lcdflashing.bmp")
		if self.MODEL == "gb800solo":
			f = open(f"{self.MAINDESTROOT}/burn.bat", "w")
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

		cmdlist.append("echo 3 > /proc/sys/vm/drop_caches")  # Clear Memory
		cmdlist.append(f"7za a -r -bt -bd {self.DIRECTORY}/{self.DISTRO}-{self.DISTROVERSION}-{self.MODEL}-backup-{self.DATE}_{iname}.zip {self.MAINDESTROOT}/*")
		cmdlist.append("sync")
		fileNotFound = ""

		if self.RECOVERY:
			if self.EMMCIMG == "usb_update.bin":
				if not isfile(f"{self.MAINDESTROOT}/{self.EMMCIMG}"):
					fileNotFound = self.EMMCIMG
			else:
				if not isfile(f"{self.MAINDEST}/{self.EMMCIMG}"):
					fileNotFound = self.EMMCIMG
		else:
			if not isfile(f"{self.MAINDEST}/{self.ROOTFSBIN}"):
				fileNotFound = self.ROOTFSBIN

			if not isfile(f"{self.MAINDEST}/{self.KERNELBIN}"):
				fileNotFound = self.KERNELBIN

		if fileNotFound:
			print(f"[Image Backup] {fileNotFound} file not found")

		cmdlist.append(self.makeEchoLine())
		if MultiBoot.canMultiBoot() and not self.RECOVERY and self.ROOTFSSUBDIR == "none":
			cmdlist.append(self.makeEcho(_("Multiboot Image created on: %s/%s-%s-%s-backup-%s_usb.zip") % (self.DIRECTORY, self.DISTRO, self.DISTROVERSION, self.MODEL, self.DATE)))
			cmdlist.append(self.makeEchoLine(True))
			cmdlist.append(self.makeSpace())
			cmdlist.append(self.makeEcho(_("Please wait...almost ready! ")))
			cmdlist.append(self.makeSpace())
			cmdlist.append(self.makeEcho(_("To restore the image:")))
			cmdlist.append(self.makeEcho(_("Use OnlineFlash in SoftwareManager")))
		elif fileNotFound == "":
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

		cmdlist.append(f"rm -rf {self.DIRECTORY}/build_{self.MODEL}")
		rdir = "RootSubdir" if self.ROOTFSSUBDIR != "none" else "root"
		cmdlist.append(f"umount /tmp/bi/{rdir}")
		cmdlist.append(f"rmdir /tmp/bi/{rdir}")
		cmdlist.append("rmdir /tmp/bi")
		cmdlist.append(f"rm -rf {self.WORKDIR}")
		cmdlist.append("echo 3 > /proc/sys/vm/drop_caches")  # Clear Memory
		cmdlist.append("sleep 5")
		END = time()
		DIFF = int(END - self.START)
		TIMELAP = str(timedelta(seconds=DIFF))
		cmdlist.append(self.makeEcho(_("Time required for this process: %s") % TIMELAP + "\n"))

		fileWriteLines(self.runScript, cmdlist, source=MODULE_NAME)
		chmod(self.runScript, 0o755)
		cmdlist = [self.runScript]

		def consoleCallback():
			remove(self.runScript)
			self.close()

		self.session.openWithCallback(consoleCallback, Console, title=self.TITLE, cmdlist=cmdlist, closeOnSuccess=False)

	def imageInfo(self, settings, bouquetsTV, bouquetsRadio, isNotCurrent):
		AboutText = _("Full Image Backup ")
		AboutText += _("By openATV Image Team") + "\n"
		AboutText += _("Support at") + " www.opena.tv\n\n"
		AboutText += _("[Image Info]\n")
		AboutText += f"{_("Model")}: {MACHINEBRAND} {MACHINENAME}\n"
		AboutText += _("Backup Date: %s\n") % strftime("%Y-%m-%d", localtime(self.START))

		if exists("/proc/stb/info/chipset"):
			AboutText += _("Chipset: BCM%s") % BoxInfo.getItem("ChipsetString") + "\n"

		cpu = getCPUInfoString()
		AboutText += f"{_("CPU")}: {cpu[0]}\n"
		AboutText += f"{_("CPU speed/cores")}: {cpu[1]}/{cpu[2]}\n"
		AboutText += f"{_("CPU brand")}: {getCPUBrand()}\n"
		socFamily = BoxInfo.getItem("socfamily")
		if socFamily:
			AboutText += f"{_("SoC family")}: {socFamily}\n"

		AboutText += _("Version: %s") % self.DISTROVERSION + "\n"
		AboutText += _("Build: %s") % self.IMAGEBUILD + "\n"
		if self.KERNEL:  # TODO get slot info
			AboutText += f"{_("Kernel version")}: {self.KERNEL}\n"

		if self.DRIVERSDATE:
			driversdate = str(self.DRIVERSDATE)
			year = driversdate[0:4]
			month = driversdate[4:6]
			day = driversdate[6:8]
			driversdate = "-".join((year, month, day))
			AboutText += f"{_("Drivers version")}:\t{driversdate}\n"

		AboutText += f"{_("Last update")}\t{self.IMGREVISION}\n\n"

		AboutText += _("[Enigma2 Settings]\n")
		for setting in settings:
			AboutText += f"{setting}\n"
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
		infoFile = join(imageDir, "usr/lib/enigma.info")
		info = {}
		enigmaInfo = False
		if isNotCurrent:
			if isfile(infoFile):
				info = MultiBoot.readSlotInfo(infoFile)
				enigmaInfo = True
			elif isfile(join(imageDir, "usr/bin/enigma2")):
				info = MultiBoot.deriveSlotInfo(imageDir)

		settingsFile = fileReadLines(join(imageDir, "etc/enigma2/settings"), source=MODULE_NAME) or []
		bouquetsTV = []
		bouquetsRadio = []
		lines = fileReadLines(join(imageDir, "etc/enigma2/bouquets.tv"), source=MODULE_NAME)
		if lines:
			for line in lines:
				if line.startswith("#SERVICE "):
					bouqet = line.split()
					if len(bouqet) > 3:
						bouqet[3] = bouqet[3].replace("\"", "")
						try:
							with open(f"/etc/enigma2/{bouqet[3]}") as fd:
								userbouqet = fd.readline()
							bouquetsTV.append(userbouqet.replace("#NAME ", ""))
						except UnicodeDecodeError:
							bouquetsTV.append(f"Error: {bouqet[3]} / not UTF-8")
						except OSError:
							pass

		lines = fileReadLines(join(imageDir, "etc/enigma2/bouquets.radio"), source=MODULE_NAME)
		if lines:
			for line in lines:
				if line.startswith("#SERVICE "):
					bouqet = line.split()
					if len(bouqet) > 3:
						bouqet[3] = bouqet[3].replace("\"", "")
						try:
							with open(f"/etc/enigma2/{bouqet[3]}") as fd:
								userbouqet = fd.readline()
							bouquetsRadio.append(userbouqet.replace("#NAME ", ""))
						except UnicodeDecodeError:
							bouquetsRadio.append(f"Error: {bouqet[3]} / not UTF-8")
						except OSError:
							pass

		return (enigmaInfo, info, settingsFile, bouquetsTV, bouquetsRadio)

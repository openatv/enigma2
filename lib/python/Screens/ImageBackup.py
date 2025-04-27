from os import chmod, listdir, makedirs
from os.path import exists, isdir, isfile, join

from Components.ActionMap import HelpableActionMap
from Components.ChoiceList import ChoiceEntryComponent, ChoiceList
from Components.config import config, configfile
from Components.Harddisk import Freespace
from Components.SystemInfo import BoxInfo, getBoxDisplayName
from Components.Sources.StaticText import StaticText
from Screens.Console import Console
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Tools.MultiBoot import MultiBoot
from Tools.Directories import fileReadLines, fileWriteLines

MODULE_NAME = __name__.split(".")[-1]

MACHINE_BRAND = BoxInfo.getItem("displaybrand")
MACHINE_NAME = BoxInfo.getItem("displaymodel")


class ImageBackup(Screen):
	skin = """
	<screen name="ImageBackup" title="Image Backup" position="center,center" size="800,460" resolution="1280,720">
		<widget source="description" render="Label" position="0,0" size="e,50" font="Regular;20" verticalAlignment="center" />
		<widget name="config" position="0,60" size="e,350" font="Regular;25" itemHeight="35" />
		<widget source="key_red" render="Label" position="0,e-40" size="180,40" backgroundColor="key_red" conditional="key_red" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="190,e-40" size="180,40" backgroundColor="key_green" conditional="key_green" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-80,e-40" size="80,40" backgroundColor="key_back" conditional="key_help" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>
	"""

	def __init__(self, session, *args):
		Screen.__init__(self, session, enableHelp=True)
		self.setTitle(_("Image Backup"))
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Start"))
		self["description"] = StaticText(_("Use the UP/DOWN buttons to select the installed image to be backed up. Press the 'Start' (GREEN) button to start the backup."))
		self["config"] = ChoiceList([ChoiceEntryComponent(None, (_("Retrieving image slots - Please wait..."), None, False))])
		self["actions"] = HelpableActionMap(self, ["CancelSaveActions", "OkActions", "NavigationActions"], {
			"cancel": (self.close, _("Exit without performing a backup")),
			"save": (self.keyStart, _("Start the backup of the selected image")),
			"close": (self.keyCloseRecursive, _("Exit and close all screens without performing a backup")),
			"ok": (self.keyStart, _("Start the backup of the selected image")),
			"top": (self["config"].goTop, _("Move to first line / screen")),
			"pageUp": (self["config"].goPageUp, _("Move up a screen")),
			"up": (self["config"].goLineUp, _("Move up a line")),
			"down": (self["config"].goLineDown, _("Move down a line")),
			"pageDown": (self["config"].goPageDown, _("Move down a screen")),
			"bottom": (self["config"].goBottom, _("Move to last line / screen"))
		}, prio=0, description=_("Image Backup Actions"))
		self.bzip2Cmd = "/usr/bin/bzip2"
		self.catCmd = "/bin/cat"
		self.copyCmd = "/bin/cp"
		self.cutCmd = "/usr/bin/cut"
		self.dateCmd = "/bin/date"
		self.ddCmd = "/bin/dd"
		self.duCmd = "/usr/bin/du"
		self.echoCmd = "/bin/echo"
		self.grepCmd = "/bin/grep"
		self.makeDirCmd = "/bin/mkdir"
		self.mkfsExt4 = "/sbin/mkfs.ext4"
		self.mkfsJffs2 = "/usr/sbin/mkfs.jffs2"
		self.mkfsUbiCmd = "/usr/sbin/mkfs.ubifs"
		self.mkupdateCmd = "/usr/sbin/mkupdate"
		self.mountCmd = "/bin/mount"
		self.moveCmd = "/bin/mv"
		self.nandDumpCmd = "/usr/sbin/nanddump"
		self.opkgCmd = "/usr/bin/opkg"
		self.partedCmd = "/usr/sbin/parted"
		self.removeCmd = "/bin/rm"
		self.removeDirCmd = "/bin/rmdir"
		self.rsyncCmd = "/usr/bin/rsync"
		self.sedCmd = "/bin/sed"
		self.shellCmd = "/bin/sh"
		self.syncCmd = "/bin/sync"
		self.tarCmd = "/bin/tar"
		self.touchCmd = "/bin/touch"
		self.ubiCmd = "/usr/sbin/ubinize"
		self.unmountCmd = "/bin/umount"
		self.zipCmd = "/usr/bin/7za"
		self.runScript = "/tmp/imagebackup.sh"
		self.usbBin = "usb_update.bin"
		self.separator = f"{"_" * 66}"
		self.onLayoutFinish.append(self.layoutFinished)
		self.callLater(self.getImageList)

	def layoutFinished(self):
		self["config"].enableAutoNavigation(False)

	def getImageList(self):
		def getImageListCallback(imageList):
			currentImageSlot = MultiBoot.getCurrentSlotCode()
			rootSlot = BoxInfo.getItem("HasKexecMultiboot") and currentImageSlot == "R"
			currentImageSlot = int(currentImageSlot) if currentImageSlot and currentImageSlot.isdecimal() else 1
			print(f"[ImageBackup] Current slot={currentImageSlot}, rootSlot={rootSlot}.")
			images = []  # ChoiceEntryComponent(key, (Label, slotCode, recovery))
			if imageList:
				for slotCode in sorted(imageList.keys()):
					print(f"[ImageBackup]     Slot {slotCode}: {imageList[slotCode]}")
					if imageList[slotCode]["status"] == "active":
						slotText = f"{slotCode} {"eMMC" if "mmcblk" in imageList[slotCode]["device"] else "USB"}"
						if slotCode == "1" and currentImageSlot == 1 and BoxInfo.getItem("canRecovery"):
							images.append(ChoiceEntryComponent(None, (_("Slot %s: %s as USB Recovery") % (slotText, imageList[slotCode]["imagename"]), slotCode, True)))
						if rootSlot:
							images.append(ChoiceEntryComponent(None, ((_("Slot %s: %s")) % (slotText, imageList[slotCode]["imagename"]), slotCode, False)))
						else:
							images.append(ChoiceEntryComponent(None, ((_("Slot %s: %s (Current image)") if slotCode == str(currentImageSlot) else _("Slot %s: %s")) % (slotText, imageList[slotCode]["imagename"]), slotCode, False)))
				if rootSlot:
					images.append(ChoiceEntryComponent(None, (_("Slot R: Root Slot Image Backup (Current image)"), "R", False)))
			else:
				if BoxInfo.getItem("canRecovery"):
					images.append(ChoiceEntryComponent(None, (_("Internal flash: %s %s as USB Recovery") % (displayDistro, imageVersion), "slotCode", True)))
				images.append(ChoiceEntryComponent(None, (_("Internal flash:  %s %s ") % (displayDistro, imageVersion), "slotCode", False)))
			self["config"].setList(images)
			for index, item in enumerate(images):
				if item[0][1] == str(currentImageSlot):
					self["config"].moveToIndex(index)
					break

		displayDistro = BoxInfo.getItem("displaydistro")
		imageVersion = BoxInfo.getItem("imageversion")
		MultiBoot.getSlotImageList(getImageListCallback)

	def keyStart(self):
		current = self["config"].getCurrent()  # (label, slotCode, recovery)
		targets = []
		choiceList = []  # (label, slotCode, target, recovery)
		if current[0][1]:  # The MultiBoot enumeration is complete as we now have slotCodes.
			for target in [join("/media", x) for x in listdir("/media")] + ([join("/media/net", x) for x in listdir("/media/net")] if isdir("/media/net") else []):
				if Freespace(target) > 300000:
					targets.append(target)
					choiceList.append((target, current[0][1], target, current[0][2]))
			choiceList.append((_("Do not backup the image"), False, None, False))
			print(f"[ImageBackup] Potential target{"" if len(targets) == 1 else "s"}: '{"', '".join(targets)}'.")
			self.session.openWithCallback(self.runImageBackup, ChoiceBox, text=_("Please select the target location to save the backup:"), choiceList=choiceList, windowTitle=self.getTitle())

	def keyCloseRecursive(self):
		self.close(True)

	def runImageBackup(self, answer):
		def consoleCallback(result=None):
			print("[ImageBackup] Image backup completed.")
			self.close()

		label, slotCode, target, recovery = answer if answer else (None, None, None, None)
		if slotCode:
			shutdownOK = config.usage.shutdownOK.value
			config.usage.shutdownOK.setValue(True)
			config.usage.shutdownOK.save()
			configfile.save()
			# Make sure that the image backup target exists.
			target = join(target, "images")
			if not exists(target):
				try:
					makedirs(target)
				except OSError as err:
					print(f"[ImageBackup] Error {err.errno}: Can't create backup directory '{target}'!  ({err.strerror})")
					self.session.open(MessageBox, f"{_("Error")} {err.errno}: {_("Can't create backup directory!")}  ({err.strerror})", MessageBox.TYPE_ERROR, timeout=10, windowTitle=self.getTitle())
					return
			# Get information about image to be backed up.
			if BoxInfo.getItem("canRecovery"):
				emmcing = BoxInfo.getItem("canRecovery")[0]
				mtdBoot = BoxInfo.getItem("canRecovery")[1]
			else:
				emmcing = "None"
				mtdBoot = "None"
			hasMultiBootMDT = False
			rootfsSubDir = None
			if MultiBoot.canMultiBoot():
				bootSlots = MultiBoot.getBootSlots()
				hasMultiBootMDT = bootSlots[slotCode].get("ubi", False)
				rootfsSubDir = bootSlots[slotCode].get("rootsubdir")
				if BoxInfo.getItem("HasKexecMultiboot") and slotCode == "R":
					mtdKernel = bootSlots[slotCode]["kernel"]
					rootfsSubDir = None
				else:
					mtdKernel = bootSlots[slotCode]["kernel"].split("/")[2]
				mtdRootFs = bootSlots[slotCode]["device"] if hasMultiBootMDT else bootSlots[slotCode]["device"].split("/")[2]
			else:
				mtdKernel = BoxInfo.getItem("mtdkernel")
				mtdRootFs = BoxInfo.getItem("mtdrootfs")
			isNotCurrent = MultiBoot.getCurrentSlotCode() != slotCode
			# Start creating the image backup script.
			print(f"[ImageBackup] Bulding shell script '{self.runScript}' to perform the image backup.")
			cmdLines = []
			cmdLines.append(f"#!{self.shellCmd}")
			cmdLines.append(f"StartTime=`{self.dateCmd} -u +\"%s\"`")
			# Display the starting message to the user.
			lines = []
			lines.append(_("Backup tool for %s %s") % getBoxDisplayName())
			lines.append(self.separator)
			lines.append("")
			lines.append(_("A backup is now being created."))
			lines.append(_("Please be patient."))
			lines.append(_("The backup can take up to about 15 minutes to complete."))
			lines.append(self.separator)
			lines.append("")
			lines.append(_("Backup Mode: USB Recovery") if recovery else _("Backup Mode: Flash Online"))
			lines.append(self.separator)
			lines.append("")
			cmdLines.append(f"{self.echoCmd} \"{"\n".join(lines)}\"")
			# Create working directories.
			cmdLines.append(f"{self.echoCmd} \"{_("Create working directories.")}\"")
			workDir = f"{join(target, "ib", "")}"  # NOTE: workDir will always have a trailing "/".
			cmdLines.append(f"{self.removeCmd} -rf {workDir}")
			cmdLines.append(f"{self.makeDirCmd} -p {workDir}")
			mountPoint = "/tmp/ib/RootSubdir/" if rootfsSubDir else "/tmp/ib/root/"  # NOTE: mountPoint will always have a trailing "/".
			backupRoot = mountPoint  # NOTE: backupRoot will always have a trailing "/".
			cmdLines.append(f"{self.makeDirCmd} -p {mountPoint}")
			cmdLines.append(f"{self.echoCmd} \"{_("Mount root file system.")}\"")  # Mount the root file system.
			if MultiBoot.canMultiBoot():
				mountArgs = f"/dev/{mtdRootFs} {mountPoint}"
				if rootfsSubDir:
					if hasMultiBootMDT:
						mountArgs = f"-t ubifs {mtdRootFs} {mountPoint}"
					backupRoot = f"{join(backupRoot, rootfsSubDir, "")}"  # NOTE: backupRoot will always have a trailing "/".
			else:
				mountArgs = f"--bind / {mountPoint}"
			cmdLines.append(f"{self.mountCmd} {mountArgs}")
			# Extract some image information.
			cmdLines.append(f"if [ -f {backupRoot}usr/lib/enigma.info ]; then")
			cmdLines.append(f"\tDistro=`{self.grepCmd} \"^distro=\" {backupRoot}usr/lib/enigma.info | {self.sedCmd} -En \"s/^\\w+=(['\\\"]?)(.*?)\\1$/\\2/p\"`")
			cmdLines.append(f"\tDisplayDistro=`{self.grepCmd} \"^displaydistro=\" {backupRoot}usr/lib/enigma.info | {self.sedCmd} -En \"s/^\\w+=(['\\\"]?)(.*?)\\1$/\\2/p\"`")
			cmdLines.append(f"\tImageVersion=`{self.grepCmd} \"^imageversion=\" {backupRoot}usr/lib/enigma.info | {self.sedCmd} -En \"s/^\\w+=(['\\\"]?)(.*?)\\1$/\\2/p\"`")
			cmdLines.append(f"elif [ -f {backupRoot}etc/image-version ]; then")
			cmdLines.append(f"\tDistro=`{self.grepCmd} \"^distro=\" {backupRoot}etc/image-version | {self.cutCmd} -d\"=\" -f2`")
			cmdLines.append("\tif [ \"$Distro\" == \"\" ]; then")
			cmdLines.append(f"\t\tDisplayDistro=`{self.grepCmd} \"^creator=\" {backupRoot}etc/image-version | {self.cutCmd} -d\"=\" -f2`")
			cmdLines.append(f"\t\tDistro=`{self.echoCmd} \"$DisplayDistro\" | {self.cutCmd} -d\" \" -f1`")
			cmdLines.append(f"\t\tVersion=`{self.grepCmd} \"^version=\" {backupRoot}etc/image-version | {self.cutCmd} -d\"=\" -f2`")
			cmdLines.append(f"\t\tImageVersion=`{self.echoCmd} \"${{Version:0:3}}\" | {self.sedCmd} -En \"s/^0*(\\d*)/\\1/p\"`.${{Version:3:1}}.${{Version:4:2}}")
			cmdLines.append("\telse")
			cmdLines.append(f"\t\tDisplayDistro=`{self.grepCmd} \"^creator=\" {backupRoot}etc/image-version | {self.cutCmd} -d\"=\" -f2`")
			cmdLines.append(f"\t\tImageVersion=`{self.grepCmd} \"^imageversion=\" {backupRoot}etc/image-version | {self.cutCmd} -d\"=\" -f2`")
			cmdLines.append("\tfi")
			cmdLines.append(f"elif [ -f {backupRoot}etc/issue ]; then")
			cmdLines.append(f"\tData=`{self.sedCmd} -n 2p {backupRoot}etc/issue`")
			cmdLines.append(f"\tDistro=`{self.echoCmd} $Data | {self.cutCmd} -d\" \" -f1`")
			cmdLines.append(f"\tDisplayDistro=`{self.sedCmd} -n 1p {backupRoot}etc/issue | {self.cutCmd} -d\" \" -f3`")
			cmdLines.append(f"\tImageVersion=`{self.echoCmd} $Data | {self.cutCmd} -d\" \" -f2`")
			cmdLines.append("else")
			cmdLines.append("\tDistro=Unknown")
			cmdLines.append("\tDisplayDistro=Unknown")
			cmdLines.append("\tImageVersion=Unknown")
			cmdLines.append("fi")
			cmdLines.append(f"{self.echoCmd} \"{_("Image version")} $DisplayDistro $ImageVersion.\"")
			# Build the "imageversion" inventory file.
			cmdLines.append(f"{self.echoCmd} \"[Image Version]\" > /tmp/imageversion")
			cmdLines.append(f"{self.echoCmd} \"distro=$Distro\" >> /tmp/imageversion")
			cmdLines.append(f"{self.echoCmd} \"displaydistro=$DisplayDistro\" >> /tmp/imageversion")
			cmdLines.append(f"{self.echoCmd} \"imageversion=$ImageVersion.\" >> /tmp/imageversion")
			if not recovery:
				infoPath = "/"
				if MultiBoot.canMultiBoot() and isNotCurrent:
					infoPath = backupRoot
				cmdLines.append(f"{self.echoCmd} >> /tmp/imageversion")
				cmdLines.append(f"{self.echoCmd} \"[Enigma2 Settings]\" >> /tmp/imageversion")
				cmdLines.append(f"{self.catCmd} {infoPath}etc/enigma2/settings >> /tmp/imageversion")
			if not isNotCurrent:
				cmdLines.append(f"{self.echoCmd} >> /tmp/imageversion")
				cmdLines.append(f"{self.echoCmd} \"[Installed Plugins]\" >> /tmp/imageversion")
				cmdLines.append(f"{self.opkgCmd} list-installed | {self.grepCmd} \"enigma2-plugin-*\" >> /tmp/imageversion")
			cmdLines.append(f"{self.echoCmd} 3 > /proc/sys/vm/drop_caches")  # Clear memory caches.
			# Create the root file system image.
			imageFs = BoxInfo.getItem("imagefs").strip().split()
			mkubifsArgs = BoxInfo.getItem("mkubifs")
			backupRootNoSlash = backupRoot[:-1]
			if "jffs2" in imageFs:
				cmdLines.append(f"{self.echoCmd} \"{_("Create root journaling flash file system.")}\"")
				cmdLines.append(f"{self.mkfsJffs2} --root={backupRootNoSlash} --faketime --output={workDir}root.jffs2 {mkubifsArgs}")
			elif "ubi" in imageFs:
				cmdLines.append(f"{self.echoCmd} \"{_("Create root UBI file system.")}\"")
				cmdLines.append(f"{self.echoCmd} > {workDir}root.ubi")
				cmdLines.append(f"{self.mkfsUbiCmd} -r {backupRootNoSlash} -o {workDir}root.ubi {mkubifsArgs}")
				lines = []
				lines.append("[ubifs]")
				lines.append("mode=ubi")
				lines.append(f"image={workDir}root.ubi")
				lines.append("vol_id=0")
				lines.append("vol_type=dynamic")
				lines.append("vol_name=rootfs")
				lines.append("vol_flags=autoresize")
				cmdLines.append(f"{self.echoCmd} '{"\n".join(lines)}' > {workDir}ubinize.cfg")
				cmdLines.append(f"{self.ubiCmd} -o {workDir}root.ubifs {BoxInfo.getItem("ubinize")} {workDir}ubinize.cfg")
			elif not recovery:
				cmdLines.append(f"{self.echoCmd} \"{_("Create tar file of root file system.")}\"")
				# cmdLines.append(f"{self.touchCmd} {workDir}rootfs.tar")  # Uncomment this line and comment out the line below to enable a fast backup debugging mode.
				cmdLines.append(f"{self.tarCmd} -cf {workDir}rootfs.tar -C {backupRootNoSlash} --exclude ./boot/kernel.img --exclude ./var/nmbd --exclude ./.resizerootfs --exclude ./.resize-rootfs --exclude ./.resize-linuxrootfs --exclude ./.resize-userdata --exclude ./var/lib/samba/private/msg.sock --exclude ./var/lib/samba/msg.sock/* --exclude ./run/avahi-daemon/socket --exclude ./run/chrony/chronyd.sock --exclude ./run/udev/control .")
				cmdLines.append(f"{self.syncCmd}")
				cmdLines.append(f"{self.echoCmd} \"{_("Compress root file system tar file. (This takes the most time!)")}\"")
				cmdLines.append(f"{self.bzip2Cmd} {workDir}rootfs.tar")
			cmdLines.append(f"{self.syncCmd}")
			# Create other image backup components.
			boxName = BoxInfo.getItem("BoxName")
			if boxName in ("gbquad4k", "gbquad4kpro", "gbue4k", "gbx34k"):
				cmdLines.append(f"{self.echoCmd} \"{_("Create boot dump.")}\"")
				cmdLines.append(f"{self.ddCmd} if=/dev/mmcblk0p1 of={workDir}boot.bin")
				cmdLines.append(f"{self.echoCmd} \"{_("Create rescue dump.")}\"")
				cmdLines.append(f"{self.ddCmd} if=/dev/mmcblk0p3 of={workDir}rescue.bin")
			displayNames = ["fast boot", "boot arguments", "base parameters", "PQ parameters", "logo"]
			model = BoxInfo.getItem("model")
			if model in ("h9", "i55plus"):
				for index, value in enumerate(["fastboot", "bootargs", "baseparam", "pq_param", "logo"]):
					cmdLines.append(f"{self.echoCmd} \"Create {displayNames[index]} dump.\"")
					cmdLines.append(f"{self.ddCmd} if=/dev/mtd{index} of={workDir}{value}.bin")
			if emmcing == self.usbBin and recovery:
				cmdLines.append(f"{self.echoCmd} \"Create {displayNames[0]} dump.\"")
				# cmdLines.append(f"{self.ddCmd} if=/dev/mmcblk0p1 of={workDir}fastboot.bin")
				cmdLines.append(f"{self.copyCmd} -f /usr/share/fastboot.bin {workDir}")
				cmdLines.append(f"{self.echoCmd} \"Create {displayNames[1]} dump.\"")
				# cmdLines.append(f"{self.ddCmd} if=/dev/mmcblk0p2 of={workDir}bootargs.bin")
				cmdLines.append(f"{self.copyCmd} -f /usr/share/bootargs.bin {workDir}")
				cmdLines.append(f"{self.echoCmd} \"{_("Create boot image dump.")}\"")
				cmdLines.append(f"{self.ddCmd} if=/dev/mmcblk0p3 of={workDir}boot.img")
				cmdLines.append(f"{self.echoCmd} \"Create {displayNames[2]} dump.\"")
				# cmdLines.append(f"{self.copyCmd} -f /usr/share/bootargs.bin {workDir}baseparam.img")
				cmdLines.append(f"{self.ddCmd} if=/dev/mmcblk0p4 of={workDir}baseparam.img")
				cmdLines.append(f"{self.echoCmd} \"Create {displayNames[3]} dump.\"")
				# cmdLines.append(f"{self.copyCmd} -f /usr/share/bootargs.bin {workDir}pq_param.bin")
				cmdLines.append(f"{self.ddCmd} if=/dev/mmcblk0p5 of={workDir}pq_param.bin")
				cmdLines.append(f"{self.echoCmd} \"Create {displayNames[4]} dump.\"")
				cmdLines.append(f"{self.ddCmd} if=/dev/mmcblk0p6 of={workDir}logo.img")
				cmdLines.append(f"{self.echoCmd} \"{_("Create device information dump.")}\"")
				# cmdLines.append(f"{self.copyCmd} -f /usr/share/bootargs.bin {workDir}deviceinfo.bin")
				cmdLines.append(f"{self.ddCmd} if=/dev/mmcblk0p7 of={workDir}deviceinfo.bin")
				cmdLines.append(f"{self.echoCmd} \"{_("Create application loader dump.")}\"")
				# cmdLines.append(f"{self.ddCmd} if=/dev/mmcblk0p10 of={workDir}apploader.bin")
				cmdLines.append(f"{self.copyCmd} -f /usr/share/apploader.bin {workDir}")
				cmdLines.append(f"{self.echoCmd} \"{_("Create root file system dump.")}\"")
				cmdLines.append(f"{self.ddCmd} if=/dev/zero of={workDir}rootfs.ext4 seek=$(((`{self.duCmd} -sb \"{backupRoot}\" | cut -f1` / 1024) + 200000)) count=60 bs=1024")
				cmdLines.append(f"{self.mkfsExt4} -F -i 4096 {workDir}rootfs.ext4")
				cmdLines.append(f"{self.makeDirCmd} -p {workDir}userdata")
				cmdLines.append(f"{self.mountCmd} {workDir}rootfs.ext4 {workDir}userdata")
				for rootIndex in range(1, 5):
					cmdLines.append(f"{self.makeDirCmd} -p {workDir}userdata/linuxrootfs{rootIndex}")
				cmdLines.append(f"{self.rsyncCmd} -aAX {backupRoot} {workDir}userdata/linuxrootfs1")
				cmdLines.append(f"{self.unmountCmd} {workDir}userdata")
			# Create the kernel dump.
			cmdLines.append(f"{self.echoCmd} \"{_("Create kernel dump.")}\"")
			kernelFile = BoxInfo.getItem("kernelfile")
			if boxName in ("dm820", "dm7080"):
				cmdLines.append(f"{self.echoCmd} \"dummy file dont delete\" > {workDir}{kernelFile}")
			elif MultiBoot.canMultiBoot() or mtdKernel.startswith("mmcblk0") or model in ("h8", "hzero"):
				if BoxInfo.getItem("HasKexecMultiboot") or BoxInfo.getItem("HasGPT"):
					cmdLines.append(f"{self.copyCmd} /{mtdKernel} {workDir}{kernelFile}")
				else:
					cmdLines.append(f"{self.ddCmd} if=/dev/{mtdKernel} of={workDir}{kernelFile}")
			else:
				cmdLines.append(f"{self.nandDumpCmd} -a -f {workDir}vmlinux.gz {join("/dev", mtdKernel)}")
			if emmcing == "disk.img" and recovery:
				blockSize = 512  # These values are all assumed to be integers!
				blockSectors = 2
				imageRoorFSAlignment = 1024
				bootPartitionSize = 3072
				kernelPartitionSize = 8192
				rootFSPartitionSize = 1048576
				emmcImageSize = 3817472
				kernelPartitionOffset = imageRoorFSAlignment + bootPartitionSize
				rootFSPartitionOffset = kernelPartitionOffset + kernelPartitionSize
				secondKernelPartitionOffset = rootFSPartitionOffset + rootFSPartitionSize
				thirdKernelPartitionOffset = secondKernelPartitionOffset + kernelPartitionSize
				fourthKernelPartitionOffset = thirdKernelPartitionOffset + kernelPartitionSize
				emmcImage = f"{workDir}{emmcing}"
				cmdLines.append(f"{self.echoCmd} \"{_("Create recovery image backup '%s'.") % emmcing}\"")
				cmdLines.append(f"{self.ddCmd} if=/dev/zero of={emmcImage} bs={blockSize} count=0 seek={emmcImageSize * blockSectors}")
				cmdLines.append(f"{self.partedCmd} -s {emmcImage} mklabel gpt")
				cmdLines.append(f"{self.partedCmd} -s {emmcImage} unit KiB mkpart boot fat16 {imageRoorFSAlignment} {imageRoorFSAlignment + bootPartitionSize}")
				cmdLines.append(f"{self.partedCmd} -s {emmcImage} unit KiB mkpart linuxkernel {kernelPartitionOffset} {kernelPartitionOffset + kernelPartitionSize}")
				cmdLines.append(f"{self.partedCmd} -s {emmcImage} unit KiB mkpart linuxrootfs ext4 {rootFSPartitionOffset} {rootFSPartitionOffset + rootFSPartitionSize}")
				cmdLines.append(f"{self.partedCmd} -s {emmcImage} unit KiB mkpart linuxkernel2 {secondKernelPartitionOffset} {secondKernelPartitionOffset + kernelPartitionSize}")
				cmdLines.append(f"{self.partedCmd} -s {emmcImage} unit KiB mkpart linuxkernel3 {thirdKernelPartitionOffset} {thirdKernelPartitionOffset + kernelPartitionSize}")
				cmdLines.append(f"{self.partedCmd} -s {emmcImage} unit KiB mkpart linuxkernel4 {fourthKernelPartitionOffset} {fourthKernelPartitionOffset + kernelPartitionSize}")
				lines = fileReadLines("/proc/swaps", default=[], source=MODULE_NAME)
				mmcblk0p7Found = False
				for line in lines:
					if "mmcblk0p7" in line:
						mmcblk0p7Found = True
						break
				if mmcblk0p7Found:
					swapPartitionSize = 262144
					swapPartitionOffset = fourthKernelPartitionOffset + kernelPartitionSize
					cmdLines.append(f"{self.partedCmd} -s {emmcImage} unit KiB mkpart swap linux-swap {swapPartitionOffset} {swapPartitionOffset + swapPartitionSize}")
					cmdLines.append(f"{self.partedCmd} -s {emmcImage} unit KiB mkpart userdata ext4 {swapPartitionOffset + swapPartitionSize} 100%")
				else:
					cmdLines.append(f"{self.partedCmd} -s {emmcImage} unit KiB mkpart userdata ext4 {fourthKernelPartitionOffset + kernelPartitionSize} 100%")
				cmdLines.append(f"{self.ddCmd} if=/dev/{mtdBoot} of={emmcImage} seek={imageRoorFSAlignment * blockSectors}")
				cmdLines.append(f"{self.ddCmd} if=/dev/{mtdKernel} of={emmcImage} seek={kernelPartitionOffset * blockSectors}")
				cmdLines.append(f"{self.ddCmd} if=/dev/{mtdRootFs} of={emmcImage} seek={rootFSPartitionOffset * blockSectors}")
			elif emmcing == "emmc.img" and recovery:  # BOOTDD_VOLUME_ID = "boot".
				blockSectors = 2  # These values are all assumed to be integers!
				imageRoorFSAlignment = 1024
				bootPartitionSize = 3072
				kernelPartitionSize = 8192
				rootFSPartitionSize = 1898496
				emmcImageSize = 7634944
				el1PartitionOffset = imageRoorFSAlignment + bootPartitionSize
				rootFSPartitionOffset = el1PartitionOffset + kernelPartitionSize
				kernel2PartitionOffset = rootFSPartitionOffset + rootFSPartitionSize
				rootFS2PartitionOffset = kernel2PartitionOffset + kernelPartitionSize
				kernel3PartitionOffset = rootFS2PartitionOffset + rootFSPartitionSize
				rootFS3PartitionOffset = kernel3PartitionOffset + kernelPartitionSize
				kernel4PartitionOffset = rootFS3PartitionOffset + rootFSPartitionSize
				rootFS4PartitionOffset = kernel4PartitionOffset + kernelPartitionSize
				emmcImage = f"{workDir}{emmcing}"
				cmdLines.append(f"{self.echoCmd} \"{_("Create recovery image backup '%s'.") % emmcing}\"")
				cmdLines.append(f"{self.ddCmd} if=/dev/zero of={emmcImage} bs=1 count=0 seek={emmcImageSize * imageRoorFSAlignment}")
				cmdLines.append(f"{self.partedCmd} -s {emmcImage} mklabel gpt")
				cmdLines.append(f"{self.partedCmd} -s {emmcImage} unit KiB mkpart boot fat16 {imageRoorFSAlignment} {imageRoorFSAlignment + bootPartitionSize}")
				cmdLines.append(f"{self.partedCmd} -s {emmcImage} set 1 boot on")
				cmdLines.append(f"{self.partedCmd} -s {emmcImage} unit KiB mkpart kernel1 {el1PartitionOffset} {el1PartitionOffset + kernelPartitionSize}")
				cmdLines.append(f"{self.partedCmd} -s {emmcImage} unit KiB mkpart rootfs1 ext4 {rootFSPartitionOffset} {rootFSPartitionOffset + rootFSPartitionSize}")
				cmdLines.append(f"{self.partedCmd} -s {emmcImage} unit KiB mkpart kernel2 {kernel2PartitionOffset} {kernel2PartitionOffset + kernelPartitionSize}")
				cmdLines.append(f"{self.partedCmd} -s {emmcImage} unit KiB mkpart rootfs2 ext4 {rootFS2PartitionOffset} {rootFS2PartitionOffset + rootFSPartitionSize}")
				cmdLines.append(f"{self.partedCmd} -s {emmcImage} unit KiB mkpart kernel3 {kernel3PartitionOffset} {kernel3PartitionOffset + kernelPartitionSize}")
				cmdLines.append(f"{self.partedCmd} -s {emmcImage} unit KiB mkpart rootfs3 ext4 {rootFS3PartitionOffset} {rootFS3PartitionOffset + rootFSPartitionSize}")
				cmdLines.append(f"{self.partedCmd} -s {emmcImage} unit KiB mkpart kernel4 {kernel4PartitionOffset} {kernel4PartitionOffset + kernelPartitionSize}")
				cmdLines.append(f"{self.partedCmd} -s {emmcImage} unit KiB mkpart rootfs4 ext4 {rootFS4PartitionOffset} {rootFS4PartitionOffset + rootFSPartitionSize}")
				cmdLines.append(f"{self.ddCmd} if=/dev/{mtdBoot} of={emmcImage} seek={imageRoorFSAlignment * blockSectors}")
				cmdLines.append(f"{self.ddCmd} if=/dev/{mtdKernel} of={emmcImage} seek={el1PartitionOffset * blockSectors}")
				cmdLines.append(f"{self.ddCmd} if=/dev/{mtdRootFs} of={emmcImage} seek={rootFSPartitionOffset * blockSectors} ")
			elif emmcing == self.usbBin and recovery:
				cmdLines.append(f"{self.echoCmd} \"{_("Create recovery image backup '%s'.") % emmcing}\"")
				lines = []
				lines.append("<?xml version=\"1.0\" encoding=\"GB2312\" ?>")
				lines.append("<Partition_Info>")
				lines.append("\t<Part Sel=\"1\" PartitionName=\"fastboot\" FlashType=\"emmc\" FileSystem=\"none\" Start=\"0\" Length=\"1M\" SelectFile=\"fastboot.bin\"/>")
				lines.append("\t<Part Sel=\"1\" PartitionName=\"bootargs\" FlashType=\"emmc\" FileSystem=\"none\" Start=\"1M\" Length=\"1M\" SelectFile=\"bootargs.bin\"/>")
				lines.append("\t<Part Sel=\"1\" PartitionName=\"bootoptions\" FlashType=\"emmc\" FileSystem=\"none\" Start=\"2M\" Length=\"1M\" SelectFile=\"boot.img\"/>")
				lines.append("\t<Part Sel=\"1\" PartitionName=\"baseparam\" FlashType=\"emmc\" FileSystem=\"none\" Start=\"3M\" Length=\"3M\" SelectFile=\"baseparam.img\"/>")
				lines.append("\t<Part Sel=\"1\" PartitionName=\"pqparam\" FlashType=\"emmc\" FileSystem=\"none\" Start=\"6M\" Length=\"4M\" SelectFile=\"pq_param.bin\"/>")
				lines.append("\t<Part Sel=\"1\" PartitionName=\"logo\" FlashType=\"emmc\" FileSystem=\"none\" Start=\"10M\" Length=\"4M\" SelectFile=\"logo.img\"/>")
				lines.append("\t<Part Sel=\"1\" PartitionName=\"deviceinfo\" FlashType=\"emmc\" FileSystem=\"none\" Start=\"14M\" Length=\"4M\" SelectFile=\"deviceinfo.bin\"/>")
				lines.append("\t<Part Sel=\"1\" PartitionName=\"loader\" FlashType=\"emmc\" FileSystem=\"none\" Start=\"26M\" Length=\"32M\" SelectFile=\"apploader.bin\"/>")
				lines.append("\t<Part Sel=\"1\" PartitionName=\"linuxkernel1\" FlashType=\"emmc\" FileSystem=\"none\" Start=\"66M\" Length=\"16M\" SelectFile=\"kernel.bin\"/>")
				lines.append(f"\t<Part Sel=\"1\" PartitionName=\"userdata\" FlashType=\"emmc\" FileSystem=\"ext3/4\" Start=\"130M\" Length=\"{"3580" if model == "sf8008m" else "7000"}M\" SelectFile=\"rootfs.ext4\"/>")
				lines.append("</Partition_Info>")
				cmdLines.append(f"{self.echoCmd} '{"\n".join(lines)}' > {workDir}emmc_partitions.xml")
				cmdLines.append(f"{self.mkupdateCmd} -s 00000003-00000001-01010101 -f {workDir}emmc_partitions.xml -d {workDir}{emmcing}")
			cmdLines.append(f"{self.syncCmd}")
			# Assemble the image backup.
			cmdLines.append(f"{self.echoCmd} \"{_("Assembling the image backup files.")}\"")
			mainDestinationRoot = f"{join(target, f"build_{boxName}", "")}"  # NOTE: mainDestinationRoot will always have a trailing "/".
			mainDestination = f"{join(target, f"build_{boxName}", BoxInfo.getItem("imagedir"), "")}"  # NOTE: mainDestination will always have a trailing "/".
			checkFiles = []
			if emmcing == self.usbBin and recovery:
				cmdLines.append(f"{self.removeCmd} -rf {mainDestinationRoot}")
				cmdLines.append(f"{self.makeDirCmd} -p {mainDestinationRoot}")
				cmdLines.append(f"{self.moveCmd} /tmp/imageversion {mainDestinationRoot}")
				cmdLines.append(f"if [ -f {backupRoot}usr/lib/enigma.info ]; then")
				cmdLines.append(f"\t{self.copyCmd} {backupRoot}usr/lib/enigma.info {mainDestinationRoot}")
				cmdLines.append("fi")
				cmdLines.append(f"if [ -f {backupRoot}usr/lib/enigma.conf ]; then")
				cmdLines.append(f"\t{self.copyCmd} {backupRoot}usr/lib/enigma.conf {mainDestinationRoot}")
				cmdLines.append("fi")
			else:
				cmdLines.append(f"{self.removeCmd} -rf {mainDestination}")
				cmdLines.append(f"{self.makeDirCmd} -p {mainDestination}")
				cmdLines.append(f"{self.moveCmd} /tmp/imageversion {mainDestination}")
				cmdLines.append(f"if [ -f {backupRoot}usr/lib/enigma.info ]; then")
				cmdLines.append(f"\t{self.copyCmd} {backupRoot}usr/lib/enigma.info {mainDestination}")
				cmdLines.append("fi")
				cmdLines.append(f"if [ -f {backupRoot}usr/lib/enigma.conf ]; then")
				cmdLines.append(f"\t{self.copyCmd} {backupRoot}usr/lib/enigma.conf {mainDestination}")
				cmdLines.append("fi")
				cmdLines.append(f"if [ -f {backupRoot}etc/image-version ]; then")
				cmdLines.append(f"\t{self.copyCmd} {backupRoot}etc/image-version {mainDestination}")
				cmdLines.append("fi")
				if not recovery:
					if model in ("dm800se", "dm500hd", "dreamone", "dreamtwo"):
						cmdLines.append(f"{self.touchCmd} {mainDestination}{kernelFile}")
					elif MultiBoot.canMultiBoot() or mtdKernel.startswith("mmcblk0") or model in ("h8", "hzero"):
						cmdLines.append(f"{self.moveCmd} {workDir}{kernelFile} {mainDestination}")
					else:
						cmdLines.append(f"{self.moveCmd} {workDir}vmlinux.gz {mainDestination}{kernelFile}")
					rootFile = BoxInfo.getItem("rootfile")
					if rootFile in ("rootfs.tar.bz2", "rootfs-two.tar.bz2", "rootfs-one.tar.bz2"):
						if model in ("dreamone", "dreamtwo"):
							cmdLines.append(f"{self.moveCmd} {workDir}rootfs.tar.bz2 {mainDestination}{rootFile}")
						else:
							cmdLines.append(f"{self.moveCmd} {workDir}{rootFile} {mainDestination}")
					else:
						cmdLines.append(f"{self.moveCmd} {workDir}root.ubifs {mainDestination}{rootFile}")
					checkFiles.append(f"{mainDestination}{kernelFile}")
					checkFiles.append(f"{mainDestination}{rootFile}")
			if recovery:
				if emmcing == self.usbBin:
					cmdLines.append(f"{self.moveCmd} {workDir}{emmcing} {mainDestinationRoot}")
					cmdLines.append(f"{self.copyCmd} -f /usr/share/fastboot.bin {mainDestinationRoot}")
					cmdLines.append(f"{self.copyCmd} -f /usr/share/bootargs.bin {mainDestinationRoot}")
					cmdLines.append(f"{self.copyCmd} -f /usr/share/apploader.bin {mainDestinationRoot}")
					checkFiles.append(f"{mainDestinationRoot}{emmcing}")
				else:
					checkFiles.append(f"{mainDestination}{emmcing}")
					cmdLines.append(f"{self.moveCmd} {workDir}{emmcing} {mainDestination}")
				if emmcing == "emmc.img":
					cmdLines.append(f"{self.echoCmd} \"Rename this file to 'force' to force an update without confirmation.\" > {mainDestination}noforce")
			elif boxName in ("vuultimo4k", "vusolo4k", "vuduo2", "vusolo2", "vusolo", "vuduo", "vuultimo", "vuuno"):
				cmdLines.append(f"{self.echoCmd} \"This file forces a reboot after the update.\" > {mainDestination}reboot.update")
			elif boxName in ("vuzero", "vusolose", "vuuno4k", "vuzero4k"):
				cmdLines.append(f"{self.echoCmd} \"This file forces the update.\" > {mainDestination}force.update")
			elif boxName in ("viperslim", "evoslimse", "evoslimt2c", "novaip", "zgemmai55", "sf98", "xpeedlxpro", "evoslim", "vipert2c"):
				cmdLines.append(f"{self.echoCmd} \"This file forces the update.\" > {mainDestination}force")
			elif rootfsSubDir:
				lines = []
				lines.append(f"Rename the 'unforce_{model}.txt' to 'force_{model}.txt' and move it to the root of your usb-stick.")
				lines.append("When you enter the recovery menu then it will force to install the image in the linux1 selection.")
				cmdLines.append(f"{self.echoCmd} \"{"\n".join(lines)}\" > {mainDestination}force_{model}_READ.ME")
			else:
				cmdLines.append(f"{self.echoCmd} \"Rename this file to 'force' to force an update without confirmation.\" > {mainDestination}noforce")
			if boxName in ("gbquad4k", "gbquad4kpro", "gbue4k", "gbx34k"):
				cmdLines.append(f"{self.moveCmd} {workDir}boot.bin {mainDestination}")
				cmdLines.append(f"{self.moveCmd} {workDir}rescue.bin {mainDestination}")
				cmdLines.append(f"{self.copyCmd} -f /usr/share/gpt.bin {mainDestination}")
			if model in ("h9", "i55plus"):
				cmdLines.append(f"{self.moveCmd} {workDir}fastboot.bin {mainDestination}")
				cmdLines.append(f"{self.moveCmd} {workDir}pq_param.bin {mainDestination}")
				cmdLines.append(f"{self.moveCmd} {workDir}bootargs.bin {mainDestination}")
				cmdLines.append(f"{self.moveCmd} {workDir}baseparam.bin {mainDestination}")
				cmdLines.append(f"{self.moveCmd} {workDir}logo.bin {mainDestination}")
			if boxName in ("gbquad", "gbquadplus", "gb800ue", "gb800ueplus", "gbultraue", "gbultraueh", "twinboxlcd", "twinboxlcdci", "singleboxlcd", "sf208", "sf228"):
				lcdWaitKey = "/usr/share/lcdwaitkey.bin"
				if isfile(lcdWaitKey):
					cmdLines.append(f"{self.copyCmd} {lcdWaitKey} {mainDestination}")
				lcdWarning = "/usr/share/lcdwarning.bin"
				if isfile(lcdWarning):
					cmdLines.append(f"{self.copyCmd} {lcdWarning} {mainDestination}")
			if boxName in ("e4hdultra", "protek4k"):
				lcdWarning = "/usr/share/lcdflashing.bmp"
				if isfile(lcdWarning):
					cmdLines.append(f"{self.copyCmd} {lcdWarning} {mainDestination}")
			if boxName == "gb800solo":
				lines = []
				lines.append("flash -noheader usbdisk0:gigablue/solo/kernel.bin flash0.kernel")
				lines.append("flash -noheader usbdisk0:gigablue/solo/rootfs.bin flash0.rootfs")
				lines.append("setenv -p STARTUP \"boot -z -elf flash0.kernel: 'rootfstype=jffs2 bmem=106M@150M root=/dev/mtdblock6 rw '\"")
				cmdLines.append(f"{self.echoCmd} '{"\n".join(lines)}' > {mainDestinationRoot}burn.bat")
			if model in ("h9", "i55plus"):
				cmdLines.append(f"{self.copyCmd} -f /usr/share/fastboot.bin {mainDestinationRoot}")
				cmdLines.append(f"{self.copyCmd} -f /usr/share/bootargs.bin {mainDestinationRoot}")
			name = "recovery_emmc" if BoxInfo.getItem("canRecovery") and recovery else "usb"
			cmdLines.append(f"{self.echoCmd} 3 > /proc/sys/vm/drop_caches")  # Clear memory caches.
			cmdLines.append(f"{self.echoCmd} \"{_("Create backup image zip file.")}\"")
			cmdLines.append(f"ZipName=$Distro-$ImageVersion-{boxName}-backup-`{self.dateCmd} +\"%Y%m%d_%H%M\"`_{name}.zip")
			cmdLines.append(f"{self.zipCmd} a -r -bt -bd -bso0 {target}/$ZipName {join(mainDestinationRoot, "*")}")
			cmdLines.append(self.syncCmd)
			checkFiles = "\" -a \"".join(checkFiles)
			cmdLines.append(f"if [ -r \"{checkFiles}\" ]; then")
			if MultiBoot.canMultiBoot() and not recovery and rootfsSubDir is None:
				lines = []
				lines.append(self.separator)
				lines.append("")
				lines.append(f"{_("Multiboot Image created:")} $ZipName")
				lines.append(self.separator)
				lines.append("")
				lines.append(_("To restore the image use 'OnlineFlash' option in the 'SoftwareManager' menu."))
				cmdLines.append(f"\t{self.echoCmd} \"{"\n".join(lines)}\"")
			else:
				lines = []
				lines.append(self.separator)
				lines.append("")
				lines.append(f"{_("Image created:")} $ZipName")
				lines.append(self.separator)
				lines.append("")
				lines.append(_("To restore the image check the manual or documentation for the receiver."))
				cmdLines.append(f"\t{self.echoCmd} \"{"\n".join(lines)}\"")
			cmdLines.append("else")
			lines = []
			lines.append(f"{_("Image creation failed!")}")
			lines.append(f"{_("Possible causes could be:")}")
			lines.append(f"{_("- Wrong backup destination.")}")
			lines.append(f"{_("- No space left on backup device.")}")
			lines.append(f"{_("- No write permission on backup device.")}")
			cmdLines.append(f"\t{self.echoCmd} \"{"\n".join(lines)}\"")
			cmdLines.append("fi")
			cmdLines.append(f"{self.removeCmd} -rf {join(target, f"build_{boxName}")}")
			cmdLines.append(f"{self.unmountCmd} {mountPoint}")  # Unmount the root file system.
			cmdLines.append(f"{self.removeDirCmd} {mountPoint}")
			cmdLines.append(f"{self.removeDirCmd} /tmp/ib/")
			cmdLines.append(f"{self.removeCmd} -rf {workDir}")
			cmdLines.append(f"{self.echoCmd} 3 > /proc/sys/vm/drop_caches")  # Clear memory caches.
			cmdLines.append(f"{self.syncCmd}")
			cmdLines.append(f"{self.echoCmd}")
			cmdLines.append(f"EndTime=`{self.dateCmd} -u +\"%s\"`")
			cmdLines.append(f"RunTime=`{self.dateCmd} -u -d@\"$(($EndTime - $StartTime))\" +\"%H:%M:%S\"`")
			cmdLines.append(f"{self.echoCmd} \"{_("Time taken for the backup:")} $RunTime\"")
			fileWriteLines(self.runScript, cmdLines, source=MODULE_NAME)
			chmod(self.runScript, 0o755)
			print("[ImageBackup] Running the shell script.")
			self.session.openWithCallback(consoleCallback, Console, title=_("Image Backup To %s") % target, cmdlist=[self.runScript], closeOnSuccess=False, showScripts=False)
			config.usage.shutdownOK.setValue(shutdownOK)
			config.usage.shutdownOK.save()
			configfile.save()
		else:
			self.close()

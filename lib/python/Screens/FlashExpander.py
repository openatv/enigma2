from os import system, listdir, statvfs, remove, popen as os_popen
from os.path import exists, join, realpath
from re import search
from subprocess import Popen, PIPE
from enigma import quitMainloop

from Components.config import ConfigSelection
from Components.Console import Console
from Components.Harddisk import harddiskmanager, Harddisk
from Screens.Setup import Setup
from Screens.MessageBox import MessageBox
from Tools.Directories import createDir, fileReadLines
from Tools.BoundFunction import boundFunction


class FlashExpander(Setup):
	def __init__(self, session):
		choices = []
		default = ""
		self.devicelist = []
		if self.ismounted("", "/usr"):
			self.found = True
			self["footnote"].setText((_("... is used, %dMB free") % self.getFreeSize("/usr")))
			choices.append(("", _("Activated")))
		else:
			# Read block devices
			for x in listdir("/sys/block"):
				if x[0:2] == "sd" or x[0:2] == "hd":
					print("[FlashExpander] device %s" % x)
					devices = Harddisk(x)
					for y in range(devices.numPartitions()):
						fstype = self.getPartitionType(devices.partitionPath(str(y + 1)))
						if fstype is False:
							fstype = self.getPartitionType(devices.partitionPath(str(y + 1)))
						bustype = devices.bus()
						if fstype in ("ext2", "ext3", "ext4", "xfs"):
							self.devicelist.append(("%s (%s) - Partition %d (%s)" % (devices.model(), bustype, y + 1, fstype), (devices, y + 1, fstype)))

			# Read network devices
			try:
				for x in self.getMounts():
					entry = x.split(" ")
					if len(entry) > 3 and entry[2] == "nfs":
						server = entry[0].split(":")
						if len(server) == 2:
							print("[FlashExpander] server %s" % server)
							self.devicelist.append(("Server (%s) - Path (%s)" % (server[0], server[1]), server))
			except Exception as error:
				print("[FlashExpander] Error <getMountPoints>: %s" % str(error))

			if len(self.devicelist) == 0:
				self["footnote"].setText(_("No HDD-, SSD- or USB-Device found. Please first initialized."))
				choices.append(("", _("No drive available")))
			else:
				self["footnote"].setText(_("FlashExpander is not installed, create?"))
				choices.append(("", _("No drive available")))
				for index, device in enumerate(self.devicelist):
					choices.append((str(index), device[0]))

		self.selection = ConfigSelection(choices=choices, default=default)
		Setup.__init__(self, session=session, setup="FlashExpander")
		self.Console = Console()

	def getMounts(self):
		return fileReadLines("/proc/mounts", [])

	def ismounted(self, device, mountpoint):
		for mount in self.getMounts():
			parts = mount.strip().split(" ")
			if len(parts) > 1 and (parts[0] == device or parts[1] == mountpoint):
				return parts[1]
		return False

	def getFreeSize(self, mountpoint):
		try:
			stat = statvfs(mountpoint)
			return int(stat.f_bfree / 1000 * stat.f_bsize / 1000)
		except OSError:
			return 0

	def getPartitionType(self, device):
		fstype = None
		try:
			for line in os_popen("/sbin/blkid %s" % device).read().split("\n"):
				if not line.startswith(device):
					continue
				fstobj = search(r' TYPE="((?:[^"\\]|\\.)*)"', line)
				if fstobj:
					fstype = fstobj.group(1)
		except Exception as error:
			print("[FlashExpander] <error get fstype> : %s" % str(error))
			return False
		return fstype

	def getPartitionUUID(self, device):
		try:
			p = Popen(["blkid", "-o", "udev", device], stdout=PIPE, stderr=PIPE, stdin=PIPE)
			txtUUID = p.stdout.read()
			start = txtUUID.find(b"ID_FS_UUID=")
			if start > -1:
				txtUUID = txtUUID[start + 11:]
				end = txtUUID.find(b"\n")
				if end > -1:
					txtUUID = txtUUID[:end]
				return b"UUID=%s" % txtUUID
			return device
		except Exception as error:
			print("[FlashExpander] <error get UUID>: %s" % str(error))
		return None

	def startCopyDisk(self, val, result):
		if result:
			partitionPath = val[0].partitionPath(str(val[1]))
			# TODO: DO WE NEED THIS -> uuidPath
			uuidPath = self.getPartitionUUID(partitionPath)
			fstype = val[2]
			print("[FlashExpander] %s %s %s" % (partitionPath, uuidPath, fstype))

			if uuidPath is None:
				self.session.open(MessageBox, _("read UUID"), MessageBox.TYPE_ERROR, timeout=5)
				return

			mountpoint = self.ismounted(uuidPath, "")
			if mountpoint is False:
				mountpoint = self.ismounted(partitionPath, "")
				if mountpoint is False and self.mount(uuidPath, "/media/FEtmp") == 0:
					mountpoint = "/media/FEtmp"

			self.copyFlash(mountpoint, (partitionPath, uuidPath, fstype))

	def startCopyServer(self, val, result):
		if result:
			serverPath = "%s:%s" % (val[0], val[1])
			print("[FlashExpander] %s" % serverPath)
			mountpoint = self.ismounted(serverPath, "")
			self.copyFlash(mountpoint, (serverPath, None, "nfs"))

	def copyFlash(self, mp, data):
		if self.checkMountPoint(mp):
			cmd = "cp -af /usr/* %s/" % (mp)
			self.Console.ePopen(cmd, self.CopyFinished)
			self.messageBox = self.session.openWithCallback(boundFunction(self.copyFlashCallback, data), MessageBox, _("Please wait, Flash memory will be copied."), MessageBox.TYPE_INFO, enable_input=False)

	def mount(self, device, mountpoint):
		if exists(mountpoint) is False:
			createDir(mountpoint, True)
		cmd = "mount %s %s" % (device, mountpoint)
		print("[FlashExpander] mount command : '%s'" % cmd)
		res = system(cmd)
		return (res >> 8)

	def checkMountPoint(self, mp):
		if mp is False:
			self.session.open(MessageBox, _("Mount failed (%s)") % mp, MessageBox.TYPE_ERROR, timeout=5)
			return False
		if self.getFreeSize(mp) < 180:
			self.session.open(MessageBox, _("Too little free space < 180MB or wrong Filesystem!"), MessageBox.TYPE_ERROR, timeout=5)
			return False
		return True

	def CopyFinished(self, result, retval, extra_args=None):
		if retval == 0:
			self.messageBox.close(True)
		else:
			self.messageBox.close(False)

	def copyFlashCallback(self, val, retval):
		if retval:
			try:
				devPath = val[0]
				uuidPath = val[1].decode("utf-8")
				fstype = val[2]

				#fstab editieren
				fstabItems = []
				with open("/etc/fstab") as fp:
					fstabItems = fp.read().split("\n")
				newlines = []
				for x in fstabItems:
					if x.startswith(devPath) or x.startswith("/dev/hdc1"):  # /dev/hdc1 wegen 7025+
						continue
					if uuidPath and x.startswith(uuidPath):
						continue
					if len(x) > 1 and x[0] != "#":
						newlines.append(x)
				if fstype == "nfs":
					newlines.append("%s\t/usr\t%s\trw,nolock,timeo=14,intr\t0 0" % (devPath, fstype))
				else:
					newlines.append("%s\t/usr\tauto\tdefaults\t0 0" % (uuidPath))
				with open("/etc/fstab", "w") as fp:
					fp.write("#automatically edited by FlashExpander\n")
					for x in newlines:
						fp.write("%s\n" % x)
				print("[FlashExpander] write new /etc/fstab")
				self.session.openWithCallback(self.Exit, MessageBox, _("Do you want to reboot your STB_BOX?"))
			except:
				self.session.open(MessageBox, _("error adding fstab entry for: %s") % (devPath), MessageBox.TYPE_ERROR, timeout=5)
				return
		else:
			self.session.open(MessageBox, _("error copy flash memory"), MessageBox.TYPE_ERROR, timeout=10)

	def Exit(self, data=False):
		if data:
			quitMainloop(2)
		self.close()

	def keySave(self):
		if self.selection.value:
			index = int(self.selection.value)
			sel = self.devicelist[index]
			if sel and sel[1]:
				if len(sel[1]) == 3:  # Device
					tstr = _("Are you sure want to create FlashExpander on\n%s\nPartition %d") % (sel[1][0].model(), sel[1][1])
					self.session.openWithCallback(boundFunction(self.startCopyDisk, sel[1]), MessageBox, tstr)
				if len(sel[1]) == 2:  # Server
					tstr = _("Are you sure want to create FlashExpander on \nServer: %s\nPath: %s") % (sel[1][0], sel[1][1])
					self.session.openWithCallback(boundFunction(self.startCopyServer, sel[1]), MessageBox, tstr)

from os import system, listdir, statvfs, remove, popen as os_popen
from os.path import exists, join, realpath
from re import search
from subprocess import Popen, PIPE
from enigma import quitMainloop

from Components.ActionMap import ActionMap
from Components.Console import Console
from Components.MenuList import MenuList
from Components.Harddisk import harddiskmanager, Harddisk
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Tools.Directories import createDir, fileReadLines
from Tools.BoundFunction import boundFunction


def getMounts():
	return fileReadLines("/proc/mounts", [])


def ismounted(dev, mp):
	for x in getMounts():
		parts = x.strip().split(" ")
		if len(parts) > 1 and (parts[0] == dev or parts[1] == mp):
			return parts[1]
	return False


def getFreeSize(mp):
	try:
		stat = statvfs(mp)
		return int(stat.f_bfree / 1000 * stat.f_bsize / 1000)
	except OSError:
		return 0


class FlashExpanderScreen(Screen):
	skin = """<screen position="center,center" size="580,50" title="FlashExpander v0.33">
			<widget name="list" position="5,5" size="570,40" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.found = False
		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"cancel": self.close,
			"ok": self.ok
		}, -1)

		if ismounted("", "/usr"):
			self.found = True
			_list = [(_("... is used, %dMB free") % getFreeSize("/usr"))]
		else:
			_list = [(_("FlashExpander is not installed, create? Press Key OK."))]

		self["list"] = MenuList(list=_list)

	def ok(self):
		if not self.found:
			self.session.openWithCallback(self.configCallback, FlashExpanderConfigScreen)

	def configCallback(self, data):
		if data:
			quitMainloop(2)
		self.close()


class FlashExpanderConfigScreen(Screen):
	skin = """<screen position="center,center" size="640,160" title="%s">
			<widget name="list" position="5,5" size="630,150" />
		</screen>""" % (_("choose device to FlashExpander"))

	def __init__(self, session):
		Screen.__init__(self, session)

		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"cancel": self.Exit,
			"ok": self.Ok
		}, -1)

		#Blocklaufwerke
		_list = []
		for x in listdir("/sys/block"):
			if x[0:2] == 'sd' or x[0:2] == 'hd':
				print("[FlashExpander] device %s" % x)
				devices = Harddisk(x)
				for y in range(devices.numPartitions()):
					fstype = self.__getPartitionType(devices.partitionPath(str(y + 1)))
					if fstype is False:
						fstype = self.__getPartitionType(devices.partitionPath(str(y + 1)))
					try:
						bustype = devices.bus_type()
					except:
						bustype = _("unknown")
					if fstype in ("ext2", "ext3", "ext4", "xfs"):
						_list.append(("%s (%s) - Partition %d (%s)" % (devices.model(), bustype, y + 1, fstype), (devices, y + 1, fstype)))

		#Netzlaufwerke
		try:
			for x in getMounts():
				entry = x.split(' ')
				if len(entry) > 3 and entry[2] == "nfs":
					server = entry[0].split(':')
					if len(server) == 2:
						print("[FlashExpander] server %s" % server)
						_list.append(("Server (%s) - Path (%s)" % (server[0], server[1]), server))
		except Exception as error:
			print("[FlashExpander] Error <getMountPoints>: %s" % str(error))

		if len(_list) == 0:
			_list.append((_("No HDD-, SSD- or USB-Device found. Please first initialized."), None))

		self["list"] = MenuList(list=_list)
		self.Console = Console()

	def Ok(self):
		sel = self["list"].getCurrent()
		if sel and sel[1]:
			if len(sel[1]) == 3:  # Device
				tstr = _("Are you sure want to create FlashExpander on\n%s\nPartition %d") % (sel[1][0].model(), sel[1][1])
				self.session.openWithCallback(boundFunction(self.__startFE_device, sel[1]), MessageBox, tstr)
			if len(sel[1]) == 2:  # Server
				tstr = _("Are you sure want to create FlashExpander on \nServer: %s\nPath: %s") % (sel[1][0], sel[1][1])
				self.session.openWithCallback(boundFunction(self.__startFE_server, sel[1]), MessageBox, tstr)

	def __getPartitionType(self, device):
		fstype = None
		try:
			if exists("/lib/udev/vol_id"):
				val = os_popen("/lib/udev/vol_id --type " + device)
				fstype = val.read().strip()
			elif exists("/sbin/blkid"):
				for line in os_popen("/sbin/blkid " + device).read().split('\n'):
					if not line.startswith(device):
						continue
					fstobj = search(r' TYPE="((?:[^"\\]|\\.)*)"', line)
					if fstobj:
						fstype = fstobj.group(1)
		except:
			print("[FlashExpander] <error get fstype>")
			return False
		return fstype

	def __getPartitionUUID(self, device):
		try:
			if exists("/dev/disk/by-uuid"):
				for uuid in listdir("/dev/disk/by-uuid/"):
					uuidPath = join("/dev/disk/by-uuid", uuid)
					if not exists(uuidPath):
						return None
					if realpath(uuidPath) == device:
						return uuidPath
			else:
				#Topfi begin (use more reliable UUID mount on boxes without /dev/disk/by-uuid)
				p = Popen(["blkid", "-o", "udev", device], stdout=PIPE, stderr=PIPE, stdin=PIPE)
				txtUUID = p.stdout.read()
				start = txtUUID.find(b"ID_FS_UUID=")
				if start > -1:
					txtUUID = txtUUID[start + 11:]
					end = txtUUID.find(b"\n")
					if end > -1:
						txtUUID = txtUUID[:end]
					return b"UUID=" + txtUUID
				#Topfi end
				return device
		except:
			print("[FlashExpander] <error get UUID>")
		return None

	def __startFE_device(self, val, result):
		if result:
			partitionPath = val[0].partitionPath(str(val[1]))
			uuidPath = self.__getPartitionUUID(partitionPath)
			fstype = val[2]
			print("[FlashExpander] %s %s %s" % (partitionPath, uuidPath, fstype))

			if uuidPath is None:
				self.session.open(MessageBox, _("read UUID"), MessageBox.TYPE_ERROR, timeout=5)
				return

			mountpoint = ismounted(uuidPath, "")
			if mountpoint is False:
				mountpoint = ismounted(partitionPath, "")
				if mountpoint is False and self.__mount(uuidPath, "/media/FEtmp") == 0:
					mountpoint = "/media/FEtmp"

			self.__copyFlash(mountpoint, (partitionPath, uuidPath, fstype))
			#if self.__checkMountPoint(mountpoint):
			#	cmd = "rm -rf %s/* && cp -a /usr/* %s/" % (mountpoint, mountpoint)
			#	self.Console.ePopen(cmd, self.__CopyFinished)
			#	self.messageBox = self.session.openWithCallback(boundFunction(self.__EndCB,(partitionPath,uuidPath,fstype)), MessageBox, _("Please wait, Flash memory will be copied."), MessageBox.TYPE_INFO,enable_input=False)

	def __startFE_server(self, val, result):
		if result:
			serverPath = "%s:%s" % (val[0], val[1])
			print("[FlashExpander] %s" % serverPath)
			mountpoint = ismounted(serverPath, "")
			self.__copyFlash(mountpoint, (serverPath, None, "nfs"))
			#if self.__checkMountPoint(mountpoint):
			#	cmd = "rm -rf %s/* && cp -a /usr/* %s/" % (mountpoint, mountpoint)
			#	self.Console.ePopen(cmd, self.__CopyFinished)
			#	self.messageBox = self.session.openWithCallback(boundFunction(self.__EndCB,("%s:%s" %(server,path),None,"nfs")), MessageBox, _("Please wait, Flash memory will be copied."), MessageBox.TYPE_INFO,enable_input=False)

	def __copyFlash(self, mp, data):
		if self.__checkMountPoint(mp):
			cmd = "cp -af /usr/* %s/" % (mp)
			self.Console.ePopen(cmd, self.__CopyFinished)
			self.messageBox = self.session.openWithCallback(boundFunction(self.__EndCB, data), MessageBox, _("Please wait, Flash memory will be copied."), MessageBox.TYPE_INFO, enable_input=False)

	def __mount(self, dev, mp):
		if exists(mp) is False:
			createDir(mp, True)
		cmd = "mount " + dev + " " + mp
		#print("[FlashExpander]",cmd)
		res = system(cmd)
		return (res >> 8)

	def __checkMountPoint(self, mp):
		if mp is False:
			self.session.open(MessageBox, _("Mount failed (%s)") % mp, MessageBox.TYPE_ERROR, timeout=5)
			return False
		if getFreeSize(mp) < 180:
			self.session.open(MessageBox, _("Too little free space < 180MB or wrong Filesystem!"), MessageBox.TYPE_ERROR, timeout=5)
			return False
		return True

	def __CopyFinished(self, result, retval, extra_args=None):
		if retval == 0:
			self.messageBox.close(True)
		else:
			self.messageBox.close(False)

	def __EndCB(self, val, retval):
		if retval:
			try:
				devPath = val[0]
				uuidPath = val[1].decode('utf-8')
				fstype = val[2]

				#fstab editieren
				fstabItems = []
				with open('/etc/fstab') as fp:
					fstabItems = fp.read().split('\n')
				newlines = []
				for x in fstabItems:
					if x.startswith(devPath) or x.startswith("/dev/hdc1"):  # /dev/hdc1 wegen 7025+
						continue
					if uuidPath and x.startswith(uuidPath):
						continue
					if len(x) > 1 and x[0] != '#':
						newlines.append(x)
				if fstype == "nfs":
					newlines.append("%s\t/usr\t%s\trw,nolock,timeo=14,intr\t0 0" % (devPath, fstype))
				else:
					newlines.append("%s\t/usr\tauto\tdefaults\t0 0" % (uuidPath))
				with open("/etc/fstab", 'w') as fp:
					fp.write("#automatically edited by FlashExpander\n")
					for x in newlines:
						fp.write(x + "\n")
				print("[FlashExpander] write new /etc/fstab")
				self.session.openWithCallback(self.Exit, MessageBox, _("Do you want to reboot your STB_BOX?"))
			except:
				self.session.open(MessageBox, _("error adding fstab entry for: %s") % (devPath), MessageBox.TYPE_ERROR, timeout=5)
				return
		else:
			self.session.open(MessageBox, _("error copy flash memory"), MessageBox.TYPE_ERROR, timeout=10)

	def Exit(self, data=False):
		self.close(data)

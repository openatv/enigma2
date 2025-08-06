from glob import glob
from os import system, stat, remove, rename
from os.path import exists, normpath
from stat import ST_SIZE
from enigma import eTimer

from Components.ActionMap import ActionMap
from Components.config import config, configfile, ConfigYesNo
from Components.Console import Console
from Components.Harddisk import harddiskmanager, getProcMounts
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Sources.StaticText import StaticText
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen

config.usage.swapautostart = ConfigYesNo(default=False)

startswap = None


def SwapAutostart():
	global startswap
	if config.usage.swapautostart.value:
		print("[SwapManager] autostart")
		startswap = StartSwap()
		startswap.start()


class StartSwap:
	def __init__(self):
		self.Console = Console()

	def start(self):
		self.Console.ePopen("sfdisk -l /dev/mmcblk* 2>/dev/null | grep swap; sfdisk -l /dev/sd? 2>/dev/null | grep swap", self.startSwap2)

	def startSwap2(self, result=None, retval=None, extra_args=None):
		if result is not None:
			if isinstance(result, bytes):
				result = result.decode(encoding="utf-8", errors="strict")
		swapPlace = ""
		if result and ("sd" in result or "mmcblk" in result):
			for line in result.split("\n"):
				if "sd" in line or "mmcblk" in line:
					parts = line.strip().split()
					swapPlace = parts[0]
					open("/etc/fstab.tmp", "w").writelines([l for l in open("/etc/fstab").readlines() if swapPlace not in l])
					rename("/etc/fstab.tmp", "/etc/fstab")
					print(f"[SwapManager] Found a swap partition:{swapPlace}")
		else:
			devicelist = []
			for p in harddiskmanager.getMountedPartitions():
				d = normpath(p.mountpoint)
				if exists(p.mountpoint) and p.mountpoint != "/" and not p.mountpoint.startswith("/media/net") and not p.mountpoint.startswith("/media/autofs"):
					devicelist.append((p.description, d))
			if devicelist:
				for device in devicelist:
					for filename in glob(device[1] + "/swap*"):
						if exists(filename):
							swapPlace = filename
							print(f"[SwapManager] Found a swapfile on {swapPlace}")

		f = open("/proc/swaps").read()
		if f.find(swapPlace) == -1:
			print(f"[SwapManager] Starting swapfile on {swapPlace}")
			system(f"swapon {swapPlace}")
		else:
			print(f"[SwapManager] Swapfile is already active on {swapPlace}")

#######################################################################


class Swap(Screen):
	skin = """
	<screen name="Swap" position="center,center" size="420,250" title="Swap File Manager" flags="wfBorder" resolution="1280,720">
		<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
		<widget name="key_red" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		<widget name="key_green" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		<widget name="key_yellow" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
		<widget name="autostart_off" position="10,50" zPosition="1" pixmap="skin_default/icons/lock_off.png" size="32,32" alphatest="on" />
		<widget name="autostart_on" position="10,50" zPosition="2" pixmap="skin_default/icons/lock_on.png" size="32,32" alphatest="on" />
		<widget name="lab1" position="50,50" size="360,30" font="Regular;20" valign="center" transparent="1"/>
		<widget name="lab2" position="10,100" size="150,30" font="Regular;20" valign="center" transparent="1"/>
		<widget name="lab3" position="10,150" size="150,30" font="Regular;20" valign="center" transparent="1"/>
		<widget name="lab4" position="10,200" size="150,30" font="Regular;20" valign="center" transparent="1" />
		<widget name="labplace" position="160,100" size="220,30" font="Regular;20" valign="center" backgroundColor="#4D5375"/>
		<widget name="labsize" position="160,150" size="220,30" font="Regular;20" valign="center" backgroundColor="#4D5375"/>
		<widget name="inactive" position="160,200" size="100,30" font="Regular;20" valign="center" halign="center" backgroundColor="red"/>
		<widget name="active" position="160,200" size="100,30" font="Regular;20" valign="center" halign="center" backgroundColor="green"/>
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("Swap Manager"))
		self["lab1"] = Label()
		self["autostart_on"] = Pixmap()
		self["autostart_off"] = Pixmap()
		self["lab2"] = Label(_("Swap Place:"))
		self["labplace"] = Label()
		self["lab3"] = Label(_("Swap Size:"))
		self["labsize"] = Label()
		self["lab4"] = Label(_("Status:"))
		self["inactive"] = Label(_("Inactive"))
		self["active"] = Label(_("Active"))
		self["key_red"] = Label(_("Activate"))
		self["key_green"] = Label(_("Create"))
		self["key_yellow"] = Label(_("Autostart"))
		self["swapname_summary"] = StaticText()
		self["swapactive_summary"] = StaticText()
		self.Console = Console()
		self.swapPlace = ""
		self.newPlace = ""
		self.creatingswap = False
		self["actions"] = ActionMap(["WizardActions", "ColorActions", "MenuActions"], {
			"back": self.close,
			"red": self.actDeact,
			"green": self.createDel,
			"yellow": self.autoSsWap,
			"menu": self.close
		})
		self.activityTimer = eTimer()
		self.activityTimer.timeout.get().append(self.getSwapDevice)
		self.updateSwap()

	def updateSwap(self, result=None, retval=None, extra_args=None):
		self["actions"].setEnabled(False)
		self.swapActive = False
		self["autostart_on"].hide()
		self["autostart_off"].show()
		self["active"].hide()
		self["inactive"].show()
		self["labplace"].hide()
		self["labsize"].hide()
		self["swapactive_summary"].setText(_("Current Status:"))
		scanning = _("Wait please while scanning...")
		self["lab1"].setText(scanning)
		self.activityTimer.start(10)

	def getSwapDevice(self):
		self.activityTimer.stop()
		if exists("/etc/rcS.d/S98SwapManager"):
			remove("/etc/rcS.d/S98SwapManager")
			config.usage.swapautostart.value = True
			config.usage.swapautostart.save()
		if exists("/tmp/swapdevices.tmp"):
			remove("/tmp/swapdevices.tmp")

		self.Console.ePopen("sfdisk -l /dev/mmcblk* 2>/dev/null | grep swap; sfdisk -l /dev/sd? 2>/dev/null | grep swap", self.updateSwap2)

	def updateSwap2(self, result=None, retval=None, extra_args=None):
		if result is not None and isinstance(result, bytes):
			result = result.decode(encoding="utf-8", errors="strict")

		self.swapsize = 0
		self.swapPlace = ""
		self.swapActive = False
		self.device = False

		if result and ("sd" in result or "mmcblk" in result):
			self["key_green"].setText("")
			for line in result.split("\n"):
				if "sd" in line or "mmcblk" in line:
					parts = line.strip().split()
					self.swapPlace = parts[0]
					if self.swapPlace == "sfdisk:":
						self.swapPlace = ""
					self.device = True

			with open("/proc/swaps") as f:
				for line in f:
					parts = line.strip().split()
					if line.find("partition") != -1:
						self.swapActive = True
						if len(parts) >= 3 and parts[2].isdigit():
							self.swapsize = int(parts[2])
		else:
			self["key_green"].setText(_("Create"))
			devicelist = []
			for p in harddiskmanager.getMountedPartitions():
				d = normpath(p.mountpoint)
				if exists(p.mountpoint) and p.mountpoint != "/" and not p.mountpoint.startswith("/media/net") and not p.mountpoint.startswith("/media/autofs"):
					devicelist.append((p.description, d))

			for device in devicelist:
				for filename in glob(device[1] + "/swap*"):
					self.swapPlace = filename
					self["key_green"].setText(_("Delete"))
					info = stat(self.swapPlace)
					self.swapsize = int(info[ST_SIZE]) // 1024

		if config.usage.swapautostart.value and self.swapPlace:
			self["autostart_off"].hide()
			self["autostart_on"].show()
		else:
			config.usage.swapautostart.value = False
			config.usage.swapautostart.save()
			configfile.save()
			self["autostart_on"].hide()
			self["autostart_off"].show()
		self["labplace"].setText(self.swapPlace)
		self["labplace"].show()

		with open("/proc/swaps") as f:
			for line in f:
				if "partition" in line or "file" in line:
					self.swapActive = True

		if self.swapsize > 0:
			displaySize = self.swapsize
			unit = "KB"
			if displaySize >= 1024:
				displaySize //= 1024
				unit = "MB"
				if displaySize >= 1024:
					displaySize //= 1024
					unit = "GB"
			self["labsize"].setText(f"{displaySize} {unit}")
		else:
			self["labsize"].setText("")

		self["labsize"].show()

		if self.swapActive is True:
			self["inactive"].hide()
			self["active"].show()
			self["key_red"].setText(_("Deactivate"))
			self["swapactive_summary"].setText(f"{_("Current Status: ")} {_("Active")}")
		else:
			self["inactive"].show()
			self["active"].hide()
			self["key_red"].setText(_("Activate"))
			self["swapactive_summary"].setText(f"{_("Current Status: ")} {_("Inactive")}")

		scanning = _("Enable Swap at startup")
		self["lab1"].setText(scanning)
		self["lab1"].show()
		self["actions"].setEnabled(True)

		name = self["labplace"].text
		self["swapname_summary"].setText(name)

	def actDeact(self):
		if self.swapActive is True:
			self.Console.ePopen(f"swapoff {self.swapPlace}", self.updateSwap)
		else:
			if not self.device:
				if self.swapPlace:
					self.Console.ePopen(f"swapon {self.swapPlace}", self.updateSwap)
				else:
					mybox = self.session.open(MessageBox, _("Swap File not found. You have to create the file before to activate."), MessageBox.TYPE_INFO)
					mybox.setTitle(_("Info"))
			else:
				self.Console.ePopen("swapon " + self.swapPlace, self.updateSwap)

	def createDel(self):
		if not self.device:
			if self.swapPlace:
				if self.swapActive is True:
					self.Console.ePopen(f"swapoff {self.swapPlace}", self.createDel2)
				else:
					self.createDel2(None, 0)
			else:
				self.doCreateSwap()

	def createDel2(self, result, retval, extra_args=None):
		if retval == 0:
			remove(self.swapPlace)
			if config.usage.swapautostart.value:
				config.usage.swapautostart.value = False
				config.usage.swapautostart.save()
				configfile.save()
			self.updateSwap()

	def doCreateSwap(self):
		supportedFileSystems = frozenset(("ext4", "ext3", "ext2", "vfat"))
		candidates = []
		mounts = getProcMounts()
		for partition in harddiskmanager.getMountedPartitions(False, mounts):
			if partition.fileSystem(mounts) in supportedFileSystems:
				candidates.append((partition.description, partition.mountpoint))
		if len(candidates):
			self.session.openWithCallback(self.doCSplace, ChoiceBox, title=_("Please select device to use as swap file location"), list=candidates)
		else:
			self.session.open(MessageBox, _("Sorry, no physical devices that supports SWAP attached. Can't create swap file on network or FAT32 file systems"), MessageBox.TYPE_INFO, timeout=10)

	def doCSplace(self, name):
		if name:
			self.newPlace = name[1]
			myoptions = [[_("%d MB") % s, str(s * 1024)] for s in (32, 64, 128, 256, 512, 1024, 1536, 2048)]
			self.session.openWithCallback(self.doCSsize, ChoiceBox, title=_("Select the Swap File Size:"), list=myoptions)

	def doCSsize(self, swapsize):
		if swapsize:
			self["actions"].setEnabled(False)
			scanning = _("Wait please while creating swap file...")
			self["lab1"].setText(scanning)
			self["lab1"].show()
			swapsize = swapsize[1]
			myfile = self.newPlace + "/swapfile"
			self.commands = []
			self.commands.append(f"dd if=/dev/zero of={myfile} bs=1024 count={swapsize} 2>/dev/null")
			self.commands.append(f"mkswap {myfile}")
			self.Console.eBatch(self.commands, self.updateSwap, debug=True)

	def autoSsWap(self):
		if self.swapPlace:
			config.usage.swapautostart.value = not config.usage.swapautostart.value
			config.usage.swapautostart.save()
			configfile.save()
		else:
			mybox = self.session.open(MessageBox, _("You have to create a Swap File before to activate the autostart."), MessageBox.TYPE_INFO)
			mybox.setTitle(_("Info"))
		self.updateSwap()

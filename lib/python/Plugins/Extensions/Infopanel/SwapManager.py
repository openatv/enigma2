# for localized messages
from . import _

from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Components.config import config, configfile, ConfigYesNo, ConfigSubsection
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Harddisk import harddiskmanager, getProcMounts
from Components.Console import Console
from Components.Sources.StaticText import StaticText
from os import system, stat as mystat, path, remove, rename
from enigma import eTimer
from glob import glob
import stat

config.plugins.infopanel = ConfigSubsection()
config.plugins.infopanel.swapautostart = ConfigYesNo(default = False)

startswap = None

def SwapAutostart(reason, session=None, **kwargs):
	global startswap
	if reason == 0:
		if config.plugins.infopanel.swapautostart.value:
			print "[SwapManager] autostart"
			startswap = StartSwap()
			startswap.start()
	
class StartSwap:
	def __init__(self):
		self.Console = Console()

	def start(self):
	 	self.Console.ePopen("sfdisk -l /dev/sd? 2>/dev/null | grep swap", self.startSwap2)

	def startSwap2(self, result = None, retval = None, extra_args = None):
		swap_place = ""
		if result and result.find('sd') != -1:
			for line in result.split('\n'):
				if line.find('sd') != -1:
					parts = line.strip().split()
					swap_place = parts[0]
					file('/etc/fstab.tmp', 'w').writelines([l for l in file('/etc/fstab').readlines() if swap_place not in l])
					rename('/etc/fstab.tmp','/etc/fstab')
					print "[SwapManager] Found a swap partition:", swap_place
		else:
			devicelist = []
			for p in harddiskmanager.getMountedPartitions():
				d = path.normpath(p.mountpoint)
				if path.exists(p.mountpoint) and p.mountpoint != "/" and not p.mountpoint.startswith('/media/net'):
					devicelist.append((p.description, d))
			if len(devicelist):
				for device in devicelist:
					for filename in glob(device[1] + '/swap*'):
						if path.exists(filename):
							swap_place = filename
							print "[SwapManager] Found a swapfile on ", swap_place

		f = file('/proc/swaps').read()
		if f.find(swap_place) == -1:
			print "[SwapManager] Starting swapfile on ", swap_place
			system('swapon ' + swap_place)
		else:
			print "[SwapManager] Swapfile is already active on ", swap_place
	
#######################################################################
class Swap(Screen):
	skin = """
	<screen name="Swap" position="center,center" size="420,250" title="Swap File Manager" flags="wfBorder" >
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
		Screen.setTitle(self, _("Swap Manager"))
		self['lab1'] = Label()
		self['autostart_on'] = Pixmap()
		self['autostart_off'] = Pixmap()
		self['lab2'] = Label(_("Swap Place:"))
		self['labplace'] = Label()
		self['lab3'] = Label(_("Swap Size:"))
		self['labsize'] = Label()
		self['lab4'] = Label(_("Status:"))
		self['inactive'] = Label(_("Inactive"))
		self['active'] = Label(_("Active"))
		self['key_red'] = Label(_("Activate"))
		self['key_green'] = Label(_("Create"))
		self['key_yellow'] = Label(_("Autostart"))
		self['swapname_summary'] = StaticText()
		self['swapactive_summary'] = StaticText()
		self.Console = Console()
		self.swap_place = ''
		self.new_place = ''
		self.creatingswap = False
		self['actions'] = ActionMap(['WizardActions', 'ColorActions', "MenuActions"], {'back': self.close, 'red': self.actDeact, 'green': self.createDel, 'yellow': self.autoSsWap, "menu": self.close})
		self.activityTimer = eTimer()
		self.activityTimer.timeout.get().append(self.getSwapDevice)
		self.updateSwap()

	def updateSwap(self, result = None, retval = None, extra_args = None):
		self["actions"].setEnabled(False)
		self.swap_active = False
		self['autostart_on'].hide()
		self['autostart_off'].show()
		self['active'].hide()
		self['inactive'].show()
		self['labplace'].hide()
		self['labsize'].hide()
		self['swapactive_summary'].setText(_("Current Status:"))
		scanning = _("Wait please while scanning...")
		self['lab1'].setText(scanning)
		self.activityTimer.start(10)

	def getSwapDevice(self):
		self.activityTimer.stop()
		if path.exists('/etc/rcS.d/S98SwapManager'):
			remove('/etc/rcS.d/S98SwapManager')
			config.plugins.infopanel.swapautostart.value = True
			config.plugins.infopanel.swapautostart.save()
		if path.exists('/tmp/swapdevices.tmp'):
			remove('/tmp/swapdevices.tmp')
		self.Console.ePopen("sfdisk -l /dev/sd? 2>/dev/null | grep swap", self.updateSwap2)

	def updateSwap2(self, result = None, retval = None, extra_args = None):
		self.swapsize = 0
		self.swap_place = ''
		self.swap_active = False
		self.device = False
		if result.find('sd') > 0:
			self['key_green'].setText("")
			for line in result.split('\n'):
				if line.find('sd') > 0:
					parts = line.strip().split()
					self.swap_place = parts[0]
					if self.swap_place == 'sfdisk:':
						self.swap_place = ''
					self.device = True
				f = open('/proc/swaps', 'r')
				for line in f.readlines():
					parts = line.strip().split()
					if line.find('partition') != -1:
						self.swap_active = True
						self.swapsize = parts[2]
						continue
				f.close()
		else:
			self['key_green'].setText(_("Create"))
			devicelist = []
			for p in harddiskmanager.getMountedPartitions():
				d = path.normpath(p.mountpoint)
				if path.exists(p.mountpoint) and p.mountpoint != "/" and not p.mountpoint.startswith('/media/net'):
					devicelist.append((p.description, d))
			if len(devicelist):
				for device in devicelist:
					for filename in glob(device[1] + '/swap*'):
						self.swap_place = filename
						self['key_green'].setText(_("Delete"))
						info = mystat(self.swap_place)
						self.swapsize = info[stat.ST_SIZE]
						continue

		if config.plugins.infopanel.swapautostart.value and self.swap_place:
			self['autostart_off'].hide()
			self['autostart_on'].show()
		else:
			config.plugins.infopanel.swapautostart.value = False
			config.plugins.infopanel.swapautostart.save()
			configfile.save()
			self['autostart_on'].hide()
			self['autostart_off'].show()
		self['labplace'].setText(self.swap_place)
		self['labplace'].show()

		f = open('/proc/swaps', 'r')
		for line in f.readlines():
			parts = line.strip().split()
			if line.find('partition') != -1:
				self.swap_active = True
				continue
			elif line.find('file') != -1:
				self.swap_active = True
				continue
		f.close()

		if self.swapsize > 0:
			if self.swapsize >= 1024:
				self.swapsize = int(self.swapsize) / 1024
				if self.swapsize >= 1024:
					self.swapsize = int(self.swapsize) / 1024
				self.swapsize = str(self.swapsize) + ' ' + 'MB'
			else:
				self.swapsize = str(self.swapsize) + ' ' + 'KB'
		else:
			self.swapsize = ''

		self['labsize'].setText(self.swapsize)
		self['labsize'].show()

		if self.swap_active == True:
			self['inactive'].hide()
			self['active'].show()
			self['key_red'].setText(_("Deactivate"))
			self['swapactive_summary'].setText(_("Current Status:") + ' ' + _("Active"))
		else:
			self['inactive'].show()
			self['active'].hide()
			self['key_red'].setText(_("Activate"))
			self['swapactive_summary'].setText(_("Current Status:") + ' ' + _("Inactive"))

		scanning = _("Enable Swap at startup")
		self['lab1'].setText(scanning)
		self['lab1'].show()
		self["actions"].setEnabled(True)

		name = self['labplace'].text
		self['swapname_summary'].setText(name)

	def actDeact(self):
		if self.swap_active == True:
			self.Console.ePopen('swapoff ' + self.swap_place, self.updateSwap)
		else:
			if not self.device:
				if self.swap_place != '':
					self.Console.ePopen('swapon ' + self.swap_place, self.updateSwap)
				else:
					mybox = self.session.open(MessageBox, _("Swap File not found. You have to create the file before to activate."), MessageBox.TYPE_INFO)
					mybox.setTitle(_("Info"))
			else:
				self.Console.ePopen('swapon ' + self.swap_place, self.updateSwap)

	def createDel(self):
		if not self.device:
			if self.swap_place != '':
				if self.swap_active == True:
					self.Console.ePopen('swapoff ' + self.swap_place, self.createDel2)
				else:
					self.createDel2(None, 0)
			else:
				self.doCreateSwap()

	def createDel2(self, result, retval, extra_args = None):
		if retval == 0:
			remove(self.swap_place)
			if config.plugins.infopanel.swapautostart.value:
				config.plugins.infopanel.swapautostart.value = False
				config.plugins.infopanel.swapautostart.save()
				configfile.save()
			self.updateSwap()

	def doCreateSwap(self):
		parts = []
		supported_filesystems = frozenset(('ext4', 'ext3', 'ext2', 'vfat'))
		candidates = []
		mounts = getProcMounts() 
		for partition in harddiskmanager.getMountedPartitions(False, mounts):
			if partition.filesystem(mounts) in supported_filesystems:
				candidates.append((partition.description, partition.mountpoint)) 
		if len(candidates):
			self.session.openWithCallback(self.doCSplace, ChoiceBox, title = _("Please select device to use as swapfile location"), list = candidates)
		else:
			self.session.open(MessageBox, _("Sorry, no physical devices that supports SWAP attached. Can't create Swapfile on network or fat32 filesystems"), MessageBox.TYPE_INFO, timeout = 10)

	def doCSplace(self, name):
		if name:
			self.new_place = name[1]
			myoptions = [[_("32 Mb"), '32768'], [_("64 Mb"), '65536'], [_("128 Mb"), '131072'], [_("256 Mb"), '262144'], [_("512 Mb"), '524288']]
			self.session.openWithCallback(self.doCSsize, ChoiceBox, title=_("Select the Swap File Size:"), list=myoptions)

	def doCSsize(self, swapsize):
		if swapsize:
			self["actions"].setEnabled(False)
			scanning = _("Wait please while creating swapfile...")
			self['lab1'].setText(scanning)
			self['lab1'].show()
			swapsize = swapsize[1]
			myfile = self.new_place + '/swapfile'
			self.commands = []
			self.commands.append('dd if=/dev/zero of=' + myfile + ' bs=1024 count=' + swapsize + ' 2>/dev/null')
			self.commands.append('mkswap ' + myfile)
			self.Console.eBatch(self.commands, self.updateSwap, debug=True)
		
	def autoSsWap(self):
		if self.swap_place:
			if config.plugins.infopanel.swapautostart.value:
				config.plugins.infopanel.swapautostart.value = False
				config.plugins.infopanel.swapautostart.save()
			else:
				config.plugins.infopanel.swapautostart.value = True
				config.plugins.infopanel.swapautostart.save()
			configfile.save()
		else:
			mybox = self.session.open(MessageBox, _("You have to create a Swap File before to activate the autostart."), MessageBox.TYPE_INFO)
			mybox.setTitle(_("Info"))
		self.updateSwap()

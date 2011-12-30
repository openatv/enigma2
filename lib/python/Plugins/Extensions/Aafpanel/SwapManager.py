# for localized messages
from . import _
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Components.config import getConfigListEntry, config, ConfigSubsection, ConfigYesNo, ConfigText, ConfigSelection, ConfigInteger, ConfigClock, NoSave, configfile
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Harddisk import harddiskmanager
from Components.Console import Console
from Components.config import config
from Components.Language import language
from Tools.Directories import fileExists, resolveFilename, SCOPE_PLUGINS, SCOPE_CURRENT_SKIN
from os import system, stat as mystat, chmod, path, remove, rename, access, W_OK, R_OK, F_OK, environ
from enigma import eTimer
import stat, time

config.plugins.aafpanel = ConfigSubsection()
config.plugins.aafpanel.swapautostart = ConfigYesNo(default = False)

def SwapAutostart(reason, session = None):
	if reason == 0:
		global device
		print "[SwapManager] autostart"
		f = open('/etc/fstab', 'r')
		for line in f.readlines():
			if line.find('swap') != -1:
				parts = line.strip().split()
				device = parts[0]
				print "[SwapManager] Found a swap partition on ", device
				swapf = file('/proc/swaps').read()
				if swapf.find(device) < 0:
					print "[SwapManager] Starting swap partition on ", device
					system('swapon ' + device)
				else:
					print "[SwapManager] Swap partition %s is already active.", device
		f.close()

		if config.plugins.aafpanel.swapautostart.value:
			swap_place = ''
			parts = []
			for p in harddiskmanager.getMountedPartitions():
				d = path.normpath(p.mountpoint)
				if path.exists(p.mountpoint) and p.mountpoint != "/":
					parts.append((p.description, d))
			if len(parts):
				for x in parts:
					if path.exists(x[1] + '/swapfile'):
						swap_place = x[1] + '/swapfile'
						print "[SwapManager] Found a swapfile on ", swap_place
						f = file('/proc/swaps').read()
						if f.find('swap_place') < 0:
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
		self.Console = Console()
		self.swap_place = ''
		self.new_place = ''
		self.creatingswap = False
		self['actions'] = ActionMap(['WizardActions', 'ColorActions'], {'back': self.close, 'red': self.actDeact, 'green': self.createDel, 'yellow': self.autoSsWap})
		self.activityTimer = eTimer()
		self.activityTimer.timeout.get().append(self.getSwapDevice)
		self.updateSwap()

	def updateSwap(self, result = None, retval = None, extra_args = None):
		self.swap_active = False
		self.autos_start = False
		self['autostart_on'].hide()
		self['autostart_off'].show()
		self['active'].hide()
		self['inactive'].show()
		self['labplace'].hide()
		self['labsize'].hide()
		scanning = _("Wait please while scanning...")
		self['lab1'].setText(scanning)
		self.activityTimer.start(10)

	def getSwapDevice(self):
		self.activityTimer.stop()
		if path.exists('/etc/rcS.d/S98SwapManager'):
			remove('/etc/rcS.d/S98SwapManager')
			config.plugins.aafpanel.swapautostart.value = True
			config.plugins.aafpanel.swapautostart.save()
		if path.exists('/tmp/swapdevices.tmp'):
			remove('/tmp/swapdevices.tmp')
		self.Console.ePopen("fdisk -l /dev/sd? | grep swap >/tmp/swapdevices.tmp", self.updateSwap2)

	def updateSwap2(self, result, retval, extra_args):
		global device
		device = ""
		if retval == 0:
			f = open('/tmp/swapdevices.tmp', 'r')
			for line in f.readlines():
				if line.find('sd') > 0:
					parts = line.strip().split()
					device = parts[0]
					continue
			f.close()
	
			self.swap_active = False
			self.autos_start = False
			self['labplace'].setText(device)
			self['labplace'].show()
			f = open('/etc/fstab', 'r')
			for line in f.readlines():
				if line.find('swap') > 0:
					self.autos_start = True
					self['autostart_off'].hide()
					self['autostart_on'].show()
					continue
			f.close()
			f = open('/proc/swaps', 'r')
			for line in f.readlines():
				if line.find('sd') > 0:
					self.swap_active = True
					parts = line.strip().split()
					size = parts[2]
					continue
			f.close()
			if self.swap_active == True:
				filesize = int(size) / 1024
				filesize = str(filesize) + ' M'
				self['labsize'].setText(filesize)
				self['labsize'].show()
				self['inactive'].hide()
				self['active'].show()
				self['key_red'].setText(_("Deactivate"))
			else:
				self['inactive'].show()
				self['active'].hide()
				self['key_red'].setText(_("Activate"))
			self['key_green'].setText(_(" "))
		else:
			self['key_green'].setText(_("Create"))
			if config.plugins.aafpanel.swapautostart.value:
				self['autostart_off'].hide()
				self['autostart_on'].show()
				self.autos_start = True
			else:
				self['autostart_on'].hide()
				self['autostart_off'].show()
			fileplace = ''
			self.swap_place = ''
			parts = []
			for p in harddiskmanager.getMountedPartitions():
				d = path.normpath(p.mountpoint)
				if path.exists(p.mountpoint) and p.mountpoint != "/" and not p.mountpoint.startswith('/media/net'):
					parts.append((p.description, d))
			if len(parts):
				for x in parts:
					if path.exists(x[1] + '/swapfile'):
						fileplace = x[0]
						self.swap_place = x[1] + '/swapfile'
						filesize = 0
						if fileplace != '':
							self['key_green'].setText(_("Delete"))
							info = mystat(self.swap_place)
							filesize = info[stat.ST_SIZE]
						if filesize > 1048576:
							filesize = filesize / 1048576
						filesize = str(filesize) + ' M'
						self['labplace'].setText(fileplace)
						self['labplace'].show()
						self['labsize'].setText(filesize)
						self['labsize'].show()
						f = open('/proc/swaps', 'r')
						for line in f.readlines():
							if line.find('swapfile') != -1:
								self.swap_active = True
								continue
						f.close()
						if self.swap_active == True:
							self['active'].show()
							self['key_red'].setText(_("Deactivate"))
						else:
							self['inactive'].show()
							self['key_red'].setText(_("Activate"))
		scanning = _("Enable Swap at startup")
		self['lab1'].setText(scanning)
		self['lab1'].show()

	def actDeact(self):
		global device
		if device == "":
			if self.swap_active == True:
				self.Console.ePopen('swapoff ' + self.swap_place, self.updateSwap)
			else:
				if self.swap_place != '':
					self.commands = []
					self.commands.append('mkswap ' + self.swap_place)
					self.commands.append('swapon ' + self.swap_place)
					self.Console.eBatch(self.commands, self.updateSwap, debug=True)
				else:
					mybox = self.session.open(MessageBox, _("Swap File not found. You have to create the file before to activate."), MessageBox.TYPE_INFO)
					mybox.setTitle(_("Info"))
		else:
			if self.swap_active == True:
				self.Console.ePopen('swapoff ' + device, self.updateSwap)
			else:
				self.Console.ePopen('swapon ' + device, self.updateSwap)

	def createDel(self):
		global device
		if device == "":
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
			if config.plugins.aafpanel.swapautostart.value:
				config.plugins.aafpanel.swapautostart.value = False
				config.plugins.aafpanel.swapautostart.save()
			self.updateSwap()

	def doCreateSwap(self):
		parts = []
		for p in harddiskmanager.getMountedPartitions():
			d = path.normpath(p.mountpoint)
			if path.exists(p.mountpoint) and p.mountpoint != "/"  and not p.mountpoint.startswith('/media/net'):
				parts.append((p.description, d))
		if len(parts):
			self.session.openWithCallback(self.doCSplace, ChoiceBox, title = _("Please select device to use as swapfile location"), list = parts)

	def doCSplace(self, name):
		if name:
			name
			self.new_place = name[1]
			myoptions = [[_("32 Mb"), '32768'], [_("64 Mb"), '65536'], [_("128 Mb"), '131072'], [_("256 Mb"), '262144'], [_("512 Mb"), '524288']]
			self.session.openWithCallback(self.doCSsize, ChoiceBox, title=_("Select the Swap File Size:"), list=myoptions)
		else:
			name

	def doCSsize(self, size):
		if size:
			size
			size = size[1]
			myfile = self.new_place + '/swapfile'
			self.Console.ePopen('dd if=/dev/zero of=' + myfile + ' bs=1024 count=' + size + ' 2>/dev/null', self.doCScreateCheck)
			self['actions'] = ActionMap()
			scanning = _("Wait please while creating swapfile...")
			self['lab1'].setText(scanning)
			self['lab1'].show()
		else:
			size

	def doCScreateCheck(self, result, retval, extra_args):
		if retval == 0:
			mybox = self.session.open(MessageBox, _("Swap File successfully created."), MessageBox.TYPE_INFO, timeout = 5)
		else:
			mybox = self.session.open(MessageBox, _("Swap File creation Failed. Check for Available space."), MessageBox.TYPE_INFO)
		mybox.setTitle(_("Info"))
		self['actions'] = ActionMap(['WizardActions', 'ColorActions'], {'back': self.close, 'red': self.actDeact, 'green': self.createDel, 'yellow': self.autoSsWap})
		self.updateSwap()
		
	def autoSsWap(self):
		global device
		if device == "":
			if config.plugins.aafpanel.swapautostart.value:
				config.plugins.aafpanel.swapautostart.value = False
				config.plugins.aafpanel.swapautostart.save()
			else:
				if self.swap_place:
					config.plugins.aafpanel.swapautostart.value = True
					config.plugins.aafpanel.swapautostart.save()
				else:
					mybox = self.session.open(MessageBox, _("You have to create a Swap File before to activate the autostart."), MessageBox.TYPE_INFO)
					mybox.setTitle(_("Info"))
			self.updateSwap()
		else:
			swapdevice = ""
			f = open('/etc/fstab', 'r')
			for line in f.readlines():
				if line.find('swap') != -1:
					parts = line.strip().split()
					swapdevice = parts[0]
					break
					continue
			f.close()
			if swapdevice != "":
				file('/etc/fstab.tmp', 'w').writelines([l for l in file('/etc/fstab').readlines() if device not in l])
				rename('/etc/fstab.tmp','/etc/fstab')
			else:
				out = open('/etc/fstab', 'a')
				line = device + '            None                 swap       defaults              0 0\n'
				out.write(line)
				out.close()
			self.updateSwap()

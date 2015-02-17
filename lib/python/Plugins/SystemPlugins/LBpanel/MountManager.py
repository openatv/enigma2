# for localized messages
from Screens.Screen import Screen
from enigma import eTimer
from Screens.MessageBox import MessageBox
from Screens.Standby import TryQuitMainloop
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.ConfigList import ConfigListScreen
from Components.config import getConfigListEntry, config, ConfigSelection, NoSave, configfile
from Components.Console import Console
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Tools.LoadPixmap import LoadPixmap
from os import system, rename, path, mkdir, remove
from time import sleep
from re import search

class LBHddMount(Screen):
	skin = """
	<screen position="0,0" size="1280,720" title="Mount Manager">

		<widget source="list" render="Listbox" position="592,191" scrollbarMode="showNever" foregroundColor="#ffffff" backgroundColor="#6e6e6e" backgroundColorSelected="#fd6502" transparent="1"
size="628,350">
			<convert type="TemplatedMultiContent">
				{"template": [
				 MultiContentEntryText(pos = (90, 0), size = (600, 30), font=0, text = 0),
				 MultiContentEntryText(pos = (110, 30), size = (600, 50), font=1, flags = RT_VALIGN_TOP, text = 1),
				 MultiContentEntryPixmapAlphaBlend(pos = (0, 0), size = (80, 80), png = 2),
				],
				"fonts": [gFont("Regular", 24),gFont("Regular", 20)],
				"itemHeight": 85
				}
			</convert>
		</widget>
		<widget name="lab1" zPosition="2" position="600,400" size="600,40" font="Regular;22" halign="center" transparent="1"/>
<!-- colores keys -->
    <!-- rojo -->
    <eLabel position="622,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#ee1d11" zPosition="-1" />
    <!-- amarillo -->
    <eLabel text="MOUNT" position="622,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,604" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#eefb1a" zPosition="-1" />
    <!-- verde -->
    <eLabel text="SETUP MOUNT" position="912,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="882,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#11b90a" zPosition="-1" />
    <!-- azul -->
    <eLabel text="MOUNT" position="912,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="882,604" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#1a2cfb" zPosition="-1" />
    <!-- fin colores keys -->
    <eLabel text="LBpanel - Red Bee" position="440,34" size="430,65" font="Regular; 42" halign="center" transparent="1" foregroundColor="white" backgroundColor="#140b1" />
    <eLabel text="PULSE EXIT PARA SALIR" position="335,644" size="500,50" font="Regular; 30" zPosition="2" halign="left" noWrap="1" transparent="1" foregroundColor="white" backgroundColor="#8f8f8f" />
    <widget source="Title" transparent="1" render="Label" zPosition="2" valign="center" halign="left" position="80,119" size="600,50" font="Regular; 30" backgroundColor="black" foregroundColor="white" noWrap="1" />
    <widget source="global.CurrentTime" render="Label" position="949,28" size="251,55" backgroundColor="#140b1" foregroundColor="white" transparent="1" zPosition="2" font="Regular;24" valign="center" halign="right" shadowColor="#000000" shadowOffset="-2,-2">
      <convert type="ClockToText">Format:%-H:%M</convert>
    </widget>
    <widget source="global.CurrentTime" render="Label" position="900,50" size="300,55" backgroundColor="#140b1" foregroundColor="white" transparent="1" zPosition="2" font="Regular;16" valign="center" halign="right" shadowColor="#000000" shadowOffset="-2,-2">
      <convert type="ClockToText">Date</convert>
    </widget>
    <widget source="session.VideoPicture" render="Pig" position="64,196" size="375,175" backgroundColor="transparent" zPosition="-1" transparent="0" />
    <widget source="session.CurrentService" render="RunningText" options="movetype=running,startpoint=0,direction=left,steptime=25,repeat=150,startdelay=1500,always=0" position="101,491" size="215,45" font="Regular; 22" transparent="1" valign="center" zPosition="2" backgroundColor="black" foregroundColor="white" noWrap="1" halign="center">
      <convert type="ServiceName">Name</convert>
    </widget>
    <widget source="session.CurrentService" render="Label" zPosition="3" font="Regular; 22" position="66,649" size="215,50" halign="center" backgroundColor="black" transparent="1" noWrap="1" foregroundColor="white">
      <convert type="VtiInfo">TempInfo</convert>
    </widget>
    <eLabel position="192,459" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#ee1d11" zPosition="-1" />
    <eLabel position="251,410" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#1a2cfb" zPosition="-2" />
    <eLabel position="281,449" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#11b90a" zPosition="-6" />
    <eLabel position="233,499" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#eefb1a" zPosition="-5" />
    <eLabel position="60,451" size="65,57" transparent="0" foregroundColor="white" backgroundColor="#ecbc13" zPosition="-6" />
    <eLabel position="96,489" size="229,50" transparent="0" foregroundColor="white" backgroundColor="black" />
    <eLabel position="0,0" size="1280,720" transparent="0" zPosition="-15" backgroundColor="#d6d6d6" />
    <ePixmap position="46,180" zPosition="0" size="413,210" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/marcotv.png" transparent="0" />
    <eLabel position="60,30" size="1160,68" transparent="0" foregroundColor="white" backgroundColor="#42b3" zPosition="-10" />
    <eLabel position="60,120" size="1160,50" transparent="0" foregroundColor="white" backgroundColor="black" />
    <eLabel position="60,640" size="229,50" transparent="0" foregroundColor="white" backgroundColor="black" />
    <eLabel position="320,640" size="901,50" transparent="0" foregroundColor="white" backgroundColor="#929292" />
    <eLabel position="592,191" size="629,370" transparent="0" foregroundColor="white" backgroundColor="#6e6e6e" zPosition="-10" />
   </screen>"""
	
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Lbpanel-Mount Manager"))
		self['lab1'] = Label()
		self.onChangedEntry = [ ]
		self.list = []
		self['list'] = List(self.list)
		self["list"].onSelectionChanged.append(self.selectionChanged)
		self['actions'] = ActionMap(['WizardActions', 'ColorActions', "MenuActions"], {'back': self.close, 'green': self.SetupMounts, 'red': self.saveMypoints, 'yellow': self.Unmount, 'blue': self.Mount, "menu": self.close})
		self.activityTimer = eTimer()
		self.activityTimer.timeout.get().append(self.updateList2)
		self.updateList()

	def createSummary(self):
		return DevicesPanelSummary

	def selectionChanged(self):
		if len(self.list) == 0:
			return
		self.sel = self['list'].getCurrent()
		seldev = self.sel
		for line in self.sel:
			try:
				line = line.strip()
				if line.find('Mount') >= 0:
					if line.find('/media/hdd') < 0:
						self["key_red"].setText(_("Use as HDD"))
				else:
					self["key_red"].setText(" ")
			except:
				pass
		if self.sel:
			try:
				name = str(self.sel[0])
				desc = str(self.sel[1].replace('\t','  '))
			except:
				name = ""
				desc = ""
		else:
			name = ""
			desc = ""
		for cb in self.onChangedEntry:
			cb(name, desc)

	def updateList(self, result = None, retval = None, extra_args = None):
		scanning = _("Wait please while scanning for devices...")
		self['lab1'].setText(scanning)
		self.activityTimer.start(10)

	def updateList2(self):
		self.activityTimer.stop()
		self.list = []
		list2 = []
		f = open('/proc/partitions', 'r')
		for line in f.readlines():
			parts = line.strip().split()
			if not parts:
				continue
			device = parts[3]
			if not search('sd[a-z][1-9]',device):
				continue
			if device in list2:
				continue
			self.buildMy_rec(device)
			list2.append(device)

		f.close()
		self['list'].list = self.list
		self['lab1'].hide()

	def buildMy_rec(self, device):
		try:
			if device.find('1') > 0:
				device2 = device.replace('1', '')
		except:
			device2 = ''
		try:
			if device.find('2') > 0:
				device2 = device.replace('2', '')
		except:
			device2 = ''
		try:
			if device.find('3') > 0:
				device2 = device.replace('3', '')
		except:
			device2 = ''
		try:
			if device.find('4') > 0:
				device2 = device.replace('4', '')
		except:
			device2 = ''
		devicetype = path.realpath('/sys/block/' + device2 + '/device')
		d2 = device
		name = 'USB: '
		mypixmap = '/usr/lib/enigma2/python/Plugins/Extensions/Infopanel/icons/dev_usbstick.png'
		model = file('/sys/block/' + device2 + '/device/model').read()
		model = str(model).replace('\n', '')
		des = ''
		if devicetype.find('/devices/pci') != -1:
			name = _("HARD DISK: ")
			mypixmap = '/usr/lib/enigma2/python/Plugins/Extensions/Infopanel/icons/dev_hdd.png'
		name = name + model
		self.Console = Console()
		self.Console.ePopen("sfdisk -l /dev/sd? | grep swap | awk '{print $(NF-9)}' >/tmp/devices.tmp")
		sleep(0.5)
		f = open('/tmp/devices.tmp', 'r')
		swapdevices = f.read()
		f.close()
		if path.exists('/tmp/devices.tmp'):
			remove('/tmp/devices.tmp')
		swapdevices = swapdevices.replace('\n','')
		swapdevices = swapdevices.split('/')
		f = open('/proc/mounts', 'r')
		for line in f.readlines():
			if line.find(device) != -1:
				parts = line.strip().split()
				d1 = parts[1]
				dtype = parts[2]
				rw = parts[3]
				break
				continue
			else:
				if device in swapdevices:
					parts = line.strip().split()
					d1 = _("None")
					dtype = 'swap'
					rw = _("None")
					break
					continue
				else:
					d1 = _("None")
					dtype = _("unavailable")
					rw = _("None")
		f.close()
		f = open('/proc/partitions', 'r')
		for line in f.readlines():
			if line.find(device) != -1:
				parts = line.strip().split()
				size = int(parts[2])
				if (((float(size) / 1024) / 1024) / 1024) > 1:
					des = _("Size: ") + str(round((((float(size) / 1024) / 1024) / 1024),2)) + _("TB")
				elif ((size / 1024) / 1024) > 1:
					des = _("Size: ") + str((size / 1024) / 1024) + _("GB")
				else:
					des = _("Size: ") + str(size / 1024) + _("MB")
			else:
				try:
					size = file('/sys/block/' + device2 + '/' + device + '/size').read()
					size = str(size).replace('\n', '')
					size = int(size)
				except:
					size = 0
				if ((((float(size) / 2) / 1024) / 1024) / 1024) > 1:
					des = _("Size: ") + str(round(((((float(size) / 2) / 1024) / 1024) / 1024),2)) + _("TB")
				elif (((size / 2) / 1024) / 1024) > 1:
					des = _("Size: ") + str(((size / 2) / 1024) / 1024) + _("GB")
				else:
					des = _("Size: ") + str((size / 2) / 1024) + _("MB")
		f.close()
		if des != '':
			if rw.startswith('rw'):
				rw = ' R/W'
			elif rw.startswith('ro'):
				rw = ' R/O'
			else:
				rw = ""
			des += '\t' + _("Mount: ") + d1 + '\n' + _("Device: ") + '/dev/' + device + '\t' + _("Type: ") + dtype + rw
			png = LoadPixmap(mypixmap)
			res = (name, des, png)
			self.list.append(res)

	def SetupMounts(self):
		self.session.openWithCallback(self.updateList, lbDevicePanelConf)

	def Mount(self):
		sel = self['list'].getCurrent()
		if sel:
			des = sel[1]
			des = des.replace('\n', '\t')
			parts = des.strip().split('\t')
			mountp = parts[1].replace(_("Mount: "), '')
			device = parts[2].replace(_("Device: "), '')
			system ('mount ' + device)
			mountok = False
			f = open('/proc/mounts', 'r')
			for line in f.readlines():
				if line.find(device) != -1:
					mountok = True
			if not mountok:
				self.session.open(MessageBox, _("Mount failed"), MessageBox.TYPE_INFO, timeout=5)
			self.updateList()

	def Unmount(self):
		sel = self['list'].getCurrent()
		if sel:
			des = sel[1]
			des = des.replace('\n', '\t')
			parts = des.strip().split('\t')
			mountp = parts[1].replace(_("Mount: "), '')
			device = parts[2].replace(_("Device: "), '')
			system ('umount ' + mountp)
			try:
				mounts = open("/proc/mounts")
			except IOError:
				return -1
			mountcheck = mounts.readlines()
			mounts.close()
			for line in mountcheck:
				parts = line.strip().split(" ")
				if path.realpath(parts[0]).startswith(device):
					self.session.open(MessageBox, _("Can't unmount partiton, make sure it is not being used for swap or record/timeshift paths"), MessageBox.TYPE_INFO)
			self.updateList()

	def saveMypoints(self):
		sel = self['list'].getCurrent()
		if sel:
			parts = sel[1].split()
			self.device = parts[4].split(':')[1]
			self.mountp = parts[3]
			if self.mountp.find('/media/hdd') < 0:
				self.Console.ePopen('umount /media/hdd')
				self.Console.ePopen('umount ' + self.device)
				self.Console.ePopen("/sbin/blkid | grep " + self.device, self.add_fstab, [self.device, self.mountp])
			else:
				self.session.open(MessageBox, _("This Device is already mounted as HDD."), MessageBox.TYPE_INFO, timeout = 10, close_on_any_key = True)
			
	def add_fstab(self, result = None, retval = None, extra_args = None):
		self.device = extra_args[0]
		self.mountp = extra_args[1]
		self.device_uuid_tmp = result.split('UUID=')
		self.device_uuid_tmp = self.device_uuid_tmp[1].replace('"',"")
		self.device_uuid_tmp = self.device_uuid_tmp.replace('\n',"")
		self.device_uuid_tmp = self.device_uuid_tmp.split()[0]
		self.device_uuid = 'UUID=' + self.device_uuid_tmp
		if not path.exists(self.mountp):
			mkdir(self.mountp, 0755)
		file('/etc/fstab.tmp', 'w').writelines([l for l in file('/etc/fstab').readlines() if '/media/hdd' not in l])
		rename('/etc/fstab.tmp','/etc/fstab')
		file('/etc/fstab.tmp', 'w').writelines([l for l in file('/etc/fstab').readlines() if self.device not in l])
		rename('/etc/fstab.tmp','/etc/fstab')
		file('/etc/fstab.tmp', 'w').writelines([l for l in file('/etc/fstab').readlines() if self.device_uuid not in l])
		rename('/etc/fstab.tmp','/etc/fstab')
		out = open('/etc/fstab', 'a')
		line = self.device_uuid + '\t/media/hdd\tauto\tdefaults\t0 0\n'
		out.write(line)
		out.close()
		self.Console.ePopen('mount /media/hdd', self.updateList)

	def restBo(self, answer):
		if answer is True:
			self.session.open(TryQuitMainloop, 2)
		else:
			self.updateList()
			self.selectionChanged()

class lbDevicePanelConf(Screen, ConfigListScreen):
	skin = """
	<screen position="0,0" size="1280,720" title="Choose where to mount your devices to:">

		<widget position="592,191" size="628,350" foregroundColor="#ffffff" backgroundColor="#6e6e6e" backgroundColorSelected="#fd6502" transparent="1" name="config" scrollbarMode="showOnDemand" />
		<widget name="Linconn" position="650,400" size="580,20" font="Regular;18" halign="center" valign="center" backgroundColor="#9f1313"/>
<!-- colores keys -->
    <!-- rojo -->
    <eLabel text="CANCELAR" position="622,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#ee1d11" zPosition="-1" />
    <!-- amarillo -->
    <eLabel position="622,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="592,604" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#eefb1a" zPosition="-1" />
    <!-- verde -->
    <eLabel text="GUARDAR" position="912,569" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="882,569" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#11b90a" zPosition="-1" />
    <!-- azul -->
    <eLabel position="912,604" size="200,30" font="Regular;20" valign="center" halign="center" backgroundColor="black" foregroundColor="white" transparent="0" />
    <eLabel position="882,604" size="30,30" transparent="0" foregroundColor="white" backgroundColor="#1a2cfb" zPosition="-1" />
    <!-- fin colores keys -->
    <eLabel text="LBpanel - Red Bee" position="440,34" size="430,65" font="Regular; 42" halign="center" transparent="1" foregroundColor="white" backgroundColor="#140b1" />
    <eLabel text="PULSE EXIT PARA SALIR" position="335,644" size="500,50" font="Regular; 30" zPosition="2" halign="left" noWrap="1" transparent="1" foregroundColor="white" backgroundColor="#8f8f8f" />
    <widget source="Title" transparent="1" render="Label" zPosition="2" valign="center" halign="left" position="80,119" size="600,50" font="Regular; 30" backgroundColor="black" foregroundColor="white" noWrap="1" />
    <widget source="global.CurrentTime" render="Label" position="949,28" size="251,55" backgroundColor="#140b1" foregroundColor="white" transparent="1" zPosition="2" font="Regular;24" valign="center" halign="right" shadowColor="#000000" shadowOffset="-2,-2">
      <convert type="ClockToText">Format:%-H:%M</convert>
    </widget>
    <widget source="global.CurrentTime" render="Label" position="900,50" size="300,55" backgroundColor="#140b1" foregroundColor="white" transparent="1" zPosition="2" font="Regular;16" valign="center" halign="right" shadowColor="#000000" shadowOffset="-2,-2">
      <convert type="ClockToText">Date</convert>
    </widget>
    <widget source="session.VideoPicture" render="Pig" position="64,196" size="375,175" backgroundColor="transparent" zPosition="-1" transparent="0" />
    <widget source="session.CurrentService" render="RunningText" options="movetype=running,startpoint=0,direction=left,steptime=25,repeat=150,startdelay=1500,always=0" position="101,491" size="215,45" font="Regular; 22" transparent="1" valign="center" zPosition="2" backgroundColor="black" foregroundColor="white" noWrap="1" halign="center">
      <convert type="ServiceName">Name</convert>
    </widget>
    <widget source="session.CurrentService" render="Label" zPosition="3" font="Regular; 22" position="66,649" size="215,50" halign="center" backgroundColor="black" transparent="1" noWrap="1" foregroundColor="white">
      <convert type="VtiInfo">TempInfo</convert>
    </widget>
    <eLabel position="192,459" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#ee1d11" zPosition="-1" />
    <eLabel position="251,410" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#1a2cfb" zPosition="-2" />
    <eLabel position="281,449" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#11b90a" zPosition="-6" />
    <eLabel position="233,499" size="165,107" transparent="0" foregroundColor="white" backgroundColor="#eefb1a" zPosition="-5" />
    <eLabel position="60,451" size="65,57" transparent="0" foregroundColor="white" backgroundColor="#ecbc13" zPosition="-6" />
    <eLabel position="96,489" size="229,50" transparent="0" foregroundColor="white" backgroundColor="black" />
    <eLabel position="0,0" size="1280,720" transparent="0" zPosition="-15" backgroundColor="#d6d6d6" />
    <ePixmap position="46,180" zPosition="0" size="413,210" pixmap="/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/images/marcotv.png" transparent="0" />
    <eLabel position="60,30" size="1160,68" transparent="0" foregroundColor="white" backgroundColor="#42b3" zPosition="-10" />
    <eLabel position="60,120" size="1160,50" transparent="0" foregroundColor="white" backgroundColor="black" />
    <eLabel position="60,640" size="229,50" transparent="0" foregroundColor="white" backgroundColor="black" />
    <eLabel position="320,640" size="901,50" transparent="0" foregroundColor="white" backgroundColor="#929292" />
    <eLabel position="592,191" size="629,370" transparent="0" foregroundColor="white" backgroundColor="#6e6e6e" zPosition="-10" />
   </screen>"""
	
	def __init__(self, session):
		Screen.__init__(self, session)
		self.list = []
		ConfigListScreen.__init__(self, self.list)
		Screen.setTitle(self, _("Choose where to mount your devices to:"))
		self['Linconn'] = Label(_("Wait please while scanning your STB_BOX devices..."))
		self['actions'] = ActionMap(['WizardActions', 'ColorActions'], {'green': self.saveMypoints, 'red': self.close, 'back': self.close})
		self.updateList()

	def updateList(self):
		self.list = []
		list2 = []
		self.Console = Console()
		self.Console.ePopen("sfdisk -l /dev/sd? | grep swap | awk '{print $(NF-9)}' >/tmp/devices.tmp")
		sleep(0.5)
		f = open('/tmp/devices.tmp', 'r')
		swapdevices = f.read()
		f.close()
		if path.exists('/tmp/devices.tmp'):
			remove('/tmp/devices.tmp')
		swapdevices = swapdevices.replace('\n','')
		swapdevices = swapdevices.split('/')
		f = open('/proc/partitions', 'r')
		for line in f.readlines():
			parts = line.strip().split()
			if not parts:
				continue
			device = parts[3]
			if not search('sd[a-z][1-9]',device):
				continue
			if device in list2:
				continue
			if device in swapdevices:
				continue
			self.buildMy_rec(device)
			list2.append(device)
		f.close()
		self['config'].list = self.list
		self['config'].l.setList(self.list)
		self['Linconn'].hide()

	def buildMy_rec(self, device):
		try:
			if device.find('1') > 0:
				device2 = device.replace('1', '')
		except:
			device2 = ''
		try:
			if device.find('2') > 0:
				device2 = device.replace('2', '')
		except:
			device2 = ''
		try:
			if device.find('3') > 0:
				device2 = device.replace('3', '')
		except:
			device2 = ''
		try:
			if device.find('4') > 0:
				device2 = device.replace('4', '')
		except:
			device2 = ''
		devicetype = path.realpath('/sys/block/' + device2 + '/device')
		d2 = device
		name = 'USB: '
		mypixmap = '/usr/lib/enigma2/python/Plugins/Extensions/Infopanel/icons/dev_usbstick.png'
		model = file('/sys/block/' + device2 + '/device/model').read()
		model = str(model).replace('\n', '')
		des = ''
		if devicetype.find('/devices/pci') != -1:
			name = _("HARD DISK: ")
			mypixmap = '/usr/lib/enigma2/python/Plugins/Extensions/Infopanel/icons/dev_hdd.png'
		name = name + model
		f = open('/proc/mounts', 'r')
		for line in f.readlines():
			if line.find(device) != -1:
				parts = line.strip().split()
				d1 = parts[1]
				dtype = parts[2]
				break
				continue
			else:
				d1 = _("None")
				dtype = _("unavailable")
		f.close()
		f = open('/proc/partitions', 'r')
		for line in f.readlines():
			if line.find(device) != -1:
				parts = line.strip().split()
				size = int(parts[2])
				if (((float(size) / 1024) / 1024) / 1024) > 1:
					des = _("Size: ") + str(round((((float(size) / 1024) / 1024) / 1024),2)) + _("TB")
				elif ((size / 1024) / 1024) > 1:
					des = _("Size: ") + str((size / 1024) / 1024) + _("GB")
				else:
					des = _("Size: ") + str(size / 1024) + _("MB")
			else:
				try:
					size = file('/sys/block/' + device2 + '/' + device + '/size').read()
					size = str(size).replace('\n', '')
					size = int(size)
				except:
					size = 0
				if ((((float(size) / 2) / 1024) / 1024) / 1024) > 1:
					des = _("Size: ") + str(round(((((float(size) / 2) / 1024) / 1024) / 1024),2)) + _("TB")
				elif (((size / 2) / 1024) / 1024) > 1:
					des = _("Size: ") + str(((size / 2) / 1024) / 1024) + _("GB")
				else:
					des = _("Size: ") + str((size / 2) / 1024) + _("MB")
		f.close()
		item = NoSave(ConfigSelection(default='/media/' + device, choices=[('/media/' + device, '/media/' + device),
		('/media/hdd', '/media/hdd'),
		('/media/hdd2', '/media/hdd2'),
		('/media/hdd3', '/media/hdd3'),
		('/media/usb', '/media/usb'),
		('/media/usb2', '/media/usb2'),
		('/media/usb3', '/media/usb3')]))
		if dtype == 'Linux':
			dtype = 'ext3'
		else:
			dtype = 'auto'
		item.value = d1.strip()
		text = name + ' ' + des + ' /dev/' + device
		res = getConfigListEntry(text, item, device, dtype)

		if des != '' and self.list.append(res):
			pass

	def saveMypoints(self):
		self.Console = Console()
		mycheck = False
		for x in self['config'].list:
			self.device = x[2]
			self.mountp = x[1].value
			self.type = x[3]
			self.Console.ePopen('umount ' + self.device)
			self.Console.ePopen("/sbin/blkid | grep " + self.device, self.add_fstab, [self.device, self.mountp] )
		message = _("Updating mount locations.")
		ybox = self.session.openWithCallback(self.delay, MessageBox, message, type=MessageBox.TYPE_INFO, timeout=5, enable_input = False)
		ybox.setTitle(_("Please wait."))

	def delay(self, val):
		message = _("Changes need a system restart to take effect.\nRestart your STB_BOX now?")
		ybox = self.session.openWithCallback(self.restartBox, MessageBox, message, MessageBox.TYPE_YESNO)
		ybox.setTitle(_("Restart STB_BOX."))

	def add_fstab(self, result = None, retval = None, extra_args = None):
		self.device = extra_args[0]
		self.mountp = extra_args[1]
		self.device_tmp = result.split(' ')
		if self.device_tmp[0].startswith('UUID='):
			self.device_uuid = self.device_tmp[0].replace('"',"")
			self.device_uuid = self.device_uuid.replace('\n',"")
		elif self.device_tmp[1].startswith('UUID='):
			self.device_uuid = self.device_tmp[1].replace('"',"")
			self.device_uuid = self.device_uuid.replace('\n',"")
		elif self.device_tmp[2].startswith('UUID='):
			self.device_uuid = self.device_tmp[2].replace('"',"")
			self.device_uuid = self.device_uuid.replace('\n',"")
		elif self.device_tmp[3].startswith('UUID='):
			self.device_uuid = self.device_tmp[3].replace('"',"")
			self.device_uuid = self.device_uuid.replace('\n',"")
		try:
			if self.device_tmp[0].startswith('TYPE='):
				self.device_type = self.device_tmp[0].replace('TYPE=',"")
				self.device_type = self.device_type.replace('"',"")
				self.device_type = self.device_type.replace('\n',"")
			elif self.device_tmp[1].startswith('TYPE='):
				self.device_type = self.device_tmp[1].replace('TYPE=',"")
				self.device_type = self.device_type.replace('"',"")
				self.device_type = self.device_type.replace('\n',"")
			elif self.device_tmp[2].startswith('TYPE='):
				self.device_type = self.device_tmp[2].replace('TYPE=',"")
				self.device_type = self.device_type.replace('"',"")
				self.device_type = self.device_type.replace('\n',"")
			elif self.device_tmp[3].startswith('TYPE='):
				self.device_type = self.device_tmp[3].replace('TYPE=',"")
				self.device_type = self.device_type.replace('"',"")
				self.device_type = self.device_type.replace('\n',"")
			elif self.device_tmp[4].startswith('TYPE='):
				self.device_type = self.device_tmp[4].replace('TYPE=',"")
				self.device_type = self.device_type.replace('"',"")
				self.device_type = self.device_type.replace('\n',"")
		except:
			self.device_type = 'auto'
				
		if self.device_type.startswith('ext'):
			self.device_type = 'auto'

		if not path.exists(self.mountp):
			mkdir(self.mountp, 0755)
		file('/etc/fstab.tmp', 'w').writelines([l for l in file('/etc/fstab').readlines() if self.device not in l])
		rename('/etc/fstab.tmp','/etc/fstab')
		file('/etc/fstab.tmp', 'w').writelines([l for l in file('/etc/fstab').readlines() if self.device_uuid not in l])
		rename('/etc/fstab.tmp','/etc/fstab')
		out = open('/etc/fstab', 'a')
		line = self.device_uuid + '\t' + self.mountp + '\t' + self.device_type + '\tdefaults\t0 0\n'
		out.write(line)
		out.close()

	def restartBox(self, answer):
		if answer is True:
			self.session.open(TryQuitMainloop, 2)
		else:
			self.close()

class DevicesPanelSummary(Screen):
	def __init__(self, session, parent):
		Screen.__init__(self, session, parent = parent)
		self["entry"] = StaticText("")
		self["desc"] = StaticText("")
		self.onShow.append(self.addWatcher)
		self.onHide.append(self.removeWatcher)

	def addWatcher(self):
		self.parent.onChangedEntry.append(self.selectionChanged)
		self.parent.selectionChanged()

	def removeWatcher(self):
		self.parent.onChangedEntry.remove(self.selectionChanged)

	def selectionChanged(self, name, desc):
		self["entry"].text = name
		self["desc"].text = desc



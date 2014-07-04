from Screens.Wizard import WizardSummary
from Screens.WizardLanguage import WizardLanguage
from Screens.Wizard import wizardManager
from Screens.Rc import Rc
from Screens.Screen import Screen
from Components.Label import Label
from Components.MenuList import MenuList
from Components.PluginComponent import plugins
from Plugins.Plugin import PluginDescriptor
from Tools.Directories import fileExists, resolveFilename, SCOPE_PLUGINS
from Components.Pixmap import Pixmap, MovingPixmap, MultiPixmap
from os import popen, path, makedirs, listdir, access, stat, rename, remove, W_OK, R_OK
from enigma import eEnv
from boxbranding import getBoxType

from Components.config import config, getConfigListEntry, ConfigSubsection, ConfigText, ConfigLocations, ConfigBoolean
from Components.Harddisk import harddiskmanager

boxtype = getBoxType()

config.misc.firstrun = ConfigBoolean(default = True)
config.plugins.configurationbackup = ConfigSubsection()
if boxtype in ('maram9', 'classm', 'axodin', 'axodinc', 'starsatlx', 'genius', 'evo', 'galaxym6') and not path.exists("/media/hdd/backup_%s" %boxtype):
	config.plugins.configurationbackup.backuplocation = ConfigText(default = '/media/backup/', visible_width = 50, fixed_size = False)
else:
	config.plugins.configurationbackup.backuplocation = ConfigText(default = '/media/hdd/', visible_width = 50, fixed_size = False)
config.plugins.configurationbackup.backupdirs = ConfigLocations(default=[eEnv.resolve('${sysconfdir}/enigma2/'), '/etc/CCcam.cfg', '/usr/keys/', '/etc/network/interfaces', '/etc/wpa_supplicant.conf', '/etc/wpa_supplicant.ath0.conf', '/etc/wpa_supplicant.wlan0.conf', '/etc/resolv.conf', '/etc/default_gw', '/etc/hostname', eEnv.resolve("${datadir}/enigma2/keymap.usr")])


backupfile = "enigma2settingsbackup.tar.gz"

def checkConfigBackup():
	parts = [ (r.description, r.mountpoint) for r in harddiskmanager.getMountedPartitions(onlyhotplug = False)]
	if boxtype in ('maram9', 'classm', 'axodin', 'axodinc', 'starsatlx', 'genius', 'evo', 'galaxym6'):
		parts.append(('mtd backup','/media/backup'))
	for x in parts:
		if x[1] == '/':
			parts.remove(x)
	if len(parts):
		for x in parts:
			if x[1].endswith('/'):
				fullbackupfile =  x[1] + 'backup_' + boxtype + '/' + backupfile
				if fileExists(fullbackupfile):
					config.plugins.configurationbackup.backuplocation.setValue(str(x[1]))
					config.plugins.configurationbackup.backuplocation.save()
					config.plugins.configurationbackup.save()
					return x
				fullbackupfile =  x[1] + 'backup/' + backupfile
				if fileExists(fullbackupfile):
					config.plugins.configurationbackup.backuplocation.setValue(str(x[1]))
					config.plugins.configurationbackup.backuplocation.save()
					config.plugins.configurationbackup.save()
					return x
			else:
				fullbackupfile =  x[1] + '/backup_' + boxtype + '/' + backupfile
				if fileExists(fullbackupfile):
					config.plugins.configurationbackup.backuplocation.setValue(str(x[1]))
					config.plugins.configurationbackup.backuplocation.save()
					config.plugins.configurationbackup.save()
					return x
				fullbackupfile =  x[1] + '/backup/' + backupfile
				if fileExists(fullbackupfile):
					config.plugins.configurationbackup.backuplocation.setValue(str(x[1]))
					config.plugins.configurationbackup.backuplocation.save()
					config.plugins.configurationbackup.save()
					return x
		return None

def checkBackupFile():
	backuplocation = config.plugins.configurationbackup.backuplocation.value
	if backuplocation.endswith('/'):
		fullbackupfile =  backuplocation + 'backup_' + boxtype + '/' + backupfile
		if fileExists(fullbackupfile):
			return True
		else:
			fullbackupfile =  backuplocation + 'backup/' + backupfile
			if fileExists(fullbackupfile):
				return True
			else:
				return False
	else:
		fullbackupfile =  backuplocation + '/backup_' + boxtype + '/' + backupfile
		if fileExists(fullbackupfile):
			return True
		else:
			fullbackupfile =  backuplocation + '/backup/' + backupfile
			if fileExists(fullbackupfile):
				return True
			else:
				return False

if checkConfigBackup() is None:
	backupAvailable = 0
else:
	backupAvailable = 1

class ImageWizard(WizardLanguage, Rc):
	skin = """
		<screen name="ImageWizard" position="0,0" size="720,576" title="Welcome..." flags="wfNoBorder" >
			<widget name="text" position="153,40" size="340,330" font="Regular;22" />
			<widget source="list" render="Listbox" position="43,340" size="490,180" scrollbarMode="showOnDemand" >
				<convert type="StringList" />
			</widget>
			<widget name="config" position="53,340" zPosition="1" size="440,180" transparent="1" scrollbarMode="showOnDemand" />
			<ePixmap pixmap="buttons/button_red.png" position="40,225" zPosition="0" size="15,16" transparent="1" alphatest="on" />
			<widget name="languagetext" position="55,225" size="95,30" font="Regular;18" />
			<widget name="wizard" pixmap="wizard.png" position="40,50" zPosition="10" size="110,174" alphatest="on" />
			<widget name="rc" pixmaps="rc.png,rcold.png" position="530,50" zPosition="10" size="154,500" alphatest="on" />
			<widget name="arrowdown" pixmap="arrowdown.png" position="-100,-100" zPosition="11" size="37,70" alphatest="on" />
			<widget name="arrowdown2" pixmap="arrowdown.png" position="-100,-100" zPosition="11" size="37,70" alphatest="on" />
			<widget name="arrowup" pixmap="arrowup.png" position="-100,-100" zPosition="11" size="37,70" alphatest="on" />
			<widget name="arrowup2" pixmap="arrowup.png" position="-100,-100" zPosition="11" size="37,70" alphatest="on" />
		</screen>"""
	def __init__(self, session):
		self.xmlfile = resolveFilename(SCOPE_PLUGINS, "SystemPlugins/SoftwareManager/imagewizard.xml")
		WizardLanguage.__init__(self, session, showSteps = False, showStepSlider = False)
		Rc.__init__(self)
		self.session = session
		self["wizard"] = Pixmap()
		Screen.setTitle(self, _("Welcome..."))
		self.selectedDevice = None

	def markDone(self):
		pass

	def listDevices(self):
		list = [ (r.description, r.mountpoint) for r in harddiskmanager.getMountedPartitions(onlyhotplug = False)]
		for x in list:
			result = access(x[1], W_OK) and access(x[1], R_OK)
			if result is False or x[1] == '/':
				list.remove(x)
		for x in list:
			if x[1].startswith('/autofs/'):
				list.remove(x)
		return list

	def deviceSelectionMade(self, index):
		self.deviceSelect(index)

	def deviceSelectionMoved(self):
		self.deviceSelect(self.selection)

	def deviceSelect(self, device):
		self.selectedDevice = device
		config.plugins.configurationbackup.backuplocation.setValue(self.selectedDevice)
		config.plugins.configurationbackup.backuplocation.save()
		config.plugins.configurationbackup.save()


if config.misc.firstrun.value:
	wizardManager.registerWizard(ImageWizard, backupAvailable, priority = 10)


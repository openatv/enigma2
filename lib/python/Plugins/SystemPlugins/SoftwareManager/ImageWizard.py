from os import W_OK, R_OK, access
from os.path import isfile, join as pathjoin

from Components.config import config
from Components.Harddisk import harddiskmanager
from Components.Pixmap import Pixmap
from Components.SystemInfo import BoxInfo
from Screens.HelpMenu import ShowRemoteControl
from Screens.Wizard import wizardManager
from Screens.WizardLanguage import WizardLanguage
from Tools.Directories import resolveFilename, SCOPE_PLUGINS

from .BackupRestore import getBackupFilename, InitConfig as BackupRestore_InitConfig


BACKUP_FILE = getBackupFilename()
BOX_TYPE = BoxInfo.getItem("machinebuild")
DISTRO = BoxInfo.getItem("distro")

config.plugins.configurationbackup = BackupRestore_InitConfig()


def checkConfigBackup():
	partitions = [(x.description, x.mountpoint) for x in harddiskmanager.getMountedPartitions(onlyhotplug=False) if x.mountpoint != "/"]
	# This test criteria should be in BoxInfo!  Don't add hardware dependencies into the general Enigma2 code.
	# if BoxInfo.getItem("isMTDBackup"):
	if BOX_TYPE in ("maram9", "classm", "axodin", "axodinc", "starsatlx", "genius", "evo", "galaxym6"):
		partitions.append(("mtd backup", "/media/backup"))
	if partitions:
		for partition in partitions:
			fullBackupFile1 = pathjoin(partition[1], "backup_%s_%s" % (DISTRO, BOX_TYPE), BACKUP_FILE)
			fullBackupFile2 = pathjoin(partition[1], "backup", BACKUP_FILE)
			if isfile(fullBackupFile1) or isfile(fullBackupFile2):
				config.plugins.configurationbackup.backuplocation.setValue(partition[1])
				config.plugins.configurationbackup.backuplocation.save()
				config.plugins.configurationbackup.save()
				return partition
		return None


def checkBackupFile():
	backupLocation = config.plugins.configurationbackup.backuplocation.value
	fullBackupFile1 = pathjoin(backupLocation, "backup_%s_%s" % (DISTRO, BOX_TYPE), BACKUP_FILE)
	fullBackupFile2 = pathjoin(backupLocation, "backup", BACKUP_FILE)
	return isfile(fullBackupFile1) or isfile(fullBackupFile2)


class ImageWizard(WizardLanguage, ShowRemoteControl):
	skin = """
		<screen name="ImageWizard" position="0,0" size="720,576" title="Welcome..." flags="wfNoBorder" resolution="720,576">
			<widget name="text" position="153,40" size="340,330" font="Regular;22" />
			<widget source="list" render="Listbox" position="43,340" size="490,180" scrollbarMode="showOnDemand">
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
		WizardLanguage.__init__(self, session, showSteps=False, showStepSlider=False)
		ShowRemoteControl.__init__(self)
		self.session = session
		self["wizard"] = Pixmap()
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self.setTitle(_("ImageWizard"))
		self.selectedDevice = None

	def markDone(self):
		pass

	def listDevices(self):
		partitions = [(x.description, x.mountpoint) for x in harddiskmanager.getMountedPartitions(onlyhotplug=False) if x.mountpoint != "/"]
		for partition in partitions:
			if not (access(partition[1], W_OK) and access(partition[1], R_OK)):
				partitions.remove(partition)
		for partition in partitions:
			if partition[1].startswith("/autofs/"):
				partitions.remove(partition)
		return partitions

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
	wizardManager.registerWizard(ImageWizard, 0 if checkConfigBackup() is None else 1, priority=10)

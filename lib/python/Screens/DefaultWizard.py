from Wizard import wizardManager
from Screens.WizardLanguage import WizardLanguage
from Tools.Directories import pathExists, resolveFilename, SCOPE_DEFAULTDIR, SCOPE_DEFAULTPARTITIONMOUNTDIR, SCOPE_DEFAULTPARTITION

from Components.Pixmap import Pixmap, MovingPixmap
from Components.config import config, ConfigBoolean, configfile, ConfigYesNo, getConfigListEntry
from Components.DreamInfoHandler import DreamInfoHandler
from Components.PluginComponent import plugins
from Plugins.Plugin import PluginDescriptor
from os import system as os_system, path as os_path, mkdir
from boxbranding import getMachineBrand, getMachineName

config.misc.defaultchosen = ConfigBoolean(default = False)

class DefaultWizard(WizardLanguage, DreamInfoHandler):
	def __init__(self, session, silent = True, showSteps = False, neededTag = None):
		DreamInfoHandler.__init__(self, self.statusCallback, neededTag = neededTag)
		self.silent = silent
		self.setDirectory()

		WizardLanguage.__init__(self, session, showSteps = False)
		self["wizard"] = Pixmap()
		self["rc"] = MovingPixmap()
		self["arrowdown"] = MovingPixmap()
		self["arrowup"] = MovingPixmap()
		self["arrowup2"] = MovingPixmap()

	def setDirectory(self):
		self.directory = resolveFilename(SCOPE_DEFAULTPARTITIONMOUNTDIR)
		self.xmlfile = "defaultwizard.xml"
		if self.directory:
			os_system("mount %s %s" % (resolveFilename(SCOPE_DEFAULTPARTITION), self.directory))

	def markDone(self):
		config.misc.defaultchosen.setValue(0)
		config.misc.defaultchosen.save()
		configfile.save()

	def statusCallback(self, status, progress):
		print "statusCallback:", status, progress
		if status == DreamInfoHandler.STATUS_DONE:
			self["text"].setText(_("The installation of the default settings is finished. You can now continue configuring your %s %s by pressing the OK button on the remote control.") % (getMachineBrand(), getMachineName()))
			self.markDone()
			self.disableKeys = False

	def getConfigList(self):
		self.packageslist = []
		configList = []
		self.fillPackagesList()
		self.packagesConfig = []
		for x in range(len(self.packageslist)):
			entry = ConfigYesNo()
			self.packagesConfig.append(entry)
			configList.append(getConfigListEntry(self.packageslist[x][0]["attributes"]["name"], entry))
		return configList

	def selectionMade(self):
		print "selection made"
		#self.installPackage(int(index))
		self.indexList = []
		for x in range(len(self.packagesConfig)):
			if self.packagesConfig[x].value:
				self.indexList.append(x)

class DreamPackageWizard(DefaultWizard):
	def __init__(self, session, packagefile, silent = False):
		if not pathExists("/tmp/package"):
			mkdir("/tmp/package")
		os_system("tar xpzf %s -C /tmp/package" % packagefile)
		self.packagefile = packagefile
		DefaultWizard.__init__(self, session, silent)

	def setDirectory(self):
		self.directory = "/tmp/package"
		self.xmlfile = "dreampackagewizard.xml"

class ImageDefaultInstaller(DreamInfoHandler):
	def __init__(self):
		DreamInfoHandler.__init__(self, self.statusCallback, blocking = True)
		self.directory = resolveFilename(SCOPE_DEFAULTDIR)
		self.fillPackagesList()
		self.installPackage(0)

	def statusCallback(self, status, progress):
		pass

def install(choice):
	if choice is not None:
		#os_system("mkdir /tmp/package && tar xpzf %s ")
		choice[2].open(DreamPackageWizard, choice[1])

def filescan_open(list, session, **kwargs):
	from Screens.ChoiceBox import ChoiceBox
	print "open default wizard"
	filelist = [(os_path.split(x.path)[1], x.path, session) for x in list]
	print filelist
	session.openWithCallback(install, ChoiceBox, title = _("Please choose he package..."), list=filelist)

def filescan(**kwargs):
	from Components.Scanner import Scanner, ScanPath
	return \
		Scanner(mimetypes = ["application/x-dream-package"],
			paths_to_scan =
				[
					ScanPath(path = "dmpkg", with_subdirs = True),
					ScanPath(path = "", with_subdirs = False),
				],
			name = "Dream-Package",
			description = _("Install settings, skins, software..."),
			openfnc = filescan_open, )

print "add dreampackage scanner plugin"
plugins.addPlugin(PluginDescriptor(name="Dream-Package", where = PluginDescriptor.WHERE_FILESCAN, fnc = filescan, internal = True))
print "added"

wizardManager.registerWizard(DefaultWizard, config.misc.defaultchosen.value, priority = 6)

if config.misc.defaultchosen.value:
	print "Installing image defaults"
	installer = ImageDefaultInstaller()
	print "installing done!"

from Wizard import wizardManager
from Screens.WizardLanguage import WizardLanguage
from Tools.Directories import crawlDirectory, resolveFilename, SCOPE_DEFAULTDIR, SCOPE_DEFAULTPARTITIONMOUNTDIR, SCOPE_DEFAULTPARTITION

from Components.Pixmap import Pixmap, MovingPixmap
from Components.config import config, ConfigBoolean, configfile, ConfigYesNo, getConfigListEntry
from Components.DreamInfoHandler import DreamInfoHandler, InfoHandler, InfoHandlerParseError
import os

config.misc.defaultchosen = ConfigBoolean(default = True)

import xml.sax

class DefaultWizard(WizardLanguage, DreamInfoHandler):
	def __init__(self, session, silent = True):
		DreamInfoHandler.__init__(self, self.statusCallback)
		self.silent = silent
		os.system("mount %s %s" % (resolveFilename(SCOPE_DEFAULTPARTITION), resolveFilename(SCOPE_DEFAULTPARTITIONMOUNTDIR)))
		self.directory = resolveFilename(SCOPE_DEFAULTPARTITIONMOUNTDIR)
		self.xmlfile = "defaultwizard.xml"
        
		WizardLanguage.__init__(self, session, showSteps = False)
		self["wizard"] = Pixmap()
		self["rc"] = MovingPixmap()
		self["arrowdown"] = MovingPixmap()
		self["arrowup"] = MovingPixmap()
		self["arrowup2"] = MovingPixmap()
        
	def markDone(self):
		config.misc.defaultchosen.value = 0
		config.misc.defaultchosen.save()
		configfile.save()
		
	def statusCallback(self, status, progress):
		print "statusCallback:", status, progress
		if status == DreamInfoHandler.STATUS_DONE:
			self["text"].setText(_("The installation of the default settings is finished. You can now continue configuring your Dreambox by pressing the OK button on the remote control."))
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
		indexList = []
		for x in range(len(self.packagesConfig)):
			if self.packagesConfig[x].value:
				indexList.append(x)
		self.installPackages(indexList)
		
class ImageDefaultInstaller(DreamInfoHandler):
	def __init__(self):
		DreamInfoHandler.__init__(self, self.statusCallback, blocking = True)
		self.directory = resolveFilename(SCOPE_DEFAULTDIR)
		self.fillPackagesList()
		self.installPackage(0)
		
	def statusCallback(self, status, progress):
		pass
		
wizardManager.registerWizard(DefaultWizard, config.misc.defaultchosen.value, priority = 6)
if config.misc.defaultchosen.value:
	print "Installing image defaults"
	installer = ImageDefaultInstaller()
	print "installing done!"

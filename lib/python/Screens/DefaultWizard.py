from Wizard import Wizard, wizardManager
from Tools.Directories import crawlDirectory, resolveFilename, SCOPE_DEFAULTDIR

from Components.Pixmap import Pixmap, MovingPixmap
from Components.config import config, ConfigBoolean, configfile
from Components.DreamInfoHandler import DreamInfoHandler, InfoHandler, InfoHandlerParseError
import os

config.misc.defaultchosen = ConfigBoolean(default = True)

import xml.sax

class DefaultWizard(Wizard, DreamInfoHandler):
	def __init__(self, session):
		DreamInfoHandler.__init__(self, self.statusCallback)
		self.directory = resolveFilename(SCOPE_DEFAULTDIR)
		self.xmlfile = "defaultwizard.xml"
        
		Wizard.__init__(self, session, showSteps = False)
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
			self["text"].setText(_("Finished"))
			self.markDone()
			os.system("killall -9 enigma2")

	def listDefaults(self):
		self.packageslist = []
		self.fillPackagesList()
		list = []
		for x in range(len(self.packageslist)):
			list.append((self.packageslist[x][0]["attributes"]["name"], str(x)))
		print "defaults list:", list
		return list
    
	def selectionMade(self, index):
		print "selected:", index
		self.installPackage(int(index))
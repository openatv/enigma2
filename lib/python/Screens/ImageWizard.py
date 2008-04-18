from Wizard import Wizard, wizardManager

from Tools.Directories import fileExists

import os

backupfile = "backupenigma2settings.tar"

def checkConfigBackup():
	paths = ['/media/hdd/', '/media/cf/']
	for x in paths:
		if fileExists(x + backupfile):
			return x
	return None

if checkConfigBackup() is None:
	backupAvailable = 0
else:
	backupAvailable = 1

class ImageWizard(Wizard):
	def __init__(self, session):
		self.xmlfile = "imagewizard.xml"
		Wizard.__init__(self, session, showSteps=False, showStepSlider=False, showList=True, showConfig=True)

	def markDone(self):
		pass

wizardManager.registerWizard(ImageWizard, backupAvailable, priority = 10)

def doBackup(path):
	os.system('tar cvpf ' + path + backupfile + ' /etc/enigma2')

def doRestore(path):
	os.system('cd / && /bin/tar xvpf ' + path + backupfile)
	

		
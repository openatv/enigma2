from Wizard import Wizard, wizardManager

from Components.Pixmap import *

from LanguageSelection import LanguageSelection
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
	skin = """
		<screen position="0,0" size="720,576" title="Welcome..." flags="wfNoBorder">
			<widget name="text" position="50,100" size="440,250" font="Regular;22" />
			<widget name="list" position="50,350" zPosition="1" size="440,200" />
			<widget name="config" position="50,350" zPosition="1" size="440,200" transparent="1" scrollbarMode="showOnDemand" />
		</screen>"""
	
	def __init__(self, session):
		self.xmlfile = "imagewizard.xml"
		
		Wizard.__init__(self, session, showSteps=False, showStepSlider=False, showList=True, showConfig=True)
		
	def markDone(self):
		pass

wizardManager.registerWizard(ImageWizard, backupAvailable)

def doBackup(path):
	os.system('tar cvpf ' + path + backupfile + ' /etc/enigma2')

def doRestore(path):
	os.system('cd / && /bin/tar xvpf ' + path + backupfile)
	

		
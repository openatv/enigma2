from os import system
from Wizard import wizardManager
from Screens.Screen import Screen
from Screens.WizardLanguage import WizardLanguage
from Screens.WizardUserInterfacePositioner import UserInterfacePositionerWizard
from Screens.VideoWizard import VideoWizard
from Screens.IniTerrestrialLocation import IniTerrestrialLocation
from Screens.Rc import Rc
from Components.Task import job_manager
from Screens.Standby import TryQuitMainloop
from Screens.MessageBox import MessageBox

from boxbranding import getBoxType, getMachineBuild, getMachineBrand, getMachineName

from Components.SystemInfo import SystemInfo
from Components.Pixmap import Pixmap
from Components.config import config, ConfigBoolean, ConfigYesNo, configfile
from Components.NimManager import nimmanager
from Components.Label import Label
from Components.ScrollLabel import ScrollLabel
from Components.ActionMap import ActionMap

from LanguageSelection import LanguageWizard

from Components.Harddisk import harddiskmanager, getPartitionNames

import os.path

config.misc.firstrun = ConfigBoolean(default = True)
config.misc.languageselected = ConfigBoolean(default = True)
config.misc.videowizardenabled = ConfigBoolean(default = True)
config.misc.skip_hdd_startup_format = ConfigYesNo(default = False)

class StartWizard(WizardLanguage, Rc):
	def __init__(self, session, silent = True, showSteps = False, neededTag = None):
		self.xmlfile = ["startwizard.xml"]
		WizardLanguage.__init__(self, session, showSteps = False)
		Rc.__init__(self)
		self["wizard"] = Pixmap()

	def markDone(self):
		# setup remote control, all stb have same settings except dm8000 which uses a different settings
		if getBoxType() == 'dm8000':
			config.misc.rcused.value = 0
		else:
			config.misc.rcused.value = 1
		config.misc.rcused.save()

		config.misc.firstrun.value = 0
		config.misc.firstrun.save()
		configfile.save()

def getFsType(dev):
		import subprocess
		try:
			lines = subprocess.check_output(["blkid", "-s", "TYPE",  "-s", "SEC_TYPE", dev]).split("\n")
		except Exception, e:
			print "[StartWizard] getFsType", str(e)
		type = None
		secType = None
		for l in lines:
			l = l.strip()
			if l:
				d = l.replace('"', "").split()
				if len(d) > 1 and d[0][-1] == ':':
					d[0] = d[0][:-1]
					if d[0] == dev:
						for lab in d[1:]:
							tag, val = lab.split('=')
							if tag == "TYPE":
								type = val
							elif tag == "SEC_TYPE":
								secType = val
						break
		if type == "ext4" and secType == "ext2":
			type = "ext2"
		return type

def getInternalHDD():
	for hdname, hd in harddiskmanager.HDDList():
		physLoc = harddiskmanager.getPhysicalDeviceLocation(hd.getDevicePhysicalName())
		if physLoc == "Internal HDD":
			return hd
	return None

def needHDDFormat():
	internalHdd = getInternalHDD()

	if not internalHdd:
		return False

	if internalHdd.numPartitions() != 1:
		return True

	internalHddName = internalHdd.getDeviceName()
	hddPathName, hddBaseName = os.path.split(internalHddName)
	for p in getPartitionNames():
		if p.startswith(hddBaseName) and p[len(hddBaseName):].isdigit():
			fsType = getFsType(os.path.join(hddPathName, p))
			if fsType:
				break
	if fsType and fsType in ("ext3", "ext4"):
		return False
	return True

class StartHDDFormatWizard(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Hard disk format required!"))

		system("showiframe /usr/share/enigma2/black.mvi")

		# Let showiframe's actions complete...
		import time
		time.sleep(1)

		self.internalHdd = getInternalHDD()
		if not self.internalHdd:
			self.close()

		msg = "The internal hard disk is not formatted correctly. In order for your %s %s to function at its best, it is recommended that you format the hard disk." % (getMachineBrand(), getMachineName())
		msg += "\n\nWARNING: Formatting will erase all data on the hard disk."
		msg += "\n\nPress OK to format your %s's hard disk." % getMachineName()
		msg += "\nOtherwise, press POWER to power down, or EXIT to skip the HDD format."
		self["text"] = Label(msg)
		self["errors"] = ScrollLabel()
		self["errors"].hide()

		self["actions"] = ActionMap(["SetupActions", "DirectionActions"],
		{
			"ok": self.doFormat,
			"cancel": self.askCancel,
			"up": self["errors"].pageUp,
			"down": self["errors"].pageDown,
			"left": self["errors"].pageUp,
			"right": self["errors"].pageDown,
		}, -2)
		self["poweractions"] = ActionMap(["PowerKeyActions"],
		{
			"powerdown": self.tryShutdown,
		}, -2)
		self.reset()

	def reset(self):
		self.firstTaskCallback = True # to wait for both the Job and JobView callbacks
		self.failedJob = None
		self.failedTask = None
		self.failedConditions = [ ]

	def doFormat(self):
		self.reset()
		try:
			job_manager.AddJob(self.internalHdd.createInitializeJob(), onSuccess=self.formatSucceeded, onFail=self.formatFailed)
			for job in job_manager.getPendingJobs():
				if job.name == _("Initializing storage device..."):
					self.showJobView(job)
					break
		except Exception, ex:
			self.session.open(MessageBox, _("Can't start job to format HDD\n")+str(ex), type=MessageBox.TYPE_ERROR, timeout=10)

	def showJobView(self, job):
		from Screens.TaskView import JobView
		job_manager.in_background = False
		self.session.openWithCallback(self.JobViewCB, JobView, job, cancelable=False, afterEventChangeable=False, afterEvent="close", backgroundable=False)

	def JobViewCB(self, in_background):
		job_manager.in_background = in_background
		if self.firstTaskCallback:
			self.firstTaskCallback = False
		else:
			self.formatFinished()

	def formatSucceeded(self, job):
		if self.firstTaskCallback:
			self.firstTaskCallback = False
		else:
			self.formatFinished()

	def formatFailed(self, job, task, res):
		self.failedJob = job
		self.failedTask = task
		self.failedConditions = res
		if self.firstTaskCallback:
			self.firstTaskCallback = False
		else:
			self.formatFinished()
		return True

	def formatFinished(self):
		if not (self.failedJob or needHDDFormat()):
			msg = "Your %s %s will restart now.\n" % (getMachineBrand(), getMachineName())
			msg += "If you are setting up your %s, the setup will continue after the restart." % getMachineName()
			self.session.openWithCallback(self.tryReboot, MessageBox, _(msg), type=MessageBox.TYPE_INFO, timeout=10)
		else:
			msg = "Formatting the internal disk of your %s %s has failed." % (getMachineBrand(), getMachineName())
			msg += "\n\nPress OK to retry the format, POWER to shut down, or EXIT to skip the format."
			msg += "\n\nIf the internal HDD was pre-installed in your %s, please note down any error messages below and call %s support." % (getMachineName(), getMachineBrand())
			self["text"].setText(msg)
			errs = ""
			if self.failedTask:
				errs = self.failedTask.name
			if self.failedJob and self.failedJob.name:
				if self.failedJob.name.endswith(_("...")):
					failedJobname = self.failedJob.name[:-len(_("..."))]
				if errs:
					errs += " in job"
				errs += " " + failedJobname
			if not errs:
				errs = "Disk format"
			errs += " failed:\n"
			if self.failedConditions:
				errs += '\n'.join(x.getErrorMessage(self.failedTask)
						for x in self.failedConditions)
			else:
				errs += "No error information available"
			self["errors"].setText(errs)
			self["errors"].show()
			self["poweractions"].setEnabled(True)
			if self.failedJob:
				job_manager.errorCB(False)

	def tryReboot(self, dummy):
		self.session.openWithCallback(self.shutdownFailed, TryQuitMainloop, 2)

	def tryShutdown(self):
		self.session.openWithCallback(self.shutdownFailed, TryQuitMainloop, 1)

	def shutdownFailed(self, *args):
		pass

	def askCancel(self):
		self.session.openWithCallback(self.askCancelCallback, MessageBox, _("Do you really want to skip the internal disk format?\n\nUsing a non-standard disk format can cause problems and make support more difficult.\n\nIf you skipped the format because the hard disk might need checking, run a filesystem check as soon as you can."), default=False, simple=True)

	def askCancelCallback(self, answer):
		if answer:
			self.close()
			config.misc.skip_hdd_startup_format.value = True
			config.misc.skip_hdd_startup_format.save()
			configfile.save()

#wizardManager.registerWizard(VideoWizard, config.misc.videowizardenabled.value, priority = 0)
#wizardManager.registerWizard(LanguageWizard, config.misc.languageselected.value, priority = -1)
#wizardManager.registerWizard(UserInterfacePositionerWizard, config.misc.firstrun.value, priority = 3)

from Screens.IniTerrestrialLocation import IniTerrestrialLocation, IniEndWizard, config

# If the internal HDD needs to be formatted make the format screen the first screen, and unconditional
if not config.misc.skip_hdd_startup_format.value and needHDDFormat():
	wizardManager.registerWizard(StartHDDFormatWizard, True, priority = -10)
wizardManager.registerWizard(StartWizard, config.misc.firstrun.value, priority = 0)

# Terrestrial Location Wizard Screen
dvbt_nimList = nimmanager.getNimListOfType("DVB-T")
if len(dvbt_nimList) != 0:
	wizardManager.registerWizard(IniTerrestrialLocation, config.misc.inifirstrun.value, priority = 1)

# IPTV Channel List downloader for T-POD
if SystemInfo["IPTVSTB"]:
	from os import path
	if path.exists("/usr/lib/enigma2/python/Plugins/Extensions/RemoteIPTVClient"):
		from Plugins.Extensions.RemoteIPTVClient.plugin import RemoteTunerScanner
		wizardManager.registerWizard(RemoteTunerScanner, config.misc.inifirstrun.value, priority = 2) # It always should show as last one

	
# End Message in wizards
wizardManager.registerWizard(IniEndWizard, config.misc.inifirstrun.value, priority = 10) # It always should show as last one

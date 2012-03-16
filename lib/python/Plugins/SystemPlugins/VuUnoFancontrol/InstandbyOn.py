from Components.config import config, ConfigSubList, ConfigSubsection
import NavigationInstance
from enigma import iRecordableService, eTimer, iPlayableService, eServiceCenter, iServiceInformation
from Components.ConfigList import ConfigListScreen
from Components.config import config, ConfigSubsection, ConfigSelection, ConfigSlider
from Components.Harddisk import harddiskmanager

config.plugins.manualfancontrols = ConfigSubsection()
config.plugins.manualfancontrols.standbymode = ConfigSelection(default = "yes", choices = [
	("no", _("no")), ("yes", _("yes"))])

if config.misc.boxtype.value == 'vuultimo':
	config.plugins.manualfancontrols.pwmvalue = ConfigSlider(default = 100, increment = 5, limits = (0, 255))
else:
	config.plugins.manualfancontrols.pwmvalue = ConfigSlider(default = 10, increment = 5, limits = (0, 255))

config.plugins.manualfancontrols.checkperiod = ConfigSelection(default = "10", choices = [
		("5", "5 " + _("seconds")), ("10", "10 " + _("seconds")), ("30", "30 " + _("seconds")),
		("60", "1 " + _("minute")), ("120", "2 " + _("minutes")),
		("300", "5 " + _("minutes")), ("600", "10 " + _("minutes"))])

instandbyOn_playingpvr = False

class instandbyOn:
	def __init__(self):
		self.fanoffmode = 'OFF'
		self.minimum_pwm = 5
		self.setPWM(config.plugins.manualfancontrols.pwmvalue.value)
		self.checkStstusTimer = eTimer()
		self.checkStstusTimer.callback.append(self.checkStstus)
		if config.plugins.manualfancontrols.pwmvalue.value == 0:
			self.fanoffmode = 'ON'
		if self.fanoffmode == 'ON':
			self.checkStatusLoopStart()

		config.misc.standbyCounter.addNotifier(self.standbyBegin, initial_call = False)
# 		print "<ManualFancontrol> init :  self.fanoffmode : ", self.fanoffmode
# 		print "<ManualFancontrol> init :  config.plugins.manualfancontrols.pwmvalue.value : ", config.plugins.manualfancontrols.pwmvalue.value

	def checkStatusLoopStart(self):
# 		print "<ManualFancontrol> checkStatusLoopStart"
		self.checkStstusTimer.start(int(config.plugins.manualfancontrols.checkperiod.value) * 1000)

	def checkStatusLoopStop(self):
# 		print "<ManualFancontrol> checkStatusLoopStop"
		self.checkStstusTimer.stop()

	def checkStstus(self):
		from Screens.Standby import inStandby
# 		print "<ManualFancontrol> checkStstus, fanoffmode : %s, "%self.fanoffmode,"inStandby : ",inStandby and True or False
		if self.fanoffmode is 'ON' : # pwmvalue is '0'
			if self.isRecording() or self.isHDDActive():
				self.setPWM(self.minimum_pwm)
			else:
				self.setPWM(0)
		elif inStandby : # standby mode but pwm > 0
			if self.isRecording() or self.isHDDActive():
				self.setPWM(config.plugins.manualfancontrols.pwmvalue.value)
			else:
				self.setPWM(0)
		elif self.getPWM() != config.plugins.manualfancontrols.pwmvalue.value : # normal mode
			self.setPWM(config.plugins.manualfancontrols.pwmvalue.value)

	def standbyBegin(self, configElement):
# 		print "<ManualFancontrol> Standby Begin"
		if config.plugins.manualfancontrols.standbymode.value == "yes" and self.fanoffmode is "OFF":
			from Screens.Standby import inStandby
			inStandby.onClose.append(self.StandbyEnd)
			self.addRecordEventCB()
			self.checkStatusLoopStart()
			self.checkStstus()

	def StandbyEnd(self):
# 		print "<ManualFancontrol> Standby End"
		if self.fanoffmode is "OFF":
			self.removeRecordEventCB()
			self.checkStatusLoopStop()
		self.checkStstus()

	def addRecordEventCB(self):
# 		print "<ManualFancontrol> addRecordEventCB"
		if self.getRecordEvent not in NavigationInstance.instance.record_event:
			NavigationInstance.instance.record_event.append(self.getRecordEvent)

	def removeRecordEventCB(self):
# 		print "<ManualFancontrol> removeRecordEventCB"
		if self.getRecordEvent in NavigationInstance.instance.record_event:
			NavigationInstance.instance.record_event.remove(self.getRecordEvent)

	def getRecordEvent(self, recservice, event):
		if event == iRecordableService.evEnd or event == iRecordableService.evStart:
			self.checkStstus()

	def isRecording(self):
		recordings = NavigationInstance.instance.getRecordings()
# 		print "<ManualFancontrol_> recordings : ",len(recordings)
		if recordings :
			return True
		else:
			return False

	def isHDDActive(self): # remake certainly
		for hdd in harddiskmanager.HDDList():
			if not hdd[1].isSleeping():
# 				print "<ManualFancontrol_> %s is not Sleeping"%hdd[0]
				return True
# 		print "<ManualFancontrol_> All HDDs are Sleeping"
		return False

	def getPWM(self):
		f = open("/proc/stb/fp/fan_pwm", "r")
		value = int(f.readline().strip(), 16)
		f.close()
# 		print "<ManualFancontrol> getPWM : %d "%value
		return value

	def setPWM(self, value):
# 		print "<ManualFancontrol> setPWM to : %d"%value
		f = open("/proc/stb/fp/fan_pwm", "w")
		f.write("%x" % value)
		f.close()

instandbyon = instandbyOn()


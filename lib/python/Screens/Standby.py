from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.config import config
from Components.AVSwitch import AVSwitch
from Components.SystemInfo import SystemInfo
from Components.Harddisk import harddiskmanager
from GlobalActions import globalActionMap
from enigma import eDVBVolumecontrol, eTimer, eDVBLocalTimeHandler, eServiceReference
from boxbranding import getMachineBrand, getMachineName, getBoxType, getBrandOEM
from Tools import Notifications
from time import localtime, time
import Screens.InfoBar
from gettext import dgettext
import Components.RecordingConfig

inStandby = None

def setLCDModeMinitTV(value):
	try:
		f = open("/proc/stb/lcd/mode", "w")
		f.write(value)
		f.close()
	except:
		pass

class Standby2(Screen):
	def Power(self):
		print "[Standby] leave standby"
		if (getBrandOEM() in ('fulan')):
			open("/proc/stb/hdmi/output", "w").write("on")
		#set input to encoder
		self.avswitch.setInput("ENCODER")
		#restart last played service
		#unmute adc
		self.leaveMute()
		# set LCDminiTV 
		if SystemInfo["Display"] and SystemInfo["LCDMiniTV"]:
			setLCDModeMinitTV(config.lcd.modeminitv.value)
		#kill me
		self.close(True)

	def setMute(self):
		if eDVBVolumecontrol.getInstance().isMuted():
			self.wasMuted = 1
			print "[Standby] mute already active"
		else:
			self.wasMuted = 0
			eDVBVolumecontrol.getInstance().volumeToggleMute()

	def leaveMute(self):
		if self.wasMuted == 0:
			eDVBVolumecontrol.getInstance().volumeToggleMute()

	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = "Standby"
		self.avswitch = AVSwitch()

		print "[Standby] enter standby"

		self["actions"] = ActionMap( [ "StandbyActions" ],
		{
			"power": self.Power,
			"discrete_on": self.Power
		}, -1)

		globalActionMap.setEnabled(False)

		self.standbyStopServiceTimer = eTimer()
		self.standbyStopServiceTimer.callback.append(self.stopService)
		self.timeHandler = None

		#mute adc
		self.setMute()
	
		if SystemInfo["Display"] and SystemInfo["LCDMiniTV"]:
			# set LCDminiTV off
			setLCDModeMinitTV("0")

		self.paused_service = None
		self.prev_running_service = None

		self.prev_running_service = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		service = self.prev_running_service and self.prev_running_service.toString()
		if service:
			if service.startswith("1:") and service.rsplit(":", 1)[1].startswith("/"):
				self.paused_service = self.session.current_dialog
				self.paused_service.pauseService()
			else:
				self.timeHandler =  eDVBLocalTimeHandler.getInstance()
				if self.timeHandler.ready():
					if self.session.nav.getCurrentlyPlayingServiceOrGroup():
						self.stopService()
					else:
						self.standbyStopServiceTimer.startLongTimer(5)
					self.timeHandler = None
				else:
					self.timeHandler.m_timeUpdated.get().append(self.stopService)

		if self.session.pipshown:
			from Screens.InfoBar import InfoBar
			InfoBar.instance and hasattr(InfoBar.instance, "showPiP") and InfoBar.instance.showPiP()

		#set input to vcr scart
		if SystemInfo["ScartSwitch"]:
			self.avswitch.setInput("SCART")
		else:
			self.avswitch.setInput("AUX")
		if (getBrandOEM() in ('fulan')):
			open("/proc/stb/hdmi/output", "w").write("off")

		if int(config.usage.hdd_standby_in_standby.value) != -1: # HDD standby timer value (box in standby) / -1 = same as when box is active
			for hdd in harddiskmanager.HDDList():
				hdd[1].setIdleTime(int(config.usage.hdd_standby_in_standby.value))

		self.onFirstExecBegin.append(self.__onFirstExecBegin)
		self.onClose.append(self.__onClose)

	def __onClose(self):
		global inStandby
		inStandby = None
		self.standbyStopServiceTimer.stop()
		self.timeHandler and self.timeHandler.m_timeUpdated.get().remove(self.stopService)
		if self.paused_service:
			self.paused_service.unPauseService()
		elif self.prev_running_service:
			service = self.prev_running_service.toString()
			if config.servicelist.startupservice_onstandby.value:
				self.session.nav.playService(eServiceReference(config.servicelist.startupservice.value))
				from Screens.InfoBar import InfoBar
				InfoBar.instance and InfoBar.instance.servicelist.correctChannelNumber()
			else:
				self.session.nav.playService(self.prev_running_service)
		self.session.screen["Standby"].boolean = False
		globalActionMap.setEnabled(True)
		for hdd in harddiskmanager.HDDList():
			hdd[1].setIdleTime(int(config.usage.hdd_standby.value)) # HDD standby timer value (box active)

	def __onFirstExecBegin(self):
		global inStandby
		inStandby = self
		self.session.screen["Standby"].boolean = True
		config.misc.standbyCounter.value += 1

	def createSummary(self):
		return StandbySummary

	def stopService(self):
		self.session.nav.stopService()

class Standby(Standby2):
	def __init__(self, session):
		if Screens.InfoBar.InfoBar and Screens.InfoBar.InfoBar.instance and Screens.InfoBar.InfoBar.ptsGetTimeshiftStatus(Screens.InfoBar.InfoBar.instance):
			self.skin = """<screen position="0,0" size="0,0"/>"""
			Screen.__init__(self, session)
			self.onFirstExecBegin.append(self.showMessageBox)
			self.onHide.append(self.close)
		else:
			Standby2.__init__(self, session)
			self.skinName = "Standby"

	def showMessageBox(self):
		Screens.InfoBar.InfoBar.checkTimeshiftRunning(Screens.InfoBar.InfoBar.instance, self.showMessageBoxcallback)

	def showMessageBoxcallback(self, answer):
		if answer:
			self.onClose.append(self.doStandby)

	def doStandby(self):
		Notifications.AddNotification(Screens.Standby.Standby2)

class StandbySummary(Screen):
	skin = """
	<screen position="0,0" size="132,64">
		<widget source="global.CurrentTime" render="Label" position="0,0" size="132,64" font="Regular;40" halign="center">
			<convert type="ClockToText" />
		</widget>
		<widget source="session.RecordState" render="FixedLabel" text=" " position="0,0" size="132,64" zPosition="1" >
			<convert type="ConfigEntryTest">config.usage.blinking_display_clock_during_recording,True,CheckSourceBoolean</convert>
			<convert type="ConditionalShowHide">Blink</convert>
		</widget>
	</screen>"""

from enigma import quitMainloop, iRecordableService
from Screens.MessageBox import MessageBox
from time import time
from Components.Task import job_manager

class QuitMainloopScreen(Screen):
	def __init__(self, session, retvalue=1):
		self.skin = """<screen name="QuitMainloopScreen" position="fill" flags="wfNoBorder">
			<ePixmap pixmap="icons/input_info.png" position="c-27,c-60" size="53,53" alphatest="on" />
			<widget name="text" position="center,c+5" size="720,100" font="Regular;22" halign="center" />
		</screen>"""
		Screen.__init__(self, session)
		from Components.Label import Label
		text = { 1: _("Your %s %s is shutting down") % (getMachineBrand(), getMachineName()),
			2: _("Your %s %s is rebooting") % (getMachineBrand(), getMachineName()),
			3: _("The user interface of your %s %s is restarting") % (getMachineBrand(), getMachineName()),
			4: _("Your frontprocessor will be upgraded\nPlease wait until your %s %s reboots\nThis may take a few minutes") % (getMachineBrand(), getMachineName()),
			5: _("The user interface of your %s %s is restarting\ndue to an error in mytest.py") % (getMachineBrand(), getMachineName()),
			42: _("Upgrade in progress\nPlease wait until your %s %s reboots\nThis may take a few minutes") % (getMachineBrand(), getMachineName()),
			43: _("Reflash in progress\nPlease wait until your %s %s reboots\nThis may take a few minutes") % (getMachineBrand(), getMachineName()),
			44: _("Your front panel will be upgraded\nThis may take a few minutes"),
			45: _("Your %s %s goes to WOL") % (getMachineBrand(), getMachineName())}.get(retvalue)
		self["text"] = Label(text)

inTryQuitMainloop = False
quitMainloopCode = 1

class TryQuitMainloop(MessageBox):
	def __init__(self, session, retvalue=1, timeout=-1, default_yes = True):
		self.retval = retvalue
		self.ptsmainloopvalue = retvalue
		recordings = session.nav.getRecordings(False,Components.RecordingConfig.recType(config.recording.warn_box_restart_rec_types.getValue()))
		jobs = len(job_manager.getPendingJobs())
		inTimeshift = Screens.InfoBar.InfoBar and Screens.InfoBar.InfoBar.instance and Screens.InfoBar.InfoBar.ptsGetTimeshiftStatus(Screens.InfoBar.InfoBar.instance)
		self.connected = False
		reason = ""
		next_rec_time = -1
		if not recordings:
			next_rec_time = session.nav.RecordTimer.getNextRecordingTime()
#		if jobs:
#			reason = (ngettext("%d job is running in the background!", "%d jobs are running in the background!", jobs) % jobs) + '\n'
#			if jobs == 1:
#				job = job_manager.getPendingJobs()[0]
#				if job.name == "VFD Checker":
#					reason = ""
#				else:
#					reason += "%s: %s (%d%%)\n" % (job.getStatustext(), job.name, int(100*job.progress/float(job.end)))
#			else:
#				reason += (_("%d jobs are running in the background!") % jobs) + '\n'
		if inTimeshift:
			reason = _("You seem to be in timeshift!") + '\n'
			default_yes = True
			timeout=30
		if recordings or (next_rec_time > 0 and (next_rec_time - time()) < 360):
			default_yes = False
			reason = _("Recording(s) are in progress or coming up in few seconds!") + '\n'

		if reason and inStandby:
			session.nav.record_event.append(self.getRecordEvent)
			self.skinName = ""
		elif reason and not inStandby:
			text = { 1: _("Really shutdown now?"),
				2: _("Really reboot now?"),
				3: _("Really restart now?"),
				4: _("Really upgrade the frontprocessor and reboot now?"),
				42: _("Really upgrade your %s %s and reboot now?") % (getMachineBrand(), getMachineName()),
				43: _("Really reflash your %s %s and reboot now?") % (getMachineBrand(), getMachineName()),
				44: _("Really upgrade the front panel and reboot now?"),
				45: _("Really WOL now?")}.get(retvalue)
			if text:
				MessageBox.__init__(self, session, reason+text, type = MessageBox.TYPE_YESNO, timeout = timeout, default = default_yes)
				self.skinName = "MessageBoxSimple"
				session.nav.record_event.append(self.getRecordEvent)
				self.connected = True
				self.onShow.append(self.__onShow)
				self.onHide.append(self.__onHide)
				return
		self.skin = """<screen position="1310,0" size="0,0"/>"""
		Screen.__init__(self, session)
		self.close(True)

	def getRecordEvent(self, recservice, event):
		if event == iRecordableService.evEnd and config.timeshift.isRecording.value:
			return
		else:
			if event == iRecordableService.evEnd:
				recordings = self.session.nav.getRecordings(False,Components.RecordingConfig.recType(config.recording.warn_box_restart_rec_types.getValue()))
				if not recordings: # no more recordings exist
					rec_time = self.session.nav.RecordTimer.getNextRecordingTime()
					if rec_time > 0 and (rec_time - time()) < 360:
						self.initTimeout(360) # wait for next starting timer
						self.startTimer()
					else:
						self.close(True) # immediate shutdown
			elif event == iRecordableService.evStart:
				self.stopTimer()

	def close(self, value):
		global quitMainloopCode
		if self.connected:
			self.connected=False
			self.session.nav.record_event.remove(self.getRecordEvent)
		if value:
			self.hide()
			if self.retval == 1:
				config.misc.DeepStandby.value = True
			self.session.nav.stopService()
			self.quitScreen = self.session.instantiateDialog(QuitMainloopScreen,retvalue=self.retval)
			self.quitScreen.show()
			print "[Standby] quitMainloop #1"
			quitMainloopCode = self.retval
			if getBoxType() == "vusolo4k":  #workaround for white display flash
				open("/proc/stb/fp/oled_brightness", "w").write("0")
			quitMainloop(self.retval)
		else:
			MessageBox.close(self, True)

	def __onShow(self):
		global inTryQuitMainloop
		inTryQuitMainloop = True

	def __onHide(self):
		global inTryQuitMainloop
		inTryQuitMainloop = False

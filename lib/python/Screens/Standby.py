import os
from time import time, localtime

import RecordTimer
from Screen import Screen
from Components.ActionMap import ActionMap
from Components.config import config
from Components.AVSwitch import AVSwitch
from Components.Console import Console
from Components.Harddisk import internalHDDNotSleeping
from Components.SystemInfo import SystemInfo
from Tools import Notifications
from GlobalActions import globalActionMap
from enigma import eDVBVolumecontrol, eTimer, eDVBLocalTimeHandler, eServiceReference
import Screens.InfoBar
from boxbranding import getMachineBrand, getMachineName, getBoxType

inStandby = None

MACHINEBRAND = getMachineBrand()
MACHINENAME = getMachineName()
BOXTYPE = getBoxType()

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
		if os.path.exists("/usr/script/Standby.sh"):
			Console().ePopen("/usr/script/Standby.sh on")
		if os.path.exists("/usr/script/standby_leave.sh"):
			Console().ePopen("/usr/script/standby_leave.sh")

		self.leaveMute()
		# set LCDminiTV
		if SystemInfo["Display"] and SystemInfo["LCDMiniTV"]:
			setLCDModeMinitTV(config.lcd.modeminitv.getValue())
		#kill me
		self.close(True)

	def setMute(self):
		if (eDVBVolumecontrol.getInstance().isMuted()):
			self.wasMuted = 1
			print "[Standby] mute already active"
		else:
			self.wasMuted = 0
			eDVBVolumecontrol.getInstance().volumeToggleMute()

	def leaveMute(self):
		if self.wasMuted == 0:
			eDVBVolumecontrol.getInstance().volumeToggleMute()

	def __init__(self, session, StandbyCounterIncrease=True):
		Screen.__init__(self, session)
		self.skinName = "Standby"
		self.avswitch = AVSwitch()

		print "[Standby] enter standby"
		if os.path.exists("/usr/script/Standby.sh"):
			Console().ePopen("/usr/script/Standby.sh off")
		if os.path.exists("/usr/script/standby_enter.sh"):
			Console().ePopen("/usr/script/standby_enter.sh")

		self["actions"] = ActionMap( [ "StandbyActions" ],
		{
			"power": self.Power,
			"discrete_on": self.Power
		}, -1)

		globalActionMap.setEnabled(False)

		from Screens.InfoBar import InfoBar
		self.infoBarInstance = InfoBar.instance
		self.StandbyCounterIncrease = StandbyCounterIncrease
		self.standbyTimeoutTimer = eTimer()
		self.standbyTimeoutTimer.callback.append(self.standbyTimeout)
		self.standbyStopServiceTimer = eTimer()
		self.standbyStopServiceTimer.callback.append(self.stopService)
		self.timeHandler = None

		self.setMute()

		# set LCDminiTV off
		if SystemInfo["Display"] and SystemInfo["LCDMiniTV"]:
			setLCDModeMinitTV("0")

		self.paused_service = self.paused_action = False

		self.prev_running_service = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		service = self.prev_running_service and self.prev_running_service.toString()
		if service:
			if service.rsplit(":", 1)[1].startswith("/"):
				self.paused_service = hasattr(self.session.current_dialog, "pauseService") and hasattr(self.session.current_dialog, "unPauseService") and self.session.current_dialog or self.infoBarInstance
				self.paused_action = hasattr(self.paused_service, "seekstate") and hasattr(self.paused_service, "SEEK_STATE_PLAY") and self.paused_service.seekstate == self.paused_service.SEEK_STATE_PLAY
				self.paused_action and self.paused_service.pauseService()
		if not self.paused_service:
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
			self.infoBarInstance and hasattr(self.infoBarInstance, "showPiP") and self.infoBarInstance.showPiP()

		if SystemInfo["ScartSwitch"]:
			self.avswitch.setInput("SCART")
		else:
			self.avswitch.setInput("AUX")

		gotoShutdownTime = int(config.usage.standby_to_shutdown_timer.value)
		if gotoShutdownTime:
			self.standbyTimeoutTimer.startLongTimer(gotoShutdownTime)

		self.onFirstExecBegin.append(self.__onFirstExecBegin)
		self.onClose.append(self.__onClose)

	def __onClose(self):
		global inStandby
		inStandby = None
		self.standbyTimeoutTimer.stop()
		self.standbyStopServiceTimer.stop()
		self.timeHandler and self.timeHandler.m_timeUpdated.get().remove(self.stopService)
		if self.paused_service:
			self.paused_action and self.paused_service.unPauseService()
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
		if RecordTimer.RecordTimerEntry.receiveRecordEvents:
			RecordTimer.RecordTimerEntry.stopTryQuitMainloop()
		self.avswitch.setInput("ENCODER")
		if os.path.exists("/usr/script/Standby.sh"):
			Console().ePopen("/usr/script/Standby.sh on")
		if os.path.exists("/usr/script/standby_leave.sh"):
			Console().ePopen("/usr/script/standby_leave.sh")

	def __onFirstExecBegin(self):
		global inStandby
		inStandby = self
		self.session.screen["Standby"].boolean = True
		if self.StandbyCounterIncrease:
			config.misc.standbyCounter.value += 1

	def stopService(self):
		self.prev_running_service = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		self.session.nav.stopService()

	def createSummary(self):
		return StandbySummary

	def standbyTimeout(self):
		if config.usage.standby_to_shutdown_timer_blocktime.value:
			curtime = localtime(time())
			if curtime.tm_year > 1970: #check if the current time is valid
				curtime = (curtime.tm_hour, curtime.tm_min, curtime.tm_sec)
				begintime = tuple(config.usage.standby_to_shutdown_timer_blocktime_begin.value)
				endtime = tuple(config.usage.standby_to_shutdown_timer_blocktime_end.value)
				if begintime <= endtime and (curtime >= begintime and curtime < endtime) or begintime > endtime and (curtime >= begintime or curtime < endtime):
					duration = (endtime[0]*3600 + endtime[1]*60) - (curtime[0]*3600 + curtime[1]*60 + curtime[2])
					if duration:
						if duration < 0:
							duration += 24*3600
						self.standbyTimeoutTimer.startLongTimer(duration)
						return
		if self.session.screen["TunerInfo"].tuner_use_mask or internalHDDNotSleeping():
			self.standbyTimeoutTimer.startLongTimer(600)
		else:
			from RecordTimer import RecordTimerEntry
			RecordTimerEntry.TryQuitMainloop()

class Standby(Standby2):
	def __init__(self, session):
		Standby2.__init__(self, session)
		self.skinName = "Standby"

	def stopService(self):
		self.prev_running_service = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		self.session.nav.stopService()

class StandbySummary(Screen):
	if getBoxType() in ('gbuhdquad', 'gbquadplus', 'gbquad', 'gbultraue', 'gb800ueplus', 'gb800ue'):
		def __init__(self, session, what = None):
			root = "/usr/share/enigma2/lcd_skin/"
			try:
				what = open(root+"active").read()
			except:
				what = "clock_lcd_analog.xml"
			tmpskin = root+what
			self.skin = open(tmpskin,'r').read()
			Screen.__init__(self, session)
	else:
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
			<ePixmap pixmap="skin_default/icons/input_info.png" position="c-27,c-60" size="53,53" alphatest="on" />
			<widget name="text" position="center,c+5" size="720,100" font="Regular;22" halign="center" />
		</screen>"""
		Screen.__init__(self, session)
		from Components.Label import Label
		text = { 1: _("Your %s %s is shutting down") % (MACHINEBRAND, MACHINENAME),
			2: _("Your %s %s is rebooting") % (MACHINEBRAND, MACHINENAME),
			3: _("The user interface of your %s %s is restarting") % (MACHINEBRAND, MACHINENAME),
			4: _("Your frontprocessor will be upgraded\nPlease wait until your %s %s reboots\nThis may take a few minutes") % (MACHINEBRAND, MACHINENAME),
			5: _("The user interface of your %s %s is restarting\ndue to an error in mytest.py") % (MACHINEBRAND, MACHINENAME),
			42: _("Unattended upgrade in progress\nPlease wait until your %s %s reboots\nThis may take a few minutes") % (MACHINEBRAND, MACHINENAME),
			43: _("Your %s %s goes to WOL") % (MACHINEBRAND, MACHINENAME)}.get(retvalue)
		self["text"] = Label(text)

inTryQuitMainloop = False

class TryQuitMainloop(MessageBox):
	def __init__(self, session, retvalue=1, timeout=-1, default_yes = False):
		self.retval = retvalue
		self.ptsmainloopvalue = retvalue
		recordings = session.nav.getRecordings()
		jobs = len(job_manager.getPendingJobs())
		self.connected = False
		reason = ""
		next_rec_time = -1
		if not recordings:
			next_rec_time = session.nav.RecordTimer.getNextRecordingTime()
		if recordings or (next_rec_time > 0 and (next_rec_time - time()) < 360):
			reason = _("Recording(s) are in progress or coming up in few seconds!") + '\n'
		if jobs:
			reason = _("Job task(s) are in progress!") + '\n'
			if jobs == 1:
				job = job_manager.getPendingJobs()[0]
				reason += "%s: %s (%d%%)\n" % (job.getStatustext(), job.name, int(100*job.progress/float(job.end)))
			else:
				reason += (_("%d jobs are running in the background!") % jobs) + '\n'
			if job.name == "VFD Checker":
				reason = ""
		if recordings or (next_rec_time > 0 and (next_rec_time - time()) < 360):
			reason = _("Recording(s) are in progress or coming up in few seconds!") + '\n'

		if reason and inStandby:
			session.nav.record_event.append(self.getRecordEvent)
			self.skinName = ""
		elif reason and not inStandby:
			text = { 1: _("Really shutdown your %s %s now?") % (MACHINEBRAND, MACHINENAME),
				2: _("Really reboot your %s %s now?") % (MACHINEBRAND, MACHINENAME),
				3: _("Really restart your %s %s now?") % (MACHINEBRAND, MACHINENAME),
				4: _("Really upgrade the frontprocessor and reboot now?"),
				42: _("Really upgrade your %s %s and reboot now?") % (MACHINEBRAND, MACHINENAME),
				43: _("Really WOL now?")}.get(retvalue)
			if text:
				MessageBox.__init__(self, session, reason+text, type = MessageBox.TYPE_YESNO, timeout = timeout, default = default_yes)
				self.skinName = "MessageBoxSimple"
				session.nav.record_event.append(self.getRecordEvent)
				self.connected = True
				self.onShow.append(self.__onShow)
				self.onHide.append(self.__onHide)
				return
		self.skin = """<screen position="0,0" size="0,0"/>"""
		Screen.__init__(self, session)
		self.close(True)

	def getRecordEvent(self, recservice, event):
		if event == iRecordableService.evEnd and config.timeshift.isRecording.value:
			return
		else:
			if event == iRecordableService.evEnd:
				recordings = self.session.nav.getRecordings()
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
		if self.connected:
			self.connected=False
			self.session.nav.record_event.remove(self.getRecordEvent)
		if value:
			self.hide()
			if self.retval == 1:
				config.misc.DeepStandby.value = True
				if os.path.exists("/usr/script/Standby.sh"):
					Console().ePopen("/usr/script/Standby.sh off")
				if os.path.exists("/usr/script/standby_enter.sh"):
					Console().ePopen("/usr/script/standby_enter.sh")
			self.session.nav.stopService()
			self.quitScreen = self.session.instantiateDialog(QuitMainloopScreen,retvalue=self.retval)
			self.quitScreen.show()
			quitMainloop(self.retval)
		else:
			MessageBox.close(self, True)

	def __onShow(self):
		global inTryQuitMainloop
		inTryQuitMainloop = True

	def __onHide(self):
		global inTryQuitMainloop
		inTryQuitMainloop = False

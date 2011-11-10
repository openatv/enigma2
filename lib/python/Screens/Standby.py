from Screen import Screen
from Components.ActionMap import ActionMap
from Components.config import config
from Components.AVSwitch import AVSwitch
from Components.SystemInfo import SystemInfo
from GlobalActions import globalActionMap
from enigma import eDVBVolumecontrol

inStandby = None

class Standby(Screen):
	def Power(self):
		print "leave standby"
		#set input to encoder
		self.avswitch.setInput("ENCODER")
		#restart last played service
		#unmute adc
		self.leaveMute()
		#kill me
		self.close(True)

	def setMute(self):
		if (eDVBVolumecontrol.getInstance().isMuted()):
			self.wasMuted = 1
			print "mute already active"
		else:	
			self.wasMuted = 0
			eDVBVolumecontrol.getInstance().volumeToggleMute()

	def leaveMute(self):
		if self.wasMuted == 0:
			eDVBVolumecontrol.getInstance().volumeToggleMute()

	def __init__(self, session):
		Screen.__init__(self, session)
		self.avswitch = AVSwitch()

		print "enter standby"

		self["actions"] = ActionMap( [ "StandbyActions" ],
		{
			"power": self.Power,
			"discrete_on": self.Power
		}, -1)

		globalActionMap.setEnabled(False)

		#mute adc
		self.setMute()

		self.paused_service = None
		self.prev_running_service = None
		if self.session.current_dialog:
			if self.session.current_dialog.ALLOW_SUSPEND == Screen.SUSPEND_STOPS:
				#get currently playing service reference
				self.prev_running_service = self.session.nav.getCurrentlyPlayingServiceReference()
				#stop actual played dvb-service
				self.session.nav.stopService()
			elif self.session.current_dialog.ALLOW_SUSPEND == Screen.SUSPEND_PAUSES:
				self.paused_service = self.session.current_dialog
				self.paused_service.pauseService()

		#set input to vcr scart
		if SystemInfo["ScartSwitch"]:
			self.avswitch.setInput("SCART")
		else:
			self.avswitch.setInput("AUX")
		self.onFirstExecBegin.append(self.__onFirstExecBegin)
		self.onClose.append(self.__onClose)

	def __onClose(self):
		global inStandby
		inStandby = None
		if self.prev_running_service:
			self.session.nav.playService(self.prev_running_service)
		elif self.paused_service:
			self.paused_service.unPauseService()
		self.session.screen["Standby"].boolean = False
		globalActionMap.setEnabled(True)

	def __onFirstExecBegin(self):
		global inStandby
		inStandby = self
		self.session.screen["Standby"].boolean = True
		config.misc.standbyCounter.value += 1

	def createSummary(self):
		return StandbySummary

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

inTryQuitMainloop = False

class TryQuitMainloop(MessageBox):
	def __init__(self, session, retvalue=1, timeout=-1, default_yes = True):
		self.retval=retvalue
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
			if jobs == 1:
				job = job_manager.getPendingJobs()[0]
				reason += "%s: %s (%d%%)\n" % (job.getStatustext(), job.name, int(100*job.progress/float(job.end)))
			else:
				reason += (_("%d jobs are running in the background!") % jobs) + '\n'
		if reason:
			if retvalue == 1:
				MessageBox.__init__(self, session, reason+_("Really shutdown now?"), type = MessageBox.TYPE_YESNO, timeout = timeout, default = default_yes)
			elif retvalue == 2:
				MessageBox.__init__(self, session, reason+_("Really reboot now?"), type = MessageBox.TYPE_YESNO, timeout = timeout, default = default_yes)
			elif retvalue == 4:
				pass
			else:
				MessageBox.__init__(self, session, reason+_("Really restart now?"), type = MessageBox.TYPE_YESNO, timeout = timeout, default = default_yes)
			self.skinName = "MessageBox"
			session.nav.record_event.append(self.getRecordEvent)
			self.connected = True
			self.onShow.append(self.__onShow)
			self.onHide.append(self.__onHide)
		else:
			self.skin = """<screen position="0,0" size="0,0"/>"""
			Screen.__init__(self, session)
			self.close(True)

	def getRecordEvent(self, recservice, event):
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
			self.conntected=False
			self.session.nav.record_event.remove(self.getRecordEvent)
		if value:
			if self.retval == 1:
				config.misc.DeepStandby.value = True
			quitMainloop(self.retval)
		else:
			MessageBox.close(self, True)

	def __onShow(self):
		global inTryQuitMainloop
		inTryQuitMainloop = True

	def __onHide(self):
		global inTryQuitMainloop
		inTryQuitMainloop = False

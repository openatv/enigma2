from Screen import Screen
from Components.ActionMap import ActionMap
from Components.config import config
from Components.AVSwitch import AVSwitch
from enigma import eDVBVolumecontrol, eDBoxLCD, eServiceReference
from Components.Sources.Clock import Clock

inStandby = None

class Standby(Screen):
	def Power(self):
		print "leave standby"
		#set input to encoder
		self.avswitch.setInput("ENCODER")
		#restart last played service
		if self.prev_running_service:
			self.session.nav.playService(self.prev_running_service)
		#unmute adc
		self.leaveMute()
		#set brightness of lcd
		eDBoxLCD.getInstance().setLCDBrightness(config.lcd.bright.value * 20)
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
			"power": self.Power
		}, -1)

		#mute adc
		self.setMute()
		#get currently playing service reference
		self.prev_running_service = self.session.nav.getCurrentlyPlayingServiceReference()
		#stop actual played dvb-service
		self.session.nav.stopService()
		#set input to vcr scart
		self.avswitch.setInput("SCART")
		#set lcd brightness to standby value
		eDBoxLCD.getInstance().setLCDBrightness(config.lcd.standby.value * 20)
		self.onShow.append(self.__onShow)
		self.onHide.append(self.__onHide)

	def createSummary(self):
		return StandbySummary

	def __onShow(self):
		global inStandby
		inStandby = self

	def __onHide(self):
		global inStandby
		inStandby = None

class StandbySummary(Screen):
	skin = """
	<screen position="0,0" size="132,64">
		<widget source="CurrentTime" render="Label" position="0,0" size="132,64" font="Regular;40" halign="center">
			<convert type="ClockToText" />
		</widget>
	</screen>"""

	def __init__(self, session, parent):
		Screen.__init__(self, session)
		self["CurrentTime"] = Clock()

from enigma import quitMainloop, iRecordableService
from Screens.MessageBox import MessageBox
from time import time

inTryQuitMainloop = False

class TryQuitMainloop(MessageBox):
	def __init__(self, session, retvalue=1, timeout=-1):
		self.retval=retvalue
		recordings = len(session.nav.getRecordings())
		self.connected = False
		next_rec_time = -1
		if not recordings:
			next_rec_time = session.nav.RecordTimer.getNextRecordingTime()
		if recordings or (next_rec_time > 0 and (next_rec_time - time()) < 360):
			if retvalue == 1:
				MessageBox.__init__(self, session, _("Recording(s) are in progress or coming up in few seconds... really shutdown now?"), type = MessageBox.TYPE_YESNO, timeout = timeout)
			elif retvalue == 2:
				MessageBox.__init__(self, session, _("Recording(s) are in progress or coming up in few seconds... really reboot now?"), type = MessageBox.TYPE_YESNO, timeout = timeout)
			elif retvalue == 4:
				pass
			else:
				MessageBox.__init__(self, session, _("Recording(s) are in progress or coming up in few seconds... really restart now?"), type = MessageBox.TYPE_YESNO, timeout = timeout)
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
			if not len(recordings): # no more recordings exist
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
			quitMainloop(self.retval)
		else:
			MessageBox.close(self, True)

	def __onShow(self):
		global inTryQuitMainloop
		inTryQuitMainloop = True

	def __onHide(self):
		global inTryQuitMainloop
		inTryQuitMainloop = False

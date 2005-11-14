from Screen import Screen
from Components.ActionMap import ActionMap
from Components.config import config
from enigma import *

class Standby(Screen):
	def Power(self):
		print "leave standby"
		#start last played service
		eAVSwitch.getInstance().setInput(0)
		self.infobar.servicelist.zap()
		self.leaveMute()
		eDBoxLCD.getInstance().setLCDBrightness(config.lcd.bright.value * 20)
		self.close()

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

	def __init__(self, session, infobar):
		Screen.__init__(self, session)
		self.infobar = infobar
		print "enter standby"

		self["actions"] = ActionMap( [ "StandbyActions" ],
		{
			"power": self.Power
		})

		self.setMute()
		self.session.nav.stopService()
		eAVSwitch.getInstance().setInput(1)
		eDBoxLCD.getInstance().setLCDBrightness(config.lcd.standby.value * 20)
	
		
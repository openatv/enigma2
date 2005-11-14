from Screen import Screen
from Components.ActionMap import ActionMap
from Components.config import config
from enigma import *

class Standby(Screen):
	def Power(self):
		print "leave standby"
		#set input to encoder
		eAVSwitch.getInstance().setInput(0)
		#start last played service
		self.infobar.servicelist.zap()
		#unmute adc
		self.leaveMute()
		#set brightness of lcd
		eDBoxLCD.getInstance().setLCDBrightness(config.lcd.bright.value * 20)
		#kill me
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

		#mute adc
		self.setMute()
		#stop actual played dvb-service
		self.session.nav.stopService()
		#set input to vcr scart
		eAVSwitch.getInstance().setInput(1)
		#set lcd brightness to standby value
		eDBoxLCD.getInstance().setLCDBrightness(config.lcd.standby.value * 20)
		#clear lcd (servicename)
		setLCD("                             ")

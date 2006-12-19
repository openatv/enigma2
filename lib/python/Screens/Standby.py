from Screen import Screen
from Components.ActionMap import ActionMap
from Components.config import config
from Components.AVSwitch import AVSwitch
from enigma import eDVBVolumecontrol, eDBoxLCD, eServiceReference

class Standby(Screen):
	def Power(self):
		print "leave standby"
		#set input to encoder
		self.avswitch.setInput("ENCODER")
		#start last played service
		#self.infobar.servicelist.zap()
		self.session.nav.playService(eServiceReference(config.tv.lastservice.value))
		
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
		self. avswitch = AVSwitch()
		print "enter standby"

		self["actions"] = ActionMap( [ "StandbyActions" ],
		{
			"power": self.Power
		}, -1)

		#mute adc
		self.setMute()
		#stop actual played dvb-service
		self.session.nav.stopService()
		#set input to vcr scart
		self.avswitch.setInput("SCART")
		#set lcd brightness to standby value
		eDBoxLCD.getInstance().setLCDBrightness(config.lcd.standby.value * 20)

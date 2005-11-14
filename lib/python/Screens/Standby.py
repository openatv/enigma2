from Screen import Screen
from Components.ActionMap import ActionMap
from enigma import *

class Standby(Screen):
	def Power(self):
		print "leave standby"
		#start last played service
		self.infobar.servicelist.zap()
		self.leaveMute()
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
		
		#stop/pause? playing services
		#switch off avs
		
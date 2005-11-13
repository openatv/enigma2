from Screen import Screen
from Components.ActionMap import ActionMap

class Standby(Screen):
	def Power(self):
		print "leave standby"
		#start last played service
		self.infobar.servicelist.zap()
		self.close()

	def __init__(self, session, infobar):
		Screen.__init__(self, session)
		self.infobar = infobar
		print "enter standby"

		self["actions"] = ActionMap( [ "StandbyActions" ],
		{
			"power": self.Power
		})

		self.session.nav.stopService()
		#stop/pause? playing services
		#switch off avs
		
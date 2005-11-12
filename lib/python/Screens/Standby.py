from Screen import Screen
from Components.ActionMap import ActionMap

class Standby(Screen):
	def Power(self):
		print "leave standby"
		self.close()

	def __init__(self, session):
		Screen.__init__(self, session)
		
		print "enter standby"

		self["actions"] = ActionMap( [ "StandbyActions" ],
		{
			"power": self.Power
		})
		
		#stop/pause? playing services
		#switch off avs
		
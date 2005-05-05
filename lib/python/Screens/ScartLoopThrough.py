from Screen import Screen
from Components.ActionMap import ActionMap

class ScartLoopThrough(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		self["actions"] = ActionMap(["OkCancelActions"], 
			{
				"cancel": self.close
			})


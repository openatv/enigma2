from Screens.Screen import Screen
from Components.TimerList import TimerList
from Components.ActionMap import ActionMap

class TimerSelection(Screen):
	def __init__(self, session, list):
		Screen.__init__(self, session)
		self.setTitle(_("Timer selection"))

		self.list = list

		self["timerlist"] = TimerList(self.list)

		self["actions"] = ActionMap(["OkCancelActions"],
			{
				"ok": self.selected,
				"cancel": self.leave,
			}, -1)


	def leave(self):
		self.close(None)

	def selected(self):
		self.close(self["timerlist"].getCurrentIndex())

from Screens.Screen import Screen
from Components.Sources.List import List
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText


class FixedMenu(Screen):
	def okbuttonClick(self):
		selection = self["menu"].getCurrent()
		if selection and len(selection) > 1:
			selection[1]()

	def __init__(self, session, title, list):
		Screen.__init__(self, session)

		self["menu"] = List(list)

		self["actions"] = ActionMap(["OkCancelActions"],
			{
				"ok": self.okbuttonClick,
				"cancel": self.close
			})

		self["title"] = StaticText(title)

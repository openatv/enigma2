from Screen import Screen
from Components.Sources.MenuList import MenuList
from Components.ActionMap import ActionMap
from Components.Header import Header

class FixedMenu(Screen):
	def okbuttonClick(self):
		selection = self["menu"].getCurrent()
		selection[1]()

	def __init__(self, session, title, list):
		Screen.__init__(self, session)

		self["menu"] = MenuList(list)	

		self["actions"] = ActionMap(["OkCancelActions"], 
			{
				"ok": self.okbuttonClick,
				"cancel": self.close
			})

		self["title"] = Header(title)

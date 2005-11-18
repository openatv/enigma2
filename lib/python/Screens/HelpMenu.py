from Screen import Screen

from Components.ActionMap import ActionMap
from Components.HelpMenuList import HelpMenuList

class HelpMenu(Screen):
	def __init__(self, session, list):
		Screen.__init__(self, session)
		
		self["list"] = HelpMenuList(list, self.close)
		self["actions"] = ActionMap(["OkCancelActions"],
			{
				"cancel": self.close,
				"ok": self["list"].ok,
			})

class HelpableScreen:
	def __init__(self):
		self["helpActions"] = ActionMap( [ "HelpActions" ],
			{
				"displayHelp": self.showHelp,
			})

	def showHelp(self):
		self.session.openWithCallback(self.callHelpAction, HelpMenu, self.helpList)

	def callHelpAction(self, *args):
		if len(args):
			(actionmap, context, action) = args
			actionmap.action(context, action)

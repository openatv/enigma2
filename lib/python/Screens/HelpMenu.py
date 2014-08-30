from Screens.Screen import Screen
from Components.Label import Label
from Components.ActionMap import ActionMap
from Components.HelpMenuList import HelpMenuList
from Screens.Rc import Rc

class HelpMenu(Screen, Rc):
	def __init__(self, session, list):
		Screen.__init__(self, session)
		self.onSelChanged = [ ]
		self["list"] = HelpMenuList(list, self.close)
		Rc.__init__(self)
		self["long_key"] = Label("")

		self["actions"] = ActionMap(["WizardActions"],
		{
			"ok": self["list"].ok,
			"back": self.close,
		}, -1)

		self.onLayoutFinish.append(self.SelectionChanged)
		self.onFirstExecBegin.append(self.doOnFirstExecBegin)

	def doOnFirstExecBegin(self):
		self["list"].onSelChanged.append(self.SelectionChanged)

	def SelectionChanged(self):
		self.clearSelectedKeys()
		selection = self["list"].getCurrent()

		longText = ""
		if selection:
			selection = selection[3][0]
			print "selection:", selection
			if len(selection) > 1:
				if selection[1] == "SHIFT":
					self.selectKey("SHIFT")
				elif selection[1] == "long":
					longText = _("Long key press")
			self.selectKey(selection[0])

		self["long_key"].setText(longText)

class HelpableScreen:
	def __init__(self):
		self["helpActions"] = ActionMap( [ "HelpActions" ],
			{
				"displayHelp": self.showHelp,
			})

	def showHelp(self):
		try:
			if self.secondInfoBarScreen and self.secondInfoBarScreen.shown:
				self.secondInfoBarScreen.hide()
		except:
			pass
		self.session.openWithCallback(self.callHelpAction, HelpMenu, self.helpList)

	def callHelpAction(self, *args):
		if args:
			(actionmap, context, action) = args
			actionmap.action(context, action)

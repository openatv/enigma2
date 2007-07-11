from Screen import Screen

from Components.Pixmap import *
from Components.Pixmap import Pixmap
from Components.Pixmap import MovingPixmap
from Components.Label import Label
from Components.Slider import Slider
from Components.ActionMap import ActionMap
from Components.HelpMenuList import HelpMenuList
import string
from xml.sax import make_parser
from xml.sax.handler import ContentHandler
from Components.MenuList import MenuList

class HelpMenu(Screen):
	def __init__(self, session, list):
		Screen.__init__(self, session)
		self.onSelChanged = [ ]
		self["list"] = HelpMenuList(list, self.close)
		self["list"].onSelChanged.append(self.SelectionChanged)
		self["rc"] = Pixmap()
		self["arrowup"] = MovingPixmap()
		self["arrowup"].hide()
		self["sh_arrowup"] = Pixmap()
		self["sh_arrowup"].hide()
		self["long_key"] = Label("")

		self["actions"] = ActionMap(["WizardActions"], 
		{
			"ok": self["list"].ok,
			"back": self.close,
		}, -1)

	def SelectionChanged(self):
		selection = self["list"].getCurrent()
		selection = selection and selection[3]
		arrow = self["arrowup"]
		sh_arrow = self["sh_arrowup"]

		if selection and selection[0][:3] == "sh_":
			sh_arrow.show()
		else:
			sh_arrow.hide()

		if selection and selection[0][:2] == "l_":
			self["long_key"].setText(_("Long Keypress"))
		else:
			self["long_key"].setText("")

		if selection is None:
			arrow.hide()
		else:
			arrow.moveTo(selection[1], selection[2], 1)
			arrow.startMoving()
			arrow.show()

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

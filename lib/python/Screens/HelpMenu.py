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
		
		self["rc"] = Pixmap()
		self["arrowup"] = MovingPixmap()

		self["actions"] = ActionMap(["WizardActions"], 
		{
			"ok": self["list"].ok,
			"back": self.close,
			"up": self.up,
			"down": self.down
		}, -1)
	
	def up(self):
		self["list"].instance.moveSelection(self["list"].instance.moveUp)
		self.SelectionChanged()
		
	def down(self):
		self["list"].instance.moveSelection(self["list"].instance.moveDown)
		self.SelectionChanged()
		
	def SelectionChanged(self):
		selection = self["list"].getCurrent()[3]
		if selection is None:
			self["arrowup"].instance.hide()
		else:
			self["arrowup"].moveTo(selection[1], selection[2], 1)
			self["arrowup"].startMoving()
			self["arrowup"].instance.show()

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

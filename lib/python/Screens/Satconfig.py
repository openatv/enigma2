from Screen import Screen
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigList
from Components.config import *

class setupSelection:
	def __init__(self, parent):
		self.parent = parent

	def handleKey(self, key):
		if key == config.key["prevElement"]:
			self.parent.value = self.parent.value - 1
		if key == config.key["nextElement"]:
			self.parent.value = self.parent.value + 1

	def __call__(self, selected):     #needed by configlist
		print "value" + self.parent.value
		return ("text", self.parent.vals[self.parent.value])

class setupElement:
	def __init__(self, configPath, control, defaultValue, vals):
		self.configPath = configPath
		self.defaultValue = defaultValue
		self.controlType = control
		self.vals = vals
		self.notifierList = [ ]
		self.enabled = True
		self.value = self.defaultValue

class Satconfig(Screen):
	def keyLeft(self):
		if (self["config"].getCurrent()[1].parent.enabled == True):
			self["config"].handleKey(config.key["prevElement"])
	def keyRight(self):
		if (self["config"].getCurrent()[1].parent.enabled == True):
			self["config"].handleKey(config.key["nextElement"])

	def __init__(self, session):
		Screen.__init__(self, session)

		self["actions"] = ActionMap(["SetupActions"],
			{
				"cancel": self.close,
				#"ok": self.close,
				"left": self.keyLeft,
				"right": self.keyRight,
			})

		blasel = setupElement("blub", setupSelection, 1, ("A", "B"))
		item = blasel.controlType(blasel)
		list = []
		list.append( ("Tuner-Slot",item) );
		self["config"] = ConfigList(list)

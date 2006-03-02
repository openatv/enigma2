from enigma import *
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import NumberActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.GUIComponent import *

import os

class ChoiceBox(Screen):
	def __init__(self, session, title = "", **kwargs):
		Screen.__init__(self, session)

		self["text"] = Label(title)
		self["list"] = MenuList(**kwargs)
				
		self["actions"] = NumberActionMap(["WizardActions", "InputActions"], 
		{
			"ok": self.go,
			"back": self.close,
			"1": self.keyNumberGlobal,
			"2": self.keyNumberGlobal,
			"3": self.keyNumberGlobal,
			"4": self.keyNumberGlobal,
			"5": self.keyNumberGlobal,
			"6": self.keyNumberGlobal,
			"7": self.keyNumberGlobal,
			"8": self.keyNumberGlobal,
			"9": self.keyNumberGlobal,
			"0": self.keyNumberGlobal
		}, -1)
		
	def keyLeft(self):
		pass
	
	def keyRight(self):
		pass
	
	def keyNumberGlobal(self, number):
		print "pressed", number
		#self["input"].number(number)
		
	def go(self):
		self.close(self["list"].l.getCurrentSelection())
		#self.close(self["input"].getText())
		
	def cancel(self):
		self.close(None)
from enigma import *
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import NumberActionMap
from Components.Label import Label
from Components.Input import Input
from Components.GUIComponent import *

import os

class Test(Screen):
	skin = """
		<screen position="100,100" size="550,400" title="Test" >
			<widget name="text" position="0,0" size="550,25" font="Regular;20" />
		</screen>"""
		
	def __init__(self, session, args = None):
		self.skin = Test.skin
		Screen.__init__(self, session)

		self["text"] = Input("1234", maxSize=True, type=Input.NUMBER)
				
		self["actions"] = NumberActionMap(["WizardActions", "InputActions"], 
		{
			"ok": self.close,
			"back": self.close,
			"left": self.keyLeft,
			"right": self.keyRight,
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
		self["text"].left()
	
	def keyRight(self):
		self["text"].right()
	
	def keyNumberGlobal(self, number):
		print "pressed", number
		self["text"].number(number)

def getPicturePaths():
	return [ "" ]

def getPlugins():
	return [("Test", "plugin to test some capabilities", "screen", "Test")]

from enigma import *
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import NumberActionMap
from Components.Label import Label
from Components.Input import Input
from Components.GUIComponent import *

import os

class InputBox(Screen):
	def __init__(self, session, title = "", **kwargs):
		Screen.__init__(self, session)

		self["text"] = Label(title)
		self["input"] = Input(**kwargs)
				
		self["actions"] = NumberActionMap(["WizardActions", "InputBoxActions", "InputAsciiActions"], 
		{
			"gotAsciiCode": self.gotAsciiCode,
			"ok": self.go,
			"back": self.cancel,
			"left": self.keyLeft,
			"right": self.keyRight,
			"delete": self.keyDelete,
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
		rcinput = eRCInput.getInstance()
		rcinput.setKeyboardMode(rcinput.kmAscii)

	def gotAsciiCode(self):
		self["input"].handleAscii(getPrevAsciiCode())

	def keyLeft(self):
		self["input"].left()
	
	def keyRight(self):
		self["input"].right()
	
	def keyNumberGlobal(self, number):
		self["input"].number(number)
		
	def keyDelete(self):
		self["input"].delete()
		
	def go(self):
		rcinput = eRCInput.getInstance()
		rcinput.setKeyboardMode(rcinput.kmNone)
		self.close(self["input"].getText())
		
	def cancel(self):
		rcinput = eRCInput.getInstance()
		rcinput.setKeyboardMode(rcinput.kmNone)
		self.close(None)

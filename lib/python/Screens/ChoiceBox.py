from enigma import *
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import NumberActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.GUIComponent import *
from Components.ChoiceList import ChoiceEntryComponent, ChoiceList

import os

class ChoiceBox(Screen):
	def __init__(self, session, title = "", list = [], keys = None, selection = 0):
		Screen.__init__(self, session)

		self["text"] = Label(title)
		self.list = []
		if keys is None:
			self.keys = [ "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "red", "green", "yellow", "blue" ] + (len(list) - 10) * [""]
		else:
			self.keys = keys
			
		self.keymap = {}
		pos = 0
		for x in list:
			strpos = str(self.keys[pos])
			self.list.append(ChoiceEntryComponent(key = strpos, text = x))
			if self.keys[pos] != "":
				self.keymap[self.keys[pos]] = list[pos]
			pos += 1
		self["list"] = ChoiceList(list = self.list, selection = selection)
				
		self["actions"] = NumberActionMap(["WizardActions", "InputActions", "ColorActions"], 
		{
			"ok": self.go,
			"back": self.cancel,
			"1": self.keyNumberGlobal,
			"2": self.keyNumberGlobal,
			"3": self.keyNumberGlobal,
			"4": self.keyNumberGlobal,
			"5": self.keyNumberGlobal,
			"6": self.keyNumberGlobal,
			"7": self.keyNumberGlobal,
			"8": self.keyNumberGlobal,
			"9": self.keyNumberGlobal,
			"0": self.keyNumberGlobal,
			"red": self.keyRed,
			"green": self.keyGreen,
			"yellow": self.keyYellow,
			"blue": self.keyBlue
		}, -1)
		
	def keyLeft(self):
		pass
	
	def keyRight(self):
		pass
	
	def keyNumberGlobal(self, number):
		print "pressed", number
		if self.keymap.has_key(str(number)):
			self.close(self.keymap[str(number)])
		
	def go(self):
		self.close(self["list"].l.getCurrentSelection()[0])
		#self.close(self["input"].getText())

	def keyRed(self):
		if self.keymap.has_key("red"):
			self.close(self.keymap["red"])

	def keyGreen(self):
		if self.keymap.has_key("green"):
			self.close(self.keymap["green"])
	
	def keyYellow(self):
		if self.keymap.has_key("yellow"):
			self.close(self.keymap["yellow"])
			
	def keyBlue(self):
		if self.keymap.has_key("blue"):
			self.close(self.keymap["blue"])
			
	def cancel(self):
		self.close(None)
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
			self.__keys = [ "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "red", "green", "yellow", "blue" ] + (len(list) - 10) * [""]
		else:
			self.__keys = keys + (len(list) - len(keys)) * [""]
			
		self.keymap = {}
		pos = 0
		for x in list:
			strpos = str(self.__keys[pos])
			self.list.append(ChoiceEntryComponent(key = strpos, text = x))
			if self.__keys[pos] != "":
				self.keymap[self.__keys[pos]] = list[pos]
			pos += 1
		self["list"] = ChoiceList(list = self.list, selection = selection)
				
		self["actions"] = NumberActionMap(["WizardActions", "InputActions", "ColorActions", "DirectionActions"], 
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
			"blue": self.keyBlue,
			"up": self.up,
			"down": self.down
		}, -1)
		
	def keyLeft(self):
		pass
	
	def keyRight(self):
		pass
	
	def up(self):
		if len(self["list"].list) > 0:
			while 1:
				self["list"].instance.moveSelection(self["list"].instance.moveUp)
				if self["list"].l.getCurrentSelection()[0][0] != "--" or self["list"].l.getCurrentSelectionIndex() == 0:
					break
		
	def down(self):
		if len(self["list"].list) > 0:
			while 1:
				self["list"].instance.moveSelection(self["list"].instance.moveDown)
				if self["list"].l.getCurrentSelection()[0][0] != "--" or self["list"].l.getCurrentSelectionIndex() == len(self["list"].list) - 1:
					break

	def keyNumberGlobal(self, number):
		print "pressed", number
		if self.keymap.has_key(str(number)):
			self.close(self.keymap[str(number)])
		
	def go(self):
		if len(self["list"].list) > 0:
			self.close(self["list"].l.getCurrentSelection()[0])
		else:
			self.close(None)

	def keyRed(self):
		if self.keymap.has_key("red"):
			entry = self.keymap["red"]
			if len(entry) > 2 and isinstance(entry[1], str) and entry[1] == "CALLFUNC":
				entry[2](self["list"].l.getCurrentSelection()[0])
			else:
				self.close(entry)

	def keyGreen(self):
		if self.keymap.has_key("green"):
			entry = self.keymap["green"]
			print entry
			if len(entry) > 2 and isinstance(entry[1], str) and entry[1] == "CALLFUNC":
				entry[2](self["list"].l.getCurrentSelection()[0])
			else:
				self.close(entry)
	
	def keyYellow(self):
		if self.keymap.has_key("yellow"):
			entry = self.keymap["yellow"]
			if len(entry) > 2 and isinstance(entry[1], str) and entry[1] == "CALLFUNC":
				entry[2](self["list"].l.getCurrentSelection()[0])
			else:
				self.close(entry)

	def keyBlue(self):
		if self.keymap.has_key("blue"):
			entry = self.keymap["blue"]
			if len(entry) > 2 and isinstance(entry[1], str) and entry[1] == "CALLFUNC":
				entry[2](self["list"].l.getCurrentSelection()[0])
			else:
				self.close(entry)

	def cancel(self):
		self.close(None)

from enigma import *
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import NumberActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.GUIComponent import *
from Components.ChoiceList import ChoiceEntryComponent, ChoiceList

import os

class PiPSetup(Screen):
	def __init__(self, session, pip):
		Screen.__init__(self, session)
		
		self.pip = pip
		
		self.pos = (self.pip.instance.position().x(), self.pip.instance.position().y())
		self.orgpos = self.pos
		
		self.size = self.pip.getSize()
		
		self.resize = 100

		self["text"] = Label(_("Please use direction keys to move the PiP window.\nPress Bouquet +/- to resize the window.\nPress OK to go back to the TV mode or EXIT to cancel the moving."))

		self["actions"] = NumberActionMap(["PiPSetupActions", "NumberActions"], 
		{
			"ok": self.go,
			"cancel": self.cancel,
			"up": self.up,
			"down": self.down,
			"left": self.left,
			"right": self.right,
			"size+": self.bigger,
			"size-": self.smaller,
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
		
	def go(self):
		self.close()
	
	def cancel(self):
		self.movePiP(self.orgpos[0], self.orgpos[1])
		self.resizePiP(100)
		self.close()
		
	def movePiP(self, x, y):
		if x < 0:
			x = 0
		if y < 0:
			y = 0
		self.pip.move(x, y)
		self.pos = (x, y)
		
	def resizePiP(self, resize):
		w = int(self.size[0] * self.resize / 100)
		h = int(self.size[1] * self.resize / 100)
		self.pip.resize(w, h)
		self.resize = resize
	
	def up(self):
		self.movePiP(self.pos[0], self.pos[1] - 10)

	def down(self):
		self.movePiP(self.pos[0], self.pos[1] + 10)
	
	def left(self):
		self.movePiP(self.pos[0] - 10, self.pos[1])
	
	def right(self):
		self.movePiP(self.pos[0] + 10, self.pos[1])
		
	def bigger(self):
		self.resizePiP(self.resize + 5)
	
	def smaller(self):
		self.resizePiP(self.resize - 5)
		
	def keyNumberGlobal(self, number):
		size = int(240 / self.size[0] * 100)
		actions = [((self.orgpos[0], self.orgpos[1]), size),
				   ((0, 0), size),
				   ((240, 0), size),
				   ((480, 0), size),
				   ((0, 192), size),
				   ((240, 192), size),
				   ((480, 192), size),
				   ((0, 384), size),
				   ((240, 384), size),
				   ((480, 384), size)]
				   
		self.movePiP(actions[number][0][0], actions[number][0][1])
		self.resizePiP(actions[number][1])
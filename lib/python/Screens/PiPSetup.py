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
		self.orgsize = self.size

		self["text"] = Label(_("Please use direction keys to move the PiP window.\nPress Bouquet +/- to resize the window.\nPress OK to go back to the TV mode or EXIT to cancel the moving."))

		self["actions"] = NumberActionMap(["PiPSetupActions"], 
		{
			"ok": self.go,
			"cancel": self.cancel,
			"up": self.up,
			"down": self.down,
			"left": self.left,
			"right": self.right,
			"size+": self.bigger,
			"size-": self.smaller,
		}, -1)
		
	def go(self):
		self.close()
	
	def cancel(self):
		self.movePiP(self.orgpos[0], self.orgpos[1])
		self.resizePiP(self.orgsize[0], self.orgsize[1])
		self.close()
		
	def movePiP(self, x, y):
		self.pip.move(x, y)
		self.pos = (x, y)
		
	def resizePiP(self, w, h):
		self.pip.resize(w, h)
		self.size = (w, h)
	
	def up(self):
		self.movePiP(self.pos[0], self.pos[1] - 1)

	def down(self):
		self.movePiP(self.pos[0], self.pos[1] + 1)
	
	def left(self):
		self.movePiP(self.pos[0] - 1, self.pos[1])
	
	def right(self):
		self.movePiP(self.pos[0] + 1, self.pos[1])
		
	def bigger(self):
		# just for testing... TODO resize with correct aspect ratio
		self.resizePiP(self.size[0] + 1, self.size[1] + 1)
	
	def smaller(self):
		# just for testing... TODO resize with correct aspect ratio
		self.resizePiP(self.size[0] - 1, self.size[1] - 1)
from Screen import Screen
from Components.ActionMap import NumberActionMap
from Components.Label import Label
from Components.Button import Button
from Components.Pixmap import Pixmap
from Components.MenuList import MenuList
from enigma import eSize, ePoint

class MinuteInput(Screen):
		def __init__(self, session, basemins = 5):
			Screen.__init__(self, session)
						
			self["minutes"] = Label()
			self.updateValue(basemins)
			
			self["actions"] = NumberActionMap([ "NumberZapActions", "MinuteInputActions" ],
			{
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
				"up": self.up,
				"down": self.down,
				"ok": self.ok,
				"cancel": self.cancel
			})
			
		def updateValue(self, minutes):
			self.minutes = minutes
			self["minutes"].setText(str(self.minutes) + _(" mins"))
			
		def keyNumberGlobal(self, number):
			#self.updateValue(self.minutes * 10 + number)
			pass
			
		def up(self):
			self.updateValue(self.minutes + 1)
		
		def down(self):
			if self.minutes > 0:
				self.updateValue(self.minutes - 1)
				
		def ok(self):
			self.close(self.minutes)
			
		def cancel(self):
			self.close(0)
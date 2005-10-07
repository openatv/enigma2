from Screen import Screen
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigList
from Components.config import *
from Components.MenuList import MenuList
from Components.NimManager import nimmanager

class NimSetup(Screen):
	def createSimpleSetup(self, nim, list, mode):
		print "request for diseqcmode:" + str(mode)
		
		b = config.Nims[nim.slotid].diseqcA
		item = b.controlType(b)
		if mode == 0:
			list.append( ("Satellite", item) )
		else:
			list.append( ("Port A", item) )
		
		if mode >= 1:
			b = config.Nims[nim.slotid].diseqcB
			item = b.controlType(b)
			list.append( ("Port B", item) )
			if mode >= 3:
				b = config.Nims[nim.slotid].diseqcC
				item = b.controlType(b)
				list.append( ("Port C", item) )

				b = config.Nims[nim.slotid].diseqcD
				item = b.controlType(b)
				list.append( ("Port D", item) )
				
	def createSetup(self):
		print "createSetup"
		self.list = [ ]
		
		b = config.Nims[self.nim.slotid].configMode
		item = b.controlType(b)
		self.list.append( ("Configmode", item) )
		
		if b.value == 0:			#simple setup
			b = config.Nims[self.nim.slotid].diseqcMode
			item = b.controlType(b)
			self.list.append( ("Diseqcmode", item) )
		
			self.createSimpleSetup(self.nim, self.list, b.value)
		else:	
			print "FIXME: implement advanced mode"

		#???
		self["config"].list = self.list
		self["config"].l.setList(self.list)
		
	def newConfig(self):	
		if self["config"].getCurrent()[0] == "Diseqcmode":
			self.createSetup()
		if self["config"].getCurrent()[0] == "Configmode":
			self.createSetup()
		
	def keyLeft(self):
		self["config"].handleKey(config.key["prevElement"])
		self.newConfig()

	def keyRight(self):
		self["config"].handleKey(config.key["nextElement"])
		self.newConfig()

	def __init__(self, session, nim):
		Screen.__init__(self, session)
		self.nim = nim

		self["actions"] = ActionMap(["SetupActions"],
		{
			"ok": self.close,
			"cancel": self.close,
			"left": self.keyLeft,
			"right": self.keyRight
		}, -1)

		self.list = [ ]
		self["config"] = ConfigList(self.list)
		
		self.createSetup()

class NimSelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		self["nimlist"] = MenuList(nimmanager.nimList())

		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"ok": self.okbuttonClick ,
			"cancel": self.close
		}, -1)

	def okbuttonClick(self):
		selection = self["nimlist"].getCurrent()
		self.session.open(NimSetup, selection[1])
		pass

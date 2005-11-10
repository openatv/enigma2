from Screen import Screen
from Components.ActionMap import NumberActionMap
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigList
from Components.config import *
from Components.MenuList import MenuList
from Components.NimManager import nimmanager
from Components.config import getConfigListEntry

class NimSetup(Screen):
	def createSimpleSetup(self, nim, list, mode):

		if mode == 0:			#single Sat
			list.append(getConfigListEntry("Satellite", config.Nims[nim.slotid].diseqcA))
		else:							# > 1 Sats
			list.append(getConfigListEntry("Port A", config.Nims[nim.slotid].diseqcA))
		
		if mode >= 1:			# > 1 Sats
			list.append(getConfigListEntry("Port B", config.Nims[nim.slotid].diseqcB))
			if mode >= 3:		# > 2 Sats
				list.append(getConfigListEntry("Port C", config.Nims[nim.slotid].diseqcC))
				list.append(getConfigListEntry("Port D", config.Nims[nim.slotid].diseqcD))
	def createPositionerSetup(self, nim, list):
		list.append(getConfigListEntry("Longitude", config.Nims[nim.slotid].longitude))
		list.append(getConfigListEntry("Latitude", config.Nims[nim.slotid].latitude))
		pass
	
	def createSetup(self):
		self.list = [ ]
		
		self.list.append(getConfigListEntry("Configmode", config.Nims[self.nim.slotid].configMode))
		
		if config.Nims[self.nim.slotid].configMode.value == 0:			#simple setup
			self.list.append(getConfigListEntry("Diseqcmode", config.Nims[self.nim.slotid].diseqcMode))
		
			if (0 <= config.Nims[self.nim.slotid].diseqcMode.value < 4):
				self.createSimpleSetup(self.nim, self.list, config.Nims[self.nim.slotid].diseqcMode.value)
			if (config.Nims[self.nim.slotid].diseqcMode.value == 4):
				self.createPositionerSetup(self.nim, self.list)
		else:	
			print "FIXME: implement advanced mode"

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
		#forbid to enable advanced mode until its ready
		if self["config"].getCurrent()[0] != "Configmode":
			self["config"].handleKey(config.key["nextElement"])
		self.newConfig()

	def keyNumberGlobal(self, number):
		print "You pressed number " + str(number)
		if (self["config"].getCurrent()[1].parent.enabled == True):
			self["config"].handleKey(config.key[str(number)])

	def keySave(self):
		for x in self["config"].list:
			x[1].save()
		nimmanager.sec.update()	
		self.close()

	def keyCancel(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def __init__(self, session, nim):
		Screen.__init__(self, session)
		self.nim = nim

		self["actions"] = NumberActionMap(["SetupActions"],
		{
			"ok": self.keySave,
			"cancel": self.keyCancel,
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
		if selection[1].nimType != -1:	#unknown/empty
			self.session.open(NimSetup, selection[1])
	
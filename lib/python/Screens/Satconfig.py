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
			list.append(getConfigListEntry(_("Satellite"), config.Nims[nim.slotid].diseqcA))
		else:							# > 1 Sats
			list.append(getConfigListEntry(_("Port A"), config.Nims[nim.slotid].diseqcA))

		if mode >= 1:			# > 1 Sats
			list.append(getConfigListEntry(_("Port B"), config.Nims[nim.slotid].diseqcB))
			if mode >= 3:		# > 2 Sats
				list.append(getConfigListEntry(_("Port C"), config.Nims[nim.slotid].diseqcC))
				list.append(getConfigListEntry(_("Port D"), config.Nims[nim.slotid].diseqcD))
	
	def createPositionerSetup(self, nim, list):
		list.append(getConfigListEntry(_("Positioner mode"), config.Nims[nim.slotid].positionerMode))
		if (config.Nims[nim.slotid].positionerMode.value == 0): # USALS
			list.append(getConfigListEntry(_("Longitude"), config.Nims[nim.slotid].longitude))
			list.append(getConfigListEntry("", config.Nims[nim.slotid].longitudeOrientation))
			list.append(getConfigListEntry(_("Latitude"), config.Nims[nim.slotid].latitude))
			list.append(getConfigListEntry("", config.Nims[nim.slotid].latitudeOrientation))
		elif (config.Nims[nim.slotid].positionerMode.value == 1): # manual
			pass
	
	def createSetup(self):
		self.list = [ ]
		
		if (nimmanager.getNimType(self.nim.slotid) == nimmanager.nimType["DVB-S"]):
			self.configMode = getConfigListEntry(_("Configuration Mode"), config.Nims[self.nim.slotid].configMode)
			self.list.append(self.configMode)
			
			if config.Nims[self.nim.slotid].configMode.value == 0:			#simple setup
				self.diseqcModeEntry = getConfigListEntry(_("DiSEqC Mode"), config.Nims[self.nim.slotid].diseqcMode)
				self.list.append(self.diseqcModeEntry)
			
				if (0 <= config.Nims[self.nim.slotid].diseqcMode.value < 4):
					self.createSimpleSetup(self.nim, self.list, config.Nims[self.nim.slotid].diseqcMode.value)
				if (config.Nims[self.nim.slotid].diseqcMode.value == 4):
					self.createPositionerSetup(self.nim, self.list)
			elif config.Nims[self.nim.slotid].configMode.value == 1: # nothing
				#self.list.append(getConfigListEntry(_("Linked to"), config.Nims[self.nim.slotid].linkedTo))
				pass
			elif config.Nims[self.nim.slotid].configMode.value == 2: # linked
				pass
		
		elif (nimmanager.getNimType(self.nim.slotid) == nimmanager.nimType["DVB-C"]):
			self.list.append(getConfigListEntry(_("Cable provider"), config.Nims[self.nim.slotid].cable))
		elif (nimmanager.getNimType(self.nim.slotid) == nimmanager.nimType["DVB-T"]):
			self.list.append(getConfigListEntry(_("Terrestrial provider"), config.Nims[self.nim.slotid].terrestrial))


		self["config"].list = self.list
		self["config"].l.setList(self.list)
		
	def newConfig(self):	
		if self["config"].getCurrent() == self.diseqcModeEntry:
			self.createSetup()
		if self["config"].getCurrent() == self.configMode:
			self.createSetup()
		
	def keyLeft(self):
		if self["config"].getCurrent() == self.configMode:
			if self.nim.slotid == 0:
				return
		self["config"].handleKey(config.key["prevElement"])
		self.newConfig()

	def keyRight(self):
		#forbid to enable advanced mode until its ready
		#perhaps its better to use an own element here
		#this suckz .. how enable advanced config?
		if self["config"].getCurrent() == self.configMode:
			if self.nim.slotid == 0:
				return

		self["config"].handleKey(config.key["nextElement"])
		self.newConfig()

	def keyNumberGlobal(self, number):
		print "You pressed number " + str(number)
		if (self["config"].getCurrent()[1].parent.enabled == True):
			self["config"].handleKey(config.key[str(number)])

	def run(self):
		for x in self["config"].list:
			x[1].save()
		nimmanager.sec.update()	

	def keySave(self):
		self.run()
		self.close()

	def keyCancel(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def __init__(self, session, slotid):
		Screen.__init__(self, session)
		
		self.nim = nimmanager.nimList()[slotid][1]
		
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
			self.session.open(NimSetup, selection[1].slotid)
	

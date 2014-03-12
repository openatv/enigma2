from boxbranding import getMachineBrand, getMachineName

from Screens.Screen import Screen
from Screens.ServiceScan import ServiceScan
from Screens.MessageBox import MessageBox

from Components.Label import Label
from Components.ActionMap import ActionMap
from Components.MenuList import MenuList 
from Components.config import config, ConfigBoolean, configfile
from Components.ConfigList import ConfigListScreen
from Components.Sources.StaticText import StaticText
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Components.NimManager import nimmanager, getConfigSatlist, InitNimManager

from enigma import eListboxPythonMultiContent, gFont, RT_HALIGN_CENTER, RT_HALIGN_LEFT, RT_VALIGN_CENTER, RT_WRAP, eComponentScan, eDVBFrontendParametersTerrestrial

config.misc.inifirstrun = ConfigBoolean(default = True)

class TerrestrialMenuList(MenuList):
	def __init__(self, list, enableWrapAround=True):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		self.l.setFont(0, gFont("Regular", 28))
		self.l.setFont(1, gFont("Regular", 14))
		self.l.setItemHeight(50)
	
def TerrestrialMenuEntryComponent(name, item):
	return [
		(item),
		MultiContentEntryText(pos=(20, 8), size=(400, 50), font=0, text = _(name)),
	]

def buildTerTransponder(frequency,
		inversion=2, bandwidth = 7000000, fechigh = 6, feclow = 6,
		modulation = 2, transmission = 2, guard = 4,
		hierarchy = 4, system = 0, plpid = 0):
#	print "freq", frequency, "inv", inversion, "bw", bandwidth, "fech", fechigh, "fecl", feclow, "mod", modulation, "tm", transmission, "guard", guard, "hierarchy", hierarchy
	parm = eDVBFrontendParametersTerrestrial()
	parm.frequency = frequency
	parm.inversion = inversion
	parm.bandwidth = bandwidth
	parm.code_rate_HP = fechigh
	parm.code_rate_LP = feclow
	parm.modulation = modulation
	parm.transmission_mode = transmission
	parm.guard_interval = guard
	parm.hierarchy = hierarchy
	parm.system = system
	parm.plpid = plpid
	return parm
      
def getInitialTerrestrialTransponderList(tlist, region):
	list = nimmanager.getTranspondersTerrestrial(region)

	for x in list:
		if x[0] == 2: #TERRESTRIAL
			parm = buildTerTransponder(x[1], x[9], x[2], x[4], x[5], x[3], x[7], x[6], x[8], x[10], x[11])
			tlist.append(parm)
			
class IniTerrestrialLocation(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Terrestrial Location Settings"))
		
		InitNimManager(nimmanager)
		
		if config.misc.inifirstrun.getValue():
			self.skinName = ["StartWizard"]

		self["text"] = Label(_("Please scroll to location and select your location and then press ok. If your location is not listed or you do not find all the channels please select Australia as your location."))
		self["key_red"] = Label(_("Exit"))
		self.mlist = []
		self["config"] = TerrestrialMenuList(self.mlist)
		
		self["actions"] = ActionMap(["SetupActions"],
		{
			"red": self.close,
			"ok": self.go,
			"save": self.go,
			"cancel": self.close,
			"back": self.close,
		}, -2)
		
		self.onLayoutFinish.append(self.createSetup)
		
	def createSetup(self):    
		n = 0
		self.mlist = []
		for x in nimmanager.terrestrialsList:
			self.mlist.append(TerrestrialMenuEntryComponent((x[0]), str(n)))
			n += 1
			
		self["config"].setList(self.mlist)
		
		self.nim0 = nimmanager.nim_slots[0]
		self.nimConfig0 = self.nim0.config
		index = self.nimConfig0.terrestrial.getValue()
		self["config"].moveToIndex(int(index))

	def saveTunerSetting(self):
		item = self["config"].getCurrent()
		
		self.nim0 = nimmanager.nim_slots[0]
		self.nimConfig0 = self.nim0.config
		self.nimConfig0.terrestrial.setValue(str(item[0]))
		self.nimConfig0.terrestrial.save()

		self.nim1 = nimmanager.nim_slots[1]
		self.nimConfig1 = self.nim1.config
		self.nimConfig1.terrestrial.setValue(str(item[0]))
		self.nimConfig1.terrestrial.save()
		
		self.nim2 = nimmanager.nim_slots[2]
		self.nimConfig2 = self.nim2.config
		self.nimConfig2.terrestrial.setValue(str(item[0]))
		self.nimConfig2.terrestrial.save()
	    
	def getNetworksForNim(self, nim):
		if nim.isCompatible("DVB-S"):
			networks = nimmanager.getSatListForNim(nim.slot)
		elif not nim.empty:
			networks = [ nim.type ] # "DVB-C" or "DVB-T". TODO: seperate networks for different C/T tuners, if we want to support that.
		else:
			# empty tuners provide no networks.
			networks = [ ]
		return networks
		  
	def go(self):
		self.saveTunerSetting()
		
		APPEND_NOW = 0
		SEARCH_CABLE_TRANSPONDERS = 1
		action = APPEND_NOW

		self.scanList = []
		self.known_networks = set()
		self.nim_iter=0
			
		flags = 0
		nim = nimmanager.nim_slots[0]
		networks = set(self.getNetworksForNim(nim))
		networkid = 0

		# don't scan anything twice
		networks.discard(self.known_networks)

		tlist = [ ]
		getInitialTerrestrialTransponderList(tlist, nimmanager.getTerrestrialDescription(nim.slot))

		flags |= eComponentScan.scanNetworkSearch #FIXMEEE.. use flags from cables / satellites / terrestrial.xml
		#tmp = self.scan_clearallservices.getValue()
		tmp = "no"
		if tmp == "yes":
			flags |= eComponentScan.scanRemoveServices
		elif tmp == "yes_hold_feeds":
			flags |= eComponentScan.scanRemoveServices
			flags |= eComponentScan.scanDontRemoveFeeds

		if action == APPEND_NOW:
			self.scanList.append({"transponders": tlist, "feid": nim.slot, "flags": flags})

		self.startScan(self.scanList)

	def startScan(self, scanList):
		if len(scanList):
			self.session.openWithCallback(self.exit, ServiceScan, scanList = scanList)
		else:
			self.session.open(MessageBox, _("Nothing to scan!\nPlease setup your location before you start a service scan."), MessageBox.TYPE_ERROR)

	def exit(self):
		self.close()

class IniEndWizard(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Congratulations!"))
		
		self.skinName = ["StartWizard"]

		self["text"] = Label(_("Congratulations, your %s %s is now set up.\nPlease press OK to start using your %s %s.") % (getMachineBrand(), getMachineName(), getMachineBrand(), getMachineName()) )

		self["actions"] = ActionMap(["SetupActions"],
		{
			"ok": self.go,
			"save": self.go
		}, -2)

	def saveIniWizardSetting(self):
		config.misc.inifirstrun.value = 0
		config.misc.inifirstrun.save()
		configfile.save()
		
	def go(self):
		self.saveIniWizardSetting()
		self.close()
		
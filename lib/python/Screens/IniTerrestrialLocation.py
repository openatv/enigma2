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
from Components.NimManager import nimmanager, InitNimManager

from enigma import eListboxPythonMultiContent, gFont, RT_HALIGN_CENTER, RT_HALIGN_LEFT, RT_VALIGN_CENTER, RT_WRAP, eComponentScan, eDVBFrontendParametersTerrestrial

config.misc.inifirstrun = ConfigBoolean(default=True)

class TerrestrialMenuList(MenuList):
	def __init__(self, list, enableWrapAround=True):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		self.l.setFont(0, gFont("Regular", 24))
		self.l.setFont(1, gFont("Regular", 14))
		self.l.setItemHeight(32)

def TerrestrialMenuEntryComponent(name, item):
	return [
		(item),
		MultiContentEntryText(pos=(20, 4), size=(400, 32), font=0, text = _(name)),
	]

def buildTerTransponder(
					frequency, inversion=2, bandwidth=7000000,
					fechigh=6, feclow=6, modulation=2, transmission=2,
					guard=4, hierarchy=4, system=0, plpid=0):
	# print "freq", frequency, "inv", inversion, "bw", bandwidth, "fech", fechigh, "fecl", feclow, "mod", modulation, "tm", transmission, "guard", guard, "hierarchy", hierarchy
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
		if x[0] == 2:  # TERRESTRIAL
			parm = buildTerTransponder(x[1], x[9], x[2], x[4], x[5], x[3], x[7], x[6], x[8], x[10], x[11])
			tlist.append(parm)

class IniTerrestrialLocation(Screen):
	skin = """
	<screen name="IniTerrestrialLocation" position="center,center" size="560,550">
		<ePixmap pixmap="buttons/red.png" position="0,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="buttons/blue.png" position="420,0" size="140,40" alphatest="on" />
		<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		<widget source="key_blue" render="Label" position="420,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#2222bb" transparent="1" />
		<widget name="config" position="0,90" size="560,384" transparent="0" enableWrapAround="1" scrollbarMode="showOnDemand" />
		<widget name="text" position="0,e-75" size="560,75" font="Regular;18" halign="center" valign="top" transparent="0" zPosition="1" />
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Terrestrial Location Settings"))

		InitNimManager(nimmanager)

		if config.misc.inifirstrun.getValue():
			self.skinName = ["IniTerrestrialLocationWizard"]

		self["text"] = Label(_("Please select your location and then press OK to begin the scan.\n\nIf your location is not listed or the scan fails to find all channels, please select Full Scan."))
		self["key_red"] = Label(_("Exit"))
		self["key_blue"] = Label(_("Set location"))
		self.mlist = []
		self["config"] = TerrestrialMenuList(self.mlist)

		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"red": self.close,
			"blue": self.setLocation,
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

		for nim in nimmanager.nim_slots:
			if nim.isCompatible("DVB-T"):
				nimConfig = nim.config
				index = nimConfig.terrestrial.getValue()
				self["config"].moveToIndex(int(index))
				break

	def saveTunerSetting(self):
		item = self["config"].getCurrent()
		for nim in nimmanager.nim_slots:
			if nim.isCompatible("DVB-T"):
				nimConfig = nim.config
				nimConfig.terrestrial.setValue(str(item[0]))
				nimConfig.terrestrial.save()

	def getNetworksForNim(self, nim):
		if nim.isCompatible("DVB-S"):
			networks = nimmanager.getSatListForNim(nim.slot)
		elif not nim.empty:
			networks = [nim.type]  # "DVB-C" or "DVB-T". TODO: separate networks for different C/T tuners, if we want to support that.
		else:
			# empty tuners provide no networks.
			networks = []
		return networks

	def setLocation(self):
		self.saveTunerSetting()
		self.close()

	def go(self):
		self.saveTunerSetting()

		APPEND_NOW = 0
		SEARCH_CABLE_TRANSPONDERS = 1
		action = APPEND_NOW

		self.scanList = []
		self.known_networks = set()
		self.nim_iter = 0

		flags = 0
		for nim in nimmanager.nim_slots:
			if nim.isCompatible("DVB-T"):
				break
		networks = set(self.getNetworksForNim(nim))
		networkid = 0

		# don't scan anything twice
		networks.discard(self.known_networks)

		tlist = []
		getInitialTerrestrialTransponderList(tlist, nimmanager.getTerrestrialDescription(nim.slot))

		flags |= eComponentScan.scanNetworkSearch  # FIXMEEE.. use flags from cables / satellites / terrestrial.xml
		# tmp = self.scan_clearallservices.getValue()
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
			self.session.openWithCallback(self.exit, ServiceScan, scanList=scanList)
		else:
			self.session.open(MessageBox, _("Nothing to scan!\nPlease setup your location before you start a service scan."), MessageBox.TYPE_ERROR)

	def exit(self, *retval):
		self.close()

class IniEndWizard(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Congratulations!"))

		self["text"] = Label(_(
							"Congratulations, your %s %s is now set up.\n"
							"Please press OK to start using your %s %s.") % (getMachineBrand(), getMachineName(), getMachineBrand(), getMachineName()))

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

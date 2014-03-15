from boxbranding import getMachineBrand, getMachineName, getBoxType
from os import system

from enigma import eTimer

from Screens.WizardLanguage import WizardLanguage
from Screens.Rc import Rc
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Components.Pixmap import Pixmap
from Components.Sources.Boolean import Boolean
from Components.Network import iNetwork
from Tools.Directories import resolveFilename, SCOPE_PLUGINS

class NetworkWizard(WizardLanguage, Rc):
	skin = """
		<screen position="0,0" size="720,576" title="Welcome..." flags="wfNoBorder" >
			<widget name="text" position="153,40" size="340,300" font="Regular;22" />
			<widget source="list" render="Listbox" position="53,340" size="440,180" scrollbarMode="showOnDemand" >
				<convert type="StringList" />
			</widget>
			<widget name="config" position="53,340" zPosition="1" size="440,180" transparent="1" scrollbarMode="showOnDemand" />
			<ePixmap pixmap="buttons/button_red.png" position="40,225" zPosition="0" size="15,16" transparent="1" alphatest="on" />
			<widget name="languagetext" position="55,225" size="95,30" font="Regular;18" />
			<widget name="wizard" pixmap="/wizard.png" position="40,50" zPosition="10" size="110,174" alphatest="on" />
			<widget name="rc" pixmaps="rc.png,rcold.png" position="500,50" zPosition="10" size="154,500" alphatest="on" />
			<widget name="arrowdown" pixmap="arrowdown.png" position="-100,-100" zPosition="11" size="37,70" alphatest="on" />
			<widget name="arrowdown2" pixmap="arrowdown.png" position="-100,-100" zPosition="11" size="37,70" alphatest="on" />
			<widget name="arrowup" pixmap="arrowup.png" position="-100,-100" zPosition="11" size="37,70" alphatest="on" />
			<widget name="arrowup2" pixmap="arrowup.png" position="-100,-100" zPosition="11" size="37,70" alphatest="on" />
			<widget source="VKeyIcon" render="Pixmap" pixmap="buttons/key_text.png" position="40,260" zPosition="0" size="35,25" transparent="1" alphatest="on" >
				<convert type="ConditionalShowHide" />
			</widget>
			<widget name="HelpWindow" pixmap="buttons/key_text.png" position="125,170" zPosition="1" size="1,1" transparent="1" alphatest="on" />
		</screen>"""
	def __init__(self, session, interface = None):
		self.xmlfile = resolveFilename(SCOPE_PLUGINS, "SystemPlugins/NetworkWizard/networkwizard.xml")
		WizardLanguage.__init__(self, session, showSteps = False, showStepSlider = False)
		Rc.__init__(self)
		Screen.setTitle(self, _("NetworkWizard"))
		self.session = session
		self["wizard"] = Pixmap()
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["VKeyIcon"] = Boolean(False)

		self.InstalledInterfaceCount = None
		self.Adapterlist = None
		self.InterfaceState = None
		self.isInterfaceUp = None
		self.WlanPluginInstalled = False
		self.ap = None
		self.w = None
		if interface is not None:
			self.selectedInterface = interface
		else:
			self.selectedInterface = None
		self.NextStep = None
		self.resetRef = None
		self.checkRef = None
		self.AdapterRef = None
		self.APList = None
		self.newAPlist = None
		self.oldlist = None

		self.originalInterfaceState = {}
		self.originalInterfaceStateChanged = False
		self.Text = None
		self.rescanTimer = eTimer()
		self.rescanTimer.callback.append(self.rescanTimerFired)
		self.getInstalledInterfaceCount()
		self.isWlanPluginInstalled()

	def exitWizardQuestion(self, ret = False):
		if ret:
			self.markDone()
			self.close()

	def markDone(self):
		self.stopScan()
		del self.rescanTimer
		self.checkOldInterfaceState()
		self.exit()
		pass

	def back(self):
		self.stopScan()
		self.ap = None
		WizardLanguage.back(self)

	def stopScan(self):
		self.rescanTimer.stop()
		if self.w is not None:
			from Plugins.SystemPlugins.WirelessLan.Wlan import iWlan
			iWlan.stopGetNetworkList()
			self.w = None

	def getInstalledInterfaceCount(self):
		self.originalInterfaceState = {}
		self.Adapterlist = iNetwork.getAdapterList()
		self.InstalledInterfaceCount = len(self.Adapterlist)
		if self.Adapterlist is not None:
			if self.InstalledInterfaceCount == 1 and self.selectedInterface is None:
					self.selectedInterface = self.Adapterlist[0]
		for interface in iNetwork.getAdapterList():
			self.originalInterfaceState[interface] = {}
			self.originalInterfaceState[interface]["up"] = iNetwork.getAdapterAttribute(interface, 'up')

	def selectInterface(self):
		self.InterfaceState = None
		if self.selectedInterface is None:
			if self.InstalledInterfaceCount <= 1:
				if not iNetwork.isWirelessInterface(self.selectedInterface):
					self.NextStep = 'nwconfig'
				else:
					self.NextStep = 'asknetworktype'
				self.checkInterface(self.selectedInterface)
			else:
				self.NextStep = 'selectinterface'
				self.currStep = self.getStepWithID(self.NextStep)
				self.afterAsyncCode()
		else:
			if not iNetwork.isWirelessInterface(self.selectedInterface):
				self.NextStep = 'nwconfig'
			else:
				self.NextStep = 'asknetworktype'
			self.checkInterface(self.selectedInterface)

	def checkOldInterfaceState(self):
		# disable up interface if it was originally down and config is unchanged.
		if self.originalInterfaceStateChanged is False:
			for interface in self.originalInterfaceState.keys():
				if interface == self.selectedInterface:
					if self.originalInterfaceState[interface]["up"] is False:
						if iNetwork.checkforInterface(interface) is True:
							system("ifconfig " + interface + " down")

	def listInterfaces(self):
		self.checkOldInterfaceState()
		list = [(iNetwork.getFriendlyAdapterName(x),x) for x in iNetwork.getAdapterList()]
		list.append((_("Exit network wizard"), "end"))
		return list

	def InterfaceSelectionMade(self, index):
		self.selectedInterface = index
		self.InterfaceSelect(index)

	def InterfaceSelect(self, index):
		if index == 'end':
			self.NextStep = 'end'
		elif index == 'eth0':
			self.NextStep = 'nwconfig'
		elif index == 'eth1' and getBoxType() == "et10000":
			self.NextStep = 'nwconfig'
		else:
			self.NextStep = 'asknetworktype'

	def InterfaceSelectionMoved(self):
		self.InterfaceSelect(self.selection)

	def checkInterface(self,iface):
		self.stopScan()
		if self.Adapterlist is None:
			self.Adapterlist = iNetwork.getAdapterList()
		if self.NextStep is not 'end':
			if len(self.Adapterlist) == 0:
				#Reset Network to defaults if network broken
				iNetwork.resetNetworkConfig('lan', self.resetNetworkConfigCB)
				self.resetRef = self.session.openWithCallback(self.resetNetworkConfigFinished, MessageBox, _("Please wait while we prepare your network interfaces..."), type = MessageBox.TYPE_INFO, enable_input = False)
			if iface in iNetwork.getInstalledAdapters():
				if iface in iNetwork.configuredNetworkAdapters and len(iNetwork.configuredNetworkAdapters) == 1:
					if iNetwork.getAdapterAttribute(iface, 'up') is True:
						self.isInterfaceUp = True
					else:
						self.isInterfaceUp = False
					self.currStep = self.getStepWithID(self.NextStep)
					self.afterAsyncCode()
				else:
					self.isInterfaceUp = iNetwork.checkforInterface(iface)
					self.currStep = self.getStepWithID(self.NextStep)
					self.afterAsyncCode()
		else:
			self.resetNetworkConfigFinished(False)

	def resetNetworkConfigFinished(self,data):
		if data is True:
			self.currStep = self.getStepWithID(self.NextStep)
			self.afterAsyncCode()
		else:
			self.currStep = self.getStepWithID(self.NextStep)
			self.afterAsyncCode()

	def resetNetworkConfigCB(self,callback,iface):
		if callback is not None:
			if callback is True:
				iNetwork.getInterfaces(self.getInterfacesFinished)

	def getInterfacesFinished(self, data):
		if data is True:
			if iNetwork.getAdapterAttribute(self.selectedInterface, 'up') is True:
				self.isInterfaceUp = True
			else:
				self.isInterfaceUp = False
			self.resetRef.close(True)
		else:
			print "we should never come here!"

	def AdapterSetupEnd(self, iface):
		self.originalInterfaceStateChanged = True
		if iNetwork.getAdapterAttribute(iface, "dhcp") is True:
			iNetwork.checkNetworkState(self.AdapterSetupEndFinished)
			self.AdapterRef = self.session.openWithCallback(self.AdapterSetupEndCB, MessageBox, _("Please wait while we test your network..."), type = MessageBox.TYPE_INFO, enable_input = False)
		else:
			self.currStep = self.getStepWithID("confdns")
			self.afterAsyncCode()

	def AdapterSetupEndCB(self,data):
		if data is True:
			if iNetwork.isWirelessInterface(self.selectedInterface):
				if self.WlanPluginInstalled:
					from Plugins.SystemPlugins.WirelessLan.Wlan import iStatus
					iStatus.getDataForInterface(self.selectedInterface,self.checkWlanStateCB)
				else:
					self.currStep = self.getStepWithID("checklanstatusend")
					self.afterAsyncCode()
			else:
				self.currStep = self.getStepWithID("checklanstatusend")
				self.afterAsyncCode()

	def AdapterSetupEndFinished(self,data):
		if data <= 2:
			self.InterfaceState = True
		else:
			self.InterfaceState = False
		self.AdapterRef.close(True)

	def checkWlanStateCB(self,data,status):
		if data is not None:
			if data is True:
				if status is not None:
					text1 = _("Your %s %s is now ready to be used.\n\nYour internet connection is working now.\n\n") % (getMachineBrand(), getMachineName())
					text2 = _('Accesspoint:') + "\t" + str(status[self.selectedInterface]["accesspoint"]) + "\n"
					text3 = _('SSID:') + "\t" + str(status[self.selectedInterface]["essid"]) + "\n"
					text4 = _('Link quality:') + "\t" + str(status[self.selectedInterface]["quality"])+ "\n"
					text5 = _('Signal strength:') + "\t" + str(status[self.selectedInterface]["signal"]) + "\n"
					text6 = _('Bitrate:') + "\t" + str(status[self.selectedInterface]["bitrate"]) + "\n"
					text7 = _('Encryption:') + " " + str(status[self.selectedInterface]["encryption"]) + "\n"
					text8 = _("Please press OK to continue.")
					infotext = text1 + text2 + text3 + text4 + text5 + text7 +"\n" + text8
					self.currStep = self.getStepWithID("checkWlanstatusend")
					self.Text = infotext
					if str(status[self.selectedInterface]["accesspoint"]) == "Not-Associated":
						self.InterfaceState = False
					self.afterAsyncCode()

	def checkNetwork(self):
		iNetwork.checkNetworkState(self.checkNetworkStateCB)
		self.checkRef = self.session.openWithCallback(self.checkNetworkCB, MessageBox, _("Please wait while we test your network..."), type = MessageBox.TYPE_INFO, enable_input = False)

	def checkNetworkCB(self,data):
		if data is True:
			if iNetwork.isWirelessInterface(self.selectedInterface):
				if self.WlanPluginInstalled:
					from Plugins.SystemPlugins.WirelessLan.Wlan import iStatus
					iStatus.getDataForInterface(self.selectedInterface,self.checkWlanStateCB)
				else:
					self.currStep = self.getStepWithID("checklanstatusend")
					self.afterAsyncCode()
			else:
				self.currStep = self.getStepWithID("checklanstatusend")
				self.afterAsyncCode()

	def checkNetworkStateCB(self,data):
		if data <= 2:
			self.InterfaceState = True
		else:
			self.InterfaceState = False
		self.checkRef.close(True)

	def rescanTimerFired(self):
		self.rescanTimer.stop()
		self.updateAPList()

	def updateAPList(self):
		self.oldlist = self.APList
		self.newAPlist = []
		newList = []
		newListIndex = None
		currentListEntry = None
		newList = self.listAccessPoints()

		for oldentry in self.oldlist:
			if oldentry not in newList:
				newList.append(oldentry)

		for newentry in newList:
			self.newAPlist.append(newentry)

		if len(self.newAPlist):
			if self.wizard[self.currStep].has_key("dynamiclist"):
				currentListEntry = self["list"].getCurrent()
				if currentListEntry is not None:
					idx = 0
					for entry in self.newAPlist:
						if entry == currentListEntry:
							newListIndex = idx
						idx +=1
				self.wizard[self.currStep]["evaluatedlist"] = self.newAPlist
				self['list'].setList(self.newAPlist)
				if newListIndex is not None:
					self["list"].setIndex(newListIndex)
				self["list"].updateList(self.newAPlist)

	def listAccessPoints(self):
		self.APList = []
		if self.WlanPluginInstalled is False:
			self.APList.append( ( _("No networks found"), None ) )
		else:
			from Plugins.SystemPlugins.WirelessLan.Wlan import iWlan
			iWlan.setInterface(self.selectedInterface)
			self.w = iWlan.getInterface()
			aps = iWlan.getNetworkList()
			if aps is not None:
				print "[NetworkWizard.py] got Accespoints!"
				tmplist = []
				complist = []
				for ap in aps:
					a = aps[ap]
					if a['active']:
						tmplist.append( (a['bssid'], a['essid']) )
						complist.append( (a['bssid'], a['essid']) )

				for entry in tmplist:
					if entry[1] == "":
						for compentry in complist:
							if compentry[0] == entry[0]:
								complist.remove(compentry)
				for entry in complist:
					self.APList.append( (entry[1], entry[1]) )
			if not len(aps):
				self.APList.append( ( _("No networks found"), None ) )

		self.rescanTimer.start(4000)
		return self.APList


	def AccessPointsSelectionMoved(self):
		self.ap = self.selection
		self.NextStep = 'wlanconfig'

	def checkWlanSelection(self):
		self.stopScan()
		self.currStep = self.getStepWithID(self.NextStep)

	def isWlanPluginInstalled(self):
		try:
			from Plugins.SystemPlugins.WirelessLan.Wlan import iWlan
		except ImportError:
			self.WlanPluginInstalled = False
		else:
			self.WlanPluginInstalled = True

	def listChoices(self):
		self.stopScan()
		list = []
		if self.WlanPluginInstalled:
			list.append((_("Configure your wireless LAN again"), "scanwlan"))
		list.append((_("Configure your internal LAN"), "nwconfig"))
		list.append((_("Exit network wizard"), "end"))
		return list

	def ChoicesSelectionMade(self, index):
		self.ChoicesSelect(index)

	def ChoicesSelect(self, index):
		if index == 'end':
			self.NextStep = 'end'
		elif index == 'nwconfig':
			self.selectedInterface = "eth0"
			self.NextStep = 'nwconfig'
		else:
			self.NextStep = 'asknetworktype'

	def ChoicesSelectionMoved(self):
		pass

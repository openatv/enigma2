from Screens.Wizard import wizardManager, WizardSummary
from Screens.WizardLanguage import WizardLanguage
from Screens.Rc import Rc
from Screens.MessageBox import MessageBox
from Components.Pixmap import Pixmap, MovingPixmap, MultiPixmap
from Components.Sources.Boolean import Boolean
from Components.config import config, ConfigBoolean, configfile, ConfigYesNo, NoSave, ConfigSubsection, ConfigText, getConfigListEntry, ConfigSelection, ConfigPassword
from Components.Network import iNetwork
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_SKIN_IMAGE
from enigma import eTimer

config.misc.firstrun = ConfigBoolean(default = True)
list = []
list.append("WEP")
list.append("WPA")
list.append("WPA2")
list.append("WPA/WPA2")

weplist = []
weplist.append("ASCII")
weplist.append("HEX")

config.plugins.wlan = ConfigSubsection()
config.plugins.wlan.essid = NoSave(ConfigText(default = "home", fixed_size = False))
config.plugins.wlan.hiddenessid = NoSave(ConfigText(default = "home", fixed_size = False))

config.plugins.wlan.encryption = ConfigSubsection()
config.plugins.wlan.encryption.enabled = NoSave(ConfigYesNo(default = False))
config.plugins.wlan.encryption.type = NoSave(ConfigSelection(list, default = "WPA/WPA2" ))
config.plugins.wlan.encryption.wepkeytype = NoSave(ConfigSelection(weplist, default = "ASCII"))
config.plugins.wlan.encryption.psk = NoSave(ConfigPassword(default = "mysecurewlan", fixed_size = False))

class NetworkWizard(WizardLanguage, Rc):
	skin = """
		<screen position="0,0" size="720,576" title="Welcome..." flags="wfNoBorder" >
			<widget name="text" position="153,40" size="340,300" font="Regular;22" />
			<widget source="list" render="Listbox" position="53,340" size="440,180" scrollbarMode="showOnDemand" >
				<convert type="StringList" />
			</widget>
			<widget name="config" position="53,340" zPosition="1" size="440,180" transparent="1" scrollbarMode="showOnDemand" />
			<ePixmap pixmap="skin_default/buttons/button_red.png" position="40,225" zPosition="0" size="15,16" transparent="1" alphatest="on" />
			<widget name="languagetext" position="55,225" size="95,30" font="Regular;18" />
			<widget name="wizard" pixmap="skin_default/wizard.png" position="40,50" zPosition="10" size="110,174" alphatest="on" />
			<widget name="rc" pixmaps="skin_default/rc.png,skin_default/rcold.png" position="500,50" zPosition="10" size="154,500" alphatest="on" />
			<widget name="arrowdown" pixmap="skin_default/arrowdown.png" position="-100,-100" zPosition="11" size="37,70" alphatest="on" />
			<widget name="arrowdown2" pixmap="skin_default/arrowdown.png" position="-100,-100" zPosition="11" size="37,70" alphatest="on" />
			<widget name="arrowup" pixmap="skin_default/arrowup.png" position="-100,-100" zPosition="11" size="37,70" alphatest="on" />
			<widget name="arrowup2" pixmap="skin_default/arrowup.png" position="-100,-100" zPosition="11" size="37,70" alphatest="on" />
			<widget source="VKeyIcon" render="Pixmap" pixmap="skin_default/buttons/key_text.png" position="40,260" zPosition="0" size="35,25" transparent="1" alphatest="on" >
				<convert type="ConditionalShowHide" />
			</widget>
			<widget name="HelpWindow" pixmap="skin_default/buttons/key_text.png" position="125,170" zPosition="1" size="1,1" transparent="1" alphatest="on" />	
		</screen>"""
	def __init__(self, session, interface = None):
		self.xmlfile = resolveFilename(SCOPE_PLUGINS, "SystemPlugins/NetworkWizard/networkwizard.xml")
		WizardLanguage.__init__(self, session, showSteps = False, showStepSlider = False)
		Rc.__init__(self)
		self.session = session
		self["wizard"] = Pixmap()
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["VKeyIcon"] = Boolean(False)

		self.InstalledInterfaceCount = None
		self.Adapterlist = None
		self.InterfaceState = None
		self.isInterfaceUp = None
		self.WlanPluginInstalled = None
		self.ap = None
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
		self.WlanList = None
		self.oldlist = None
		self.originalAth0State = None
		self.originalEth0State = None
		self.originalWlan0State = None
		self.originalInterfaceStateChanged = False
		self.Text = None
		self.rescanTimer = eTimer()
		self.rescanTimer.callback.append(self.rescanTimerFired)
		self.getInstalledInterfaceCount()
		self.isWlanPluginInstalled()
		
	def exitWizardQuestion(self, ret = False):
		if (ret):
			self.markDone()
			self.close()
		
	def markDone(self):
		self.rescanTimer.stop()
		del self.rescanTimer
		self.checkOldInterfaceState()
		pass

	def getInstalledInterfaceCount(self):
		self.rescanTimer.stop()
		self.Adapterlist = iNetwork.getAdapterList()
		self.InstalledInterfaceCount = len(self.Adapterlist)
		if self.Adapterlist is not None:
			if self.InstalledInterfaceCount == 1 and self.selectedInterface is None:
					self.selectedInterface = self.Adapterlist[0]
		self.originalAth0State = iNetwork.getAdapterAttribute('ath0', 'up')
		self.originalEth0State = iNetwork.getAdapterAttribute('eth0', 'up')
		self.originalWlan0State = iNetwork.getAdapterAttribute('wlan0', 'up')

	def selectInterface(self):
		self.InterfaceState = None
		if self.selectedInterface is None and self.InstalledInterfaceCount <= 1:
			if self.selectedInterface == 'eth0':
				self.NextStep = 'nwconfig'
			else:
				self.NextStep = 'scanwlan'
			self.checkInterface(self.selectedInterface)
		elif self.selectedInterface is not None and self.InstalledInterfaceCount <= 1:
			if self.selectedInterface == 'eth0':
				self.NextStep = 'nwconfig'
			else:
				self.NextStep = 'scanwlan'
			self.checkInterface(self.selectedInterface)
		elif self.selectedInterface is None and self.InstalledInterfaceCount > 1:
			self.NextStep = 'selectinterface'
			self.currStep = self.getStepWithID(self.NextStep)
			self.afterAsyncCode()
		elif self.selectedInterface is not None and self.InstalledInterfaceCount > 1:
			if self.selectedInterface == 'eth0':
				self.NextStep = 'nwconfig'
			else:
				self.NextStep = 'scanwlan'
			self.checkInterface(self.selectedInterface)
		else:
			self.NextStep = 'selectinterface'
			self.currStep = self.getStepWithID(self.NextStep)
			self.afterAsyncCode()			

	def checkOldInterfaceState(self):
		# disable up interface if it was originally down and config is unchanged.
		if self.originalAth0State is False and self.originalInterfaceStateChanged is False:
			if iNetwork.checkforInterface('ath0') is True:
				iNetwork.deactivateInterface('ath0')		
		if self.originalEth0State is False and self.originalInterfaceStateChanged is False:
			if iNetwork.checkforInterface('eth0') is True:
				iNetwork.deactivateInterface('eth0')
		if self.originalWlan0State is False and self.originalInterfaceStateChanged is False:
			if iNetwork.checkforInterface('wlan0') is True:
				iNetwork.deactivateInterface('wlan0')

	def listInterfaces(self):
		self.rescanTimer.stop()
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
		else:
			self.NextStep = 'scanwlan'

	def InterfaceSelectionMoved(self):
		self.InterfaceSelect(self.selection)
		
	def checkInterface(self,iface):
		self.rescanTimer.stop()
		if self.Adapterlist is None:
			self.Adapterlist = iNetwork.getAdapterList()
		if self.NextStep is not 'end':
			if len(self.Adapterlist) == 0:
				#Reset Network to defaults if network broken
				iNetwork.resetNetworkConfig('lan', self.resetNetworkConfigCB)
				self.resetRef = self.session.openWithCallback(self.resetNetworkConfigFinished, MessageBox, _("Please wait while we prepare your network interfaces..."), type = MessageBox.TYPE_INFO, enable_input = False)
			if iface in ('eth0', 'wlan0', 'ath0'):
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
			if self.selectedInterface in ('wlan0', 'ath0'):
				if self.WlanPluginInstalled == True:
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
					text1 = _("Your Dreambox is now ready to use.\n\nYour internet connection is working now.\n\n")
					text2 = _('Accesspoint:') + "\t" + str(status[self.selectedInterface]["acesspoint"]) + "\n"
					text3 = _('SSID:') + "\t" + str(status[self.selectedInterface]["essid"]) + "\n"
					text4 = _('Link Quality:') + "\t" + str(status[self.selectedInterface]["quality"])+ "\n"
					text5 = _('Signal Strength:') + "\t" + str(status[self.selectedInterface]["signal"]) + "\n"
					text6 = _('Bitrate:') + "\t" + str(status[self.selectedInterface]["bitrate"]) + "\n"
					text7 = _('Encryption:') + " " + str(status[self.selectedInterface]["encryption"]) + "\n"
					text8 = _("Please press OK to continue.")
					infotext = text1 + text2 + text3 + text4 + text5 + text7 +"\n" + text8
					self.currStep = self.getStepWithID("checkWlanstatusend")
					self.Text = infotext
					if str(status[self.selectedInterface]["acesspoint"]) == "Not-Associated":
						self.InterfaceState = False
					self.afterAsyncCode()

	def checkNetwork(self):
		iNetwork.checkNetworkState(self.checkNetworkStateCB)
		self.checkRef = self.session.openWithCallback(self.checkNetworkCB, MessageBox, _("Please wait while we test your network..."), type = MessageBox.TYPE_INFO, enable_input = False)

	def checkNetworkCB(self,data):
		if data is True:
			if self.selectedInterface in ('wlan0', 'ath0'):
				if self.WlanPluginInstalled == True:
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
			if newentry[1] == "hidden...":
				continue
			self.newAPlist.append(newentry)
		
		if len(self.newAPlist):
			if "hidden..." not in self.newAPlist:
				self.newAPlist.append(( _("enter hidden network SSID"), "hidden..." ))

			if (self.wizard[self.currStep].has_key("dynamiclist")):
				currentListEntry = self["list"].getCurrent()
				idx = 0
				for entry in self.newAPlist:
					if entry == currentListEntry:
						newListIndex = idx
					idx +=1
				self.wizard[self.currStep]["evaluatedlist"] = self.newAPlist
				self['list'].setList(self.newAPlist)
				self["list"].setIndex(newListIndex)
				self["list"].updateList(self.newAPlist)

	def listAccessPoints(self):
		self.APList = []
		try:
			from Plugins.SystemPlugins.WirelessLan.Wlan import Wlan
		except ImportError:
			self.APList.append( ( _("No networks found"),_("unavailable") ) )
			return self.APList
		else:
			try:
				self.w = Wlan(self.selectedInterface)
				aps = self.w.getNetworkList()
			except ValueError:
				self.APList = []
				self.APList.append( ( _("No networks found"),_("unavailable") ) )
				return self.APList
			else:
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
	
				if "hidden..." not in self.APList:
					self.APList.append(( _("enter hidden network SSID"), "hidden..." ))
			
				self.rescanTimer.start(3000)
				return self.APList

	def AccessPointsSelectionMade(self, index):
		self.ap = index
		self.WlanList = []
		currList = []
		if (self.wizard[self.currStep].has_key("dynamiclist")):
			currList = self['list'].list
			for entry in currList:
				self.WlanList.append( (entry[1], entry[0]) )
		self.AccessPointsSelect(index)

	def AccessPointsSelect(self, index):
		self.NextStep = 'wlanconfig'

	def AccessPointsSelectionMoved(self):
		self.AccessPointsSelect(self.selection)

	def checkWlanSelection(self):
		self.rescanTimer.stop()
		self.currStep = self.getStepWithID(self.NextStep)

	def isWlanPluginInstalled(self):
		try:
			from Plugins.SystemPlugins.WirelessLan.Wlan import Wlan
		except ImportError:
			self.WlanPluginInstalled = False
		else:
			self.WlanPluginInstalled = True

	def listChoices(self):
		self.rescanTimer.stop()
		list = []
		if self.WlanPluginInstalled == True:
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
			self.NextStep = 'scanwlan'

	def ChoicesSelectionMoved(self):
		pass


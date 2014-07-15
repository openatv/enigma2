from boxbranding import getMachineBrand, getMachineName
from os import system

from enigma import eTimer

from Screens.Screen import Screen
from Screens.WizardLanguage import WizardLanguage
from Screens.Rc import Rc
from Screens.MessageBox import MessageBox

from Components.About import about
from Components.Pixmap import Pixmap
from Components.Sources.Boolean import Boolean
from Components.Sources.StaticText import StaticText
from Components.Network import iNetwork
from Components.config import config, ConfigSubsection, ConfigBoolean
from Tools.Directories import resolveFilename, SCOPE_PLUGINS

config.misc.networkwizard = ConfigSubsection()
config.misc.networkwizard.hasnetwork = ConfigBoolean(default = False)

firstRun = False
checkNetwork = False

class NotificationBox(Screen):
	skin = """
	<screen name="NotificationBox" position="150,40" zPosition="100" size="503,66" backgroundColor="#202020" flags="wfNoBorder">
		<eLabel position="0,0" size="500,63" backgroundColor="#c0c0c0" zPosition="-1" />
		<widget source="text" render="Label" position="5,5" zPosition="100" size="490,53" font="Regular;18" halign="center" valign="center" />
	</screen>"""
	
	def __init__(self, session, text):
		Screen.__init__(self, session)
		self["text"] = StaticText(text)


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
			<widget name="rc" pixmaps="skin_default/rc0.png,skin_default/rc1.png,skin_default/rc2.png" position="500,50" zPosition="10" size="154,500" alphatest="on" />
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
		self.WlanPluginInstalled = False
		self.ap = None
		self.w = None
		self.selectedInterface = interface
		self.originalSelectedInterface = interface
		self.NextStep = None
		self.resetRef = None
		self.AdapterRef = None
		self.APList = None
		self.newAPlist = None
		self.oldlist = None
		self.notification = None
		
		self.originalInterfaceState = {}
		self.originalInterfaceStateChanged = False
		self.Text = None
		self.rescanTimer = eTimer()
		self.rescanTimer.callback.append(self.rescanTimerFired)
		self.dhcpWaitTimerRunCount = 0
		self.dhcpWaitTimer = eTimer()
		self.dhcpWaitTimer.callback.append(self.dhcpWaitTimerFired)

		self.getInstalledInterfaceCount()
		self.isWlanPluginInstalled()

	def exitWizardQuestion(self, ret = False):
		if ret:
			self.markDone()
			self.close()
		
	def markDone(self):
		self.stopScan()
		del self.rescanTimer
		del self.dhcpWaitTimer
		self.dhcpWaitTimerRunCount = 0
		self.checkOldInterfaceState()
		global firstRun
		if firstRun == True:
			firstRun = False

	def back(self):
		self.stopScan()
		self.ap = None
		WizardLanguage.back(self)
		if len(self.stepHistory) <= 1:
			if self.originalSelectedInterface is None:
				self.selectedInterface = None		
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
					self.originalSelectedInterface = self.Adapterlist[0]
		for interface in iNetwork.getAdapterList():
			self.originalInterfaceState[interface] = {}
			self.originalInterfaceState[interface]["up"] = iNetwork.getAdapterAttribute(interface, 'up')

	def verifyFirstRun(self):
		#check if we have already a working network connection after flashing/factory reset
		if firstRun and checkNetwork:
			self.notification = self.session.instantiateDialog(NotificationBox, _("Please wait while we test your network connection..."))
			self.notification.show()			
			iNetwork.checkNetworkState(self.firstRunNetworkCheck)
		elif firstRun and not checkNetwork:
			self.prepareNextStep()
		else:
			self.selectInterface()

	def firstRunNetworkCheck(self,data):
		self.notification.close()
		del self.notification
		global checkNetwork
		#be sure 'back' does not start the check again
		if checkNetwork == True:
			checkNetwork = False
		self.prepareNextStep()

	def prepareNextStep(self):
		if iNetwork.NetworkState <= 2:
			if self.selectedInterface == "eth0" and iNetwork.getAdapterAttribute(self.selectedInterface, 'up'):
				if str('.'.join(["%d" % d for d in iNetwork.getAdapterAttribute(self.selectedInterface, 'ip')])) != "0.0.0.0":
					self.isInterfaceUp = True
					self.NextStep = 'alreadyConfiguredInterface'
					text1 = _("Your internet connection is already configured.") + "\n\n"
					text2 = _("Network") + ":\t" + str(iNetwork.getFriendlyAdapterName(self.selectedInterface)) + "\n"
					text3 = _("IP Address") + ":\t" + str('.'.join(["%d" % d for d in iNetwork.getAdapterAttribute(self.selectedInterface, 'ip')])) + "\n\n"
					text4 = _("Please choose what you want to do next.")
					infotext = text1 + text2 + text3 + text4
					self.currStep = self.getStepWithID(self.NextStep)
					self.Text = infotext
					self.afterAsyncCode()
				else:
					self.selectInterface()
			else:
				self.selectInterface()
		else:
			self.selectInterface()

	def prepareAlreadyConfiguredInterfaceSelection(self):
		list = []
		list.append((_("Continue configuring your network"), "selectinterface"))
		list.append((_("Exit network wizard"), "end"))
		return list

	def AlreadyConfiguredInterfaceSelectionMade(self):
		if self.selection == 'end':
			self.NextStep = 'end'
		else:
			if self.InstalledInterfaceCount > 1:
					self.selectedInterface = None
			self.NextStep = 'selectinterface'
			
	def selectInterface(self):
		self.InterfaceState = None
		if self.NextStep == "end":
			self.currStep = self.getStepWithID(self.NextStep)
			self.afterAsyncCode()
		else:
			if self.selectedInterface is None:
				if self.InstalledInterfaceCount <= 1:
					self.NextStep = 'nwconfig'
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
		iNetwork.checkNetworkState(self.AdapterSetupEndFinished)
		self.AdapterRef = self.session.openWithCallback(self.AdapterSetupEndCB, MessageBox, _("Please wait while we test your network..."), type = MessageBox.TYPE_INFO, enable_input = False)

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
				self.Text = self.getLanStatusMsg()
				self.afterAsyncCode()

	def AdapterSetupEndFinished(self,data):
		if data <= 2:
			config.misc.networkwizard.hasnetwork.value = True
			config.misc.networkwizard.save()		  
			self.InterfaceState = True
			self.AdapterRef.close(True)
		else:
			if iNetwork.getAdapterAttribute(self.selectedInterface, 'up') is True and self.dhcpWaitTimerRunCount <=2:
				#some wlan drivers need a long time to get an ip, lets wait max three times and retest network, if first pass didn't got a usable result.
				self.dhcpWaitTimer.startLongTimer(4)
			else:
				config.misc.networkwizard.hasnetwork.value = False
				config.misc.networkwizard.save()  
				self.InterfaceState = False
				self.AdapterRef.close(True)

	def dhcpWaitTimerFired(self):
		if self.dhcpWaitTimerRunCount <=2:
			self.dhcpWaitTimerRunCount+=1
		else:
			self.dhcpWaitTimer.stop()
		iNetwork.getInterfaces(self.getInterfacesReReadFinished)

	def getInterfacesReReadFinished(self, data):
		if data is True:
			if iNetwork.getAdapterAttribute(self.selectedInterface, 'up') is True:
				self.isInterfaceUp = True
			else:
				self.isInterfaceUp = False
		iNetwork.checkNetworkState(self.AdapterSetupEndFinished)

	def checkWlanStateCB(self,data,status):
		if data is not None:
			if data is True:
				if status is not None:
					wlan0 = about.getIfConfig('wlan0')
					if wlan0.has_key('addr'):
						text11 = _("Your IP:") + "\t" + wlan0['addr'] + "\n\n"
						if wlan0.has_key('netmask'):
							text11 += _("Netmask:") + "\t" + wlan0['netmask'] + "\n"
						if wlan0.has_key('brdaddr'):
							text11 += _("Broadcast:") + "\t" + wlan0['brdaddr'] + "\n"
						if wlan0.has_key('hwaddr'):
							text11 += _("MAC:") + "\t" + wlan0['hwaddr'] + "\n\n"  
					text1 = _("Your %s %s is now ready to be used.\n\nYour internet connection is working now.\n\n") % (getMachineBrand(), getMachineName())
					text2 = _('Accesspoint:') + "\t" + str(status[self.selectedInterface]["accesspoint"]) + "\n"
					text3 = _('SSID:') + "\t" + str(status[self.selectedInterface]["essid"]) + "\n"
					text4 = _('Link quality:') + "\t" + str(status[self.selectedInterface]["quality"])+ "\n"
					text5 = _('Signal strength:') + "\t" + str(status[self.selectedInterface]["signal"]) + "\n"
					text6 = _('Bitrate:') + "\t" + str(status[self.selectedInterface]["bitrate"]) + " Mbps\n"
					text7 = _('Encryption:') + "\t" + str(status[self.selectedInterface]["encryption"]) + "\n"
					text8 = _("Please press OK to continue.")
					try:
						infotext = text1 + text11 + text2 + text3 + text4 + text5 + text6 + text7 + "\n" + text8
					except:
						infotext = text1 + text2 + text3 + text4 + text5 + text6 + text7 + "\n" + text8
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
				self.APList.append( ( _("Searching for WLAN networks..."), None ) )
			
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

	def getLanStatusMsg(self):
		eth0 = about.getIfConfig('eth0')
		if eth0.has_key('addr'):
			text11 = _("Your IP:") + "\t" + eth0['addr'] + "\n\n"
			if eth0.has_key('netmask'):
				text11 += _("Netmask:") + "\t" + eth0['netmask'] + "\n"
			if eth0.has_key('brdaddr'):
				text11 += _("Broadcast:") + "\t" + eth0['brdaddr'] + "\n"
			if eth0.has_key('hwaddr'):
				text11 += _("MAC:") + "\t" + eth0['hwaddr'] + "\n"  
		try:
			text1 = _("Your %s %s is now ready to be used.\n\nYour internet connection is working now.\n\n") % (getMachineBrand(), getMachineName())
			text2 = _("Please press OK to continue.")
			return text1 + text11 +"\n" + text2
		except:
			text1 = _("Your %s %s is now ready to be used.\n\nYour internet connection is not working now.\n\n") % (getMachineBrand(), getMachineName())
			text2 = _("Please press OK to continue.")
			return text1 + "\n" + text2

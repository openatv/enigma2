from Screens.Wizard import wizardManager, WizardSummary
from Screens.WizardLanguage import WizardLanguage
from Screens.Rc import Rc
from Screens.MessageBox import MessageBox

from Components.Pixmap import Pixmap, MovingPixmap, MultiPixmap
from Components.Sources.Boolean import Boolean
from Components.config import config, ConfigBoolean, configfile, ConfigYesNo, NoSave, ConfigSubsection, ConfigText, getConfigListEntry, ConfigSelection, ConfigPassword
from Components.Network import iNetwork

from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_SKIN_IMAGE


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
	def __init__(self, session):
		self.xmlfile = resolveFilename(SCOPE_PLUGINS, "SystemPlugins/NetworkWizard/networkwizard.xml")
		WizardLanguage.__init__(self, session, showSteps = False, showStepSlider = False)
		Rc.__init__(self)
		self.session = session
		self["wizard"] = Pixmap()
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["VKeyIcon"] = Boolean(False)

		self.InterfaceState = None
		self.isInterfaceUp = None
		self.WlanPluginInstalled = None
		self.ap = None
		self.selectedInterface = None
		self.NextStep = None
		self.myref = None
		self.checkRef = None
		self.AdapterRef = None
		self.WlanList = None
		self.isWlanPluginInstalled()

	def listInterfaces(self):
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
		self.Adapterlist = iNetwork.getAdapterList()
		if self.NextStep is not 'end':
			if len(self.Adapterlist) == 0:
				#Reset Network to defaults if network broken
				iNetwork.resetNetworkConfig('lan', self.checkInterfaceCB)
				self.myref = self.session.openWithCallback(self.resetfinishedCB, MessageBox, _("Please wait while we prepare your network interfaces..."), type = MessageBox.TYPE_INFO, enable_input = False)
			if iface == 'eth0':
				if iface in iNetwork.configuredNetworkAdapters and len(iNetwork.configuredNetworkAdapters) == 1:
					if iNetwork.getAdapterAttribute(iface, 'up') is True:
						self.isInterfaceUp = True
					else:
						self.isInterfaceUp = False
					self.resetfinishedCB(False)
				else:
					iNetwork.resetNetworkConfig('lan',self.checkInterfaceCB)
					self.myref = self.session.openWithCallback(self.resetfinishedCB, MessageBox, _("Please wait while we prepare your network interfaces..."), type = MessageBox.TYPE_INFO, enable_input = False)
			elif iface == 'wlan0':
				if iface in iNetwork.configuredNetworkAdapters and len(iNetwork.configuredNetworkAdapters) == 1:
					if iNetwork.getAdapterAttribute(iface, 'up') is True:
						self.isInterfaceUp = True
					else:
						self.isInterfaceUp = False
					self.resetfinishedCB(False)
				else:
					iNetwork.resetNetworkConfig('wlan',self.checkInterfaceCB)
					self.myref = self.session.openWithCallback(self.resetfinishedCB, MessageBox, _("Please wait while we prepare your network interfaces..."), type = MessageBox.TYPE_INFO, enable_input = False)
			elif iface == 'ath0':
				if iface in iNetwork.configuredNetworkAdapters and len(iNetwork.configuredNetworkAdapters) == 1:
					if iNetwork.getAdapterAttribute(iface, 'up') is True:
						self.isInterfaceUp = True
					else:
						self.isInterfaceUp = False
					self.resetfinishedCB(False)
				else:
					iNetwork.resetNetworkConfig('wlan-mpci',self.checkInterfaceCB)
					self.myref = self.session.openWithCallback(self.resetfinishedCB, MessageBox, _("Please wait while we prepare your network interfaces..."), type = MessageBox.TYPE_INFO, enable_input = False)
		else:
			self.resetfinishedCB(False)
			
	def resetfinishedCB(self,data):
		if data is True:
			self.currStep = self.getStepWithID(self.NextStep)
			self.afterAsyncCode()
		else:
			self.currStep = self.getStepWithID(self.NextStep)
			self.afterAsyncCode()

	def checkInterfaceCB(self,callback,iface):
		if callback is not None:
			if callback is True:
				iNetwork.getInterfaces(self.getInterfacesDataAvail)
				

	def getInterfacesDataAvail(self, data):
		if data is True:
			if iNetwork.getAdapterAttribute(self.selectedInterface, 'up') is True:
				self.isInterfaceUp = True
			else:
				self.isInterfaceUp = False
			self.myref.close(True)

	def AdapterSetupEnd(self, iface):
		if iNetwork.getAdapterAttribute(iface, "dhcp") is True:
			iNetwork.checkNetworkState(self.AdapterSetupEndFinished)
			self.AdapterRef = self.session.openWithCallback(self.AdapterSetupEndCB, MessageBox, _("Please wait while we test your network..."), type = MessageBox.TYPE_INFO, enable_input = False)

		else:
			self.currStep = self.getStepWithID("confdns")
			self.afterAsyncCode()

	def AdapterSetupEndCB(self,data):
		if data is True:
			self.currStep = self.getStepWithID("checklanstatusend")
			self.afterAsyncCode()

	def AdapterSetupEndFinished(self,data):
		if data <= 2:
			self.InterfaceState = True
		else:
			self.InterfaceState = False
		self.AdapterRef.close(True)
			
	def checkNetwork(self):
		iNetwork.checkNetworkState(self.checkNetworkStateFinished)
		self.checkRef = self.session.openWithCallback(self.checkNetworkCB, MessageBox, _("Please wait while we test your network..."), type = MessageBox.TYPE_INFO, enable_input = False)

	def checkNetworkCB(self,data):
		if data is True:
			self.currStep = self.getStepWithID("checklanstatusend")
			self.afterAsyncCode()

	def checkNetworkStateFinished(self,data):
		if data <= 2:
			self.InterfaceState = True
		else:
			self.InterfaceState = False
		self.checkRef.close(True)
	
	def markDone(self):
		pass

	def listModes(self):
		list = []
		self.WlanList = []
		try:
			from Plugins.SystemPlugins.WirelessLan.Wlan import Wlan
		except ImportError:
			list.append( ( _("No networks found"),_("unavailable") ) )
			self.WlanList.append(_("No networks found"))
			return list
		else:	
			self.w = Wlan(self.selectedInterface)
			aps = self.w.getNetworkList()
			if aps is not None:
				print "[NetworkWizard.py] got Accespoints!"
				for ap in aps:
					a = aps[ap]
					if a['active']:
						if a['essid'] != "":
							#a['essid'] = a['bssid']
							list.append( (a['essid'], a['essid']) )
							self.WlanList.append(a['essid'])	
			if "hidden..." not in list:
				list.append( ( _("enter hidden network SSID"),_("hidden...") ) )
				self.WlanList.append(_("hidden..."))	
			return list

	def modeSelectionMade(self, index):
		self.modeSelect(index)
		
	def modeSelectionMoved(self):
		self.modeSelect(self.selection)
		
	def modeSelect(self, mode):
		self.ap = mode
		print "ModeSelected:", mode

	def restartNetwork(self):
		iNetwork.restartNetwork()
		self.checkNetwork()
	
	def isWlanPluginInstalled(self):		
		try:
			from Plugins.SystemPlugins.WirelessLan.Wlan import Wlan
		except ImportError:
			self.WlanPluginInstalled = False
		else:
			self.WlanPluginInstalled = True


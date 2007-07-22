from Screen import Screen
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigListScreen
from Components.config import config, getConfigListEntry
from Components.Network import iNetwork
from Components.Label import Label
from Components.MenuList import MenuList
from Components.config import config, ConfigYesNo, ConfigIP, NoSave, ConfigNothing
from Components.PluginComponent import plugins
from Plugins.Plugin import PluginDescriptor


class NetworkAdapterSelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		
		self["adapterlist"] = MenuList(iNetwork.getAdapterList())
		
		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"ok": self.okbuttonClick ,
			"cancel": self.close
		})

	def okbuttonClick(self):
		selection = self["adapterlist"].getCurrent()
		print "selection:", selection
		if selection is not None:
			self.session.open(AdapterSetup, selection)
			
class NameserverSetup(Screen, ConfigListScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.backupNameserverList = iNetwork.getNameserverList()[:]
		print "backup-list:", self.backupNameserverList
		
		self["red"] = Label(_("Delete"))
		self["green"] = Label(_("Add"))
		
		self.createConfig()
		
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
		{
			"ok": self.ok,
			"cancel": self.cancel,
			"green": self.add,
			"red": self.remove
		}, -2)

		self.list = []
		ConfigListScreen.__init__(self, self.list)
		self.createSetup()
		
	def createConfig(self):
		self.nameservers = iNetwork.getNameserverList()
		self.nameserverEntries = []
		
		for nameserver in self.nameservers:
			self.nameserverEntries.append(NoSave(ConfigIP(default=nameserver)))
			
	def createSetup(self):
		self.list = []

		#self.nameserverConfigEntries = []
		for i in range(len(self.nameserverEntries)):
			self.list.append(getConfigListEntry(_("Nameserver %d") % (i + 1), self.nameserverEntries[i]))
		
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def ok(self):
		iNetwork.clearNameservers()
		for nameserver in self.nameserverEntries:
			iNetwork.addNameserver(nameserver.value)
		iNetwork.writeNameserverConfig()
		self.close()
	
	def cancel(self):
		iNetwork.clearNameservers()
		print "backup-list:", self.backupNameserverList
		for nameserver in self.backupNameserverList:
			iNetwork.addNameserver(nameserver)
		self.close()
	
	def add(self):
		iNetwork.addNameserver([0,0,0,0])
		self.createConfig()
		self.createSetup()
	
	def remove(self):
		print "currentIndex:", self["config"].getCurrentIndex()
		
		index = self["config"].getCurrentIndex()
		if index < len(self.nameservers):
			iNetwork.removeNameserver(self.nameservers[index])
			self.createConfig()
			self.createSetup()

		
class AdapterSetup(Screen, ConfigListScreen):
	def __init__(self, session, iface):
		Screen.__init__(self, session)
		
		self.iface = iface

		print iNetwork.getAdapterAttribute(self.iface, "dhcp")
		self.dhcpConfigEntry = NoSave(ConfigYesNo(default=iNetwork.getAdapterAttribute(self.iface, "dhcp")))
		self.hasGatewayConfigEntry = NoSave(ConfigYesNo(default=True))
		self.ipConfigEntry = NoSave(ConfigIP(default=iNetwork.getAdapterAttribute(self.iface, "ip")))
		self.netmaskConfigEntry = NoSave(ConfigIP(default=iNetwork.getAdapterAttribute(self.iface, "netmask")))
		self.gatewayConfigEntry = NoSave(ConfigIP(default=iNetwork.getAdapterAttribute(self.iface, "gateway")))
        
		self["iface"] = Label(iNetwork.getAdapterName(self.iface))
		        
		self["actions"] = ActionMap(["SetupActions"],
		{
			"ok": self.ok,
			"cancel": self.cancel,
		}, -2)

		self.list = []
		ConfigListScreen.__init__(self, self.list)
		self.createSetup()

		self["introduction"] = Label(_("Press OK to activate the settings."))

	def createSetup(self):
		self.list = []

		self.dhcpEntry = getConfigListEntry(_("Use DHCP"), self.dhcpConfigEntry)
		self.list.append(self.dhcpEntry)
		if not self.dhcpConfigEntry.value:
			self.list.append(getConfigListEntry(_('IP Address'), self.ipConfigEntry))
			self.list.append(getConfigListEntry(_('Netmask'), self.netmaskConfigEntry))
			self.list.append(getConfigListEntry(_('Use a gateway'), self.hasGatewayConfigEntry))
			if self.hasGatewayConfigEntry.value:
				self.list.append(getConfigListEntry(_('Gateway'), self.gatewayConfigEntry))
		
		self.extended = None
		self.extendedSetup = None
		for p in plugins.getPlugins(PluginDescriptor.WHERE_NETWORKSETUP):
			callFnc = p.__call__["ifaceSupported"](self.iface)
			if callFnc is not None:
				self.extended = callFnc
				print p.__call__
				if p.__call__.has_key("configStrings"):
					self.configStrings = p.__call__["configStrings"]
				else:
					self.configStrings = None
				
				if p.__call__.has_key("menuEntryName"):
					menuEntryName = p.__call__["menuEntryName"](self.iface)
				else:
					menuEntryName = _('Extended Setup...')
				self.extendedSetup = getConfigListEntry(menuEntryName, NoSave(ConfigNothing()))
				self.list.append(self.extendedSetup)

		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def newConfig(self):
		print self["config"].getCurrent()
		if self["config"].getCurrent() == self.dhcpEntry:
			self.createSetup()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.createSetup()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.createSetup()

	def ok(self):
		selection = self["config"].getCurrent()
		if selection == self.extendedSetup:
			self.extended(self.session, self.iface)
		else:
			iNetwork.setAdapterAttribute(self.iface, "dhcp", self.dhcpConfigEntry.value)
			iNetwork.setAdapterAttribute(self.iface, "ip", self.ipConfigEntry.value)
			iNetwork.setAdapterAttribute(self.iface, "netmask", self.netmaskConfigEntry.value)
			if self.hasGatewayConfigEntry.value:
				iNetwork.setAdapterAttribute(self.iface, "gateway", self.gatewayConfigEntry.value)
			else:
				iNetwork.removeAdapterAttribute(self.iface, "gateway")
			
			if self.extended is not None and self.configStrings is not None:
				iNetwork.setAdapterAttribute(self.iface, "configStrings", self.configStrings(self.iface))

			iNetwork.deactivateNetworkConfig()
			iNetwork.writeNetworkConfig()    
			iNetwork.activateNetworkConfig()
			self.close()

	def cancel(self):
		iNetwork.getInterfaces()
		self.close()

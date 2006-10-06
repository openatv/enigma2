from Screen import Screen
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigList, ConfigListScreen
from Components.config import config, getConfigListEntry
from Components.Network import iNetwork
from Components.Label import Label

class NetworkSetup(Screen, ConfigListScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
        
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

		self.dhcpEntry = getConfigListEntry(_("Use DHCP"), config.network.dhcp)
		self.list.append(self.dhcpEntry)
		self.list.append(getConfigListEntry(_('IP Address'), config.network.ip))
		if not config.network.dhcp.value:
			self.list.append(getConfigListEntry(_('Netmask'), config.network.netmask))
			self.list.append(getConfigListEntry(_('Gateway'), config.network.gateway))
			self.list.append(getConfigListEntry(_('Nameserver'), config.network.dns))

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
		#for x in self["config"].list:
			#x[1].save()
		iNetwork.writeNetworkConfig()    
		iNetwork.activateNetworkConfig()
		self.close()

	def cancel(self):
		for x in self["config"].list:
			x[1].cancel()
		iNetwork.loadNetworkConfig()
		self.close()

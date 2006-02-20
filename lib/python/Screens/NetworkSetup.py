from Screen import Screen
from Components.ActionMap import NumberActionMap
from Components.ConfigList import ConfigList
from Components.config import config
from Components.config import getConfigListEntry
from Components.Network import iNetwork
from Components.Label import Label

class NetworkSetup(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
        
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

		self.list = []
		self["config"] = ConfigList(self.list)
		self.createSetup()
        
		self["introduction"] = Label(_("Press OK to activate the settings."))
        
	def createSetup(self):
		self.list = []
        
		self.dhcpEntry = getConfigListEntry(_("Use DHCP"), config.network.dhcp)
		self.list.append(self.dhcpEntry)
		self.list.append(getConfigListEntry(_('IP Address'), config.network.ip))
		if (config.network.dhcp.value == 0):
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
		self["config"].handleKey(config.key["prevElement"])
		self.newConfig()

	def keyRight(self):
		self["config"].handleKey(config.key["nextElement"])
		self.newConfig()
    
	def keyNumberGlobal(self, number):
		print "You pressed number " + str(number)
		if (self["config"].getCurrent()[1].parent.enabled == True):
			self["config"].handleKey(config.key[str(number)])
        
	def keySave(self):
		#for x in self["config"].list:
			#x[1].save()
        
		iNetwork.writeNetworkConfig()    
		iNetwork.activateNetworkConfig()
		self.close()

	def keyCancel(self):
		for x in self["config"].list:
			x[1].cancel()
		iNetwork.loadNetworkConfig()
		self.close()

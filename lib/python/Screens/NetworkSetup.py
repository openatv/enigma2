from Screen import Screen
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigList
from Components.config import config
from Components.config import getConfigListEntry

class NetworkSetup(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        
        self["actions"] = ActionMap(["SetupActions"],
        {
            "ok": self.keySave,
            "cancel": self.keyCancel,
            "left": self.keyLeft,
            "right": self.keyRight
        }, -1)

        self.list = []
        self["config"] = ConfigList(self.list)
        self.createSetup()
        
    def createSetup(self):
        self.list = []
        
        self.list.append(getConfigListEntry("Use DHCP", config.network.dhcp))
        if (config.network.dhcp.value == 0):
            self.list.append(getConfigListEntry("IP Address", config.network.ip))
            self.list.append(getConfigListEntry("Netmask", config.network.netmask))
            self.list.append(getConfigListEntry("Gateway", config.network.gateway))
            self.list.append(getConfigListEntry("Nameserver", config.network.dns))
        
        self["config"].list = self.list
        self["config"].l.setList(self.list)
        
    def newConfig(self):
        print self["config"].getCurrent()
        if self["config"].getCurrent()[0] == "Use DHCP":
            self.createSetup()

    def keyLeft(self):
        self["config"].handleKey(config.key["prevElement"])
        self.newConfig()

    def keyRight(self):
        self["config"].handleKey(config.key["nextElement"])
        self.newConfig()

    def keySave(self):
        for x in self["config"].list:
            x[1].save()
        self.close()

    def keyCancel(self):
        for x in self["config"].list:
            x[1].cancel()
        self.close()        
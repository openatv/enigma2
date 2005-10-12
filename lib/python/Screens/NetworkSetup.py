from Screen import Screen
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigList
from Components.config import config
from Components.config import getConfigListEntry
from Components.Network import iNetwork

class NetworkSetup(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        
        self["actions"] = ActionMap(["SetupActions"],
        {
            "ok": self.keySave,
            "cancel": self.keyCancel,
            "left": self.keyLeft,
            "right": self.keyRight,
            "1": self.keyNumber1,
            "2": self.keyNumber2,
            "3": self.keyNumber3,
            "4": self.keyNumber4,
            "5": self.keyNumber5,
            "6": self.keyNumber6,
            "7": self.keyNumber7,
            "8": self.keyNumber8,
            "9": self.keyNumber9,
            "0": self.keyNumber0
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
    
    def keyNumberGlobal(self, number):
        print "You pressed number " + str(number)
        if (self["config"].getCurrent()[1].parent.enabled == True):
            self["config"].handleKey(config.key[str(number)])
        
    def keyNumber1(self):
        self.keyNumberGlobal(1)
    def keyNumber2(self):
        self.keyNumberGlobal(2)
    def keyNumber3(self):
        self.keyNumberGlobal(3)
    def keyNumber4(self):
        self.keyNumberGlobal(4)
    def keyNumber5(self):
        self.keyNumberGlobal(5)
    def keyNumber6(self):
        self.keyNumberGlobal(6)
    def keyNumber7(self):
        self.keyNumberGlobal(7)
    def keyNumber8(self):
        self.keyNumberGlobal(8)
    def keyNumber9(self):
        self.keyNumberGlobal(9)
    def keyNumber0(self):
        self.keyNumberGlobal(0)        

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
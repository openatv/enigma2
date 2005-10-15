from Screen import Screen
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigList
from Components.config import config
from Components.config import getConfigListEntry
from Components.NimManager import nimmanager
from Components.Label import Label
from Components.ScanSetup import InitScanSetup

class ScanSetup(Screen):
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

        self["introduction"] = Label("Press OK to start the scan")
        
    def createSetup(self):
        #InitScanSetup()
        self.list = []
        
        self.list.append(getConfigListEntry("Type of scan", config.scan.type))
        self.list.append(getConfigListEntry("Tuner", config.scan.nims))
        
        # single transponder scan
        if (config.scan.type.value == 0):
            if (nimmanager.getNimType(config.scan.nims.value) == nimmanager.nimType["DVB-S"]):
                self.list.append(getConfigListEntry("Frequency", config.scan.sat.frequency))
                self.list.append(getConfigListEntry("Inversion", config.scan.sat.inversion))
                self.list.append(getConfigListEntry("Symbolrate", config.scan.sat.symbolrate))
                self.list.append(getConfigListEntry("Polarity", config.scan.sat.polarzation))
                self.list.append(getConfigListEntry("FEC", config.scan.sat.fec))
            if (nimmanager.getNimType(config.scan.nims.value) == nimmanager.nimType["DVB-C"]):
                self.list.append(getConfigListEntry("Frequency", config.scan.cab.frequency))
                self.list.append(getConfigListEntry("Inversion", config.scan.cab.inversion))
                self.list.append(getConfigListEntry("Symbolrate", config.scan.cab.symbolrate))
                self.list.append(getConfigListEntry("Modulation", config.scan.cab.modulation))
                self.list.append(getConfigListEntry("FEC", config.scan.cab.fec))
            if (nimmanager.getNimType(config.scan.nims.value) == nimmanager.nimType["DVB-T"]):
                self.list.append(getConfigListEntry("Frequency", config.scan.ter.frequency))
                self.list.append(getConfigListEntry("Inversion", config.scan.ter.inversion))
                self.list.append(getConfigListEntry("Bandwidth", config.scan.ter.bandwidth))
                self.list.append(getConfigListEntry("Code rate high", config.scan.ter.fechigh))
                self.list.append(getConfigListEntry("Code rate low", config.scan.ter.feclow))
                self.list.append(getConfigListEntry("Modulation", config.scan.ter.modulation))
                self.list.append(getConfigListEntry("Transmission mode", config.scan.ter.transmission))
                self.list.append(getConfigListEntry("Guard interval mode", config.scan.ter.guard))
                self.list.append(getConfigListEntry("Hierarchy mode", config.scan.ter.hierarchy))

        # single satellite scan
        print "NIM: ", config.scan.nims.value
        print config.scan.satselection
        if (config.scan.type.value == 1):
            print config.scan.satselection[config.scan.nims.value]
            self.list.append(getConfigListEntry("Satellite", config.scan.satselection[config.scan.nims.value]))
            
        
        # multi sat scan
        if (config.scan.type.value == 2):
            for sat in nimmanager.satList:
                self.list.append(getConfigListEntry(sat[0], config.scan.scansat[sat[1]]))                
                
        self["config"].list = self.list
        self["config"].l.setList(self.list)
        
    def newConfig(self):
        print self["config"].getCurrent()
        if self["config"].getCurrent()[0] == "Type of scan":
            self.createSetup()
        if self["config"].getCurrent()[0] == "Tuner":
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
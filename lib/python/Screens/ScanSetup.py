from Screen import Screen
from Components.config import *
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigList
from Components.config import config
from Components.config import getConfigListEntry
from Components.NimManager import nimmanager
from Components.Label import Label

class ScanSetup(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        
        self.updateSatList()
        self.createConfig()

        
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

    def updateSatList(self):
        self.satList = []
        for slot in nimmanager.nimslots:
            self.satList.append(nimmanager.getSatListForNim(slot.slotid))
            
    def createSetup(self):
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
        print config.scan.satselection
        if (config.scan.type.value == 1):
            self.updateSatList()
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
            
    def createConfig(self):
            config.scan = ConfigSubsection()
            config.scan.sat = ConfigSubsection()
            config.scan.cab = ConfigSubsection()
            config.scan.ter = ConfigSubsection()        
        
            config.scan.type = configElement_nonSave("config.scan.type", configSelection, 0, ("Single transponder", "Single satellite", "Multisat"))
            nimList = [ ]
            for nim in nimmanager.nimList():
                nimList.append(nim[0])
            nimList.append("all")
            config.scan.nims = configElement_nonSave("config.scan.nims", configSelection, 0, nimList)
            
            # sat
            config.scan.sat.frequency = configElement_nonSave("config.scan.sat.frequency", configSequence, [12187], configsequencearg.get("INTEGER", (10000, 14000)))
            config.scan.sat.inversion = configElement_nonSave("config.scan.sat.inversion", configSelection, 0, ("off", "on"))
            config.scan.sat.symbolrate = configElement_nonSave("config.scan.sat.symbolrate", configSequence, [27500], configsequencearg.get("INTEGER", (1, 30000)))
            config.scan.sat.polarzation = configElement_nonSave("config.scan.sat.polarzation", configSelection, 0, ("horizontal", "vertical"))
            config.scan.sat.fec = configElement_nonSave("config.scan.sat.fec", configSelection, 0, ("Auto", "1/2", "2/3", "3/4", "4/5", "5/6", "7/8", "8/9"))
        
            # cable
            config.scan.cab.frequency = configElement_nonSave("config.scan.cab.frequency", configSequence, [466], configsequencearg.get("INTEGER", (10000, 14000)))
            config.scan.cab.inversion = configElement_nonSave("config.scan.cab.inversion", configSelection, 0, ("off", "on"))
            config.scan.cab.modulation = configElement_nonSave("config.scan.cab.modulation", configSelection, 0, ("Auto", "16-QAM", "32-QAM", "64-QAM", "128-QAM", "256-QAM"))
            config.scan.cab.fec = configElement_nonSave("config.scan.cab.fec", configSelection, 0, ("Auto", "1/2", "2/3", "3/4", "4/5", "5/6", "7/8", "8/9"))
            config.scan.cab.symbolrate = configElement_nonSave("config.scan.cab.symbolrate", configSequence, [6900], configsequencearg.get("INTEGER", (1, 30000)))
            
            # terrestial
            config.scan.ter.frequency = configElement_nonSave("config.scan.ter.frequency", configSequence, [466], configsequencearg.get("INTEGER", (10000, 14000)))
            config.scan.ter.inversion = configElement_nonSave("config.scan.ter.inversion", configSelection, 0, ("off", "on"))
            config.scan.ter.bandwidth = configElement_nonSave("config.scan.ter.bandwidth", configSelection, 0, ("Auto", "6 MHz", "7MHz", "8MHz"))
            config.scan.ter.fechigh = configElement_nonSave("config.scan.ter.fechigh", configSelection, 0, ("Auto", "1/2", "2/3", "3/4", "4/5", "5/6", "7/8", "8/9"))
            config.scan.ter.feclow = configElement_nonSave("config.scan.ter.feclow", configSelection, 0, ("Auto", "1/2", "2/3", "3/4", "4/5", "5/6", "7/8", "8/9"))
            config.scan.ter.modulation = configElement_nonSave("config.scan.ter.modulation", configSelection, 0, ("Auto", "16-QAM", "32-QAM", "64-QAM", "128-QAM", "256-QAM"))
            config.scan.ter.transmission = configElement_nonSave("config.scan.ter.transmission", configSelection, 0, ("Auto", "2K", "8K"))
            config.scan.ter.guard = configElement_nonSave("config.scan.ter.guard", configSelection, 0, ("Auto", "1/4", "1/8", "1/16", "1/32"))
            config.scan.ter.hierarchy = configElement_nonSave("config.scan.ter.hierarchy", configSelection, 0, ("Auto", "1", "2", "4"))
            
            config.scan.scansat = {}
            for sat in nimmanager.satList:
                #print sat[1]
                config.scan.scansat[sat[1]] = configElement_nonSave("config.scan.scansat[" + str(sat[1]) + "]", configSelection, 0, ("yes", "no"))
                
            config.scan.satselection = []
            slotid = 0
            for slot in nimmanager.nimslots:
                config.scan.satselection.append(configElement_nonSave("config.scan.satselection[" + str(slot.slotid) + "]", configSatlist, 0, self.satList[slot.slotid]))
        
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
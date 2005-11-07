from Screen import Screen
from Components.config import *
from Components.ActionMap import NumberActionMap
from Components.ConfigList import ConfigList
from Components.NimManager import nimmanager
from Components.Label import Label
from time import *

class TimerEntry(Screen):
    def __init__(self, session):
        Screen.__init__(self, session)
        
        self.createConfig()
        
        self["actions"] = NumberActionMap(["SetupActions"],
        {
            "ok": self.keyGo,
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

        self["introduction"] = Label("Press OK to start the scan")

    def createConfig(self):
            config.timerentry = ConfigSubsection()

            config.timerentry.date = configElement_nonSave("config.timerentry.date", configDateTime, time(), ("%d.%B %Y", 86400))
            config.timerentry.time = configElement_nonSave("config.timerentry.time", configDateTime, time(), ("%H:%M", 60))

    def createSetup(self):
        self.list = []
        
        self.list.append(getConfigListEntry("Date", config.timerentry.date))
        self.list.append(getConfigListEntry("Time", config.timerentry.time))        
        
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

    def keyNumberGlobal(self, number):
        print "You pressed number " + str(number)
        if (self["config"].getCurrent()[1].parent.enabled == True):
            self["config"].handleKey(config.key[str(number)])

    def keyGo(self):
        for x in self["config"].list:
            x[1].save()
        self.session.openWithCallback(self.keyCancel, ServiceScan)        

        #self.close()

    def keyCancel(self):
        for x in self["config"].list:
            x[1].cancel()
        self.close()
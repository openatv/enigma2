from Screen import Screen
from Components.config import *
from Components.ActionMap import NumberActionMap
from Components.ConfigList import ConfigList
from Components.NimManager import nimmanager
from Components.Label import Label
from time import *

class TimerEntry(Screen):
    def __init__(self, session, timer):
        Screen.__init__(self, session)
        
        self.createConfig(timer)
        
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

    def createConfig(self, timer):
            config.timerentry = ConfigSubsection()

            config.timerentry.type = configElement_nonSave("config.timerentry.type", configSelection, 0, ("once", "repeated"))
            config.timerentry.description = configElement_nonSave("config.timerentry.description", configText, timer.description, (configText.extendableSize,))

            config.timerentry.repeated = configElement_nonSave("config.timerentry.repeated", configSelection, 0, ("daily", "weekly", "Mon-Fri", "user-defined"))

            config.timerentry.startdate = configElement_nonSave("config.timerentry.startdate", configDateTime, timer.begin, ("%d.%B %Y", 86400))
            config.timerentry.starttime = configElement_nonSave("config.timerentry.starttime", configSequence, [int(strftime("%H", localtime(timer.begin))), int(strftime("%M", localtime(timer.begin)))], configsequencearg.get("CLOCK"))

            config.timerentry.enddate = configElement_nonSave("config.timerentry.enddate", configDateTime, timer.end, ("%d.%B %Y", 86400))
            config.timerentry.endtime = configElement_nonSave("config.timerentry.endtime", configSequence, [int(strftime("%H", localtime(timer.end))), int(strftime("%M", localtime(timer.end)))], configsequencearg.get("CLOCK"))
            
            config.timerentry.weekday = configElement_nonSave("config.timerentry.weekday", configDateTime, time(), ("%A", 86400))
            
            config.timerentry.monday = configElement_nonSave("config.timerentry.monday", configSelection, 0, ("yes", "no"))
            config.timerentry.tuesday = configElement_nonSave("config.timerentry.tuesday", configSelection, 0, ("yes", "no"))
            config.timerentry.wednesday = configElement_nonSave("config.timerentry.wednesday", configSelection, 0, ("yes", "no"))
            config.timerentry.thursday = configElement_nonSave("config.timerentry.thursday", configSelection, 0, ("yes", "no"))
            config.timerentry.friday = configElement_nonSave("config.timerentry.friday", configSelection, 0, ("yes", "no"))
            config.timerentry.saturday = configElement_nonSave("config.timerentry.saturday", configSelection, 0, ("yes", "no"))
            config.timerentry.sunday = configElement_nonSave("config.timerentry.sunday", configSelection, 0, ("yes", "no"))
            
            # FIXME some service-chooser needed here
            config.timerentry.service = configElement_nonSave("config.timerentry.service", configSelection, 0, ((str(timer.service_ref.getServiceName())),))
            
    def createSetup(self):
        self.list = []
        self.list.append(getConfigListEntry("Description", config.timerentry.description))
        self.list.append(getConfigListEntry("TimerType", config.timerentry.type))
        
        if (config.timerentry.type.value == 0): # once
            pass
        else: # repeated
            self.list.append(getConfigListEntry("Frequency", config.timerentry.repeated))
            if (config.timerentry.repeated.value == 0): # daily
                pass
            if (config.timerentry.repeated.value == 2): # Mon-Fri
                pass
            if (config.timerentry.repeated.value == 1): # weekly
                self.list.append(getConfigListEntry("Weekday", config.timerentry.weekday))

            if (config.timerentry.repeated.value == 3): # user-defined
                self.list.append(getConfigListEntry("Monday", config.timerentry.monday))
                self.list.append(getConfigListEntry("Tuesday", config.timerentry.tuesday))
                self.list.append(getConfigListEntry("Wednesday", config.timerentry.wednesday))
                self.list.append(getConfigListEntry("Thursday", config.timerentry.thursday))
                self.list.append(getConfigListEntry("Friday", config.timerentry.friday))
                self.list.append(getConfigListEntry("Saturday", config.timerentry.saturday))
                self.list.append(getConfigListEntry("Sunday", config.timerentry.sunday))
                
            #self.list.append(getConfigListEntry("StartDate", config.timerentry.startdate))
#        self.list.append(getConfigListEntry("Weekday", config.timerentry.weekday))
        
        if (config.timerentry.type.value == 0): # once
            self.list.append(getConfigListEntry("StartDate", config.timerentry.startdate))
        self.list.append(getConfigListEntry("StartTime", config.timerentry.starttime))
        if (config.timerentry.type.value == 0): # once
            self.list.append(getConfigListEntry("EndDate", config.timerentry.enddate))
        self.list.append(getConfigListEntry("EndTime", config.timerentry.endtime))
        
        self.list.append(getConfigListEntry("Channel", config.timerentry.service))        
        
        self["config"].list = self.list
        self["config"].l.setList(self.list)
        
    def newConfig(self):
        print self["config"].getCurrent()
        if self["config"].getCurrent()[0] == "TimerType":
            self.createSetup()
        if self["config"].getCurrent()[0] == "Frequency":
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
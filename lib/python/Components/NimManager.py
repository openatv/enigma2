from config import config       #global config instance

from config import configElement
from config import ConfigSubsection
from config import ConfigSlider
from config import configSelection

class nimSlot:
	def __init__(self, slotid, nimtype, name):
		self.slotid = slotid
		self.nimType = nimtype
		self.name = name

class NimManager:
	def getNimType(self, slotID):
		#FIXME get it from /proc
		if slotID == 0:
			return self.nimType["DVB-S"]
		else:
			return self.nimType["empty/unknown"]

	def getNimName(self, slotID):
		#FIXME get it from /proc
		return "Alps BSBE1"

	def getNimSocketCount(self):
		#FIXME get it from /proc
		return 2

	def getConfigPrefix(self, slotid):
		return "config.Nim" + ("A","B","C","D")[slotid] + "."
			
	def __init__(self):
		#use as enum
		self.nimType = {		"empty/unknown": -1,
												"DVB-S": 0,
												"DVB-C": 1,
												"DVB-T": 2}
												
		self.nimCount = self.getNimSocketCount()

		self.nimslots = [ ]
		x = 0
		while x < self.nimCount:
			tType = self.getNimType(x)
			tName = self.getNimName(x)
			tNim = nimSlot(x, tType, tName)
			self.nimslots.append(tNim)
			x += 1
		
		InitNimManager(self)	#init config stuff

	def nimList(self):
		list = [ ]
		for slot in self.nimslots:
			nimText = "Socket " + ("A", "B", "C", "D")[slot.slotid] + ": "
			if slot.nimType == -1:
				nimText += "empty/unknown"
			else:
				nimText += slot.name + " ("	
				nimText += ("DVB-S", "DVB-C", "DVB-T")[slot.nimType] + ")"
			list.append((nimText, slot))
		return list

def InitNimManager(nimmgr):
	config.Nims = [ConfigSubsection()] * nimmgr.nimCount

	for slot in nimmgr.nimslots:
		x = slot.slotid
		cname = nimmgr.getConfigPrefix(x)
		
		if slot.nimType == nimmgr.nimType["DVB-S"]:
			config.Nims[x].configMode = configElement(cname + "configMode",configSelection, 0, ("Simple", "Advanced"));
			config.Nims[x].diseqcMode = configElement(cname + "diseqcMode",configSelection, 0, ("Single", "Toneburst A/B", "DiSEqC A/B"));
			config.Nims[x].diseqcMode = configElement(cname + "toneburstA",configSelection, 0, ("Astra", "Hotbird"));
			config.Nims[x].diseqcMode = configElement(cname + "toneburstB",configSelection, 0, ("Astra", "Hotbird"));
			config.Nims[x].diseqcMode = configElement(cname + "diseqcA",configSelection, 0, ("Astra", "Hotbird"));
			config.Nims[x].diseqcMode = configElement(cname + "diseqcB",configSelection, 0, ("Astra", "Hotbird"));
			config.Nims[x].diseqcMode = configElement(cname + "diseqcC",configSelection, 0, ("Astra", "Hotbird"));
			config.Nims[x].diseqcMode = configElement(cname + "diseqcD",configSelection, 0, ("Astra", "Hotbird"));
		else:
			print "pls add support for this frontend type!"		

	#def nimConfig

  #def inputDevicesRepeatChanged(configElement):
  #  iDevices.setRepeat(configElement.value);

  #def inputDevicesDelayChanged(configElement):
  #  iDevices.setDelay(configElement.value);

  # this will call the "setup-val" initial
  #config.inputDevices.repeat.addNotifier(inputDevicesRepeatChanged);
  #config.inputDevices.delay.addNotifier(inputDevicesDelayChanged);

nimmanager = NimManager()

from config import config       #global config instance

from config import configElement
from config import ConfigSubsection
from config import ConfigSlider
from config import configSelection
from config import configSatlist

import xml.dom.minidom
from xml.dom import EMPTY_NAMESPACE
from skin import elementsWithTag
from Tools import XMLTools

class boundFunction:
	def __init__(self, fnc, *args):
		self.fnc = fnc
		self.args = args
	def __call__(self, *args):
		self.fnc(*self.args + args)

class nimSlot:
	def __init__(self, slotid, nimtype, name):
		self.slotid = slotid
		self.nimType = nimtype
		self.name = name

class NimManager:
	def readSatsfromFile(self):
		self.satellites = { }
		#FIXME: path ok???
		satfile = file('/etc/tuxbox/satellites.xml', 'r')
		satdom = xml.dom.minidom.parseString(satfile.read())
		satfile.close()

		for entries in elementsWithTag(satdom.childNodes, "satellites"):
			for x in elementsWithTag(entries.childNodes, "sat"):
				#print "found sat " + x.getAttribute('name') + " " + str(x.getAttribute('position'))
				tpos = x.getAttribute('position')
				tname = x.getAttribute('name')
				#tname.encode('utf8')
				self.satellites[tpos] = tname
				self.satList.append( (tname, tpos) )

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
		self.satList = [ ]										
												
		self.readSatsfromFile()										
												
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

	#callbacks for c++ config
	def nimConfigModeChanged(self, slotid, mode):
		print "nimConfigModeChanged set to " + str(mode)
	def nimDiseqcModeChanged(self, slotid, mode):
		print "nimDiseqcModeChanged set to " + str(mode)
	def nimPortAChanged(self, slotid, val):
		print "nimDiseqcA set to " + str(val)
	def nimPortBChanged(self, slotid, val):
		print "nimDiseqcB set to " + str(val)
	def nimPortCChanged(self, slotid, val):
		print "nimDiseqcC set to " + str(val)
	def nimPortDChanged(self, slotid, val):
		print "nimDiseqcD set to " + str(val)


def InitNimManager(nimmgr):
	config.Nims = [ConfigSubsection()] * nimmgr.nimCount

	def nimConfigModeChanged(slotid, configElement):
		nimmgr.nimConfigModeChanged(slotid, configElement.value)
	def nimDiseqcModeChanged(slotid, configElement):
		nimmgr.nimDiseqcModeChanged(slotid, configElement.value)
		
	def nimPortAChanged(slotid, configElement):
		nimmgr.nimPortAChanged(slotid, configElement.vals[configElement.value][1])
	def nimPortBChanged(slotid, configElement):
		nimmgr.nimPortBChanged(slotid, configElement.vals[configElement.value][1])
	def nimPortCChanged(slotid, configElement):
		nimmgr.nimPortCChanged(slotid, configElement.vals[configElement.value][1])
	def nimPortDChanged(slotid, configElement):
		nimmgr.nimPortDChanged(slotid, configElement.vals[configElement.value][1])

	for slot in nimmgr.nimslots:
		x = slot.slotid
		cname = nimmgr.getConfigPrefix(x)
		
		if slot.nimType == nimmgr.nimType["DVB-S"]:
			config.Nims[x].configMode = configElement(cname + "configMode",configSelection, 0, ("Simple", "Advanced"));
			config.Nims[x].diseqcMode = configElement(cname + "diseqcMode",configSelection, 2, ("Single", "Toneburst A/B", "DiSEqC A/B", "DiSEqC A/B/C/D"));
			config.Nims[x].diseqcA = configElement(cname + "diseqcA",configSatlist, 192, nimmgr.satList);
			config.Nims[x].diseqcB = configElement(cname + "diseqcB",configSatlist, 130, nimmgr.satList);
			config.Nims[x].diseqcC = configElement(cname + "diseqcC",configSatlist, 0, nimmgr.satList);
			config.Nims[x].diseqcD = configElement(cname + "diseqcD",configSatlist, 0, nimmgr.satList);
			
			#perhaps the instance of the slot is more useful?
			config.Nims[x].configMode.addNotifier(boundFunction(nimConfigModeChanged,x))
			config.Nims[x].diseqcMode.addNotifier(boundFunction(nimDiseqcModeChanged,x))
			config.Nims[x].diseqcA.addNotifier(boundFunction(nimPortAChanged,x))
			config.Nims[x].diseqcB.addNotifier(boundFunction(nimPortBChanged,x))
			config.Nims[x].diseqcC.addNotifier(boundFunction(nimPortCChanged,x))
			config.Nims[x].diseqcD.addNotifier(boundFunction(nimPortDChanged,x))
		else:
			print "pls add support for this frontend type!"		

nimmanager = NimManager()

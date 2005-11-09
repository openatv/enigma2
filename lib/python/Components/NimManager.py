from config import config       #global config instance

from config import configElement
from config import ConfigSubsection
from config import ConfigSlider
from config import configSelection
from config import configSequence
from config import configsequencearg
from config import configSatlist

from enigma import *

import xml.dom.minidom
from xml.dom import EMPTY_NAMESPACE
from skin import elementsWithTag
from Tools import XMLTools

from xml.sax import make_parser
from xml.sax.handler import ContentHandler

class SecConfigure:
	def addLNBSimple(self, slotid, orbpos, toneburstmode, diseqcmode, diseqcpos):
		#simple defaults
		eDVBSatelliteEquipmentControl.getInstance().addLNB()
		eDVBSatelliteEquipmentControl.getInstance().setLNBTunerMask(1 << slotid)
		eDVBSatelliteEquipmentControl.getInstance().setLNBLOFL(9750000)
		eDVBSatelliteEquipmentControl.getInstance().setLNBLOFH(10600000)
		eDVBSatelliteEquipmentControl.getInstance().setLNBThreshold(11750000)
		eDVBSatelliteEquipmentControl.getInstance().setRepeats(0)
		eDVBSatelliteEquipmentControl.getInstance().setFastDiSEqC(0)
		eDVBSatelliteEquipmentControl.getInstance().setSeqRepeat(0)
		eDVBSatelliteEquipmentControl.getInstance().setVoltageMode(0) #HV
		eDVBSatelliteEquipmentControl.getInstance().setToneMode(0)		#HILO
		eDVBSatelliteEquipmentControl.getInstance().setCommandOrder(0)
		#user values
		eDVBSatelliteEquipmentControl.getInstance().setDiSEqCMode(diseqcmode)
		eDVBSatelliteEquipmentControl.getInstance().setToneburst(toneburstmode)
		eDVBSatelliteEquipmentControl.getInstance().setCommittedCommand(diseqcpos)

		#print "set orbpos to:" + str(orbpos)
		eDVBSatelliteEquipmentControl.getInstance().addSatellite(orbpos)

	def update(self):
		eDVBSatelliteEquipmentControl.getInstance().clear()

		for slot in self.NimManager.nimslots:
			x = slot.slotid
			if slot.nimType == self.NimManager.nimType["DVB-S"]:
				print "slot: " + str(x) + " configmode: " + str(config.Nims[x].configMode.value)
				if config.Nims[x].configMode.value == 0:		#simple config
					if config.Nims[x].diseqcMode.value == 0:			#single
						self.addLNBSimple(x, int(config.Nims[x].diseqcA.vals[config.Nims[x].diseqcA.value][1]), 0, 0, 4)
					elif config.Nims[x].diseqcMode.value == 1:		#Toneburst A/B
						self.addLNBSimple(x, int(config.Nims[x].diseqcA.vals[config.Nims[x].diseqcA.value][1]), 1, 0, 4)
						self.addLNBSimple(x, int(config.Nims[x].diseqcB.vals[config.Nims[x].diseqcB.value][1]), 1, 0, 4)
					elif config.Nims[x].diseqcMode.value == 2:		#DiSEqC A/B
						self.addLNBSimple(x, int(config.Nims[x].diseqcA.vals[config.Nims[x].diseqcA.value][1]), 0, 1, 0)
						self.addLNBSimple(x, int(config.Nims[x].diseqcB.vals[config.Nims[x].diseqcB.value][1]), 0, 1, 1)
					elif config.Nims[x].diseqcMode.value == 3:		#DiSEqC A/B/C/D
						self.addLNBSimple(x, int(config.Nims[x].diseqcA.vals[config.Nims[x].diseqcA.value][1]), 0, 1, 0)
						self.addLNBSimple(x, int(config.Nims[x].diseqcB.vals[config.Nims[x].diseqcB.value][1]), 0, 1, 1)
						self.addLNBSimple(x, int(config.Nims[x].diseqcC.vals[config.Nims[x].diseqcC.value][1]), 0, 1, 2)
						self.addLNBSimple(x, int(config.Nims[x].diseqcD.vals[config.Nims[x].diseqcD.value][1]), 0, 1, 3)
						pass
					elif config.Nims[x].diseqcMode.value == 4:		#Positioner
						print "FIXME: positioner suppport"
					pass
				else:																	#advanced config
					print "FIXME add support for advanced config"
		
	def __init__(self, nimmgr):
		self.NimManager = nimmgr
		self.update()
		
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
	class parseSats(ContentHandler):
		def __init__(self, satList, satellites):
			self.isPointsElement, self.isReboundsElement = 0, 0
			self.satList = satList
			self.satellites = satellites
	
		def startElement(self, name, attrs):
			if (name == "sat"):
				#print "found sat " + attrs.get('name',"") + " " + str(attrs.get('position',""))
				tpos = attrs.get('position',"")
				tname = attrs.get('name',"")
				self.satellites[tpos] = tname
				self.satList.append( (tname, tpos) )

	def readSatsfromFile(self):
		self.satellites = { }

		print "Reading satellites.xml"
		parser = make_parser()
		satHandler = self.parseSats(self.satList, self.satellites)
		parser.setContentHandler(satHandler)
		parser.parse('/etc/tuxbox/satellites.xml')

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
	
	def getSatListForNim(self, slotid):
		#print "slotid:", slotid
		list = []
		#print "self.satellites:", self.satList[config.Nims[slotid].diseqcA.value]
		#print "diseqcA:", config.Nims[slotid].diseqcA.value
		if (config.Nims[slotid].diseqcMode.value <= 3):
			list.append(self.satList[config.Nims[slotid].diseqcA.value])
		if (0 < config.Nims[slotid].diseqcMode.value <= 3):
			list.append(self.satList[config.Nims[slotid].diseqcB.value])
		if (config.Nims[slotid].diseqcMode.value == 3):
			list.append(self.satList[config.Nims[slotid].diseqcC.value])
			list.append(self.satList[config.Nims[slotid].diseqcD.value])
		return list

	#callbacks for c++ config
	def nimConfigModeChanged(self, slotid, mode):
		#print "nimConfigModeChanged set to " + str(mode)
		pass
	def nimDiseqcModeChanged(self, slotid, mode):
		#print "nimDiseqcModeChanged set to " + str(mode)
		pass
	def nimPortAChanged(self, slotid, val):
		#print "nimDiseqcA set to " + str(val)
		pass
	def nimPortBChanged(self, slotid, val):
		#print "nimDiseqcB set to " + str(val)
		pass
	def nimPortCChanged(self, slotid, val):
		#print "nimDiseqcC set to " + str(val)
		pass
	def nimPortDChanged(self, slotid, val):
		#print "nimDiseqcD set to " + str(val)
		pass


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
			config.Nims[x].diseqcMode = configElement(cname + "diseqcMode",configSelection, 2, ("Single", "Toneburst A/B", "DiSEqC A/B", "DiSEqC A/B/C/D", "Positioner"));
			config.Nims[x].diseqcA = configElement(cname + "diseqcA",configSatlist, 192, nimmgr.satList);
			config.Nims[x].diseqcB = configElement(cname + "diseqcB",configSatlist, 130, nimmgr.satList);
			config.Nims[x].diseqcC = configElement(cname + "diseqcC",configSatlist, 0, nimmgr.satList);
			config.Nims[x].diseqcD = configElement(cname + "diseqcD",configSatlist, 0, nimmgr.satList);
			config.Nims[x].longitude = configElement(cname + "longitude",configSequence, [0,0], configsequencearg.get("FLOAT", [(0,90),(0,999)]));
			config.Nims[x].latitude = configElement(cname + "latitude",configSequence, [0,0], configsequencearg.get("FLOAT", [(0,90),(0,999)]));
			
			#perhaps the instance of the slot is more useful?
			config.Nims[x].configMode.addNotifier(boundFunction(nimConfigModeChanged,x))
			config.Nims[x].diseqcMode.addNotifier(boundFunction(nimDiseqcModeChanged,x))
			config.Nims[x].diseqcA.addNotifier(boundFunction(nimPortAChanged,x))
			config.Nims[x].diseqcB.addNotifier(boundFunction(nimPortBChanged,x))
			config.Nims[x].diseqcC.addNotifier(boundFunction(nimPortCChanged,x))
			config.Nims[x].diseqcD.addNotifier(boundFunction(nimPortDChanged,x))
		else:
			print "pls add support for this frontend type!"		
			
	nimmgr.sec = SecConfigure(nimmgr)

nimmanager = NimManager()

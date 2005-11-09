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
		sec = eDVBSatelliteEquipmentControl.getInstance()
		sec.addLNB()
		sec.setLNBTunerMask(1 << slotid)
		sec.setLNBLOFL(9750000)
		sec.setLNBLOFH(10600000)
		sec.setLNBThreshold(11750000)
		sec.setRepeats(0)
		sec.setFastDiSEqC(0)
		sec.setSeqRepeat(0)
		sec.setVoltageMode(0) #HV
		sec.setToneMode(0)		#HILO
		sec.setCommandOrder(0)
		#user values
		sec.setDiSEqCMode(diseqcmode)
		sec.setToneburst(toneburstmode)
		sec.setCommittedCommand(diseqcpos)
		#print "set orbpos to:" + str(orbpos)
		sec.addSatellite(orbpos)

	def update(self):
		eDVBSatelliteEquipmentControl.getInstance().clear()

		for slot in self.NimManager.nimslots:
			x = slot.slotid
			nim = config.Nims[x]
			if slot.nimType == self.NimManager.nimType["DVB-S"]:
				print "slot: " + str(x) + " configmode: " + str(nim.configMode.value)
				if nim.configMode.value == 0:		#simple config
					if nim.diseqcMode.value == 0:			#single
						self.addLNBSimple(x, int(nim.diseqcA.vals[nim.diseqcA.value][1]), 0, 0, 4)
					elif nim.diseqcMode.value == 1:		#Toneburst A/B
						self.addLNBSimple(x, int(nim.diseqcA.vals[nim.diseqcA.value][1]), 1, 0, 4)
						self.addLNBSimple(x, int(nim.diseqcB.vals[nim.diseqcB.value][1]), 1, 0, 4)
					elif nim.diseqcMode.value == 2:		#DiSEqC A/B
						self.addLNBSimple(x, int(nim.diseqcA.vals[nim.diseqcA.value][1]), 0, 1, 0)
						self.addLNBSimple(x, int(nim.diseqcB.vals[nim.diseqcB.value][1]), 0, 1, 1)
					elif nim.diseqcMode.value == 3:		#DiSEqC A/B/C/D
						self.addLNBSimple(x, int(nim.diseqcA.vals[nim.diseqcA.value][1]), 0, 1, 0)
						self.addLNBSimple(x, int(nim.diseqcB.vals[nim.diseqcB.value][1]), 0, 1, 1)
						self.addLNBSimple(x, int(nim.diseqcC.vals[nim.diseqcC.value][1]), 0, 1, 2)
						self.addLNBSimple(x, int(nim.diseqcD.vals[nim.diseqcD.value][1]), 0, 1, 3)
					elif nim.diseqcMode.value == 4:		#Positioner
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
		nim = config.Nims[x]
		
		if slot.nimType == nimmgr.nimType["DVB-S"]:
			nim.configMode = configElement(cname + "configMode",configSelection, 0, ("Simple", "Advanced"));
			nim.diseqcMode = configElement(cname + "diseqcMode",configSelection, 2, ("Single", "Toneburst A/B", "DiSEqC A/B", "DiSEqC A/B/C/D", "Positioner"));
			nim.diseqcA = configElement(cname + "diseqcA",configSatlist, 192, nimmgr.satList);
			nim.diseqcB = configElement(cname + "diseqcB",configSatlist, 130, nimmgr.satList);
			nim.diseqcC = configElement(cname + "diseqcC",configSatlist, 0, nimmgr.satList);
			nim.diseqcD = configElement(cname + "diseqcD",configSatlist, 0, nimmgr.satList);
			nim.longitude = configElement(cname + "longitude",configSequence, [0,0], configsequencearg.get("FLOAT", [(0,90),(0,999)]));
			nim.latitude = configElement(cname + "latitude",configSequence, [0,0], configsequencearg.get("FLOAT", [(0,90),(0,999)]));
			
			#perhaps the instance of the slot is more useful?
			nim.configMode.addNotifier(boundFunction(nimConfigModeChanged,x))
			nim.diseqcMode.addNotifier(boundFunction(nimDiseqcModeChanged,x))
			nim.diseqcA.addNotifier(boundFunction(nimPortAChanged,x))
			nim.diseqcB.addNotifier(boundFunction(nimPortBChanged,x))
			nim.diseqcC.addNotifier(boundFunction(nimPortCChanged,x))
			nim.diseqcD.addNotifier(boundFunction(nimPortDChanged,x))
		else:
			print "pls add support for this frontend type!"		
			
	nimmgr.sec = SecConfigure(nimmgr)

nimmanager = NimManager()

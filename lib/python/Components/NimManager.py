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

from Tools.BoundFunction import boundFunction

def tryOpen(filename):
	try:
		procFile = open(filename)
	except IOError:
		return ""
	return procFile

class SecConfigure:
	def addLNBSimple(self, slotid, diseqcmode, toneburstmode = 0, diseqcpos = 0, orbpos = 0, longitude = 0, latitude = 0, loDirection = 0, laDirection = 0):
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

		if (0 <= diseqcmode < 3):
			sec.addSatellite(orbpos)
			self.satList.append(orbpos)
		elif (diseqcmode == 3): # diseqc 1.2
			sec.setLatitude(latitude)
			sec.setLaDirection(laDirection)
			sec.setLongitude(longitude)
			sec.setLoDirection(loDirection)
			sec.setUseInputpower(True)
			sec.setInputpowerDelta(50)
			
			for x in self.NimManager.satList:
				print "Add sat " + str(x[1])
				sec.addSatellite(int(x[1]))
				sec.setVoltageMode(0)
				sec.setToneMode(0)
				self.satList.append(int(x[1]))
				

	def linkNIMs(self, nim1, nim2):
		eDVBSatelliteEquipmentControl.getInstance().setTunerLinked(nim1, nim2)
		
	def getSatList(self):
		return self.satList

	def update(self):
		eDVBSatelliteEquipmentControl.getInstance().clear()
		
		self.satList = []

		for slot in self.NimManager.nimslots:
			x = slot.slotid
			nim = config.Nims[x]
			if slot.nimType == self.NimManager.nimType["DVB-S"]:
				print "slot: " + str(x) + " configmode: " + str(nim.configMode.value)
				if nim.configMode.value == 1:
					self.linkNIMs(x, nim.linkedTo.value)
					nim = config.Nims[nim.linkedTo.value]
				if nim.configMode.value == 0:		#simple config
					if nim.diseqcMode.value == 0:			#single
						self.addLNBSimple(slotid = x, orbpos = int(nim.diseqcA.vals[nim.diseqcA.value][1]), toneburstmode = 0, diseqcmode = 0, diseqcpos = 4)
					elif nim.diseqcMode.value == 1:		#Toneburst A/B
						self.addLNBSimple(slotid = x, orbpos = int(nim.diseqcA.vals[nim.diseqcA.value][1]), toneburstmode = 1, diseqcmode = 0, diseqcpos = 4)
						self.addLNBSimple(slotid = x, orbpos = int(nim.diseqcB.vals[nim.diseqcB.value][1]), toneburstmode = 1, diseqcmode = 0, diseqcpos = 4)
					elif nim.diseqcMode.value == 2:		#DiSEqC A/B
						self.addLNBSimple(slotid = x, orbpos = int(nim.diseqcA.vals[nim.diseqcA.value][1]), toneburstmode = 0, diseqcmode = 1, diseqcpos = 0)
						self.addLNBSimple(slotid = x, orbpos = int(nim.diseqcB.vals[nim.diseqcB.value][1]), toneburstmode = 0, diseqcmode = 1, diseqcpos = 1)
					elif nim.diseqcMode.value == 3:		#DiSEqC A/B/C/D
						self.addLNBSimple(slotid = x, orbpos = int(nim.diseqcA.vals[nim.diseqcA.value][1]), toneburstmode = 0, diseqcmode = 1, diseqcpos = 0)
						self.addLNBSimple(slotid = x, orbpos = int(nim.diseqcB.vals[nim.diseqcB.value][1]), toneburstmode = 0, diseqcmode = 1, diseqcpos = 1)
						self.addLNBSimple(slotid = x, orbpos = int(nim.diseqcC.vals[nim.diseqcC.value][1]), toneburstmode = 0, diseqcmode = 1, diseqcpos = 2)
						self.addLNBSimple(slotid = x, orbpos = int(nim.diseqcD.vals[nim.diseqcD.value][1]), toneburstmode = 0, diseqcmode = 1, diseqcpos = 3)
					elif nim.diseqcMode.value == 4:		#Positioner
						self.addLNBSimple(slotid = x, diseqcmode = 3, longitude = float(str(nim.longitude.value[0]) + "." + str(nim.longitude.value[1])), loDirection = nim.longitudeOrientation.value - 2, latitude = float(str(nim.latitude.value[0]) + "." + str(nim.latitude.value[1])), laDirection = nim.latitudeOrientation.value)
					pass
				else:																	#advanced config
					print "FIXME add support for advanced config"
		
	def __init__(self, nimmgr):
		self.NimManager = nimmgr
		self.update()
		
class nimSlot:
	def __init__(self, slotid, nimtype, name):
		self.slotid = slotid
		self.nimType = nimtype
		self.name = name

class NimManager:
	class parseSats(ContentHandler):
		def __init__(self, satList, satellites, transponders):
			self.isPointsElement, self.isReboundsElement = 0, 0
			self.satList = satList
			self.satellites = satellites
			self.transponders = transponders
	
		def startElement(self, name, attrs):
			if (name == "sat"):
				#print "found sat " + attrs.get('name',"") + " " + str(attrs.get('position',""))
				tpos = attrs.get('position',"")
				tname = attrs.get('name',"")
				self.satellites[tpos] = tname
				self.satList.append( (tname, tpos) )
				self.parsedSat = int(tpos)
			elif (name == "transponder"):
				freq = int(attrs.get('frequency',""))
				sr = int(attrs.get('symbol_rate',""))
				pol = int(attrs.get('polarization',""))
				fec = int(attrs.get('fec_inner',""))
				if self.parsedSat in self.transponders:
					pass
				else:
					self.transponders[self.parsedSat] = [ ]

				self.transponders[self.parsedSat].append((0, freq, sr, pol, fec))

	class parseCables(ContentHandler):
		def __init__(self, cablesList, transponders):
			self.isPointsElement, self.isReboundsElement = 0, 0
			self.cablesList = cablesList
			self.transponders = transponders
	
		def startElement(self, name, attrs):
			if (name == "cable"):
				#print "found sat " + attrs.get('name',"") + " " + str(attrs.get('position',""))
				tname = attrs.get('name',"")
				self.cablesList.append(str(tname))
				self.parsedCab = str(tname)
			elif (name == "transponder"):
				freq = int(attrs.get('frequency',""))
				sr = int(attrs.get('symbol_rate',""))
				mod = int(attrs.get('modulation',""))
				fec = int(attrs.get('fec_inner',""))
				if self.parsedCab in self.transponders:
					pass
				else:
					self.transponders[self.parsedCab] = [ ]

				self.transponders[self.parsedCab].append((0, freq, sr, mod, fec))

	class parseTerrestrials(ContentHandler):
		def __init__(self, terrestrialsList, transponders):
			self.isPointsElement, self.isReboundsElement = 0, 0
			self.terrestrialsList = terrestrialsList
			self.transponders = transponders
	
		def startElement(self, name, attrs):
			if (name == "terrestrial"):
				#print "found sat " + attrs.get('name',"") + " " + str(attrs.get('position',""))
				tname = attrs.get('name',"")
				tflags = attrs.get('flags',"")
				self.terrestrialsList.append((tname, tflags))
				self.parsedTer = str(tname)
			elif (name == "transponder"):
				# TODO finish this!
				freq = int(attrs.get('centre_frequency',""))
				bw = int(attrs.get('bandwidth',""))
				const = int(attrs.get('constellation',""))
				crh = int(attrs.get('code_rate_hp',""))
				crl = int(attrs.get('code_rate_lp',""))
				guard = int(attrs.get('guard_interval',""))
				transm = int(attrs.get('transmission_mode',""))
				hierarchy = int(attrs.get('hierarchy_information',""))
				inv = int(attrs.get('inversion',""))
				if self.parsedTer in self.transponders:
					pass
				else:
					self.transponders[self.parsedTer] = [ ]

				self.transponders[self.parsedTer].append((0, freq, bw, const, crh, crl, guard, transm, hierarchy, inv))

	def getTransponders(self, pos):
		return self.transponders[pos]

	def getConfiguredSats(self):
		return self.sec.getSatList()

	def getSatDescription(self, pos):
		return self.satellites[str(pos)]

	def readSatsfromFile(self):
		self.satellites = { }
		self.transponders = { }
		self.transponderscable = { }
		self.transpondersterrestrial = { }		
		
		parser = make_parser()
		if (self.hasNimType(self.nimType["DVB-S"])):
			print "Reading satellites.xml"
			satHandler = self.parseSats(self.satList, self.satellites, self.transponders)
			parser.setContentHandler(satHandler)
			parser.parse('/etc/tuxbox/satellites.xml')
		if (self.hasNimType(self.nimType["DVB-C"])):
			print "Reading cables.xml"
			cabHandler = self.parseCables(self.cablesList, self.transponderscable)
			parser.setContentHandler(cabHandler)
			parser.parse('/etc/tuxbox/cables.xml')

		if (self.hasNimType(self.nimType["DVB-T"])):
			print "Reading terrestrial.xml"
			terHandler = self.parseTerrestrials(self.terrestrialsList, self.transpondersterrestrial)
			parser.setContentHandler(terHandler)
			parser.parse('/etc/tuxbox/terrestrial.xml')
		
	def parseProc(self):
		self.nimTypes = {}
		self.nimNames = {}		
		self.nimSocketCount = 0
		nimfile = tryOpen("/proc/bus/nim_sockets")

		if nimfile == "":
				return self.nimType["empty/unknown"]
			
		lastsocket = -1

		while 1:		
			line = nimfile.readline()
			if line == "":
				break
			if line.strip().startswith("NIM Socket"):
				parts = line.strip().split(" ")
				id = int(parts[2][:1])
				lastsocket = int(id)
				self.nimSocketCount += 1
			elif line.strip().startswith("Type:"):
				self.nimTypes[lastsocket] = str(line.strip()[6:])
			elif line.strip().startswith("Name:"):
				self.nimNames[lastsocket] = str(line.strip()[6:])
			elif line.strip().startswith("empty"):
				self.nimNames[lastsocket] = _("N/A")
				self.nimTypes[lastsocket] = "empty/unknown"

		nimfile.close()

	def getNimType(self, slotID):
		if slotID >= self.nimCount:
			return "empty/unknown"
		else:	
			return self.nimType[self.nimTypes[slotID]]
			
	def getNimName(self, slotID):
		return self.nimNames[slotID]

	def getNimSocketCount(self):
		return self.nimSocketCount
	
	def hasNimType(self, chktype):
		for id, type in self.nimTypes.items():
			if (chktype == self.nimType[str(type)]):
				return True
		return False
	
	def getNimListOfType(self, type, exception = -1):
		list = []
		for x in self.nimslots:
			if ((x.nimType == type) and (x.slotid != exception)):
				list.append(x.slotid)
		return list

	def getConfigPrefix(self, slotid):
		return "config.Nim" + ("A","B","C","D")[slotid] + "."
			
	def __init__(self):
		#use as enum
		self.nimType = {		"empty/unknown": -1,
												"DVB-S": 0,
												"DVB-C": 1,
												"DVB-T": 2}
		self.satList = [ ]
		self.cablesList = []
		self.terrestrialsList = []
												
		self.parseProc()

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
			nimText = _("Socket ") + ("A", "B", "C", "D")[slot.slotid] + ": "
			if slot.nimType == -1:
				nimText += _("empty/unknown")
			else:
				nimText += slot.name + " ("	
				nimText += ("DVB-S", "DVB-C", "DVB-T")[slot.nimType] + ")"
			list.append((nimText, slot))
		return list
	
	def getSatListForNim(self, slotid):
		list = []
		if (self.getNimType(slotid) != self.nimType["empty/unknown"]):
			#print "slotid:", slotid
			
			#print "self.satellites:", self.satList[config.Nims[slotid].diseqcA.value]
			#print "diseqcA:", config.Nims[slotid].diseqcA.value
			if (config.Nims[slotid].diseqcMode.value <= 3):
				list.append(self.satList[config.Nims[slotid].diseqcA.value])
			if (0 < config.Nims[slotid].diseqcMode.value <= 3):
				list.append(self.satList[config.Nims[slotid].diseqcB.value])
			if (config.Nims[slotid].diseqcMode.value == 3):
				list.append(self.satList[config.Nims[slotid].diseqcC.value])
				list.append(self.satList[config.Nims[slotid].diseqcD.value])
			if (config.Nims[slotid].diseqcMode.value == 4):
				for x in self.satList:
					list.append(x)
		return list

	#callbacks for c++ config
	def nimConfigModeChanged(self, slotid, mode):
		if (mode != 1): # not linked
			print "Unlinking slot " + str(slotid)
			# TODO call c++ to unlink nim in slot slotid
		if (mode == 1): # linked
			pass
			#FIXME!!!
			#if (len(self.getNimListOfType(self.nimType["DVB-S"], slotid)) > 0):
			#	print "Linking slot " + str(slotid) + " to " + str(nimmgr.getConfigPrefix(slotid).value)
			# TODO call c++ to link nim in slot slotid with nim in slot nimmgr.getConfigPrefix(slotid).value
	def nimLinkedToChanged(self, slotid, val):
		print "Linking slot " + str(slotid) + " to " + str(val)

	def nimDiseqcModeChanged(self, slotid, mode):
		#print "nimDiseqcModeChanged set to " + str(mode)
		pass
	def nimPortAChanged(self, slotid, val):
		#print "nimDiseqcA set to " + str(slotid) + " val:" + str(val)
		pass
	def nimPortBChanged(self, slotid, val):
		#print "nimDiseqcA set to " + str(slotid) + " val:" + str(val)
		#print "nimDiseqcB set to " + str(val)
		pass
	def nimPortCChanged(self, slotid, val):
		#print "nimDiseqcC set to " + str(val)
		pass
	def nimPortDChanged(self, slotid, val):
		#print "nimDiseqcD set to " + str(val)
		pass

def InitNimManager(nimmgr):
	config.Nims = []
	for x in range(nimmgr.nimCount):
		config.Nims.append(ConfigSubsection())
		
	def nimConfigModeChanged(slotid, configElement):
		nimmgr.nimConfigModeChanged(slotid, configElement.value)
	def nimLinkedToChanged(slotid, configElement):
		nimmgr.nimLinkedToChanged(slotid, configElement.value)
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
			nim.configMode = configElement(cname + "configMode", configSelection, 0, (_("Simple"), _("Loopthrough to Socket A"))) # "Advanced"));
			
			#important - check if just the 2nd one is LT only and the first one is DVB-S
			if nim.configMode.value == 1: #linked
				if x == 0:										#first one can never be linked to anything
					nim.configMode.value = 0		#reset to simple
					nim.configMode.save()
				else:
					#FIXME: make it better
					for y in nimmgr.nimslots:
						if y.slotid == 0:
							if y.nimType != nimmgr.nimType["DVB-S"]:
								nim.configMode.value = 0		#reset to simple
								nim.configMode.save()

			nim.diseqcMode = configElement(cname + "diseqcMode", configSelection, 2, (_("Single"), _("Toneburst A/B"), _("DiSEqC A/B"), _("DiSEqC A/B/C/D"), _("Positioner")));
			nim.diseqcA = configElement(cname + "diseqcA", configSatlist, 192, nimmgr.satList);
			nim.diseqcB = configElement(cname + "diseqcB", configSatlist, 130, nimmgr.satList);
			nim.diseqcC = configElement(cname + "diseqcC", configSatlist, 0, nimmgr.satList);
			nim.diseqcD = configElement(cname + "diseqcD", configSatlist, 0, nimmgr.satList);
			nim.positionerMode = configElement(cname + "positionerMode", configSelection, 0, (_("USALS"), _("manual")));
			nim.longitude = configElement(cname + "longitude", configSequence, [5,100], configsequencearg.get("FLOAT", [(0,100),(0,999)]));
			nim.longitudeOrientation = configElement(cname + "longitudeOrientation", configSelection, 0, (_("East"), _("West")))
			nim.latitude = configElement(cname + "latitude", configSequence, [50,767], configsequencearg.get("FLOAT", [(0,100),(0,999)]));
			nim.latitudeOrientation = configElement(cname + "latitudeOrientation", configSelection, 0, (_("North"), _("South")))
			satNimList = nimmgr.getNimListOfType(nimmgr.nimType["DVB-S"], slot.slotid)
			satNimListNames = []
			for x in satNimList:
				satNimListNames.append(_("Slot ") + ("A", "B", "C", "D")[x] + ": " + nimmgr.getNimName(x))
			nim.linkedTo = configElement(cname + "linkedTo", configSelection, 0, satNimListNames);
			
			#perhaps the instance of the slot is more useful?
			nim.configMode.addNotifier(boundFunction(nimConfigModeChanged,x))
			nim.diseqcMode.addNotifier(boundFunction(nimDiseqcModeChanged,x))
			nim.diseqcA.addNotifier(boundFunction(nimPortAChanged,int(x)))
			nim.diseqcB.addNotifier(boundFunction(nimPortBChanged,x))
			nim.diseqcC.addNotifier(boundFunction(nimPortCChanged,x))
			nim.diseqcD.addNotifier(boundFunction(nimPortDChanged,x))
			nim.linkedTo.addNotifier(boundFunction(nimLinkedToChanged,x))
		elif slot.nimType == nimmgr.nimType["DVB-C"]:
			nim.cable = configElement(cname + "cable", configSelection, 0, nimmgr.cablesList);
		elif slot.nimType == nimmgr.nimType["DVB-T"]:
			nim.cable = configElement(cname + "terrestrial", configSelection, 0, nimmgr.terrestrialsList);
		else:
			print "pls add support for this frontend type!"		

	nimmgr.sec = SecConfigure(nimmgr)

nimmanager = NimManager()

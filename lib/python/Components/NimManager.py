from config import config       #global config instance

from config import configElement
from config import ConfigSubsection
from config import configSelection
from config import currentConfigSelectionElement
from config import getConfigSelectionElement
from config import configSequence
from config import configsequencearg
from config import configSatlist

from enigma import eDVBSatelliteEquipmentControl, \
	eDVBSatelliteLNBParameters as lnbParam, \
	eDVBSatelliteDiseqcParameters as diseqcParam, \
	eDVBSatelliteSwitchParameters as switchParam, \
	eDVBSatelliteRotorParameters as rotorParam

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
	def addLNBSimple(self, sec, slotid, diseqcmode, toneburstmode = 0, diseqcpos = 0, orbpos = 0, longitude = 0, latitude = 0, loDirection = 0, laDirection = 0):
		#simple defaults
		sec.addLNB()
		tunermask = 1 << slotid
		if self.equal.has_key(slotid):
			tunermask |= (1 << self.equal[slotid])
		elif self.linked.has_key(slotid):
			tunermask |= (1 << self.linked[slotid])
		sec.setLNBTunerMask(tunermask)
		sec.setLNBLOFL(9750000)
		sec.setLNBLOFH(10600000)
		sec.setLNBThreshold(11700000)
		sec.setLNBIncreasedVoltage(lnbParam.OFF)
		sec.setRepeats(0)
		sec.setFastDiSEqC(0)
		sec.setSeqRepeat(0)
		sec.setVoltageMode(switchParam.HV)
		sec.setToneMode(switchParam.HILO)
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
			if self.satposdepends.has_key(slotid):
				tunermask |= (1 << self.satposdepends[slotid])
				sec.setLNBTunerMask(tunermask)
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
				sec.setRotorPosNum(0) # USALS
				self.satList.append(int(x[1]))

	def setSatposDepends(self, sec, nim1, nim2):
		print "tuner", nim1, "depends on satpos of", nim2
		sec.setTunerDepends(nim1, nim2)

	def linkNIMs(self, sec, nim1, nim2):
		print "link tuner", nim1, "to tuner", nim2
		sec.setTunerLinked(nim1, nim2)

	def getSatList(self):
		return self.satList

	def update(self):
		sec = eDVBSatelliteEquipmentControl.getInstance()
		sec.clear() ## this do unlinking NIMs too !!
		print "sec config cleared"
		self.satList = []

		self.linked = { }
		self.satposdepends = { }
		self.equal = { }
		for slot in self.NimManager.nimslots:
			x = slot.slotid
			nim = config.Nims[x]
			if slot.nimType == self.NimManager.nimType["DVB-S"]:
				if currentConfigSelectionElement(nim.configMode) == "equal":
					self.equal[nim.equalTo.value]=x
				if currentConfigSelectionElement(nim.configMode) == "loopthrough":
					self.linkNIMs(sec, x, nim.linkedTo.value)
					self.linked[nim.linkedTo.value]=x
				elif currentConfigSelectionElement(nim.configMode) == "satposdepends":
					self.setSatposDepends(sec, x, nim.satposDependsTo.value)
					self.satposdepends[nim.satposDependsTo.value]=x

		for slot in self.NimManager.nimslots:
			x = slot.slotid
			nim = config.Nims[x]
			if slot.nimType == self.NimManager.nimType["DVB-S"]:
				print "slot: " + str(x) + " configmode: " + str(nim.configMode.value)
				if currentConfigSelectionElement(nim.configMode) in [ "loopthrough", "satposdepends", "equal", "nothing" ]:
					pass
				elif currentConfigSelectionElement(nim.configMode) == "simple":		#simple config
					if currentConfigSelectionElement(nim.diseqcMode) == "single":			#single
						self.addLNBSimple(sec, slotid = x, orbpos = int(nim.diseqcA.vals[nim.diseqcA.value][1]), toneburstmode = diseqcParam.NO, diseqcmode = diseqcParam.NONE, diseqcpos = diseqcParam.SENDNO)
					elif currentConfigSelectionElement(nim.diseqcMode) == "toneburst_a_b":		#Toneburst A/B
						self.addLNBSimple(sec, slotid = x, orbpos = int(nim.diseqcA.vals[nim.diseqcA.value][1]), toneburstmode = diseqcParam.A, diseqcmode = diseqcParam.V1_0, diseqcpos = diseqcParam.SENDNO)
						self.addLNBSimple(sec, slotid = x, orbpos = int(nim.diseqcB.vals[nim.diseqcB.value][1]), toneburstmode = diseqcParam.B, diseqcmode = diseqcParam.V1_0, diseqcpos = diseqcParam.SENDNO)
					elif currentConfigSelectionElement(nim.diseqcMode) == "diseqc_a_b":		#DiSEqC A/B
						self.addLNBSimple(sec, slotid = x, orbpos = int(nim.diseqcA.vals[nim.diseqcA.value][1]), toneburstmode = diseqcParam.NO, diseqcmode = diseqcParam.V1_0, diseqcpos = diseqcParam.AA)
						self.addLNBSimple(sec, slotid = x, orbpos = int(nim.diseqcB.vals[nim.diseqcB.value][1]), toneburstmode = diseqcParam.NO, diseqcmode = diseqcParam.V1_0, diseqcpos = diseqcParam.AB)
					elif currentConfigSelectionElement(nim.diseqcMode) == "diseqc_a_b_c_d":		#DiSEqC A/B/C/D
						self.addLNBSimple(sec, slotid = x, orbpos = int(nim.diseqcA.vals[nim.diseqcA.value][1]), toneburstmode = diseqcParam.NO, diseqcmode = diseqcParam.V1_0, diseqcpos = diseqcParam.AA)
						self.addLNBSimple(sec, slotid = x, orbpos = int(nim.diseqcB.vals[nim.diseqcB.value][1]), toneburstmode = diseqcParam.NO, diseqcmode = diseqcParam.V1_0, diseqcpos = diseqcParam.AB)
						self.addLNBSimple(sec, slotid = x, orbpos = int(nim.diseqcC.vals[nim.diseqcC.value][1]), toneburstmode = diseqcParam.NO, diseqcmode = diseqcParam.V1_0, diseqcpos = diseqcParam.BA)
						self.addLNBSimple(sec, slotid = x, orbpos = int(nim.diseqcD.vals[nim.diseqcD.value][1]), toneburstmode = diseqcParam.NO, diseqcmode = diseqcParam.V1_0, diseqcpos = diseqcParam.BB)
					elif currentConfigSelectionElement(nim.diseqcMode) == "positioner":		#Positioner
						if currentConfigSelectionElement(nim.latitudeOrientation) == "north":
							laValue = rotorParam.NORTH
						else:
							laValue = rotorParam.SOUTH
						if currentConfigSelectionElement(nim.longitudeOrientation) == "east":
							loValue = rotorParam.EAST
						else:
							loValue = rotorParam.WEST
						self.addLNBSimple(sec, slotid = x, diseqcmode = 3,
							longitude = configsequencearg.getFloat(nim.longitude),
							loDirection = loValue,
							latitude = configsequencearg.getFloat(nim.latitude),
							laDirection = laValue)
				elif currentConfigSelectionElement(nim.configMode) == "advanced": #advanced config
					self.updateAdvanced(sec, x)
		print "sec config completed"

	def updateAdvanced(self, sec, slotid):
		lnbSat = {}
		for x in range(1,33):
			lnbSat[x] = []
		for x in self.NimManager.satList:
			lnb = config.Nims[slotid].advanced.sat[x[1]].lnb.value
			if lnb != 0:
				print "add", x[1], "to", lnb
				lnbSat[lnb].append(x[1])
		for x in range(1,33):
			if len(lnbSat[x]) > 0:
				currLnb = config.Nims[slotid].advanced.lnb[x]
				sec.addLNB()

				tunermask = 1 << slotid
				if self.equal.has_key(slotid):
					tunermask |= (1 << self.equal[slotid])
				elif self.linked.has_key(slotid):
					tunermask |= (1 << self.linked[slotid])

				if currentConfigSelectionElement(currLnb.lof) == "universal_lnb":
					sec.setLNBLOFL(9750000)
					sec.setLNBLOFH(10600000)
					sec.setLNBThreshold(11700000)
				elif currentConfigSelectionElement(currLnb.lof) == "c_band":
					sec.setLNBLOFL(5150000)
					sec.setLNBLOFH(5150000)
					sec.setLNBThreshold(5150000)
				elif currentConfigSelectionElement(currLnb.lof) == "user_defined":
					sec.setLNBLOFL(currLnb.lofl.value[0] * 1000)
					sec.setLNBLOFH(currLnb.lofh.value[0] * 1000)
					sec.setLNBThreshold(currLnb.threshold.value[0] * 1000)
					
				if currentConfigSelectionElement(currLnb.output_12v) == "0V":
					pass # nyi in drivers
				elif currentConfigSelectionElement(currLnb.output_12v) == "12V":
					pass # nyi in drivers
					
				if currentConfigSelectionElement(currLnb.increased_voltage) == "yes":
					sec.setLNBIncreasedVoltage(lnbParam.ON)
				else:
					sec.setLNBIncreasedVoltage(lnbParam.OFF)
					
				if currentConfigSelectionElement(currLnb.diseqcMode) == "none":
					sec.setDiSEqCMode(diseqcParam.NONE)
				elif currentConfigSelectionElement(currLnb.diseqcMode) == "1_0":
					sec.setDiSEqCMode(diseqcParam.V1_0)
				elif currentConfigSelectionElement(currLnb.diseqcMode) == "1_1":
					sec.setDiSEqCMode(diseqcParam.V1_1)
				elif currentConfigSelectionElement(currLnb.diseqcMode) == "1_2":
					sec.setDiSEqCMode(diseqcParam.V1_2)

					if self.satposdepends.has_key(slotid):  # only useable with rotors
						tunermask |= (1 << self.satposdepends[slotid])

				if currentConfigSelectionElement(currLnb.diseqcMode) != "none":
					if currentConfigSelectionElement(currLnb.toneburst) == "none":
						sec.setToneburst(diseqcParam.NO)
					elif currentConfigSelectionElement(currLnb.toneburst) == "A":
						sec.setToneburst(diseqcParam.A)
					elif currentConfigSelectionElement(currLnb.toneburst) == "B":
						sec.setToneburst(diseqcParam.B)
						
					if currentConfigSelectionElement(currLnb.commitedDiseqcCommand) == "none":
						sec.setCommittedCommand(diseqcParam.SENDNO)
					elif currentConfigSelectionElement(currLnb.commitedDiseqcCommand) == "AA":
						sec.setCommittedCommand(diseqcParam.AA)
					elif currentConfigSelectionElement(currLnb.commitedDiseqcCommand) == "AB":
						sec.setCommittedCommand(diseqcParam.AB)
					elif currentConfigSelectionElement(currLnb.commitedDiseqcCommand) == "BA":
						sec.setCommittedCommand(diseqcParam.BA)
					elif currentConfigSelectionElement(currLnb.commitedDiseqcCommand) == "BB":
						sec.setCommittedCommand(diseqcParam.BB)
					else:
						sec.setCommittedCommand(long(currentConfigSelectionElement(currLnb.commitedDiseqcCommand)))

					if currentConfigSelectionElement(currLnb.fastDiseqc) == "yes":
						sec.setFastDiSEqC(True)
					else:
						sec.setFastDiSEqC(False)
						
					if currentConfigSelectionElement(currLnb.sequenceRepeat) == "yes":
						sec.setSeqRepeat(True)
					else:
						sec.setSeqRepeat(False)
						
					if currentConfigSelectionElement(currLnb.diseqcMode) == "1_0":
						currCO = currLnb.commandOrder1_0.value
					else:
						currCO = currLnb.commandOrder.value
						
						if currLnb.uncommittedDiseqcCommand.value > 0:
							sec.setUncommittedCommand(0xF0|(currLnb.uncommittedDiseqcCommand.value-1))
						else:
							sec.setUncommittedCommand(0) # SENDNO
						
						if currentConfigSelectionElement(currLnb.diseqcRepeats) == "none":
							sec.setRepeats(0)
						elif currentConfigSelectionElement(currLnb.diseqcRepeats) == "One":
							sec.setRepeats(1)
						elif currentConfigSelectionElement(currLnb.diseqcRepeats) == "Two":
							sec.setRepeats(2)
						elif currentConfigSelectionElement(currLnb.diseqcRepeats) == "Three":
							sec.setRepeats(3)
						
					setCommandOrder=False
					if currCO == 0: # committed, toneburst
						setCommandOrder=True
					elif currCO == 1: # toneburst, committed
						setCommandOrder=True
					elif currCO == 2: # committed, uncommitted, toneburst
						setCommandOrder=True
					elif currCO == 3: # toneburst, committed, uncommitted
						setCommandOrder=True
					elif currCO == 4: # uncommitted, committed, toneburst
						setCommandOrder=True
					elif currCO == 5: # toneburst, uncommitted, commmitted
						setCommandOrder=True
					if setCommandOrder:
						sec.setCommandOrder(currCO)
						
				if currentConfigSelectionElement(currLnb.diseqcMode) == "1_2":
					latitude = configsequencearg.getFloat(currLnb.latitude)
					sec.setLatitude(latitude)
					longitude = configsequencearg.getFloat(currLnb.longitude)
					sec.setLongitude(longitude)
					if currentConfigSelectionElement(currLnb.latitudeOrientation) == "north":
						sec.setLaDirection(rotorParam.NORTH)
					else:
						sec.setLaDirection(rotorParam.SOUTH)
					if currentConfigSelectionElement(currLnb.longitudeOrientation) == "east":
						sec.setLoDirection(rotorParam.EAST)
					else:
						sec.setLoDirection(rotorParam.WEST)
						
				if currentConfigSelectionElement(currLnb.powerMeasurement) == "yes":
					sec.setUseInputpower(True)
					sec.setInputpowerDelta(currLnb.powerThreshold.value[0])
				else:
					sec.setUseInputpower(False)

				sec.setLNBTunerMask(tunermask)

				# finally add the orbital positions
				for y in lnbSat[x]:
					sec.addSatellite(y)
					currSat = config.Nims[slotid].advanced.sat[y]
					if currentConfigSelectionElement(currSat.voltage) == "polarization":
						sec.setVoltageMode(switchParam.HV)
					elif currentConfigSelectionElement(currSat.voltage) == "13V":
						sec.setVoltageMode(switchParam._14V)
					elif currentConfigSelectionElement(currSat.voltage) == "18V":
						sec.setVoltageMode(switchParam._18V)
						
					if currentConfigSelectionElement(currSat.tonemode) == "band":
						sec.setToneMode(switchParam.HILO)
					elif currentConfigSelectionElement(currSat.tonemode) == "on":
						sec.setToneMode(switchParam.ON)
					elif currentConfigSelectionElement(currSat.tonemode) == "off":
						sec.setToneMode(switchParam.OFF)
						
					if  currentConfigSelectionElement(currSat.usals) == "no":
						sec.setRotorPosNum(currSat.rotorposition.value[0])
					else:
						sec.setRotorPosNum(0) #USALS

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
				tpos = int(attrs.get('position',""))
				if tpos < 0:
					tpos = 3600 + tpos
				tname = attrs.get('name',"").encode("UTF-8")
				self.satellites[tpos] = tname
				self.satList.append( (tname, tpos) )
				self.parsedSat = int(tpos)
			elif (name == "transponder"):
				system = int(attrs.get('system',"0"))
				freq = int(attrs.get('frequency',""))
				sr = int(attrs.get('symbol_rate',""))
				pol = int(attrs.get('polarization',""))
				fec = int(attrs.get('fec_inner',""))
				if self.parsedSat in self.transponders:
					pass
				else:
					self.transponders[self.parsedSat] = [ ]

				self.transponders[self.parsedSat].append((0, freq, sr, pol, fec, system))

	class parseCables(ContentHandler):
		def __init__(self, cablesList, transponders):
			self.isPointsElement, self.isReboundsElement = 0, 0
			self.cablesList = cablesList
			self.transponders = transponders
	
		def startElement(self, name, attrs):
			if (name == "cable"):
				#print "found sat " + attrs.get('name',"") + " " + str(attrs.get('position',""))
				tname = attrs.get('name',"").encode("UTF-8")
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
				self.transponders[self.parsedCab].append((1, freq, sr, mod, fec))

	class parseTerrestrials(ContentHandler):
		def __init__(self, terrestrialsList, transponders):
			self.isPointsElement, self.isReboundsElement = 0, 0
			self.terrestrialsList = terrestrialsList
			self.transponders = transponders
	
		def startElement(self, name, attrs):
			if (name == "terrestrial"):
				#print "found sat " + attrs.get('name',"") + " " + str(attrs.get('position',""))
				tname = attrs.get('name',"").encode("UTF-8")
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

				self.transponders[self.parsedTer].append((2, freq, bw, const, crh, crl, guard, transm, hierarchy, inv))

	def getTransponders(self, pos):
		if self.transponders.has_key(pos):
			return self.transponders[pos]
		else:
			return []

	def getTranspondersCable(self, cable):
		return self.transponderscable[cable]

	def getTranspondersTerrestrial(self, region):
		return self.transpondersterrestrial[region]
	
	def getCableDescription(self, nim):
		return self.cablesList[config.Nims[nim].cable.value]

	def getTerrestrialDescription(self, nim):
		return self.terrestrialsList[config.Nims[nim].terrestrial.value][0]

	def getTerrestrialFlags(self, nim):
		return self.terrestrialsList[config.Nims[nim].terrestrial.value][1]

	def getConfiguredSats(self):
		return self.sec.getSatList()

	def getSatDescription(self, pos):
		return self.satellites[pos]

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
				#self.nimTypes[lastsocket] = str("DVB-T")
			elif line.strip().startswith("Name:"):
				self.nimNames[lastsocket] = str(line.strip()[6:])
			elif line.strip().startswith("empty"):
				self.nimNames[lastsocket] = _("N/A")
				self.nimTypes[lastsocket] = "empty/unknown"

		nimfile.close()

	def getNimType(self, slotID):
		if slotID >= self.nimCount:
			return self.nimType["empty/unknown"]
		else:	
			return self.nimType[self.nimTypes[slotID]]
			
	def getNimTypeName(self, slotID):
		if slotID >= self.nimCount:
			return "empty/unknown"
		else:	
			return self.nimTypes[slotID]
		
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

	def getNimConfigMode(self, slotid):
		return currentConfigSelectionElement(config.Nims[slotid].configMode)
	
	def getSatList(self):
		return self.satList

	def getSatListForNim(self, slotid):
		list = []
		if (self.getNimType(slotid) == self.nimType["DVB-S"]):
			#print "slotid:", slotid
			
			#print "self.satellites:", self.satList[config.Nims[slotid].diseqcA.value]
			#print "diseqcA:", config.Nims[slotid].diseqcA.value
			configMode = currentConfigSelectionElement(config.Nims[slotid].configMode)
			if configMode == "simple":
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
			elif configMode == "advanced":
				for x in self.satList:
					if config.Nims[slotid].advanced.sat[x[1]].lnb.value != 0:
						list.append(x)
		return list

	def getRotorSatListForNim(self, slotid):
		list = []
		if (self.getNimType(slotid) == self.nimType["DVB-S"]):
			#print "slotid:", slotid

			#print "self.satellites:", self.satList[config.Nims[slotid].diseqcA.value]
			#print "diseqcA:", config.Nims[slotid].diseqcA.value
			configMode = currentConfigSelectionElement(config.Nims[slotid].configMode)
			if configMode == "simple":
				if (config.Nims[slotid].diseqcMode.value == 4):
					for x in self.satList:
						list.append(x)
			elif configMode == "advanced":
				for x in self.satList:
					nim = config.Nims[slotid]
					lnbnum = nim.advanced.sat[x[1]].lnb.value
					if lnbnum != 0:
						lnb = nim.advanced.lnb[lnbnum]
						if lnb.diseqcMode.value == 3: # diseqc 1.2
							list.append(x)
		return list

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
		
#	def nimConfigModeChanged(slotid, configElement):
#		nimmgr.nimConfigModeChanged(slotid, configElement.value)
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
			if slot.slotid == 0:
				nim.configMode = configElement(cname + "configMode", configSelection, 0, (
				("simple", _("Simple")), ("advanced", _("Advanced"))), False)
			else:
				nim.configMode = configElement(cname + "configMode", configSelection, 0, (
				("equal", _("Equal to Socket A")),
				("loopthrough", _("Loopthrough to Socket A")),
				("nothing", _("Nothing connected")),
				("satposdepends", _("Secondary cable from motorized LNB")),
				("simple", _("Simple")),
				("advanced", _("Advanced"))), False)
			#important - check if just the 2nd one is LT only and the first one is DVB-S
			if currentConfigSelectionElement(nim.configMode) in ["loopthrough", "satposdepends", "equal"]:
				if x == 0:										#first one can never be linked to anything
					nim.configMode.value = getConfigSelectionElement(nim.configMode, "simple")		#reset to simple
					nim.configMode.save()
				else:
					#FIXME: make it better
					for y in nimmgr.nimslots:
						if y.slotid == 0:
							if y.nimType != nimmgr.nimType["DVB-S"]:
								nim.configMode.value = getConfigSelectionElement(nim.configMode, "simple")		#reset to simple
								nim.configMode.save()

			nim.diseqcMode = configElement(cname + "diseqcMode", configSelection, 2, (("single", _("Single")), ("toneburst_a_b", _("Toneburst A/B")), ("diseqc_a_b", _("DiSEqC A/B")), ("diseqc_a_b_c_d", _("DiSEqC A/B/C/D")), ("positioner", _("Positioner"))), False);
			nim.diseqcA = configElement(cname + "diseqcA", configSatlist, 192, nimmgr.satList, False);
			nim.diseqcB = configElement(cname + "diseqcB", configSatlist, 130, nimmgr.satList, False);
			nim.diseqcC = configElement(cname + "diseqcC", configSatlist, 0, nimmgr.satList, False);
			nim.diseqcD = configElement(cname + "diseqcD", configSatlist, 0, nimmgr.satList, False);
			nim.positionerMode = configElement(cname + "positionerMode", configSelection, 0, (("usals", _("USALS")), ("manual", _("manual"))), False);
			nim.longitude = configElement(cname + "longitude", configSequence, [5,100], configsequencearg.get("FLOAT", [(0,90),(0,999)]), False);
			nim.longitudeOrientation = configElement(cname + "longitudeOrientation", configSelection, 0, (("east", _("East")), ("west", _("West"))), False)
			nim.latitude = configElement(cname + "latitude", configSequence, [50,767], configsequencearg.get("FLOAT", [(0,90),(0,999)]), False);
			nim.latitudeOrientation = configElement(cname + "latitudeOrientation", configSelection, 0, (("north", _("North")), ("south", _("South"))), False)
			satNimList = nimmgr.getNimListOfType(nimmgr.nimType["DVB-S"], slot.slotid)
			satNimListNames = []
			for x in satNimList:
				satNimListNames.append((("Slot_" + ("A", "B", "C", "D")[x] + "_" + nimmgr.getNimName(x)), _("Slot ") + ("A", "B", "C", "D")[x] + ": " + nimmgr.getNimName(x)))
			nim.equalTo = configElement(cname + "equalTo", configSelection, 0, satNimListNames, False);
			nim.linkedTo = configElement(cname + "linkedTo", configSelection, 0, satNimListNames, False);
			nim.satposDependsTo = configElement(cname + "satposDependsTo", configSelection, 0, satNimListNames, False);
			
			#perhaps the instance of the slot is more useful?
#			nim.configMode.addNotifier(boundFunction(nimConfigModeChanged,x))
			nim.diseqcMode.addNotifier(boundFunction(nimDiseqcModeChanged,x))
			nim.diseqcA.addNotifier(boundFunction(nimPortAChanged,int(x)))
			nim.diseqcB.addNotifier(boundFunction(nimPortBChanged,x))
			nim.diseqcC.addNotifier(boundFunction(nimPortCChanged,x))
			nim.diseqcD.addNotifier(boundFunction(nimPortDChanged,x))
			
			# advanced config:
			nim.advanced = ConfigSubsection()
			nim.advanced.sats = configElement(cname + "advanced.sats", configSatlist, 192, nimmgr.satList, False);
			nim.advanced.sat = {}
			lnbs = ["not available"]
			for y in range(1, 33):
				lnbs.append("LNB " + str(y))
			for x in nimmgr.satList:
				nim.advanced.sat[x[1]] = ConfigSubsection()
				nim.advanced.sat[x[1]].voltage = configElement(cname + "advanced.sat" + str(x[1]) + ".voltage", configSelection, 0, (("polarization", _("Polarization")), ("13V", _("13 V")), ("18V", _("18 V"))), False)
				nim.advanced.sat[x[1]].tonemode = configElement(cname + "advanced.sat" + str(x[1]) + ".tonemode", configSelection, 0, (("band", _("Band")), ("on", _("On")), ("off", _("Off"))), False)
				nim.advanced.sat[x[1]].usals = configElement(cname + "advanced.sat" + str(x[1]) + ".usals", configSelection, 0, (("yes", _("Yes")), ("no", _("No"))), False)
				nim.advanced.sat[x[1]].rotorposition = configElement(cname + "advanced.sat" + str(x[1]) + ".rotorposition", configSequence, [1], configsequencearg.get("INTEGER", (1, 255)), False)
				nim.advanced.sat[x[1]].lnb = configElement(cname + "advanced.sat" + str(x[1]) + ".lnb", configSelection, 0, lnbs, False)

			csw = [("none", _("None")), ("AA", _("AA")), ("AB", _("AB")), ("BA", _("BA")), ("BB", _("BB"))]
			for y in range(0, 16):
				csw.append((str(0xF0|y), "Input " + str(y+1)))

			ucsw = [("none", _("None"))]
			for y in range(1, 17):
				ucsw.append("Input " + str(y))

			nim.advanced.lnb = [0]
			for x in range(1, 33):
				nim.advanced.lnb.append(ConfigSubsection())
				nim.advanced.lnb[x].lof = configElement(cname + "advanced.lnb" + str(x) + ".lof", configSelection, 0, (("universal_lnb", _("Universal LNB")), ("c_band", _("C-Band")), ("user_defined", _("User defined"))), False)
				nim.advanced.lnb[x].lofl = configElement(cname + "advanced.lnb" + str(x) + ".lofl", configSequence, [9750], configsequencearg.get("INTEGER", (0, 99999)), False)
				nim.advanced.lnb[x].lofh = configElement(cname + "advanced.lnb" + str(x) + ".lofh", configSequence, [10600], configsequencearg.get("INTEGER", (0, 99999)), False)
				nim.advanced.lnb[x].threshold = configElement(cname + "advanced.lnb" + str(x) + ".threshold", configSequence, [11700], configsequencearg.get("INTEGER", (0, 99999)), False)
				nim.advanced.lnb[x].output_12v = configElement(cname + "advanced.lnb" + str(x) + ".output_12v", configSelection, 0, (("0V", _("0 V")), ("12V", _("12 V"))), False)
				nim.advanced.lnb[x].increased_voltage = configElement(cname + "advanced.lnb" + str(x) + ".increased_voltage", configSelection, 0, (("no", _("No")), ("yes", _("Yes"))), False)
				nim.advanced.lnb[x].toneburst = configElement(cname + "advanced.lnb" + str(x) + ".toneburst", configSelection, 0, (("none", _("None")), ("A", _("A")), ("B", _("B"))), False)
				nim.advanced.lnb[x].diseqcMode = configElement(cname + "advanced.lnb" + str(x) + ".diseqcMode", configSelection, 0, (("none", _("None")), ("1_0", _("1.0")), ("1_1", _("1.1")), ("1_2", _("1.2"))), False)
				nim.advanced.lnb[x].commitedDiseqcCommand = configElement(cname + "advanced.lnb" + str(x) + ".commitedDiseqcCommand", configSelection, 0, csw, False)
				nim.advanced.lnb[x].fastDiseqc = configElement(cname + "advanced.lnb" + str(x) + ".fastDiseqc", configSelection, 0, (("no", _("No")), ("yes", _("Yes"))), False)
				nim.advanced.lnb[x].sequenceRepeat = configElement(cname + "advanced.lnb" + str(x) + ".sequenceRepeat", configSelection, 0, (("no", _("No")), ("yes", _("Yes"))), False)
				nim.advanced.lnb[x].commandOrder1_0 = configElement(cname + "advanced.lnb" + str(x) + ".commandOrder1_0", configSelection, 0, ("committed, toneburst", "toneburst, committed"), False)
				nim.advanced.lnb[x].commandOrder = configElement(cname + "advanced.lnb" + str(x) + ".commandOrder", configSelection, 0, ("committed, toneburst", "toneburst, committed", "committed, uncommitted, toneburst", "toneburst, committed, uncommitted", "uncommitted, committed, toneburst", "toneburst, uncommitted, commmitted"), False)
				nim.advanced.lnb[x].uncommittedDiseqcCommand = configElement(cname + "advanced.lnb" + str(x) + ".uncommittedDiseqcCommand", configSelection, 0, ucsw, False)
				nim.advanced.lnb[x].diseqcRepeats = configElement(cname + "advanced.lnb" + str(x) + ".diseqcRepeats", configSelection, 0, (("none", _("None")), ("one", _("One")), ("two", _("Two")), ("three", _("Three"))), False)
				nim.advanced.lnb[x].longitude = configElement(cname + "advanced.lnb" + str(x) + ".longitude", configSequence, [5,100], configsequencearg.get("FLOAT", [(0,90),(0,999)]), False)
				nim.advanced.lnb[x].longitudeOrientation = configElement(cname + "advanced.lnb" + str(x) + ".longitudeOrientation", configSelection, 0, (("east", _("East")), ("west", _("West"))), False)
				nim.advanced.lnb[x].latitude = configElement(cname + "advanced.lnb" + str(x) + ".latitude", configSequence, [50,767], configsequencearg.get("FLOAT", [(0,90),(0,999)]), False)
				nim.advanced.lnb[x].latitudeOrientation = configElement(cname + "advanced.lnb" + str(x) + ".latitudeOrientation", configSelection, 0, (("north", _("North")), ("south", _("South"))), False)
				nim.advanced.lnb[x].powerMeasurement = configElement(cname + "advanced.lnb" + str(x) + ".powerMeasurement", configSelection, 0, (("yes", _("Yes")), ("no", _("No"))), False)
				nim.advanced.lnb[x].powerThreshold = configElement(cname + "advanced.lnb" + str(x) + ".powerThreshold", configSequence, [50], configsequencearg.get("INTEGER", (0, 100)), False)
		elif slot.nimType == nimmgr.nimType["DVB-C"]:
			nim.cable = configElement(cname + "cable", configSelection, 0, nimmgr.cablesList, False);
		elif slot.nimType == nimmgr.nimType["DVB-T"]:
			list = []
			for x in nimmgr.terrestrialsList:
				list.append(x[0])
			nim.terrestrial = configElement(cname + "terrestrial", configSelection, 0, list, False);
		else:
			print "pls add support for this frontend type!"		

	nimmgr.sec = SecConfigure(nimmgr)

nimmanager = NimManager()

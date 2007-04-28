from config import config, ConfigSubsection, ConfigSelection, ConfigFloat, ConfigSatlist, ConfigYesNo, ConfigInteger, ConfigSubList, ConfigNothing, ConfigSubDict, ConfigOnOff

from enigma import eDVBSatelliteEquipmentControl as secClass, \
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

def getConfigSatlist(orbpos, satlist):
	default_orbpos = None
	for x in satlist:
		if x[0] == orbpos:
			default_orbpos = orbpos
			break
	return ConfigSatlist(satlist, default_orbpos)

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
			sec.setLatitude(latitude)
			sec.setLaDirection(laDirection)
			sec.setLongitude(longitude)
			sec.setLoDirection(loDirection)
			sec.setUseInputpower(True)
			sec.setInputpowerDelta(50)

			for x in self.NimManager.satList:
				print "Add sat " + str(x[0])
				sec.addSatellite(int(x[0]))
				sec.setVoltageMode(0)
				sec.setToneMode(0)
				sec.setRotorPosNum(0) # USALS
				self.satList.append(int(x[0]))

		sec.setLNBTunerMask(tunermask)

	def setSatposDepends(self, sec, nim1, nim2):
		print "tuner", nim1, "depends on satpos of", nim2
		sec.setTunerDepends(nim1, nim2)

	def linkNIMs(self, sec, nim1, nim2):
		print "link tuner", nim1, "to tuner", nim2
		sec.setTunerLinked(nim1, nim2)

	def getSatList(self):
		return self.satList

	def update(self):
		sec = secClass.getInstance()
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
				if nim.configMode.value == "equal":
					self.equal[nim.equalTo.index]=x
				if nim.configMode.value == "loopthrough":
					self.linkNIMs(sec, x, nim.linkedTo.index)
					self.linked[nim.linkedTo.index]=x
				elif nim.configMode.value == "satposdepends":
					self.setSatposDepends(sec, x, nim.satposDependsTo.index)
					self.satposdepends[nim.satposDependsTo.index]=x

		for slot in self.NimManager.nimslots:
			x = slot.slotid
			nim = config.Nims[x]
			if slot.nimType == self.NimManager.nimType["DVB-S"]:
				print "slot: " + str(x) + " configmode: " + str(nim.configMode.value)
				print "diseqcmode: ", nim.configMode.value
				if nim.configMode.value in [ "loopthrough", "satposdepends", "equal", "nothing" ]:
					pass
				elif nim.configMode.value == "simple":		#simple config
					if nim.diseqcMode.value == "single":			#single
						self.addLNBSimple(sec, slotid = x, orbpos = nim.diseqcA.orbital_position, toneburstmode = diseqcParam.NO, diseqcmode = diseqcParam.NONE, diseqcpos = diseqcParam.SENDNO)
					elif nim.diseqcMode.value == "toneburst_a_b":		#Toneburst A/B
						self.addLNBSimple(sec, slotid = x, orbpos = nim.diseqcA.orbital_position, toneburstmode = diseqcParam.A, diseqcmode = diseqcParam.V1_0, diseqcpos = diseqcParam.SENDNO)
						self.addLNBSimple(sec, slotid = x, orbpos = nim.diseqcB.orbital_position, toneburstmode = diseqcParam.B, diseqcmode = diseqcParam.V1_0, diseqcpos = diseqcParam.SENDNO)
					elif nim.diseqcMode.value == "diseqc_a_b":		#DiSEqC A/B
						self.addLNBSimple(sec, slotid = x, orbpos = nim.diseqcA.orbital_position, toneburstmode = diseqcParam.NO, diseqcmode = diseqcParam.V1_0, diseqcpos = diseqcParam.AA)
						self.addLNBSimple(sec, slotid = x, orbpos = nim.diseqcB.orbital_position, toneburstmode = diseqcParam.NO, diseqcmode = diseqcParam.V1_0, diseqcpos = diseqcParam.AB)
					elif nim.diseqcMode.value == "diseqc_a_b_c_d":		#DiSEqC A/B/C/D
						self.addLNBSimple(sec, slotid = x, orbpos = nim.diseqcA.orbital_position, toneburstmode = diseqcParam.NO, diseqcmode = diseqcParam.V1_0, diseqcpos = diseqcParam.AA)
						self.addLNBSimple(sec, slotid = x, orbpos = nim.diseqcB.orbital_position, toneburstmode = diseqcParam.NO, diseqcmode = diseqcParam.V1_0, diseqcpos = diseqcParam.AB)
						self.addLNBSimple(sec, slotid = x, orbpos = nim.diseqcC.orbital_position, toneburstmode = diseqcParam.NO, diseqcmode = diseqcParam.V1_0, diseqcpos = diseqcParam.BA)
						self.addLNBSimple(sec, slotid = x, orbpos = nim.diseqcD.orbital_position, toneburstmode = diseqcParam.NO, diseqcmode = diseqcParam.V1_0, diseqcpos = diseqcParam.BB)
					elif nim.diseqcMode.value == "positioner":		#Positioner
						if nim.latitudeOrientation.value == "north":
							laValue = rotorParam.NORTH
						else:
							laValue = rotorParam.SOUTH
						if nim.longitudeOrientation.value == "east":
							loValue = rotorParam.EAST
						else:
							loValue = rotorParam.WEST
						self.addLNBSimple(sec, slotid = x, diseqcmode = 3,
							longitude = nim.longitude.float,
							loDirection = loValue,
							latitude = nim.latitude.float,
							laDirection = laValue)
				elif nim.configMode.value == "advanced": #advanced config
					self.updateAdvanced(sec, x)
		print "sec config completed"

	def updateAdvanced(self, sec, slotid):
		lnbSat = {}
		for x in range(1,33):
			lnbSat[x] = []
		for x in self.NimManager.satList:
			lnb = int(config.Nims[slotid].advanced.sat[x[0]].lnb.value)
			if lnb != 0:
				print "add", x[0], "to", lnb
				lnbSat[lnb].append(x[0])
		for x in range(1,33):
			if len(lnbSat[x]) > 0:
				currLnb = config.Nims[slotid].advanced.lnb[x]
				sec.addLNB()

				tunermask = 1 << slotid
				if self.equal.has_key(slotid):
					tunermask |= (1 << self.equal[slotid])
				elif self.linked.has_key(slotid):
					tunermask |= (1 << self.linked[slotid])

				if currLnb.lof.value == "universal_lnb":
					sec.setLNBLOFL(9750000)
					sec.setLNBLOFH(10600000)
					sec.setLNBThreshold(11700000)
				elif currLnb.lof.value == "c_band":
					sec.setLNBLOFL(5150000)
					sec.setLNBLOFH(5150000)
					sec.setLNBThreshold(5150000)
				elif currLnb.lof.value == "user_defined":
					sec.setLNBLOFL(currLnb.lofl.value * 1000)
					sec.setLNBLOFH(currLnb.lofh.value * 1000)
					sec.setLNBThreshold(currLnb.threshold.value * 1000)
					
#				if currLnb.output_12v.value == "0V":
#					pass # nyi in drivers
#				elif currLnb.output_12v.value == "12V":
#					pass # nyi in drivers
					
				if currLnb.increased_voltage.value:
					sec.setLNBIncreasedVoltage(lnbParam.ON)
				else:
					sec.setLNBIncreasedVoltage(lnbParam.OFF)
				
				dm = currLnb.diseqcMode.value 
				if dm == "none":
					sec.setDiSEqCMode(diseqcParam.NONE)
				elif dm == "1_0":
					sec.setDiSEqCMode(diseqcParam.V1_0)
				elif dm == "1_1":
					sec.setDiSEqCMode(diseqcParam.V1_1)
				elif dm == "1_2":
					sec.setDiSEqCMode(diseqcParam.V1_2)

					if self.satposdepends.has_key(slotid):  # only useable with rotors
						tunermask |= (1 << self.satposdepends[slotid])

				if dm != "none":
					if currLnb.toneburst.value == "none":
						sec.setToneburst(diseqcParam.NO)
					elif currLnb.toneburst.value == "A":
						sec.setToneburst(diseqcParam.A)
					elif currLnb.toneburst.value == "B":
						sec.setToneburst(diseqcParam.B)
					
					# Committed Diseqc Command
					cdc = currLnb.commitedDiseqcCommand.value
					
					c = { "none": diseqcParam.SENDNO,
						"AA": diseqcParam.AA,
						"AB": diseqcParam.AB,
						"BA": diseqcParam.BA,
						"BB": diseqcParam.BB }

					if c.has_key(cdc):
						sec.setCommittedCommand(c[cdc])
					else:
						sec.setCommittedCommand(long(cdc))

					sec.setFastDiSEqC(currLnb.fastDiseqc.value)
						
					sec.setSeqRepeat(currLnb.sequenceRepeat.value)
						
					if currLnb.diseqcMode.value == "1_0":
						currCO = currLnb.commandOrder1_0.value
					else:
						currCO = currLnb.commandOrder.value

						udc = int(currLnb.uncommittedDiseqcCommand.value)
						if udc > 0:
							sec.setUncommittedCommand(0xF0|(udc-1))
						else:
							sec.setUncommittedCommand(0) # SENDNO

						sec.setRepeats({"none": 0, "one": 1, "two": 2, "three": 3}[currLnb.diseqcRepeats.value])

					setCommandOrder = False
					
					# 0 "committed, toneburst", 
					# 1 "toneburst, committed", 
					# 2 "committed, uncommitted, toneburst",
					# 3 "toneburst, committed, uncommitted",
					# 4 "uncommitted, committed, toneburst"
					# 5 "toneburst, uncommitted, commmitted"
					order_map = {"ct": 0, "tc": 1, "cut": 2, "tcu": 3, "uct": 4, "tuc": 5}
					sec.setCommandOrder(order_map[currCO])

				if dm == "1_2":
					latitude = currLnb.latitude.float
					sec.setLatitude(latitude)
					longitude = currLnb.longitude.float
					sec.setLongitude(longitude)
					if currLnb.latitudeOrientation.value == "north":
						sec.setLaDirection(rotorParam.NORTH)
					else:
						sec.setLaDirection(rotorParam.SOUTH)
					if currLnb.longitudeOrientation.value == "east":
						sec.setLoDirection(rotorParam.EAST)
					else:
						sec.setLoDirection(rotorParam.WEST)
						
				if currLnb.powerMeasurement.value:
					sec.setUseInputpower(True)
					sec.setInputpowerDelta(currLnb.powerThreshold.value)
				else:
					sec.setUseInputpower(False)

				sec.setLNBTunerMask(tunermask)

				# finally add the orbital positions
				for y in lnbSat[x]:
					sec.addSatellite(y)
					currSat = config.Nims[slotid].advanced.sat[y]

					if currSat.voltage.value == "polarization":
						sec.setVoltageMode(switchParam.HV)
					elif currSat.voltage.value == "13V":
						sec.setVoltageMode(switchParam._14V)
					elif currSat.voltage.value == "18V":
						sec.setVoltageMode(switchParam._18V)
						
					if currSat.tonemode == "band":
						sec.setToneMode(switchParam.HILO)
					elif currSat.tonemode == "on":
						sec.setToneMode(switchParam.ON)
					elif currSat.tonemode == "off":
						sec.setToneMode(switchParam.OFF)
						
					if not currSat.usals.value:
						sec.setRotorPosNum(currSat.rotorposition.value)
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
				self.satList.append( (tpos, tname) )
				self.parsedSat = int(tpos)
			elif (name == "transponder"):
				modulation = int(attrs.get('modulation',"1")) # QPSK default
				system = int(attrs.get('system',"0")) # DVB-S default
				freq = int(attrs.get('frequency',""))
				sr = int(attrs.get('symbol_rate',""))
				pol = int(attrs.get('polarization',""))
				fec = int(attrs.get('fec_inner',"0")) # AUTO default
				if self.parsedSat in self.transponders:
					pass
				else:
					self.transponders[self.parsedSat] = [ ]

				self.transponders[self.parsedSat].append((0, freq, sr, pol, fec, system, modulation))

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
				#sr = int(attrs.get('symbol_rate',""))
				#mod = int(attrs.get('modulation',"3")) # QAM64 default
				#fec = int(attrs.get('fec_inner',"0")) # AUTO default
				if self.parsedCab in self.transponders:
					pass
				else:
					self.transponders[self.parsedCab] = [ ]
				self.transponders[self.parsedCab].append((1, freq))

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
				bw = int(attrs.get('bandwidth',"3")) # AUTO
				const = int(attrs.get('constellation',"1")) # AUTO
				crh = int(attrs.get('code_rate_hp',"5")) # AUTO
				if crh > 5: # our terrestrial.xml is buggy... 6 for AUTO
					crh = 5
				crl = int(attrs.get('code_rate_lp',"5")) # AUTO
				if crl > 5: # our terrestrial.xml is buggy... 6 for AUTO
					crl = 5
				guard = int(attrs.get('guard_interval',"4")) # AUTO
				transm = int(attrs.get('transmission_mode',"2")) # AUTO
				hierarchy = int(attrs.get('hierarchy_information',"4")) # AUTO
				inv = int(attrs.get('inversion',"2")) # AUTO
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
		return self.cablesList[0]
	
	def getCableTrustNit(self, nim):
		return config.Nims[nim].cabletype.value == "quick"

	def getTerrestrialDescription(self, nim):
		return self.terrestrialsList[config.Nims[nim].terrestrial.index][0]

	def getTerrestrialFlags(self, nim):
		return self.terrestrialsList[config.Nims[nim].terrestrial.index][1]

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

		entries = {}
		while 1:		
			line = nimfile.readline()
			if line == "":
				break
			if line.strip().startswith("NIM Socket"):
				parts = line.strip().split(" ")
				id = int(parts[2][:1])
				lastsocket = int(id)
				entries[lastsocket] = {}
			elif line.strip().startswith("Type:"):
				entries[lastsocket]["type"] = str(line.strip()[6:])
				#entries[lastsocket]["type"] = str("DVB-S2")
			elif line.strip().startswith("Name:"):
				entries[lastsocket]["name"] = str(line.strip()[6:])
			elif line.strip().startswith("empty"):
				entries[lastsocket]["type"] = "empty/unknown"
				entries[lastsocket]["name"] = _("N/A")
		nimfile.close()
		
		for id,entry  in entries.items():
			if not(entry.has_key("name") and entry.has_key("type") and self.nimType.has_key(entry["type"])):
				entry["name"] =  _("N/A")
				entry["type"] = "empty/unknown"
			self.nimNames[id] = entry["name"]
			self.nimTypes[id] = entry["type"]
			self.nimSocketCount += 1

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
		return config.Nims[slotid].configMode.value
	
	def getSatList(self):
		return self.satList

	def getSatListForNim(self, slotid):
		list = []
		if (self.getNimType(slotid) == self.nimType["DVB-S"]):
			#print "slotid:", slotid
			
			#print "self.satellites:", self.satList[config.Nims[slotid].diseqcA.value]
			#print "diseqcA:", config.Nims[slotid].diseqcA.value
			configMode = config.Nims[slotid].configMode.value

			if configMode == "equal":
				slotid=0 #FIXME add handling for more than two tuners !!!
				configMode = config.Nims[slotid].configMode.value

			if configMode == "simple":
				dm = config.Nims[slotid].diseqcMode.value
				if dm in ["single", "toneburst_a_b", "diseqc_a_b", "diseqc_a_b_c_d"]:
					list.append(self.satList[config.Nims[slotid].diseqcA.index])
				if dm in ["toneburst_a_b", "diseqc_a_b", "diseqc_a_b_c_d"]:
					list.append(self.satList[config.Nims[slotid].diseqcB.index])
				if dm == "diseqc_a_b_c_d":
					list.append(self.satList[config.Nims[slotid].diseqcC.index])
					list.append(self.satList[config.Nims[slotid].diseqcD.index])
				if dm == "positioner":
					for x in self.satList:
						list.append(x)
			elif configMode == "advanced":
				for x in self.satList:
					if int(config.Nims[slotid].advanced.sat[x[0]].lnb.value) != 0:
						list.append(x)

		return list

	def getRotorSatListForNim(self, slotid):
		list = []
		if (self.getNimType(slotid) == self.nimType["DVB-S"]):
			#print "slotid:", slotid

			#print "self.satellites:", self.satList[config.Nims[slotid].diseqcA.value]
			#print "diseqcA:", config.Nims[slotid].diseqcA.value
			configMode = config.Nims[slotid].configMode.value
			if configMode == "simple":
				if config.Nims[slotid].diseqcMode.value == "positioner":
					for x in self.satList:
						list.append(x)
			elif configMode == "advanced":
				for x in self.satList:
					nim = config.Nims[slotid]
					lnbnum = int(nim.advanced.sat[x[0]].lnb.value)
					if lnbnum != 0:
						lnb = nim.advanced.lnb[lnbnum]
						if lnb.diseqcMode.value == "1_2":
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

def InitSecParams():
	config.sec = ConfigSubsection()

	x = ConfigInteger(default=15, limits = (0, 9999))
	x.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_AFTER_CONT_TONE, configElement.value))
	config.sec.delay_after_continuous_tone_change = x

	x = ConfigInteger(default=10, limits = (0, 9999))
	x.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_AFTER_FINAL_VOLTAGE_CHANGE, configElement.value))
	config.sec.delay_after_final_voltage_change = x

	x = ConfigInteger(default=120, limits = (0, 9999))
	x.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_BETWEEN_DISEQC_REPEATS, configElement.value))
	config.sec.delay_between_diseqc_repeats = x

	x = ConfigInteger(default=50, limits = (0, 9999))
	x.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_AFTER_LAST_DISEQC_CMD, configElement.value))
	config.sec.delay_after_last_diseqc_command = x

	x = ConfigInteger(default=50, limits = (0, 9999))
	x.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_AFTER_TONEBURST, configElement.value))
	config.sec.delay_after_toneburst = x

	x = ConfigInteger(default=750, limits = (0, 9999))
	x.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_AFTER_ENABLE_VOLTAGE_BEFORE_SWITCH_CMDS, configElement.value))
	config.sec.delay_after_enable_voltage_before_switch_command = x

	x = ConfigInteger(default=700, limits = (0, 9999))
	x.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_BETWEEN_SWITCH_AND_MOTOR_CMD, configElement.value))
	config.sec.delay_between_switch_and_motor_command = x

	x = ConfigInteger(default=150, limits = (0, 9999))
	x.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_AFTER_VOLTAGE_CHANGE_BEFORE_MEASURE_IDLE_INPUTPOWER, configElement.value))
	config.sec.delay_after_voltage_change_before_measure_idle_inputpower = x

	x = ConfigInteger(default=750, limits = (0, 9999))
	x.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_AFTER_ENABLE_VOLTAGE_BEFORE_MOTOR_CMD, configElement.value))
	config.sec.delay_after_enable_voltage_before_motor_command = x

	x = ConfigInteger(default=150, limits = (0, 9999))
	x.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_AFTER_MOTOR_STOP_CMD, configElement.value))
	config.sec.delay_after_motor_stop_command = x

	x = ConfigInteger(default=150, limits = (0, 9999))
	x.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_AFTER_VOLTAGE_CHANGE_BEFORE_MOTOR_CMD, configElement.value))
	config.sec.delay_after_voltage_change_before_motor_command = x

	x = ConfigInteger(default=120, limits = (0, 9999))
	x.addNotifier(lambda configElement: secClass.setParam(secClass.MOTOR_RUNNING_TIMEOUT, configElement.value))
	config.sec.motor_running_timeout = x

	x = ConfigInteger(default=1, limits = (0, 5))
	x.addNotifier(lambda configElement: secClass.setParam(secClass.MOTOR_COMMAND_RETRIES, configElement.value))
	config.sec.motor_command_retries = x


def InitNimManager(nimmgr):
	InitSecParams()

	config.Nims = ConfigSubList()
	for x in range(nimmgr.nimCount):
		config.Nims.append(ConfigSubsection())

#	def nimConfigModeChanged(slotid, configElement):
#		nimmgr.nimConfigModeChanged(slotid, configElement.value)
	def nimDiseqcModeChanged(slotid, configElement):
		nimmgr.nimDiseqcModeChanged(slotid, configElement.value)

	def nimPortAChanged(slotid, configElement):
		nimmgr.nimPortAChanged(slotid, configElement.value)
	def nimPortBChanged(slotid, configElement):
		nimmgr.nimPortBChanged(slotid, configElement.value)
	def nimPortCChanged(slotid, configElement):
		nimmgr.nimPortCChanged(slotid, configElement.value)
	def nimPortDChanged(slotid, configElement):
		nimmgr.nimPortDChanged(slotid, configElement.value)

	for slot in nimmgr.nimslots:
		x = slot.slotid
		cname = nimmgr.getConfigPrefix(x)
		nim = config.Nims[x]

		if slot.nimType == nimmgr.nimType["DVB-S"]:
			if slot.slotid == 0:
				nim.configMode = ConfigSelection(
					choices = {
						"simple": _("simple"),
						"advanced": _("advanced")},
					default = "simple")
			else:
				nim.configMode = ConfigSelection(
					choices = {
						"equal": _("equal to Socket A"),
						"loopthrough": _("loopthrough to socket A"),
						"nothing": _("nothing connected"),
						"satposdepends": _("second cable of motorized LNB"),
						"simple": _("simple"),
						"advanced": _("advanced")},
					default = "loopthrough")

			#important - check if just the 2nd one is LT only and the first one is DVB-S
			if nim.configMode.value in ["loopthrough", "satposdepends", "equal"]:
				if x == 0: # first one can never be linked to anything
					# reset to simple
					nim.configMode.value = "simple"
					nim.configMode.save()
				else:
					#FIXME: make it better
					for y in nimmgr.nimslots:
						if y.slotid == 0:
							if y.nimType != nimmgr.nimType["DVB-S"]:
								# reset to simple
								nim.configMode.value = "simple"
								nim.configMode.save()

			nim.diseqcMode = ConfigSelection(
				choices = [
					("single", _("Single")),
					("toneburst_a_b", _("Toneburst A/B")),
					("diseqc_a_b", _("DiSEqC A/B")),
					("diseqc_a_b_c_d", _("DiSEqC A/B/C/D")),
					("positioner", _("Positioner"))],
				default = "diseqc_a_b")

			nim.diseqcA = getConfigSatlist(192, nimmgr.satList)
			nim.diseqcB = getConfigSatlist(130, nimmgr.satList)
			nim.diseqcC = ConfigSatlist(list = nimmgr.satList)
			nim.diseqcD = ConfigSatlist(list = nimmgr.satList)
			nim.positionerMode = ConfigSelection(
				choices = [
					("usals", _("USALS")),
					("manual", _("manual"))],
				default = "usals")
			nim.longitude = ConfigFloat(default=[5,100], limits=[(0,359),(0,999)])
			nim.longitudeOrientation = ConfigSelection(choices={"east": _("East"), "west": _("West")}, default = "east")
			nim.latitude = ConfigFloat(default=[50,767], limits=[(0,359),(0,999)])
			nim.latitudeOrientation = ConfigSelection(choices={"north": _("North"), "south": _("South")}, default="north")
			satNimList = nimmgr.getNimListOfType(nimmgr.nimType["DVB-S"], slot.slotid)
			satNimListNames = {}
			for x in satNimList:
				satNimListNames["Slot_" + ("A", "B", "C", "D")[x] + "_" + nimmgr.getNimName(x)] = _("Slot ") + ("A", "B", "C", "D")[x] + ": " + nimmgr.getNimName(x)
			if len(satNimListNames):
				nim.equalTo = ConfigSelection(choices = satNimListNames)
				nim.linkedTo = ConfigSelection(choices = satNimListNames)
				nim.satposDependsTo = ConfigSelection(choices = satNimListNames)

			#perhaps the instance of the slot is more useful?
#			nim.configMode.addNotifier(boundFunction(nimConfigModeChanged,x))
			nim.diseqcMode.addNotifier(boundFunction(nimDiseqcModeChanged,x))
			nim.diseqcA.addNotifier(boundFunction(nimPortAChanged,int(x)))
			nim.diseqcB.addNotifier(boundFunction(nimPortBChanged,x))
			nim.diseqcC.addNotifier(boundFunction(nimPortCChanged,x))
			nim.diseqcD.addNotifier(boundFunction(nimPortDChanged,x))

			# advanced config:
			nim.advanced = ConfigSubsection()
			nim.advanced.sats = getConfigSatlist(192,nimmgr.satList)
			nim.advanced.sat = ConfigSubDict()
			lnbs = [("0", "not available")]
			for y in range(1, 33):
				lnbs.append((str(y), "LNB " + str(y)))

			for x in nimmgr.satList:
				nim.advanced.sat[x[0]] = ConfigSubsection()
				nim.advanced.sat[x[0]].voltage = ConfigSelection(choices={"polarization": _("Polarization"), "13V": _("13 V"), "18V": _("18 V")}, default = "polarization")
				nim.advanced.sat[x[0]].tonemode = ConfigSelection(choices={"band": _("Band"), "on": _("On"), "off": _("Off")}, default = "band")
				nim.advanced.sat[x[0]].usals = ConfigYesNo(default=True)
				nim.advanced.sat[x[0]].rotorposition = ConfigInteger(default=1, limits=(1, 255))
				nim.advanced.sat[x[0]].lnb = ConfigSelection(choices = lnbs)

			csw = [("none", _("None")), ("AA", _("AA")), ("AB", _("AB")), ("BA", _("BA")), ("BB", _("BB"))]
			for y in range(0, 16):
				csw.append((str(0xF0|y), "Input " + str(y+1)))

			ucsw = [("0", _("None"))]
			for y in range(1, 17):
				ucsw.append((str(y), "Input " + str(y)))

			nim.advanced.lnb = ConfigSubList()
			nim.advanced.lnb.append(ConfigNothing())
			for x in range(1, 33):
				nim.advanced.lnb.append(ConfigSubsection())
				nim.advanced.lnb[x].lof = ConfigSelection(choices={"universal_lnb": _("Universal LNB"), "c_band": _("C-Band"), "user_defined": _("User defined")}, default="universal_lnb")
				nim.advanced.lnb[x].lofl = ConfigInteger(default=9750, limits = (0, 99999))
				nim.advanced.lnb[x].lofh = ConfigInteger(default=10600, limits = (0, 99999))
				nim.advanced.lnb[x].threshold = ConfigInteger(default=11700, limits = (0, 99999))
#				nim.advanced.lnb[x].output_12v = ConfigSelection(choices = [("0V", _("0 V")), ("12V", _("12 V"))], default="0V")
				nim.advanced.lnb[x].increased_voltage = ConfigYesNo(default=False)
				nim.advanced.lnb[x].toneburst = ConfigSelection(choices = [("none", _("None")), ("A", _("A")), ("B", _("B"))], default = "none")
				nim.advanced.lnb[x].diseqcMode = ConfigSelection(choices = [("none", _("None")), ("1_0", _("1.0")), ("1_1", _("1.1")), ("1_2", _("1.2"))], default = "none")
				nim.advanced.lnb[x].commitedDiseqcCommand = ConfigSelection(choices = csw)
				nim.advanced.lnb[x].fastDiseqc = ConfigYesNo(default=False)
				nim.advanced.lnb[x].sequenceRepeat = ConfigYesNo(default=False)
				nim.advanced.lnb[x].commandOrder1_0 = ConfigSelection(choices = [("ct", "committed, toneburst"), ("tc", "toneburst, committed")], default = "ct")
				nim.advanced.lnb[x].commandOrder = ConfigSelection(choices = [
						("ct", "committed, toneburst"),
						("tc", "toneburst, committed"),
						("cut", "committed, uncommitted, toneburst"),
						("tcu", "toneburst, committed, uncommitted"),
						("uct", "uncommitted, committed, toneburst"),
						("tuc", "toneburst, uncommitted, commmitted")],
						default="ct")
				nim.advanced.lnb[x].uncommittedDiseqcCommand = ConfigSelection(choices = ucsw)
				nim.advanced.lnb[x].diseqcRepeats = ConfigSelection(choices = [("none", _("None")), ("one", _("One")), ("two", _("Two")), ("three", _("Three"))], default = "none")
				nim.advanced.lnb[x].longitude = ConfigFloat(default = [5,100], limits = [(0,359),(0,999)])
				nim.advanced.lnb[x].longitudeOrientation = ConfigSelection(choices = [("east", _("East")), ("west", _("West"))], default = "east")
				nim.advanced.lnb[x].latitude = ConfigFloat(default = [50,767], limits = [(0,359),(0,999)])
				nim.advanced.lnb[x].latitudeOrientation = ConfigSelection(choices = [("north", _("North")), ("south", _("South"))], default = "north")
				nim.advanced.lnb[x].powerMeasurement = ConfigYesNo(default=True)
				nim.advanced.lnb[x].powerThreshold = ConfigInteger(default=50, limits=(0, 100))

		elif slot.nimType == nimmgr.nimType["DVB-C"]:
			nim.cabletype = ConfigSelection(choices = [("quick", _("Quick")), ("complete", _("Complete"))], default = "complete")
		elif slot.nimType == nimmgr.nimType["DVB-T"]:
			list = []
			n = 0
			for x in nimmgr.terrestrialsList:
				list.append((str(n), x[0]))
				n += 1
			nim.terrestrial = ConfigSelection(choices = list)
			nim.terrestrial_5V = ConfigOnOff()
		else:
			print "pls add support for this frontend type!"		
#			assert False

	nimmgr.sec = SecConfigure(nimmgr)


nimmanager = NimManager()

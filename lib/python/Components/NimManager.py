from config import config, ConfigSubsection, ConfigSelection, ConfigFloat, \
	ConfigSatlist, ConfigYesNo, ConfigInteger, ConfigSubList, ConfigNothing, \
	ConfigSubDict, ConfigOnOff, ConfigDateTime

from enigma import eDVBSatelliteEquipmentControl as secClass, \
	eDVBSatelliteLNBParameters as lnbParam, \
	eDVBSatelliteDiseqcParameters as diseqcParam, \
	eDVBSatelliteSwitchParameters as switchParam, \
	eDVBSatelliteRotorParameters as rotorParam, \
	eDVBResourceManager, eDVBDB

from time import localtime, mktime
from datetime import datetime

from sets import Set

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
		return None
	return procFile

class SecConfigure:
	def getConfiguredSats(self):
		return self.configuredSatellites

	def addSatellite(self, sec, orbpos):
		sec.addSatellite(orbpos)
		self.configuredSatellites.add(orbpos)

	def addLNBSimple(self, sec, slotid, diseqcmode, toneburstmode = diseqcParam.NO, diseqcpos = diseqcParam.SENDNO, orbpos = 0, longitude = 0, latitude = 0, loDirection = 0, laDirection = 0, turningSpeed = rotorParam.FAST, useInputPower=True, inputPowerDelta=50):
		if orbpos is None:
			return
		#simple defaults
		sec.addLNB()
		tunermask = 1 << slotid
		if self.equal.has_key(slotid):
			for slot in self.equal[slotid]:
				tunermask |= (1 << slot)
		elif self.linked.has_key(slotid):
			for slot in self.linked[slotid]:
				tunermask |= (1 << slot)
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
		sec.setUncommittedCommand(0) # SENDNO
		#print "set orbpos to:" + str(orbpos)

		if 0 <= diseqcmode < 3:
			self.addSatellite(sec, orbpos)
		elif (diseqcmode == 3): # diseqc 1.2
			if self.satposdepends.has_key(slotid):
				tunermask |= (1 << self.satposdepends[slotid])
			sec.setLatitude(latitude)
			sec.setLaDirection(laDirection)
			sec.setLongitude(longitude)
			sec.setLoDirection(loDirection)
			sec.setUseInputpower(useInputPower)
			sec.setInputpowerDelta(inputPowerDelta)
			sec.setRotorTurningSpeed(turningSpeed)

			for x in self.NimManager.satList:
				print "Add sat " + str(x[0])
				self.addSatellite(sec, int(x[0]))
				sec.setVoltageMode(0)
				sec.setToneMode(0)
				sec.setRotorPosNum(0) # USALS
		
		sec.setLNBSlotMask(tunermask)

	def setSatposDepends(self, sec, nim1, nim2):
		print "tuner", nim1, "depends on satpos of", nim2
		sec.setTunerDepends(nim1, nim2)

	def linkNIMs(self, sec, nim1, nim2):
		print "link tuner", nim1, "to tuner", nim2
		sec.setTunerLinked(nim1, nim2)
		
	def getRoot(self, slotid, connto):
		visited = []
		while (self.NimManager.getNimConfig(connto).configMode.value in ["satposdepends", "equal", "loopthrough"]):
			connto = int(self.NimManager.getNimConfig(connto).connectedTo.value)
			if connto in visited: # prevent endless loop
				return slotid
			visited.append(connto)
		return connto

	def update(self):
		sec = secClass.getInstance()
		self.configuredSatellites = Set()
		sec.clear() ## this do unlinking NIMs too !!
		print "sec config cleared"

		self.linked = { }
		self.satposdepends = { }
		self.equal = { }

		nim_slots = self.NimManager.nim_slots

		used_nim_slots = [ ]

		for slot in nim_slots:
			if slot.type is not None:
				used_nim_slots.append((slot.slot, slot.description, slot.config.configMode.value != "nothing" and True or False))
		eDVBResourceManager.getInstance().setFrontendSlotInformations(used_nim_slots)

		for slot in nim_slots:
			x = slot.slot
			nim = slot.config
			if slot.isCompatible("DVB-S"):
				# save what nim we link to/are equal to/satposdepends to.
				# this is stored in the *value* (not index!) of the config list
				if nim.configMode.value == "equal":
					connto = self.getRoot(x, int(nim.connectedTo.value))
					if not self.equal.has_key(connto):
						self.equal[connto] = []
					self.equal[connto].append(x)
				elif nim.configMode.value == "loopthrough":
					self.linkNIMs(sec, x, int(nim.connectedTo.value))
					connto = self.getRoot(x, int(nim.connectedTo.value))
					if not self.linked.has_key(connto):
						self.linked[connto] = []
					self.linked[connto].append(x)
				elif nim.configMode.value == "satposdepends":
					self.setSatposDepends(sec, x, int(nim.connectedTo.value))
					connto = self.getRoot(x, int(nim.connectedTo.value))
					if not self.satposdepends.has_key(connto):
						self.satposdepends[connto] = []
					self.satposdepends[connto].append(x)
					

		for slot in nim_slots:
			x = slot.slot
			nim = slot.config
			if slot.isCompatible("DVB-S"):
				print "slot: " + str(x) + " configmode: " + str(nim.configMode.value)
				print "diseqcmode: ", nim.diseqcMode.value
				if nim.configMode.value in [ "loopthrough", "satposdepends", "nothing" ]:
					pass
				else:
					sec.setSlotNotLinked(x)
					if nim.configMode.value == "equal":
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
							inputPowerDelta=50
							useInputPower=False
							turning_speed=0
							if nim.powerMeasurement.value:
								useInputPower=True
								inputPowerDelta=nim.powerThreshold.value
								turn_speed_dict = { "fast": rotorParam.FAST, "slow": rotorParam.SLOW }
								if turn_speed_dict.has_key(nim.turningSpeed.value):
									turning_speed = turn_speed_dict[nim.turningSpeed.value]
								else:
									beg_time = localtime(nim.fastTurningBegin.value)
									end_time = localtime(nim.fastTurningEnd.value)
									turning_speed = ((beg_time.tm_hour+1) * 60 + beg_time.tm_min + 1) << 16
									turning_speed |= (end_time.tm_hour+1) * 60 + end_time.tm_min + 1
							self.addLNBSimple(sec, slotid = x, diseqcmode = 3,
								longitude = nim.longitude.float,
								loDirection = loValue,
								latitude = nim.latitude.float,
								laDirection = laValue,
								turningSpeed = turning_speed,
								useInputPower = useInputPower,
								inputPowerDelta = inputPowerDelta)
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
					turn_speed_dict = { "fast": rotorParam.FAST, "slow": rotorParam.SLOW }
					if turn_speed_dict.has_key(currLnb.turningSpeed.value):
						turning_speed = turn_speed_dict[currLnb.turningSpeed.value]
					else:
						beg_time = localtime(currLnb.fastTurningBegin.value)
						end_time = localtime(currLnb.fastTurningEnd.value)
						turning_speed = ((beg_time.tm_hour + 1) * 60 + beg_time.tm_min + 1) << 16
						turning_speed |= (end_time.tm_hour + 1) * 60 + end_time.tm_min + 1
					sec.setRotorTurningSpeed(turning_speed)
				else:
					sec.setUseInputpower(False)

				sec.setLNBSlotMask(tunermask)

				# finally add the orbital positions
				for y in lnbSat[x]:
					self.addSatellite(sec, y)
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
		self.configuredSatellites = Set()
		self.update()

class NIM(object):
	def __init__(self, slot, type, description, has_outputs = True, internally_connectable = None):
		self.slot = slot

		if type not in ["DVB-S", "DVB-C", "DVB-T", "DVB-S2", None]:
			print "warning: unknown NIM type %s, not using." % type
			type = None

		self.type = type
		self.description = description
		self.has_outputs = has_outputs
		self.internally_connectable = internally_connectable

	def isCompatible(self, what):
		compatible = {
				None: [None],
				"DVB-S": ["DVB-S", None],
				"DVB-C": ["DVB-C", None],
				"DVB-T": ["DVB-T", None],
				"DVB-S2": ["DVB-S", "DVB-S2", None]
			}
		return what in compatible[self.type]
	
	def connectableTo(self):
		connectable = {
				"DVB-S": ["DVB-S", "DVB-S2"],
				"DVB-C": ["DVB-C"],
				"DVB-T": ["DVB-T"],
				"DVB-S2": ["DVB-S", "DVB-S2"]
			}
		return connectable[self.type]

	def getSlotName(self):
		# get a friendly description for a slot name.
		# we name them "Tuner A/B/C/...", because that's what's usually written on the back
		# of the device.
		return _("Tuner ") + chr(ord('A') + self.slot)

	slot_name = property(getSlotName)

	def getSlotID(self):
		return chr(ord('A') + self.slot)
	
	def hasOutputs(self):
		return self.has_outputs
	
	def internallyConnectableTo(self):
		return self.internally_connectable

	slot_id = property(getSlotID)

	def getFriendlyType(self):
		return {
			"DVB-S": "DVB-S", 
			"DVB-T": "DVB-T",
			"DVB-S2": "DVB-S2",
			"DVB-C": "DVB-C",
			None: _("empty")
			}[self.type]

	friendly_type = property(getFriendlyType)

	def getFriendlyFullDescription(self):
		nim_text = self.slot_name + ": "
			
		if self.empty:
			nim_text += _("(empty)")
		else:
		 	nim_text += self.description + " (" + self.friendly_type + ")"
		
		return nim_text

	friendly_full_description = property(getFriendlyFullDescription)
	config_mode = property(lambda self: config.Nims[self.slot].configMode.value)
	config = property(lambda self: config.Nims[self.slot])
	empty = property(lambda self: self.type is None)

class NimManager:
	def getConfiguredSats(self):
		return self.sec.getConfiguredSats()

	def getTransponders(self, pos):
		if self.transponders.has_key(pos):
			return self.transponders[pos]
		else:
			return []

	def getTranspondersCable(self, nim):
		nimConfig = config.Nims[nim]
		if nimConfig.configMode.value != "nothing" and nimConfig.cable.scan_type.value == "provider":
			return self.transponderscable[self.cablesList[nimConfig.cable.scan_provider.index][0]]
		return [ ]

	def getTranspondersTerrestrial(self, region):
		return self.transpondersterrestrial[region]
	
	def getCableDescription(self, nim):
		return self.cablesList[config.Nims[nim].scan_provider.index][0]

	def getCableFlags(self, nim):
		return self.cablesList[config.Nims[nim].scan_provider.index][1]

	def getTerrestrialDescription(self, nim):
		return self.terrestrialsList[config.Nims[nim].terrestrial.index][0]

	def getTerrestrialFlags(self, nim):
		return self.terrestrialsList[config.Nims[nim].terrestrial.index][1]

	def getSatDescription(self, pos):
		return self.satellites[pos]

	def readTransponders(self):
		# read initial networks from file. we only read files which we are interested in,
		# which means only these where a compatible tuner exists.
		self.satellites = { }
		self.transponders = { }
		self.transponderscable = { }
		self.transpondersterrestrial = { }
		db = eDVBDB.getInstance()
		if self.hasNimType("DVB-S"):
			print "Reading satellites.xml"
			db.readSatellites(self.satList, self.satellites, self.transponders)
#			print "SATLIST", self.satList
#			print "SATS", self.satellites
#			print "TRANSPONDERS", self.transponders

		if self.hasNimType("DVB-C"):
			print "Reading cables.xml"
			db.readCables(self.cablesList, self.transponderscable)
#			print "CABLIST", self.cablesList
#			print "TRANSPONDERS", self.transponders

		if self.hasNimType("DVB-T"):
			print "Reading terrestrial.xml"
			db.readTerrestrials(self.terrestrialsList, self.transpondersterrestrial)
#			print "TERLIST", self.terrestrialsList
#			print "TRANSPONDERS", self.transpondersterrestrial

	def enumerateNIMs(self):
		# enum available NIMs. This is currently very dreambox-centric and uses the /proc/bus/nim_sockets interface.
		# the result will be stored into nim_slots.
		# the content of /proc/bus/nim_sockets looks like:
		# NIM Socket 0:
		#          Type: DVB-S
		#          Name: BCM4501 DVB-S2 NIM (internal)
		# NIM Socket 1:
		#          Type: DVB-S
		#          Name: BCM4501 DVB-S2 NIM (internal)
		# NIM Socket 2:
		#          Type: DVB-T
		#          Name: Philips TU1216
		# NIM Socket 3:
		#          Type: DVB-S
		#          Name: Alps BSBE1 702A
		
		#
		# Type will be either "DVB-S", "DVB-S2", "DVB-T", "DVB-C" or None.

		# nim_slots is an array which has exactly one entry for each slot, even for empty ones.
		self.nim_slots = [ ]

		nimfile = tryOpen("/proc/bus/nim_sockets")

		if nimfile is None:
			return

		current_slot = None

		entries = {}
		for line in nimfile.readlines():
			if line == "":
				break
			if line.strip().startswith("NIM Socket"):
				parts = line.strip().split(" ")
				current_slot = int(parts[2][:-1])
				entries[current_slot] = {}
			elif line.strip().startswith("Type:"):
				entries[current_slot]["type"] = str(line.strip()[6:])
			elif line.strip().startswith("Name:"):
				entries[current_slot]["name"] = str(line.strip()[6:])
			elif line.strip().startswith("Has_Outputs:"):
				input = str(line.strip()[len("Has_Outputs:") + 1:])
				entries[current_slot]["has_outputs"] = (input == "yes")
			elif line.strip().startswith("Internally_Connectable:"):
				input = int(line.strip()[len("Internally_Connectable:") + 1:])
				entries[current_slot]["internally_connectable"] = input 
			elif line.strip().startswith("empty"):
				entries[current_slot]["type"] = None
				entries[current_slot]["name"] = _("N/A")
		nimfile.close()
		
		for id, entry in entries.items():
			if not (entry.has_key("name") and entry.has_key("type")):
				entry["name"] =  _("N/A")
				entry["type"] = None
			if not (entry.has_key("has_outputs")):
				entry["has_outputs"] = True
			if not (entry.has_key("internally_connectable")):
				entry["internally_connectable"] = None
			self.nim_slots.append(NIM(slot = id, description = entry["name"], type = entry["type"], has_outputs = entry["has_outputs"], internally_connectable = entry["internally_connectable"]))

	def hasNimType(self, chktype):
		for slot in self.nim_slots:
			if slot.isCompatible(chktype):
				return True
		return False
	
	def getNimType(self, slotid):
		return self.nim_slots[slotid].type
	
	def getNimDescription(self, slotid):
		return self.nim_slots[slotid].friendly_full_description

	def getNimListOfType(self, type, exception = -1):
		# returns a list of indexes for NIMs compatible to the given type, except for 'exception'
		list = []
		for x in self.nim_slots:
			if x.isCompatible(type) and x.slot != exception:
				list.append(x.slot)
		return list

	def __init__(self):
		self.satList = [ ]
		self.cablesList = []
		self.terrestrialsList = []
		self.enumerateNIMs()
		self.readTransponders()
		InitNimManager(self)	#init config stuff

	# get a list with the friendly full description
	def nimList(self):
		list = [ ]
		for slot in self.nim_slots:
			list.append(slot.friendly_full_description)
		return list
	
	def getSlotCount(self):
		return len(self.nim_slots)
	
	def hasOutputs(self, slotid):
		return self.nim_slots[slotid].hasOutputs()
	
	def canConnectTo(self, slotid):
		slots = []
		if self.nim_slots[slotid].internallyConnectableTo() is not None:
			slots.append(self.nim_slots[slotid].internallyConnectableTo())
		for type in self.nim_slots[slotid].connectableTo(): 
			for slot in self.getNimListOfType(type, exception = slotid):
				# FIXME we restrict loopthrough from dvb-s2 to dvb-s, because the c++ part can't handle it
				if not (type == "DVB-S" and self.getNimType(slot)):
					if self.hasOutputs(slot):
						slots.append(slot)
		slots.sort()
		
		return slots
	
	def canEqualTo(self, slotid):
		type = self.getNimType(slotid)
		if self.getNimConfig(slotid) == "DVB-S2":
			type = "DVB-S"
		nimList = self.getNimListOfType(type, slotid)
		for nim in nimList[:]:
			mode = self.getNimConfig(nim)
			if mode.configMode.value == "loopthrough" or mode.configMode.value == "satposdepends":
				nimList.remove(nim)
		return nimList
	
	def canDependOn(self, slotid):
		type = self.getNimType(slotid)
		if self.getNimConfig(slotid) == "DVB-S2":
			type = "DVB-S"
		nimList = self.getNimListOfType(type, slotid)
		positionerList = []
		for nim in nimList[:]:
			mode = self.getNimConfig(nim)
			if mode.configMode.value == "simple" and mode.diseqcMode.value == "positioner":
				alreadyConnected = False
				for testnim in nimList:
					testmode = self.getNimConfig(testnim)
					if testmode.configMode.value == "satposdepends" and int(testmode.connectedTo.value) == int(nim):
						alreadyConnected = True
						break
				if not alreadyConnected:
					positionerList.append(nim)
		return positionerList
	
	def getNimConfig(self, slotid):
		return config.Nims[slotid]

	def getSatList(self):
		return self.satList

	def getSatListForNim(self, slotid):
		list = []
		if self.nim_slots[slotid].isCompatible("DVB-S"):
			#print "slotid:", slotid

			#print "self.satellites:", self.satList[config.Nims[slotid].diseqcA.index]
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
		if self.nim_slots[slotid].isCompatible("DVB-S"):
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

	x = ConfigInteger(default=200, limits = (0, 9999))
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

	x = ConfigInteger(default=360, limits = (0, 9999))
	x.addNotifier(lambda configElement: secClass.setParam(secClass.MOTOR_RUNNING_TIMEOUT, configElement.value))
	config.sec.motor_running_timeout = x

	x = ConfigInteger(default=1, limits = (0, 5))
	x.addNotifier(lambda configElement: secClass.setParam(secClass.MOTOR_COMMAND_RETRIES, configElement.value))
	config.sec.motor_command_retries = x

	x = ConfigInteger(default=20, limits = (0, 9999))
	x.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_AFTER_VOLTAGE_CHANGE_BEFORE_SWITCH_CMDS, configElement.value))
	config.sec.delay_after_change_voltage_before_switch_command = x

# TODO add support for satpos depending nims to advanced nim configuration
# so a second/third/fourth cable from a motorized lnb can used behind a
# diseqc 1.0 / diseqc 1.1 / toneburst switch
# the C(++) part should can handle this
# the configElement should be only visible when diseqc 1.2 is disabled

def InitNimManager(nimmgr):
	InitSecParams()

	config.Nims = ConfigSubList()
	for x in range(len(nimmgr.nim_slots)):
		config.Nims.append(ConfigSubsection())

	for slot in nimmgr.nim_slots:
		x = slot.slot
		nim = config.Nims[x]
		
		if slot.isCompatible("DVB-S"):
			choices = { "nothing": _("nothing connected"),
					"simple": _("simple"),
					"advanced": _("advanced")}
			if len(nimmgr.getNimListOfType(slot.type, exception = x)) > 0:
				choices["equal"] = _("equal to")
				choices["satposdepends"] = _("second cable of motorized LNB")
			if len(nimmgr.canConnectTo(x)) > 0:
				choices["loopthrough"] = _("loopthrough to")
			nim.configMode = ConfigSelection(choices = choices, default = "nothing")

			#important - check if just the 2nd one is LT only and the first one is DVB-S
			# CHECKME: is this logic correct for >2 slots?
#			if nim.configMode.value in ["loopthrough", "satposdepends", "equal"]:
#				if x == 0: # first one can never be linked to anything
#					# reset to simple
#					nim.configMode.value = "simple"
#					nim.configMode.save()
#				else:
					#FIXME: make it better
			for y in nimmgr.nim_slots:
				if y.slot == 0:
					if not y.isCompatible("DVB-S"):
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

			choices = []
			for id in nimmgr.getNimListOfType("DVB-S"):
				if id != x:
					choices.append((str(id), nimmgr.getNimDescription(id)))
			nim.connectedTo = ConfigSelection(choices = choices)
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
			nim.powerMeasurement = ConfigYesNo(default=True)
			nim.powerThreshold = ConfigInteger(default=50, limits=(0, 100))
			nim.turningSpeed = ConfigSelection(choices = [("fast", _("Fast")), ("slow", _("Slow")), ("fast epoch", _("Fast epoch")) ], default = "fast")
			btime = datetime(1970, 1, 1, 7, 0);
			nim.fastTurningBegin = ConfigDateTime(default = mktime(btime.timetuple()), formatstring = _("%H:%M"), increment = 900)
			etime = datetime(1970, 1, 1, 19, 0);
			nim.fastTurningEnd = ConfigDateTime(default = mktime(etime.timetuple()), formatstring = _("%H:%M"), increment = 900)

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
				nim.advanced.lnb[x].turningSpeed = ConfigSelection(choices = [("fast", _("Fast")), ("slow", _("Slow")), ("fast epoch", _("Fast epoch"))], default = "fast")
				btime = datetime(1970, 1, 1, 7, 0);
				nim.advanced.lnb[x].fastTurningBegin = ConfigDateTime(default=mktime(btime.timetuple()), formatstring = _("%H:%M"), increment = 600)
				etime = datetime(1970, 1, 1, 19, 0);
				nim.advanced.lnb[x].fastTurningEnd = ConfigDateTime(default=mktime(etime.timetuple()), formatstring = _("%H:%M"), increment = 600)
		elif slot.isCompatible("DVB-C"):
			nim.configMode = ConfigSelection(
				choices = {
					"enabled": _("enabled"),
					"nothing": _("nothing connected"),
					},
				default = "enabled")
			list = [ ]
			n = 0
			for x in nimmgr.cablesList:
				list.append((str(n), x[0]))
				n += 1
			nim.cable = ConfigSubsection()
			possible_scan_types = [("bands", _("Frequency bands")), ("steps", _("Frequency steps"))]
			if n:
				possible_scan_types.append(("provider", _("Provider")))
				nim.cable.scan_provider = ConfigSelection(default = "0", choices = list)
			nim.cable.scan_type = ConfigSelection(default = "bands", choices = possible_scan_types)
			nim.cable.scan_band_EU_VHF_I = ConfigYesNo(default = True)
			nim.cable.scan_band_EU_MID = ConfigYesNo(default = True)
			nim.cable.scan_band_EU_VHF_III = ConfigYesNo(default = True)
			nim.cable.scan_band_EU_UHF_IV = ConfigYesNo(default = True)
			nim.cable.scan_band_EU_UHF_V = ConfigYesNo(default = True)
			nim.cable.scan_band_EU_SUPER = ConfigYesNo(default = True)
			nim.cable.scan_band_EU_HYPER = ConfigYesNo(default = True)
			nim.cable.scan_band_US_LOW = ConfigYesNo(default = False)
			nim.cable.scan_band_US_MID = ConfigYesNo(default = False)
			nim.cable.scan_band_US_HIGH = ConfigYesNo(default = False)
			nim.cable.scan_band_US_SUPER = ConfigYesNo(default = False)
			nim.cable.scan_band_US_HYPER = ConfigYesNo(default = False)
			nim.cable.scan_frequency_steps = ConfigInteger(default = 1000, limits = (1000, 10000))
			nim.cable.scan_mod_qam16 = ConfigYesNo(default = False)
			nim.cable.scan_mod_qam32 = ConfigYesNo(default = False)
			nim.cable.scan_mod_qam64 = ConfigYesNo(default = True)
			nim.cable.scan_mod_qam128 = ConfigYesNo(default = False)
			nim.cable.scan_mod_qam256 = ConfigYesNo(default = True)
			nim.cable.scan_sr_6900 = ConfigYesNo(default = True)
			nim.cable.scan_sr_6875 = ConfigYesNo(default = True)
			nim.cable.scan_sr_ext1 = ConfigInteger(default = 0, limits = (0, 7230))
			nim.cable.scan_sr_ext2 = ConfigInteger(default = 0, limits = (0, 7230))
		elif slot.isCompatible("DVB-T"):
			nim.configMode = ConfigSelection(
				choices = {
					"enabled": _("enabled"),
					"nothing": _("nothing connected"),
					},
				default = "enabled")
			list = []
			n = 0
			for x in nimmgr.terrestrialsList:
				list.append((str(n), x[0]))
				n += 1
			nim.terrestrial = ConfigSelection(choices = list)
			nim.terrestrial_5V = ConfigOnOff()
		else:
			nim.configMode = ConfigSelection(choices = { "nothing": _("disabled") }, default="nothing");
			print "pls add support for this frontend type!"		
#			assert False

	nimmgr.sec = SecConfigure(nimmgr)

nimmanager = NimManager()

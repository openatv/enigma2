from time import localtime, mktime
from datetime import datetime
import xml.etree.cElementTree
import os

from enigma import  eDVBFrontendParametersSatellite, \
	eDVBSatelliteEquipmentControl as secClass, \
	eDVBSatelliteDiseqcParameters as diseqcParam, \
	eDVBSatelliteSwitchParameters as switchParam, \
	eDVBSatelliteRotorParameters as rotorParam, \
	eDVBResourceManager, eDVBDB, eEnv

from Tools.HardwareInfo import HardwareInfo
from Tools.BoundFunction import boundFunction
from Components.About import about
from config import config, ConfigSubsection, ConfigSelection, ConfigFloat, ConfigSatlist, ConfigYesNo, ConfigInteger, ConfigSubList, ConfigNothing, ConfigSubDict, ConfigOnOff, ConfigDateTime, ConfigText

config.unicable = ConfigSubsection()

def getConfigSatlist(orbpos, satlist):
	default_orbpos = None
	for x in satlist:
		if x[0] == orbpos:
			default_orbpos = orbpos
			break
	return ConfigSatlist(satlist, default_orbpos)

class SecConfigure:
	def getConfiguredSats(self):
		return self.configuredSatellites

	def addSatellite(self, sec, orbpos):
		sec.addSatellite(orbpos)
		self.configuredSatellites.add(orbpos)

	def addLNBSimple(self, sec, slotid, diseqcmode, toneburstmode = diseqcParam.NO, diseqcpos = diseqcParam.SENDNO, orbpos = 0, longitude = 0, latitude = 0, loDirection = 0, laDirection = 0, turningSpeed = rotorParam.FAST, useInputPower=True, inputPowerDelta=50, fastDiSEqC = False, setVoltageTone = True, diseqc13V = False, CircularLNB = False):
		if orbpos is None or orbpos == 3600 or orbpos == 3601:
			return
		#simple defaults
		sec.addLNB()
		tunermask = 1 << slotid
		if slotid in self.equal:
			for slot in self.equal[slotid]:
				tunermask |= (1 << slot)
		if slotid in self.linked:
			for slot in self.linked[slotid]:
				tunermask |= (1 << slot)
		sec.setLNBSatCRformat(0)
		sec.setLNBNum(1)
		sec.setLNBLOFL(CircularLNB and 10750000 or 9750000)
		sec.setLNBLOFH(CircularLNB and 10750000 or 10600000)
		sec.setLNBThreshold(CircularLNB and 10750000 or 11700000)
		sec.setLNBIncreasedVoltage(False)
		sec.setRepeats(0)
		sec.setFastDiSEqC(fastDiSEqC)
		sec.setSeqRepeat(False)
		sec.setCommandOrder(0)

		#user values

		sec.setDiSEqCMode(3 if diseqcmode == 4 else diseqcmode)
		sec.setToneburst(toneburstmode)
		sec.setCommittedCommand(diseqcpos)
		sec.setUncommittedCommand(0) # SENDNO

		if 0 <= diseqcmode < 3:
			self.addSatellite(sec, orbpos)
			if setVoltageTone:
				sec.setVoltageMode(switchParam.HV_13 if diseqc13V else switchParam.HV)
				sec.setToneMode(switchParam.HILO)
			else:
				# noinspection PyProtectedMember
				sec.setVoltageMode(switchParam._14V)
				sec.setToneMode(switchParam.OFF)
		elif 3 <= diseqcmode < 5: # diseqc 1.2
			if slotid in self.satposdepends:
				for slot in self.satposdepends[slotid]:
					tunermask |= (1 << slot)
			sec.setLatitude(latitude)
			sec.setLaDirection(laDirection)
			sec.setLongitude(longitude)
			sec.setLoDirection(loDirection)
			sec.setUseInputpower(useInputPower)
			sec.setInputpowerDelta(inputPowerDelta)
			sec.setRotorTurningSpeed(turningSpeed)
			user_satList = self.NimManager.satList
			if diseqcmode == 4:
				user_satList = []
				if orbpos and isinstance(orbpos, str):
					orbpos = orbpos.replace("]", "").replace("[", "")
					for user_sat in self.NimManager.satList:
						sat_str = str(user_sat[0])
						if ("," not in orbpos and sat_str == orbpos) or ((', ' + sat_str + ',' in orbpos) or (orbpos.startswith(sat_str + ',')) or (orbpos.endswith(', ' + sat_str))):
							user_satList.append(user_sat)
			for x in user_satList:
				print "[SecConfigure] Add sat " + str(x[0])
				self.addSatellite(sec, int(x[0]))
				sec.setVoltageMode(switchParam.HV_13 if diseqc13V else switchParam.HV)
				sec.setToneMode(switchParam.HILO)
				sec.setRotorPosNum(0) # USALS

		sec.setLNBSlotMask(tunermask)

	def setSatposDepends(self, sec, nim1, nim2):
		print "[SecConfigure] tuner", nim1, "depends on satpos of", nim2
		sec.setTunerDepends(nim1, nim2)

	def linkInternally(self, slotid):
		nim = self.NimManager.getNim(slotid)
		if nim.internallyConnectableTo is not None:
			nim.setInternalLink()

	def linkNIMs(self, sec, nim1, nim2):
		print "[SecConfigure] link tuner", nim1, "to tuner", nim2
		# for internally connect tuner A to B
		if '7356' not in about.getChipSetString() and nim2 == (nim1 - 1):
			self.linkInternally(nim1)
		elif '7356' in about.getChipSetString():
			self.linkInternally(nim1)
		sec.setTunerLinked(nim1, nim2)

	def getRoot(self, slotid, connto):
		visited = []
		while self.NimManager.getNimConfig(connto).configMode.value in ("satposdepends", "equal", "loopthrough"):
			connto = int(self.NimManager.getNimConfig(connto).connectedTo.value)
			if connto in visited: # prevent endless loop
				return slotid
			visited.append(connto)
		return connto

	def update(self):
		sec = secClass.getInstance()
		self.configuredSatellites = set()
		for slotid in self.NimManager.getNimListOfType("DVB-S"):
			if self.NimManager.nimInternallyConnectableTo(slotid) is not None:
				self.NimManager.nimRemoveInternalLink(slotid)
		sec.clear() ## this do unlinking NIMs too !!
		print "[SecConfigure] sec config cleared"

		self.linked = { }
		self.satposdepends = { }
		self.equal = { }

		nim_slots = self.NimManager.nim_slots

		used_nim_slots = [ ]

		for slot in nim_slots:
			if slot.type is not None:
				used_nim_slots.append((slot.slot, slot.description, slot.config.configMode.value != "nothing" and True or False, slot.isCompatible("DVB-S2"), slot.frontend_id is None and -1 or slot.frontend_id))
		eDVBResourceManager.getInstance().setFrontendSlotInformations(used_nim_slots)

		for slot in nim_slots:
			x = slot.slot
			nim = slot.config
			if slot.isCompatible("DVB-S"):
				# save what nim we link to/are equal to/satposdepends to.
				# this is stored in the *value* (not index!) of the config list
				if nim.configMode.value == "equal":
					connto = self.getRoot(x, int(nim.connectedTo.value))
					if connto not in self.equal:
						self.equal[connto] = []
					self.equal[connto].append(x)
				elif nim.configMode.value == "loopthrough":
					self.linkNIMs(sec, x, int(nim.connectedTo.value))
					connto = self.getRoot(x, int(nim.connectedTo.value))
					if connto not in self.linked:
						self.linked[connto] = []
					self.linked[connto].append(x)
				elif nim.configMode.value == "satposdepends":
					self.setSatposDepends(sec, x, int(nim.connectedTo.value))
					connto = self.getRoot(x, int(nim.connectedTo.value))
					if connto not in self.satposdepends:
						self.satposdepends[connto] = []
					self.satposdepends[connto].append(x)

		for slot in nim_slots:
			x = slot.slot
			nim = slot.config
			hw = HardwareInfo()
			if slot.isCompatible("DVB-S"):
				print "[SecConfigure] slot: " + str(x) + " configmode: " + str(nim.configMode.value)
				if nim.configMode.value in ( "loopthrough", "satposdepends", "nothing" ):
					pass
				else:
					sec.setSlotNotLinked(x)
					if nim.configMode.value == "equal":
						pass
					elif nim.configMode.value == "simple":		#simple config
						print "[SecConfigure] diseqcmode: ", nim.diseqcMode.value
						if nim.diseqcMode.value == "single":			#single
							currentCircular = False
							if nim.diseqcA.value in ("360", "560"): 
								currentCircular = nim.simpleDiSEqCSetCircularLNB.value
							if nim.simpleSingleSendDiSEqC.value:
								self.addLNBSimple(sec, slotid = x, orbpos = nim.diseqcA.orbital_position, toneburstmode = diseqcParam.NO, diseqcmode = diseqcParam.V1_0, diseqcpos = diseqcParam.AA, diseqc13V = nim.diseqc13V.value, CircularLNB = currentCircular)
							else:
								self.addLNBSimple(sec, slotid = x, orbpos = nim.diseqcA.orbital_position, toneburstmode = diseqcParam.NO, diseqcmode = diseqcParam.NONE, diseqcpos = diseqcParam.SENDNO, diseqc13V = nim.diseqc13V.value, CircularLNB = currentCircular)
						elif nim.diseqcMode.value == "toneburst_a_b":		#Toneburst A/B
							self.addLNBSimple(sec, slotid = x, orbpos = nim.diseqcA.orbital_position, toneburstmode = diseqcParam.A, diseqcmode = diseqcParam.V1_0, diseqcpos = diseqcParam.SENDNO, diseqc13V = nim.diseqc13V.value)
							self.addLNBSimple(sec, slotid = x, orbpos = nim.diseqcB.orbital_position, toneburstmode = diseqcParam.B, diseqcmode = diseqcParam.V1_0, diseqcpos = diseqcParam.SENDNO, diseqc13V = nim.diseqc13V.value)
						elif nim.diseqcMode.value == "diseqc_a_b":		#DiSEqC A/B
							fastDiSEqC = nim.simpleDiSEqCOnlyOnSatChange.value
							setVoltageTone = nim.simpleDiSEqCSetVoltageTone.value
							self.addLNBSimple(sec, slotid = x, orbpos = nim.diseqcA.orbital_position, toneburstmode = diseqcParam.NO, diseqcmode = diseqcParam.V1_0, diseqcpos = diseqcParam.AA, fastDiSEqC = fastDiSEqC, setVoltageTone = setVoltageTone, diseqc13V = nim.diseqc13V.value)
							self.addLNBSimple(sec, slotid = x, orbpos = nim.diseqcB.orbital_position, toneburstmode = diseqcParam.NO, diseqcmode = diseqcParam.V1_0, diseqcpos = diseqcParam.AB, fastDiSEqC = fastDiSEqC, setVoltageTone = setVoltageTone, diseqc13V = nim.diseqc13V.value)
						elif nim.diseqcMode.value == "diseqc_a_b_c_d":		#DiSEqC A/B/C/D
							fastDiSEqC = nim.simpleDiSEqCOnlyOnSatChange.value
							setVoltageTone = nim.simpleDiSEqCSetVoltageTone.value
							self.addLNBSimple(sec, slotid = x, orbpos = nim.diseqcA.orbital_position, toneburstmode = diseqcParam.NO, diseqcmode = diseqcParam.V1_0, diseqcpos = diseqcParam.AA, fastDiSEqC = fastDiSEqC, setVoltageTone = setVoltageTone, diseqc13V = nim.diseqc13V.value)
							self.addLNBSimple(sec, slotid = x, orbpos = nim.diseqcB.orbital_position, toneburstmode = diseqcParam.NO, diseqcmode = diseqcParam.V1_0, diseqcpos = diseqcParam.AB, fastDiSEqC = fastDiSEqC, setVoltageTone = setVoltageTone, diseqc13V = nim.diseqc13V.value)
							self.addLNBSimple(sec, slotid = x, orbpos = nim.diseqcC.orbital_position, toneburstmode = diseqcParam.NO, diseqcmode = diseqcParam.V1_0, diseqcpos = diseqcParam.BA, fastDiSEqC = fastDiSEqC, setVoltageTone = setVoltageTone, diseqc13V = nim.diseqc13V.value)
							self.addLNBSimple(sec, slotid = x, orbpos = nim.diseqcD.orbital_position, toneburstmode = diseqcParam.NO, diseqcmode = diseqcParam.V1_0, diseqcpos = diseqcParam.BB, fastDiSEqC = fastDiSEqC, setVoltageTone = setVoltageTone, diseqc13V = nim.diseqc13V.value)
						elif nim.diseqcMode.value in ("positioner", "positioner_select"):		#Positioner
							current_mode = 3
							sat = 0
							if nim.diseqcMode.value == "positioner_select":
								current_mode = 4
								sat = nim.userSatellitesList.value
							if nim.latitudeOrientation.value == "north":
								laValue = rotorParam.NORTH
							else:
								laValue = rotorParam.SOUTH
							if nim.longitudeOrientation.value == "east":
								loValue = rotorParam.EAST
							else:
								loValue = rotorParam.WEST
							inputPowerDelta=nim.powerThreshold.value
							useInputPower=False
							turning_speed=0
							if nim.powerMeasurement.value:
								useInputPower=True
								turn_speed_dict = { "fast": rotorParam.FAST, "slow": rotorParam.SLOW }
								if nim.turningSpeed.value in turn_speed_dict:
									turning_speed = turn_speed_dict[nim.turningSpeed.value]
								else:
									beg_time = localtime(nim.fastTurningBegin.value)
									end_time = localtime(nim.fastTurningEnd.value)
									turning_speed = ((beg_time.tm_hour+1) * 60 + beg_time.tm_min + 1) << 16
									turning_speed |= (end_time.tm_hour+1) * 60 + end_time.tm_min + 1
							self.addLNBSimple(sec, slotid = x, diseqcmode = current_mode,
								orbpos = sat,
								longitude = nim.longitude.float,
								loDirection = loValue,
								latitude = nim.latitude.float,
								laDirection = laValue,
								turningSpeed = turning_speed,
								useInputPower = useInputPower,
								inputPowerDelta = inputPowerDelta,
								diseqc13V = nim.diseqc13V.value)
					elif nim.configMode.value == "advanced": #advanced config
						self.updateAdvanced(sec, x)
		print "[SecConfigure] sec config completed"

	def updateAdvanced(self, sec, slotid):
		try:
			if config.Nims[slotid].advanced.unicableconnected is not None:
				if config.Nims[slotid].advanced.unicableconnected.value:
					config.Nims[slotid].advanced.unicableconnectedTo.save_forced = True
					self.linkNIMs(sec, slotid, int(config.Nims[slotid].advanced.unicableconnectedTo.value))
					connto = self.getRoot(slotid, int(config.Nims[slotid].advanced.unicableconnectedTo.value))
					if connto not in self.linked:
						self.linked[connto] = []
					self.linked[connto].append(slotid)
				else:
					config.Nims[slotid].advanced.unicableconnectedTo.save_forced = False
		except:
			pass

		lnbSat = {}
		for x in range(1, 71):
			lnbSat[x] = []

		#wildcard for all satellites ( for rotor )
		for x in range(3601, 3605):
			lnb = int(config.Nims[slotid].advanced.sat[x].lnb.value)
			if lnb != 0:
				for x in self.NimManager.satList:
					print "[SecConfigure] add", x[0], "to", lnb
					lnbSat[lnb].append(x[0])

		#wildcard for user satellites ( for rotor )
		for x in range(3605, 3607):
			lnb = int(config.Nims[slotid].advanced.sat[x].lnb.value)
			if lnb != 0:
				userSatlist = config.Nims[slotid].advanced.sat[x].userSatellitesList.value
				userSatlist = userSatlist.replace("]", "").replace("[", "")
				for user_sat in self.NimManager.satList:
					sat_str = str(user_sat[0])
					if userSatlist and ("," not in userSatlist and sat_str == userSatlist) or ((', ' + sat_str + ',' in userSatlist) or (userSatlist.startswith(sat_str + ',')) or (userSatlist.endswith(', ' + sat_str))):
						print "[SecConfigure] add", user_sat[0], "to", lnb
						lnbSat[lnb].append(user_sat[0])

		for x in self.NimManager.satList:
			lnb = int(config.Nims[slotid].advanced.sat[x[0]].lnb.value)
			if lnb != 0:
				print "[SecConfigure] add", x[0], "to", lnb
				lnbSat[lnb].append(x[0])

		for x in range(1, 71):
			if len(lnbSat[x]) > 0:
				currLnb = config.Nims[slotid].advanced.lnb[x]
				sec.addLNB()

				if x < 65:
					sec.setLNBNum(x)

				tunermask = 1 << slotid
				if slotid in self.equal:
					for slot in self.equal[slotid]:
						tunermask |= (1 << slot)
				if slotid in self.linked:
					for slot in self.linked[slotid]:
						tunermask |= (1 << slot)

				if currLnb.lof.value != "unicable":
					sec.setLNBSatCRformat(0) # Unicable / JESS disabled, 0 = SatCR_format_none
				if currLnb.lof.value == "universal_lnb":
					sec.setLNBLOFL(9750000)
					sec.setLNBLOFH(10600000)
					sec.setLNBThreshold(11700000)
				elif currLnb.lof.value == "unicable":
					sec.setLNBLOFL(currLnb.lofl.value * 1000)
					sec.setLNBLOFH(currLnb.lofh.value * 1000)
					sec.setLNBThreshold(currLnb.threshold.value * 1000)
					sec.setLNBSatCR(currLnb.scrList.index)
					sec.setLNBSatCRvco(currLnb.scrfrequency.value * 1000)
					sec.setLNBSatCRPositionNumber(int(currLnb.positionNumber.value) + int(currLnb.positionsOffset.value))
					sec.setLNBSatCRformat(currLnb.format.value == "jess" and 2 or 1)
				elif currLnb.lof.value == "c_band":
					sec.setLNBLOFL(5150000)
					sec.setLNBLOFH(5150000)
					sec.setLNBThreshold(5150000)
				elif currLnb.lof.value == "user_defined":
					sec.setLNBLOFL(currLnb.lofl.value * 1000)
					sec.setLNBLOFH(currLnb.lofh.value * 1000)
					sec.setLNBThreshold(currLnb.threshold.value * 1000)
				elif currLnb.lof.value == "circular_lnb":
					sec.setLNBLOFL(10750000)
					sec.setLNBLOFH(10750000)
					sec.setLNBThreshold(10750000)

				if currLnb.increased_voltage.value:
					sec.setLNBIncreasedVoltage(True)
				else:
					sec.setLNBIncreasedVoltage(False)

				dm = currLnb.diseqcMode.value
				if dm == "none":
					sec.setDiSEqCMode(diseqcParam.NONE)
				elif dm == "1_0":
					sec.setDiSEqCMode(diseqcParam.V1_0)
				elif dm == "1_1":
					sec.setDiSEqCMode(diseqcParam.V1_1)
				elif dm == "1_2":
					sec.setDiSEqCMode(diseqcParam.V1_2)

					if slotid in self.satposdepends:
						for slot in self.satposdepends[slotid]:
							tunermask |= (1 << slot)

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

					if cdc in c:
						sec.setCommittedCommand(c[cdc])
					else:
						sec.setCommittedCommand(long(cdc))

					sec.setFastDiSEqC(currLnb.fastDiseqc.value)

					sec.setSeqRepeat(currLnb.sequenceRepeat.value)

					if currLnb.diseqcMode.value == "1_0":
						currCO = currLnb.commandOrder1_0.value
						sec.setRepeats(0)
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
						if currLnb.turningSpeed.value in turn_speed_dict:
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

				sec.setLNBPrio(int(currLnb.prio.value))

				# finally add the orbital positions
				for y in lnbSat[x]:
					self.addSatellite(sec, y)
					if x > 64:
						satpos = x > 64 and (3606-(70 - x)) or y
					else:
						satpos = y
					currSat = config.Nims[slotid].advanced.sat[satpos]
					if currSat.voltage.value == "polarization":
						if config.Nims[slotid].diseqc13V.value:
							sec.setVoltageMode(switchParam.HV_13)
						else:
							sec.setVoltageMode(switchParam.HV)
					elif currSat.voltage.value == "13V":
						# noinspection PyProtectedMember
						sec.setVoltageMode(switchParam._14V)
					elif currSat.voltage.value == "18V":
						# noinspection PyProtectedMember
						sec.setVoltageMode(switchParam._18V)

					if currSat.tonemode.value == "band":
						sec.setToneMode(switchParam.HILO)
					elif currSat.tonemode.value == "on":
						sec.setToneMode(switchParam.ON)
					elif currSat.tonemode.value == "off":
						sec.setToneMode(switchParam.OFF)
					if not currSat.usals.value and x < 65:
						sec.setRotorPosNum(currSat.rotorposition.value)
					else:
						sec.setRotorPosNum(0) #USALS

	def __init__(self, nimmgr):
		self.NimManager = nimmgr
		self.configuredSatellites = set()
		self.update()

class NIM(object):
	def __init__(self, slot, type, description, has_outputs = True, internally_connectable = None, multi_type = {}, frontend_id = None, i2c = None, is_empty = False):
		nim_types = ["DVB-S", "DVB-S2", "DVB-C", "DVB-T", "DVB-T2", "ATSC"]

		if type and type not in nim_types:
			print "[NIM] warning: unknown NIM type %s, not using." % type
			type = None

		self.slot = slot
		self.type = type
		self.description = description
		self.has_outputs = has_outputs
		self.internally_connectable = internally_connectable
		self.multi_type = multi_type
		self.i2c = i2c
		self.frontend_id = frontend_id
		self.__is_empty = is_empty

		self.compatible = {
				None: (None,),
				"DVB-S": ("DVB-S", None),
				"DVB-C": ("DVB-C", None),
				"DVB-T": ("DVB-T", None),
				"DVB-S2": ("DVB-S", "DVB-S2", None),
				"DVB-C2": ("DVB-C", "DVB-C2", None),
				"DVB-T2": ("DVB-T", "DVB-T2", None),
				"ATSC": ("ATSC", None),
			}

		# get multi type using delsys information
		if self.frontend_id is not None:
			types = [type for type in nim_types if eDVBResourceManager.getInstance().frontendIsCompatible(self.frontend_id, type)]
			print "[NIM] get types from delsys", types
			if "DVB-T2" in types:
				# DVB-T2 implies DVB-T support
				types.remove("DVB-T")
			if "DVB-S2" in types:
				# DVB-S2 implies DVB-S support
				types.remove("DVB-S")
			if len(types) > 1:
				self.multi_type = {}
				for type in types:
					self.multi_type[str(types.index(type))] = type
			elif len(self.multi_type) > 1:
				print "[NIM] DVB API not reporting tuner %d as multitype" % self.frontend_id

	def isCompatible(self, what):
		return self.isSupported() and what in self.compatible[self.getType()]

	def canBeCompatible(self, what):
		return self.isSupported() and (self.isCompatible(what) or [x for x in self.multi_type.values() if what in self.compatible[x]]) and True

	def getType(self):
		try:
			if self.isMultiType():
				return self.multi_type[self.config.multiType.value]
		except:
			pass
		return self.type

	def connectableTo(self):
		connectable = {
				"DVB-S": ("DVB-S", "DVB-S2"),
				"DVB-C": ("DVB-C", "DVB-C2"),
				"DVB-T": ("DVB-T","DVB-T2"),
				"DVB-S2": ("DVB-S", "DVB-S2"),
				"DVB-C2": ("DVB-C", "DVB-C2"),
				"DVB-T2": ("DVB-T", "DVB-T2"),
				"ATSC": "ATSC",
			}
		return connectable[self.getType()]

	def getSlotID(self, slot=None):
		return chr(ord('A') + (slot if slot is not None else self.slot))

	def getSlotName(self):
		# get a friendly description for a slot name.
		# we name them "Tuner A/B/C/...", because that's what's usually written on the back
		# of the device.
		return "%s %s" % (_("Tuner"), self.slot_id)

	def getI2C(self):
		return self.i2c

	def hasOutputs(self):
		return self.has_outputs

	def internallyConnectableTo(self):
		return self.internally_connectable

	def setInternalLink(self):
		if self.internally_connectable is not None:
			print "[NimManager] setting internal link on frontend id", self.frontend_id
			f = open("/proc/stb/frontend/%d/rf_switch" % self.frontend_id, "w")
			f.write("internal")
			f.close()

	def removeInternalLink(self):
		if self.internally_connectable is not None:
			print "[NimManager] removing internal link on frontend id", self.frontend_id
			f = open("/proc/stb/frontend/%d/rf_switch" % self.frontend_id, "w")
			f.write("external")
			f.close()

	def isMultiType(self):
		return len(self.multi_type) and True

	def isEmpty(self):
		return self.__is_empty

	# empty tuners are supported!
	def isSupported(self):
		return (self.frontend_id is not None) or self.__is_empty

	def isMultistream(self):
		multistream = self.frontend_id is not None and eDVBResourceManager.getInstance().frontendIsMultistream(self.frontend_id) or False
		# HACK due to poor support for VTUNER_SET_FE_INFO
		# When vtuner does not accept fe_info we have to fallback to detection using tuner name
		# More tuner names will be added when confirmed as multistream (FE_CAN_MULTISTREAM)
		if not multistream and "TBS" in self.description:
			multistream = True
		return multistream

	# returns dict {<slotid>: <type>}
	def getMultiTypeList(self):
		return self.multi_type

	def isFBCTuner(self):
		return (self.frontend_id is not None) and os.access("/proc/stb/frontend/%d/fbc_id" % self.frontend_id, os.F_OK)

	def isFBCRoot(self):
		return self.isFBCTuner() and (self.slot % 8 < (self.getType() == "DVB-C" and 1 or 2))

	def isFBCLink(self):
		return self.isFBCTuner() and not (self.slot % 8 < (self.getType() == "DVB-C" and 1 or 2))

	def isNotFirstFBCTuner(self):
		return self.isFBCTuner() and self.slot % 8 and True

	def getFriendlyType(self):
		return self.getType() or _("empty")

	def getFullDescription(self):
		return self.empty and _("(empty)") or "%s (%s)" % (self.description, self.isSupported() and self.friendly_type or _("not supported"))

	def getFriendlyFullDescription(self):
		return "%s: %s" % (self.slot_name, self.getFullDescription())

	def getFriendlyFullDescriptionCompressed(self):
		if self.isFBCTuner():
			return "%s %s-%s: %s" % (_("Tuner"), self.getSlotID(self.slot - (self.slot % 8)), self.getSlotID((self.slot - (self.slot % 8)) + 7), self.getFullDescription())
		#compress by combining dual tuners by checking if the next tuner has a rf switch
		elif os.access("/proc/stb/frontend/%d/rf_switch" % (self.frontend_id + 1), os.F_OK):
			return "%s-%s: %s" % (self.slot_name, self.getSlotID(self.slot + 1), self.getFullDescription())
		return self.getFriendlyFullDescription()

	slot_id = property(getSlotID)
	slot_name = property(getSlotName)
	friendly_full_description = property(getFriendlyFullDescription)
	friendly_full_description_compressed = property(getFriendlyFullDescriptionCompressed)
	friendly_type = property(getFriendlyType)
	config_mode = property(lambda self: config.Nims[self.slot].configMode.value)
	config = property(lambda self: config.Nims[self.slot])
	empty = property(lambda self: self.getType() is None)

class NimManager:
	def getConfiguredSats(self):
		return self.sec.getConfiguredSats()

	def getTransponders(self, pos, feid = None):
		if pos in self.transponders:
			if feid is None or self.nim_slots[feid].isMultistream():
				return self.transponders[pos]
			else: # remove multistream transponders
				return [tp for tp in self.transponders[pos] if not (tp[5] == eDVBFrontendParametersSatellite.System_DVB_S2 and (tp[10] > -1 or tp[11] > 0 or tp[12] > 1))]
		else:
			return []

	def getTranspondersCable(self, nim):
		nimConfig = config.Nims[nim]
		if nimConfig.configMode.value != "nothing" and nimConfig.cable.scan_type.value == "provider":
			return self.transponderscable[self.cablesList[nimConfig.cable.scan_provider.index][0]]
		return [ ]

	def getTranspondersTerrestrial(self, region):
		return self.transpondersterrestrial[region]

	def getTranspondersATSC(self, nim):
		nimConfig = config.Nims[nim]
		if nimConfig.configMode.value != "nothing":
			return self.transpondersatsc[self.atscList[nimConfig.atsc.index][0]]
		return []

	def getCablesList(self):
		return self.cablesList

	def getCablesCountrycodeList(self):
		countrycodes = []
		for x in self.cablesList:
			if x[2] and x[2] not in countrycodes:
				countrycodes.append(x[2])
		return countrycodes

	def getCablesByCountrycode(self, countrycode):
		if countrycode:
			return [x for x in self.cablesList if x[2] == countrycode]
		return []

	def getCableDescription(self, nim):
		return self.cablesList[config.Nims[nim].cable.scan_provider.index][0]

	def getCableFlags(self, nim):
		return self.cablesList[config.Nims[nim].cable.scan_provider.index][1]
		
	def getCableCountrycode(self, nim):
		return self.cablesList[config.Nims[nim].cable.scan_provider.index][2]

	def getTerrestrialsList(self):
		return self.terrestrialsList

	def getTerrestrialsCountrycodeList(self):
		countrycodes = []
		for x in self.terrestrialsList:
			if x[2] and x[2] not in countrycodes:
				countrycodes.append(x[2])
		return countrycodes

	def getTerrestrialsByCountrycode(self, countrycode):
		if countrycode:
			return [x for x in self.terrestrialsList if x[2] == countrycode]
		return []

	def getTerrestrialDescription(self, nim):
		return self.terrestrialsList[config.Nims[nim].terrestrial.index][0]

	def getTerrestrialFlags(self, nim):
		return self.terrestrialsList[config.Nims[nim].terrestrial.index][1]

	def getTerrestrialCountrycode(self, nim):
		return self.terrestrialsList[config.Nims[nim].terrestrial.index][2]

	def getSatDescription(self, pos):
		return self.satellites[pos]

	def sortFunc(self, x):
		orbpos = x[0]
		if orbpos > 1800:
			return orbpos - 3600
		else:
			return orbpos + 1800

	def readTransponders(self):
		self.satellites = { }
		self.transponders = { }
		self.transponderscable = { }
		self.transpondersterrestrial = { }
		self.transpondersatsc = { }
		db = eDVBDB.getInstance()

		if self.hasNimType("DVB-S"):
			print "[NimManager] Reading satellites.xml"
			db.readSatellites(self.satList, self.satellites, self.transponders)
			self.satList.sort() # sort by orbpos

		if self.hasNimType("DVB-C") or self.hasNimType("DVB-T"):
			print "[NimManager] Reading cables.xml"
			db.readCables(self.cablesList, self.transponderscable)
			print "[NimManager] Reading terrestrial.xml"
			db.readTerrestrials(self.terrestrialsList, self.transpondersterrestrial)

		if self.hasNimType("ATSC"):
			print "[NimManager] Reading atsc.xml"
			db.readATSC(self.atscList, self.transpondersatsc)

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

		if config.clientmode.enabled.value:
			print "[NimManager][enumerateNIMs] Receiver in client mode. Local NIMs will be ignored."
			return

		try:
			nimfile = open("/proc/bus/nim_sockets")
		except IOError:
			return

		current_slot = None

		entries = {}
		for line in nimfile:
			if not line:
				break
			line = line.strip()
			if line.startswith("NIM Socket"):
				parts = line.split(" ")
				current_slot = int(parts[2][:-1])
				entries[current_slot] = {}
			elif line.startswith("Type:"):
				entries[current_slot]["type"] = str(line[6:])
				entries[current_slot]["isempty"] = False
			elif line.startswith("Name:"):
				entries[current_slot]["name"] = str(line[6:])
				entries[current_slot]["isempty"] = False
			elif line.startswith("Has_Outputs:"):
				input = str(line[len("Has_Outputs:") + 1:])
				entries[current_slot]["has_outputs"] = (input == "yes")
			elif line.startswith("Internally_Connectable:"):
				input = int(line[len("Internally_Connectable:") + 1:])
				entries[current_slot]["internally_connectable"] = input
			elif line.startswith("Frontend_Device:"):
				input = int(line[len("Frontend_Device:") + 1:])
				entries[current_slot]["frontend_device"] = input
			elif line.startswith("Mode"):
				# "Mode 1: DVB-T" -> ["Mode 1", "DVB-T"]
				split = line.split(":")
				if len(split) > 1 and split[1]:
					split2 = split[0].split(" ")
					modes = entries[current_slot].get("multi_type", {})
					modes[split2[1]] = split[1].strip()
					entries[current_slot]["multi_type"] = modes
			elif line.startswith("I2C_Device:"):
				input = int(line[len("I2C_Device:") + 1:])
				entries[current_slot]["i2c"] = input
			elif line.startswith("empty"):
				entries[current_slot]["type"] = None
				entries[current_slot]["name"] = _("N/A")
				entries[current_slot]["isempty"] = True
		nimfile.close()

		for id, entry in entries.items():
			print "[NimManager][enumerateNIMs] slot:", id, "- entry:", entry
			if entry.has_key("name") and "SI4768" in entry["name"] and entry.has_key("type") and "C2" in entry["type"]: # temporary workaround for GIGA DVB-C/T2 NIM (SI4768) tuner
				entry["type"] = "DVB-C"
				print "[NimManager][enumerateNIMs] Apply DVB-C workaround for GIGA DVB-C/T2 NIM (SI4768) tuner"
			if not ("name" in entry and "type" in entry):
				entry["name"] =  _("N/A")
				entry["type"] = None
			if "i2c" not in entry:
				entry["i2c"] = None
			if "has_outputs" not in entry:
				entry["has_outputs"] = True
			if "frontend_device" in entry: # check if internally connectable
				if os.path.exists("/proc/stb/frontend/%d/rf_switch" % entry["frontend_device"]):
					entry["internally_connectable"] = entry["frontend_device"] - 1
				else:
					entry["internally_connectable"] = None
			else:
				entry["frontend_device"] = entry["internally_connectable"] = None
			if "multi_type" not in entry:
				entry["multi_type"] = {}
			self.nim_slots.append(NIM(slot = id, description = entry["name"], type = entry["type"], has_outputs = entry["has_outputs"], internally_connectable = entry["internally_connectable"], multi_type = entry["multi_type"], frontend_id = entry["frontend_device"], i2c = entry["i2c"], is_empty = entry["isempty"]))

	def hasNimType(self, chktype):
		return any(slot.canBeCompatible(chktype) for slot in self.nim_slots)

	def getNimType(self, slotid):
		return self.nim_slots[slotid].type

	def getNimDescription(self, slotid):
		return self.nim_slots[slotid].friendly_full_description

	def getNimName(self, slotid):
		return self.nim_slots[slotid].description

	def getNim(self, slotid):
		return self.nim_slots[slotid]

	def getI2CDevice(self, slotid):
		return self.nim_slots[slotid].getI2C()

	def getNimListOfType(self, type, exception = -1):
		# returns a list of indexes for NIMs compatible to the given type, except for 'exception'
		list = [x.slot for x in self.nim_slots if x.isCompatible(type) and x.slot != exception]
		return list

	def __init__(self):
		self.satList = [ ]
		self.cablesList = []
		self.terrestrialsList = []
		self.atscList = []
		self.enumerateNIMs()
		self.readTransponders()
		InitNimManager(self)	#init config stuff

	# get a list with the friendly full description
	def nimList(self):
		return [slot.friendly_full_description for slot in self.nim_slots]

	def nimListCompressed(self):
		return [slot.friendly_full_description_compressed for slot in self.nim_slots if not(slot.isNotFirstFBCTuner() or slot.internally_connectable)]

	def getSlotCount(self):
		return len(self.nim_slots)

	def hasOutputs(self, slotid):
		return self.nim_slots[slotid].hasOutputs()

	def nimInternallyConnectableTo(self, slotid):
		return self.nim_slots[slotid].internallyConnectableTo()

	def nimRemoveInternalLink(self, slotid):
		self.nim_slots[slotid].removeInternalLink()

	def canConnectTo(self, slotid):
		slots = []
		if self.nim_slots[slotid].internallyConnectableTo() is not None:
			slots.append(self.nim_slots[slotid].internallyConnectableTo())
		for type in self.nim_slots[slotid].connectableTo():
			for slot in self.getNimListOfType(type, exception = slotid):
				if self.hasOutputs(slot):
					slots.append(slot)
		# remove nims, that have a conntectedTo reference on
		for testnim in slots[:]:
			for nim in self.getNimListOfType("DVB-S", slotid):
				nimConfig = self.getNimConfig(nim)
				if "configMode" in nimConfig.content.items and nimConfig.configMode.value == "loopthrough" and int(nimConfig.connectedTo.value) == testnim:
					slots.remove(testnim)
					break
		slots.sort()
		return slots

	def canEqualTo(self, slotid):
		type = self.getNimType(slotid)
		type = type[:5] # DVB-S2 --> DVB-S, DVB-T2 --> DVB-T, DVB-C2 --> DVB-C
		nimList = self.getNimListOfType(type, slotid)
		for nim in nimList[:]:
			mode = self.getNimConfig(nim)
			if mode.configMode.value == "loopthrough" or mode.configMode.value == "satposdepends":
				nimList.remove(nim)
		return nimList

	def canDependOn(self, slotid):
		type = self.getNimType(slotid)
		type = type[:5] # DVB-S2 --> DVB-S, DVB-T2 --> DVB-T, DVB-C2 --> DVB-C
		nimList = self.getNimListOfType(type, slotid)
		positionerList = []
		for nim in nimList[:]:
			mode = self.getNimConfig(nim)
			nimHaveRotor = mode.configMode.value == "simple" and mode.diseqcMode.value  in ("positioner", "positioner_select")
			if not nimHaveRotor and mode.configMode.value == "advanced":
				for x in range(3601, 3607):
					lnb = int(mode.advanced.sat[x].lnb.value)
					if lnb != 0:
						nimHaveRotor = True
						break
				if not nimHaveRotor:
					for sat in mode.advanced.sat.values():
						lnb_num = int(sat.lnb.value)
						diseqcmode = lnb_num and mode.advanced.lnb[lnb_num].diseqcMode.value or ""
						if diseqcmode == "1_2":
							nimHaveRotor = True
							break
			if nimHaveRotor:
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

	def getSatName(self, pos):
		for sat in self.satList:
			if sat[0] == pos:
				return sat[1]
		return _("N/A")

	def getSatList(self):
		return self.satList

	# returns True if something is configured to be connected to this nim
	# if slotid == -1, returns if something is connected to ANY nim
	def somethingConnected(self, slotid = -1):
		if slotid == -1:
			connected = False
			for id in range(self.getSlotCount()):
				if self.somethingConnected(id):
					connected = True
			return connected
		else:
			nim = config.Nims[slotid]
			configMode = nim.configMode.value

			if any([self.nim_slots[slotid].isCompatible(x) for x in "DVB-S", "DVB-T", "DVB-C", "ATSC"]):
				return not (configMode == "nothing")

	def getSatListForNim(self, slotid):
		list = []
		if self.nim_slots[slotid].isCompatible("DVB-S"):
			nim = config.Nims[slotid]
			#print "slotid:", slotid

			#print "self.satellites:", self.satList[config.Nims[slotid].diseqcA.index]
			#print "diseqcA:", config.Nims[slotid].diseqcA.value
			configMode = nim.configMode.value

			if configMode == "equal":
				slotid = int(nim.connectedTo.value)
				nim = config.Nims[slotid]
				configMode = nim.configMode.value
			elif configMode == "loopthrough":
				slotid = self.sec.getRoot(slotid, int(nim.connectedTo.value))
				nim = config.Nims[slotid]
				configMode = nim.configMode.value

			if configMode == "simple":
				dm = nim.diseqcMode.value
				if dm in ("single", "toneburst_a_b", "diseqc_a_b", "diseqc_a_b_c_d"):
					if nim.diseqcA.orbital_position < 3600:
						list.append(self.satList[nim.diseqcA.index - 2])
				if dm in ("toneburst_a_b", "diseqc_a_b", "diseqc_a_b_c_d"):
					if nim.diseqcB.orbital_position < 3600:
						list.append(self.satList[nim.diseqcB.index - 2])
				if dm == "diseqc_a_b_c_d":
					if nim.diseqcC.orbital_position < 3600:
						list.append(self.satList[nim.diseqcC.index - 2])
					if nim.diseqcD.orbital_position < 3600:
						list.append(self.satList[nim.diseqcD.index - 2])
				if dm == "positioner":
					for x in self.satList:
						list.append(x)
				if dm == "positioner_select":
					userSatlist = nim.userSatellitesList.value
					userSatlist = userSatlist.replace("]", "").replace("[", "")
					for x in self.satList:
						sat_str = str(x[0])
						if userSatlist and ("," not in userSatlist and sat_str == userSatlist) or ((', ' + sat_str + ',' in userSatlist) or (userSatlist.startswith(sat_str + ',')) or (userSatlist.endswith(', ' + sat_str))):
							list.append(x)
			elif configMode == "advanced":
				for x in range(3601, 3605):
					if int(nim.advanced.sat[x].lnb.value) != 0:
						for x in self.satList:
							list.append(x)
				if not list:
					for x in self.satList:
						if int(nim.advanced.sat[x[0]].lnb.value) != 0:
							list.append(x)
				for x in range(3605, 3607):
					if int(nim.advanced.sat[x].lnb.value) != 0:
						userSatlist = nim.advanced.sat[x].userSatellitesList.value
						userSatlist = userSatlist.replace("]", "").replace("[", "")
						for user_sat in self.satList:
							sat_str = str(user_sat[0])
							if userSatlist and ("," not in userSatlist and sat_str == userSatlist) or ((', ' + sat_str + ',' in userSatlist) or (userSatlist.startswith(sat_str + ',')) or (userSatlist.endswith(', ' + sat_str))) and user_sat not in list:
								list.append(user_sat)
		return list

	def getRotorSatListForNim(self, slotid):
		list = []
		if self.nim_slots[slotid].isCompatible("DVB-S"):
			nim = config.Nims[slotid]
			configMode = nim.configMode.value
			if configMode == "simple":
				if nim.diseqcMode.value == "positioner":
					for x in self.satList:
						list.append(x)
				elif nim.diseqcMode.value == "positioner_select":
					userSatlist = nim.userSatellitesList.value
					userSatlist = userSatlist.replace("]", "").replace("[", "")
					for x in self.satList:
						sat_str = str(x[0])
						if userSatlist and ("," not in userSatlist and sat_str == userSatlist) or ((', ' + sat_str + ',' in userSatlist) or (userSatlist.startswith(sat_str + ',')) or (userSatlist.endswith(', ' + sat_str))):
							list.append(x)
			elif configMode == "advanced":
				for x in range(3601, 3605):
					if int(nim.advanced.sat[x].lnb.value) != 0:
						for x in self.satList:
							list.append(x)
				if not list:
					for x in self.satList:
						lnbnum = int(nim.advanced.sat[x[0]].lnb.value)
						if lnbnum != 0:
							lnb = nim.advanced.lnb[lnbnum]
							if lnb.diseqcMode.value == "1_2":
								list.append(x)
				for x in range(3605, 3607):
					if int(nim.advanced.sat[x].lnb.value) != 0:
						userSatlist = nim.advanced.sat[x].userSatellitesList.value
						userSatlist = userSatlist.replace("]", "").replace("[", "")
						for user_sat in self.satList:
							sat_str = str(user_sat[0])
							if userSatlist and ("," not in userSatlist and sat_str == userSatlist) or ((', ' + sat_str + ',' in userSatlist) or (userSatlist.startswith(sat_str + ',')) or (userSatlist.endswith(', ' + sat_str))) and user_sat not in list:
								list.append(user_sat)
		return list

def InitSecParams():
	config.sec = ConfigSubsection()
	config.sec.delay_after_continuous_tone_disable_before_diseqc = ConfigInteger(default=25, limits = (0, 9999))
	config.sec.delay_after_final_continuous_tone_change = ConfigInteger(default=10, limits = (0, 9999))
	config.sec.delay_after_final_voltage_change = ConfigInteger(default=10, limits = (0, 9999))
	config.sec.delay_between_diseqc_repeats = ConfigInteger(default=120, limits = (0, 9999))
	config.sec.delay_after_last_diseqc_command = ConfigInteger(default=100, limits = (0, 9999))
	config.sec.delay_after_toneburst = ConfigInteger(default=50, limits = (0, 9999))
	config.sec.delay_after_change_voltage_before_switch_command = ConfigInteger(default=75, limits = (0, 9999))
	config.sec.delay_after_enable_voltage_before_switch_command = ConfigInteger(default=200, limits = (0, 9999))
	config.sec.delay_between_switch_and_motor_command = ConfigInteger(default=700, limits = (0, 9999))
	config.sec.delay_after_voltage_change_before_measure_idle_inputpower = ConfigInteger(default=500, limits = (0, 9999))
	config.sec.delay_after_enable_voltage_before_motor_command = ConfigInteger(default=900, limits = (0, 9999))
	config.sec.delay_after_motor_stop_command = ConfigInteger(default=500, limits = (0, 9999))
	config.sec.delay_after_voltage_change_before_motor_command = ConfigInteger(default=500, limits = (0, 9999))
	config.sec.delay_before_sequence_repeat = ConfigInteger(default=70, limits = (0, 9999))
	config.sec.motor_running_timeout = ConfigInteger(default=360, limits = (0, 9999))
	config.sec.motor_command_retries = ConfigInteger(default=1, limits = (0, 5))
	config.sec.delay_after_diseqc_reset_cmd = ConfigInteger(default=50, limits = (0, 9999))
	config.sec.delay_after_diseqc_peripherial_poweron_cmd = ConfigInteger(default=150, limits = (0, 9999))

	config.sec.delay_before_sequence_repeat.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_BEFORE_SEQUENCE_REPEAT, configElement.value))
	config.sec.motor_running_timeout.addNotifier(lambda configElement: secClass.setParam(secClass.MOTOR_RUNNING_TIMEOUT, configElement.value))
	config.sec.motor_command_retries.addNotifier(lambda configElement: secClass.setParam(secClass.MOTOR_COMMAND_RETRIES, configElement.value))
	config.sec.delay_after_diseqc_reset_cmd.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_AFTER_DISEQC_RESET_CMD, configElement.value))
	config.sec.delay_after_diseqc_peripherial_poweron_cmd.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_AFTER_DISEQC_PERIPHERIAL_POWERON_CMD, configElement.value))
	config.sec.delay_after_voltage_change_before_motor_command.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_AFTER_VOLTAGE_CHANGE_BEFORE_MOTOR_CMD, configElement.value))
	config.sec.delay_after_motor_stop_command.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_AFTER_MOTOR_STOP_CMD, configElement.value))
	config.sec.delay_after_enable_voltage_before_motor_command.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_AFTER_ENABLE_VOLTAGE_BEFORE_MOTOR_CMD, configElement.value))
	config.sec.delay_after_voltage_change_before_measure_idle_inputpower.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_AFTER_VOLTAGE_CHANGE_BEFORE_MEASURE_IDLE_INPUTPOWER, configElement.value))
	config.sec.delay_between_switch_and_motor_command.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_BETWEEN_SWITCH_AND_MOTOR_CMD, configElement.value))
	config.sec.delay_after_enable_voltage_before_switch_command.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_AFTER_ENABLE_VOLTAGE_BEFORE_SWITCH_CMDS, configElement.value))
	config.sec.delay_after_change_voltage_before_switch_command.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_AFTER_VOLTAGE_CHANGE_BEFORE_SWITCH_CMDS, configElement.value))
	config.sec.delay_after_toneburst.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_AFTER_TONEBURST, configElement.value))
	config.sec.delay_after_last_diseqc_command.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_AFTER_LAST_DISEQC_CMD, configElement.value))
	config.sec.delay_between_diseqc_repeats.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_BETWEEN_DISEQC_REPEATS, configElement.value))
	config.sec.delay_after_final_voltage_change.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_AFTER_FINAL_VOLTAGE_CHANGE, configElement.value))
	config.sec.delay_after_final_continuous_tone_change.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_AFTER_FINAL_CONT_TONE_CHANGE, configElement.value))
	config.sec.delay_after_continuous_tone_disable_before_diseqc.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_AFTER_CONT_TONE_DISABLE_BEFORE_DISEQC, configElement.value))

# TODO add support for satpos depending nims to advanced nim configuration
# so a second/third/fourth cable from a motorized lnb can used behind a
# diseqc 1.0 / diseqc 1.1 / toneburst switch
# the C(++) part should can handle this
# the configElement should be only visible when diseqc 1.2 is disabled

def InitNimManager(nimmgr, update_slots = []):
	hw = HardwareInfo()
	addNimConfig = False
	try:
		config.Nims
	except:
		addNimConfig = True

	if addNimConfig:
		InitSecParams()
		config.Nims = ConfigSubList()
		for x in range(len(nimmgr.nim_slots)):
			config.Nims.append(ConfigSubsection())

	lnb_choices = {
		"universal_lnb": _("Universal LNB"),
		"unicable": _("SCR (Unicable/JESS)"),
		"c_band": _("C-Band"),
		"circular_lnb": _("Circular LNB"),
		"user_defined": _("User defined")}

	lnb_choices_default = "universal_lnb"

	prio_list = [ ("-1", _("Auto")) ]
	for prio in range(65)+range(14000,14065)+range(19000,19065):
		description = ""
		if prio == 0:
			description = _(" (disabled)")
		elif 0 < prio < 65:
			description = _(" (lower than any auto)")
		elif 13999 < prio < 14066:
			description = _(" (higher than rotor any auto)")
		elif 18999 < prio < 19066:
			description = _(" (higher than any auto)")
		prio_list.append((str(prio), str(prio) + description))

	advanced_lnb_csw_choices = [("none", _("None")), ("AA", _("Port A")), ("AB", _("Port B")), ("BA", _("Port C")), ("BB", _("Port D"))]

	advanced_lnb_ucsw_choices = [("0", _("None"))] + [(str(y), _("Input ") + str(y)) for y in range(1, 17)]

	diseqc_mode_choices = [
		("single", _("Single")), ("toneburst_a_b", _("Toneburst A/B")),
		("diseqc_a_b", "DiSEqC A/B"), ("diseqc_a_b_c_d", "DiSEqC A/B/C/D"),
		("positioner", _("Positioner")), ("positioner_select", _("Positioner (selecting satellites)"))]

	positioner_mode_choices = [("usals", _("USALS")), ("manual", _("manual"))]

	diseqc_satlist_choices = [(3600, _('automatic'), 1), (3601, _('nothing connected'), 1)] + nimmgr.satList

	longitude_orientation_choices = [("east", _("East")), ("west", _("West"))]
	latitude_orientation_choices = [("north", _("North")), ("south", _("South"))]
	turning_speed_choices = [("fast", _("Fast")), ("slow", _("Slow")), ("fast epoch", _("Fast epoch"))]

	advanced_satlist_choices = nimmgr.satList + [
		(3601, _('All satellites 1 (USALS)'), 1), (3602, _('All satellites 2 (USALS)'), 1),
		(3603, _('All satellites 3 (USALS)'), 1), (3604, _('All satellites 4 (USALS)'), 1), (3605, _('Selecting satellites 1 (USALS)'), 1), (3606, _('Selecting satellites 2 (USALS)'), 1)]
	advanced_lnb_choices = [("0", _("not configured"))] + [(str(y), "LNB " + str(y)) for y in range(1, 65)]
	advanced_voltage_choices = [("polarization", _("Polarization")), ("13V", _("13 V")), ("18V", _("18 V"))]
	advanced_tonemode_choices = [("band", _("Band")), ("on", _("On")), ("off", _("Off"))]
	advanced_lnb_toneburst_choices = [("none", _("None")), ("A", _("A")), ("B", _("B"))]
	advanced_lnb_allsat_diseqcmode_choices = [("1_2", _("1.2"))]
	advanced_lnb_diseqcmode_choices = [("none", _("None")), ("1_0", _("1.0")), ("1_1", _("1.1")), ("1_2", _("1.2"))]
	advanced_lnb_commandOrder1_0_choices = [("ct", "DiSEqC 1.0, toneburst"), ("tc", "toneburst, DiSEqC 1.0")]
	advanced_lnb_commandOrder_choices = [
		("ct", "DiSEqC 1.0, toneburst"), ("tc", "toneburst, DiSEqC 1.0"),
		("cut", "DiSEqC 1.0, DiSEqC 1.1, toneburst"), ("tcu", "toneburst, DiSEqC 1.0, DiSEqC 1.1"),
		("uct", "DiSEqC 1.1, DiSEqC 1.0, toneburst"), ("tuc", "toneburst, DiSEqC 1.1, DiSEqC 1.0")]
	advanced_lnb_diseqc_repeat_choices = [("none", _("None")), ("one", _("One")), ("two", _("Two")), ("three", _("Three"))]
	advanced_lnb_fast_turning_btime = mktime(datetime(1970, 1, 1, 7, 0).timetuple())
	advanced_lnb_fast_turning_etime = mktime(datetime(1970, 1, 1, 19, 0).timetuple())

	def configLOFChanged(configElement):
		if configElement.value == "unicable":
			x = configElement.slot_id
			lnb = configElement.lnb_id
			nim = config.Nims[x]
			lnbs = nim.advanced.lnb
			section = lnbs[lnb]
			if isinstance(section.unicable, ConfigNothing):
				def getformat(value, index):
					return index >= 4 and "jess" or "unicable" if value == "dSRC" else value
				def positionsChanged(configEntry):
					section.positionNumber = ConfigSelection(["%d" % (x+1) for x in range(configEntry.value)], default="%d" % min(lnb, configEntry.value))
				def scrListChanged(productparameters, srcfrequencylist, configEntry):
					section.format = ConfigSelection([("unicable", _("SCR Unicable")), ("jess", _("SCR JESS"))], default=productparameters.get("format", "unicable"))
					section.scrfrequency = ConfigInteger(default=int(srcfrequencylist[configEntry.index]))
					section.positions = ConfigInteger(default=int(productparameters.get("positions", 1)))
					section.positions.addNotifier(positionsChanged)
					section.positionsOffset = ConfigInteger(default=int(productparameters.get("positionsoffset", 0)))
					section.lofl = ConfigInteger(default=int(productparameters.get("lofl", 9750)))
					section.lofh = ConfigInteger(default=int(productparameters.get("lofh", 10600)))
					section.threshold = ConfigInteger(default=int(productparameters.get("threshold", 11700)))
				def unicableProductChanged(manufacturer, lnb_or_matrix, configEntry):
					config.unicable.unicableProduct.value = configEntry.value
					config.unicable.unicableProduct.save()
					productparameters = [p for p in [m.getchildren() for m in unicable_xml.find(lnb_or_matrix) if m.get("name") == manufacturer][0] if p.get("name") == configEntry.value][0]
					srcfrequencylist = productparameters.get("scrs").split(",")
					section.scrList = ConfigSelection([("%d" % (x + 1), "SCR %d (%s)" % ((x + 1), srcfrequencylist[x])) for x in range(len(srcfrequencylist))])
					section.scrList.save_forced = True
					section.scrList.addNotifier(boundFunction(scrListChanged, productparameters, srcfrequencylist))
				def unicableManufacturerChanged(lnb_or_matrix, configEntry):
					config.unicable.unicableManufacturer.value = configEntry.value
					config.unicable.unicableManufacturer.save()
					productslist = [p.get("name") for p in [m.getchildren() for m in unicable_xml.find(lnb_or_matrix) if m.get("name") == configEntry.value][0]]
					if not config.unicable.content.items.get("unicableProduct", False) or config.unicable.unicableProduct.value not in productslist:
						config.unicable.unicableProduct = ConfigSelection(productslist)
					config.unicable.unicableProduct.save_forced = True
					section.unicableProduct = ConfigSelection(productslist, default=config.unicable.unicableProduct.value)
					section.unicableProduct.save_forced = True
					section.unicableProduct.addNotifier(boundFunction(unicableProductChanged, configEntry.value, lnb_or_matrix))
				def userScrListChanged(srcfrequencyList, configEntry):
					section.scrfrequency = ConfigInteger(default=int(srcfrequencyList[configEntry.index]), limits=(950, 2150))
					section.lofl = ConfigInteger(default=9750, limits=(950, 2150))
					section.lofh = ConfigInteger(default=10600, limits=(950, 2150))
					section.threshold = ConfigInteger(default=11700, limits=(950, 2150))
				def formatChanged(configEntry):
					section.positions = ConfigInteger(default=configEntry.value == "jess" and 64 or 2)
					section.positions.addNotifier(positionsChanged)
					section.positionsOffset = ConfigInteger(default=0)
					section.scrList = ConfigSelection([("%d" % (x + 1), "SCR %d" % (x + 1)) for x in range(configEntry.value == "jess" and 32 or 8)])
					section.scrList.save_forced = True
					srcfrequencyList = configEntry.value=="jess" and (1210, 1420, 1680, 2040, 984, 1020, 1056, 1092, 1128, 1164, 1256, 1292, 1328, 1364, 1458, 1494, 1530, 1566, 1602,\
						1638, 1716, 1752, 1788, 1824, 1860, 1896, 1932, 1968, 2004, 2076, 2112, 2148) or (1284, 1400, 1516, 1632, 1748, 1864, 1980, 2096)
					section.scrList.addNotifier(boundFunction(userScrListChanged, srcfrequencyList))
				def unicableChanged(configEntry):
					config.unicable.unicable.value = configEntry.value
					config.unicable.unicable.save()
					if configEntry.value == "unicable_matrix":
						manufacturerlist = [m.get("name") for m in unicable_xml.find("matrix")]
						if not config.unicable.content.items.get("unicableManufacturer", False) or config.unicable.unicableManufacturer.value not in manufacturerlist:
							config.unicable.unicableManufacturer = ConfigSelection(manufacturerlist)
						section.unicableManufacturer = ConfigSelection(manufacturerlist, default=config.unicable.unicableManufacturer.value)
						section.unicableManufacturer.save_forced = True
						config.unicable.unicableManufacturer.save_forced = True
						section.unicableManufacturer.addNotifier(boundFunction(unicableManufacturerChanged, "matrix"))
					elif configEntry.value == "unicable_lnb":
						manufacturerlist = [m.get("name") for m in unicable_xml.find("lnb")]
						if not config.unicable.content.items.get("unicableManufacturer", False) or config.unicable.unicableManufacturer.value not in manufacturerlist:
							config.unicable.unicableManufacturer = ConfigSelection(manufacturerlist)
						section.unicableManufacturer = ConfigSelection(manufacturerlist, default=config.unicable.unicableManufacturer.value)
						section.unicableManufacturer.save_forced = True
						config.unicable.unicableManufacturer.save_forced = True
						section.unicableManufacturer.addNotifier(boundFunction(unicableManufacturerChanged, "lnb"))
					else:
						section.format = ConfigSelection([("unicable", _("SCR Unicable")), ("jess", _("SCR JESS"))])
						section.format.addNotifier(formatChanged)

				unicable_xml = xml.etree.cElementTree.parse(eEnv.resolve("${datadir}/enigma2/unicable.xml")).getroot()
				unicableList = [("unicable_lnb", _("SCR (Unicable/JESS)") + " " + _("LNB")), ("unicable_matrix", _("SCR (Unicable/JESS)") + " " + _("Switch")), ("unicable_user", _("SCR (Unicable/JESS)") + " " + _("User defined"))]
				if not config.unicable.content.items.get("unicable", False):
					config.unicable.unicable = ConfigSelection(unicableList)
				section.unicable = ConfigSelection(unicableList, default=config.unicable.unicable.value)
				section.unicable.addNotifier(unicableChanged)

				nim.advanced.unicableconnected = ConfigYesNo(default=False)
				nim.advanced.unicableconnectedTo = ConfigSelection([(str(id), nimmgr.getNimDescription(id)) for id in nimmgr.getNimListOfType("DVB-S") if id != x])

	def configDiSEqCModeChanged(configElement):
		section = configElement.section
		if configElement.value == "1_2" and isinstance(section.longitude, ConfigNothing):
			section.longitude = ConfigFloat(default = [5,100], limits = [(0,359),(0,999)])
			section.longitudeOrientation = ConfigSelection(longitude_orientation_choices, "east")
			section.latitude = ConfigFloat(default = [50,767], limits = [(0,359),(0,999)])
			section.latitudeOrientation = ConfigSelection(latitude_orientation_choices, "north")
			section.tuningstepsize = ConfigFloat(default = [0,360], limits = [(0,9),(0,999)])
			section.rotorPositions = ConfigInteger(default = 99, limits = [1,999])
			section.turningspeedH = ConfigFloat(default = [2,3], limits = [(0,9),(0,9)])
			section.turningspeedV = ConfigFloat(default = [1,7], limits = [(0,9),(0,9)])
			section.powerMeasurement = ConfigYesNo(default=True)
			section.powerThreshold = ConfigInteger(default=15, limits=(0, 100))
			section.turningSpeed = ConfigSelection(turning_speed_choices, "fast")
			section.fastTurningBegin = ConfigDateTime(default=advanced_lnb_fast_turning_btime, formatstring = _("%H:%M"), increment = 600)
			section.fastTurningEnd = ConfigDateTime(default=advanced_lnb_fast_turning_etime, formatstring = _("%H:%M"), increment = 600)

	def configLNBChanged(configElement):
		x = configElement.slot_id
		nim = config.Nims[x]
		if isinstance(configElement.value, tuple):
			lnb = int(configElement.value[0])
		else:
			lnb = int(configElement.value)
		lnbs = nim.advanced.lnb
		if lnb and lnb not in lnbs:
			section = lnbs[lnb] = ConfigSubsection()
			section.lofl = ConfigInteger(default=9750, limits = (0, 99999))
			section.lofh = ConfigInteger(default=10600, limits = (0, 99999))
			section.threshold = ConfigInteger(default=11700, limits = (0, 99999))
			section.increased_voltage = ConfigYesNo(False)
			section.toneburst = ConfigSelection(advanced_lnb_toneburst_choices, "none")
			section.longitude = ConfigNothing()
			if lnb > 64:
				tmp = ConfigSelection(advanced_lnb_allsat_diseqcmode_choices, "1_2")
				tmp.section = section
				configDiSEqCModeChanged(tmp)
			else:
				tmp = ConfigSelection(advanced_lnb_diseqcmode_choices, "none")
				tmp.section = section
				tmp.addNotifier(configDiSEqCModeChanged)
			section.diseqcMode = tmp
			section.commitedDiseqcCommand = ConfigSelection(advanced_lnb_csw_choices)
			section.fastDiseqc = ConfigYesNo(False)
			section.sequenceRepeat = ConfigYesNo(False)
			section.commandOrder1_0 = ConfigSelection(advanced_lnb_commandOrder1_0_choices, "ct")
			section.commandOrder = ConfigSelection(advanced_lnb_commandOrder_choices, "ct")
			section.uncommittedDiseqcCommand = ConfigSelection(advanced_lnb_ucsw_choices)
			section.diseqcRepeats = ConfigSelection(advanced_lnb_diseqc_repeat_choices, "none")
			section.prio = ConfigSelection(prio_list, "-1")
			section.unicable = ConfigNothing()
			tmp = ConfigSelection(lnb_choices, lnb_choices_default)
			tmp.slot_id = x
			tmp.lnb_id = lnb
			tmp.addNotifier(configLOFChanged, initial_call = False)
			section.lof = tmp

	def configModeChanged(configMode):
		slot_id = configMode.slot_id
		nim = config.Nims[slot_id]
		if configMode.value == "advanced" and isinstance(nim.advanced, ConfigNothing):
			# advanced config:
			nim.advanced = ConfigSubsection()
			nim.advanced.sat = ConfigSubDict()
			nim.advanced.sats = getConfigSatlist(192, advanced_satlist_choices)
			nim.advanced.lnb = ConfigSubDict()
			nim.advanced.lnb[0] = ConfigNothing()
			for x in nimmgr.satList:
				tmp = ConfigSubsection()
				tmp.voltage = ConfigSelection(advanced_voltage_choices, "polarization")
				tmp.tonemode = ConfigSelection(advanced_tonemode_choices, "band")
				tmp.usals = ConfigYesNo(True)
				tmp.rotorposition = ConfigInteger(default=1, limits=(1, 255))
				lnb = ConfigSelection(advanced_lnb_choices, "0")
				lnb.slot_id = slot_id
				lnb.addNotifier(configLNBChanged, initial_call = False)
				tmp.lnb = lnb
				nim.advanced.sat[x[0]] = tmp
			for x in range(3601, 3607):
				tmp = ConfigSubsection()
				tmp.voltage = ConfigSelection(advanced_voltage_choices, "polarization")
				tmp.tonemode = ConfigSelection(advanced_tonemode_choices, "band")
				tmp.usals = ConfigYesNo(default=True)
				tmp.userSatellitesList = ConfigText('[]')
				tmp.rotorposition = ConfigInteger(default=1, limits=(1, 255))
				lnbnum = 65+x-3601
				lnb = ConfigSelection([("0", _("not configured")), (str(lnbnum), "LNB %d"%(lnbnum))], "0")
				lnb.slot_id = slot_id
				lnb.addNotifier(configLNBChanged, initial_call = False)
				tmp.lnb = lnb
				nim.advanced.sat[x] = tmp

	def scpcSearchRangeChanged(configElement):
		fe_id = configElement.fe_id
		slot_id = configElement.slot_id
		if os.path.exists("/proc/stb/frontend/%d/use_scpc_optimized_search_range" % fe_id):
			f = open("/proc/stb/frontend/%d/use_scpc_optimized_search_range" % (fe_id), "w")
			f.write(configElement.value)
			f.close()

	def toneAmplitudeChanged(configElement):
		fe_id = configElement.fe_id
		slot_id = configElement.slot_id
		if os.path.exists("/proc/stb/frontend/%d/tone_amplitude" % fe_id):
			f = open("/proc/stb/frontend/%d/tone_amplitude" % fe_id, "w")
			f.write(configElement.value)
			f.close()

	def createSatConfig(nim, x, empty_slots):
		try:
			nim.toneAmplitude
		except:
			nim.toneAmplitude = ConfigSelection([("11", "340mV"), ("10", "360mV"), ("9", "600mV"), ("8", "700mV"), ("7", "800mV"), ("6", "900mV"), ("5", "1100mV")], "7")
			nim.toneAmplitude.fe_id = x - empty_slots
			nim.toneAmplitude.slot_id = x
			nim.toneAmplitude.addNotifier(toneAmplitudeChanged)
			nim.scpcSearchRange = ConfigSelection([("0", _("no")), ("1", _("yes"))], "0")
			nim.scpcSearchRange.fe_id = x - empty_slots
			nim.scpcSearchRange.slot_id = x
			nim.scpcSearchRange.addNotifier(scpcSearchRangeChanged)
			nim.diseqc13V = ConfigYesNo(False)
			nim.diseqcMode = ConfigSelection(diseqc_mode_choices, "single")
			nim.connectedTo = ConfigSelection([(str(id), nimmgr.getNimDescription(id)) for id in nimmgr.getNimListOfType("DVB-S") if id != x])
			nim.simpleSingleSendDiSEqC = ConfigYesNo(False)
			nim.simpleDiSEqCSetVoltageTone = ConfigYesNo(True)
			nim.simpleDiSEqCOnlyOnSatChange = ConfigYesNo(False)
			nim.simpleDiSEqCSetCircularLNB = ConfigYesNo(True)
			nim.diseqcA = ConfigSatlist(list = diseqc_satlist_choices)
			nim.diseqcB = ConfigSatlist(list = diseqc_satlist_choices)
			nim.diseqcC = ConfigSatlist(list = diseqc_satlist_choices)
			nim.diseqcD = ConfigSatlist(list = diseqc_satlist_choices)
			nim.positionerMode = ConfigSelection(positioner_mode_choices, "usals")
			nim.userSatellitesList = ConfigText('[]')
			nim.pressOKtoList = ConfigNothing()
			nim.longitude = ConfigFloat(default=[5,100], limits=[(0,359),(0,999)])
			nim.longitudeOrientation = ConfigSelection(longitude_orientation_choices, "east")
			nim.latitude = ConfigFloat(default=[50,767], limits=[(0,359),(0,999)])
			nim.latitudeOrientation = ConfigSelection(latitude_orientation_choices, "north")
			nim.tuningstepsize = ConfigFloat(default = [0,360], limits = [(0,9),(0,999)])
			nim.rotorPositions = ConfigInteger(default = 99, limits = [1,999])
			nim.turningspeedH = ConfigFloat(default = [2,3], limits = [(0,9),(0,9)])
			nim.turningspeedV = ConfigFloat(default = [1,7], limits = [(0,9),(0,9)])
			nim.powerMeasurement = ConfigYesNo(False)
			nim.powerThreshold = ConfigInteger(default=hw.get_device_name() == "dm8000" and 15 or 50, limits=(0, 100))
			nim.turningSpeed = ConfigSelection(turning_speed_choices, "fast")
			btime = datetime(1970, 1, 1, 7, 0)
			nim.fastTurningBegin = ConfigDateTime(default = mktime(btime.timetuple()), formatstring = _("%H:%M"), increment = 900)
			etime = datetime(1970, 1, 1, 19, 0)
			nim.fastTurningEnd = ConfigDateTime(default = mktime(etime.timetuple()), formatstring = _("%H:%M"), increment = 900)

	def createCableConfig(nim, x):
		try:
			nim.cable
		except:
			#list = [(str(n), x[0]) for n, x in enumerate(nimmgr.cablesList)]
			list = [x[0] for x in nimmgr.cablesList]
			nim.cable = ConfigSubsection()
			nim.cable.scan_networkid = ConfigInteger(default = 0, limits = (0, 99999))
			possible_scan_types = [("bands", _("Frequency bands")), ("steps", _("Frequency steps"))]
			default_scan_type = "bands"
			if list:
				possible_scan_types.append(("provider", _("Provider")))
				default_scan_type = "provider"
				nim.cable.scan_provider = ConfigSelection(choices = list)
			nim.cable.scan_type = ConfigSelection(default = default_scan_type, choices = possible_scan_types)
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

	def createTerrestrialConfig(nim, x):
		try:
			nim.terrestrial
		except:
			#list = [(str(n), x[0]) for n, x in enumerate(nimmgr.terrestrialsList)]
			list = [x[0] for x in nimmgr.terrestrialsList]
			nim.terrestrial = ConfigSelection(choices = list)
			nim.terrestrial_5V = ConfigOnOff()

	def createATSCConfig(nim, x):
		try:
			nim.atsc
		except:
			#list = [(str(n), x[0]) for n, x in enumerate(nimmgr.atscList)]
			list = [x[0]for x in nimmgr.atscList]
			nim.atsc = ConfigSelection(choices = list)

	def tunerTypeChanged(nimmgr, configElement, initial=False):
		fe_id = configElement.fe_id
		eDVBResourceManager.getInstance().setFrontendType(nimmgr.nim_slots[fe_id].frontend_id, nimmgr.nim_slots[fe_id].getType())
		try:
			raw_channel = eDVBResourceManager.getInstance().allocateRawChannel(fe_id)
			if raw_channel is None:
				self.session.nav.stopService()
				raw_channel = eDVBResourceManager.getInstance().allocateRawChannel(fe_id)
				if raw_channel is None:
					print "[InitNimManager] %d: tunerTypeChanged to '%s' failed (BUSY)" %(fe_id, configElement.getText())
					return
			frontend = raw_channel.getFrontend()
			is_changed_mode = os.path.exists("/proc/stb/frontend/%d/mode" % fe_id)
			if not is_changed_mode and frontend.setDeliverySystem(nimmgr.nim_slots[fe_id].getType()):
				print "[InitNimManager] tunerTypeChanged feid %d to mode %d" % (fe_id, int(configElement.value))
				InitNimManager(nimmgr)
				configElement.save()
			elif is_changed_mode:
				cur_type = int(open("/proc/stb/frontend/%d/mode" % (fe_id), "r").read())
				if cur_type != int(configElement.value):
					print "[InitNimManager] tunerTypeChanged feid %d from %d to mode %d" % (fe_id, cur_type, int(configElement.value))

					is_dvb_shutdown_timeout = os.path.exists("/sys/module/dvb_core/parameters/dvb_shutdown_timeout")
					if is_dvb_shutdown_timeout:
						try:
							oldvalue = open("/sys/module/dvb_core/parameters/dvb_shutdown_timeout", "r").readline()
							f = open("/sys/module/dvb_core/parameters/dvb_shutdown_timeout", "w")
							f.write("0")
							f.close()
						except:
							print "[InitNimManager] tunerTypeChanged read /sys/module/dvb_core/parameters/dvb_shutdown_timeout failed"

					frontend.closeFrontend()
					f = open("/proc/stb/frontend/%d/mode" % (fe_id), "w")
					f.write(configElement.value)
					f.close()
					frontend.reopenFrontend()

					if is_dvb_shutdown_timeout:
						try:
							f = open("/sys/module/dvb_core/parameters/dvb_shutdown_timeout", "w")
							f.write(oldvalue)
							f.close()
						except:
							print "[InitNimManager] tunerTypeChanged write to /sys/module/dvb_core/parameters/dvb_shutdown_timeout failed"

					nimmgr.enumerateNIMs()
					if initial:
						print "[InitNimManager] tunerTypeChanged force update setting"
						nimmgr.sec.update()
					configElement.save()
				else:
					print "[InitNimManager] tunerTypeChanged tuner type is already %d" % cur_type
		except Exception as e:
			print "[InitNimManager] tunerTypeChanged error: ", e

	empty_slots = 0
	for slot in nimmgr.nim_slots:
		x = slot.slot
		nim = config.Nims[x]
		addMultiType = False
		try:
			nim.multiType
		except:
			addMultiType = True
		if slot.isMultiType() and addMultiType:
			typeList = []
			for id in slot.getMultiTypeList().keys():
				type = slot.getMultiTypeList()[id]
				typeList.append((id, type))
			nim.multiType = ConfigSelection(typeList, "0")

			nim.multiType.fe_id = x - empty_slots
			nim.multiType.addNotifier(boundFunction(tunerTypeChanged, nimmgr), initial_call=False)
			tunerTypeChanged(nimmgr, nim.multiType, initial=True)

		print"[NimManager] slotname = %s, slotdescription = %s, multitype = %s" % (slot.slot_name, slot.description,(slot.isMultiType() and addMultiType))

	empty_slots = 0
	for slot in nimmgr.nim_slots:
		x = slot.slot
		nim = config.Nims[x]

		if slot.isCompatible("DVB-S"):
			createSatConfig(nim, x, empty_slots)
			config_mode_choices = [("nothing", _("nothing connected")),
				("simple", _("simple")), ("advanced", _("advanced"))]
			if len(nimmgr.getNimListOfType(slot.type, exception = x)) > 0:
				config_mode_choices.append(("equal", _("equal to")))
				config_mode_choices.append(("satposdepends", _("second cable of motorized LNB")))
			if len(nimmgr.canConnectTo(x)) > 0:
				config_mode_choices.append(("loopthrough", _("loopthrough to")))
			nim.advanced = ConfigNothing()
			tmp = ConfigSelection(config_mode_choices, slot.isFBCLink() and "nothing" or "simple")
			tmp.slot_id = x
			tmp.addNotifier(configModeChanged, initial_call = False)
			nim.configMode = tmp
		elif slot.isCompatible("DVB-C"):
			nim.configMode = ConfigSelection(
				choices = {
					"enabled": _("enabled"),
					"nothing": _("nothing connected"),
					},
				default = "enabled")
			createCableConfig(nim, x)
		elif slot.isCompatible("DVB-T"):
			nim.configMode = ConfigSelection(
				choices = {
					"enabled": _("enabled"),
					"nothing": _("nothing connected"),
					},
				default = "enabled")
			createTerrestrialConfig(nim, x)
		elif slot.isCompatible("ATSC"):
			nim.configMode = ConfigSelection(
				choices = {
					"enabled": _("enabled"),
					"nothing": _("nothing connected"),
					},
				default = "enabled")
			createATSCConfig(nim, x)
		else:
			empty_slots += 1
			nim.configMode = ConfigSelection(choices = { "nothing": _("disabled") }, default="nothing")
			if slot.type is not None:
				print "[InitNimManager] pls add support for this frontend type!", slot.type

	nimmgr.sec = SecConfigure(nimmgr)
	empty_slots = 0
	for slot in nimmgr.nim_slots:
		x = slot.slot
		nim = config.Nims[x]
		empty = True

		if update_slots and (x not in update_slots):
			continue

		if slot.canBeCompatible("DVB-S"):
			createSatConfig(nim, x, empty_slots)
			empty = False
		if slot.canBeCompatible("DVB-C"):
			createCableConfig(nim, x)
			empty = False
		if slot.canBeCompatible("DVB-T"):
			createTerrestrialConfig(nim, x)
			empty = False
		if slot.canBeCompatible("ATSC"):
			createATSCConfig(nim, x)
			empty = False
		if empty:
			empty_slots += 1

nimmanager = NimManager()

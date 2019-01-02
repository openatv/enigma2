from boxbranding import getBoxType, getBrandOEM
from time import localtime, mktime
from datetime import datetime
import xml.etree.cElementTree
from os import path

from enigma import eDVBSatelliteEquipmentControl as secClass, \
	eDVBSatelliteLNBParameters as lnbParam, \
	eDVBSatelliteDiseqcParameters as diseqcParam, \
	eDVBSatelliteSwitchParameters as switchParam, \
	eDVBSatelliteRotorParameters as rotorParam, \
	eDVBResourceManager, eDVBDB, eEnv, iDVBFrontend, pNavigation

from Tools.HardwareInfo import HardwareInfo
from Tools.BoundFunction import boundFunction
from Components.About import about
from config import config, ConfigSubsection, ConfigSelection, ConfigFloat, ConfigSatlist, ConfigYesNo, ConfigInteger, ConfigSubList, ConfigNothing, ConfigSubDict, ConfigOnOff, ConfigDateTime, ConfigText

maxFixedLnbPositions = 0

# LNB65 3601 All satellites 1 (USALS)
# LNB66 3602 All satellites 2 (USALS)
# LNB67 3603 All satellites 3 (USALS)
# LNB68 3604 All satellites 4 (USALS)
# LNB69 3605 Selecting satellites 1 (USALS)
# LNB70 3606 Selecting satellites 2 (USALS)
MAX_LNB_WILDCARDS = 6
MAX_ORBITPOSITION_WILDCARDS = 6

#magic numbers
ORBITPOSITION_LIMIT = 3600

iDVBFrontendDict = {
	iDVBFrontend.feSatellite:	"DVB-S",
	iDVBFrontend.feCable:		"DVB-C",
	iDVBFrontend.feTerrestrial:	"DVB-T",
	iDVBFrontend.feATSC:		"ATSC",
}

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
		if sec.addLNB():
			print "No space left on m_lnbs (mac No. 144 LNBs exceeded)"
			return
		tunermask = 1 << slotid
		if self.equal.has_key(slotid):
			for slot in self.equal[slotid]:
				tunermask |= (1 << slot)
		if self.linked.has_key(slotid):
			for slot in self.linked[slotid]:
				tunermask |= (1 << slot)
		sec.setLNBSatCR(-1)
		sec.setLNBSatCRTuningAlgo(0)
		sec.setLNBBootupTime(0)
		sec.setLNBSatCRpositionnumber(1)
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
				if diseqc13V:
					sec.setVoltageMode(switchParam.HV_13)
				else:
					sec.setVoltageMode(switchParam.HV)
				sec.setToneMode(switchParam.HILO)
			else:
				# noinspection PyProtectedMember
				sec.setVoltageMode(switchParam._14V)
				sec.setToneMode(switchParam.OFF)
		elif 3 <= diseqcmode < 5: # diseqc 1.2
			if self.satposdepends.has_key(slotid):
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
					for user_sat in self.NimManager.satList:
						if str(user_sat[0]) in orbpos:
							user_satList.append(user_sat)
			for x in user_satList:
				print "Add sat " + str(x[0])
				self.addSatellite(sec, int(x[0]))
				if diseqc13V:
					sec.setVoltageMode(switchParam.HV_13)
				else:
					sec.setVoltageMode(switchParam.HV)
				sec.setToneMode(switchParam.HILO)
				sec.setRotorPosNum(0) # USALS

		sec.setLNBSlotMask(tunermask)

	def setSatposDepends(self, sec, nim1, nim2):
		print "tuner", nim1, "depends on satpos of", nim2
		sec.setTunerDepends(nim1, nim2)

	def linkInternally(self, slotid):
		nim = self.NimManager.getNim(slotid)
		if nim.internallyConnectableTo is not None:
			nim.setInternalLink()

	def linkNIMs(self, sec, nim1, nim2):
		print "link tuner", nim1, "to tuner", nim2
		# for internally connect tuner A to B
		if getBoxType() == 'vusolo2' or nim2 == (nim1 - 1):
			self.linkInternally(nim1)
		sec.setTunerLinked(nim1, nim2)

	def getRoot(self, slotid, connto):
		visited = []
		while self.NimManager.getNimConfig(connto).dvbs.configMode.value in ("satposdepends", "equal", "loopthrough"):
			connto = int(self.NimManager.getNimConfig(connto).dvbs.connectedTo.value)
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
		print "sec config cleared"

		self.linked = { }
		self.satposdepends = { }
		self.equal = { }

		nim_slots = self.NimManager.nim_slots
		used_nim_slots = [ ]

		try:
			for slot in nim_slots:
				if slot.frontend_id is not None:
					types = [type for type in ["DVB-C", "DVB-T", "DVB-T2", "DVB-S", "DVB-S2", "ATSC"] if eDVBResourceManager.getInstance().frontendIsCompatible(slot.frontend_id, type)]
					if "DVB-T2" in types:
						# DVB-T2 implies DVB-T support
						types.remove("DVB-T")
					if "DVB-S2" in types:
						# DVB-S2 implies DVB-S support
						types.remove("DVB-S")
					if "DVB-S2X" in types:
						# DVB-S2X implies DVB-S2 support
						types.remove("DVB-S2")
					if len(types) > 1:
						slot.multi_type = {}
						for type in types:
							slot.multi_type[str(types.index(type))] = type
		except:
			pass

		for slot in nim_slots:
			if slot.type is not None:
				used_nim_slots.append((
					slot.slot,
					slot.description,
					(slot.canBeCompatible("ATSC") and (slot.config.atsc.configMode.value != "nothing" and True or False)) or
					(slot.canBeCompatible("DVB-S") and (slot.config.dvbs.configMode.value != "nothing" and True or False)) or
					(slot.canBeCompatible("DVB-C") and (slot.config.dvbc.configMode.value != "nothing" and True or False)) or
					(slot.canBeCompatible("DVB-T") and (slot.config.dvbt.configMode.value != "nothing" and True or False)) or
					(slot.canBeCompatible("DVB-S2") and (slot.config.dvbs.configMode.value != "nothing" and True or False)),
					slot.canBeCompatible("DVB-S2X") and (slot.config.dvbs.configMode.value != "nothing" and True or False),
					slot.frontend_id is None and -1 or slot.frontend_id))
		eDVBResourceManager.getInstance().setFrontendSlotInformations(used_nim_slots)

		for slot in nim_slots:
			x = slot.slot
			if slot.canBeCompatible("DVB-S"):
				nim = slot.config.dvbs
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
			hw = HardwareInfo()
			if slot.canBeCompatible("DVB-S"):
				nim = slot.config.dvbs
				print "slot: " + str(x) + " configmode: " + str(nim.configMode.value)
				if nim.configMode.value in ( "loopthrough", "satposdepends", "nothing" ):
					pass
				else:
					sec.setSlotNotLinked(x)
					if nim.configMode.value == "equal":
						pass
					elif nim.configMode.value == "simple":		#simple config
						print "diseqcmode: ", nim.diseqcMode.value
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
								if turn_speed_dict.has_key(nim.turningSpeed.value):
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
			if slot.canBeCompatible("DVB-T"):
				nim = slot.config.dvbt
				print "slot: " + str(x) + " configmode: " + str(nim.configMode.value)
			if slot.canBeCompatible("DVB-C"):
				nim = slot.config.dvbc
				print "slot: " + str(x) + " configmode: " + str(nim.configMode.value)

		for slot in nim_slots:
			if slot.frontend_id is not None:
				if slot.isMultiType():
					eDVBResourceManager.getInstance().setFrontendType(slot.frontend_id, "dummy", False) #to force a clear of m_delsys_whitelist
					types = slot.getMultiTypeList()
					for FeType in types.itervalues():
						if FeType in ("DVB-S", "DVB-S2", "DVB-S2X") and config.Nims[slot.slot].dvbs.configMode.value == "nothing":
							continue
						elif FeType in ("DVB-T", "DVB-T2") and config.Nims[slot.slot].dvbt.configMode.value == "nothing":
							continue
						elif FeType in ("DVB-C", "DVB-C2") and config.Nims[slot.slot].dvbc.configMode.value == "nothing":
							continue
						elif FeType in ("ATSC") and config.Nims[slot.slot].atsc.configMode.value == "nothing":
							continue
						eDVBResourceManager.getInstance().setFrontendType(slot.frontend_id, FeType, True)
				else:
					eDVBResourceManager.getInstance().setFrontendType(slot.frontend_id, slot.getType())
		print "sec config completed"

	def updateAdvanced(self, sec, slotid):
		advanced = config.Nims[slotid].dvbs.advanced
		try:
			if advanced.unicableconnected is not None:
				if advanced.unicableconnected.value:
					advanced.unicableconnectedTo.save_forced = True
					self.linkNIMs(sec, slotid, int(advanced.unicableconnectedTo.value))
					connto = self.getRoot(slotid, int(advanced.unicableconnectedTo.value))
					if not self.linked.has_key(connto):
						self.linked[connto] = []
					self.linked[connto].append(slotid)
				else:
					advanced.unicableconnectedTo.save_forced = False
		except:
			pass

		lnbSat = {}
		for x in range(1, 71):
			lnbSat[x] = []

		#wildcard for all satellites ( for rotor )
		for x in range(3601, 3605):
			lnb = int(advanced.sat[x].lnb.value)
			if lnb != 0:
				for x in self.NimManager.satList:
					print "add", x[0], "to", lnb
					lnbSat[lnb].append(x[0])

		#wildcard for user satellites ( for rotor )
		for x in range(3605, 3607):
			lnb = int(advanced.sat[x].lnb.value)
			if lnb != 0:
				for user_sat in self.NimManager.satList:
					if str(user_sat[0]) in advanced.sat[x].userSatellitesList.value:
						print "add", user_sat[0], "to", lnb
						lnbSat[lnb].append(user_sat[0])

		for x in self.NimManager.satList:
			lnb = int(advanced.sat[x[0]].lnb.value)
			if lnb != 0:
				print "add", x[0], "to", lnb
				lnbSat[lnb].append(x[0])

		for x in range(1, 71):
			if len(lnbSat[x]) > 0:
				currLnb = advanced.lnb[x]
				if sec.addLNB():
					print "No space left on m_lnbs (max No. 144 LNBs exceeded)"
					return

				posnum = 1;	#default if LNB movable
				if x <= maxFixedLnbPositions:
					posnum = x;
					sec.setLNBSatCRpositionnumber(x)	# LNB has fixed Position
				else:
					sec.setLNBSatCRpositionnumber(0)	# or not (movable LNB)

				tunermask = 1 << slotid
				if self.equal.has_key(slotid):
					for slot in self.equal[slotid]:
						tunermask |= (1 << slot)
				if self.linked.has_key(slotid):
					for slot in self.linked[slotid]:
						tunermask |= (1 << slot)
				if currLnb.lof.value != "unicable":
					sec.setLNBSatCR(-1)
					sec.setLNBSatCRTuningAlgo(0)
					sec.setLNBBootupTime(0)
				if currLnb.lof.value == "universal_lnb":
					sec.setLNBLOFL(9750000)
					sec.setLNBLOFH(10600000)
					sec.setLNBThreshold(11700000)
				elif currLnb.lof.value == "unicable":
					def setupUnicable(configManufacturer, ProductDict):
						manufacturer_name = configManufacturer.value.decode('utf-8')
						manufacturer = ProductDict[manufacturer_name]
						product_name = manufacturer.product.value.decode('utf-8')
						if product_name == "None" and manufacturer.product.saved_value != "None":
							product_name = manufacturer.product.value = manufacturer.product.saved_value
						manufacturer_scr = manufacturer.scr
						manufacturer_positions_value = manufacturer.positions[product_name][0].value
						position_idx = (posnum - 1) % manufacturer_positions_value
						if product_name in manufacturer_scr:
							diction = manufacturer.diction[product_name].value
							positionsoffset = manufacturer.positionsoffset[product_name][0].value
							if diction !="EN50607" or ((posnum <= (positionsoffset + manufacturer_positions_value) and (posnum > positionsoffset) and x <= maxFixedLnbPositions)): #for every allowed position
								sec.setLNBSatCRformat(diction =="EN50607" and 1 or 0)
								sec.setLNBSatCR(manufacturer_scr[product_name].index)
								sec.setLNBSatCRvco(manufacturer.vco[product_name][manufacturer_scr[product_name].index].value*1000)
								sec.setLNBSatCRpositions(manufacturer_positions_value)
								sec.setLNBLOFL(manufacturer.lofl[product_name][position_idx].value * 1000)
								sec.setLNBLOFH(manufacturer.lofh[product_name][position_idx].value * 1000)
								sec.setLNBThreshold(manufacturer.loft[product_name][position_idx].value * 1000)
								sec.setLNBSatCRTuningAlgo(["traditional", "reliable", "traditional_retune", "reliable_retune"].index(currLnb.unicableTuningAlgo.value))
								sec.setLNBBootupTime(manufacturer.bootuptime[product_name][0].value)
								configManufacturer.save_forced = True
								manufacturer.product.save_forced = True
								manufacturer.vco[product_name][manufacturer_scr[product_name].index].save_forced = True
							else: #positionnumber out of range
								print "positionnumber out of range"
						else:
							print "no product in list"
							
					if currLnb.unicable.value == "unicable_user":
#TODO satpositions for satcruser
						if currLnb.dictionuser.value == "EN50607": 
							sec.setLNBSatCRformat(1)
							sec.setLNBSatCR(currLnb.satcruserEN50607.index)
							sec.setLNBSatCRvco(currLnb.satcrvcouserEN50607[currLnb.satcruserEN50607.index].value*1000)
						else:
							sec.setLNBSatCRformat(0)
							sec.setLNBSatCR(currLnb.satcruserEN50494.index)
							sec.setLNBSatCRvco(currLnb.satcrvcouserEN50494[currLnb.satcruserEN50494.index].value*1000)

						sec.setLNBLOFL(currLnb.lofl.value * 1000)
						sec.setLNBLOFH(currLnb.lofh.value * 1000)
						sec.setLNBThreshold(currLnb.threshold.value * 1000)
						sec.setLNBSatCRpositions(64)
						sec.setLNBBootupTime(currLnb.bootuptimeuser.value)
					elif currLnb.unicable.value == "unicable_matrix":
						self.reconstructUnicableDate(currLnb.unicableMatrixManufacturer, currLnb.unicableMatrix, currLnb)
						setupUnicable(currLnb.unicableMatrixManufacturer, currLnb.unicableMatrix)
					elif currLnb.unicable.value == "unicable_lnb":
						self.reconstructUnicableDate(currLnb.unicableLnbManufacturer, currLnb.unicableLnb, currLnb)
						setupUnicable(currLnb.unicableLnbManufacturer, currLnb.unicableLnb)
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
				elif currLnb.lof.value == "ka_sat":
					sec.setLNBLOFL(21200000)
					sec.setLNBLOFH(21200000)
					sec.setLNBThreshold(21200000)

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

					if self.satposdepends.has_key(slotid):
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

					if c.has_key(cdc):
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

				sec.setLNBPrio(int(currLnb.prio.value))

				# finally add the orbital positions
				for y in lnbSat[x]:
					self.addSatellite(sec, y)
					if x > maxFixedLnbPositions:
						satpos = x > maxFixedLnbPositions and (3606-(70 - x)) or y
					else:
						satpos = y
					currSat = advanced.sat[satpos]
					if currSat.voltage.value == "polarization":
						if config.Nims[slotid].dvbs.diseqc13V.value:
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
					if not currSat.usals.value and x <= maxFixedLnbPositions:
						sec.setRotorPosNum(currSat.rotorposition.value)
					else:
						sec.setRotorPosNum(0) #USALS

	def reconstructUnicableDate(self, configManufacturer, ProductDict, currLnb):
		val = currLnb.content.stored_values
		if currLnb.unicable.value == "unicable_lnb":
			ManufacturerName = val.get('unicableLnbManufacturer', 'none')
			SDict = val.get('unicableLnb', None)
		elif currLnb.unicable.value == "unicable_matrix":
			ManufacturerName = val.get('unicableMatrixManufacturer', 'none')
			SDict = val.get('unicableMatrix', None)
		else:
			return
		#print "[reconstructUnicableDate] SDict %s" % SDict
		if SDict is None:
			return

		if ManufacturerName is not None:
			ManufacturerName = ManufacturerName.decode("utf-8")
		print "ManufacturerName %s" % ManufacturerName

		PDict = SDict.get(ManufacturerName, None)			#dict contained last stored device data
		if PDict is None:
			return

		PN = PDict.get('product', None)				#product name
		if PN is None:
			return

		if ManufacturerName in ProductDict.keys():			# manufacture are listed, use its ConfigSubsection
			tmp = ProductDict[ManufacturerName]
			if PN in tmp.product.choices.choices:
				return
		else:								#if manufacture not in list, then generate new ConfigSubsection
			print "[reconstructUnicableDate] Manufacturer %s not in unicable.xml" % ManufacturerName
			tmp = ConfigSubsection()
			tmp.scr = ConfigSubDict()
			tmp.vco = ConfigSubDict()
			tmp.lofl = ConfigSubDict()
			tmp.lofh = ConfigSubDict()
			tmp.loft = ConfigSubDict()
			tmp.bootuptime = ConfigSubDict()
			tmp.diction = ConfigSubDict()
			tmp.product = ConfigSelection(choices = [], default = None)
			tmp.positions = ConfigSubDict()
			tmp.positionsoffset = ConfigSubDict()

		if PN not in tmp.product.choices.choices:
			print "[reconstructUnicableDate] Product %s not in unicable.xml" % PN
			scrlist = []
			SatCR = int(PDict.get('scr', {PN:1}).get(PN,1)) - 1
			vco = int(PDict.get('vco', {PN:0}).get(PN,0).get(str(SatCR),1))

			positionslist=[1,(9750, 10600, 11700)]	##adenin_todo
			positions = int(positionslist[0])
			tmp.positions[PN] = ConfigSubList()
			tmp.positions[PN].append(ConfigInteger(default=positions, limits = (positions, positions)))

			tmp.bootuptime[PN] = ConfigSubList()
			tmpbootuptime[PN].append(ConfigInteger(default=0, limits = (0, 0)))

			positionsoffsetlist=[0,]	##adenin_todo
			positionsoffset = int(positionsoffsetlist[0])
			tmp.positionsoffset[PN] = ConfigSubList()
			tmp.positionsoffset[PN].append(ConfigInteger(default=positionsoffset, limits = (positionsoffset, positionsoffset)))

			tmp.vco[PN] = ConfigSubList()

			for cnt in range(0,SatCR + 1):
				vcofreq = (cnt == SatCR) and vco or 0		# equivalent to vcofreq = (cnt == SatCR) ? vco : 0
				if vcofreq == 0 :
					scrlist.append(("%d" %(cnt+1),"SCR %d " %(cnt+1) +_("not used")))
				else:
					scrlist.append(("%d" %(cnt+1),"SCR %d" %(cnt+1)))
				print "vcofreq %d" % vcofreq
				tmp.vco[PN].append(ConfigInteger(default=vcofreq, limits = (vcofreq, vcofreq)))

			tmp.scr[PN] = ConfigSelection(choices = scrlist, default = scrlist[SatCR][0])

			tmp.lofl[PN] = ConfigSubList()
			tmp.lofh[PN] = ConfigSubList()
			tmp.loft[PN] = ConfigSubList()
			for cnt in range(1,positions+1):
				lofl = int(positionslist[cnt][0])
				lofh = int(positionslist[cnt][1])
				loft = int(positionslist[cnt][2])
				tmp.lofl[PN].append(ConfigInteger(default=lofl, limits = (lofl, lofl)))
				tmp.lofh[PN].append(ConfigInteger(default=lofh, limits = (lofh, lofh)))
				tmp.loft[PN].append(ConfigInteger(default=loft, limits = (loft, loft)))

			dictionlist = [("EN50494", "Unicable(EN50494)")]	##adenin_todo
			tmp.diction[PN] = ConfigSelection(choices = dictionlist, default = dictionlist[0][0])

			tmp.product.choices.choices.append(PN)
			tmp.product.choices.default = PN

			tmp.scr[PN].save_forced = True
			tmp.scr.save_forced = True
			tmp.vco.save_forced = True
			tmp.product.save_forced = True

			ProductDict[ManufacturerName] = tmp

		if ManufacturerName not in configManufacturer.choices.choices:		#check if name in choices list
			configManufacturer.choices.choices.append(ManufacturerName)	#add name to choises list

	def __init__(self, nimmgr):
		self.NimManager = nimmgr
		self.configuredSatellites = set()
		self.update()

class NIM(object):
	def __init__(self, slot, type, description, has_outputs=True, internally_connectable=None, multi_type=None, frontend_id=None, i2c=None, is_empty=False, input_name = None, supports_blind_scan = False):
		if not multi_type: multi_type = {}
		self.slot = slot

		if type not in ("DVB-S", "DVB-C", "DVB-T", "DVB-S2", "DVB-S2X", "DVB-T2", "DVB-C2", "ATSC", None):
			print "warning: unknown NIM type %s, not using." % type
			type = None

		self.type = type
		self.description = description
		self.has_outputs = has_outputs
		self.internally_connectable = internally_connectable
		self.multi_type = multi_type
		self.supports_blind_scan = supports_blind_scan
		self.i2c = i2c
		self.frontend_id = frontend_id
		self.__is_empty = is_empty
		self.input_name = input_name

		self.compatible = {
				None: (None,),
				"DVB-S": ("DVB-S", None),
				"DVB-C": ("DVB-C", None),
				"DVB-T": ("DVB-T", None),
				"DVB-S2": ("DVB-S", "DVB-S2", None),
				"DVB-S2X": ("DVB-S", "DVB-S2", "DVB-S2X", None),
				"DVB-C2": ("DVB-C", "DVB-C2", None),
				"DVB-T2": ("DVB-T", "DVB-T2", None),
				"ATSC": ("ATSC", None),
			}

	def isCompatible(self, what):
		if not self.isSupported():
			return False
		return what in self.compatible[self.getType()]

	def canBeCompatible(self, what):
		if not self.isSupported():
			print "%s is not suportetd "%(what)
			return False
		if self.isMultiType():
			#print"[adenin] %s is multitype"%(self.slot)
			for type in self.multi_type.values():
				if what in self.compatible[type]:
					return True
		elif  what in self.compatible[self.getType()]:
			#print"[adenin] %s is NOT multitype"%(self.slot)
			return True
		return False

	def getType(self):
		try:
			if self.isMultiType():
				type = self.multi_type[self.config.multiType.value]
				return type
		except:
			pass
		return self.type

	def connectableTo(self):
		connectable = {
				"DVB-S": ("DVB-S", "DVB-S2"),
				"DVB-C": ("DVB-C", "DVB-C2"),
				"DVB-T": ("DVB-T","DVB-T2"),
				"DVB-S2": ("DVB-S", "DVB-S2"),
				"DVB-S2X": ("DVB-S", "DVB-S2", "DVB-S2X"),
				"DVB-C2": ("DVB-C", "DVB-C2"),
				"DVB-T2": ("DVB-T", "DVB-T2"),
				"ATSC": "ATSC",
			}
		return connectable[self.getType()]

	def getSlotInputName(self):
		name = self.input_name
		if name is None:
			name = chr(ord('A') + self.slot)
		return name
	
	slot_input_name = property(getSlotInputName)

	def getSlotName(self):
		# get a friendly description for a slot name.
		# we name them "Tuner A/B/C/...", because that's what's usually written on the back
		# of the device.
		# for DM7080HD "Tuner A1/A2/B/C/..."
		descr = _("Tuner ")
		return descr + self.getSlotInputName()

	slot_name = property(getSlotName)

	def getSlotID(self):
		return chr(ord('A') + self.slot)

	def getI2C(self):
		return self.i2c

	def hasOutputs(self):
		return self.has_outputs

	def internallyConnectableTo(self):
		return self.internally_connectable

	def setInternalLink(self):
		if self.internally_connectable is not None:
			print "setting internal link on frontend id", self.frontend_id
			f = open("/proc/stb/frontend/%d/rf_switch" % self.frontend_id, "w")
			f.write("internal")
			f.close()

	def removeInternalLink(self):
		if self.internally_connectable is not None:
			print "removing internal link on frontend id", self.frontend_id
			f = open("/proc/stb/frontend/%d/rf_switch" % self.frontend_id, "w")
			f.write("external")
			f.close()

	def isMultiType(self):
		return len(self.multi_type) > 0

	def isEmpty(self):
		return self.__is_empty

	# empty tuners are supported!
	def isSupported(self):
		return (self.frontend_id is not None) or self.__is_empty

	def isMultistream(self):
		multistream = (self.frontend_id is not None) and eDVBResourceManager.getInstance().frontendIsMultistream(self.frontend_id) or False
		# HACK due to poor support for VTUNER_SET_FE_INFO
		# When vtuner does not accept fe_info we have to fallback to detection using tuner name
		# More tuner names will be added when confirmed as multistream (FE_CAN_MULTISTREAM)
		if not multistream and "TBS" in self.description:
			multistream = True
		return multistream

	def supportsBlindScan(self):
		return self.supports_blind_scan

	# returns dict {<slotid>: <type>}
	def getMultiTypeList(self):
		return self.multi_type

	slot_id = property(getSlotID)

	def getFriendlyType(self):
		return {
			"DVB-S": "DVB-S",
			"DVB-T": "DVB-T",
			"DVB-C": "DVB-C",
			"DVB-S2": "DVB-S2",
			"DVB-S2X": "DVB-S2X",
			"DVB-T2": "DVB-T2",
			"DVB-C2": "DVB-C2",
			"ATSC": "ATSC",
			None: _("empty")
			}[self.getType()]

	friendly_type = property(getFriendlyType)

	def getFriendlyFullDescription(self):
		nim_text = self.slot_name + ": "

		if self.empty:
			nim_text += _("(empty)")
		elif not self.isSupported():
			nim_text += self.description + " (" + _("not supported") + ")"
		else:
			if self.isMultiType():
				nim_text += self.description
			else:
				nim_text += self.description + " (" + self.friendly_type + ")"
		return nim_text

	friendly_full_description = property(getFriendlyFullDescription)
	config_mode_dvbs = property(lambda self: config.Nims[self.slot].dvbs.configMode.value)
	config_mode_dvbt = property(lambda self: config.Nims[self.slot].dvbt.configMode.value)
	config_mode_dvbc = property(lambda self: config.Nims[self.slot].dvbc.configMode.value)
	config_mode_atsc = property(lambda self: config.Nims[self.slot].atsc.configMode.value)

	config = property(lambda self: config.Nims[self.slot])
	empty = property(lambda self: self.getType() is None)

class NimManager:
	def getConfiguredSats(self):
		return self.sec.getConfiguredSats()

	def getTransponders(self, pos):
		if self.transponders.has_key(pos):
			return self.transponders[pos]
		else:
			return []

	def getTranspondersCable(self, nim):
		nimConfig = config.Nims[nim].dvbc
		if nimConfig.configMode.value != "nothing" and nimConfig.scan_type.value == "provider":
			return self.transponderscable[self.cablesList[nimConfig.scan_provider.index][0]]
		return [ ]

	def getTranspondersTerrestrial(self, region):
		return self.transpondersterrestrial[region]

	def getTranspondersATSC(self, nim):
		nimConfig = config.Nims[nim].atsc
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
		return self.cablesList[config.Nims[nim].dvbc.scan_provider.index][0]

	def getCableFlags(self, nim):
		return self.cablesList[config.Nims[nim].dvbc.scan_provider.index][1]

	def getCableCountrycode(self, nim):
		return self.cablesList and self.cablesList[config.Nims[nim].dvbc.scan_provider.index][2] or None

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
		return self.terrestrialsList[config.Nims[nim].dvbt.terrestrial.index][0]

	def getATSCDescription(self, nim):
		return self.atscList[config.Nims[nim].atsc.atsc.index][0]

	def getTerrestrialFlags(self, nim):
		return self.terrestrialsList[config.Nims[nim].dvbt.terrestrial.index][1]

	def getTerrestrialCountrycode(self, nim):
		return self.terrestrialsList and self.terrestrialsList[config.Nims[nim].dvbt.terrestrial.index][2] or None

	def getATSCFlags(self, nim):
		return self.atscList[config.Nims[nim].atsc.atsc.index][1]

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

		try:
			for slot in self.nim_slots:
				if slot.frontend_id is not None:
					types = [type for type in ["DVB-C", "DVB-T", "DVB-T2", "DVB-S", "DVB-S2", "DVB-S2X", "ATSC"] if eDVBResourceManager.getInstance().frontendIsCompatible(slot.frontend_id, type)]
					if "DVB-T2" in types:
						# DVB-T2 implies DVB-T support
						types.remove("DVB-T")
					if "DVB-S2" in types:
						# DVB-S2 implies DVB-S support
						types.remove("DVB-S")
					if len(types) > 1:
						slot.multi_type = {}
						for type in types:
							slot.multi_type[str(types.index(type))] = type
		except:
			pass

		if self.hasNimType("DVB-S"):
			print "Reading satellites.xml"
			if db.readSatellites(self.satList, self.satellites, self.transponders):
				self.satList.sort() # sort by orbpos
			else: #satellites.xml not found or corrupted
				from Tools.Notifications import AddPopup
				from Screens.MessageBox import MessageBox
				def emergencyAid():
					if not path.exists("/etc/enigma2/lamedb"):
						print "/etc/enigma2/lamedb not found"
						return None
					f = file("/etc/enigma2/lamedb","r")
					lamedb = f.readlines()
					f.close()

					if lamedb[0].find("/3/") != -1:
						version = 3
					elif lamedb[0].find("/4/") != -1:
						version = 4
					else:
						print "unknown lamedb version: ",lamedb[0]
						return False
					print "import version %d" % version

					collect = False
					transponders = []
					tp = []
					for line in lamedb:
						if line == "transponders\n":
							collect = True
							continue
						if line == "end\n":
							break
						if collect:
							data = line.strip().split(":")
							if data[0] == "/":
								transponders.append(tp)
								tp = []
							else:
								tp.append(data)

					t1 = ("namespace","tsid","onid")
					t2_sv3 = ("frequency",
						"symbol_rate",
						"polarization",
						"fec_inner",
						"position",
						"inversion",
						"system",
						"modulation",
						"rolloff",
						"pilot",
						)
					t2_sv4 = ("frequency",
						"symbol_rate",
						"polarization",
						"fec_inner",
						"position",
						"inversion",
						"flags",
						"system",
						"modulation",
						"rolloff",
						"pilot"
						)

					tplist = []
					for x in transponders:
						tp = {}
						if len(x[0]) > len(t1):
							continue
						freq = x[1][0].split()
						if len(freq) != 2:
							continue
						x[1][0] = freq[1]
						if freq[0] == "s" or freq[0] == "S":
							if ((version == 3) and len(x[1]) > len(t2_sv3)) or ((version == 4) and len(x[1]) > len(t2_sv4)):
								continue
							for y in range(0, len(x[0])):
								tp.update({t1[y]:x[0][y]})
							for y in range(0, len(x[1])):
								if version == 3:
									tp.update({t2_sv3[y]:x[1][y]})
								elif version == 4:
									tp.update({t2_sv4[y]:x[1][y]})
							if ((int(tp.get("namespace"),16) >> 16) & 0xFFF) != int(tp.get("position")):
								print "Namespace %s and Position %s are not identical"% (tp.get("namespace"), tp.get("position"))
								continue
							if version >= 4:
								tp.update({"supposition":((int(tp.get("namespace","0"),16) >> 24) & 0x0F)})
						elif freq[0] == "c" or freq[0] == "C":
							print "DVB-C"
							continue
						elif freq[0] == "t" or freq[0] == "T":
							print "DVB-T"
							continue
						tplist.append(tp)

					satDict = {}
					for tp in tplist:
						freq = int(tp.get("frequency",0))
						if freq:
							tmp_sat = satDict.get(int(tp.get("position")),{})
							tmp_tp = self.transponders.get(int(tp.get("position")),[])
							sat_pos = int(tp.get("position"))
							fake_sat_pos = int(tp.get("position"))
							if sat_pos > 1800:
								sat_pos -= 1800
								dir = 'W'
							else:
								dir = 'E'
							if freq >= 10000000 and freq <= 13000000:
								fake_sat_pos = sat_pos
								tmp_sat.update({'name':'%3.1f%c Ku-band satellite' %(sat_pos/10.0, dir)})
								#tmp_sat.update({"band":"Ku"})
							if freq >= 3000000 and freq <= 4000000:
								fake_sat_pos = sat_pos + 1
								tmp_sat.update({'name':'%3.1f%c C-band satellite' %(sat_pos/10.0, dir)})
								#tmp_sat.update({"band":"C"})
							if freq >= 17000000 and freq <= 23000000:
								fake_sat_pos = sat_pos + 2
								tmp_sat.update({'name':'%3.1f%c Ka-band satellite' %(sat_pos/10.0, dir)})
								#tmp_sat.update({"band":"Ka"})
							tmp_tp.append((
									0,			#???
									int(tp.get("frequency",0)),
									int(tp.get("symbol_rate",0)),
									int(tp.get("polarization",0)),
									int(tp.get("fec_inner",0)),
									int(tp.get("system",0)),
									int(tp.get("modulation",0)),
									int(tp.get("inversion",0)),
									int(tp.get("rolloff",0)),
									int(tp.get("pilot",0)),
									-1,			#tsid  -1 -> any tsid are valid
									-1			#onid  -1 -> any tsid are valid
								))
							tmp_sat.update({'flags':int(tp.get("flags"))})
							satDict.update({fake_sat_pos:tmp_sat})
							self.transponders.update({fake_sat_pos:tmp_tp})

					for sat_pos in satDict:
						self.satellites.update({sat_pos: satDict.get(sat_pos).get('name')})
						self.satList.append((sat_pos, satDict.get(sat_pos).get('name'), satDict.get(sat_pos).get('flags')))

					return True

				AddPopup(_("satellites.xml not found or corrupted!\nIt is possible to watch TV,\nbut it's not possible to search for new TV channels\nor to configure tuner settings"), type = MessageBox.TYPE_ERROR, timeout = 0, id = "SatellitesLoadFailed")
				if not emergencyAid():
					AddPopup(_("resoring satellites.xml not posibel!"), type = MessageBox.TYPE_ERROR, timeout = 0, id = "SatellitesLoadFailed")
					return

		if self.hasNimType("DVB-C") or self.hasNimType("DVB-T") or self.hasNimType("DVB-T2"):
			print "Reading cables.xml"
			db.readCables(self.cablesList, self.transponderscable)
			print "Reading terrestrial.xml"
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
		# Type will be either "DVB-S", "DVB-S2", "DVB-S2X", "DVB-T", "DVB-C" or None.

		# nim_slots is an array which has exactly one entry for each slot, even for empty ones.
		self.nim_slots = [ ]

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
			elif line.strip().startswith("Input_Name:"):
				entries[current_slot]["input_name"] = str(line.strip()[12:])
			elif line.startswith("Name:"):
				entries[current_slot]["name"] = str(line[6:])
				entries[current_slot]["isempty"] = False
			elif line.startswith("Has_Outputs:"):
				input = str(line[len("Has_Outputs:") + 1:])
				entries[current_slot]["has_outputs"] = (input == "yes")
			elif line.startswith("Internally_Connectable:"):
				input = int(line[len("Internally_Connectable:") + 1:])
				entries[current_slot]["internally_connectable"] = input
			elif line.startswith("Supports_Blind_Scan:"):
				input = str(line[len("Supports_Blind_Scan:") + 1:])
				entries[current_slot]["supports_blind_scan"] = (input == "yes")
			elif line.startswith("Frontend_Device:"):
				input = int(line[len("Frontend_Device:") + 1:])
				entries[current_slot]["frontend_device"] = input
			elif line.startswith("Mode"):
				# Mode 0: DVB-C
				# Mode 1: DVB-T
				# "Mode 1: DVB-T" -> ["Mode 1", "DVB-T"]
				split = line.split(":")
				split[1] = split[1].replace(' ','')
				split2 = split[0].split(" ")
				modes = entries[current_slot].get("multi_type", {})
				modes[split2[1]] = split[1]
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
			if not (entry.has_key("name") and entry.has_key("type")):
				entry["name"] =  _("N/A")
				entry["type"] = None
			if not (entry.has_key("i2c")):
				entry["i2c"] = None
			if not (entry.has_key("has_outputs")):
				entry["has_outputs"] = True
			if entry.has_key("frontend_device"): # check if internally connectable
				if path.exists("/proc/stb/frontend/%d/rf_switch" % entry["frontend_device"]) and ((id > 0) or (getBoxType() == 'vusolo2')):
					entry["internally_connectable"] = entry["frontend_device"] - 1
				else:
					entry["internally_connectable"] = None
			else:
				entry["frontend_device"] = entry["internally_connectable"] = None
			if not (entry.has_key("multi_type")):
				if entry["name"] == "DVB-T2/C USB-Stick": # workaround dvbsky hybrid usb stick
					entry["multi_type"] = {'0': 'DVB-T'}
					entry["multi_type"] = {'1': 'DVB-C'}
				else:
					entry["multi_type"] = {}
			if not (entry.has_key("input_name")):
				entry["input_name"] = chr(ord('A') + id)
			if "supports_blind_scan" not in entry:
				entry["supports_blind_scan"] = False
			self.nim_slots.append(NIM(slot = id, description = entry["name"], type = entry["type"], has_outputs = entry["has_outputs"], internally_connectable = entry["internally_connectable"], multi_type = entry["multi_type"], frontend_id = entry["frontend_device"], i2c = entry["i2c"], is_empty = entry["isempty"], input_name = entry.get("input_name", None), supports_blind_scan = entry["supports_blind_scan"]))

	def hasNimType(self, chktype):
		for slot in self.nim_slots:
			if slot.canBeCompatible(chktype):
				return True
		return False

	def getNimType(self, slotid):
		return self.nim_slots[slotid].type

	def getNimDescription(self, slotid):
		return self.nim_slots[slotid].friendly_full_description

	def getNimName(self, slotid):
		return self.nim_slots[slotid].description

	def getNimSlotInputName(self, slotid):
		# returns just "A", "B", ...
		return self.nim_slots[slotid].slot_input_name

	def getNim(self, slotid):
		return self.nim_slots[slotid]

	def getI2CDevice(self, slotid):
		return self.nim_slots[slotid].getI2C()

	def getNimListOfType(self, type, exception = -1):
		# returns a list of indexes for NIMs compatible to the given type, except for 'exception'
		list = []
		for x in self.nim_slots:
			if x.isMultiType() and x.canBeCompatible(type) and x.slot != exception:
				list.append(x.slot)
			elif x.isCompatible(type) and x.slot != exception:
				list.append(x.slot)
		return list

	def __init__(self):
		sec = secClass.getInstance()
		global maxFixedLnbPositions
		maxFixedLnbPositions = sec.getMaxFixedLnbPositions()
		self.satList = [ ]
		self.cablesList = []
		self.terrestrialsList = []
		self.atscList = []
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
				if self.hasOutputs(slot) and slot not in slots:
					slots.append(slot)
		# remove nims, that have a conntectedTo reference on
		for testnim in slots[:]:
			for nim in self.getNimListOfType("DVB-S", slotid):
				try:
					nimConfig = self.getNimConfig(nim)
					if nimConfig.content.items.has_key("configMode") and nimConfig.configMode.value == "loopthrough" and int(nimConfig.connectedTo.value) == testnim:
						slots.remove(testnim)
						break
				except:
					pass

		slots.sort()
		return slots

	def canEqualTo(self, slotid):
		type = self.getNimType(slotid)
		type = type[:5] # DVB-S2X --> DVB-S2 --> DVB-S, DVB-T2 --> DVB-T, DVB-C2 --> DVB-C
		nimList = self.getNimListOfType(type, slotid)
		for nim in nimList[:]:
			if self.nim_slots[nim].canBeCompatible('DVB-S'):
				mode = self.getNimConfig(nim).dvbs
				if mode.configMode.value == "loopthrough" or mode.configMode.value == "satposdepends":
					nimList.remove(nim)
		return nimList

	def canDependOn(self, slotid):
		type = self.getNimType(slotid)
		type = type[:5] # DVB-S2X --> DVB-S2 --> DVB-S, DVB-T2 --> DVB-T, DVB-C2 --> DVB-C
		nimList = self.getNimListOfType(type, slotid)
		positionerList = []
		for nim in nimList[:]:
			if self.nim_slots[nim].canBeCompatible('DVB-S'):
				mode = self.getNimConfig(nim).dvbs
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
						testmode = self.getNimConfig(testnim).dvbs
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
			res = False
			if self.nim_slots[slotid].canBeCompatible("DVB-S"):
				nim = config.Nims[slotid].dvbs
				configMode = nim.configMode.value
				res = res or not (configMode == "nothing")
			if self.nim_slots[slotid].canBeCompatible("DVB-T"):
				nim = config.Nims[slotid].dvbt
				configMode = nim.configMode.value
				res = res or not (configMode == "nothing")
			if self.nim_slots[slotid].canBeCompatible("DVB-C"):
				nim = config.Nims[slotid].dvbc
				configMode = nim.configMode.value
				res = res or not (configMode == "nothing")
			if self.nim_slots[slotid].canBeCompatible("ATSC"):
				nim = config.Nims[slotid].atsc
				configMode = nim.configMode.value
				res = res or not (configMode == "nothing")
			return res

	def getSatListForNim(self, slotid):
		list = []
		if self.nim_slots[slotid].canBeCompatible("DVB-S"):
			nim = config.Nims[slotid].dvbs
			configMode = nim.configMode.value

			if configMode == "nothing":
				return list

			elif configMode == "equal":
				slotid = int(nim.connectedTo.value)
				nim = config.Nims[slotid].dvbs
				configMode = nim.configMode.value
			elif configMode == "loopthrough":
				slotid = self.sec.getRoot(slotid, int(nim.connectedTo.value))
				nim = config.Nims[slotid].dvbs
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
					for x in self.satList:
						if str(x[0]) in nim.userSatellitesList.value:
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
						for user_sat in self.satList:
							if str(user_sat[0]) in nim.advanced.sat[x].userSatellitesList.value and user_sat not in list:
								list.append(user_sat)
		return list

	def getRotorSatListForNim(self, slotid):
		list = []
		if self.nim_slots[slotid].isCompatible("DVB-S"):
			nim = config.Nims[slotid].dvbs
			configMode = nim.configMode.value
			if configMode == "simple":
				if nim.diseqcMode.value == "positioner":
					for x in self.satList:
						list.append(x)
				elif nim.diseqcMode.value == "positioner_select":
					for x in self.satList:
						if str(x[0]) in nim.userSatellitesList.value:
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
						for user_sat in self.satList:
							if str(user_sat[0]) in nim.advanced.sat[x].userSatellitesList.value and user_sat not in list:
								list.append(user_sat)
		return list

def InitSecParams():
	config.sec = ConfigSubsection()

	x = ConfigInteger(default=25, limits = (0, 9999))
	x.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_AFTER_CONT_TONE_DISABLE_BEFORE_DISEQC, configElement.value))
	config.sec.delay_after_continuous_tone_disable_before_diseqc = x

	x = ConfigInteger(default=10, limits = (0, 9999))
	x.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_AFTER_FINAL_CONT_TONE_CHANGE, configElement.value))
	config.sec.delay_after_final_continuous_tone_change = x

	x = ConfigInteger(default=10, limits = (0, 9999))
	x.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_AFTER_FINAL_VOLTAGE_CHANGE, configElement.value))
	config.sec.delay_after_final_voltage_change = x

	x = ConfigInteger(default=120, limits = (0, 9999))
	x.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_BETWEEN_DISEQC_REPEATS, configElement.value))
	config.sec.delay_between_diseqc_repeats = x

	x = ConfigInteger(default=100, limits = (0, 9999))
	x.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_AFTER_LAST_DISEQC_CMD, configElement.value))
	config.sec.delay_after_last_diseqc_command = x

	x = ConfigInteger(default=50, limits = (0, 9999))
	x.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_AFTER_TONEBURST, configElement.value))
	config.sec.delay_after_toneburst = x

	x = ConfigInteger(default=75, limits = (0, 9999))
	x.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_AFTER_VOLTAGE_CHANGE_BEFORE_SWITCH_CMDS, configElement.value))
	config.sec.delay_after_change_voltage_before_switch_command = x

	x = ConfigInteger(default=200, limits = (0, 9999))
	x.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_AFTER_ENABLE_VOLTAGE_BEFORE_SWITCH_CMDS, configElement.value))
	config.sec.delay_after_enable_voltage_before_switch_command = x

	x = ConfigInteger(default=700, limits = (0, 9999))
	x.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_BETWEEN_SWITCH_AND_MOTOR_CMD, configElement.value))
	config.sec.delay_between_switch_and_motor_command = x

	x = ConfigInteger(default=500, limits = (0, 9999))
	x.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_AFTER_VOLTAGE_CHANGE_BEFORE_MEASURE_IDLE_INPUTPOWER, configElement.value))
	config.sec.delay_after_voltage_change_before_measure_idle_inputpower = x

	x = ConfigInteger(default=900, limits = (0, 9999))
	x.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_AFTER_ENABLE_VOLTAGE_BEFORE_MOTOR_CMD, configElement.value))
	config.sec.delay_after_enable_voltage_before_motor_command = x

	x = ConfigInteger(default=500, limits = (0, 9999))
	x.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_AFTER_MOTOR_STOP_CMD, configElement.value))
	config.sec.delay_after_motor_stop_command = x

	x = ConfigInteger(default=500, limits = (0, 9999))
	x.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_AFTER_VOLTAGE_CHANGE_BEFORE_MOTOR_CMD, configElement.value))
	config.sec.delay_after_voltage_change_before_motor_command = x

	x = ConfigInteger(default=70, limits = (0, 9999))
	x.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_BEFORE_SEQUENCE_REPEAT, configElement.value))
	config.sec.delay_before_sequence_repeat = x

	x = ConfigInteger(default=360, limits = (0, 9999))
	x.addNotifier(lambda configElement: secClass.setParam(secClass.MOTOR_RUNNING_TIMEOUT, configElement.value))
	config.sec.motor_running_timeout = x

	x = ConfigInteger(default=1, limits = (0, 5))
	x.addNotifier(lambda configElement: secClass.setParam(secClass.MOTOR_COMMAND_RETRIES, configElement.value))
	config.sec.motor_command_retries = x

	x = ConfigInteger(default=50, limits = (0, 9999))
	x.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_AFTER_DISEQC_RESET_CMD, configElement.value))
	config.sec.delay_after_diseqc_reset_cmd = x

	x = ConfigInteger(default=150, limits = (0, 9999))
	x.addNotifier(lambda configElement: secClass.setParam(secClass.DELAY_AFTER_DISEQC_PERIPHERIAL_POWERON_CMD, configElement.value))
	config.sec.delay_after_diseqc_peripherial_poweron_cmd = x

# TODO add support for satpos depending nims to advanced nim configuration
# so a second/third/fourth cable from a motorized lnb can used behind a
# diseqc 1.0 / diseqc 1.1 / toneburst switch
# the C(++) part should can handle this
# the configElement should be only visible when diseqc 1.2 is disabled

jess_alias = ("JESS","UNICABLE2","SCD2","EN50607","EN 50607")

lscr = [("scr%d" % i) for i in range(1,33)]

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
			tmp = ConfigSubsection()
			tmp.dvbs = ConfigSubsection()
			tmp.dvbc = ConfigSubsection()
			tmp.dvbt = ConfigSubsection()
			tmp.atsc = ConfigSubsection()
			config.Nims.append(tmp)

	lnb_choices = {
		"universal_lnb": _("Universal LNB"),
		"unicable": _("Unicable / JESS"),
		"c_band": _("C-Band"),
		"circular_lnb": _("Circular LNB"),
		"ka_sat": _("KA-SAT"),
		"user_defined": _("User defined")}

	lnb_choices_default = "universal_lnb"

	unicablelnbproducts = {}
	unicablematrixproducts = {}
	file = open(eEnv.resolve("${datadir}/enigma2/unicable.xml"), 'r')
	doc = xml.etree.cElementTree.parse(file)
	file.close()
	root = doc.getroot()

	entry = root.find("lnb")
	for manufacturer in entry.getchildren():
		m={}
		m_update = m.update
		for product in manufacturer.getchildren():
			p={}												#new dict empty for new product
			p_update = p.update
			scr=[]
			scr_append = scr.append
			scr_pop = scr.pop
			for i in range(len(lscr)):
				scr_append(product.get(lscr[i],"0"))
			for i in range(len(lscr)):
				if scr[len(lscr)-i-1] == "0":
					scr_pop()
				else:
					break;

			p_update({"frequencies":tuple(scr)})								#add scr frequencies to dict product

			diction = product.get("format","EN50494").upper()
			if diction in jess_alias:
				diction = "EN50607"
			else:
				diction = "EN50494"
			p_update({"diction":tuple([diction])})								#add diction to dict product

			positionsoffset = product.get("positionsoffset",0)
			p_update({"positionsoffset":tuple([positionsoffset])})						#add positionsoffset to dict product

			positions=[]
			positions_append = positions.append
			positions_append(int(product.get("positions",1)))
			for cnt in range(positions[0]):
				lof=[]
				lof.append(int(product.get("lofl",9750)))
				lof.append(int(product.get("lofh",10600)))
				lof.append(int(product.get("threshold",11700)))
				positions_append(tuple(lof))

			p_update({"positions":tuple(positions)})							#add positons to dict product

			bootuptime = product.get("bootuptime",2700)
			p_update({"bootuptime":tuple([bootuptime])})							#add add boot up time

			m_update({product.get("name"):p})								#add dict product to dict manufacturer
		unicablelnbproducts.update({manufacturer.get("name"):m})

	entry = root.find("matrix")
	for manufacturer in entry.getchildren():
		m={}
		m_update = m.update
		for product in manufacturer.getchildren():
			p={}												#new dict empty for new product
			p_update = p.update
			scr=[]
			scr_append = scr.append
			scr_pop = scr.pop
			for i in range(len(lscr)):
				scr_append(product.get(lscr[i],"0"))
			for i in range(len(lscr)):
				if scr[len(lscr)-i-1] == "0":
					scr_pop()
				else:
					break;

			p_update({"frequencies":tuple(scr)})								#add scr frequencies to dict product

			diction = product.get("format","EN50494").upper()
			if diction in jess_alias:
				diction = "EN50607"
			else:
				diction = "EN50494"
			p_update({"diction":tuple([diction])})								#add diction to dict product

			positionsoffset = product.get("positionsoffset",0)
			p_update({"positionsoffset":tuple([positionsoffset])})						#add positionsoffset to dict product

			positions=[]
			positions_append = positions.append
			positions_append(int(product.get("positions",1)))
			for cnt in range(positions[0]):
				lof=[]
				lof.append(int(product.get("lofl",9750)))
				lof.append(int(product.get("lofh",10600)))
				lof.append(int(product.get("threshold",11700)))
				positions_append(tuple(lof))

			p_update({"positions":tuple(positions)})							#add positons to dict product

			bootuptime = product.get("bootuptime",2700)
			p_update({"bootuptime":tuple([bootuptime])})							#add boot up time

			m_update({product.get("name"):p})								#add dict product to dict manufacturer
		unicablematrixproducts.update({manufacturer.get("name"):m})						#add dict manufacturer to dict unicablematrixproducts

	UnicableLnbManufacturers = unicablelnbproducts.keys()
	UnicableLnbManufacturers.sort()
	UnicableMatrixManufacturers = unicablematrixproducts.keys()
	UnicableMatrixManufacturers.sort()

	unicable_choices = {
		"unicable_lnb": _("Unicable LNB"),
		"unicable_matrix": _("Unicable Matrix"),
		"unicable_user": "Unicable "+_("User defined")}
	unicable_choices_default = "unicable_lnb"

	advanced_lnb_satcr_user_choicesEN50494 = [("%d" % i, "SatCR %d" % i) for i in range(1,9)]

	advanced_lnb_satcr_user_choicesEN50607 = [("%d" % i, "SatCR %d" % i) for i in range(1,33)]

	advanced_lnb_diction_user_choices = [("EN50494", "Unicable(EN50494)"), ("EN50607", "JESS(EN50607)")]

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

	advanced_lnb_ucsw_choices = [("0", _("None"))] + [(str(y), "Input " + str(y)) for y in range(1, 17)]

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
	advanced_lnb_choices = [("0", _("not configured"))] + [(str(y), "LNB " + str(y)) for y in range(1, (maxFixedLnbPositions+1))]
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
			nim = config.Nims[x].dvbs
			lnbs = nim.advanced.lnb
			section = lnbs[lnb]
			if isinstance(section.unicable, ConfigNothing):
				if lnb == 1 or lnb > maxFixedLnbPositions:
					section.unicable = ConfigSelection(unicable_choices, unicable_choices_default)
				else:
					section.unicable = ConfigSelection(choices = {"unicable_matrix": _("Unicable Matrix"),"unicable_user": "Unicable "+_("User defined")}, default = "unicable_matrix")

			def fillUnicableConf(sectionDict, unicableproducts, vco_null_check):
				for manufacturer in unicableproducts:
					products = unicableproducts[manufacturer].keys()
					products.sort()
					products_valide = []
					products_valide_append = products_valide.append
					tmp = ConfigSubsection()
					tmp.scr = ConfigSubDict()
					tmp.vco = ConfigSubDict()
					tmp.lofl = ConfigSubDict()
					tmp.lofh = ConfigSubDict()
					tmp.loft = ConfigSubDict()
					tmp.bootuptime = ConfigSubDict()
					tmp.positionsoffset = ConfigSubDict()
					tmp.positions = ConfigSubDict()
					tmp.diction = ConfigSubDict()
					for article in products:
						positionsoffsetlist = unicableproducts[manufacturer][article].get("positionsoffset")
						positionsoffset = int(positionsoffsetlist[0])

						positionslist = unicableproducts[manufacturer][article].get("positions")
						positions = int(positionslist[0])

						bootuptimelist = unicableproducts[manufacturer][article].get("bootuptime")
						bootuptime = int(bootuptimelist[0])
						tmp.bootuptime[article] = ConfigSubList()
						tmp.bootuptime[article].append(ConfigInteger(default=bootuptime, limits = (bootuptime, bootuptime)))

						dictionlist = [unicableproducts[manufacturer][article].get("diction")]
						if dictionlist[0][0] !="EN50607" or ((lnb > positionsoffset) and (lnb <= (positions + positionsoffset))):
							tmp.positionsoffset[article] = ConfigSubList()
							tmp.positionsoffset[article].append(ConfigInteger(default=positionsoffset, limits = (positionsoffset, positionsoffset)))
							tmp.positions[article] = ConfigSubList()
							tmp.positions[article].append(ConfigInteger(default=positions, limits = (positions, positions)))
							tmp.diction[article] = ConfigSelection(choices = dictionlist, default = dictionlist[0][0])
							
							scrlist = []
							scrlist_append = scrlist.append
							vcolist=unicableproducts[manufacturer][article].get("frequencies")
							tmp.vco[article] = ConfigSubList()
							for cnt in range(1,len(vcolist)+1):
								vcofreq = int(vcolist[cnt-1])
								if vcofreq == 0 and vco_null_check:
									scrlist_append(("%d" %cnt,"SCR %d " %cnt +_("not used")))
								else:
									scrlist_append(("%d" %cnt,"SCR %d" %cnt))
								tmp.vco[article].append(ConfigInteger(default=vcofreq, limits = (vcofreq, vcofreq)))

							tmp.scr[article] = ConfigSelection(choices = scrlist, default = scrlist[0][0])

							tmp.lofl[article] = ConfigSubList()
							tmp.lofh[article] = ConfigSubList()
							tmp.loft[article] = ConfigSubList()

							tmp_lofl_article_append = tmp.lofl[article].append
							tmp_lofh_article_append = tmp.lofh[article].append
							tmp_loft_article_append = tmp.loft[article].append
							
							for cnt in range(1,positions+1):
								lofl = int(positionslist[cnt][0])
								lofh = int(positionslist[cnt][1])
								loft = int(positionslist[cnt][2])
								tmp_lofl_article_append(ConfigInteger(default=lofl, limits = (lofl, lofl)))
								tmp_lofh_article_append(ConfigInteger(default=lofh, limits = (lofh, lofh)))
								tmp_loft_article_append(ConfigInteger(default=loft, limits = (loft, loft)))
							products_valide_append(article)

					if len(products_valide)==0:
						products_valide_append("None")
					tmp.product = ConfigSelection(choices = products_valide, default = products_valide[0])
					sectionDict[manufacturer] = tmp

			print "MATRIX"
			section.unicableMatrix = ConfigSubDict()
			section.unicableMatrixManufacturer = ConfigSelection(UnicableMatrixManufacturers, UnicableMatrixManufacturers[0])
			fillUnicableConf(section.unicableMatrix, unicablematrixproducts, True)

			print "LNB"
			section.unicableLnb = ConfigSubDict()
			section.unicableLnbManufacturer = ConfigSelection(UnicableLnbManufacturers, UnicableLnbManufacturers[0])
			fillUnicableConf(section.unicableLnb, unicablelnbproducts, False)

			#TODO satpositions for satcruser

			section.bootuptimeuser = ConfigInteger(default=2700, limits = (0, 15000))
			section.dictionuser = ConfigSelection(advanced_lnb_diction_user_choices, default="EN50494")
			section.satcruserEN50494 = ConfigSelection(advanced_lnb_satcr_user_choicesEN50494, default="1")
			section.satcruserEN50607 = ConfigSelection(advanced_lnb_satcr_user_choicesEN50607, default="1")

			tmpEN50494 = ConfigSubList()
			for i in (1284, 1400, 1516, 1632, 1748, 1864, 1980, 2096):
				tmpEN50494.append(ConfigInteger(default=i, limits = (950, 2150)))
			section.satcrvcouserEN50494 = tmpEN50494

			tmpEN50607 = ConfigSubList()
			for i in (1210, 1420, 1680, 2040, 984, 1020, 1056, 1092, 1128, 1164, 1256, 1292, 1328, 1364, 1458, 1494, 1530, 1566, 1602, 1638, 1716, 1752, 1788, 1824, 1860, 1896, 1932, 1968, 2004, 2076, 2112, 2148):
				tmpEN50607.append(ConfigInteger(default=i, limits = (950, 2150)))
			section.satcrvcouserEN50607 = tmpEN50607

			nim.advanced.unicableconnected = ConfigYesNo(default=False)
			nim.advanced.unicableconnectedTo = ConfigSelection([(str(id), nimmgr.getNimDescription(id)) for id in nimmgr.getNimListOfType("DVB-S") if id != x])
			if nim.advanced.unicableconnected.value == True and nim.advanced.unicableconnectedTo.value != nim.advanced.unicableconnectedTo.saved_value:
				from Tools.Notifications import AddPopup
				from Screens.MessageBox import MessageBox
				nim.advanced.unicableconnected.value = False
				nim.advanced.unicableconnected.save()
#TODO the following three lines correct the error: 'msgid' format string with unnamed arguments cannot be properly localized
#				tuner1 = chr(int(x) + ord('A'))
#				tuner2 =  chr(int(nim.advanced.unicableconnectedTo.saved_value) + ord('A'))
#				txt = _("Misconfigured unicable connection from tuner %(tuner1)s to tuner %(tuner2)s!\nTuner %(tuner1)s option \"connected to\" are disabled now") % locals()
				txt = _("Misconfigured unicable connection from tuner %s to tuner %s!\nTuner %s option \"connected to\" are disabled now") % (chr(int(x) + ord('A')), chr(int(nim.advanced.unicableconnectedTo.saved_value) + ord('A')), chr(int(x) + ord('A')),)
				AddPopup(txt, type = MessageBox.TYPE_ERROR, timeout = 0, id = "UnicableConnectionFailed")

			section.unicableTuningAlgo = ConfigSelection([("reliable", _("reliable")),("traditional", _("traditional (fast)")),("reliable_retune", _("reliable, retune")),("traditional_retune", _("traditional (fast), retune"))], default="reliable_retune")

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
			section.powerThreshold = ConfigInteger(default=hw.get_device_name() == "dm7025" and 50 or 15, limits=(0, 100))
			section.turningSpeed = ConfigSelection(turning_speed_choices, "fast")
			section.fastTurningBegin = ConfigDateTime(default=advanced_lnb_fast_turning_btime, formatstring = _("%H:%M"), increment = 600)
			section.fastTurningEnd = ConfigDateTime(default=advanced_lnb_fast_turning_etime, formatstring = _("%H:%M"), increment = 600)

	def configLNBChanged(configElement):
		x = configElement.slot_id
		nim = config.Nims[x].dvbs
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
			if lnb > maxFixedLnbPositions:
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
		nim = config.Nims[slot_id].dvbs
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
				lnbnum = maxFixedLnbPositions + x - 3600
				lnb = ConfigSelection([("0", _("not configured")), (str(lnbnum), "LNB %d"%(lnbnum))], "0")
				lnb.slot_id = slot_id
				lnb.addNotifier(configLNBChanged, initial_call = False)
				tmp.lnb = lnb
				nim.advanced.sat[x] = tmp

	def scpcSearchRangeChanged(configElement):
		fe_id = configElement.fe_id
		slot_id = configElement.slot_id
		name = nimmgr.nim_slots[slot_id].description
		if path.exists("/proc/stb/frontend/%d/use_scpc_optimized_search_range" % fe_id):
			f = open("/proc/stb/frontend/%d/use_scpc_optimized_search_range" % fe_id, "w")
			f.write(configElement.value)
			f.close()

	def toneAmplitudeChanged(configElement):
		fe_id = configElement.fe_id
		slot_id = configElement.slot_id
		if path.exists("/proc/stb/frontend/%d/tone_amplitude" % fe_id):
			f = open("/proc/stb/frontend/%d/tone_amplitude" % fe_id, "w")
			f.write(configElement.value)
			f.close()

	def t2miRawModeChanged(configElement):
		fe_id = configElement.fe_id
		slot_id = configElement.slot_id
		if path.exists("/proc/stb/frontend/%d/t2mirawmode" % fe_id):
			f = open("/proc/stb/frontend/%d/t2mirawmode" % fe_id, "w")
			f.write(configElement.value)
			f.close()

	def connectedToChanged(slot_id, nimmgr, configElement):
		configMode = nimmgr.getNimConfig(slot_id).dvbs.configMode
		if configMode.value == 'loopthrough':
			internally_connectable = nimmgr.nimInternallyConnectableTo(slot_id)
			dest_slot = configElement.value
			if internally_connectable is not None and int(internally_connectable) == int(dest_slot):
				configMode.choices.updateItemDescription(configMode.index, _("internally loopthrough to"))
			else:
				configMode.choices.updateItemDescription(configMode.index, _("externally loopthrough to"))

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
			nim.t2miRawMode = ConfigSelection([("disable", _("disabled")), ("enable", _("enabled"))], "disable")
			nim.t2miRawMode.fe_id = x - empty_slots
			nim.t2miRawMode.slot_id = x
			nim.t2miRawMode.addNotifier(t2miRawModeChanged)
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
			nim.scan_networkid
		except:
			list = [(x[0], x[0]) for x in nimmgr.cablesList]
			nim.scan_networkid = ConfigInteger(default = 0, limits = (0, 99999))
			possible_scan_types = [("bands", _("Frequency bands")), ("steps", _("Frequency steps")), ("provider", _("Provider"))]
			nim.scan_provider = ConfigSelection(default = "0", choices = list)
			nim.scan_type = ConfigSelection(default = "provider", choices = possible_scan_types)
			nim.scan_band_EU_VHF_I = ConfigYesNo(default = True)
			nim.scan_band_EU_MID = ConfigYesNo(default = True)
			nim.scan_band_EU_VHF_III = ConfigYesNo(default = True)
			nim.scan_band_EU_UHF_IV = ConfigYesNo(default = True)
			nim.scan_band_EU_UHF_V = ConfigYesNo(default = True)
			nim.scan_band_EU_SUPER = ConfigYesNo(default = True)
			nim.scan_band_EU_HYPER = ConfigYesNo(default = True)
			nim.scan_band_US_LOW = ConfigYesNo(default = False)
			nim.scan_band_US_MID = ConfigYesNo(default = False)
			nim.scan_band_US_HIGH = ConfigYesNo(default = False)
			nim.scan_band_US_SUPER = ConfigYesNo(default = False)
			nim.scan_band_US_HYPER = ConfigYesNo(default = False)
			nim.scan_frequency_steps = ConfigInteger(default = 1000, limits = (1000, 10000))
			nim.scan_mod_qam16 = ConfigYesNo(default = False)
			nim.scan_mod_qam32 = ConfigYesNo(default = False)
			nim.scan_mod_qam64 = ConfigYesNo(default = True)
			nim.scan_mod_qam128 = ConfigYesNo(default = False)
			nim.scan_mod_qam256 = ConfigYesNo(default = True)
			nim.scan_sr_6900 = ConfigYesNo(default = True)
			nim.scan_sr_6875 = ConfigYesNo(default = True)
			nim.scan_sr_ext1 = ConfigInteger(default = 0, limits = (0, 7230))
			nim.scan_sr_ext2 = ConfigInteger(default = 0, limits = (0, 7230))

	def createTerrestrialConfig(nim, x):
		try:
			nim.terrestrial
		except:
			list = [(x[0], x[0]) for x in nimmgr.terrestrialsList]
			nim.terrestrial = ConfigSelection(choices = list)
			nim.terrestrial_5V = ConfigOnOff()

	def createATSCConfig(nim, x):
		try:
			nim.atsc
		except:
			list = [(x[0], x[0]) for x in nimmgr.atscList]
			nim.atsc = ConfigSelection(choices = list)

	try:
		for slot in nimmgr.nim_slots:
			if slot.frontend_id is not None:
				types = [type for type in ["DVB-C", "DVB-T", "DVB-T2", "DVB-S", "DVB-S2", "DVB-S2X", "ATSC"] if eDVBResourceManager.getInstance().frontendIsCompatible(slot.frontend_id, type)]
				if "DVB-T2" in types:
					# DVB-T2 implies DVB-T support
					types.remove("DVB-T")
				if "DVB-S2" in types:
					# DVB-S2 implies DVB-S support
					types.remove("DVB-S")
				if "DVB-S2X" in types:
					# DVB-S2X implies DVB-S2 support
					types.remove("DVB-S2")
				if len(types) > 1:
					slot.multi_type = {}
					for type in types:
						slot.multi_type[str(types.index(type))] = type
	except:
		pass

	empty_slots = 0
	for slot in nimmgr.nim_slots:
		x = slot.slot
		nim = config.Nims[x]
		nim.force_legacy_signal_stats = ConfigYesNo(default = False)
		if slot.canBeCompatible("DVB-S"):
			nim = config.Nims[x].dvbs
			createSatConfig(nim, x, empty_slots)
			config_mode_choices = [("nothing", _("nothing connected")),
				("simple", _("simple")), ("advanced", _("advanced"))]
			if len(nimmgr.getNimListOfType(slot.type, exception = x)) > 0:
				config_mode_choices.append(("equal", _("equal to")))
				config_mode_choices.append(("satposdepends", _("second cable of motorized LNB")))
			if len(nimmgr.canConnectTo(x)) > 0:
				config_mode_choices.append(("loopthrough", _("loopthrough to")))
			nim.advanced = ConfigNothing()
			if slot.isMultiType():
				tmp = ConfigSelection(config_mode_choices, "nothing")
			else:
				tmp = ConfigSelection(config_mode_choices, "simple")
			tmp.slot_id = x
			tmp.addNotifier(configModeChanged, initial_call = False)
			nim.configMode = tmp
			nim.configMode.connectedToChanged = boundFunction(connectedToChanged, x, nimmgr)
			nim.connectedTo.addNotifier(boundFunction(connectedToChanged, x, nimmgr), initial_call = False)
		if slot.canBeCompatible("DVB-C"):
			nim = config.Nims[x].dvbc
			nim.configMode = ConfigSelection(
				choices = {
					"enabled": _("enabled"),
					"nothing": _("nothing connected"),
					},
				default = "enabled")
			createCableConfig(nim, x)
		if slot.canBeCompatible("DVB-T"):
			nim = config.Nims[x].dvbt
			nim.configMode = ConfigSelection(
				choices = {
					"enabled": _("enabled"),
					"nothing": _("nothing connected"),
					},
				default = "enabled")
			createTerrestrialConfig(nim, x)
		if slot.canBeCompatible("ATSC"):
			nim = config.Nims[x].atsc
			nim.configMode = ConfigSelection(
				choices = {
					"enabled": _("enabled"),
					"nothing": _("nothing connected"),
					},
				default = "enabled")
			createATSCConfig(nim, x)
		if not(slot.canBeCompatible("DVB-S") or slot.canBeCompatible("DVB-T") or slot.canBeCompatible("DVB-C") or slot.canBeCompatible("ATSC")):
			empty_slots += 1
			nim.configMode = ConfigSelection(choices = { "nothing": _("disabled") }, default="nothing")
			if slot.type is not None:
				print "pls add support for this frontend type!", slot.type

	nimmgr.sec = SecConfigure(nimmgr)

	def tunerTypeChanged(nimmgr, configElement):
		if int(iDVBFrontend.dvb_api_version) < 5 or getBrandOEM() in ('vuplus'):
			print "dvb_api_version ",iDVBFrontend.dvb_api_version
			print "api <5 or old style tuner driver"
			fe_id = configElement.fe_id
			slot = nimmgr.nim_slots[fe_id]
			raw_channel = eDVBResourceManager.getInstance().allocateRawChannel(fe_id)
			if raw_channel is None:
				print "[ERROR] no raw channel, type change failed"
				return False
			frontend = raw_channel.getFrontend()
			if frontend is None:
				print "[ERROR] no frontend, type change failed"
				return False
			if slot.isMultiType():
				eDVBResourceManager.getInstance().setFrontendType(slot.frontend_id, "dummy", False) #to force a clear of m_delsys_whitelist
				types = slot.getMultiTypeList()
				#print"[adenin]",types
				for FeType in types.itervalues():
					if FeType in ("DVB-S", "DVB-S2", "DVB-S2X") and config.Nims[slot.slot].dvbs.configMode.value == "nothing":
						continue
					elif FeType in ("DVB-T", "DVB-T2") and config.Nims[slot.slot].dvbt.configMode.value == "nothing":
						continue
					elif FeType in ("DVB-C", "DVB-C2") and config.Nims[slot.slot].dvbc.configMode.value == "nothing":
						continue
					elif FeType in ("ATSC") and config.Nims[slot.slot].atsc.configMode.value == "nothing":
						continue
					eDVBResourceManager.getInstance().setFrontendType(slot.frontend_id, FeType, True)
			else:
				eDVBResourceManager.getInstance().setFrontendType(slot.frontend_id, slot.getType())
			system = configElement.getText()
			if path.exists("/proc/stb/frontend/%d/mode" % fe_id):
				cur_type = int(open("/proc/stb/frontend/%d/mode" % fe_id, "r").read())
				if cur_type != int(configElement.value):
					print "tunerTypeChanged feid %d from %d to mode %d" % (fe_id, cur_type, int(configElement.value))

					try:
						oldvalue = open("/sys/module/dvb_core/parameters/dvb_shutdown_timeout", "r").readline()
						f = open("/sys/module/dvb_core/parameters/dvb_shutdown_timeout", "w")
						f.write("0")
						f.close()
					except:
						print "[info] no /sys/module/dvb_core/parameters/dvb_shutdown_timeout available"

					for x in iDVBFrontendDict.iteritems():
						if x[1] == system:
							frontend.overrideType(x[0])
							break
					frontend.closeFrontend()
					f = open("/proc/stb/frontend/%d/mode" % fe_id, "w")
					f.write(configElement.value)
					f.close()
					frontend.reopenFrontend()
					try:
						f = open("/sys/module/dvb_core/parameters/dvb_shutdown_timeout", "w")
						f.write(oldvalue)
						f.close()
					except:
						print "[info] no /sys/module/dvb_core/parameters/dvb_shutdown_timeout available"


					nimmgr.enumerateNIMs()
				else:
					print "tuner type is already %d" %cur_type
			else:
				print"[ERROR] path not found: /proc/stb/frontend/%d/mode" % fe_id

	empty_slots = 0
	for slot in nimmgr.nim_slots:
		x = slot.slot
		nim = config.Nims[x]
		addMultiType = False
		try:
			nim.multiType
		except:
			if slot.description.find("Sundtek SkyTV Ultimate III") > -1:
				print"[NimManager] Sundtek SkyTV Ultimate III detected, multiType = False"
				addMultiType = False
			else:
				addMultiType = True
		if slot.isMultiType() and addMultiType:
			typeList = []
			for id in slot.getMultiTypeList().keys():
				type = slot.getMultiTypeList()[id]
				typeList.append((id, type))
			nim.multiType = ConfigSelection(typeList, "0")

			nim.multiType.fe_id = x - empty_slots
			nim.multiType.addNotifier(boundFunction(tunerTypeChanged, nimmgr))

		print"[NimManager] slotname = %s, slotdescription = %s, multitype = %s, current type = %s" % (slot.input_name, slot.description,(slot.isMultiType()),slot.getType())

	empty_slots = 0
	for slot in nimmgr.nim_slots:
		x = slot.slot
		empty = True

		if update_slots and (x not in update_slots):
			continue

		if slot.canBeCompatible("DVB-S"):
			nim = config.Nims[x].dvbs
			createSatConfig(nim, x, empty_slots)
			empty = False
		if slot.canBeCompatible("DVB-C"):
			nim = config.Nims[x].dvbc
			createCableConfig(nim, x)
			empty = False
		if slot.canBeCompatible("DVB-T"):
			nim = config.Nims[x].dvbt
			createTerrestrialConfig(nim, x)
			empty = False
		if slot.canBeCompatible("ATSC"):
			nim = config.Nims[x].atsc
			createATSCConfig(nim, x)
			empty = False
		if empty:
			empty_slots += 1

nimmanager = NimManager()

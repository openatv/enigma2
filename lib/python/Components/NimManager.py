from config import config       #global config instance

from config import configElement
from config import ConfigSubsection
from config import ConfigSlider
from config import configSelection
from config import currentConfigSelectionElement
from config import getConfigSelectionElement
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
				if currentConfigSelectionElement(nim.configMode) == "loopthrough":
					self.linkNIMs(x, nim.linkedTo.value)
					nim = config.Nims[nim.linkedTo.value]
				elif currentConfigSelectionElement(nim.configMode) == "simple":		#simple config
					if currentConfigSelectionElement(nim.diseqcMode) == "single":			#single
						self.addLNBSimple(slotid = x, orbpos = int(nim.diseqcA.vals[nim.diseqcA.value][1]), toneburstmode = 0, diseqcmode = 0, diseqcpos = 4)
					elif currentConfigSelectionElement(nim.diseqcMode) == "toneburst_a_b":		#Toneburst A/B
						self.addLNBSimple(slotid = x, orbpos = int(nim.diseqcA.vals[nim.diseqcA.value][1]), toneburstmode = 1, diseqcmode = 0, diseqcpos = 4)
						self.addLNBSimple(slotid = x, orbpos = int(nim.diseqcB.vals[nim.diseqcB.value][1]), toneburstmode = 1, diseqcmode = 0, diseqcpos = 4)
					elif currentConfigSelectionElement(nim.diseqcMode) == "diseqc_a_b":		#DiSEqC A/B
						self.addLNBSimple(slotid = x, orbpos = int(nim.diseqcA.vals[nim.diseqcA.value][1]), toneburstmode = 0, diseqcmode = 1, diseqcpos = 0)
						self.addLNBSimple(slotid = x, orbpos = int(nim.diseqcB.vals[nim.diseqcB.value][1]), toneburstmode = 0, diseqcmode = 1, diseqcpos = 1)
					elif currentConfigSelectionElement(nim.diseqcMode) == "diseqc_a_b_c_d":		#DiSEqC A/B/C/D
						self.addLNBSimple(slotid = x, orbpos = int(nim.diseqcA.vals[nim.diseqcA.value][1]), toneburstmode = 0, diseqcmode = 1, diseqcpos = 0)
						self.addLNBSimple(slotid = x, orbpos = int(nim.diseqcB.vals[nim.diseqcB.value][1]), toneburstmode = 0, diseqcmode = 1, diseqcpos = 1)
						self.addLNBSimple(slotid = x, orbpos = int(nim.diseqcC.vals[nim.diseqcC.value][1]), toneburstmode = 0, diseqcmode = 1, diseqcpos = 2)
						self.addLNBSimple(slotid = x, orbpos = int(nim.diseqcD.vals[nim.diseqcD.value][1]), toneburstmode = 0, diseqcmode = 1, diseqcpos = 3)
					elif currentConfigSelectionElement(nim.diseqcMode) == "positioner":		#Positioner
						self.addLNBSimple(slotid = x, diseqcmode = 3, longitude = float(str(nim.longitude.value[0]) + "." + str(nim.longitude.value[1])), loDirection = nim.longitudeOrientation.value - 2, latitude = float(str(nim.latitude.value[0]) + "." + str(nim.latitude.value[1])), laDirection = nim.latitudeOrientation.value)
					pass
				elif currentConfigSelectionElement(nim.configMode) == "nothing":
					pass
				else:																	#advanced config
					self.updateAdvanced(x)

	def updateAdvanced(self, slotid):
		sec = eDVBSatelliteEquipmentControl.getInstance()
		lnbSat = {}
		for x in range(1,33):
			lnbSat[x] = []
		for x in self.NimManager.satList:
			lnb = config.Nims[slotid].advanced.sat[x[1]].lnb.value
			if lnb != 0:
				lnbSat[lnb].append(x[1])
		for x in range(1,33):
			if len(lnbSat[x]) > 0:
				currLnb = config.Nims[slotid].advanced.lnb[x]
				sec.addLNB()
				sec.setLNBTunerMask(1 << slotid)
				if currentConfigSelectionElement(currLnb.lof) == "universal_lnb":
					sec.setLNBLOFL(9750000)
					sec.setLNBLOFH(10600000)
					sec.setLNBThreshold(11750000)
				elif currentConfigSelectionElement(currLnb.lof) == "c_band":
					sec.setLNBLOFL(5150000)
					sec.setLNBLOFH(5150000)
					sec.setLNBThreshold(5150000)
				elif currentConfigSelectionElement(currLnb.lof) == "user_defined":
					sec.setLNBLOFL(currLnb.lofl.value * 1000)
					sec.setLNBLOFH(currLnb.lofh.value * 1000)
					sec.setLNBThreshold(currLnb.threshold.value * 1000)
					
				if currentConfigSelectionElement(currLnb.output_12v) == "0V":
					pass
				elif currentConfigSelectionElement(currLnb.output_12v) == "12V":
					pass
				
				if currentConfigSelectionElement(currLnb.increased_voltage) == "yes":
					pass
				else:
					pass
				
				if currentConfigSelectionElement(currLnb.diseqcMode) == "none":
					pass
				elif currentConfigSelectionElement(currLnb.diseqcMode) == "1_0":
					pass
				elif currentConfigSelectionElement(currLnb.diseqcMode) == "1_1":
					pass
				elif currentConfigSelectionElement(currLnb.diseqcMode) == "1_2":
					pass

				if currentConfigSelectionElement(currLnb.diseqcMode) != "none":
					if currentConfigSelectionElement(currLnb.toneburst) == "none":
						pass
					elif currentConfigSelectionElement(currLnb.toneburst) == "A":
						pass
					elif currentConfigSelectionElement(currLnb.toneburst) == "B":
						pass


					if currentConfigSelectionElement(currLnb.commitedDiseqcCommand) == "none":
						pass
					elif currentConfigSelectionElement(currLnb.commitedDiseqcCommand) == "AA":
						pass
					elif currentConfigSelectionElement(currLnb.commitedDiseqcCommand) == "AB":
						pass
					elif currentConfigSelectionElement(currLnb.commitedDiseqcCommand) == "BA":
						pass				
					elif currentConfigSelectionElement(currLnb.commitedDiseqcCommand) == "BB":
						pass
				
					if currentConfigSelectionElement(currLnb.fastDiseqc) == "yes":
						pass
					else:
						pass
				
					if currentConfigSelectionElement(currLnb.sequenceRepeat) == "yes":
						pass
					else:
						pass
				
					if currentConfigSelectionElement(currLnb.diseqcMode) == "1_0":
						currCO = currLnb.commandOrder1_0.value
					else:
						currCO = currLnb.commandOrder.value
						
						pass # do something with currLnb.uncommittedDiseqcCommand.value... holds 0 for none, 1 for input 1, 2 for input 2 etc.
						
						if currentConfigSelectionElement(currLnb.diseqcRepeats) == "none":
							pass
						elif currentConfigSelectionElement(currLnb.diseqcRepeats) == "One":
							pass
						elif currentConfigSelectionElement(currLnb.diseqcRepeats) == "Two":
							pass
						elif currentConfigSelectionElement(currLnb.diseqcRepeats) == "Three":
							pass
										
					if currCO == 0: # committed, toneburst
						pass
					elif currCO == 1: # toneburst, committed
						pass
					elif currCO == 2: # committed, uncommitted, toneburst
						pass
					elif currCO == 3: # toneburst, committed, uncommitted
						pass
					elif currCO == 4: # uncommitted, committed, toneburst
						pass
					elif currCO == 5: # toneburst, uncommitted, commmitted
						pass
					
				if currentConfigSelectionElement(currLnb.diseqcMode) == "1_2":
					sec.setLatitude(float(str(currLnb.latitude.value[0]) + "." + str(currLnb.latitude.value[1])))
					sec.setLaDirection(nim.latitudeOrientation.value)
					sec.setLongitude(float(str(currLnb.longitude.value[0]) + "." + str(currLnb.longitude.value[1])))
					sec.setLoDirection(nim.longitudeOrientation.value - 2)

				if currentConfigSelectionElement(currLnb.powerMeasurement) == "yes":
					pass # set to currLnb.powerThreshold.value, which is an integer holding the mA value
	
				# finally add the orbital positions
				for y in lnbSat[x]:
					sec.addSatellite(y)
					currSat = config.Nims[slotid].advanced.sat[y]
					if currentConfigSelectionElement(currSat.voltage) == "polarization":
						pass
					elif currentConfigSelectionElement(currSat.voltage) == "13V":
						pass
					elif currentConfigSelectionElement(currSat.voltage) == "18V":
						pass

					if currentConfigSelectionElement(currSat.tonemode) == "band":
						pass
					elif currentConfigSelectionElement(currSat.tonemode) == "on":
						pass
					elif currentConfigSelectionElement(currSat.tonemode) == "off":
						pass
					
					if  currentConfigSelectionElement(currSat.usals) == "no":
						pass # use currSat.rotorposition.value to set the stored rotor position
					else:
						pass # use usals for this sat!
					
					
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

				self.transponders[self.parsedCab].append((1, freq, sr, mod, fec))

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

				self.transponders[self.parsedTer].append((2, freq, bw, const, crh, crl, guard, transm, hierarchy, inv))

	def getTransponders(self, pos):
		return self.transponders[pos]

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
		if (mode != 2): # not linked
			print "Unlinking slot " + str(slotid)
			# TODO call c++ to unlink nim in slot slotid
		if (mode == 2): # linked
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
			if slot.slotid == 0:
				nim.configMode = configElement(cname + "configMode", configSelection, 0, (("simple", _("Simple")), ("advanced", _("Advanced"))))
			else:							
				nim.configMode = configElement(cname + "configMode", configSelection, 0, (("simple", _("Simple")), ("nothing", _("Nothing connected")), ("loopthrough", _("Loopthrough to Socket A")), ("advanced", _("Advanced"))))
			
			#important - check if just the 2nd one is LT only and the first one is DVB-S
			if currentConfigSelectionElement(nim.configMode) == "loopthrough": #linked
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

			nim.diseqcMode = configElement(cname + "diseqcMode", configSelection, 2, (("single", _("Single")), ("toneburst_a_b", _("Toneburst A/B")), ("diseqc_a_b", _("DiSEqC A/B")), ("diseqc_a_b_c_d", _("DiSEqC A/B/C/D")), ("positioner", _("Positioner"))));
			nim.diseqcA = configElement(cname + "diseqcA", configSatlist, 192, nimmgr.satList);
			nim.diseqcB = configElement(cname + "diseqcB", configSatlist, 130, nimmgr.satList);
			nim.diseqcC = configElement(cname + "diseqcC", configSatlist, 0, nimmgr.satList);
			nim.diseqcD = configElement(cname + "diseqcD", configSatlist, 0, nimmgr.satList);
			nim.positionerMode = configElement(cname + "positionerMode", configSelection, 0, (("usals", _("USALS")), ("manual", _("manual"))));
			nim.longitude = configElement(cname + "longitude", configSequence, [5,100], configsequencearg.get("FLOAT", [(0,90),(0,999)]));
			nim.longitudeOrientation = configElement(cname + "longitudeOrientation", configSelection, 0, (_("East"), _("West")))
			nim.latitude = configElement(cname + "latitude", configSequence, [50,767], configsequencearg.get("FLOAT", [(0,90),(0,999)]));
			nim.latitudeOrientation = configElement(cname + "latitudeOrientation", configSelection, 0, (("north", _("North")), ("south", _("South"))))
			satNimList = nimmgr.getNimListOfType(nimmgr.nimType["DVB-S"], slot.slotid)
			satNimListNames = []
			for x in satNimList:
				satNimListNames.append((("Slot_" + ("A", "B", "C", "D")[x] + "_" + nimmgr.getNimName(x)), _("Slot ") + ("A", "B", "C", "D")[x] + ": " + nimmgr.getNimName(x)))
			nim.linkedTo = configElement(cname + "linkedTo", configSelection, 0, satNimListNames);
			
			#perhaps the instance of the slot is more useful?
			nim.configMode.addNotifier(boundFunction(nimConfigModeChanged,x))
			nim.diseqcMode.addNotifier(boundFunction(nimDiseqcModeChanged,x))
			nim.diseqcA.addNotifier(boundFunction(nimPortAChanged,int(x)))
			nim.diseqcB.addNotifier(boundFunction(nimPortBChanged,x))
			nim.diseqcC.addNotifier(boundFunction(nimPortCChanged,x))
			nim.diseqcD.addNotifier(boundFunction(nimPortDChanged,x))
			nim.linkedTo.addNotifier(boundFunction(nimLinkedToChanged,x))
			
			# advanced config:
			nim.advanced = ConfigSubsection()
			nim.advanced.sats = configElement(cname + "advanced.sats", configSatlist, 192, nimmgr.satList);
			nim.advanced.sat = {}
			lnbs = ["not available"]
			for y in range(1, 33):
				lnbs.append("LNB " + str(y))
			for x in nimmgr.satList:
				nim.advanced.sat[x[1]] = ConfigSubsection()
				nim.advanced.sat[x[1]].voltage = configElement(cname + "advanced.sat" + str(x[1]) + ".voltage", configSelection, 0, (("polarization", _("Polarization")), ("13V", _("13 V")), ("18V", _("18 V"))))
				nim.advanced.sat[x[1]].tonemode = configElement(cname + "advanced.sat" + str(x[1]) + ".tonemode", configSelection, 0, (("band", _("Band")), ("on", _("On")), ("off", _("Off"))))
				nim.advanced.sat[x[1]].usals = configElement(cname + "advanced.sat" + str(x[1]) + ".usals", configSelection, 0, (("yes", _("Yes")), ("no", _("No"))))
				nim.advanced.sat[x[1]].rotorposition = configElement(cname + "advanced.sat" + str(x[1]) + ".rotorposition", configSequence, [1], configsequencearg.get("INTEGER", (1, 255)))
				nim.advanced.sat[x[1]].lnb = configElement(cname + "advanced.sat" + str(x[1]) + ".lnb", configSelection, 0, lnbs)
			
			nim.advanced.lnb = [0]
			for x in range(1, 33):
				nim.advanced.lnb.append(ConfigSubsection())
				nim.advanced.lnb[x].lof = configElement(cname + "advanced.lnb" + str(x) + ".lof", configSelection, 0, (("universal_lnb", _("Universal LNB")), ("c_band", _("C-Band")), ("user_defined", _("User defined"))))
				nim.advanced.lnb[x].lofl = configElement(cname + "advanced.lnb" + str(x) + ".lofl", configSequence, [9750], configsequencearg.get("INTEGER", (0, 99999)))
				nim.advanced.lnb[x].lofh = configElement(cname + "advanced.lnb" + str(x) + ".lofh", configSequence, [10600], configsequencearg.get("INTEGER", (0, 99999)))
				nim.advanced.lnb[x].threshold = configElement(cname + "advanced.lnb" + str(x) + ".threshold", configSequence, [11750], configsequencearg.get("INTEGER", (0, 99999)))
				nim.advanced.lnb[x].output_12v = configElement(cname + "advanced.lnb" + str(x) + ".output_12v", configSelection, 0, (("0V", _("0 V")), ("12V", _("12 V"))))
				nim.advanced.lnb[x].increased_voltage = configElement(cname + "advanced.lnb" + str(x) + ".increased_voltage", configSelection, 0, (("no", _("No")), ("yes", _("Yes"))))
				nim.advanced.lnb[x].toneburst = configElement(cname + "advanced.lnb" + str(x) + ".toneburst", configSelection, 0, (("none", _("None")), ("A", _("A")), ("B", _("B"))))
				nim.advanced.lnb[x].diseqcMode = configElement(cname + "advanced.lnb" + str(x) + ".diseqcMode", configSelection, 0, (("none", _("None")), ("1_0", _("1.0")), ("1_1", _("1.1")), ("1_2", _("1.2"))))
				nim.advanced.lnb[x].commitedDiseqcCommand = configElement(cname + "advanced.lnb" + str(x) + ".commitedDiseqcCommand", configSelection, 0, (("none", _("None")), ("AA", _("AA")), ("AB", _("AB")), ("BA", _("BA")), ("BB", _("BB"))))
				nim.advanced.lnb[x].fastDiseqc = configElement(cname + "advanced.lnb" + str(x) + ".fastDiseqc", configSelection, 0, (("no", _("No")), ("yes", _("Yes"))))
				nim.advanced.lnb[x].sequenceRepeat = configElement(cname + "advanced.lnb" + str(x) + ".sequenceRepeat", configSelection, 0, (("no", _("No")), ("yes", _("Yes"))))
				nim.advanced.lnb[x].commandOrder1_0 = configElement(cname + "advanced.lnb" + str(x) + ".commandOrder1_0", configSelection, 0, ("committed, toneburst", "toneburst, committed"))
				nim.advanced.lnb[x].commandOrder = configElement(cname + "advanced.lnb" + str(x) + ".commandOrder", configSelection, 0, ("committed, toneburst", "toneburst, committed", "committed, uncommitted, toneburst", "toneburst, committed, uncommitted", "uncommitted, committed, toneburst", "toneburst, uncommitted, commmitted"))
				disCmd = ["none"]
				for y in range(1, 17):
					disCmd.append("Input " + str(y))
				nim.advanced.lnb[x].uncommittedDiseqcCommand = configElement(cname + "advanced.lnb" + str(x) + ".uncommittedDiseqcCommand", configSelection, 0, disCmd)
				nim.advanced.lnb[x].diseqcRepeats = configElement(cname + "advanced.lnb" + str(x) + ".diseqcRepeats", configSelection, 0, (("none", _("None")), ("one", _("One")), ("two", _("Two")), ("three", _("Three"))))
				nim.advanced.lnb[x].longitude = configElement(cname + "advanced.lnb" + str(x) + ".longitude", configSequence, [5,100], configsequencearg.get("FLOAT", [(0,90),(0,999)]));
				nim.advanced.lnb[x].longitudeOrientation = configElement(cname + "advanced.lnb" + str(x) + ".longitudeOrientation", configSelection, 0, (_("East"), _("West")))
				nim.advanced.lnb[x].latitude = configElement(cname + "advanced.lnb" + str(x) + ".latitude", configSequence, [50,767], configsequencearg.get("FLOAT", [(0,90),(0,999)]));
				nim.advanced.lnb[x].latitudeOrientation = configElement(cname + "advanced.lnb" + str(x) + ".latitudeOrientation", configSelection, 0, (("north", _("North")), ("south", _("South"))))
				nim.advanced.lnb[x].powerMeasurement = configElement(cname + "advanced.lnb" + str(x) + ".powerMeasurement", configSelection, 0, (("yes", _("Yes")), ("no", _("No"))))
				nim.advanced.lnb[x].powerThreshold = configElement(cname + "advanced.lnb" + str(x) + ".powerThreshold", configSequence, [50], configsequencearg.get("INTEGER", (0, 100)))
		elif slot.nimType == nimmgr.nimType["DVB-C"]:
			nim.cable = configElement(cname + "cable", configSelection, 0, nimmgr.cablesList);
		elif slot.nimType == nimmgr.nimType["DVB-T"]:
			nim.cable = configElement(cname + "terrestrial", configSelection, 0, nimmgr.terrestrialsList);
		else:
			print "pls add support for this frontend type!"		

	nimmgr.sec = SecConfigure(nimmgr)

nimmanager = NimManager()

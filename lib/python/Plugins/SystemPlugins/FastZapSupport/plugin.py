
from Plugins.Plugin import PluginDescriptor
import NavigationInstance

from Tools import Notifications
from Screens.MessageBox import MessageBox

from enigma import iPlayableService, iServiceInformation, eEnv

import struct
import os
import re

from Components.NimManager import nimmanager
from Components.config import ConfigNothing, config

from Components.ServiceEventTracker import ServiceEventTracker

from enigma import iPlayableService
from Screens.InfoBar import InfoBar

fast_zap_support = None

LANEDB_PATH = eEnv.resolve("${sysconfdir}/enigma2/") + "lamedb"

FAVOURITES_PATH = eEnv.resolve("${sysconfdir}/enigma2/") + "userbouquet.favourites.tv"

PROC_FBC_PATH = "/proc/stb/frontend/fbc"

#PROC_FBC_PATH = "/home/root/fbc"

def strToHex(s):
		return hex(int(s, 16))

class FastZapSupport:
	def __init__(self, session):
		self.session = session
		self.onClose = [ ] # hack

		self.channelList = []
#		self.srefList = []
		self.channelData = []
		self.procData = {}

		self.parseChannelDB()
		srefList = self.getSrefList()
		self.channelData = self.makeChannelData(srefList)

		self.parseNimConfiguration()
		self.writeDataProc(self.channelData)

		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
		{
			iPlayableService.evStart: self.serviceStarted,
		})

	def serviceStarted(self):
		if InfoBar.instance:
			channelList = InfoBar.instance.servicelist

			prevService = channelList.servicelist.getPrev().toString()
			curService = channelList.servicelist.getCurrent().toString()
			nextService = channelList.servicelist.getNext().toString()
			
#			print "[FastZapSupport] PREV : ", prevService
#			print "[FastZapSupport] CUR : ", curService
#			print "[FastZapSupport] NEXT : ", nextService

			srefList = []
			srefList.append(prevService)
			srefList.append(nextService)

			# sref
			# type:flags:stype:sid:tsid:onid:namespace:psid:ptsid:

			channelData = self.makeChannelData(srefList)
			self.writeDataProc(channelData)

	def python_scanf(self, my_str, pattern):
		D = ('%d',      '(\d+?)')
		F = ('%f', '(\d+\.\d+?)')
		S = ('%s',       '(.+?)')
		re_pattern = pattern.replace(*D).replace(*F).replace(*S)
		match = re.match(re_pattern, my_str)
		if match:
			return match.groups()
		raise ValueError("String doesn't match pattern")

	def parseChannelDB(self):
		global LANEDB_PATH

		if not os.access(LANEDB_PATH, os.R_OK):
			return

		channelList = []
		f = open(LANEDB_PATH, "r")
		line = f.readline()

		try:
			version = self.python_scanf(line, "eDVB services /%d/")
			if len(version)!=1 or version[0] != '4':
#				print "invalid version"
				return None
		except Exception, ex:
#			print "[fastzapsupport] exception error : ", ex
			return None

		line = f.readline()

		if line != "transponders\n":
#			print "[FastZapSupport] no transponders"
			return None

		channel_idx = 0

		while 1:
			line = f.readline()
			if not line:
				break
			if line == "end\n":
				break
			tmp = line.strip('\n').split(':')
			if len(tmp) != 3:
				continue

			channelID = {}
			channelID["namespace"] = tmp[0]
			channelID["tsid"] = tmp[1]
			channelID["onid"] = tmp[2]

			feParms = {}
			feParms["frequency"] = None
			feParms["symbol_rate"] = None
			feParms["polarisation"] = None
			feParms["fec"] = None
			feParms["orbital_position"] = None
			feParms["inversion"] = None
			feParms["flags"] = None
			feParms["system"] = None
			feParms["modulation"] = None
			feParms["rolloff"] = None
			feParms["pilot"] = None

			while 1:
				line = f.readline()
				if line == "/\n":
					break
				if line[1] == 's':
					s = line[3:].strip('\n').split(':')
					if len(s) >= 7:
						ss = s[:7]
						feParms["frequency"], feParms["symbol_rate"], feParms["polarisation"], feParms["fec"], feParms["orbital_position"], feParms["inversion"], feParms["flags"] = ss
						if feParms["polarisation"] < 0:
							feParms["polarisation"] += 3600

						feParms["system"] = '0' # DVB-S
						feParms["modulation"] = '1' # QPSK
						feParms["rolloff"] = '0' # 0.35
						feParms["pilot"] = '2' # unknown

					if len(s) >= 8:
						ss = s[7:]
						feParms["system"], feParms["modulation"], feParms["rolloff"], feParms["pilot"] = ss

			if feParms["frequency"] is None:
				continue

			channel = {}
			channel["channelID"] = channelID
			channel["feParms"] = feParms
			channel["idx"] = channel_idx
			channelList.append(channel)
			channel_idx += 1

#		print "[FastZapSupport] %d transponders" % len(channelList)
		self.channelList = channelList

	def parseNimConfiguration(self):
		self.diseqc_position = {}
		for x in nimmanager.nim_slots:
			nimConfig = nimmanager.getNimConfig(x.slot)

			if x.isCompatible("DVB-S"):
				if nimConfig.configMode.value == "simple":
#					print "[FastZapSupport] nimConfig.diseqcMode.value : ", nimConfig.diseqcMode.value
					if nimConfig.diseqcMode.value == "single" and not nimConfig.simpleSingleSendDiSEqC.value:					
						continue

					elif nimConfig.diseqcMode.value == "diseqc_a_b" or nimConfig.diseqcMode.value == "diseqc_a_b_c_d":
						pass

					else:
						continue

					if nimConfig.diseqcA.orbital_position != 3601: # 3601: nothing connected
						if not self.diseqc_position.has_key(nimConfig.diseqcA.orbital_position):
							self.diseqc_position[nimConfig.diseqcA.orbital_position] = {"pos" : "AA", "lofth" : 11700000}

					if nimConfig.diseqcB.orbital_position != 3601:
						if not self.diseqc_position.has_key(nimConfig.diseqcB.orbital_position):
							self.diseqc_position[nimConfig.diseqcB.orbital_position] = {"pos" : "AB", "lofth" : 11700000}

					if nimConfig.diseqcC.orbital_position != 3601:
						if not self.diseqc_position.has_key(nimConfig.diseqcC.orbital_position):
							self.diseqc_position[nimConfig.diseqcC.orbital_position] = {"pos" : "BA", "lofth" : 11700000}

					if nimConfig.diseqcD.orbital_position != 3601:
						if not self.diseqc_position.has_key(nimConfig.diseqcD.orbital_position):
							self.diseqc_position[nimConfig.diseqcD.orbital_position] = {"pos" : "BB", "lofth": 11700000}

				elif nimConfig.configMode.value == "advanced":
					if nimConfig.advanced.sats.orbital_position is None:
						continue

					cur_orb_pos = nimConfig.advanced.sats.orbital_position
					satlist = nimConfig.advanced.sat.keys()

					if cur_orb_pos not in satlist:
						cur_orb_pos = satlist[0]

					currSat = nimConfig.advanced.sat[cur_orb_pos]
					lnbnum = int(currSat.lnb.value)
					currLnb = nimConfig.advanced.lnb[lnbnum]

					if isinstance(currLnb, ConfigNothing):
						continue

					if currLnb.lof.value == "universal_lnb":
						lofth = 11700000

					elif currLnb.lof.value == "user_defined":
						lofth = int(currLnb.threshold.value) * 1000
					else:
						continue

					if currLnb.diseqcMode.value == "none":
						continue

					if currLnb.commitedDiseqcCommand.value == "none":
						continue

					if currLnb.commitedDiseqcCommand.value in ["AA", "AB", "BA", "BB"]:
						position = currLnb.commitedDiseqcCommand.value

					else:
						position = "AA"

					self.diseqc_position[cur_orb_pos] = {"pos" : position, "lofth" : lofth}

	def getTone(self, frequency, orbital_position):
		tone = "low"
		lofth = 11700000

		if self.diseqc_position.has_key(orbital_position):
			lofth = self.diseqc_position[orbital_position]["lofth"]

		if frequency > lofth:
			tone = "high"

		return tone

	def getPosition(self, orbital_position):
		if self.diseqc_position.has_key(orbital_position):
			return self.diseqc_position[orbital_position]["pos"]

		return None

	def getSrefList(self):
		srefList = []

		global FAVOURITES_PATH

		if not os.access(FAVOURITES_PATH, os.R_OK):
#			print "[FastZapSupport] Error, %s not found." % FAVOURITES_PATH
			return

		f = open(FAVOURITES_PATH, "r")
		while 1:
			line = f.readline()
			if not line:
				break

			if not line.startswith("#SERVICE"):
				continue

			data = line.split(' ')
			if (len(data) != 2):
				continue

			res = re.search("\d+:\d+:\w+:\w+:\w+:\w+:\w+:\w+:\w+:\w+:", data[1])

			if res:
				sref = res.group()
				sref_split = sref.split(":")
				type = int(sref_split[0])
				flag = int(sref_split[1])
				stype = int(sref_split[2], 16) # hex to int
				if type != 1 or flag != 0:
					continue

				# VIDEO : 1, 17, 22, 25, 134, 195
				# AUDIO : 2, 10
				# HEVC : 31
				if not stype in (1, 17, 22, 25, 134, 195, 2, 10, 31):
					continue # unknown service type

				if sref not in srefList:
					srefList.append(sref)

#		print "[FastZapSupport] TOTAL %d Services" % len(srefList)

		return srefList

	def getChannel(self, sref):
		sref_tsid = strToHex(sref.split(":")[4])
		sref_onid = strToHex(sref.split(":")[5])
		sref_namespace = strToHex(sref.split(":")[6])
		for channel in self.channelList:
			channel_tsid = strToHex(channel["channelID"]["tsid"])
			channel_onid = strToHex(channel["channelID"]["onid"])
			channel_namespace = strToHex(channel["channelID"]["namespace"])
			if (sref_tsid == channel_tsid) and (sref_onid == channel_onid) and (sref_namespace == channel_namespace):
				return channel

		return None

	def makeChannelData(self, srefList):
		channelData = []
		for sref in srefList:
			channel = self.getChannel(sref)
			if channel is None:
				continue

			if channel not in channelData:
				channelData.append((channel, sref))

#		print "[FastZapSupport] TOTAL %d channels" % len(channelData)

		return channelData

	def writeDataProc(self, channelData):
		global PROC_FBC_PATH

		if not os.access(PROC_FBC_PATH, os.F_OK):
#			print "[FastZapSupport] Error, %s not found!" % PROC_FBC_PATH
			return

		fbc_proc_list = ["frequency", "symbolrate", "polarisation", "fec", "inv", "system", "modulation", "rolloff", "pilot", "tone", "position", "sid"]
		procData = {}

		for c in fbc_proc_list:
			procData[c] = []

		pol_table = ["h", "v"]
		fec_table = ["auto", "12", "23", "34", "56", "78", "89", "35", "45", "910", "none"]
		inv_table = ["on", "off", "auto"]
		system_table = ["dvbs", "dvbs2"]
		modulation_table = ["auto", "qpsk", "8psk", "qam16"]
		rolloff_table = ["0_35", "0_25", "0_20"]
		pilot_table = ["off", "on", "auto"]
		position_table = {"AA" : "a", "AB" : "b", "BA" : "c", "BB" : "d"}

		for (channel, sref) in channelData:
			feParms = channel["feParms"]

			position = self.getPosition(int(feParms["orbital_position"]))
			if position is None:
				continue

			procData["position"].append(position_table[position]) # aa, ab, ba, bb

			procData["frequency"].append(str(feParms["frequency"]))
			procData["symbolrate"].append(str(feParms["symbol_rate"]))
			procData["polarisation"].append(pol_table[int(feParms["polarisation"])])
			procData["fec"].append(fec_table[int(feParms["fec"])])
			procData["inv"].append(inv_table[int(feParms["inversion"])])
			procData["system"].append(system_table[int(feParms["system"])])

			if system_table[int(feParms["system"])] == "dvbs2":
				procData["modulation"].append( modulation_table[int(feParms["modulation"])] )
				procData["rolloff"].append(  rolloff_table[int(feParms["rolloff"])] )
				procData["pilot"].append( pilot_table[int(feParms["pilot"])] )

			else:
				procData["modulation"].append("none")
				procData["rolloff"].append("none")
				procData["pilot"].append("none")

			procData["tone"].append(self.getTone(int(feParms["frequency"]), int(feParms["orbital_position"]))) # low or high

			sid = str(int(sref.split(":")[3], 16))
			procData["sid"].append(sid)

		total = len(procData["position"])
		for c in fbc_proc_list:
			if self.procData.get(c, []) != procData[c]:
				procPath = "%s/%s" % (PROC_FBC_PATH, c)

				data = str(total) + " " + ','.join(procData[c])
				if not os.access(procPath, os.W_OK):
#					print "[FastZapSupport] %s not found, skip write (data : %s)" % (procPath, data)
					continue

#				print "[FastZapSupport] %s data updated" % procPath

				open("%s/%s" % (PROC_FBC_PATH, c) , "w").write(data)

				self.procData[c] = procData[c]

def FastZapSupportInit(reason, **kwargs):
	if kwargs.has_key("session"):
		session = kwargs["session"]
		global fast_zap_support
		fast_zap_support = FastZapSupport(session)

def SatConfigChanged():
	global fast_zap_support
	fast_zap_support.parseNimConfiguration()
	fast_zap_support.writeDataProc(fast_zap_support.channelData)

def lamedbChanged():
	global fast_zap_support
	fast_zap_support.parseChannelDB()

from Components.config import config, ConfigSubsection, ConfigBoolean
config.plugins.fastzapsetup = ConfigSubsection()
config.plugins.fastzapsetup.activate = ConfigBoolean(default = False)

class FastZapSetup:
	def __init__(self):
		config.plugins.fastzapsetup.activate.addNotifier(self.updateProc)

	def getExtensionName(self):
		if config.plugins.fastzapsetup.activate.value:
			return _("Disable FastZapping")

		return _("Enable FastZapping")

	def updateToggle(self):
		if config.plugins.fastzapsetup.activate.value:
			config.plugins.fastzapsetup.activate.value = False
		else:
			config.plugins.fastzapsetup.activate.value = True

	def updateProc(self, configElement):
		val = configElement.value and "enable" or "disable"
		try:
			global PROC_FBC_PATH
			procPath = "%s/fcc" % PROC_FBC_PATH
			print "[FastZapSetup] write %s to %s" % (val ,procPath)
			open(procPath, "w").write(val)

		except Exception, ex:
			print "[FastZapSetup] exception error : ", ex

		configElement.save()

fastzapsetup_instance = FastZapSetup()
def addExtentions(infobarExtensions):
	infobarExtensions.addExtension((fastzapsetup_instance.getExtensionName, fastzapsetup_instance.updateToggle, lambda: True), None)

def Plugins(**kwargs):
	list = []
	list.append(
		PluginDescriptor(name="FastZapSupport",
		description="FastZapSupport",
		where = [PluginDescriptor.WHERE_SESSIONSTART],
		fnc = FastZapSupportInit))

	list.append(
		PluginDescriptor(name="FastZapSupport",
		description="FastZapSupport",
		where = [PluginDescriptor.WHERE_SATCONFIGCHANGED],
		fnc = SatConfigChanged))

	list.append(
		PluginDescriptor(name="FastZapSupport",
		description="FastZapSupport",
		where = [PluginDescriptor.WHERE_SERVICESCAN],
		fnc = lamedbChanged))

	list.append(
		PluginDescriptor(name="FastZapSetup",
		description="FastZapSetup",
		where = [PluginDescriptor.WHERE_EXTENSIONSINGLE],
		fnc = addExtentions))

	return list

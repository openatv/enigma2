# -*- coding: UTF-8 -*-
# Version 0.2
from Screens.Screen import Screen
from Components.Label import Label
from Components.ServiceEventTracker import ServiceEventTracker, InfoBarBase
from enigma import eTimer, eServiceCenter, iServiceInformation, iPlayableService, eDVBFrontendParametersSatellite, eDVBFrontendParametersCable
from Tools.Directories import fileExists, resolveFilename
import os
import re
from Components.config import ConfigSubsection, ConfigYesNo, config, ConfigNumber

config.SecondInfobar = ConfigSubsection()
config.SecondInfobar.emminfodelay = ConfigNumber(default=1000)
config.SecondInfobar.ecminfodelay = ConfigNumber(default=1000)
config.SecondInfobar.shownetdet = ConfigYesNo(default=True)
config.SecondInfobar.Enabled = ConfigYesNo(default=True)

ecmfile = "/tmp/ecm.info"

def parse_ecm(filename):
	addr = caid = pid = provid = port = ""
	source = ecmtime = hops = 0
	try:
		file = open(ecmfile, "r")
		for line in file.readlines():
			line = line.strip()
			if (line.find("CAID") >= 0): # camd3
				x = line.split(" ")
				caid = x[(x.index("CAID") + 1)].split(",")[0].strip()
			elif (line.find("CaID") >= 0): # mbox, incubus, mgcamd
				x = line.split(" ")
				caid = x[(x.index("CaID") + 1)].split(",")[0].strip()
			elif (line.find("caid") >= 0):
				x = line.split(":", 1)
				caid = x[1].strip()
			if (line.find("pid:") >= 0):
				x = line.split(":", 1)
				pid = x[1].strip()
			elif (line.find("pid") >= 0): # mbox, incubus, mgcamd
				x = line.split(" ")
				pid = x[(x.index("pid") + 1)].strip()
			elif (line.find("PID") >= 0): # camd3
				x = line.split(" ")
				pid = x[(x.index("PID") + 1)].split(",")[0].strip()
			if (line.find("prov:") >= 0): # mbox, incubus, mgcamd
				x = line.split(":", 1)
				provid = x[1].strip().split(",")[0]
			elif (line.find("provid:") >= 0):
				x = line.split(":", 1)
				provid = x[1].strip()
			elif (line.find("PROVIDER") >= 0): # camd3
				x = line.split(" ")
				provid = x[(x.index("PROVIDER") + 1)].split(",")[0].strip()
			if (line.find("msec") >= 0):
				x = line.split(" ", 1)
				ecmtime = int(x[0].strip())
			elif (line.find("ecm time:") >= 0):
				x = line.split(":", 1)
				ecmtime = int((float(x[1].strip()) * 1000))
			elif (line.find("dw delay:") >= 0): # incubus
				x = line.split(":", 1)
				ecmtime = x[1].strip()
			elif (line.find("Time:") >= 0): # mbox
				x = line.split(": (", 1)
				ecmtime = x[1].strip().split("ms)")[0]
			if (line.find("hops:") >= 0): # cccam, incubus
				x = line.split(":", 1)
				hops = int(x[1].strip())
			if (line.find("using:") >= 0): # cccam
				x = line.split(":", 1)
				if (x[1].strip() == "emu"):
					source = 1
				else:
					if ((x[1].strip() == "net") or ((x[1].strip() == "newcamd") or (x[1].strip() == "card share"))):
						source = 2
			elif (line.find("source:") >= 0):
				x = line.split(":")
				if (x[1].strip() == "emu"):
					source = 1
				elif (x[1].find("net") >= 0): # mgcamd
					source = 2
#					port = x[2].strip().split(")")[0]
#					addr = x[1].split(" ")[4]
				elif (x[1].strip() == "newcamd"):
					source = 2
			elif (line.find("FROM:") >= 0): # camd3
				x = line.split(":")
				if (x[1].strip() == "emu"):
					source = 1
				elif (x[1].strip() >= 0):
					source = 2
			elif (line.find("decode:") >= 0): # mbox
				x = line.split(":")
				if (x[1].strip() == "Local"):
					source = 1
				elif (x[1].strip() >= 0):
					source = 2
			elif (line.find("address:") >= 0): # incubus
				x = line.split(":")
				if (x[1].strip() == "cccam"):
					source = 2
				elif (x[1].strip() >= 0):
					source = 1
		file.close()
		return caid, pid, provid, ecmtime, source, addr, port, hops
	except:
		return 0

class SecondInfobarTool():

	def parseEcmInfoLine(self, line):
		if line.__contains__(":"):
			idx = line.index(":")
			line = line[idx+1:]
			line = line.replace("\n", "")
			while line.startswith(" "):
				line = line[1:]
			while line.endswith(" "):
				line = line[:-1]
			return line
		else:
			return ""

	def readEmuName(self, emu):
		try:
			if config.softcam.actCam.value:
				emu = config.softcam.actCam.value
			return emu
		except:
			return "None"

	def readSrvName(self, srv):
		try:
			f = open(ecmfile, "r")
			for line in f.readlines():
				line = line.lower()
				if line.startswith("decode:") or line.startswith("from:") or line.startswith("address:") or line.startswith("source:"):
					srv = self.parseEcmInfoLine(line)
					if (line.find("address:") >= 0):
						x = line.split("@", 1)
						srv = x[1].strip().split(":")[0]
					if (line.find("source:") >= 0):
						x = line.split("at", 1)
						srv = x[1].strip().split(":")[0]
					return srv
			f.close()
			return srv
		except:
			return "None"

	def readEmuActive(self):
		try:
			f = open("/var/emu/emuactive", "r")
			line = f.readline()
			f.close()
			return line[:-1]
		except:
			return "None"

	def readSrvActive(self):
		try:
			f = open("/var/emu/csactive", "r")
			line = f.readline()
			f.close()
			return line[:-1]
		except:
			return "None"

	def readEcmInfoFile(self, emu):
		try:
			f = open(ecmfile, "r")
			for line in f.readlines():
				line = line.lower()
				return line
			f.close()
			return line
		except:
			return "None"

	def readEcmInfo(self):
		info = parse_ecm(self.readEcmInfoFile())
		if info != 0:
			caid = info[0]
			pid = info[1]
			provid = info[2]
			ecmtime = info[3]
			source = info[4]
			addr = info[5]
			port = info[6]
			hops = info[7]
			returnMsg = ""
			if provid != "":
				returnMsg += "Provider: " + provid + "\n"
			if caid != "":
				returnMsg += "Ca ID: " + caid + "\n"
			if pid != "":
				returnMsg += "Pid: " + pid + "\n"
			if source == 0:
				returnMsg += "Decode: Unsupported!\n"
			elif source == 1:
				returnMsg += "Decode: Internal\n"
			elif source == 2:
				returnMsg += "Decode: Network\n"
				if config.SecondInfobar.shownetdet.value:
					if addr != "":
						returnMsg += "Source: " + addr + "\n"
			if hops > 0:
				returnMsg += "Hops: " + str(hops) + "\n"
			if ecmtime > 0:
				returnMsg += "ECM Time: " + str(ecmtime) + " msec\n"
			return returnMsg
		else:
			return "No Info"

t = SecondInfobarTool()

class SecondInfobar(Screen):

	def readEcmFile(self):
		emuActive = t.readEmuActive()
		return t.readEcmInfoFile(emuActive)

	def readEmuName(self):
		emuActive = t.readEmuActive()
		return t.readEmuName(emuActive)

	def readCsName(self):
		csActive = t.readSrvActive()
		return t.readSrvName(csActive)

	def showEmuName(self):
		self["emuname"].setText(self.readEmuName())
		csName = self.readCsName()
		if csName != "None":
			self["emuname"].setText(self["emuname"].getText() + " / " + csName)

	def __init__(self, session):
		Screen.__init__(self, session)
		self.systemCod = [
				"beta_no", "beta_emm", "beta_ecm",
				"seca_no", "seca_emm", "seca_ecm",
				"irdeto_no", "irdeto_emm", "irdeto_ecm",
				"cw_no", "cw_emm", "cw_ecm",
				"nagra_no", "nagra_emm", "nagra_ecm",
				"nds_no", "nds_emm", "nds_ecm",
				"via_no", "via_emm", "via_ecm", "conax_no",
				"conax_emm", "conax_ecm",
				"b_fta" , "b_emu", "b_spider"
				]

		self.systemCaids = {
				"06" : "irdeto", "01" : "seca", "18" : "nagra",
				"05" : "via", "0B" : "conax", "17" : "beta",
				"0D" : "cw", "4A" : "irdeto", "09" : "nds"
				}
		for x in self.systemCod:
			self[x] = Label()

		self["TunerInfo"] = Label()
		self["EmuInfo"] = Label()
		self["ecmtime"] = Label()
		self["netcard"] = Label()
		self["emuname"] = Label()
		self["mboxinfo"] = Label()
		self["cardinfo"] = Label()

		self.count = 0
		self.ecm_timer = eTimer()
		self.ecm_timer.timeout.get().append(self.__updateEmuInfo)
		self.emm_timer = eTimer()
		self.emm_timer.timeout.get().append(self.__updateEMMInfo)
		self.__evStart()

		self.__event_tracker = ServiceEventTracker(screen=self,eventmap=
			{
				iPlayableService.evStart: self.__evStart,
				iPlayableService.evUpdatedInfo: self.__evUpdatedInfo,
				iPlayableService.evTunedIn: self.__evTunedIn
			})
		self.onShow.append(self.showEmuName)
		self.onShow.append(self.__evTunedIn)

	def __evStart(self):
		if self.emm_timer.isActive():
			self.emm_timer.stop()
		if self.ecm_timer.isActive():
			self.ecm_timer.stop()
		self.count = 0
		self.displayClean()


	def __evTunedIn(self):
		service = self.session.nav.getCurrentService()
		info = service and service.info()
		if info is not None:
			self.displayClean()
			self.emm_timer.start(config.SecondInfobar.emminfodelay.value)
			self.ecm_timer.start(config.SecondInfobar.ecminfodelay.value)

	def __updateEMMInfo(self):
		self.emm_timer.stop()
		service = self.session.nav.getCurrentService()
		info = service and service.info()
		if info is not None:
			self.showEMM(info.getInfoObject(iServiceInformation.sCAIDs))


	def __updateEmuInfo(self):
		service = self.session.nav.getCurrentService()
		info = service and service.info()
		if info is not None:
			if info.getInfo(iServiceInformation.sIsCrypted):
				if self.count < 4:
					self.count = self.count + 1
				else:
					self.ecm_timer.changeInterval(10000)
				info = parse_ecm(self.readEcmFile())
				if info != 0:
					caid = info[0]
					pid = info[1]
					provid = info[2]
					ecmtime = info[3]
					source = info[4]
					addr = info[5]
					port = info[6]
					hops = info[7]

					if ecmtime > 0:
						self['ecmtime'].setText((('ECM Time: ' + str(ecmtime)) + ' msec'))
					if provid != '':
						self['EmuInfo'].setText(('Provider: ' + provid))
					if pid != '':
						self['EmuInfo'].setText(((self['EmuInfo'].getText() + '    Pid: ') + pid))
					if hops > 0:
						self['cardinfo'].setText('Hops: ' + str(hops))

					self['b_fta'].hide()
					self['b_emu'].hide()
					self['b_spider'].hide()

					if source == 0:
						self['netcard'].setText('Decode: Unsupported!')
					elif source == 1:
						self['b_emu'].show()
						self['netcard'].setText('Decode: Internal')
					elif source == 2:
						if addr != '':
							if (addr.find('127.0.0.1') or addr.find('localhost')) >= 0:
								self['netcard'].setText('Decode: Internal')
							else:
								self['b_spider'].show()
								if config.SecondInfobar.shownetdet.value:
									self['netcard'].setText('Source: ' + addr + ':' + port)
									if hops > 0:
										self['cardinfo'].setText(((self['cardinfo'].getText() + ' Hops: ') + str(hops)))
						else:
							self['b_spider'].show()
							self['netcard'].setText('Decode: Network')
					if caid != '':
						self['EmuInfo'].setText(self['EmuInfo'].getText() + '    Ca ID:' + caid)
						self.showECM(caid)
						self.showMbox(caid, provid)
			else:
				self['EmuInfo'].setText('')
				self['ecmtime'].setText('')
				self['netcard'].setText('')
				self['cardinfo'].setText('')
				self['b_fta'].show()


	def showECM(self, caid):
		caid = caid.lower()
		if caid.__contains__("x"):
			idx = caid.index("x")
			caid = caid[idx+1:]
			if len(caid) == 3:
				caid = "0%s" % caid
			caid = caid[:2]
			caid = caid.upper()
			if self.systemCaids.has_key(caid):
				system = self.systemCaids.get(caid)
				self[system + "_emm"].hide()
				self[system + "_ecm"].show()

	def int2hex(self, int):
		return "%x" % int

	def showEMM(self, caids):
		if caids:
			if len(caids) > 0:
				for caid in caids:
					caid = self.int2hex(caid)
					if len(caid) == 3:
						caid = "0%s" % caid
					caid = caid[:2]
					caid = caid.upper()
					if self.systemCaids.has_key(caid):
						system = self.systemCaids.get(caid)
						self[system + "_no"].hide()
						self[system + "_emm"].show()

	def displayClean(self):
		self["EmuInfo"].setText("")
		self["ecmtime"].setText("")
		self["netcard"].setText("")
		self["cardinfo"].setText("")
		for x in self.systemCod:
			self[x].hide()
			if x.find('_no') >= 0:
				self[x].show()

	def showMbox(self, provid, caid):
		verif = os.path.isfile("/tmp/mbox.ver")
		if (verif == False):
			self["mboxinfo"].hide()
		if (verif == True):
			self["mboxinfo"].show()
			cardlocal = 0
			verif = os.path.isfile("/tmp/share.info")
			if (verif == True):
				fichier = open("/tmp/share.info", "r")
				carte = fichier.readlines()
				fichier.close
				carteT = str((cardlocal + len(carte)))
				totalc = carteT
				localc = str(cardlocal)
				sharec = str(len(carte))
			else:
				localc = "0"
				totalc = "0"
				sharec = "0"
			verif = os.path.isfile("/tmp/share.onl")
			if (verif == True):
				fichier = open("/tmp/share.onl", "r")
				share = fichier.readlines()
				fichier.close
				peert = len(share)
				peert = str(peert)
				peerl = 0
				peerf = 0
				for i in share:
					if (i[0] == "0"):
						peerf = (peerf + 1)
					elif (i[0] == "1"):
						peerl = (peerl + 1)

				peerf = str(peerf)
				peerl = str(peerl)
			else:
				peert = "0"
				peerl = "0"
				peerf = "0"
		else:
			localc = "0"
			totalc = "0"
			sharec = "0"
			peert = "0"
			peerl = "0"
			peerf = "0"
		self["mboxinfo"].setText("Mbox Cards: " + totalc + " - " + localc + " - "  + sharec + "    " + "Mbox Peers: " + peert + " - " + peerl + " - " + peerf)


	def __evUpdatedInfo(self):
		self["TunerInfo"].setText("")
		service = self.session.nav.getCurrentService()
		frontendInfo = service.frontendInfo()
		frontendData = frontendInfo and frontendInfo.getAll(True)
		if frontendData is not None:
			tuner_type = frontendData.get("tuner_type", "None")
			sr = str(int(frontendData.get("symbol_rate", 0) / 1000))
			freq = str(int(frontendData.get("frequency", 0) / 1000))
			if tuner_type == "DVB-S":
				try:
					orb = {
						3590:'Thor/Intelsat (1.0°W)',3560:'Amos (4.0°W)',3550:'Atlantic Bird (5.0°W)',3530:'Nilesat/Atlantic Bird (7.0°W)',
						3520:'Atlantic Bird (8.0°W)',3475:'Atlantic Bird (12.5°W)',3460:'Express (14.0°W)', 3450:'Telstar (15.0°W)',
						3420:'Intelsat (18.0°W)',3380:'Nss (22.0°W)',3355:'Intelsat (24.5°W)', 3325:'Intelsat (27.5°W)',3300:'Hispasat (30.0°W)',
						3285:'Intelsat (31.5°W)',3170:'Intelsat (43.0°W)',3150:'Intelsat (45.0°W)',
						750:'Abs (75.0°E)',720:'Intelsat (72.0°E)',705:'Eutelsat W5 (70.5°E)',685:'Intelsat (68.5°E)',620:'Intelsat 902 (62.0°E)',
						600:'Intelsat 904 (60.0°E)',570:'Nss (57.0°E)',530:'Express AM22 (53.0°E)',480:'Eutelsat 2F2 (48.0°E)',450:'Intelsat (45.0°E)',
						420:'Turksat 2A (42.0°E)',400:'Express AM1 (40.0°E)',390:'Hellas Sat 2 (39.0°E)',380:'Paksat 1 (38.0°E)',
						360:'Eutelsat Sesat (36.0°E)',335:'Astra 1M (33.5°E)',330:'Eurobird 3 (33.0°E)', 328:'Galaxy 11 (32.8°E)',
						315:'Astra 5A (31.5°E)',310:'Turksat (31.0°E)',305:'Arabsat (30.5°E)',285:'Eurobird 1 (28.5°E)',
						284:'Eurobird/Astra (28.2°E)',282:'Eurobird/Astra (28.2°E)',
						260:'Badr 3/4 (26.0°E)',255:'Eurobird 2 (25.5°E)',235:'Astra 1E (23.5°E)',215:'Eutelsat (21.5°E)',
						216:'Eutelsat W6 (21.6°E)',210:'AfriStar 1 (21.0°E)',192:'Astra 1F (19.2°E)',160:'Eutelsat W2 (16.0°E)',
						130:'Hot Bird 6,7A,8 (13.0°E)',100:'Eutelsat W1 (10.0°E)',90:'Eurobird 9 (9.0°E)',70:'Eutelsat W3A (7.0°E)',
						50:'Sirius 4 (5.0°E)',48:'Sirius 4 (4.8°E)',30:'Telecom 2 (3.0°E)'
						}[frontendData.get("orbital_position", "None")]
				except:
					orb = 'Unsupported SAT: %s' % str([frontendData.get("orbital_position", "None")])
				pol = {
						eDVBFrontendParametersSatellite.Polarisation_Horizontal : "H",
						eDVBFrontendParametersSatellite.Polarisation_Vertical : "V",
						eDVBFrontendParametersSatellite.Polarisation_CircularLeft : "CL",
						eDVBFrontendParametersSatellite.Polarisation_CircularRight : "CR"
						}[frontendData.get("polarization", eDVBFrontendParametersSatellite.Polarisation_Horizontal)]
				fec = {
						eDVBFrontendParametersSatellite.FEC_None : "None",
						eDVBFrontendParametersSatellite.FEC_Auto : "Auto",
						eDVBFrontendParametersSatellite.FEC_1_2 : "1/2",
						eDVBFrontendParametersSatellite.FEC_2_3 : "2/3",
						eDVBFrontendParametersSatellite.FEC_3_4 : "3/4",
						eDVBFrontendParametersSatellite.FEC_5_6 : "5/6",
						eDVBFrontendParametersSatellite.FEC_7_8 : "7/8",
						eDVBFrontendParametersSatellite.FEC_3_5 : "3/5",
						eDVBFrontendParametersSatellite.FEC_4_5 : "4/5",
						eDVBFrontendParametersSatellite.FEC_8_9 : "8/9",
						eDVBFrontendParametersSatellite.FEC_9_10 : "9/10"
						}[frontendData.get("fec_inner", eDVBFrontendParametersSatellite.FEC_Auto)]
				self["TunerInfo"].setText( "Frequenz:  " + freq + " MHz " + pol + " " + fec + " " + sr + "    Satellite: " + orb)
			elif tuner_type == "DVB-C":
				try:
					fec = {
							eDVBFrontendParametersCable.FEC_None : "None",
							eDVBFrontendParametersCable.FEC_Auto : "Auto",
							eDVBFrontendParametersCable.FEC_1_2 : "1/2",
							eDVBFrontendParametersCable.FEC_2_3 : "2/3",
							eDVBFrontendParametersCable.FEC_3_4 : "3/4",
							eDVBFrontendParametersCable.FEC_5_6 : "5/6",
							eDVBFrontendParametersCable.FEC_7_8 : "7/8",
							eDVBFrontendParametersCable.FEC_8_9 : "8/9"
							}[frontendData.get("fec_inner", eDVBFrontendParametersSatellite.FEC_Auto)]
					self["TunerInfo"].setText( "Freq: " + freq + " MHz, Fec: " + fec + ", SR: " + sr )
				except:
					pass
			else:
				self["TunerInfo"].setText( "Freq: " + freq + " MHz, SR: " + sr )

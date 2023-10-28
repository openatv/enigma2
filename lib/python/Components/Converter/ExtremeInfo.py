from enigma import eDVBFrontendParametersCable, eDVBFrontendParametersSatellite, eServiceCenter, eServiceReference, iServiceInformation

from Components.Element import cached
from Components.Converter.Converter import Converter
from Components.Converter.Poll import Poll


class ExtremeInfo(Poll, Converter):
	TUNERINFO = 0
	CAMNAME = 1
	NUMBER = 2
	ECMINFO = 3
	IRDCRYPT = 4
	SECACRYPT = 5
	NAGRACRYPT = 6
	VIACRYPT = 7
	CONAXCRYPT = 8
	BETACRYPT = 9
	CRWCRYPT = 10
	DREAMCRYPT = 11
	NDSCRYPT = 12
	IRDECM = 13
	SECAECM = 14
	NAGRAECM = 15
	VIAECM = 16
	CONAXECM = 17
	BETAECM = 18
	CRWECM = 19
	DREAMECM = 20
	NDSECM = 21
	CAIDINFO = 22
	FTA = 23
	EMU = 24
	CRD = 25
	NET = 26
	TUNERINFOBP = 27
	BISCRYPT = 28
	BISECM = 29
	MGCAMD = 30
	BULCRYPT = 31
	BULECM = 32
# This is for future enhancement
#	OSCAM = 33
#	CAMD3 = 34
#	CCAM = 35
#	MBOX = 36
#	GBOX = 37
#	INCUBUS = 38
#	WICARDD = 39

	def __init__(self, type):
		Poll.__init__(self)
		Converter.__init__(self, type)
		self.list = []
		self.getLists()
		self.type = {
			"TunerInfo": self.TUNERINFO,
			"CamName": self.CAMNAME,
			"Number": self.NUMBER,
			"EcmInfo": self.ECMINFO,
			"CaidInfo": self.CAIDINFO,
			"IrdCrypt": self.IRDCRYPT,
			"SecaCrypt": self.SECACRYPT,
			"NagraCrypt": self.NAGRACRYPT,
			"ViaCrypt": self.VIACRYPT,
			"ConaxCrypt": self.CONAXCRYPT,
			"BetaCrypt": self.BETACRYPT,
			"CrwCrypt": self.CRWCRYPT,
			"DreamCrypt": self.DREAMCRYPT,
			"NdsCrypt": self.NDSCRYPT,
			"IrdEcm": self.IRDECM,
			"SecaEcm": self.SECAECM,
			"NagraEcm": self.NAGRAECM,
			"ViaEcm": self.VIAECM,
			"ConaxEcm": self.CONAXECM,
			"BetaEcm": self.BETAECM,
			"CrwEcm": self.CRWECM,
			"DreamEcm": self.DREAMECM,
			"NdsEcm": self.NDSECM,
			"Fta": self.FTA,
			"Emu": self.EMU,
			"Crd": self.CRD,
			"Net": self.NET,
			"TunerInfoBP": self.TUNERINFOBP,
			"BisCrypt": self.BISCRYPT,
			"BisEcm": self.BISECM,
			"Mgcamd": self.MGCAMD,
			"BulCrypt": self.BULCRYPT,
			"BulEcm": self.BULECM
# This is for future enhancement
#			"Oscam": self.OSCAM,
#			"Camd3": self.CAMD3,
#			"Cccam": self.CCAM,
#			"Mbox": self.MBOX,
#			"Gbox": self.GBOX,
#			"Incubus": self.INCUBUS,
#			"Wicardd": self.WICARDD
		}.get(type, self.TUNERINFO)

	@cached
	def getText(self):
		service = self.source.service
		info = service and service.info()
		if not info:
			return ""
		text = ""
		if self.type == self.TUNERINFO or self.type == self.TUNERINFOBP:
			text = self.getTunerInfo(service)
		elif self.type == self.CAMNAME:
			text = self.getCamName()
		elif self.type == self.NUMBER:
			name = info.getName().replace(" -*-", "").replace(" -*-", "")
			text = self.getServiceNumber(name, info.getInfoString(iServiceInformation.sServiceref))
		elif self.type == self.ECMINFO:
			ecmcam = self.getEcmCamInfo()
			text = ecmcam
		elif self.type == self.CAIDINFO:
			text = self.getCaidInfo()
		return text

	text = property(getText)

	@cached
	def getBoolean(self):
		self.poll_interval = 500
		self.poll_enabled = True
		service = self.source.service
		if service and service.info():
			value = {
				self.IRDCRYPT: self.getCrypt("06"),
				self.SECACRYPT: self.getCrypt("01"),
				self.NAGRACRYPT: self.getCrypt("18"),
				self.VIACRYPT: self.getCrypt("05"),
				self.CONAXCRYPT: self.getCrypt("0B"),
				self.BETACRYPT: self.getCrypt("17"),
				self.CRWCRYPT: self.getCrypt("0D"),
				self.DREAMCRYPT: self.getCrypt("4A"),
				self.NDSCRYPT: self.getCrypt("09"),
				self.IRDECM: self.getEcm("06"),
				self.SECAECM: self.getEcm("01"),
				self.NAGRAECM: self.getEcm("18"),
				self.VIAECM: self.getEcm("05"),
				self.CONAXECM: self.getEcm("0B"),
				self.BETAECM: self.getEcm("17"),
				self.CRWECM: self.getEcm("0D"),
				self.DREAMECM: self.getEcm("4A"),
				self.NDSECM: self.getEcm("09"),
				self.FTA: self.getFta(),
				self.EMU: self.getEmu(),
				self.CRD: self.getCrd(),
				self.NET: self.getNet(),
				self.BISCRYPT: self.getCrypt("26"),
				self.BISECM: self.getEcm("26"),
#				self.MGCAMD: self.getCam("Mgcamd"),
#				self.OSCAM: self.getOscam(),
#				self.CAMD3: self.getCam("Camd3"),
#				self.CCAM: self.getCam("Cccamd"),
#				self.MBOX: self.getCam("Mbox"),
#				self.GBOX: self.getCam("Gbox"),
#				self.INCUBUS: self.getCam("Incubus"),
#				self.WICARDD: self.getCam("Wicardd"),
				self.BULCRYPT: self.getCrypt("55"),
				self.BULECM: self.getEcm("55")
			}.get(self.type, False)
		else:
			value = False
		return value

	boolean = property(getBoolean)

	def getFta(self):
		ca = self.getCaidInfo()
		return ca == "No CA info available"

	def getecminfo(self):
		try:
			with open("/tmp/ecm.info") as fd:
				content = fd.read().split("\n")
		except OSError:
			content = []
		return content

	def getEmu(self):
		contentInfo = self.getecminfo()
		for line in contentInfo:
			if line.startswith("source:") or line.startswith("reader:"):
				using = self.parseEcmInfoLine(line)
				if using == "emu":
					return True
		return False

	def getCrd(self):
		contentInfo = self.getecminfo()
		for line in contentInfo:
			if line.startswith("from:"):
				using = self.parseEcmInfoLine(line)
				if using == "local":
					return True
			elif line.startswith("source:"):
				using = self.parseEcmInfoLine(line)
				if using == "card":
					return True
		return False

	def getNet(self):
		contentInfo = self.getecminfo()
		for line in contentInfo:
			if line.startswith("source:"):
				using = self.parseEcmInfoLine(line)
				using = using[:3]
				if using == "net":
					return True
			elif line.startswith("protocol:"):
				using = self.parseEcmInfoLine(line)
				if using == "newcamd":
					return True
		return False

	def getEcm(self, value):
		service = self.source.service
		if service:
			info = service and service.info()
			if info:
				contentInfo = self.getecminfo()
				for line in contentInfo:
					if line.startswith("caid:"):
						caid = self.parseEcmInfoLine(line)
						if "x" in caid:
							idx = caid.index("x")
							caid = caid[idx + 1:]
							if len(caid) == 3:
								caid = f"0{caid}"
							caid = caid[:2]
							caid = caid.upper()
							if caid == value:
								return True
					elif line.startswith("====="):
						caid = self.parseInfoLine(line)
						if "x" in caid:
							idx = caid.index("x")
							caid = caid[idx + 1:]
							caid = caid[:2]
							caid = caid.upper()
							if caid == value:
								return True
		return False

	def int2hex(self, integer):
		return f"{integer:04x}".upper()

	def getCrypt(self, value):
		service = self.source.service
		if service:
			info = service and service.info()
			if info:
				caids = info.getInfoObject(iServiceInformation.sCAIDs)
				if caids:
					for caid in caids:
						caid = self.int2hex(caid)
						caid = caid[:2]
						if caid == value:
							return True
		return False

	def getCaidInfo(self):
		service = self.source.service
		cainfo = "Caid:  "
		if service:
			info = service and service.info()
			if info:
				caids = info.getInfoObject(iServiceInformation.sCAIDs)
				if caids:
					for caid in caids:
						caid = self.int2hex(caid)
						cainfo += f"{caid}  "

					return cainfo
		return "No CA info available"

	def getCamName(self):
		self.poll_interval = 2000
		self.poll_enabled = True
		emu = ""
		cs = ""
		content = ""
		# contentInfo = content.split("\n")
		if content != "":
			emu = content
			if "\n" in emu:
				idx = emu.index("\n")
				emu = emu[:idx]
		try:
			content = open("/usr/bin/csactive").read()
		except OSError:
			content = ""
		if content != "":
			cs = content
			if "\n" in cs:
				idx = cs.index("\n")
				cs = cs[:idx]
		if cs != "" and emu != "":
			emu += f" + {cs}"
			return emu
		if cs == "" and emu != "":
			return emu
		if cs != "" and emu == "":
			return cs
		try:
			content = open("/tmp/cam.info").read()
		except OSError:
			content = ""
		# contentInfo = content.split("\n")
		if content != "":
			return content
		return "No emu or unknown"

	def getEcmCamInfo(self):
		service = self.source.service
		if service:
			info = service and service.info()
			if info and info.getInfoObject(iServiceInformation.sCAIDs):
				ecm_info = self.ecmfile()
				if ecm_info:
					caid = ecm_info.get("caid", "")
					caid = caid.lstrip("0x")
					caid = caid.upper()
					caid = caid.zfill(4)
					caid = f"CAID: {caid}"
					provider = ecm_info.get("Provider", "")
					provider = provider.lstrip("0x")
					provider = provider.upper()
					provider = provider.zfill(6)
					provider = f"Prov: {provider}"
					reader = ecm_info.get("reader", None)
					reader = f"{reader}"
					prov = ecm_info.get("prov", "")
					prov = prov.lstrip("0x")
					prov = prov.upper()
					prov = prov.zfill(6)
					prov = f"{prov}"
					from2 = ecm_info.get("from", None)
					from2 = f"{from2}"
					ecm_time = ecm_info.get("ecm time", None)
					if ecm_time:
						ecm_time = f"0.{ecm_time} s" if "msec" in ecm_time else f"{ecm_time} s"
					address = ecm_info.get("address", "")
					using = ecm_info.get("using", "")
					if using:
						if using == "emu":
							textvalue = f"(EMU) {caid} - {ecm_time}"
						elif using == "CCcam-s2s":
							textvalue = f"(NET) {caid} - {address} - {reader} - {ecm_time}"
						else:
							textvalue = f"{caid} - {address} - READER: {reader} - {ecm_time}"
					else:
						source = ecm_info.get("source", None)
						if source:
							textvalue = f"Source:EMU {caid}" if source == "emu" else f"{caid} - {source} - {ecm_time}"
						oscsource = ecm_info.get("reader", None)
						if oscsource:
							textvalue = f"Source:EMU {caid}" if oscsource == "emu" else f"{caid} - {from2} - {prov} - {reader} - {ecm_time}"
						wicarddsource = ecm_info.get("response time", None)
						if wicarddsource:
							textvalue = f"{caid} - {provider} - {wicarddsource}"
						decode = ecm_info.get("decode", None)
						if decode:
							textvalue = f"(EMU) {caid}" if decode == "Internal" else f"{caid} - {decode}"
		else:
			textvalue = "No info from emu or FTA"
		return textvalue

	def ecmfile(self):
		self.poll_interval = 2000
		self.poll_enabled = True
		ecm = None
		info = {}
		service = self.source.service
		if service:
			frontendInfo = service.frontendInfo()
			if frontendInfo:
				try:
					ecm = open(f"/tmp/ecm{frontendInfo.getAll(False).get('tuner_number')}.info", "rb").readlines()
				except Exception:
					try:
						ecm = open("/tmp/ecm.info", "rb").readlines()
					except OSError:
						pass
			if ecm:
				for line in ecm:
					x = line.lower().find("msec")
					if x != -1:
						info["ecm time"] = line[0:x + 4]
					else:
						item = line.split(":", 1)
						if len(item) > 1:
							info[item[0].strip().lower()] = item[1].strip()
						elif "caid" not in info:
							x = line.lower().find("caid")
							if x != -1:
								y = line.find(",")
								if y != -1:
									info["caid"] = line[x + 5:y]
		return info

	def parseEcmInfoLine(self, line):
		if ":" in line:
			idx = line.index(":")
			line = line[idx + 1:]
			line = line.replace("\n", "")
			while line.startswith(" "):
				line = line[1:]
			while line.endswith(" "):
				line = line[:-1]
			return line
		else:
			return ""

	def parseInfoLine(self, line):
		if "CaID" in line:
			idx = line.index("D")
			line = line[idx + 1:]
			line = line.replace("\n", "")
			while line.startswith(" "):
				line = line[1:]
			while line.endswith(" "):
				line = line[:-1]
			return line
		else:
			return ""

	def changed(self, what):
		Converter.changed(self, what)

	def getServiceNumber(self, name, ref):
		items = []
		if ref.startswith("1:0:2"):
			items = self.radio_list
		elif ref.startswith("1:0:1"):
			items = self.tv_list
		number = "---"
		if name in items:
			for idx in range(len(items)):
				if name == items[idx]:
					number = f"{idx + 1}"
					break
		return number

	def getLists(self):
		def getListFromRef(ref):
			serviceList = []
			serviceHandler = eServiceCenter.getInstance()
			services = serviceHandler.list(ref)
			bouquets = services and services.getContent("SN", True)
			for bouquet in bouquets:
				services = serviceHandler.list(eServiceReference(bouquet[0]))
				channels = services and services.getContent("SN", True)
				for channel in channels:
					if not channel[0].startswith("1:64:"):
						serviceList.append(channel[1].replace(" -*-", "").replace(" -*-", ""))
			return serviceList

		self.tv_list = getListFromRef(eServiceReference("1:7:1:0:0:0:0:0:0:0:(type == 1) || (type == 17) || (type == 195) || (type == 25) FROM BOUQUET \"bouquets.tv\" ORDER BY bouquet"))
		self.radio_list = getListFromRef(eServiceReference("1:7:2:0:0:0:0:0:0:0:(type == 2) FROM BOUQUET \"bouquets.radio\" ORDER BY bouquet"))

	def getTunerInfo(self, service):
		tunerinfo = ""
		feinfo = service and service.frontendInfo()
		if feinfo is not None:
			frontendData = feinfo and feinfo.getAll(True)
			if frontendData is not None:
				tunerType = frontendData.get("tuner_type")
				if tunerType in ("DVB-S", "DVB-C"):
					frequency = str(frontendData.get("frequency") / 1000) + " MHz"
					symbolrate = str(int(frontendData.get("symbol_rate", 0) / 1000))
					if tunerType == "DVB-S":
						orbitalPosition = frontendData.get("orbital_position", "None")
						orb = {
							3590: "Thor/Intelsat (1.0W)",
							3560: "Amos (4.0W)",
							3550: "Atlantic Bird (5.0W)",
							3530: "Nilesat/Atlantic Bird (7.0W)",
							3520: "Atlantic Bird (8.0W)",
							3475: "Atlantic Bird (12.5W)",
							3460: "Express (14.0W)",
							3450: "Telstar (15.0W)",
							3420: "Intelsat (18.0W)",
							3380: "Nss (22.0W)",
							3355: "Intelsat (24.5W)",
							3325: "Intelsat (27.5W)",
							3300: "Hispasat (30.0W)",
							3285: "Intelsat (31.5W)",
							3170: "Intelsat (43.0W)",
							3150: "Intelsat (45.0W)",
							3070: "Intelsat (53.0W)",
							3045: "Intelsat (55.5W)",
							3020: "Intelsat 9 (58.0W)",
							2990: "Amazonas (61.0W)",
							2900: "Star One (70.0W)",
							2880: "AMC 6 (72.0W)",
							2875: "Echostar 6 (72.7W)",
							2860: "Horizons (74.0W)",
							2810: "AMC5 (79.0W)",
							2780: "NIMIQ 4 (82.0W)",
							2690: "NIMIQ 1 (91.0W)",
							3592: "Thor/Intelsat (0.8W)",
							2985: "Echostar 3,12 (61.5W)",
							2830: "Echostar 8 (77.0W)",
							2630: "Galaxy 19 (97.0W)",
							2500: "Echostar 10,11 (110.0W)",
							2502: "DirectTV 5 (110.0W)",
							2410: "Echostar 7 Anik F3 (119.0W)",
							2391: "Galaxy 23 (121.0W)",
							2390: "Echostar 9 (121.0W)",
							2412: "DirectTV 7S (119.0W)",
							2310: "Galaxy 27 (129.0W)",
							2311: "Ciel 2 (129.0W)",
							2120: "Echostar 2 (148.0W)",
							1100: "BSat 1A,2A (110.0E)",
							1101: "N-Sat 110 (110.0E)",
							1131: "KoreaSat 5 (113.0E)",
							1440: "SuperBird 7,C2 (144.0E)",
							1006: "AsiaSat 2 (100.5E)",
							1030: "Express A2 (103.0E)",
							1056: "Asiasat 3S (105.5E)",
							1082: "NSS 11 (108.2E)",
							881: "ST1 (88.0E)",
							900: "Yamal 201 (90.0E)",
							917: "Mesat (91.5E)",
							950: "Insat 4B (95.0E)",
							951: "NSS 6 (95.0E)",
							765: "Telestar (76.5E)",
							785: "ThaiCom 5 (78.5E)",
							800: "Express (80.0E)",
							830: "Insat 4A (83.0E)",
							850: "Intelsat 709 (85.2E)",
							750: "Abs (75.0E)",
							720: "Intelsat (72.0E)",
							705: "Eutelsat W5 (70.5E)",
							685: "Intelsat (68.5E)",
							620: "Intelsat 902 (62.0E)",
							600: "Intelsat 904 (60.0E)",
							570: "Nss (57.0E)",
							530: "Express AM22 (53.0E)",
							480: "Eutelsat 2F2 (48.0E)",
							450: "Intelsat (45.0E)",
							420: "Turksat 2A (42.0E)",
							400: "Express AM1 (40.0E)",
							390: "Hellas Sat 2 (39.0E)",
							380: "Paksat 1 (38.0E)",
							360: "Eutelsat Sesat (36.0E)",
							335: "Astra 1M (33.5E)",
							330: "Eurobird 3 (33.0E)",
							328: "Galaxy 11 (32.8E)",
							315: "Astra 5A (31.5E)",
							310: "Turksat (31.0E)",
							305: "Arabsat (30.5E)",
							285: "Eurobird 1 (28.5E)",
							284: "Eurobird/Astra (28.2E)",
							282: "Eurobird/Astra (28.2E)",
							1220: "AsiaSat (122.0E)",
							1380: "Telstar 18 (138.0E)",
							260: "Badr 3/4 (26.0E)",
							255: "Eurobird 2 (25.5E)",
							235: "Astra 1E (23.5E)",
							215: "Eutelsat (21.5E)",
							216: "Eutelsat W6 (21.6E)",
							210: "AfriStar 1 (21.0E)",
							192: "Astra 1F (19.2E)",
							160: "Eutelsat W2 (16.0E)",
							130: "Hot Bird 6,7A,8 (13.0E)",
							100: "Eutelsat W1 (10.0E)",
							90: "Eurobird 9 (9.0E)",
							70: "Eutelsat W3A (7.0E)",
							50: "Sirius 4 (5.0E)",
							48: "Sirius 4 (4.8E)",
							30: "Telecom 2 (3.0E)"
						}.get(orbitalPosition, f"Unsupported SAT: {orbitalPosition}")
						if self.type == self.TUNERINFO:
							pol = {
								eDVBFrontendParametersSatellite.Polarisation_Horizontal: "H",
								eDVBFrontendParametersSatellite.Polarisation_Vertical: "V",
								eDVBFrontendParametersSatellite.Polarisation_CircularLeft: "CL",
								eDVBFrontendParametersSatellite.Polarisation_CircularRight: "CR"
							}[frontendData.get("polarization", eDVBFrontendParametersSatellite.Polarisation_Horizontal)]
						else:
							pol = {
								eDVBFrontendParametersSatellite.Polarisation_Horizontal: "Horizontal",
								eDVBFrontendParametersSatellite.Polarisation_Vertical: "Vertical",
								eDVBFrontendParametersSatellite.Polarisation_CircularLeft: "Circular Left",
								eDVBFrontendParametersSatellite.Polarisation_CircularRight: "Circular Right"
							}[frontendData.get("polarization", eDVBFrontendParametersSatellite.Polarisation_Horizontal)]
						fec = {
							eDVBFrontendParametersSatellite.FEC_None: "None",
							eDVBFrontendParametersSatellite.FEC_Auto: "Auto",
							eDVBFrontendParametersSatellite.FEC_1_2: "1/2",
							eDVBFrontendParametersSatellite.FEC_2_3: "2/3",
							eDVBFrontendParametersSatellite.FEC_3_4: "3/4",
							eDVBFrontendParametersSatellite.FEC_3_5: "3/5",
							eDVBFrontendParametersSatellite.FEC_4_5: "4/5",
							eDVBFrontendParametersSatellite.FEC_5_6: "5/6",
							eDVBFrontendParametersSatellite.FEC_6_7: "6/7",
							eDVBFrontendParametersSatellite.FEC_7_8: "7/8",
							eDVBFrontendParametersSatellite.FEC_8_9: "8/9",
							eDVBFrontendParametersSatellite.FEC_9_10: "9/10"
						}[frontendData.get("fec_inner", eDVBFrontendParametersSatellite.FEC_Auto)]
						if self.type == self.TUNERINFO:
							tunerinfo = f"{frequency}  {pol}  {fec}  {symbolrate}  {orb}"
						else:
							tunerinfo = f"Satellite: {orb}\nFrequency: {frequency}\nPolarization: {pol}\nSymbolrate: {symbolrate}\nFEC: {fec}"
					elif frontendData.get("tuner_type") == "DVB-C":
						fec = {
							eDVBFrontendParametersCable.FEC_None: "None",
							eDVBFrontendParametersCable.FEC_Auto: "Auto",
							eDVBFrontendParametersCable.FEC_1_2: "1/2",
							eDVBFrontendParametersCable.FEC_2_3: "2/3",
							eDVBFrontendParametersCable.FEC_3_4: "3/4",
							eDVBFrontendParametersCable.FEC_3_5: "3/5",
							eDVBFrontendParametersCable.FEC_4_5: "4/5",
							eDVBFrontendParametersCable.FEC_5_6: "5/6",
							eDVBFrontendParametersCable.FEC_7_8: "7/8",
							eDVBFrontendParametersCable.FEC_8_9: "8/9"
						}[frontendData.get("fec_inner", eDVBFrontendParametersCable.FEC_Auto)]
						if self.type == self.TUNERINFO:
							tunerinfo = f"{frequency}  {fec}  {symbolrate}"
						else:
							tunerinfo = f"Frequency: {frequency}\nSymbolrate: {symbolrate}\nFEC: {fec}"
					elif self.type == self.TUNERINFO:
						tunerinfo = f"{frequency}  {symbolrate}"
					else:
						tunerinfo = f"Frequency: {frequency}\nSymbolrate: {symbolrate}"
					return tunerinfo
			else:
				return ""


# This is for future enhancement
#	def getOscam(self):
#		self.poll_interval = 2000
#		self.poll_enabled = True
#		content = ""  # ??
#		contentInfo = content.split("\n")
#		for line in contentInfo:
#			if line.startswith("Oscam"):
#				return True
#		return False

#	def getCam(self, find):
#		self.poll_interval = 2000
#		self.poll_enabled = True
#		content = ""  # ??
#		contentInfo = content.split("\n")
#		for line in contentInfo:
#			if find in line:
#				return True
#		return False

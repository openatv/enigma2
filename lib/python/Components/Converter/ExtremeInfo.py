from enigma import eDVBFrontendParametersCable, eDVBFrontendParametersSatellite, eServiceCenter, eServiceReference, iServiceInformation

from Components.Converter.Converter import Converter
from Components.Converter.Poll import Poll
from Components.Element import cached
from ServiceReference import isRadioServiceReference


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
	# This is for future enhancement.
	# OSCAM = 33
	# CAMD3 = 34
	# CCAM = 35
	# MBOX = 36
	# GBOX = 37
	# INCUBUS = 38
	# WICARDD = 39

	SATELLITES = {
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
	}

	def __init__(self, tokens):
		Poll.__init__(self)
		Converter.__init__(self, tokens)
		self.list = []
		self.getLists()
		self.type = {
			"BetaCrypt": self.BETACRYPT,
			"BetaEcm": self.BETAECM,
			"BisCrypt": self.BISCRYPT,
			"BisEcm": self.BISECM,
			"BulCrypt": self.BULCRYPT,
			"BulEcm": self.BULECM,
			"CaidInfo": self.CAIDINFO,
			"CamName": self.CAMNAME,
			"ConaxCrypt": self.CONAXCRYPT,
			"ConaxEcm": self.CONAXECM,
			"Crd": self.CRD,
			"CrwCrypt": self.CRWCRYPT,
			"CrwEcm": self.CRWECM,
			"DreamCrypt": self.DREAMCRYPT,
			"DreamEcm": self.DREAMECM,
			"EcmInfo": self.ECMINFO,
			"Emu": self.EMU,
			"Fta": self.FTA,
			"IrdCrypt": self.IRDCRYPT,
			"IrdEcm": self.IRDECM,
			"Mgcamd": self.MGCAMD,
			"NagraCrypt": self.NAGRACRYPT,
			"NagraEcm": self.NAGRAECM,
			"NdsCrypt": self.NDSCRYPT,
			"NdsEcm": self.NDSECM,
			"Net": self.NET,
			"Number": self.NUMBER,
			"SecaCrypt": self.SECACRYPT,
			"SecaEcm": self.SECAECM,
			"TunerInfo": self.TUNERINFO,
			"TunerInfoBP": self.TUNERINFOBP,
			"ViaCrypt": self.VIACRYPT,
			"ViaEcm": self.VIAECM
			# This is for future enhancement.
			# "Camd3": self.CAMD3,
			# "Cccam": self.CCAM,
			# "Gbox": self.GBOX,
			# "Incubus": self.INCUBUS,
			# "Mbox": self.MBOX,
			# "Oscam": self.OSCAM,
			# "Wicardd": self.WICARDD
		}.get(tokens, self.TUNERINFO)

	def changed(self, what):
		Converter.changed(self, what)

	def ecmfile(self):
		self.poll_interval = 2000
		self.poll_enabled = True
		info = {}
		ecm = None
		service = self.source.service
		if service:
			frontendInfo = service.frontendInfo()
			if frontendInfo:
				try:
					with open(f"/tmp/ecm{frontendInfo.getAll(False).get('tuner_number')}.info") as fd:
						ecm = fd.readlines()
				except Exception:
					try:
						with open("/tmp/ecm.info") as fd:
							ecm = fd.readlines()
					except OSError:
						pass
			for line in ecm or ():
				index = line.lower().find("msec")
				if index != -1:
					info["ecm time"] = line[0:index + 4]
				else:
					item = line.split(":", 1)
					if len(item) > 1:
						info[item[0].strip().lower()] = item[1].strip()
					elif "caid" not in info:
						start = line.lower().find("caid")
						if start != -1:
							end = line.find(",")
							if end != -1:
								info["caid"] = line[start + 5:end]
		return info

	@cached
	def getBoolean(self):
		self.poll_interval = 500
		self.poll_enabled = True
		value = False
		service = self.source.service
		if service and service.info():
			cryptCaids = {
				self.BETACRYPT: "17",
				self.BISCRYPT: "26",
				self.BULCRYPT: "55",
				self.CONAXCRYPT: "0B",
				self.CRWCRYPT: "0D",
				self.DREAMCRYPT: "4A",
				self.IRDCRYPT: "06",
				self.NAGRACRYPT: "18",
				self.NDSCRYPT: "09",
				self.SECACRYPT: "01",
				self.VIACRYPT: "05"
			}
			ecmCaids = {
				self.BETAECM: "17",
				self.BISECM: "26",
				self.BULECM: "55",
				self.CONAXECM: "0B",
				self.CRWECM: "0D",
				self.DREAMECM: "4A",
				self.IRDECM: "06",
				self.NAGRAECM: "18",
				self.NDSECM: "09",
				self.SECAECM: "01",
				self.VIAECM: "05"
			}
			match self.type:
				case self.CRD:
					value = self.getCrd()
				case self.EMU:
					value = self.getEmu()
				case self.FTA:
					value = self.getFta()
				case self.NET:
					value = self.getNet()
				case _ if self.type in cryptCaids:
					value = self.getCrypt(cryptCaids[self.type])
				case _ if self.type in ecmCaids:
					value = self.getEcm(ecmCaids[self.type])
		return value

	boolean = property(getBoolean)

	def getCaidInfo(self):
		result = "No CA info available"
		service = self.source.service
		info = service and service.info()
		caids = info and info.getInfoObject(iServiceInformation.sCAIDs)
		if caids:
			result = f"Caid:  {''.join(f'{self.int2hex(x)}  ' for x in caids)}"
		return result

	def getCamName(self):
		self.poll_interval = 2000
		self.poll_enabled = True
		result = ""
		try:
			with open("/usr/bin/csactive") as fd:
				result = fd.read().split("\n")[0]
		except OSError:
			pass
		if not result:
			try:
				with open("/tmp/cam.info") as fd:
					result = fd.read()
			except OSError:
				pass
		return result or "No emu or unknown"

	def getCrd(self):
		return any((x.startswith("from:") and self.parseEcmInfoLine(x) == "local") or (x.startswith("source:") and self.parseEcmInfoLine(x) == "card") for x in self.getecminfo())

	def getCrypt(self, value):
		service = self.source.service
		info = service and service.info()
		caids = info and info.getInfoObject(iServiceInformation.sCAIDs)
		return bool(caids) and any(self.int2hex(x)[:2] == value for x in caids)

	def getEcm(self, value):
		result = False
		service = self.source.service
		info = service and service.info()
		if info:
			for line in self.getecminfo():
				if line.startswith("caid:"):
					caid = self.parseEcmInfoLine(line)
					padding = True
				elif line.startswith("====="):
					caid = self.parseInfoLine(line)
					padding = False
				else:
					caid = ""
				if "x" in caid:
					caid = caid[caid.index("x") + 1:]
					if padding and len(caid) == 3:
						caid = f"0{caid}"
					if caid[:2].upper() == value:
						result = True
						break
		return result

	def getEcmCamInfo(self):
		text = ""
		service = self.source.service
		if service:
			info = service.info()
			if info and info.getInfoObject(iServiceInformation.sCAIDs):
				ecmInfo = self.ecmfile()
				if ecmInfo:
					caid = f"CAID: {ecmInfo.get('caid', '').lstrip('0x').upper().zfill(4)}"
					provider = f"Prov: {ecmInfo.get('Provider', '').lstrip('0x').upper().zfill(6)}"
					reader = f"{ecmInfo.get('reader')}"
					prov = ecmInfo.get("prov", "").lstrip("0x").upper().zfill(6)
					fromSource = f"{ecmInfo.get('from')}"
					ecmTime = ecmInfo.get("ecm time")
					if ecmTime:
						ecmTime = f"0.{ecmTime} s" if "msec" in ecmTime else f"{ecmTime} s"
					address = ecmInfo.get("address", "")
					using = ecmInfo.get("using", "")
					if using:
						match using:
							case "CCcam-s2s":
								text = f"(NET) {caid} - {address} - {reader} - {ecmTime}"
							case "emu":
								text = f"(EMU) {caid} - {ecmTime}"
							case _:
								text = f"{caid} - {address} - READER: {reader} - {ecmTime}"
					else:
						source = ecmInfo.get("source")
						if source:
							text = f"Source:EMU {caid}" if source == "emu" else f"{caid} - {source} - {ecmTime}"
						oscSource = ecmInfo.get("reader")
						if oscSource:
							text = f"Source:EMU {caid}" if oscSource == "emu" else f"{caid} - {fromSource} - {prov} - {reader} - {ecmTime}"
						wicarddSource = ecmInfo.get("response time")
						if wicarddSource:
							text = f"{caid} - {provider} - {wicarddSource}"
						decode = ecmInfo.get("decode")
						if decode:
							text = f"(EMU) {caid}" if decode == "Internal" else f"{caid} - {decode}"
		else:
			text = "No info from emu or FTA"
		return text

	def getecminfo(self):
		try:
			with open("/tmp/ecm.info") as fd:
				content = fd.read().split("\n")
		except OSError:
			content = []
		return content

	def getEmu(self):
		return any(x.startswith(("source:", "reader:")) and self.parseEcmInfoLine(x) == "emu" for x in self.getecminfo())

	def getFta(self):
		return self.getCaidInfo() == "No CA info available"

	def getLists(self):
		def getListFromRef(ref):
			serviceList = []
			serviceHandler = eServiceCenter.getInstance()
			services = serviceHandler.list(ref)
			bouquets = services and services.getContent("SN", True)
			for bouquet in bouquets:
				services = serviceHandler.list(eServiceReference(bouquet[0]))
				channels = services and services.getContent("SN", True)
				serviceList.extend(x[1].replace(" -*-", "").replace(" -*-", "") for x in channels if not x[0].startswith("1:64:"))
			return serviceList

		self.tv_list = getListFromRef(eServiceReference("1:7:1:0:0:0:0:0:0:0:(type == 1) || (type == 17) || (type == 195) || (type == 25) FROM BOUQUET \"bouquets.tv\" ORDER BY bouquet"))
		self.radio_list = getListFromRef(eServiceReference("1:7:2:0:0:0:0:0:0:0:(type == 2) FROM BOUQUET \"bouquets.radio\" ORDER BY bouquet"))

	def getNet(self):
		return any((x.startswith("source:") and self.parseEcmInfoLine(x).startswith("net")) or (x.startswith("protocol:") and self.parseEcmInfoLine(x) == "newcamd") for x in self.getecminfo())

	def getServiceNumber(self, name, ref):
		items = []
		if isRadioServiceReference(ref):
			items = self.radio_list
		elif ref.startswith("1:0:1"):
			items = self.tv_list
		return f"{items.index(name) + 1}" if name in items else "---"

	@cached
	def getText(self):
		text = ""
		service = self.source.service
		info = service and service.info()
		if info:
			match self.type:
				case self.CAIDINFO:
					text = self.getCaidInfo()
				case self.CAMNAME:
					text = self.getCamName()
				case self.ECMINFO:
					text = self.getEcmCamInfo()
				case self.NUMBER:
					name = info.getName().replace(" -*-", "").replace(" -*-", "")
					text = self.getServiceNumber(name, info.getInfoString(iServiceInformation.sServiceref))
				case self.TUNERINFO | self.TUNERINFOBP:
					text = self.getTunerInfo(service)
		return text

	text = property(getText)

	def getTunerInfo(self, service):
		tunerInfo = ""
		frontendInfo = service and service.frontendInfo()
		frontendData = frontendInfo and frontendInfo.getAll(True)
		if frontendData:
			tunerType = frontendData.get("tuner_type")
			if tunerType in ("DVB-S", "DVB-C"):
				frequency = f"{frontendData.get('frequency') / 1000} MHz"
				symbolRate = str(int(frontendData.get("symbol_rate", 0) / 1000))
				if tunerType == "DVB-S":
					orbitalPosition = frontendData.get("orbital_position", "None")
					satellite = self.SATELLITES.get(orbitalPosition, f"Unsupported SAT: {orbitalPosition}")
					if self.type == self.TUNERINFO:
						polarization = {
							eDVBFrontendParametersSatellite.Polarisation_Horizontal: "H",
							eDVBFrontendParametersSatellite.Polarisation_Vertical: "V",
							eDVBFrontendParametersSatellite.Polarisation_CircularLeft: "CL",
							eDVBFrontendParametersSatellite.Polarisation_CircularRight: "CR"
						}[frontendData.get("polarization", eDVBFrontendParametersSatellite.Polarisation_Horizontal)]
					else:
						polarization = {
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
						tunerInfo = f"{frequency}  {polarization}  {fec}  {symbolRate}  {satellite}"
					else:
						tunerInfo = f"Satellite: {satellite}\nFrequency: {frequency}\nPolarization: {polarization}\nSymbolrate: {symbolRate}\nFEC: {fec}"
				else:
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
						tunerInfo = f"{frequency}  {fec}  {symbolRate}"
					else:
						tunerInfo = f"Frequency: {frequency}\nSymbolrate: {symbolRate}\nFEC: {fec}"
		return tunerInfo

	def int2hex(self, integer):
		return f"{integer:04x}".upper()

	def parseEcmInfoLine(self, line):
		return line.split(":", 1)[1].replace("\n", "").strip(" ") if ":" in line else ""

	def parseInfoLine(self, line):
		return line[line.index("D") + 1:].replace("\n", "").strip(" ") if "CaID" in line else ""

	# This is for future enhancement.
	# def getCam(self, find):
	# 	self.poll_interval = 2000
	# 	self.poll_enabled = True
	# 	content = ""  # ??
	# 	return any(find in x for x in content.split("\n"))

	# def getOscam(self):
	# 	self.poll_interval = 2000
	# 	self.poll_enabled = True
	# 	content = ""  # ??
	# 	return any(x.startswith("Oscam") for x in content.split("\n"))

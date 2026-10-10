from enigma import eAVControl, iPlayableService, iServiceInformation

from skin import parameters, parseColor
from Components.Converter.Converter import Converter
from Components.Converter.Poll import Poll
from Components.Element import cached
from Components.config import config
from Tools.GetEcmInfo import GetEcmInfo, getCaidData
from Tools.Transponder import ConvertToHumanReadable

CODEC_NAMES = {  # Stream type to codec mapping.
	-1: "N/A",
	0: "MPEG2",
	1: "AVC",
	2: "H263",
	3: "VC1",
	4: "MPEG4-VC",
	5: "VC1-SM",
	6: "MPEG1",
	7: "HEVC",
	8: "VP8",
	9: "VP9",
	10: "XVID",
	11: "N/A 11",
	12: "N/A 12",
	13: "DIVX 3.11",
	14: "DIVX 4",
	15: "DIVX 5",
	16: "AVS",
	17: "N/A 17",
	18: "VP6",
	19: "N/A 19",
	20: "N/A 20",
	21: "SPARK"
}
codec_data = CODEC_NAMES  # Legacy name currently only used in Information.py.


class PliExtraInfo(Converter, Poll):
	satelliteNames = {
		30: "Rascom/Eutelsat 3E",
		48: "SES 5",
		70: "Eutelsat 7E",
		90: "Eutelsat 9E",
		100: "Eutelsat 10E",
		130: "Hot Bird",
		160: "Eutelsat 16E",
		192: "Astra 1KR/1LMNP",
		200: "Arabsat 20E",
		216: "Eutelsat 21.5E",
		235: "Astra 3",
		255: "Eutelsat 25.5E",
		260: "Badr 4/5/6",
		282: "Astra 2E/2F/2G",
		305: "Arabsat 30.5E",
		315: "Astra 5",
		330: "Eutelsat 33E",
		360: "Eutelsat 36E",
		380: "Paksat",
		390: "Hellas Sat",
		400: "Express 40E",
		420: "Turksat",
		450: "Intelsat 45E",
		480: "Afghansat",
		490: "Yamal 49E",
		530: "Express 53E",
		570: "NSS 57E",
		600: "Intelsat 60E",
		620: "Intelsat 62E",
		685: "Intelsat 68.5E",
		705: "Eutelsat 70.5E",
		720: "Intelsat 72E",
		750: "ABS",
		765: "Apstar",
		785: "ThaiCom",
		800: "Express 80E",
		830: "Insat",
		851: "Intelsat/Horizons",
		880: "ST2",
		900: "Yamal 90E",
		915: "Mesat",
		950: "NSS/SES 95E",
		1005: "AsiaSat 100E",
		1030: "Express 103E",
		1055: "Asiasat 105E",
		1082: "NSS/SES 108E",
		1100: "BSat/NSAT",
		1105: "ChinaSat",
		1130: "KoreaSat",
		1222: "AsiaSat 122E",
		1380: "Telstar 18",
		1440: "SuperBird",
		2310: "Ciel",
		2390: "Echostar/Galaxy 121W",
		2410: "Echostar/DirectTV 119W",
		2500: "Echostar/DirectTV 110W",
		2630: "Galaxy 97W",
		2690: "NIMIQ 91W",
		2780: "NIMIQ 82W",
		2830: "Echostar/QuetzSat",
		2880: "AMC 72W",
		2900: "Star One",
		2985: "Echostar 61.5W",
		2990: "Amazonas",
		3020: "Intelsat 58W",
		3045: "Intelsat 55.5W",
		3070: "Intelsat 53W",
		3100: "Intelsat 50W",
		3150: "Intelsat 45W",
		3169: "Intelsat 43.1W",
		3195: "SES 40.5W",
		3225: "NSS/Telstar 37W",
		3255: "Intelsat 34.5W",
		3285: "Intelsat 31.5W",
		3300: "Hispasat",
		3325: "Intelsat 27.5W",
		3355: "Intelsat 24.5W",
		3380: "SES 22W",
		3400: "NSS 20W",
		3420: "Intelsat 18W",
		3450: "Telstar 15W",
		3460: "Express 14W",
		3475: "Eutelsat 12.5W",
		3490: "Express 11W",
		3520: "Eutelsat 8W",
		3530: "Nilesat/Eutelsat 7W",
		3550: "Eutelsat 5W",
		3560: "Amos",
		3592: "Thor/Intelsat"
	}
	caTable = (
		("CryptoCaidSecaAvailable", "S", False),
		("CryptoCaidViaAvailable", "V", False),
		("CryptoCaidIrdetoAvailable", "I", False),
		("CryptoCaidNDSAvailable", "Nd", False),
		("CryptoCaidConaxAvailable", "Co", False),
		("CryptoCaidCryptoWAvailable", "Cw", False),
		("CryptoCaidPowerVUAvailable", "P", False),
		("CryptoCaidBetaAvailable", "B", False),
		("CryptoCaidNagraAvailable", "N", False),
		("CryptoCaidBissAvailable", "Bi", False),
		("CryptoCaidDre3Available", "D3", False),
		("CryptoCaidDreAvailable", "D", False),
		("CryptoCaidBulCrypt1Available", "B1", False),
		("CryptoCaidBulCrypt2Available", "B2", False),
		("CryptoCaidTandbergAvailable", "T", False),
		("CryptoCaidSecaSelected", "S", True),
		("CryptoCaidViaSelected", "V", True),
		("CryptoCaidIrdetoSelected", "I", True),
		("CryptoCaidNDSSelected", "Nd", True),
		("CryptoCaidConaxSelected", "Co", True),
		("CryptoCaidCryptoWSelected", "Cw", True),
		("CryptoCaidPowerVUSelected", "P", True),
		("CryptoCaidBetaSelected", "B", True),
		("CryptoCaidNagraSelected", "N", True),
		("CryptoCaidBissSelected", "Bi", True),
		("CryptoCaidDre3Selected", "D3", True),
		("CryptoCaidDreSelected", "D", True),
		("CryptoCaidBulCrypt1Selected", "B1", True),
		("CryptoCaidBulCrypt2Selected", "B2", True),
		("CryptoCaidTandbergSelected", "T", True)
	)
	cryptoData = {
		"CryptoSeca": ("0x100", "0x1ff", "S"),
		"CryptoVia": ("0x500", "0x5ff", "V"),
		"CryptoIrdeto": ("0x600", "0x6ff", "I"),
		"CryptoNDS": ("0x900", "0x9ff", "NDS"),
		"CryptoConax": ("0xb00", "0xbff", "CO"),
		"CryptoCryptoW": ("0xd00", "0xdff", "CW"),
		"CryptoBeta": ("0x1700", "0x17ff", "B"),
		"CryptoNagra": ("0x1800", "0x18ff", "N"),
		"CryptoBiss": ("0x2600", "0x26ff", "BI"),
		"CryptoDre": ("0x4ae0", "0x4ae1", "DC"),
		"CryptoTandberg": ("0x1010", "0x1010", "T"),
		"CryptoPowerVU": ("0xe00", "0xeff", "P")
	}

	def __init__(self, tokens):
		Converter.__init__(self, tokens)
		Poll.__init__(self)
		self.type = tokens
		self.cryptoColors = parameters.get("PliExtraInfoCryptoColors", ("#004C7D3F", "#009F9F9F", "#00EEEE00", "#00FFFFFF"))
		self.cryptoColors = [rf"\c{parseColor(x).argb():08X}" for x in self.cryptoColors]
		self.infoColors = parameters.get("PliExtraInfoColors", ("#0000FF00", "#00FFFF00", "#007F7F7F", "#00FFFFFF"))  # "Found", "Not found", "Available", "Default" colors.
		self.infoColors = [rf"\c{parseColor(x).argb():08X}" for x in self.infoColors]
		self.poll_interval = 1000  # This is a shared variable!
		self.poll_enabled = True  # This is a shared variable!
		self.ecmData = GetEcmInfo()
		self.feRaw = None
		self.feData = None
		self.feDataUpdate = None

	def changed(self, what):
		if what[0] == self.CHANGED_SPECIFIC:
			self.feDataUpdate = False
			if what[1] == iPlayableService.evNewProgramInfo:
				self.feDataUpdate = True
			if what[1] == iPlayableService.evEnd:
				self.feRaw = None
				self.feData = None
			Converter.changed(self, what)
		elif what[0] == self.CHANGED_POLL and self.feDataUpdate is not None:
			self.feDataUpdate = False
			Converter.changed(self, what)

	def createChannelNumber(self, feData, feRaw):
		return "DVB-T" in feRaw.get("tuner_type") and feData.get("channel") or ""

	def createCrypto(self, info, start, end, crypto):
		availableCAIDs = info.getInfoObject(iServiceInformation.sCAIDs)
		if int(start, 16) <= int(self.currentCAID, 16) <= int(end, 16):
			color = self.cryptoColors[0]
		else:
			color = self.cryptoColors[1]
			try:
				for caid in availableCAIDs:
					if int(start, 16) <= caid <= int(end, 16):
						color = self.cryptoColors[2]
			except Exception:
				pass
		return f"{color}{crypto}{self.cryptoColors[3]}"

	def createCryptoBar(self, info):
		data = []
		availableCAIDs = info.getInfoObject(iServiceInformation.sCAIDs)
		for caidData in getCaidData():
			if int(caidData[0], 16) <= int(self.currentCAID, 16) <= int(caidData[1], 16):
				color = self.infoColors[0]
			else:
				color = self.infoColors[2]
				try:
					for caid in availableCAIDs:
						if int(caidData[0], 16) <= caid <= int(caidData[1], 16):
							color = self.infoColors[1]
				except Exception:
					pass
			if color != self.infoColors[2] or caidData[5]:
				data.append(f"{color}{caidData[3]}")
		return f"{' '.join(data)}{self.infoColors[3]}"

	def createCryptoNameCaid(self, info):
		caidName = "FTA"
		if int(self.currentCAID, 16):
			try:
				for caidData in getCaidData():
					if int(caidData[0], 16) <= int(self.currentCAID, 16) <= int(caidData[1], 16):
						caidName = caidData[2]
						break
				caidName = f"{caidName}:{int(self.currentCAID, 16):04X}"
			except Exception:
				caidName = ""
		return caidName

	def createCryptoSpecial(self, info):
		caidName = "FTA"
		try:
			for caidData in getCaidData():
				if int(caidData[0], 16) <= int(self.currentCAID, 16) <= int(caidData[1], 16):
					caidName = caidData[2]
					break
			caidName = f"{caidName}:{int(self.currentCAID, 16):04X}:{int(self.currentProvID, 16):04X}:{info.getInfo(iServiceInformation.sSID):04X}"
		except Exception:
			caidName = ""
		return caidName

	def createFEC(self, feData, feRaw):
		if "DVB-T" in feRaw.get("tuner_type"):
			codeRateLP = feData.get("code_rate_lp")
			codeRateHP = feData.get("code_rate_hp")
			guardInterval = feData.get("guard_interval")
			fec = f"{codeRateLP}-{codeRateHP}-{guardInterval}" if codeRateLP and codeRateHP and guardInterval else ""
		else:
			fec = feData.get("fec_inner", "")
		return fec

	def createFrequency(self, feData):
		return str(feData.get("frequency", ""))

	def createMisPls(self, feData):
		data = []
		if feData.get("is_id") and feData.get("is_id") > -1:
			data.append(f"MIS {feData.get('is_id')}")
		if feData.get("pls_code") and feData.get("pls_code") > 0:
			data.append(f"{feData.get('pls_mode')} {feData.get('pls_code')}")
		if feData.get("t2mi_plp_id") and feData.get("t2mi_plp_id") > -1:
			data.append(f"T2MI {feData.get('t2mi_plp_id')} PID {feData.get('t2mi_pid')}")
		return "  ".join(data)

	def createModulation(self, feData):
		return feData.get("constellation" if "DVB-T" in feData.get("tuner_type") else "modulation", "")

	def createOrbPos(self, feRaw):
		orbPos = feRaw.get("orbital_position")
		if orbPos:
			if orbPos > 1800:
				orbPos = f"{float(3600 - orbPos) / 10.0}\u00B0{_('W')}"
			elif orbPos > 0:
				orbPos = f"{float(orbPos) / 10.0}\u00B0{_('E')}"
		return orbPos or ""

	def createOrbPosOrTunerSystem(self, feData, feRaw):
		orbPos = self.createOrbPos(feRaw)
		return orbPos if orbPos else self.createTunerSystem(feData)

	def createPIDInfo(self, info):
		originalNetworkID, transportStreamID, serviceIDPID, videoPID, audioPID, programClockReferencePID = (max(info.getInfo(x), 0) for x in (iServiceInformation.sONID, iServiceInformation.sTSID, iServiceInformation.sSID, iServiceInformation.sVideoPID, iServiceInformation.sAudioPID, iServiceInformation.sPCRPID))
		return f"{originalNetworkID}-{transportStreamID}:{serviceIDPID:05d}:{videoPID:04d}:{audioPID:04d}:{programClockReferencePID:04d}"

	def createPolarization(self, feData):
		return feData.get("polarization_abbreviation") or ""

	def createProviderName(self, info):
		return info.getInfoString(iServiceInformation.sProvider)

	def createResolution(self, info):
		avControl = eAVControl.getInstance()
		gamma = {
			0: "SDR",
			1: "HDR",
			2: "HDR10",
			3: "HLG"
		}.get(info.getInfo(iServiceInformation.sGamma), "")
		gamma = f"  {gamma}" if gamma else ""
		return f"{avControl.getResolutionX(0)}x{avControl.getResolutionY(0)}{'p' if avControl.getProgressive() else 'i'}{(avControl.getFrameRate(0) + 500) // 1000}{gamma}"

	def createServiceRef(self, info):
		return info.getInfoString(iServiceInformation.sServiceref)

	def createSymbolRate(self, feData, feRaw):
		return str(feData.get("bandwidth" if "DVB-T" in feRaw.get("tuner_type") else "symbol_rate", ""))

	def createTransponderInfo(self, feData, feRaw, info):
		if feRaw:
			data = [self.createTunerSystem(feData)]
			if "DVB-T" in feRaw.get("tuner_type"):
				data.append(self.createChannelNumber(feData, feRaw))
			data += [
				self.createFrequency(feData),
				self.createPolarization(feData),
				self.createSymbolRate(feData, feRaw),
				self.createFEC(feData, feRaw),
				self.createModulation(feData),
				self.createOrbPos(feRaw),
				self.createMisPls(feData)
			]
			result = "  ".join(data)
		else:
			refstr = info.getInfoString(iServiceInformation.sServiceref)
			result = refstr.split(":")[10].replace("%3a", ":").replace("%3A", ":") if "%3a//" in refstr.lower() else ""
		return result

	def createTransponderName(self, feRaw):
		orbPos = feRaw.get("orbital_position")
		if orbPos:
			frequency = feRaw.get("frequency")
			if frequency and frequency < 10700000:  # C-band.
				if orbPos > 1800:
					orbPos += 1
				else:
					orbPos -= 1
			if orbPos in self.satelliteNames:
				orbPos = self.satelliteNames[orbPos]
			elif orbPos > 1800:
				orbPos = f"{float(3600 - orbPos) / 10.0}\u00B0{_('W')}"
			else:
				orbPos = f"{float(orbPos) / 10.0}\u00B0{_('E')}"
		return orbPos or ""

	def createTunerSystem(self, feData):
		return feData.get("system") or ""

	def createTunerType(self, feRaw):
		return feRaw.get("tuner_type") or ""

	def createVideoCodec(self, info):
		return CODEC_NAMES.get(info.getInfo(iServiceInformation.sVideoType), _("N/A"))

	@cached
	def getBool(self):
		result = False
		service = self.source.service
		info = service and service.info()
		if info:
			requestCAID = None
			requestSelected = None
			for item in self.caTable:
				if item[0] == self.type:
					requestCAID = item[1]
					requestSelected = item[2]
					break
			if requestCAID and info.getInfo(iServiceInformation.sIsCrypted) == 1:
				data = self.ecmData.getEcmData()
				if data:
					currentCAID = data[1]
					availableCAIDs = info.getInfoObject(iServiceInformation.sCAIDs)
					for caidData in getCaidData():
						if caidData[3] == requestCAID:
							if requestSelected:
								if int(caidData[0], 16) <= int(currentCAID, 16) <= int(caidData[1], 16):
									result = True
									break
							else:  # Request available.
								try:
									for caid in availableCAIDs:
										if int(caidData[0], 16) <= caid <= int(caidData[1], 16):
											result = True
											break
								except Exception:
									pass
							if result:
								break
		return result

	boolean = property(getBool)

	def getCryptoInfo(self, info):
		if info.getInfo(iServiceInformation.sIsCrypted) == 1:
			data = self.ecmData.getEcmData()
			self.currentSource = data[0]
			self.currentCAID = data[1]
			self.currentProvID = data[2]
		else:
			self.currentSource = ""
			self.currentCAID = "0"
			self.currentProvID = "0"

	@cached
	def getText(self):
		text = ""
		service = self.source.service
		info = service and service.info()
		if info:
			showCryptoInfo = config.usage.show_cryptoinfo.value > 0
			match self.type:
				case "CryptoBar" | "CryptoNameCaid" | "CryptoSpecial":
					if showCryptoInfo:
						self.getCryptoInfo(info)
						match self.type:
							case "CryptoBar":
								text = self.createCryptoBar(info)
							case "CryptoNameCaid":
								text = self.createCryptoNameCaid(info)
							case "CryptoSpecial":
								text = self.createCryptoSpecial(info)
				case "CryptoInfo":
					self.getCryptoInfo(info)
					if showCryptoInfo:
						text = "  ".join((self.createCryptoBar(info), self.createCryptoSpecial(info)))
					else:
						text = "  ".join((self.createCryptoBar(info), self.currentSource, self.createCryptoSpecial(info)))
				case "ResolutionString":
					text = self.createResolution(info)
				case "VideoCodec":
					text = self.createVideoCodec(info)
				case _ if self.type in self.cryptoData:
					if showCryptoInfo:
						self.getCryptoInfo(info)
						text = self.createCrypto(info, *self.cryptoData[self.type])
				case _:
					if self.feDataUpdate:
						feInfo = service.frontendInfo()
						if feInfo:
							self.feRaw = feInfo.getAll(config.usage.infobar_frontend_source.value == "settings")
							if self.feRaw:
								self.feData = ConvertToHumanReadable(self.feRaw)
					feRaw = self.feRaw
					if feRaw:
						feData = self.feData
					else:
						feRaw = info.getInfoObject(iServiceInformation.sTransponderData)
						feData = ConvertToHumanReadable(feRaw) if feRaw else None
					if feRaw:
						match self.type:
							case "All":
								self.getCryptoInfo(info)
								lines = ["  ".join((self.createProviderName(info), self.createTransponderInfo(feData, feRaw, info), self.createTransponderName(feRaw)))]
								if showCryptoInfo:
									lines.append("  ".join((self.createCryptoBar(info), self.createCryptoSpecial(info))))
									lines.append("  ".join((self.createPIDInfo(info), self.createVideoCodec(info), self.createResolution(info))))
								else:
									lines.append("  ".join((self.createCryptoBar(info), self.currentSource)))
									lines.append("  ".join((self.createCryptoSpecial(info), self.createVideoCodec(info), self.createResolution(info))))
								text = "\n".join(lines)
							case "OrbitalPosition":
								text = self.createOrbPos(feRaw)
							case "OrbitalPositionOrTunerSystem":
								text = self.createOrbPosOrTunerSystem(feData, feRaw)
							case "PIDInfo":
								text = self.createPIDInfo(info)
							case "ServiceInfo":
								text = "  ".join((
									self.createProviderName(info),
									self.createTunerSystem(feData),
									self.createFrequency(feRaw),
									self.createPolarization(feData),
									self.createSymbolRate(feData, feRaw),
									self.createFEC(feData, feRaw),
									self.createModulation(feData),
									self.createOrbPos(feRaw),
									self.createTransponderName(feRaw),
									self.createVideoCodec(info),
									self.createResolution(info)
								))
							case "ServiceRef":
								text = self.createServiceRef(info)
							case "TerrestrialChannelNumber":
								text = self.createChannelNumber(feData, feRaw)
							case "TransponderFEC":
								text = self.createFEC(feData, feRaw)
							case "TransponderFrequency":
								text = self.createFrequency(feRaw)
							case "TransponderInfo":
								text = self.createTransponderInfo(feData, feRaw, info)
							case "TransponderInfo2line":
								line1 = "  ".join((self.createProviderName(info), self.createTunerSystem(feData), self.createTransponderName(feRaw)))
								line2 = "  ".join((self.createFrequency(feData), self.createPolarization(feData), self.createSymbolRate(feData, feRaw), f"{self.createModulation(feData)}-{self.createFEC(feData, feRaw)}"))
								text = f"{line1}\n{line2}"
							case "TransponderModulation":
								text = self.createModulation(feData)
							case "TransponderPolarization":
								text = self.createPolarization(feData)
							case "TransponderSymbolRate":
								text = self.createSymbolRate(feData, feRaw)
							case "TunerSystem":
								text = self.createTunerSystem(feData)
							case "TunerType":
								text = self.createTunerType(feRaw)
							case _:
								text = _("Invalid type")
		return text

	text = property(getText)

#
# Extended ServiceName Converter for Enigma2 Dreamboxes (ServiceName2.py)
# Coded by vlamo (c) 2011
#
# Version: 0.4 (03.06.2011 18:40)
# Version: 0.5 (08.09.2012) add Alternative numbering mode support - Dmitry73 & 2boom
# Version: 0.6 (19.10.2012) add stream mapping
# Version: 0.7 (19.09.2013) add iptv info - nikolasi & 2boom
# Version: 0.8 (29.10.2013) add correct output channelnumner - Dmitry73
# Version: 0.9 (18.11.2013) code fix and optimization - Taapat & nikolasi
# Version: 1.0 (04.12.2013) code fix and optimization - Dmitry73
# Version: 1.1 (06-17.12.2013) small cosmetic fix - 2boom
# Version: 1.2 (25.12.2013) small iptv fix - MegAndretH
# Version: 1.3 (27.01.2014) small iptv fix - 2boom
# Version: 1.4 (30.06.2014) fix iptv reference - 2boom
# Version: 1.5 (04.07.2014) fix iptv reference cosmetic - 2boom
# Support: http://dream.altmaster.net/ & http://gisclub.tv

from enigma import eServiceCenter, eServiceReference, eTimer, getBestPlayableServiceReference, iPlayableService, iPlayableServicePtr, iServiceInformation

from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.NimManager import nimmanager
from Components.config import config
import NavigationInstance
try:
	from Components.Renderer.ChannelNumber import ChannelNumberClasses
	correctChannelNumber = True
except ImportError:
	correctChannelNumber = False


class ServiceName2(Converter):
	NAME = 0
	NUMBER = 1
	BOUQUET = 2
	PROVIDER = 3
	REFERENCE = 4
	ORBPOS = 5
	TPRDATA = 6
	SATELLITE = 7
	ALLREF = 8
	FORMAT = 9

	def __init__(self, tokens):
		Converter.__init__(self, tokens)
		self.type = {
			"AllRef": self.ALLREF,
			"Bouquet": self.BOUQUET,
			"Name": self.NAME,
			"Number": self.NUMBER,
			"OrbitalPos": self.ORBPOS,
			"Provider": self.PROVIDER,
			"Reference": self.REFERENCE,
			"Satellite": self.SATELLITE,
			"TpansponderInfo": self.TPRDATA
		}.get(tokens, self.FORMAT if tokens else self.NAME)
		if self.type == self.FORMAT:
			self.sfmt = tokens[:]
		try:
			if (self.type == self.NUMBER or (self.type == self.FORMAT and "%n" in self.sfmt)) and correctChannelNumber:
				ChannelNumberClasses.append(self.forceChanged)
		except Exception:
			pass
		self.refstr = self.isStream = self.ref = self.info = self.what = self.tpdata = None
		self.Timer = eTimer()
		self.Timer.callback.append(self.neededChange)
		self.IPTVcontrol = self.isAdditionalService(group=False)
		self.AlternativeControl = self.isAdditionalService(group=True)

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] == iPlayableService.evStart:
			self.refstr = self.isStream = self.ref = self.info = self.tpdata = None
			if self.type in (self.NUMBER, self.BOUQUET) or (self.type == self.FORMAT and ("%n" in self.sfmt or "%B" in self.sfmt)):
				self.what = what
				self.Timer.start(200, True)
			else:
				Converter.changed(self, what)

	def forceChanged(self, what):
		if what is True:
			self.refstr = self.isStream = self.ref = self.info = self.tpdata = None
			Converter.changed(self, (self.CHANGED_ALL,))
			self.what = None

	def getIPTVProvider(self, refstr):
		providers = (  # The order is important, the first match wins.
			(("tvshka",), "SCHURA"),
			(("udp/239.0.1",), "Lanet"),
			(("3a7777",), "IPTVNTV"),
			(("KartinaTV",), "KartinaTV"),
			(("Megaimpuls",), "MEGAIMPULSTV"),
			(("Newrus",), "NEWRUSTV"),
			(("Sovok",), "SOVOKTV"),
			(("Rodnoe",), "RODNOETV"),
			(("238.1.1.181%3a1234",), "VIASAT"),
			(("cdnet",), "NonameTV"),
			(("unicast",), "StarLink"),
			(("udp/239.255.2.",), "Planeta"),
			(("udp/233.7.70.",), "Rostelecom"),
			(("udp/239.1.1.",), "Real"),
			(("udp/238.0.", "udp/233.191."), "Triolan"),
			(("%3a8208",), "MOVISTAR+"),
			(("udp/239.0.0.",), "Trinity"),
			((".cn.ru", "novotelecom"), "Novotelecom"),
			(("www.youtube.com",), "www.youtube.com"),
			((".torrent-tv.ru",), "torrent-tv.ru"),
			(("web.tvbox.md",), "web.tvbox.md"),
			(("live-p12",), "PAC12"),
			((".ottg.",), "Glanc"),
			(("/iptv/",), "Edem"),
			(("only4", "1ce"), "Only4"),
			(("wisp.cat",), "TvoeTV"),
			(("4097",), "StreamTV"),
			(("%3a1234",), "IPTV1")
		)
		return next((name for keys, name in providers if any(x in refstr for x in keys)), "")

	def getPlayingref(self, ref):
		playingRef = NavigationInstance.instance and NavigationInstance.instance.getCurrentlyPlayingServiceReference()
		return playingRef or eServiceReference()

	def getProviderName(self, ref):
		providerName = ""
		if isinstance(ref, eServiceReference):
			from Screens.ChannelSelection import service_types_radio, service_types_tv  # Prevent circular import.
			typeString = service_types_radio if ref.getData(0) in (2, 10) else service_types_tv
			pos = typeString.rfind(":")
			rootString = f"{typeString[:pos + 1]} (channelID == {ref.getUnsignedData(4):08x}{ref.getUnsignedData(2):04x}{ref.getUnsignedData(3):04x}) && {typeString[pos + 1:]} FROM PROVIDERS ORDER BY name"
			serviceHandler = eServiceCenter.getInstance()
			providerList = serviceHandler.list(eServiceReference(rootString))
			if providerList is not None:
				while not providerName:
					provider = providerList.getNext()
					if not provider.valid():
						break
					if provider.flags & eServiceReference.isDirectory:
						serviceList = serviceHandler.list(provider)
						if serviceList is not None:
							while True:
								service = serviceList.getNext()
								if not service.valid():
									break
								if service == ref:
									info = serviceHandler.info(provider)
									providerName = info and info.getName(provider) or "Unknown"
									break
		return providerName

	def getReferenceType(self, refstr, ref):
		if ref is None:
			if NavigationInstance.instance:
				playRef = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
				if playRef:
					refstr = playRef.toString() or ""
					prefix = "GStreamer " if refstr.startswith("4097:") else ""
					refstr = f"{prefix}{' '.join(refstr.split(':')[10:])}" if "%3a//" in refstr else f"{prefix}{':'.join(refstr.split(':')[:10])}"
		elif refstr != "":
			prefix = ""
			if refstr.startswith("1:7:"):
				if "FROM BOUQUET" in refstr:
					prefix = "Bouquet "
				elif "(provider == " in refstr:
					prefix = "Provider "
				elif "(satellitePosition == " in refstr:
					prefix = "Satellit "
				elif "(channelID == " in refstr:
					prefix = "Current tr "
			elif refstr.startswith("1:134:"):
				prefix = "Alter "
			elif refstr.startswith("1:64:"):
				prefix = "Marker "
			elif refstr.startswith("4097:"):
				prefix = "GStreamer "
			if self.isStream:
				if self.refstr:
					serviceRef = " ".join(self.refstr.split(":")[10:]) if "%3a//" in self.refstr else ":".join(self.refstr.split(":")[:10])
				else:
					serviceRef = " ".join(refstr.split(":")[10:])
			else:
				serviceRef = ":".join((self.refstr or refstr).split(":")[:10])
			refstr = f"{prefix}{serviceRef}"
		return refstr

	def getSatelliteName(self, ref):
		result = ""
		if isinstance(ref, eServiceReference):
			orbpos = ref.getUnsignedData(4) >> 16
			if orbpos == 0xFFFF:  # Cable.
				result = _("Cable")
			elif orbpos == 0xEEEE:  # Terrestrial.
				result = _("Terrestrial")
			else:  # Satellite.
				orbpos = ref.getData(4) >> 16
				if orbpos < 0:
					orbpos += 3600
				try:
					result = str(nimmanager.getSatDescription(orbpos))
				except Exception:
					if not (ref.flags & (eServiceReference.isDirectory | eServiceReference.isMarker)):
						refString = ref.toString().lower()
						if refString.startswith("-1"):
							result = ""
						elif refString.startswith("1:134:"):
							result = _("Alternative")
						elif refString.startswith("4097:"):
							result = _("Internet")
						else:
							result = f"{(3600 - orbpos) // 10}.{(3600 - orbpos) % 10}°W" if orbpos > 1800 else f"{orbpos // 10}.{orbpos % 10}°E"
		return result

	def getServiceNumber(self, ref):
		def searchHelper(serviceHandler, num, bouquet):
			found = None
			serviceList = serviceHandler.list(bouquet)
			if serviceList is not None:
				while found is None:
					service = serviceList.getNext()
					if not service.valid():
						break
					if not (service.flags & (eServiceReference.isMarker | eServiceReference.isDirectory)):
						num += 1
						if service == ref:
							found = service
			return found, num

		result = (0, "")
		if isinstance(ref, eServiceReference):
			isRadioService = ref.getData(0) in (2, 10)
			lastPath = config.radio.lastroot.value if isRadioService else config.tv.lastroot.value
			if "FROM BOUQUET" not in lastPath:
				if "FROM PROVIDERS" in lastPath:
					result = ("P", _("Provider"))
				elif "FROM SATELLITES" in lastPath:
					result = ("S", _("Satellites"))
				elif ") ORDER BY name" in lastPath:
					result = ("A", _("All Services"))
				else:
					result = (0, "N/A")
			else:
				try:
					acount = config.plugins.NumberZapExt.enable.value and config.plugins.NumberZapExt.acount.value or config.usage.alternative_number_mode.value
				except Exception:
					acount = False
				rootString = next((x for x in reversed(lastPath.split(";")) if x != ""), "")
				serviceHandler = eServiceCenter.getInstance()
				service = None
				number = 0
				if acount is True or not config.usage.multibouquet.value:
					bouquet = eServiceReference(rootString)
					service, number = searchHelper(serviceHandler, 0, bouquet)
				else:
					bouquetRootString = "1:7:2:0:0:0:0:0:0:0:FROM BOUQUET \"bouquets.radio\" ORDER BY bouquet" if isRadioService else "1:7:1:0:0:0:0:0:0:0:FROM BOUQUET \"bouquets.tv\" ORDER BY bouquet"
					current = eServiceReference(rootString)
					bouquet = eServiceReference(bouquetRootString)
					bouquetList = serviceHandler.list(bouquet)
					if bouquetList is not None:
						while True:
							bouquet = bouquetList.getNext()
							if not bouquet.valid():
								break
							if bouquet.flags & eServiceReference.isDirectory:
								service, number = searchHelper(serviceHandler, number, bouquet)
								if service is not None and current == bouquet:
									break
				if service is not None:
					info = serviceHandler.info(bouquet)
					result = (number, info and info.getName(bouquet) or "")
		return result

	@cached
	def getText(self):
		def getAllRef():
			referenceType = self.getReferenceType(refstr, ref)
			if any(x in referenceType for x in ("Bouquet", "Satellit", "Provider")):
				result = " "
			elif "%3a" in referenceType:
				result = ":".join(refstr.split(":")[:10])
			else:
				result = referenceType
			return result

		def getName():
			name = ref and (info.getName(ref) or "N/A") or (info.getName() or "N/A")
			if self.ref:
				name = f"{name} (alter)"
			return name.replace("\xc2\x86", "").replace("\xc2\x87", "")

		def getNumberAndBouquet():
			return self.getServiceNumber(ref or eServiceReference(info.getInfoString(iServiceInformation.sServiceref)))

		def getProvider():
			if self.isStream:
				result = self.getIPTVProvider(self.refstr if self.refstr and "%3a//" in self.refstr else refstr)
			elif self.ref:
				result = self.getProviderName(self.ref)
			elif ref:
				result = self.getProviderName(ref)
			else:
				result = info.getInfoString(iServiceInformation.sProvider) or ""
			return result

		def getSatellite():
			if self.isStream:
				result = _("Internet")
			elif self.ref:
				result = self.getSatelliteName(self.ref)
			else:
				result = self.getSatelliteName(ref or eServiceReference(info.getInfoString(iServiceInformation.sServiceref)))
			return result

		text = ""
		service = self.source.service
		if isinstance(service, iPlayableServicePtr):
			info = service and service.info()
			ref = None
		else:  # Reference.
			info = service and self.source.info
			ref = service
		if info:
			refstr = (ref.toString() if ref else info.getInfoString(iServiceInformation.sServiceref)) or ""
			if self.AlternativeControl and ref and refstr.startswith("1:134:") and self.ref is None:
				alternativeRef = self.resolveAlternate(ref)
				if alternativeRef:
					self.ref = alternativeRef
					self.info = eServiceCenter.getInstance().info(self.ref)
					self.refstr = self.ref.toString()
					if not self.info:
						info = None
		if info:
			if self.IPTVcontrol and ("%3a//" in refstr or (self.refstr and "%3a//" in self.refstr) or refstr.startswith("4097:")):
				self.isStream = True
			match self.type:
				case self.ALLREF:
					text = getAllRef()
				case self.BOUQUET:
					text = getNumberAndBouquet()[1]
				case self.FORMAT:
					parts = self.sfmt.split("%")
					text = parts[0]
					for part in parts[1:]:
						code = part[:1]
						match code:
							case "A":  # AllRef.
								text += getAllRef()
							case "B":  # Bouquet.
								text += getNumberAndBouquet()[1]
							case "N":  # Name.
								text += getName()
							case "P":  # Provider.
								text += getProvider()
							case "R":  # Reference.
								text += self.refstr or refstr
							case "S":  # Satellite.
								text += getSatellite()
							case "n":  # Number.
								try:
									service = self.source.serviceref
									number = service and service.getChannelNum() or None
								except Exception:
									number = None
								if not number:
									number = getNumberAndBouquet()[0]
								text += str(number) if number else ""
							case _ if code in "TtsFfiOMpYroclhmgbe":
								text += self.getTransponderInfo(self.info, self.ref, code) if self.ref else self.getTransponderInfo(info, ref, code)
						text += part[1:]
					text = text.replace("N/A", "").strip()
				case self.NAME:
					text = getName()
				case self.NUMBER:
					try:
						service = self.source.service if self.source and self.source.__class__.__name__ == "ServiceEvent" else self.source.serviceref
						text = str(service and service.getChannelNum() or "")
					except Exception:
						number = getNumberAndBouquet()[0]
						text = str(number) if number else ""
				case self.ORBPOS:
					if self.isStream:
						text = "Stream"
					else:
						text = self.getTransponderInfo(self.info, self.ref, "O") if self.ref and self.info else self.getTransponderInfo(info, ref, "O")
				case self.PROVIDER:
					text = getProvider()
				case self.REFERENCE:
					text = self.refstr or refstr
				case self.SATELLITE:
					text = getSatellite()
				case self.TPRDATA:
					if self.isStream:
						text = _("Streaming")
					else:
						text = self.getTransponderInfo(self.info, self.ref, "T") if self.ref and self.info else self.getTransponderInfo(info, ref, "T")
		return text

	text = property(getText)

	def getTransponderInfo(self, info, ref, fmt):
		result = ""
		if self.tpdata is None:
			self.tpdata = info.getInfoObject(ref, iServiceInformation.sTransponderData) if ref else info.getInfoObject(iServiceInformation.sTransponderData)
			if not isinstance(self.tpdata, dict):
				self.tpdata = None
		if self.tpdata is not None:
			tunerType = "IP-TV" if self.isStream else self.tpdata.get("tuner_type", "")
			if (not fmt or fmt == "T") and tunerType == "IP-TV":
				result = _("Streaming")
			else:
				if not fmt or fmt == "T":
					match tunerType:
						case "DVB-C":
							fmt = ["t ", "F ", "Y ", "i ", "f ", "M"]  # (type frequency symbol_rate inversion fec modulation)
						case "DVB-T":
							if ref:
								fmt = ["O ", "F ", "c ", "l ", "h ", "m ", "g "]  # (orbital_position code_rate_hp transmission_mode guard_interval constellation)
							else:
								fmt = ["t ", "F ", "c ", "l ", "h ", "m ", "g "]  # (type frequency code_rate_hp transmission_mode guard_interval constellation)
						case _:
							fmt = ["O ", "s ", "M ", "F ", "p ", "Y ", "f"]  # (orbital_position frequency polarization symbol_rate fec)
				codeRates = {0: "1/2", 1: "2/3", 2: "3/4", 3: "5/6", 4: "7/8", 5: "Auto"}
				for line in fmt:
					match line[:1]:
						case "F":  # Frequency (dvb-s/s2/c/t) in KHz.
							if tunerType in ("DVB-S", "DVB-C") and self.tpdata.get("frequency", 0) > 0:
								result += f"{self.tpdata.get('frequency', 0) // 1000} MHz"
							if tunerType == "DVB-T":
								result += f"{(self.tpdata.get('frequency', 0) + 500) / 1000 / 1000.0:.3f} MHz"
						case "M":  # Modulation (dvb-s/s2/c).
							value = self.tpdata.get("modulation", 1)
							if tunerType == "DVB-S":
								result += {0: "Auto", 1: "QPSK", 2: "8PSK", 3: "QAM16"}.get(value, "")
							elif tunerType == "DVB-C":
								result += {0: "Auto", 1: "QAM16", 2: "QAM32", 3: "QAM64", 4: "QAM128", 5: "QAM256"}.get(value, "")
						case "O":  # Orbital_position (dvb-s/s2).
							if tunerType == "DVB-S":
								value = self.tpdata.get("orbital_position", 0)
								result += f"{(3600 - value) // 10}.{(3600 - value) % 10}°W" if value > 1800 else f"{value // 10}.{value % 10}°E"
							else:
								result += {"DVB-C": "DVB-C", "DVB-T": "DVB-T", "Iptv": "Stream"}.get(tunerType, "")
						case "Y":  # Symbol_rate (dvb-s/s2/c).
							if tunerType in ("DVB-S", "DVB-C"):
								result += f"{self.tpdata.get('symbol_rate', 0) // 1000}"
						case "b":  # Bandwidth (dvb-t).
							if tunerType == "DVB-T":
								result += {0: "8 MHz", 1: "7 MHz", 2: "6 MHz", 3: "Auto"}.get(self.tpdata.get("bandwidth", 1), "")
						case "c":  # Constellation (dvb-t).
							if tunerType == "DVB-T":
								result += {0: "QPSK", 1: "QAM16", 2: "QAM64", 3: "Auto"}.get(self.tpdata.get("constellation", 3), "")
						case "e":  # Hierarchy_information (dvb-t).
							if tunerType == "DVB-T":
								result += {0: "None", 1: "1", 2: "2", 3: "4", 4: "Auto"}.get(self.tpdata.get("hierarchy_information", 4), "")
						case "f":  # FEC_inner (dvb-s/s2/c/t).
							if tunerType in ("DVB-S", "DVB-C"):
								result += {0: "Auto", 1: "1/2", 2: "2/3", 3: "3/4", 4: "5/6", 5: "7/8", 6: "8/9", 7: "3/5", 8: "4/5", 9: "9/10", 15: "None"}.get(self.tpdata.get("fec_inner", 15), "")
							elif tunerType == "DVB-T":
								result += codeRates.get(self.tpdata.get("code_rate_lp", 5), "")
						case "g":  # Guard_interval (dvb-t).
							if tunerType == "DVB-T":
								result += {0: "1/32", 1: "1/16", 2: "1/8", 3: "1/4", 4: "Auto"}.get(self.tpdata.get("guard_interval", 4), "")
						case "h":  # Code_rate_hp (dvb-t).
							if tunerType == "DVB-T":
								result += codeRates.get(self.tpdata.get("code_rate_hp", 5), "")
						case "i":  # Inversion (dvb-s/s2/c/t).
							if tunerType in ("DVB-S", "DVB-C", "DVB-T"):
								result += {0: "On", 1: "Off", 2: "Auto"}.get(self.tpdata.get("inversion", 2), "")
						case "l":  # Code_rate_lp (dvb-t).
							if tunerType == "DVB-T":
								result += codeRates.get(self.tpdata.get("code_rate_lp", 5), "")
						case "m":  # Transmission_mode (dvb-t).
							if tunerType == "DVB-T":
								result += {0: "2k", 1: "8k", 2: "Auto"}.get(self.tpdata.get("transmission_mode", 2), "")
						case "o":  # Pilot (dvb-s2).
							if not self.isStream:
								value = self.tpdata.get("pilot")
								if value is not None:
									result += {0: "Off", 1: "On", 2: "Auto"}.get(value, "")
						case "p":  # Polarization (dvb-s/s2).
							if tunerType == "DVB-S":
								result += {0: "H", 1: "V", 2: "LHC", 3: "RHC"}.get(self.tpdata.get("polarization", 0), "?")
						case "r":  # Rolloff (dvb-s2).
							if not self.isStream:
								value = self.tpdata.get("rolloff")
								if value is not None:
									result += {0: "0.35", 1: "0.25", 2: "0.20"}.get(value, "")
						case "s":  # System (dvb-s/s2/c/t).
							result += {0: "DVB-S", 1: "DVB-S2"}.get(self.tpdata.get("system", 0), "") if tunerType == "DVB-S" else tunerType
						case "t":  # Tuner_type (dvb-s/s2/c/t).
							result += {"DVB-S": _("Satellite"), "DVB-C": _("Cable"), "DVB-T": _("Terrestrial"), "IP-TV": _("Stream-tv")}.get(tunerType, "N/A")
					result += line[1:]
		return result

	def isAdditionalService(self, group=False):
		def searchService(serviceHandler, bouquet):
			found = False
			serviceList = serviceHandler.list(bouquet)
			if serviceList is not None:
				while not found:
					service = serviceList.getNext()
					if not service.valid():
						break
					if not (service.flags & (eServiceReference.isMarker | eServiceReference.isDirectory)):
						found = bool(service.flags & eServiceReference.isGroup) if group else "%3a//" in service.toString().lower()
			return found

		isService = False
		serviceHandler = eServiceCenter.getInstance()
		if config.usage.multibouquet.value:
			bouquetList = serviceHandler.list(eServiceReference("1:7:1:0:0:0:0:0:0:0:FROM BOUQUET \"bouquets.tv\" ORDER BY bouquet"))
			if bouquetList is not None:
				while not isService:
					bouquet = bouquetList.getNext()
					if not bouquet.valid():
						break
					if bouquet.flags & eServiceReference.isDirectory:
						isService = searchService(serviceHandler, bouquet)
		else:
			serviceTypesTv = "1:7:1:0:0:0:0:0:0:0:(type == 1) || (type == 17) || (type == 22) || (type == 25) || (type == 134) || (type == 195)"
			isService = searchService(serviceHandler, eServiceReference(f"{serviceTypesTv} FROM BOUQUET \"userbouquet.favourites.tv\" ORDER BY bouquet"))
		return isService

	def neededChange(self):
		if self.what:
			Converter.changed(self, self.what)
			self.what = None

	def resolveAlternate(self, ref):
		alternativeRef = getBestPlayableServiceReference(ref, self.getPlayingref(ref))
		if not alternativeRef:
			alternativeRef = getBestPlayableServiceReference(ref, eServiceReference(), True)
		return alternativeRef

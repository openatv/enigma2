# -*- coding: utf-8 -*-
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

from Components.Converter.Converter import Converter
from enigma import iServiceInformation, iPlayableService, iPlayableServicePtr, eServiceReference, eServiceCenter, eTimer, getBestPlayableServiceReference
from Components.Element import cached
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

	def __init__(self, type):
		Converter.__init__(self, type)
		if type == "Name" or not len(str(type)):
			self.type = self.NAME
		elif type == "Number":
			self.type = self.NUMBER
		elif type == "Bouquet":
			self.type = self.BOUQUET
		elif type == "Provider":
			self.type = self.PROVIDER
		elif type == "Reference":
			self.type = self.REFERENCE
		elif type == "OrbitalPos":
			self.type = self.ORBPOS
		elif type == "TpansponderInfo":
			self.type = self.TPRDATA
		elif type == "Satellite":
			self.type = self.SATELLITE
		elif type == "AllRef":
			self.type = self.ALLREF
		else:
			self.type = self.FORMAT
			self.sfmt = type[:]
		try:
			if (self.type == 1 or (self.type == 9 and "%n" in self.sfmt)) and correctChannelNumber:
				ChannelNumberClasses.append(self.forceChanged)
		except Exception:
			pass
		self.refstr = self.isStream = self.ref = self.info = self.what = self.tpdata = None
		self.Timer = eTimer()
		self.Timer.callback.append(self.neededChange)
		self.IPTVcontrol = self.isAdditionalService(type=0)
		self.AlternativeControl = self.isAdditionalService(type=1)

	def isAdditionalService(self, type=0):
		def searchService(serviceHandler, bouquet):
			istype = False
			servicelist = serviceHandler.list(bouquet)
			if servicelist is not None:
				while True:
					s = servicelist.getNext()
					if not s.valid():
						break
					if not (s.flags & (eServiceReference.isMarker | eServiceReference.isDirectory)):
						if type:
							if s.flags & eServiceReference.isGroup:
								istype = True
								return istype
						else:
							if "%3a//" in s.toString().lower():
								istype = True
								return istype
			return istype

		isService = False
		serviceHandler = eServiceCenter.getInstance()
		if not config.usage.multibouquet.value:
			service_types_tv = "1:7:1:0:0:0:0:0:0:0:(type == 1) || (type == 17) || (type == 22) || (type == 25) || (type == 134) || (type == 195)"
			rootstr = f"{service_types_tv} FROM BOUQUET \"userbouquet.favourites.tv\" ORDER BY bouquet"
		else:
			rootstr = "1:7:1:0:0:0:0:0:0:0:FROM BOUQUET \"bouquets.tv\" ORDER BY bouquet"
		bouquet = eServiceReference(rootstr)
		if not config.usage.multibouquet.value:
			isService = searchService(serviceHandler, bouquet)
		else:
			bouquetlist = serviceHandler.list(bouquet)
			if bouquetlist is not None:
				while True:
					bouquet = bouquetlist.getNext()
					if not bouquet.valid():
						break
					if bouquet.flags & eServiceReference.isDirectory:
						isService = searchService(serviceHandler, bouquet)
						if isService:
							break
		return isService

	def getServiceNumber(self, ref):
		def searchHelper(serviceHandler, num, bouquet):
			servicelist = serviceHandler.list(bouquet)
			if servicelist is not None:
				while True:
					s = servicelist.getNext()
					if not s.valid():
						break
					if not (s.flags & (eServiceReference.isMarker | eServiceReference.isDirectory)):
						num += 1
						if s == ref:
							return s, num
			return None, num

		if isinstance(ref, eServiceReference):
			isRadioService = ref.getData(0) in (2, 10)
			lastpath = isRadioService and config.radio.lastroot.value or config.tv.lastroot.value
			if "FROM BOUQUET" not in lastpath:
				if "FROM PROVIDERS" in lastpath:
					return "P", _("Provider")
				if "FROM SATELLITES" in lastpath:
					return "S", _("Satellites")
				if ") ORDER BY name" in lastpath:
					return "A", _("All Services")
				return 0, "N/A"
			try:
				acount = config.plugins.NumberZapExt.enable.value and config.plugins.NumberZapExt.acount.value or config.usage.alternative_number_mode.value
			except Exception:
				acount = False
			rootstr = ""
			for x in lastpath.split(";"):
				if x != "":
					rootstr = x
			serviceHandler = eServiceCenter.getInstance()
			if acount is True or not config.usage.multibouquet.value:
				bouquet = eServiceReference(rootstr)
				service, number = searchHelper(serviceHandler, 0, bouquet)
			else:
				if isRadioService:
					bqrootstr = "1:7:2:0:0:0:0:0:0:0:FROM BOUQUET \"bouquets.radio\" ORDER BY bouquet"
				else:
					bqrootstr = "1:7:1:0:0:0:0:0:0:0:FROM BOUQUET \"bouquets.tv\" ORDER BY bouquet"
				number = 0
				cur = eServiceReference(rootstr)
				bouquet = eServiceReference(bqrootstr)
				bouquetlist = serviceHandler.list(bouquet)
				if bouquetlist is not None:
					while True:
						bouquet = bouquetlist.getNext()
						if not bouquet.valid():
							break
						if bouquet.flags & eServiceReference.isDirectory:
							service, number = searchHelper(serviceHandler, number, bouquet)
							if service is not None and cur == bouquet:
								break
			if service is not None:
				info = serviceHandler.info(bouquet)
				name = info and info.getName(bouquet) or ""
				return number, name
		return 0, ""

	def getProviderName(self, ref):
		if isinstance(ref, eServiceReference):
			from Screens.ChannelSelection import service_types_radio, service_types_tv
			typestr = ref.getData(0) in (2, 10) and service_types_radio or service_types_tv
			pos = typestr.rfind(":")
			rootstr = f"{typestr[:pos + 1]} (channelID == {ref.getUnsignedData(4):08x}{ref.getUnsignedData(2):04x}{ref.getUnsignedData(3):04x}) && {typestr[pos + 1:]} FROM PROVIDERS ORDER BY name"
			provider_root = eServiceReference(rootstr)
			serviceHandler = eServiceCenter.getInstance()
			providerlist = serviceHandler.list(provider_root)
			if providerlist is not None:
				while True:
					provider = providerlist.getNext()
					if not provider.valid():
						break
					if provider.flags & eServiceReference.isDirectory:
						servicelist = serviceHandler.list(provider)
						if servicelist is not None:
							while True:
								service = servicelist.getNext()
								if not service.valid():
									break
								if service == ref:
									info = serviceHandler.info(provider)
									return info and info.getName(provider) or "Unknown"
		return ""

	def getTransponderInfo(self, info, ref, fmt):
		result = ""
		if self.tpdata is None:
			if ref:
				self.tpdata = ref and info.getInfoObject(ref, iServiceInformation.sTransponderData)
			else:
				self.tpdata = info.getInfoObject(iServiceInformation.sTransponderData)
			if not isinstance(self.tpdata, dict):
				self.tpdata = None
				return result
		if self.isStream:
			type = "IP-TV"
		else:
			type = self.tpdata.get("tuner_type", "")
		if not fmt or fmt == "T":
			if type == "DVB-C":
				fmt = ["t ", "F ", "Y ", "i ", "f ", "M"]  # (type frequency symbol_rate inversion fec modulation)
			elif type == "DVB-T":
				if ref:
					fmt = ["O ", "F ", "c ", "l ", "h ", "m ", "g "]  # (orbital_position code_rate_hp transmission_mode guard_interval constellation)
				else:
					fmt = ["t ", "F ", "c ", "l ", "h ", "m ", "g "]  # (type frequency code_rate_hp transmission_mode guard_interval constellation)
			elif type == "IP-TV":
				return _("Streaming")
			else:
				fmt = ["O ", "s ", "M ", "F ", "p ", "Y ", "f"]  # (orbital_position frequency polarization symbol_rate fec)
		for line in fmt:
			match line[:1]:
				case "t":  # Tuner_type (dvb-s/s2/c/t).
					if type == "DVB-S":
						result += _("Satellite")
					elif type == "DVB-C":
						result += _("Cable")
					elif type == "DVB-T":
						result += _("Terrestrial")
					elif type == "IP-TV":
						result += _("Stream-tv")
					else:
						result += "N/A"
				case "s":  # System (dvb-s/s2/c/t).
					if type == "DVB-S":
						x = self.tpdata.get("system", 0)
						result += x in list(range(2)) and {0: "DVB-S", 1: "DVB-S2"}[x] or ""
					else:
						result += type
				case "F":  # Frequency (dvb-s/s2/c/t) in KHz.
					if type in ("DVB-S", "DVB-C") and self.tpdata.get("frequency", 0) > 0:
						result += f"{self.tpdata.get("frequency", 0) // 1000} MHz"
					if type == "DVB-T":
						result += f"{(self.tpdata.get("frequency", 0) + 500) / 1000 / 1000.0:.3f} MHz"
						# result += "%.3f"%(((self.tpdata.get("frequency", 0) / 1000) +1) / 1000.0) + " MHz "
				case "f":  # FEC_inner (dvb-s/s2/c/t).
					if type in ("DVB-S", "DVB-C"):
						x = self.tpdata.get("fec_inner", 15)
						result += x in list(range(10)) + [15] and {0: "Auto", 1: "1/2", 2: "2/3", 3: "3/4", 4: "5/6", 5: "7/8", 6: "8/9", 7: "3/5", 8: "4/5", 9: "9/10", 15: "None"}[x] or ""
					elif type == "DVB-T":
						x = self.tpdata.get("code_rate_lp", 5)
						result += x in list(range(6)) and {0: "1/2", 1: "2/3", 2: "3/4", 3: "5/6", 4: "7/8", 5: "Auto"}[x] or ""
				case "i":  # Inversion (dvb-s/s2/c/t).
					if type in ("DVB-S", "DVB-C", "DVB-T"):
						x = self.tpdata.get("inversion", 2)
						result += x in list(range(3)) and {0: "On", 1: "Off", 2: "Auto"}[x] or ""
				case "O":  # Orbital_position (dvb-s/s2).
					if type == "DVB-S":
						x = self.tpdata.get("orbital_position", 0)
						result += x > 1800 and f"{(3600 - x) // 10}.{(3600 - x) % 10}°W" or f"{x // 10}.{x % 10}°E"
					elif type == "DVB-T":
						result += "DVB-T"
					elif type == "DVB-C":
						result += "DVB-C"
					elif type == "Iptv":
						result += "Stream"
				case "M":  # Modulation (dvb-s/s2/c).
					x = self.tpdata.get("modulation", 1)
					if type == "DVB-S":
						result += x in list(range(4)) and {0: "Auto", 1: "QPSK", 2: "8PSK", 3: "QAM16"}[x] or ""
					elif type == "DVB-C":
						result += x in list(range(6)) and {0: "Auto", 1: "QAM16", 2: "QAM32", 3: "QAM64", 4: "QAM128", 5: "QAM256"}[x] or ""
				case "p":  # Polarization (dvb-s/s2).
					if type == "DVB-S":
						x = self.tpdata.get("polarization", 0)
						result += x in list(range(4)) and {0: "H", 1: "V", 2: "LHC", 3: "RHC"}[x] or "?"
				case "Y":  # Symbol_rate (dvb-s/s2/c).
					if type in ("DVB-S", "DVB-C"):
						result += f"{self.tpdata.get("symbol_rate", 0) // 1000}"
				case "r":  # Rolloff (dvb-s2).
					if not self.isStream:
						x = self.tpdata.get("rolloff")
						if x is not None:
							result += x in list(range(3)) and {0: "0.35", 1: "0.25", 2: "0.20"}[x] or ""
				case "o":  # Pilot (dvb-s2).
					if not self.isStream:
						x = self.tpdata.get("pilot")
						if x is not None:
							result += x in list(range(3)) and {0: "Off", 1: "On", 2: "Auto"}[x] or ""
				case "c":  # Constellation (dvb-t).
					if type == "DVB-T":
						x = self.tpdata.get("constellation", 3)
						result += x in list(range(4)) and {0: "QPSK", 1: "QAM16", 2: "QAM64", 3: "Auto"}[x] or ""
				case "l":  # Code_rate_lp (dvb-t).
					if type == "DVB-T":
						x = self.tpdata.get("code_rate_lp", 5)
						result += x in list(range(6)) and {0: "1/2", 1: "2/3", 2: "3/4", 3: "5/6", 4: "7/8", 5: "Auto"}[x] or ""
				case "h":  # Code_rate_hp (dvb-t).
					if type == "DVB-T":
						x = self.tpdata.get("code_rate_hp", 5)
						result += x in list(range(6)) and {0: "1/2", 1: "2/3", 2: "3/4", 3: "5/6", 4: "7/8", 5: "Auto"}[x] or ""
				case "m":  # Transmission_mode (dvb-t).
					if type == "DVB-T":
						x = self.tpdata.get("transmission_mode", 2)
						result += x in list(range(3)) and {0: "2k", 1: "8k", 2: "Auto"}[x] or ""
				case "g":  # Guard_interval (dvb-t).
					if type == "DVB-T":
						x = self.tpdata.get("guard_interval", 4)
						result += x in list(range(5)) and {0: "1/32", 1: "1/16", 2: "1/8", 3: "1/4", 4: "Auto"}[x] or ""
				case "b":  # Bandwidth (dvb-t).
					if type == "DVB-T":
						x = self.tpdata.get("bandwidth", 1)
						result += x in list(range(4)) and {0: "8 MHz", 1: "7 MHz", 2: "6 MHz", 3: "Auto"}[x] or ""
				case "e":  # Hierarchy_information (dvb-t).
					if type == "DVB-T":
						x = self.tpdata.get("hierarchy_information", 4)
						result += x in list(range(5)) and {0: "None", 1: "1", 2: "2", 3: "4", 4: "Auto"}[x] or ""
			result += line[1:]
		return result

	def getSatelliteName(self, ref):
		if isinstance(ref, eServiceReference):
			orbpos = ref.getUnsignedData(4) >> 16
			if orbpos == 0xFFFF:  # Cable
				return _("Cable")
			elif orbpos == 0xEEEE:  # Terrestrial
				return _("Terrestrial")
			else:  # Satellite
				orbpos = ref.getData(4) >> 16
				if orbpos < 0:
					orbpos += 3600
				try:
					from Components.NimManager import nimmanager
					return str(nimmanager.getSatDescription(orbpos))
				except Exception:
					dir = ref.flags & (eServiceReference.isDirectory | eServiceReference.isMarker)
					if not dir:
						refString = ref.toString().lower()
						if refString.startswith("-1"):
							return ""
						elif refString.startswith("1:134:"):
							return _("Alternative")
						elif refString.startswith("4097:"):
							return _("Internet")
						else:
							return orbpos > 1800 and f"{(3600 - orbpos) // 10}.{(3600 - orbpos) % 10}°W" or f"{orbpos // 10}.{orbpos % 10}°E"
		return ""

	def getIPTVProvider(self, refstr):
		if "tvshka" in refstr:
			return "SCHURA"
		elif "udp/239.0.1" in refstr:
			return "Lanet"
		elif "3a7777" in refstr:
			return "IPTVNTV"
		elif "KartinaTV" in refstr:
			return "KartinaTV"
		elif "Megaimpuls" in refstr:
			return "MEGAIMPULSTV"
		elif "Newrus" in refstr:
			return "NEWRUSTV"
		elif "Sovok" in refstr:
			return "SOVOKTV"
		elif "Rodnoe" in refstr:
			return "RODNOETV"
		elif "238.1.1.181%3a1234" in refstr:
			return "VIASAT"
		elif "cdnet" in refstr:
			return "NonameTV"
		elif "unicast" in refstr:
			return "StarLink"
		elif "udp/239.255.2." in refstr:
			return "Planeta"
		elif "udp/233.7.70." in refstr:
			return "Rostelecom"
		elif "udp/239.1.1." in refstr:
			return "Real"
		elif "udp/238.0." in refstr or "udp/233.191." in refstr:
			return "Triolan"
		elif "%3a8208" in refstr:
			return "MOVISTAR+"
		elif "udp/239.0.0." in refstr:
			return "Trinity"
		elif ".cn.ru" in refstr or "novotelecom" in refstr:
			return "Novotelecom"
		elif "www.youtube.com" in refstr:
			return "www.youtube.com"
		elif ".torrent-tv.ru" in refstr:
			return "torrent-tv.ru"
		elif "web.tvbox.md" in refstr:
			return "web.tvbox.md"
		elif "live-p12" in refstr:
			return "PAC12"
		elif ".ottg." in refstr:
			return "Glanc"
		elif "/iptv/" in refstr:
			return "Edem"
		elif "only4" in refstr or "1ce" in refstr:
			return "Only4"
		elif "wisp.cat" in refstr:
			return "TvoeTV"
		elif "4097" in refstr:
			return "StreamTV"
		elif "%3a1234" in refstr:
			return "IPTV1"
		return ""

	def getPlayingref(self, ref):
		playingref = None
		if NavigationInstance.instance:
			playingref = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
		if not playingref:
			playingref = eServiceReference()
		return playingref

	def resolveAlternate(self, ref):
		nref = getBestPlayableServiceReference(ref, self.getPlayingref(ref))
		if not nref:
			nref = getBestPlayableServiceReference(ref, eServiceReference(), True)
		return nref

	def getReferenceType(self, refstr, ref):
		if ref is None:
			if NavigationInstance.instance:
				playref = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
				if playref:
					refstr = playref.toString() or ""
					prefix = ""
					if refstr.startswith("4097:"):
						prefix += "GStreamer "
					if "%3a//" in refstr:
						sref = " ".join(refstr.split(":")[10:])
						refstr = prefix + sref
					else:
						sref = ":".join(refstr.split(":")[:10])
						refstr = prefix + sref
		else:
			if refstr != "":
				prefix = ""
				if refstr.startswith("1:7:"):
					if "FROM BOUQUET" in refstr:
						prefix += "Bouquet "
					elif "(provider == " in refstr:
						prefix += "Provider "
					elif "(satellitePosition == " in refstr:
						prefix += "Satellit "
					elif "(channelID == " in refstr:
						prefix += "Current tr "
				elif refstr.startswith("1:134:"):
					prefix += "Alter "
				elif refstr.startswith("1:64:"):
					prefix += "Marker "
				elif refstr.startswith("4097:"):
					prefix += "GStreamer "
				if self.isStream:
					if self.refstr:
						sref = " ".join(self.refstr.split(":")[10:]) if "%3a//" in self.refstr else ":".join(self.refstr.split(":")[:10])
					else:
						sref = " ".join(refstr.split(":")[10:])
					return prefix + sref
				else:
					sref = ":".join(self.refstr.split(":")[:10]) if self.refstr else ":".join(refstr.split(":")[:10])
					return prefix + sref
		return refstr

	@cached
	def getText(self):
		service = self.source.service
		if isinstance(service, iPlayableServicePtr):
			info = service and service.info()
			ref = None
		else:  # reference
			info = service and self.source.info
			ref = service
		if not info:
			return ""
		if ref:
			refstr = ref.toString()
		else:
			refstr = info.getInfoString(iServiceInformation.sServiceref)
		if refstr is None:
			refstr = ""
		if self.AlternativeControl:
			if ref and refstr.startswith("1:134:") and self.ref is None:
				nref = self.resolveAlternate(ref)
				if nref:
					self.ref = nref
					self.info = eServiceCenter.getInstance().info(self.ref)
					self.refstr = self.ref.toString()
					if not self.info:
						return ""
		if self.IPTVcontrol:
			if "%3a//" in refstr or (self.refstr and "%3a//" in self.refstr) or refstr.startswith("4097:"):
				self.isStream = True
		match self.type:
			case self.NAME:
				name = ref and (info.getName(ref) or "N/A") or (info.getName() or "N/A")
				prefix = ""
				if self.ref:
					prefix = " (alter)"
				name += prefix
				return name.replace("\xc2\x86", "").replace("\xc2\x87", "")
			case self.NUMBER:
				try:
					service = self.source.service if self.source and self.source.__class__.__name__ == "ServiceEvent" else self.source.serviceref
					num = service and service.getChannelNum() or ""
					return str(num)
				except Exception:
					num, bouq = self.getServiceNumber(ref or eServiceReference(info.getInfoString(iServiceInformation.sServiceref)))
					return num and str(num) or ""
			case self.BOUQUET:
				num, bouq = self.getServiceNumber(ref or eServiceReference(info.getInfoString(iServiceInformation.sServiceref)))
				return bouq
			case self.PROVIDER:
				if self.isStream:
					if self.refstr and ("%3a//" in self.refstr):
						return self.getIPTVProvider(self.refstr)
					return self.getIPTVProvider(refstr)
				else:
					if self.ref:
						return self.getProviderName(self.ref)
					if ref:
						return self.getProviderName(ref)
					else:
						return info.getInfoString(iServiceInformation.sProvider) or ""
			case self.REFERENCE:
				if self.refstr:
					return self.refstr
				return refstr
			case self.ORBPOS:
				if self.isStream:
					return "Stream"
				else:
					if self.ref and self.info:
						return self.getTransponderInfo(self.info, self.ref, "O")
					return self.getTransponderInfo(info, ref, "O")
			case self.TPRDATA:
				if self.isStream:
					return _("Streaming")
				else:
					if self.ref and self.info:
						return self.getTransponderInfo(self.info, self.ref, "T")
					return self.getTransponderInfo(info, ref, "T")
			case self.SATELLITE:
				if self.isStream:
					return _("Internet")
				else:
					if self.ref:
						return self.getSatelliteName(self.ref)
				# test #
					return self.getSatelliteName(ref or eServiceReference(info.getInfoString(iServiceInformation.sServiceref)))
			case self.ALLREF:
				tmpref = self.getReferenceType(refstr, ref)
				if "Bouquet" in tmpref or "Satellit" in tmpref or "Provider" in tmpref:
					return " "
				elif "%3a" in tmpref:
					return ":".join(refstr.split(":")[:10])
				return tmpref
			case self.FORMAT:
				num = bouq = ""
				tmp = self.sfmt[:].split("%")
				if tmp:
					ret = tmp[0]
					tmp.remove(ret)
				else:
					return ""
				for line in tmp:
					f = line[:1]
					match f:
						case "N":  # Name.
							name = ref and (info.getName(ref) or "N/A") or (info.getName() or "N/A")
							postfix = ""
							if self.ref:
								postfix = " (alter)"
							name += postfix
							ret += name.replace("\xc2\x86", "").replace("\xc2\x87", "")
						case "n":  # Number.
							try:
								service = self.source.serviceref
								num = service and service.getChannelNum() or None
							except Exception:
								num = None
							if num:
								ret += str(num)
							else:
								num, bouq = self.getServiceNumber(ref or eServiceReference(info.getInfoString(iServiceInformation.sServiceref)))
								ret += num and str(num) or ""
						case "B":  # Bouquet.
							num, bouq = self.getServiceNumber(ref or eServiceReference(info.getInfoString(iServiceInformation.sServiceref)))
							ret += bouq
						case "P":  # Provider.
							if self.isStream:
								if self.refstr and "%3a//" in self.refstr:
									ret += self.getIPTVProvider(self.refstr)
								else:
									ret += self.getIPTVProvider(refstr)
							else:
								if self.ref:
									ret += self.getProviderName(self.ref)
								else:
									if ref:
										ret += self.getProviderName(ref)
									else:
										ret += info.getInfoString(iServiceInformation.sProvider) or ""
						case "R":  # Reference.
							if self.refstr:
								ret += self.refstr
							else:
								ret += refstr
						case "S":  # Satellite.
							if self.isStream:
								ret += _("Internet")
							else:
								if self.ref:
									ret += self.getSatelliteName(self.ref)
								else:
									ret += self.getSatelliteName(ref or eServiceReference(info.getInfoString(iServiceInformation.sServiceref)))
						case "A":  # AllRef.
							tmpref = self.getReferenceType(refstr, ref)
							if "Bouquet" in tmpref or "Satellit" in tmpref or "Provider" in tmpref:
								ret += " "
							elif "%3a" in tmpref:
								ret += ":".join(refstr.split(":")[:10])
							else:
								ret += tmpref
						case _:
							if f in "TtsFfiOMpYroclhmgbe":
								ret += self.getTransponderInfo(self.info, self.ref, f) if self.ref else self.getTransponderInfo(info, ref, f)
					ret += line[1:]
				return ret.replace("N/A", "").strip()

	text = property(getText)

	def neededChange(self):
		if self.what:
			Converter.changed(self, self.what)
			self.what = None

	def forceChanged(self, what):
		if what is True:
			self.refstr = self.isStream = self.ref = self.info = self.tpdata = None
			Converter.changed(self, (self.CHANGED_ALL,))
			self.what = None

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] in (iPlayableService.evStart,):
			self.refstr = self.isStream = self.ref = self.info = self.tpdata = None
			if self.type in (self.NUMBER, self.BOUQUET) or \
				(self.type == self.FORMAT and ("%n" in self.sfmt or "%B" in self.sfmt)):
				self.what = what
				self.Timer.start(200, True)
			else:
				Converter.changed(self, what)

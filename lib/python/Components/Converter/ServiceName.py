# -*- coding: utf-8 -*-
from Components.Converter.Converter import Converter
from Components.config import config
from enigma import iServiceInformation, iPlayableService, iPlayableServicePtr, eServiceReference, eEPGCache, eServiceCenter
from Components.Element import cached
from ServiceReference import resolveAlternate, ServiceReference
from Tools.Directories import fileExists
from Tools.Transponder import ConvertToHumanReadable
from Components.NimManager import nimmanager
from Components.Converter.ChannelNumbers import channelnumbers
import Screens.InfoBar

class ServiceName(Converter, object):
	NAME = 0
	NUMBER = 1

	NAME_ONLY = 2
	NAME_EVENT = 3
	PROVIDER = 4
	REFERENCE = 5
	EDITREFERENCE = 6
	TRANSPONDER = 7

	def __init__(self, type):
		Converter.__init__(self, type)
		self.epgQuery = eEPGCache.getInstance().lookupEventTime
		self.mode = ""
		if ';' in type:
			type, self.mode = type.split(';')
		if type == "Name" or not len(str(type)):
			self.type = self.NAME
		elif type == "Number":
			self.type = self.NUMBER
		elif type == "Provider":
			self.type = self.PROVIDER
		elif type == "Reference":
			self.type = self.REFERENCE
		elif type == "EditReference":
			self.type = self.EDITREFERENCE
		elif type == "NameOnly":
			self.type = self.NAME_ONLY
		elif type == "NameAndEvent":
			self.type = self.NAME_EVENT
		elif type == "TransponderInfo":
			self.type = self.TRANSPONDER
		else:
			self.type = self.NAME

		self.refstr = self.isStream = self.ref = self.info = self.what = self.tpdata = None
		self.IPTVcontrol = self.isAdditionalService(type=0)
		self.AlternativeControl = self.isAdditionalService(type=1)

	def isAdditionalService(self, type=0):
		def searchService(serviceHandler, bouquet):
			istype = False
			servicelist = serviceHandler.list(bouquet)
			if not servicelist is None:
				while True:
					s = servicelist.getNext()
					if not s.valid(): break
					if not (s.flags & (eServiceReference.isMarker|eServiceReference.isDirectory)):
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
			service_types_tv = '1:7:1:0:0:0:0:0:0:0:(type == 1) || (type == 17) || (type == 22) || (type == 25) || (type == 134) || (type == 195)'
			rootstr = '%s FROM BOUQUET "userbouquet.favourites.tv" ORDER BY bouquet'%(service_types_tv)
		else:
			rootstr = '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "bouquets.tv" ORDER BY bouquet'
		bouquet = eServiceReference(rootstr)
		if not config.usage.multibouquet.value:
			isService = searchService(serviceHandler, bouquet)
		else:
			bouquetlist = serviceHandler.list(bouquet)
			if not bouquetlist is None:
				while True:
					bouquet = bouquetlist.getNext()
					if not bouquet.valid(): break
					if bouquet.flags & eServiceReference.isDirectory:
						isService = searchService(serviceHandler, bouquet)
						if isService: break
		return isService 

	def getServiceNumber(self, ref):
		def searchHelper(serviceHandler, num, bouquet):
			servicelist = serviceHandler.list(bouquet)
			if not servicelist is None:
				while True:
					s = servicelist.getNext()
					if not s.valid(): break
					if not (s.flags & (eServiceReference.isMarker|eServiceReference.isDirectory)):
						num += 1
						if s == ref: return s, num
			return None, num

		if isinstance(ref, eServiceReference):
			isRadioService = ref.getData(0) in (2,10)
			lastpath = isRadioService and config.radio.lastroot.value or config.tv.lastroot.value
			if 'FROM BOUQUET' not in lastpath:
				if 'FROM PROVIDERS' in lastpath:
					return 'P', 'Provider'
				if 'FROM SATELLITES' in lastpath:
					return 'S', 'Satellites'
				if ') ORDER BY name' in lastpath:
					return 'A', 'All Services'
				return 0, 'N/A'
			try:
				acount = config.plugins.NumberZapExt.enable.value and config.plugins.NumberZapExt.acount.value or config.usage.alternative_number_mode.value
			except:
				acount = False
			rootstr = ''
			for x in lastpath.split(';'):
				if x != '': rootstr = x
			serviceHandler = eServiceCenter.getInstance()
			if acount is True or not config.usage.multibouquet.value:
				bouquet = eServiceReference(rootstr)
				service, number = searchHelper(serviceHandler, 0, bouquet)
			else:
				if isRadioService:
					bqrootstr = '1:7:2:0:0:0:0:0:0:0:FROM BOUQUET "bouquets.radio" ORDER BY bouquet'
				else:
					bqrootstr = '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "bouquets.tv" ORDER BY bouquet'
				number = 0
				cur = eServiceReference(rootstr)
				bouquet = eServiceReference(bqrootstr)
				bouquetlist = serviceHandler.list(bouquet)
				if not bouquetlist is None:
					while True:
						bouquet = bouquetlist.getNext()
						if not bouquet.valid(): break
						if bouquet.flags & eServiceReference.isDirectory:
							service, number = searchHelper(serviceHandler, number, bouquet)
							if not service is None and cur == bouquet: break
			if not service is None:
				info = serviceHandler.info(bouquet)
				name = info and info.getName(bouquet) or ''
				return number, name
		return 0, ''

	def getProviderName(self, ref):
		if isinstance(ref, eServiceReference):
			from Screens.ChannelSelection import service_types_radio, service_types_tv
			typestr = ref.getData(0) in (2,10) and service_types_radio or service_types_tv
			pos = typestr.rfind(':')
			rootstr = '%s (channelID == %08x%04x%04x) && %s FROM PROVIDERS ORDER BY name' %(typestr[:pos+1],ref.getUnsignedData(4),ref.getUnsignedData(2),ref.getUnsignedData(3),typestr[pos+1:])
			provider_root = eServiceReference(rootstr)
			serviceHandler = eServiceCenter.getInstance()
			providerlist = serviceHandler.list(provider_root)
			if not providerlist is None:
				while True:
					provider = providerlist.getNext()
					if not provider.valid(): break
					if provider.flags & eServiceReference.isDirectory:
						servicelist = serviceHandler.list(provider)
						if not servicelist is None:
							while True:
								service = servicelist.getNext()
								if not service.valid(): break
								if service == ref:
									info = serviceHandler.info(provider)
									return info and info.getName(provider) or "Unknown"
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

	@cached
	def getText(self):
		service = self.source.service
		if service is None:
			return ""

		if isinstance(service, iPlayableServicePtr):
			info = service and service.info()
			ref = None
		else: # reference
			info = service and self.source.info
			ref = service

		if not info:
			return ""

		if ref:
			refstr = ref.toString()
		else:
			refstr = info.getInfoString(iServiceInformation.sServiceref)
		if refstr is None:
			refstr = ''
		if self.AlternativeControl: 
			if ref and refstr.startswith("1:134:") and self.ref is None:
				nref = self.resolveAlternate(ref)
				if nref:
					self.ref = nref
					self.info = eServiceCenter.getInstance().info(self.ref)
					self.refstr = self.ref.toString()
					if not self.info: return ""
		if self.IPTVcontrol:
			if '%3a//' in refstr or (self.refstr and '%3a//' in self.refstr) or refstr.startswith("4097:"):
				self.isStream = True

		if self.type == self.NAME or self.type == self.NAME_ONLY or self.type == self.NAME_EVENT:
			name = ref and info.getName(ref)
			if name is None:
				name = info.getName()
			name = name.replace('\xc2\x86', '').replace('\xc2\x87', '')
			if self.type == self.NAME_EVENT:
				act_event = info and info.getEvent(0)
				if not act_event and info:
					refstr = info.getInfoString(iServiceInformation.sServiceref)
					act_event = self.epgQuery(eServiceReference(refstr), -1, 0)
				if act_event is None:
					return "%s - " % name
				else:
					return "%s - %s" % (name, act_event.getEventName())
			elif self.type != self.NAME_ONLY and config.usage.show_infobar_channel_number.value and hasattr(self.source, "serviceref") and self.source.serviceref and '0:0:0:0:0:0:0:0:0' not in self.source.serviceref.toString():
				numservice = self.source.serviceref
				num = numservice and numservice.getChannelNum() or None
				if num is not None:
					return str(num) + '   ' + name
				else:
					return name
			else:
				return name
		elif self.type == self.NUMBER:
			try:
				service = self.source.serviceref
				num = service and service.getChannelNum() or None
			except:
				num = None
			if num:
				return str(num)
			else:
				num, bouq = self.getServiceNumber(ref or eServiceReference(info.getInfoString(iServiceInformation.sServiceref)))
				return num and str(num) or ''
		elif self.type == self.PROVIDER:
			if self.isStream:
				if self.refstr and ('%3a//' in self.refstr or '%3a//' in self.refstr):
					return self.getIPTVProvider(self.refstr)
				return self.getIPTVProvider(refstr)
			else:
				if self.ref:
					return self.getProviderName(self.ref)
				if ref:
					return self.getProviderName(ref)
				else: 
					return info.getInfoString(iServiceInformation.sProvider) or ''
		elif self.type == self.REFERENCE or self.type == self.EDITREFERENCE and hasattr(self.source, "editmode") and self.source.editmode:
			if not ref:
				refstr = info.getInfoString(iServiceInformation.sServiceref)
				path = refstr and eServiceReference(refstr).getPath()
				if path and fileExists("%s.meta" % path):
					fd = open("%s.meta" % path, "r")
					refstr = fd.readline().strip()
					fd.close()
				return refstr
			nref = resolveAlternate(ref)
			if nref:
				ref = nref
			return ref.toString()
		elif self.type == self.TRANSPONDER:
			if ref:
				nref = resolveAlternate(ref)
				if nref:
					ref = nref
					info = eServiceCenter.getInstance().info(ref)
				transponder_info = info.getInfoObject(ref, iServiceInformation.sTransponderData)
			else:
				transponder_info = info.getInfoObject(iServiceInformation.sTransponderData)
			if "InRootOnly" in self.mode and not self.rootBouquet():
				return ""
			if "NoRoot" in self.mode and self.rootBouquet():
				return ""
			if transponder_info:
				self.t_info = ConvertToHumanReadable(transponder_info)
				if self.system() and "DVB-T" in self.system():
					return self.dvb_t()
				elif self.system() and "DVB-C" in self.system():
					return self.dvb_c()
				elif self.system() and "DVB-S" in self.system(): 
					return 	self.dvb_s()
				return ""
			if ref:
				result = ref.toString()
			else:
				result = info.getInfoString(iServiceInformation.sServiceref)
			if "%3a//" in result:
				return result.rsplit("%3a//", 1)[1].split("/")[0]
			return ""

	text = property(getText)

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] in (iPlayableService.evStart,):
			Converter.changed(self, what)

	def dvb_s(self):
		return "%s %s %s %s %s %s %s" % (self.orb_pos(), self.system(), self.freq(), self.polar(), self.s_rate(), self.fec(), self.mod())
	def dvb_t(self):
		return "%s %s %s/%s" % (self.system(), self.ch_number(), self.freq(), self.bandwidth())
	def dvb_c(self):
		return "%s %s %s %s %s" % (self.system(), self.freq(), self.s_rate(), self.fec(), self.mod())
	def system(self):
		return self.t_info["system"]
	def freq(self):
		return self.t_info["frequency"]
	def bandwidth(self):
		return self.t_info["bandwidth"]
	def s_rate(self):
		return self.t_info["symbol_rate"]
	def mod(self):
		return self.t_info["modulation"]
	def polar(self):
		return self.t_info["polarization_abbreviation"]
	def orb_pos(self):
		op = self.t_info["orbital_position"]
		if '(' in op:
			op = op.split('(')[1]
			return "%s°%s" % (op[:-2],op[-2:-1])
		op = op.split(' ')[0]
		return "%s°%s" % (op[:-1],op[-1:])
	def fec(self):
		return self.t_info["fec_inner"]
	def ch_number(self):
		for n in nimmanager.nim_slots:
			if n.isCompatible("DVB-T"):
				channel = channelnumbers.getChannelNumber(self.freq(), n.slot)
				if channel:
					return _("CH") + "%s" % channel
		return ""

	def rootBouquet(self):
		servicelist = Screens.InfoBar.InfoBar.instance.servicelist
		epg_bouquet = servicelist and 		list.getRoot()
		if ServiceReference(epg_bouquet).getServiceName():
			return False
		return True

from Components.Converter.Converter import Converter
from enigma import iServiceInformation, iPlayableService, eDVBCAHandler
from Components.Element import cached

class CryptoInfo(Converter, object):
	SOFTCAM = 1
	DECODEINFO = 2
	VERBOSEINFO = 3
	DECODETIME = 4
	USINGCARDID = 5
	HAS_SECA = 0x100
	HAS_VIACCESS = 0x500
	HAS_IRDETO = 0x600
	HAS_CONAX = 0xb00
	HAS_CRYPTOWORKS = 0xd00
	HAS_BETACRYPT = 0x1700
	HAS_NAGRA = 0x1800
	HAS_NDS = 0x900
	USING_SECA = HAS_SECA + 0x10000
	USING_VIACCESS = HAS_VIACCESS + 0x10000
	USING_IRDETO = HAS_IRDETO + 0x10000
	USING_CONAX = HAS_CONAX + 0x10000
	USING_CRYPTOWORKS = HAS_CRYPTOWORKS + 0x10000
	USING_BETACRYPT = HAS_BETACRYPT + 0x10000
	USING_NAGRA = HAS_NAGRA + 0x10000
	USING_NDS = HAS_NDS + 0x10000

	def __init__(self, type):
		Converter.__init__(self, type)
		options = {
				"SoftCam": self.SOFTCAM,
				"DecodeInfo": self.DECODEINFO,
				"VerboseInfo": self.VERBOSEINFO,
				"DecodeTime": self.DECODETIME,
				"UsingCardId": self.USINGCARDID,
				"HasSeca": self.HAS_SECA,
				"HasViaccess": self.HAS_VIACCESS,
				"HasIrdeto": self.HAS_IRDETO,
				"HasConax": self.HAS_CONAX,
				"HasCryptoworks": self.HAS_CRYPTOWORKS,
				"HasBetacrypt": self.HAS_BETACRYPT,
				"HasNagra": self.HAS_NAGRA,
				"HasNds": self.HAS_NDS,
				"UsingSeca": self.USING_SECA,
				"UsingViaccess": self.USING_VIACCESS,
				"UsingIrdeto": self.USING_IRDETO,
				"UsingConax": self.USING_CONAX,
				"UsingCryptoworks": self.USING_CRYPTOWORKS,
				"UsingBetacrypt": self.USING_BETACRYPT,
				"UsingNagra": self.USING_NAGRA,
				"UsingNds": self.USING_NDS,
			}
		events = {
				self.HAS_SECA: [iPlayableService.evUpdatedInfo],
				self.HAS_VIACCESS: [iPlayableService.evUpdatedEventInfo],
				self.HAS_IRDETO: [iPlayableService.evUpdatedInfo],
				self.HAS_CRYPTOWORKS: [iPlayableService.evUpdatedInfo],
				self.HAS_CONAX: [iPlayableService.evUpdatedEventInfo],
				self.HAS_BETACRYPT: [iPlayableService.evVideoSizeChanged],
				self.HAS_NAGRA: [iPlayableService.evUpdatedEventInfo],
				self.HAS_NDS: [iPlayableService.evUpdatedEventInfo],
			}

		self.type = options[type]
		self.active = False
		self.textvalue = ""

		if self.type == self.SOFTCAM:
			eDVBCAHandler.getCryptoInfo().clientname.get().append(self.clientName)
		if self.type == self.DECODEINFO:
			eDVBCAHandler.getCryptoInfo().clientinfo.get().append(self.clientInfo)
		elif self.type == self.VERBOSEINFO:
			eDVBCAHandler.getCryptoInfo().verboseinfo.get().append(self.verboseInfo)
		elif self.type == self.DECODETIME:
			eDVBCAHandler.getCryptoInfo().decodetime.get().append(self.decodeTime)
		elif self.type == self.USINGCARDID:
			eDVBCAHandler.getCryptoInfo().usingcardid.get().append(self.usingCardId)
		elif self.type > 0x10000:
			eDVBCAHandler.getCryptoInfo().usedcaid.get().append(self.caidChanged)
		else:
			self.interesting_events = events[self.type]

	@cached
	def getBoolean(self):
		service = self.source.service
		info = service and service.info()
		if not info:
			return False

		if self.type < 0x10000:
			caids = info.getInfoObject(iServiceInformation.sCAIDs)
			for caid in caids:
				caid &= 0xff00
			return self.type in caids
		else:
			return self.active

	boolean = property(getBoolean)

	@cached
	def getText(self):
		return self.textvalue

	text = property(getText)

	def changed(self, what):
		if self.type >= self.HAS_SECA and self.type < 0x10000:
			if what[0] != self.CHANGED_SPECIFIC or what[1] in self.interesting_events:
				Converter.changed(self, what)

	def caidChanged(self, caid):
		oldactive = self.active
		caid &= 0xff00
		if self.type == (caid + 0x10000):
			self.active = True
		else:
			self.active = False
		if self.active != oldactive:
			Converter.changed(self, (self.CHANGED_ALL,))

	def decodeTime(self, time):
		self.textvalue = "%01d.%03d" % (time/1000, time%1000)
		if self.type == self.DECODETIME:
			Converter.changed(self, (self.CHANGED_ALL,))

	def clientName(self, name):
		if self.type == self.SOFTCAM:
			self.textvalue = name
			Converter.changed(self, (self.CHANGED_ALL,))

	def clientInfo(self, name):
		if self.type == self.DECODEINFO:
			self.textvalue = name
			Converter.changed(self, (self.CHANGED_ALL,))

	def verboseInfo(self, info):
		if self.type == self.VERBOSEINFO:
			self.textvalue = info
			Converter.changed(self, (self.CHANGED_ALL,))

	def usingCardId(self, info):
		if self.type == self.USINGCARDID:
			self.textvalue = info
			Converter.changed(self, (self.CHANGED_ALL,))

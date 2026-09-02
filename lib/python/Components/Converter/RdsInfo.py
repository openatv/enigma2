from enigma import iRdsDecoder, iPlayableService
from Components.Converter.Converter import Converter
from Components.Element import cached


class RdsInfo(Converter):
	RASS_INTERACTIVE_AVAILABLE = 0
	RTP_TEXT_CHANGED = 1
	RADIO_TEXT_CHANGED = 2
	RTP_TEXT_WITHOUT_EVENT = 3
	RADIO_TEXT_WITHOUT_CURRENT_EVENT = 4

	def __init__(self, type):
		Converter.__init__(self, type)
		self.type, self.interesting_events = {
				"RadioText": (self.RADIO_TEXT_CHANGED, (iPlayableService.evUpdatedRadioText,)),
				"RtpText": (self.RTP_TEXT_CHANGED, (iPlayableService.evUpdatedRtpText,)),
				"RadioTextIfNoEvent": (self.RADIO_TEXT_WITHOUT_CURRENT_EVENT, (iPlayableService.evUpdatedRadioText, iPlayableService.evUpdatedEventInfo)),
				"RtpTextIfNoEvent": (self.RTP_TEXT_WITHOUT_EVENT, (iPlayableService.evUpdatedRtpText, iPlayableService.evUpdatedEventInfo)),
				"RasInteractiveAvailable": (self.RASS_INTERACTIVE_AVAILABLE, (iPlayableService.evUpdatedRassInteractivePicMask,))
			}[type]

	def hasEvent(self, index):
		service = self.source.navcore.getCurrentService()
		info = service and service.info()
		return bool(info and info.getEvent(index))

	@cached
	def getText(self):
		decoder = self.source.decoder
		text = ""
		if decoder:
			if self.type in (self.RADIO_TEXT_CHANGED, self.RADIO_TEXT_WITHOUT_CURRENT_EVENT):
				if self.type == self.RADIO_TEXT_CHANGED or not self.hasEvent(0):
					text = decoder.getText(iRdsDecoder.RadioText)
			elif self.type in (self.RTP_TEXT_CHANGED, self.RTP_TEXT_WITHOUT_EVENT):
				if self.type == self.RTP_TEXT_CHANGED or not self.hasEvent(0):
					text = decoder.getText(iRdsDecoder.RtpText)
			else:
				print("[RdsInfo] unknown RdsInfo Converter type", self.type)
		return text

	text = property(getText)

	@cached
	def getBoolean(self):
		decoder = self.source.decoder
		if self.type == self.RASS_INTERACTIVE_AVAILABLE:
			mask = decoder and decoder.getRassInteractiveMask()
			return (mask and mask[0] & 1 and True) or False
		elif self.type == self.RADIO_TEXT_CHANGED or self.type == self.RADIO_TEXT_WITHOUT_CURRENT_EVENT:
			return bool(decoder and not (self.type == self.RADIO_TEXT_WITHOUT_CURRENT_EVENT and self.hasEvent(0)) and decoder.getText(iRdsDecoder.RadioText))
		elif self.type == self.RTP_TEXT_CHANGED or self.type == self.RTP_TEXT_WITHOUT_EVENT:
			return bool(decoder and not (self.type == self.RTP_TEXT_WITHOUT_EVENT and self.hasEvent(0)) and decoder.getText(iRdsDecoder.RtpText))
	boolean = property(getBoolean)

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] in self.interesting_events:
			Converter.changed(self, what)

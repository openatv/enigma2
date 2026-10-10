from enigma import iPlayableService, iRdsDecoder

from Components.Converter.Converter import Converter
from Components.Element import cached


class RdsInfo(Converter):
	RASS_INTERACTIVE_AVAILABLE = 0
	RTP_TEXT_CHANGED = 1
	RADIO_TEXT_CHANGED = 2
	RTP_TEXT_WITHOUT_EVENT = 3
	RADIO_TEXT_WITHOUT_CURRENT_EVENT = 4

	def __init__(self, tokens):
		Converter.__init__(self, tokens)
		self.type, self.interesting_events = {
			"RadioText": (self.RADIO_TEXT_CHANGED, (iPlayableService.evUpdatedRadioText,)),
			"RadioTextIfNoEvent": (self.RADIO_TEXT_WITHOUT_CURRENT_EVENT, (iPlayableService.evUpdatedRadioText, iPlayableService.evUpdatedEventInfo)),
			"RasInteractiveAvailable": (self.RASS_INTERACTIVE_AVAILABLE, (iPlayableService.evUpdatedRassInteractivePicMask,)),
			"RtpText": (self.RTP_TEXT_CHANGED, (iPlayableService.evUpdatedRtpText,)),
			"RtpTextIfNoEvent": (self.RTP_TEXT_WITHOUT_EVENT, (iPlayableService.evUpdatedRtpText, iPlayableService.evUpdatedEventInfo))
		}[tokens]

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] in self.interesting_events:
			Converter.changed(self, what)

	@cached
	def getBoolean(self):
		result = None
		decoder = self.source.decoder
		match self.type:
			case self.RADIO_TEXT_CHANGED | self.RADIO_TEXT_WITHOUT_CURRENT_EVENT:
				result = bool(decoder and not (self.type == self.RADIO_TEXT_WITHOUT_CURRENT_EVENT and self.hasEvent(0)) and decoder.getText(iRdsDecoder.RadioText))
			case self.RASS_INTERACTIVE_AVAILABLE:
				mask = decoder and decoder.getRassInteractiveMask()
				result = bool(mask and mask[0] & 1)
			case self.RTP_TEXT_CHANGED | self.RTP_TEXT_WITHOUT_EVENT:
				result = bool(decoder and not (self.type == self.RTP_TEXT_WITHOUT_EVENT and self.hasEvent(0)) and decoder.getText(iRdsDecoder.RtpText))
		return result

	boolean = property(getBoolean)

	@cached
	def getText(self):
		text = ""
		decoder = self.source.decoder
		if decoder:
			match self.type:
				case self.RADIO_TEXT_CHANGED | self.RADIO_TEXT_WITHOUT_CURRENT_EVENT:
					if self.type == self.RADIO_TEXT_CHANGED or not self.hasEvent(0):
						text = decoder.getText(iRdsDecoder.RadioText)
				case self.RTP_TEXT_CHANGED | self.RTP_TEXT_WITHOUT_EVENT:
					if self.type == self.RTP_TEXT_CHANGED or not self.hasEvent(0):
						text = decoder.getText(iRdsDecoder.RtpText)
				case _:
					print(f"[RdsInfo] Unknown RdsInfo converter type {self.type}.")
		return text

	text = property(getText)

	def hasEvent(self, index):
		service = self.source.navcore.getCurrentService()
		info = service and service.info()
		return bool(info and info.getEvent(index))

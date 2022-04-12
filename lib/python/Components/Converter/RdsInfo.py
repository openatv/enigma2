from __future__ import print_function
from enigma import iRdsDecoder, iPlayableService
from Components.Converter.Converter import Converter
from Components.Element import cached


class RdsInfo(Converter):
	RASS_INTERACTIVE_AVAILABLE = 0
	RTP_TEXT_CHANGED = 1
	RADIO_TEXT_CHANGED = 2

	def __init__(self, type):
		Converter.__init__(self, type)
		self.type, self.interesting_events = {
				"RadioText": (self.RADIO_TEXT_CHANGED, (iPlayableService.evUpdatedRadioText,)),
				"RtpText": (self.RTP_TEXT_CHANGED, (iPlayableService.evUpdatedRtpText,)),
				"RasInteractiveAvailable": (self.RASS_INTERACTIVE_AVAILABLE, (iPlayableService.evUpdatedRassInteractivePicMask,))
			}[type]

	@cached
	def getText(self):
		decoder = self.source.decoder
		text = ""
		if decoder:
			if self.type == self.RADIO_TEXT_CHANGED:
				text = decoder.getText(iRdsDecoder.RadioText)
			elif self.type == self.RTP_TEXT_CHANGED:
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
		elif self.type == self.RADIO_TEXT_CHANGED:
			return (len(decoder.getText(iRdsDecoder.RadioText)) and True) or False
		elif self.type == self.RTP_TEXT_CHANGED:
			return (len(decoder.getText(iRdsDecoder.RtpText)) and True) or False
	boolean = property(getBoolean)

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] in self.interesting_events:
			Converter.changed(self, what)

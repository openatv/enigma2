from Components.Converter.Converter import Converter
from Components.Element import cached

class FrontendInfo(Converter, object):
	BER = 0
	SNR = 1
	AGC = 2
	LOCK = 3
	SNRdB = 4

	def __init__(self, type):
		Converter.__init__(self, type)
		if type == "BER":
			self.type = self.BER
		elif type == "SNR":
			self.type = self.SNR
		elif type == "SNRdB":
			self.type = self.SNRdB
		elif type == "AGC":
			self.type = self.AGC
		else:
			self.type = self.LOCK

	@cached
	def getText(self):
		assert self.type != self.LOCK, "the text output of FrontendInfo cannot be used for lock info"
		percent = None
		if self.type == self.BER: # as count
			count = self.source.ber
			if count is not None:
				return str(count)
			else:
				return "N/A"
		elif self.type == self.AGC:
			percent = self.source.agc
		elif self.type == self.SNR:
			percent = self.source.snr
		elif self.type == self.SNRdB:
			if self.source.snr_db is not None:
				return "%3.02f dB" % (self.source.snr_db / 100.0)
			elif self.source.snr is not None: #fallback to normal SNR...
				percent = self.source.snr
				return "SNR:%d %%" % (percent * 100 / 65536)
		if percent is None:
			return "N/A"

		return "%d %%" % (percent * 100 / 65536)

	@cached
	def getBool(self):
		assert self.type in [self.LOCK, self.BER], "the boolean output of FrontendInfo can only be used for lock or BER info"
		if self.type == self.LOCK:
			return self.source.lock
		else:
			return self.source.ber > 0

	text = property(getText)

	boolean = property(getBool)

	@cached
	def getValue(self):
		assert self.type != self.LOCK, "the value/range output of FrontendInfo can not be used for lock info"
		if self.type == self.AGC:
			return self.source.agc or 0
		elif self.type == self.SNR:
			return self.source.snr or 0
		elif self.type == self.BER:
			if self.BER < self.range:
				return self.BER or 0
			else:
				return self.range

	range = 65536
	value = property(getValue)

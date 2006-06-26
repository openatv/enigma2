from Components.Converter.Converter import Converter

class FrontendInfo(Converter, object):
	BER = 0
	SNR = 1
	AGC = 2
	LOCK = 3

	def __init__(self, type, *args, **kwargs):
		Converter.__init__(self)
		if type == "BER":
			self.type = self.BER
		elif type == "SNR":
			self.type = self.SNR
		elif type == "AGC":
			self.type = self.AGC
		else:
			self.type = self.LOCK

	def getText(self):
		assert self.type != self.LOCK, "the text output of FrontendInfo cannot be used for lock info"
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
		
		if percent is None:
			return "N/A"

		return "%d %%" % (percent * 100 / 65536)

	def getBool(self):
		assert self.type == LOCK, "the boolean output of FrontendInfo can only be used for lock info"
		return self.source.lock

	text = property(getText)

	boolean = property(getBool)

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

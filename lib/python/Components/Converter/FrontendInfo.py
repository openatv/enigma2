from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.config import config
from Components.NimManager import nimmanager

class FrontendInfo(Converter, object):
	BER = 0
	SNR = 1
	AGC = 2
	LOCK = 3
	SNRdB = 4
	SLOT_NUMBER = 5
	TUNER_TYPE = 6
	STRING = 7

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
		elif type == "NUMBER":
			self.type = self.SLOT_NUMBER
		elif type == "TYPE":
			self.type = self.TUNER_TYPE
		elif type.startswith("STRING"):
			self.type = self.STRING
			type = type.split(",")
			self.space_for_tuners = len(type) > 1 and int(type[1]) or 10
			self.space_for_tuners_with_spaces = len(type) > 2 and int(type[2]) or 6
		else:
			self.type = self.LOCK

	@cached
	def getText(self):
		assert self.type not in (self.LOCK, self.SLOT_NUMBER), "the text output of FrontendInfo cannot be used for lock info"
		percent = None
		swapsnr = config.usage.swap_snr_on_osd.value
		if self.type == self.BER: # as count
			count = self.source.ber
			if count is not None:
				return str(count)
			else:
				return "N/A"
		elif self.type == self.AGC:
			percent = self.source.agc
		elif (self.type == self.SNR and not swapsnr) or (self.type == self.SNRdB and swapsnr):
			percent = self.source.snr
		elif self.type  == self.SNR or self.type == self.SNRdB:
			if self.source.snr_db is not None:
				return "%3.01f dB" % (self.source.snr_db / 100.0)
			elif self.source.snr is not None: #fallback to normal SNR...
				percent = self.source.snr
		elif self.type == self.TUNER_TYPE:
			return self.source.frontend_type and self.frontend_type or "Unknown"
		elif self.type == self.STRING:
			string = ""
			for n in nimmanager.nim_slots:
				if n.type:
					if n.slot == self.source.slot_number:
						color = "\c0000??00"
					elif self.source.tuner_mask & 1 << n.slot:
						color = "\c00??????"
					elif len(nimmanager.nim_slots) <= self.space_for_tuners:
						color = "\c007?7?7?"
					else:
						continue
					if string and len(nimmanager.nim_slots) <= self.space_for_tuners_with_spaces:
						string += " "
					string += color + chr(ord("A")+n.slot)
			return string
		if percent is None:
			return "N/A"
		return "%d %%" % (percent * 100 / 65536)

	@cached
	def getBool(self):
		assert self.type in (self.LOCK, self.BER), "the boolean output of FrontendInfo can only be used for lock or BER info"
		if self.type == self.LOCK:
			lock = self.source.lock
			if lock is None:
				lock = False
			return lock
		else:
			ber = self.source.ber
			if ber is None:
				ber = 0
			return ber > 0

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
		elif self.type == self.TUNER_TYPE:
			type = self.source.frontend_type
			if type == 'DVB-S':
				return 0
			elif type == 'DVB-C':
				return 1
			elif type == 'DVB-T':
				return 2
			elif type == 'ATSC':
				return 3
			return -1
		elif self.type == self.SLOT_NUMBER:
			num = self.source.slot_number
			return num is None and -1 or num

	range = 65536
	value = property(getValue)

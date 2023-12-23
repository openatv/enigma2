from Components.config import config
from Components.Element import cached
from Components.NimManager import nimmanager
from Components.Converter.Converter import Converter
import NavigationInstance


class FrontendInfo(Converter):
	BER = 0
	SNR = 1
	AGC = 2
	LOCK = 3
	SNRdB = 4
	SLOT_NUMBER = 5
	TUNER_TYPE = 6
	STRING = 7
	REC_TUNER = 8

	def __init__(self, type):
		Converter.__init__(self, type)

		if type.startswith("STRING"):
			self.type = self.STRING
			type = type.split(",")
			self.space_for_tuners = len(type) > 1 and int(type[1]) or 10
			self.space_for_tuners_with_spaces = len(type) > 2 and int(type[2]) or 6
		elif type.split("_")[0] == "REC":
			self.type = self.REC_TUNER
			self.tunernum = int(type.split("_")[1])
		else:
			self.type = {
				"BER": self.BER,
				"SNR": self.SNR,
				"SNRdB": self.SNRdB,
				"AGC": self.AGC,
				"NUMBER": self.SLOT_NUMBER,
				"TYPE": self.TUNER_TYPE
			}.get(type, self.LOCK)

	@cached
	def getText(self):
		assert self.type not in (self.LOCK, self.SLOT_NUMBER), "the text output of FrontendInfo cannot be used for lock info"
		percent = None
		swapsnr = config.usage.swap_snr_on_osd.value
		if self.type == self.BER:  # as count
			count = self.source.ber
			return str(count) if count is not None else "N/A"
		elif self.type == self.AGC:
			percent = self.source.agc
		elif (self.type == self.SNR and not swapsnr) or (self.type == self.SNRdB and swapsnr):
			percent = self.source.snr
		elif self.type == self.SNR or self.type == self.SNRdB:
			if self.source.snr_db is not None:
				return "%3.01f dB" % (self.source.snr_db / 100.0)
			elif self.source.snr is not None:  # fallback to normal SNR...
				percent = self.source.snr
		elif self.type == self.TUNER_TYPE:
			return self.source.frontend_type or _("Unknown")
		elif self.type == self.STRING:
			string = ""
			for n in nimmanager.nim_slots:
				if n.type:
					if n.slot == self.source.slot_number:
						color = r"\c0000ff00"
					elif self.source.tuner_mask & 1 << n.slot:
						color = r"\c00ffffff"
					elif len(nimmanager.nim_slots) <= self.space_for_tuners:
						color = r"\c007f7f7f"
					else:
						continue
					if string and len(nimmanager.nim_slots) <= self.space_for_tuners_with_spaces:
						string += " "
					string += color + chr(ord("A") + n.slot)
			return string
		if percent is None:
			return "N/A"
		return f"{int(percent * 100 / 65536)} %"

	@cached
	def getBool(self):
		assert self.type in (self.LOCK, self.BER, self.REC_TUNER), "the boolean output of FrontendInfo can only be used for lock or BER info or Tuner-Rec"
		if self.type == self.LOCK:
			return self.source.lock or False
		elif self.type == self.REC_TUNER:
			for timer in NavigationInstance.instance.RecordTimer.timer_list:
				if timer.isRunning() and not timer.justplay:
					service = timer.record_service
					feinfo = service and service.frontendInfo()
					data = feinfo and feinfo.getFrontendData()
					if data:
						tuner = data.get('tuner_number', -1)
						if tuner is not None and tuner > -1 and tuner == self.tunernum:
							return True
			return False
		else:
			return (self.source.ber or 0) > 0

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
			ber = self.source.ber or 0
			return self.range if ber > self.range else ber
		elif self.type == self.TUNER_TYPE:
			return {
				"DVB-S": 0,
				"DVB-C": 1,
				"DVB-T": 2,
				"ATSC": 3
			}.get(self.source.frontend_type, -1)
		elif self.type == self.SLOT_NUMBER:
			num = self.source.slot_number
			return num is None and -1 or num

	range = 65536
	value = property(getValue)

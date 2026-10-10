from urllib.parse import urlsplit
from skin import parseColor
from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.NimManager import nimmanager
from Components.config import config
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
	TUNERS = 9
	SNR_STREAM = 10

	range = 65536

	def __init__(self, tokens):
		def checkColor(color, default):
			if color in ("", "Default"):
				color = default
			return None if color == "None" else rf"\c{parseColor(color, default).argb():08X}"

		Converter.__init__(self, tokens)
		if tokens.startswith("STRING"):  # "STRING[,spaceForTuners[,spaceForTunersWithSpaces]]"
			self.type = self.STRING
			data = [x.strip() for x in tokens.split(",")]
			self.spaceForTuners = len(data) > 1 and int(data[1]) or 10
			self.spaceForTunersWithSpaces = len(data) > 2 and int(data[2]) or 6
		elif tokens.startswith("TUNERS"):  # "TUNERS[,idleColor[,activeColor[,recordingColor[,disabledColor[,spacer]]]]]"
			self.type = self.TUNERS
			data = [x.strip() for x in tokens.split(",", 5)]
			self.idleColor = checkColor(data[1], "#00CFCFCF") if len(data) > 1 and data[1] else r"\c00CFCFCF"
			self.activeColor = checkColor(data[2], "#0000FF00") if len(data) > 2 and data[2] else r"\c0000FF00"
			self.recordingColor = checkColor(data[3], "#00FF0000") if len(data) > 3 and data[3] else r"\c00FF0000"
			self.disabledColor = checkColor(data[4], "#006F6F6F") if len(data) > 4 and data[4] else r"\c006F6F6F"
			if len(data) > 5 and data[5]:
				spacer = data[5]
				self.spacer = spacer[1:-1] if len(spacer) > 1 and spacer[0] == spacer[-1] else spacer
			else:
				self.spacer = " "
		elif tokens.split("_")[0] == "REC":
			self.type = self.REC_TUNER
			self.tunerNum = int(tokens.split("_")[1])
		else:
			self.type = {
				"AGC": self.AGC,
				"BER": self.BER,
				"NUMBER": self.SLOT_NUMBER,
				"SNR": self.SNR,
				"SNRStream": self.SNR_STREAM,
				"SNRdB": self.SNRdB,
				"TYPE": self.TUNER_TYPE
			}.get(tokens, self.LOCK)
		self.recordTimer = None
		if self.type in (self.TUNERS, self.REC_TUNER) and NavigationInstance.instance:
			self.recordTimer = NavigationInstance.instance.RecordTimer
			self.recordTimer.on_state_change.append(self.recordTimerStateChanged)

	def destroy(self):
		if self.recordTimer:
			self.recordTimer.on_state_change.remove(self.recordTimerStateChanged)
			self.recordTimer = None

	def getAGC(self):
		agc = self.source.agc
		result = agc
		# Si2166D/Si2169D frontends report a small bogus non-zero AGC value (seen: 89-124) instead of None.
		# Ignore it and estimate a display value from the signal quality, also when the frontend has no AGC.
		if not (agc and agc > 255):
			snr = self.source.snr
			if snr:
				snrPercent = snr * 100.0 / 65535.0
				if snrPercent < 35:
					agcPercent = snrPercent * 1.8
				elif snrPercent < 70:
					agcPercent = 63 + ((snrPercent - 35) * 0.8)
				else:
					agcPercent = 91 + ((snrPercent - 70) * 0.3)
				result = round(min(100, agcPercent) * self.range / 100.0)  # In this case round() returns an integer.
		return result

	@cached
	def getBool(self):
		assert self.type in (self.LOCK, self.BER, self.REC_TUNER), "the boolean output of FrontendInfo can only be used for lock or BER info or Tuner-Rec"
		match self.type:
			case self.LOCK:
				result = self.source.lock or False
			case self.REC_TUNER:
				result = self.tunerNum in self.getRecordingTuners()
			case _:
				result = (self.source.ber or 0) > 0
		return result

	boolean = property(getBool)

	@cached
	def getRecordingTuners(self):
		tuners = set()
		if self.recordTimer:
			for timer in self.recordTimer.timer_list:
				if timer.isRunning() and not timer.justplay:
					service = timer.record_service
					feInfo = service and service.frontendInfo()
					feData = feInfo and feInfo.getFrontendData()
					tuner = feData.get("tuner_number", -1) if feData else -1
					if tuner is not None and tuner > -1:
						tuners.add(tuner)
		return tuners

	@cached
	def getText(self):
		assert self.type not in (self.LOCK, self.SLOT_NUMBER), "the text output of FrontendInfo cannot be used for lock info"
		text = None
		# Opt-in InfoBar display; ordinary SNR widgets (e.g. Satfinder) stay unchanged.
		prefix = "SNR: " if self.type == self.SNR_STREAM else ""
		if self.type == self.SNR_STREAM:
			nav = NavigationInstance.instance
			ref = nav.getCurrentlyPlayingServiceReference() if nav else None
			if ref:
				# DVB-I supplies verified format hints. Other IPTV services can only
				# be labeled by their URL; never probe a stream from the UI.
				if getattr(nav, "isCurrentServiceDVBI", False):
					streamType = {0x100: "DASH", 0x200: "HLS"}.get(ref.getUnsignedData(7) & 0x300, "DVB-I")
					text = f"IP: {streamType}"
				else:
					try:
						address = urlsplit(ref.getPath())
					except ValueError:
						address = None
					if address and address.scheme.lower() in ("http", "https", "rtsp", "rtsps", "rtmp", "rtmps", "rtp", "udp", "srt", "mms", "mmsh", "mmst"):
						path = address.path.lower()
						streamType = "DASH" if path.endswith(".mpd") else "HLS" if path.endswith(".m3u8") else "Stream"
						text = f"IP: {streamType}"
		if text is None:
			percent = None
			snrSwap = config.usage.swap_snr_on_osd.value
			match self.type:
				case self.AGC:
					percent = self.getAGC()
				case self.BER:  # As count.
					count = self.source.ber
					text = _("N/A") if count is None else str(count)
				case self.SNR | self.SNR_STREAM if not snrSwap:
					percent = self.source.snr
				case self.SNRdB if snrSwap:
					percent = self.source.snr
				case self.SNR | self.SNRdB | self.SNR_STREAM if self.source.snr_db is not None:
					text = f"{prefix}{self.source.snr_db / 100.0:3.1f} dB"
				case self.SNR | self.SNRdB | self.SNR_STREAM:  # Fallback to normal SNR.
					percent = self.source.snr
				case self.STRING:
					tuners = []
					count = len(nimmanager.nim_slots)
					for slot in [x for x in nimmanager.nim_slots if x.type]:
						if slot.slot == self.source.slot_number:
							color = r"\c0000FF00"
						elif self.source.tuner_mask & 1 << slot.slot:
							color = r"\c00FFFFFF"
						elif count <= self.spaceForTuners:
							color = r"\c007F7F7F"
						else:
							continue
						tuners.append(f"{color}{chr(ord('A') + slot.slot)}")
					text = " ".join(tuners) if tuners and count <= self.spaceForTunersWithSpaces else "".join(tuners)
				case self.TUNERS:
					recordingTuners = self.getRecordingTuners() if self.recordingColor and self.recordingColor != self.activeColor else ()
					tuners = []
					for slot in nimmanager.nim_slots:
						if self.recordingColor and slot.slot in recordingTuners:
							color = self.recordingColor
						elif self.activeColor and self.source.tuner_mask & 1 << slot.slot:
							color = self.activeColor
						elif self.idleColor and slot.isEnabled():
							color = self.idleColor
						elif self.disabledColor and not slot.isEnabled():
							color = self.disabledColor
						else:
							color = None
						if color:
							tuners.append(rf"{color}{chr(ord('A') + slot.slot)}\C")
					text = self.spacer.join(tuners)
				case self.TUNER_TYPE:
					text = self.source.frontend_type or _("Unknown")
			if text is None:
				text = f"{prefix}{_('N/A') if percent is None else f'{percent * 100 // 65536}%'}"
		return text

	text = property(getText)

	@cached
	def getValue(self):
		assert self.type != self.LOCK, "the value/range output of FrontendInfo can not be used for lock info"
		match self.type:
			case self.AGC:
				result = self.getAGC() or 0
			case self.BER:
				ber = self.source.ber or 0
				result = self.range if ber > self.range else ber
			case self.SLOT_NUMBER:
				num = self.source.slot_number
				result = -1 if num is None else num
			case self.SNR:
				result = self.source.snr or 0
			case self.TUNER_TYPE:
				result = {
					"ATSC": 3,
					"DVB-C": 1,
					"DVB-S": 0,
					"DVB-T": 2
				}.get(self.source.frontend_type, -1)
			case _:
				result = None
		return result

	value = property(getValue)

	def recordTimerStateChanged(self, timer):
		self.changed((self.CHANGED_ALL,))

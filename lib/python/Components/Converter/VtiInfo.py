from enigma import iPlayableService, iServiceInformation

from Components.Converter.Converter import Converter
from Components.Converter.Poll import Poll
from Components.Element import cached
from Components.config import config


class VtiInfo(Poll, Converter):
	ECMINFO = 1
	ONLINETEST = 21
	TEMPINFO = 22
	FANINFO = 23
	ALL = 24

	def __init__(self, tokens):
		Poll.__init__(self)
		Converter.__init__(self, tokens)
		self.poll_interval = 2000
		self.poll_enabled = True
		self.type = {
			"EcmInfo": self.ECMINFO,
			"FanInfo": self.FANINFO,
			"OnlineTest": self.ONLINETEST,
			"TempInfo": self.TEMPINFO
		}.get(tokens, self.ALL)

	def changed(self, what):
		if what[0] == self.CHANGED_SPECIFIC and what[1] == iPlayableService.evUpdatedInfo or what[0] == self.CHANGED_POLL:
			Converter.changed(self, what)

	def ecmfile(self):
		info = {}
		ecm = None
		service = self.source.service
		if service:
			frontendInfo = service.frontendInfo()
			if frontendInfo:
				try:
					with open(f"/tmp/ecm{frontendInfo.getAll(False).get('tuner_number')}.info") as fd:
						ecm = fd.readlines()
				except Exception:
					try:
						with open("/tmp/ecm.info") as fd:
							ecm = fd.readlines()
					except OSError:
						pass
			for line in ecm or ():
				index = line.lower().find("msec")
				if index != -1:
					info["ecm time"] = line[0:index + 4]
				else:
					item = line.split(":", 1)
					if len(item) > 1:
						info[item[0].strip().lower()] = item[1].strip()
					elif "caid" not in info:
						start = line.lower().find("caid")
						if start != -1:
							end = line.find(",")
							if end != -1:
								info["caid"] = line[start + 5:end]
			if info.get("from") and config.softcam.hideServerName.value:
				info["from"] = "•" * len(info["from"])
		return info

	def fanfile(self):
		text = None
		try:
			with open("/proc/stb/fp/fan_speed") as fd:
				text = f"FAN: {fd.readline().strip()}"
		except OSError:
			pass
		return text

	@cached
	def getBoolean(self):
		return self.pingtest() if self.type == self.ONLINETEST else False

	boolean = property(getBoolean)

	@cached
	def getText(self):
		text = ""
		service = self.source.service
		if service:
			info = service.info()
			match self.type:
				case self.ECMINFO:
					if config.misc.ecm_info.value and info and info.getInfoObject(iServiceInformation.sCAIDs):
						ecmInfo = self.ecmfile()
						if ecmInfo:
							caid = f"CAID: {ecmInfo.get('caid', '').lstrip('0x').upper().zfill(4)}"
							hops = f"HOPS: {ecmInfo.get('hops')}"
							ecmTime = ecmInfo.get("ecm time")
							if ecmTime:
								ecmTime = f"TIME: {ecmTime} ms" if "msec" in ecmTime else f"TIME: {ecmTime} s"
							using = ecmInfo.get("using", "")
							if using:
								text = f"{caid} - {ecmTime}" if using == "emu" else f"{caid} - {ecmInfo.get('address', '')} - {hops} - {ecmTime}"
							else:
								source = ecmInfo.get("source")
								if source:
									text = caid if source == "emu" else f"{caid} - {source} - {ecmTime}"
								oscSource = ecmInfo.get("from")
								if oscSource:
									text = f"{caid} - {oscSource} - {hops} - {ecmTime}"
								decode = ecmInfo.get("decode")
								if decode:
									text = f"{caid} - {decode} - RESPONSE: {ecmInfo.get('response')} ms - PROVIDER: {ecmInfo.get('provider')}"
				case self.FANINFO:
					text = self.fanfile()
				case self.TEMPINFO:
					text = self.tempfile()
		return text

	text = property(getText)

	def pingtest(self):
		result = False
		try:
			with open("/tmp/.pingtest.info") as fd:
				lines = fd.readlines()
			result = bool(lines) and lines[-1].startswith("0")
		except OSError:
			pass
		return result

	def tempfile(self):
		text = None
		try:
			with open("/proc/stb/sensors/temp0/value") as fd:
				temp = fd.readline().strip()
			with open("/proc/stb/sensors/temp0/unit") as fd:
				unit = fd.readline().strip()
			text = f"TEMP: {temp} °{unit}"
		except Exception:
			pass
		return text

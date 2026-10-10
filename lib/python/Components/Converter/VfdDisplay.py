from datetime import datetime

from enigma import iPlayableService

from Components.Converter.Converter import Converter
from Components.Converter.Poll import Poll
from Components.Element import cached
from Components.config import configfile


class VfdDisplay(Poll, Converter):
	def __init__(self, tokens):
		Converter.__init__(self, tokens)
		Poll.__init__(self)
		self.num = None
		self.showclock = 0
		self.delay = 5000
		self.loop = -1
		self.type = tokens.lower().split(";")
		configValue = None
		for value in self.type:
			if value.startswith("config."):
				configValue = configfile.getResolvedKey(value, silent=True)  # Invalid/non-existent keys will return None.
				break
		if configValue == "nothing":
			self.delay = 0
			self.type = ["nothing"]
		else:
			match configValue:
				case "number":
					self.type = ["number"]
				case "time":
					self.type = []
			if "number" in self.type and "clock" not in self.type:  # Only channel number.
				self.delay = 0
				self.poll_enabled = False
			else:
				self.poll_enabled = True
				if "clock" in self.type and "number" not in self.type:  # Only clock.
					self.showclock = 1
					self.delay = -1
				else:
					for value in self.type:
						if value.isdigit():
							self.delay = int(value) * 1000
							break
					if "loop" in self.type and self.delay:
						self.loop = self.delay
				self.hour = {
					(False, False): "%H",
					(False, True): "%k",
					(True, False): "%I",
					(True, True): "%l"
				}[("12h" in self.type, "nozero" in self.type)]

	def changed(self, what):
		if what[0] is self.CHANGED_SPECIFIC and (what[1] in (iPlayableService.evStart, iPlayableService.evEnd, iPlayableService.evNewProgramInfo)) and self.delay >= 0:
			self.showclock = 0
			if self.loop != -1:
				self.loop = self.delay
			service = self.source.serviceref
			if service:
				channelNum = service.getChannelNum()
				self.num = f"{channelNum:4d}" if "nozero" in self.type else f"{channelNum:04d}"
			else:
				self.num = None
			Converter.changed(self, what)
		elif what[0] is self.CHANGED_POLL or what[0] is self.CHANGED_ALL:
			Converter.changed(self, what)

	@cached
	def getText(self):
		text = None
		if "nothing" in self.type:
			text = "    "
		elif hasattr(self.source, "text"):
			text = self.source.text.rjust(4) if "nozero" in self.type else self.source.text.zfill(4)
		elif self.showclock == 0:
			if self.delay:
				self.poll_interval = self.delay
				self.showclock = 1
			if self.num:
				text = self.num
		else:
			match self.showclock:
				case 1:
					if "noblink" in self.type:
						self.poll_interval = self.delay
					else:
						self.poll_interval = 1000
						self.showclock = 3
					clockFormat = f"{self.hour}%02M"
				case 2:
					self.showclock = 3
					clockFormat = f"{self.hour}%02M"
				case _:
					self.showclock = 2
					clockFormat = f"{self.hour}:%02M"
			if self.loop != -1:
				self.loop -= 1000
				if self.loop <= 0:
					self.loop = self.delay
					self.showclock = 0
			text = datetime.today().strftime(clockFormat)
		return text

	text = property(getText)

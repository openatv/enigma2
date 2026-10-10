from enigma import iServiceInformation

from Components.Converter.Converter import Converter
from Components.Element import ElementError, cached


class ServiceTime(Converter):
	STARTTIME = 0
	ENDTIME = 1
	DURATION = 2

	def __init__(self, tokens):
		Converter.__init__(self, tokens)
		self.type = {
			"Duration": self.DURATION,
			"EndTime": self.ENDTIME,
			"StartTime": self.STARTTIME
		}.get(tokens)
		if self.type is None:
			raise ElementError(f"'{tokens}' is not <StartTime|EndTime|Duration> for ServiceTime converter")

	@cached
	def getTime(self):
		result = None
		service = self.source.service
		info = self.source.info
		if info and service:
			match self.type:
				case self.DURATION:
					duration = info.getLength(service)
					if duration == -1:  # Try to get the duration from the event.
						event = info.getEvent(service)
						if event:
							duration = event.getDuration()
					result = duration + 10  # Add 10 seconds to fix rounding to minutes.
				case self.ENDTIME:
					begin = info.getInfo(service, iServiceInformation.sTimeCreate)
					result = begin + info.getLength(service) + 10  # Add 10 seconds to fix rounding to minutes.
				case self.STARTTIME:
					result = info.getInfo(service, iServiceInformation.sTimeCreate)
		return result

	time = property(getTime)

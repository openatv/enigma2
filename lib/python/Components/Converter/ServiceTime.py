from enigma import iServiceInformation

from Components.Element import ElementError, cached
from Components.Converter.Converter import Converter


class ServiceTime(Converter):
	STARTTIME = 0
	ENDTIME = 1
	DURATION = 2

	def __init__(self, token):
		Converter.__init__(self, token)
		self.type = {
			"Duration": self.DURATION,
			"EndTime": self.ENDTIME,
			"StartTime": self.STARTTIME
		}.get(token)
		if self.type is None:
			raise ElementError(f"'{token}' is not <StartTime|EndTime|Duration> for ServiceTime converter")

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
					result = duration + 10 if duration >= 0 else None  # Keep unknown durations empty; round known durations to minutes.
				case self.ENDTIME:
					from NavigationInstance import instance  # Read the current navigation instance after startup.
					if instance:
						path = service.getPath()
						for timer in instance.RecordTimer.timer_list:
							if timer.isRunning() and not timer.justplay and timer.record_service:
								filename = getattr(timer, "Filename", None)
								if filename and path == f"{filename}{timer.record_service.getFilenameExtension()}":
									result = timer.end
									break
					if result is None:
						begin = info.getInfo(service, iServiceInformation.sTimeCreate)
						length = info.getLength(service)
						if begin > 0 and length >= 0:
							result = begin + length + 10  # Add 10 seconds to fix rounding to minutes.
				case self.STARTTIME:
					result = info.getInfo(service, iServiceInformation.sTimeCreate)
		return result

	time = property(getTime)

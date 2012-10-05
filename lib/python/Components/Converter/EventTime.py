from Converter import Converter
from Poll import Poll
from time import time
from Components.Element import cached, ElementError
from Components.config import config
from enigma import eEPGCache

class EventTime(Poll, Converter, object):
	STARTTIME = 0
	ENDTIME = 1
	REMAINING = 2
	REMAINING_VFD = 3
	PROGRESS = 4
	DURATION = 5
	ELAPSED = 6
	ELAPSED_VFD = 7
	NEXT_START_TIME = 8
	NEXT_END_TIME = 9
	NEXT_DURATION = 10
	THIRD_START_TIME = 11
	THIRD_END_TIME = 12
	THIRD_DURATION = 13

	def __init__(self, type):
		Converter.__init__(self, type)
		Poll.__init__(self)
		self.epgcache = eEPGCache.getInstance()
		if type == "EndTime":
			self.type = self.ENDTIME
		elif type == "Remaining":
			self.type = self.REMAINING
			self.poll_interval = 60*1000
			self.poll_enabled = True
		elif type == "VFDRemaining":
			self.type = self.REMAINING_VFD
			self.poll_interval = 60*1000
			self.poll_enabled = True
		elif type == "StartTime":
			self.type = self.STARTTIME
		elif type == "Duration":
			self.type = self.DURATION
		elif type == "Progress":
			self.type = self.PROGRESS
			self.poll_interval = 30*1000
			self.poll_enabled = True
		elif type == "Elapsed":
			self.type = self.ELAPSED
			self.poll_interval = 60*1000
			self.poll_enabled = True
		elif type == "VFDElapsed":
			self.type = self.ELAPSED_VFD
			self.poll_interval = 60*1000
			self.poll_enabled = True
		elif type == "NextStartTime":
			self.type = self.NEXT_START_TIME
		elif type == "NextEndTime":
			self.type = self.NEXT_END_TIME
		elif type == "NextDurartion":
			self.type = self.NEXT_DURATION
		elif type == "ThirdStartTime":
			self.type = self.THIRD_START_TIME
		elif type == "ThirdEndTime":
			self.type = self.THIRD_END_TIME
		elif type == "ThirdDurartion":
			self.type = self.THIRD_DURATION
		else:
			raise ElementError("'%s' is not <StartTime|EndTime|Remaining|Elapsed|Duration|Progress> for EventTime converter" % type)

	@cached
	def getTime(self):
		assert self.type != self.PROGRESS

		event = self.source.event
		if event is None:
			return None

		if self.type == self.STARTTIME:
			return event.getBeginTime()
		elif self.type == self.ENDTIME:
			return event.getBeginTime() + event.getDuration()
		elif self.type == self.DURATION:
			return event.getDuration()
		elif self.type == self.REMAINING or self.type == self.REMAINING_VFD or self.type == self.ELAPSED or self.type == self.ELAPSED_VFD:
			now = int(time())
			start_time = event.getBeginTime()
			duration = event.getDuration()
			end_time = start_time + duration
			elapsed = now - start_time
			if start_time <= now <= end_time:
				if self.type == self.REMAINING and config.usage.swap_time_remaining_on_osd.getValue() == "0":
					return (duration, end_time - now)
				elif self.type == self.REMAINING and config.usage.swap_time_remaining_on_osd.getValue() == "1":
					return (duration, elapsed)
				elif self.type == self.REMAINING and config.usage.swap_time_remaining_on_osd.getValue() == "2":
					return (duration, elapsed, end_time - now)
				elif self.type == self.REMAINING and config.usage.swap_time_remaining_on_osd.getValue() == "3":
					return (duration, end_time - now, elapsed)
				elif self.type == self.ELAPSED and config.usage.swap_time_remaining_on_osd.getValue() == "0":
					return (duration, elapsed)
				elif self.type == self.ELAPSED and config.usage.swap_time_remaining_on_osd.getValue() == "1":
					return (duration, end_time - now)
				elif self.type == self.ELAPSED and config.usage.swap_time_remaining_on_osd.getValue() == "2":
					return (duration, elapsed, end_time - now)
				elif self.type == self.ELAPSED and config.usage.swap_time_remaining_on_osd.getValue() == "3":
					return (duration, end_time - now, elapsed)
				elif self.type == self.REMAINING_VFD and config.usage.swap_time_remaining_on_vfd.getValue() == "0":
					return (duration, end_time - now)
				elif self.type == self.REMAINING_VFD and config.usage.swap_time_remaining_on_vfd.getValue() == "1":
					return (duration, elapsed)
				elif self.type == self.REMAINING_VFD and config.usage.swap_time_remaining_on_vfd.getValue() == "2":
					return (duration, elapsed, end_time - now)
				elif self.type == self.REMAINING_VFD and config.usage.swap_time_remaining_on_vfd.getValue() == "3":
					return (duration, end_time - now, elapsed)
				elif self.type == self.ELAPSED_VFD and config.usage.swap_time_remaining_on_vfd.getValue() == "0":
					return (duration, elapsed)
				elif self.type == self.ELAPSED_VFD and config.usage.swap_time_remaining_on_vfd.getValue() == "1":
					return (duration, end_time - now)
				elif self.type == self.ELAPSED_VFD and config.usage.swap_time_remaining_on_vfd.getValue() == "2":
					return (duration, elapsed, end_time - now)
				elif self.type == self.ELAPSED_VFD and config.usage.swap_time_remaining_on_vfd.getValue() == "3":
					return (duration, end_time - now, elapsed)
			else:
				return (duration, None)

		elif self.type == self.NEXT_START_TIME or self.type == self.NEXT_END_TIME or self.type == self.NEXT_DURATION or self.type == self.THIRD_START_TIME or self.type == self.THIRD_END_TIME or self.type == self.THIRD_DURATION:
			reference = self.source.service
			info = reference and self.source.info
			if info is None:
				return
			test = [ 'IBDCX', (reference.toString(), 1, -1, 1440) ] # search next 24 hours
			self.list = [] if self.epgcache is None else self.epgcache.lookupEvent(test)
			if self.list:
				try:
					if self.type == self.NEXT_START_TIME and self.list[1][1]:
						return self.list[1][1]
					elif self.type == self.NEXT_END_TIME and self.list[1][1] and self.list[1][2]:
						return int(self.list[1][1]) + int(self.list[1][2])
					elif self.type == self.THIRD_START_TIME and self.list[2][1]:
						return self.list[2][1]
					elif self.type == self.THIRD_END_TIME and self.list[2][1] and self.list[2][2]:
						return int(self.list[2][1]) + int(self.list[2][2])
					else:
						# failed to return any epg data.
						return None
				except:
					# failed to return any epg data.
					return None


	@cached
	def getValue(self):
		assert self.type == self.PROGRESS

		event = self.source.event
		if event is None:
			return None

		now = int(time())
		start_time = event.getBeginTime()
		duration = event.getDuration()
		if start_time <= now <= (start_time + duration) and duration > 0:
			return (now - start_time) * 1000 / duration
		else:
			return None

	time = property(getTime)
	value = property(getValue)
	range = 1000

	def changed(self, what):
		Converter.changed(self, what)
		if self.type == self.PROGRESS and len(self.downstream_elements):
			if not self.source.event and self.downstream_elements[0].visible:
				self.downstream_elements[0].visible = False
			elif self.source.event and not self.downstream_elements[0].visible:
				self.downstream_elements[0].visible = True

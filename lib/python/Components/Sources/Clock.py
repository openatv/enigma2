from Tools.Event import Event
from enigma import eTimer
import time

from Source import Source

class Clock(Source):
	def __init__(self):
		self.changed = Event(start=self.start, stop=self.stop)
		self.clock_timer = eTimer()
		self.clock_timer.timeout.get().append(self.changed)

	def start(self):
		self.clock_timer.start(1000)

	def stop(self):
		self.clock_timer.stop()

	def getClock(self):
		return time.time()

	time = property(getClock)

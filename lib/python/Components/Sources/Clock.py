from Tools.Event import Event
from enigma import eTimer
import time

from Source import Source

class Clock(Source):
	def __init__(self):
		Source.__init__(self)
		self.clock_timer = eTimer()
		self.clock_timer.timeout.get().append(self.changed)
		self.clock_timer.start(1000)

	def getClock(self):
		return time.time()

	time = property(getClock)

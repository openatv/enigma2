from time import time as gettime

from enigma import eTimer

from Components.Element import cached
from Components.Sources.Source import Source


class Clock(Source):
	def __init__(self):
		Source.__init__(self)
		self.clockTimer = eTimer()
		self.clockTimer.callback.append(self.poll)
		self.clockTimer.start(1000)

	@cached
	def getClock(self):
		return gettime()

	time = property(getClock)

	def poll(self):
		self.changed((self.CHANGED_POLL,))

	def doSuspend(self, suspended):
		if suspended:
			self.clockTimer.stop()
		else:
			self.clockTimer.start(1000)
			self.poll()

	def destroy(self):
		self.clockTimer.callback.remove(self.poll)
		Source.destroy(self)

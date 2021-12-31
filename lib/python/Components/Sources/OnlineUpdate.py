from enigma import eTimer
from Components.Element import cached
from Components.OnlineUpdateCheck import versioncheck
from Components.Sources.Source import Source


class OnlineUpdateStableCheck(Source):
	def __init__(self):
		Source.__init__(self)
		self.checkTimer = eTimer()
		self.checkTimer.callback.append(self.poll)
		self.checkTimer.start(60000)

	@cached
	def getBoolean(self):
		return versioncheck.getStableUpdateAvailable()

	boolean = property(getBoolean)

	def poll(self):
		self.changed((self.CHANGED_POLL,))

	def doSuspend(self, suspended):
		if suspended:
			self.checkTimer.stop()
		else:
			self.checkTimer.start(3600000)
			self.poll()

	def destroy(self):
		self.checkTimer.callback.remove(self.poll)
		Source.destroy(self)


class OnlineUpdateUnstableCheck(Source):
	def __init__(self):
		Source.__init__(self)
		self.checkTimer = eTimer()
		self.checkTimer.callback.append(self.poll)
		self.checkTimer.start(60000)

	@cached
	def getBoolean(self):
		return versioncheck.getUnstableUpdateAvailable()

	boolean = property(getBoolean)

	def poll(self):
		self.changed((self.CHANGED_POLL,))

	def doSuspend(self, suspended):
		if suspended:
			self.checkTimer.stop()
		else:
			self.checkTimer.start(3600000)
			self.poll()

	def destroy(self):
		self.checkTimer.callback.remove(self.poll)
		Source.destroy(self)

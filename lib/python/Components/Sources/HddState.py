from Source import Source
from Components.Element import cached
from Components.Harddisk import harddiskmanager
from Components.config import config
from enigma import eTimer, eConsoleAppContainer

class HddState(Source):
	def __init__(self, session, poll=60):
		Source.__init__(self)
		self.isSleeping = False
		self.session = session
		self.standby_time = poll
		self.timer = eTimer()
		self.idle_time = int(config.usage.hdd_standby.value)
		config.usage.hdd_standby.addNotifier(self.setStandbyTime, initial_call=False)
		self.timer.callback.append(self.runIdle)
		self.hdd = self.isInternalHDD()
		self.container = eConsoleAppContainer()
		if self.hdd:
			if self.idle_time:
				self.runIdle()
			else:
				self.isSleeping = True

	def runIdle(self):
		if self.hdd and self.idle_time:
			cmd = "hdparm -C %s" % self.hdd[1].disk_path
			self.container.dataAvail.append(self.setHddState)
			self.container.execute(cmd)

	def setHddState(self, str):
		self.container.dataAvail.remove(self.setHddState)
		prev_state = self.isSleeping
		if 'standby' in str:
			self.isSleeping = False
			idle = self.standby_time
		else:
			self.isSleeping = True
			idle = self.idle_time
		if prev_state != self.isSleeping:
			self.changed((self.CHANGED_ALL,))
		self.timer.startLongTimer(idle)

	def setStandbyTime(self, cfgElem):
		self.timer.stop()
		self.idle_time = int(cfgElem.value)
		if self.idle_time and self.hdd:
			self.timer.startLongTimer(self.standby_time)

	def isInternalHDD(self):
		if harddiskmanager.HDDCount():
			for hdd in harddiskmanager.HDDList():
				if "pci" in hdd[1].phys_path or "ahci" in hdd[1].phys_path:
					return hdd
		return None

	@cached
	def getBoolean(self):
		return self.isSleeping and True or False
	boolean = property(getBoolean)

	@cached
	def getValue(self):
		return self.isSleeping
	value = property(getValue)

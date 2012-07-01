from PerServiceDisplay import PerServiceDisplay, PerServiceBase
from Components.GUIComponent import GUIComponent
from enigma import eTimer, iPlayableService, ePositionGauge
import time

class ServicePosition(PerServiceDisplay, object):
	TYPE_LENGTH = 0,
	TYPE_POSITION = 1,
	TYPE_REMAINING = 2,
	TYPE_RELATIVE = 3

	def __init__(self, navcore, type):
		object.__init__(self)
		self.updateTimer = eTimer()
		self.updateTimer.callback.append(self.update)
		PerServiceDisplay.__init__(self, navcore,
			{
				iPlayableService.evStart: self.newService,
				iPlayableService.evEnd: self.stopEvent
			})
		self.type = type
		self.relative_base = 0
#		self.setType(type)

	def newService(self):
		self.setType(self.type)

	def setType(self, type):
		self.type = type

		self.updateTimer.start(500)
		self.update()

	def setRelative(self, rel):
		self.relative_base = rel

	def get(self, what):
		service = self.navcore.getCurrentService()
		seek = service and service.seek()
		if seek != None:
			if what == self.TYPE_LENGTH:
				r = seek.getLength()
			elif what == self.TYPE_POSITION:
				r = seek.getPlayPosition()
			if not r[0]:
				return r[1] / 90000

		return -1

	def update(self):
		seek = None
		service = self.navcore.getCurrentService()
		if service != None:
			seek = service.seek()

		if seek is not None:
			if self.type != self.TYPE_RELATIVE:
				if self.type == self.TYPE_LENGTH:
					l = self.get(self.TYPE_LENGTH)
				elif self.type == self.TYPE_POSITION:
					l = self.get(self.TYPE_POSITION)
				elif self.type == self.TYPE_REMAINING:
					l = self.get(self.TYPE_LENGTH) - self.get(self.TYPE_POSITION)

				self.setText("%d:%02d" % (l/60, l%60))
			else:
				l = self.get(self.TYPE_POSITION)
				if l != -1:
					l += self.relative_base
					try:
						t = time.localtime(l)
						timestr = "%2d:%02d:%02d" % (t.tm_hour, t.tm_min, t.tm_sec)
					except ValueError:
						timestr = ""
				else:
					timestr = ""

				self.setText(timestr)

			self.updateTimer.start(500)
		else:
			self.updateTimer.start(10000)
			self.setText("-:--")

	def stopEvent(self):
		self.updateTimer.stop()
		self.setText("");

class ServicePositionGauge(PerServiceBase, GUIComponent):
	def __init__(self, navcore):
		GUIComponent.__init__(self)
		PerServiceBase.__init__(self, navcore,
			{
				iPlayableService.evStart: self.newService,
				iPlayableService.evEnd: self.stopEvent,
				iPlayableService.evCuesheetChanged: self.newCuesheet
			})
		self.instance = None
		self.__seek_position = 0

	def newService(self):
		if self.get() is None:
			self.disablePolling()
		else:
			self.enablePolling(interval=500)
			self.newCuesheet()

	def get(self):
		service = self.navcore.getCurrentService()
		seek = service and service.seek()
		if seek is None:
			return (0, 0)

		len = seek.getLength()
		pos = seek.getPlayPosition()

		if len[0] or pos[0]:
			return (0, 0)
		return (len[1], pos[1])

	def poll(self):
		data = self.get()
		if data is None:
			return

		if self.instance is not None:
			self.instance.setLength(data[0])
			self.instance.setPosition(data[1])

	def stopEvent(self):
		self.disablePolling()

	GUI_WIDGET = ePositionGauge

	def postWidgetCreate(self, instance):
		self.newService()
		self.setSeekPosition(self.__seek_position)

	def newCuesheet(self):
		service = self.navcore.getCurrentService()
		cue = service and service.cueSheet()
		cutlist = (cue and cue.getCutList()) or [ ]
		if self.instance is not None:
			self.instance.setInOutList(cutlist)

	def getSeekEnable(self):
		return self.__seek_enable

	def setSeekEnable(self, val):
		self.__seek_enable = val
		if self.instance is not None:
			self.instance.enableSeekPointer(val)

	seek_pointer_enabled = property(getSeekEnable, setSeekEnable)

	def getSeekPosition(self):
		return self.__seek_position

	def setSeekPosition(self, pos):
		print "set seek position:", pos
		self.__seek_position = pos
		if self.instance is not None:
			print "set instance."
			self.instance.setSeekPosition(pos)

	seek_pointer_position = property(getSeekPosition, setSeekPosition)

	def destroy(self):
		PerServiceBase.destroy(self)
		GUIComponent.destroy(self)

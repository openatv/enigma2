from GUIComponent import *
from VariableText import *
from VariableValue import *

from enigma import iPlayableService
from enigma import eLabel, eSlider, eTimer

class PerServiceBase(object):
	def __init__(self, navcore, eventmap):
		self.eventmap = eventmap
		self.navcore = navcore
		self.navcore.event.append(self.event)
		self.poll_timer = eTimer()
		self.poll_timer.timeout.get().append(self.poll)
		
		# start with stopped state, so simulate that
		self.event(iPlayableService.evEnd)

	def destroy(self):
		self.navcore.event.remove(self.event)

	def event(self, ev):
		# loop up if we need to handle this event
		if self.eventmap.has_key(ev):
			# call handler
			self.eventmap[ev]()
	
	def enablePolling(self, interval=60000):
		if interval:
			self.poll_timer.start(interval)
		else:
			self.poll_timer.stop()
	
	def disablePolling(self):
		self.enablePolling(interval=0)

	def poll(self):
		pass

class PerServiceDisplay(PerServiceBase, VariableText, GUIComponent):
	"""Mixin for building components which display something which changes on navigation events, for example "service name" """
	def __init__(self, navcore, eventmap):
		GUIComponent.__init__(self)
		VariableText.__init__(self)
		PerServiceBase.__init__(self, navcore, eventmap)

	GUI_WIDGET = eLabel

class PerServiceDisplayProgress(PerServiceBase, VariableValue, GUIComponent):
	def __init__(self, navcore, eventmap):
		GUIComponent.__init__(self)
		VariableValue.__init__(self)
		self.eventmap = eventmap
		self.navcore = navcore
		self.navcore.event.append(self.event)

		# start with stopped state, so simulate that
		self.event(iPlayableService.evEnd)

	GUI_WIDGET = eSlider

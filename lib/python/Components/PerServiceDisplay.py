from GUIComponent import *
from VariableText import *

from enigma import pNavigation
from enigma import eLabel

class PerServiceDisplay(GUIComponent, VariableText):
	"""Mixin for building components which display something which changes on navigation events, for example "service name" """
	
	def __init__(self, navcore, eventmap):
		GUIComponent.__init__(self)
		VariableText.__init__(self)
		self.eventmap = eventmap
		self.navcore = navcore
		self.navcore.event.append(self.event)

		# start with stopped state, so simulate that
		self.event(pNavigation.evStopService)

	def event(self, ev):
		# loop up if we need to handle this event
		if self.eventmap.has_key(ev):
			# call handler
			self.eventmap[ev]()
	
	def createWidget(self, parent, skindata):
		# by default, we use a label to display our data.
		g = eLabel(parent)
		return g


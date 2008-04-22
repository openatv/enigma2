class InfoBarBase:
	def __init__(self):
		ServiceEventTracker.setActiveInfoBar(self)
		self.onClose.append(self.__close)

	def __close(self):
		ServiceEventTracker.popActiveInfoBar()

class ServiceEventTracker:
	"""Tracks service events into a screen"""
	InfoBarStack = [ ]
	InfoBarStackSize = 0

	def __init__(self, screen, eventmap):
		self.__eventmap = eventmap
		self.screen = screen
		screen.session.nav.event.append(self.__event)
		screen.onClose.append(self.__del_event)

	def __del_event(self):
		self.screen.session.nav.event.remove(self.__event)

	def __event(self, ev):
		set = ServiceEventTracker
		ssize = set.InfoBarStackSize
		stack = set.InfoBarStack
		if ev in self.__eventmap:
			if not isinstance(self.screen, InfoBarBase) or (ssize and stack[ssize-1] == self.screen):
				self.__eventmap[ev]()
#			else:
#				print "ignore event", ev, "for inactive infobar '" + str(self.screen) + "'"

	@staticmethod
	def setActiveInfoBar(infobar):
		set = ServiceEventTracker
		assert infobar not in set.InfoBarStack, "FATAL: Infobar '" + str(infobar) + "' is already active!"
		set.InfoBarStack.append(infobar)
		set.InfoBarStackSize += 1
#		print "ServiceEventTracker set active '" + str(infobar) + "'"

	@staticmethod
	def popActiveInfoBar():
		set = ServiceEventTracker
		stack = set.InfoBarStack
		if set.InfoBarStackSize:
			set.InfoBarStackSize -= 1
			del stack[set.InfoBarStackSize]
#			if set.InfoBarStackSize:
#				print "ServiceEventTracker reset active '" + str(stack[set.InfoBarStackSize-1]) + "'"

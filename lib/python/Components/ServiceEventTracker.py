class InfoBarBase:
	def __init__(self, steal_current_service = False):
		if steal_current_service:
			ServiceEventTracker.setActiveInfoBar(self, None, None)
		else:
			nav = self.session.nav
			ServiceEventTracker.setActiveInfoBar(self, not steal_current_service and nav.getCurrentService(), nav.getCurrentlyPlayingServiceReference())
		self.onClose.append(self.__close)

	def __close(self):
		ServiceEventTracker.popActiveInfoBar()

class ServiceEventTracker:
	"""Tracks service events into a screen"""
	InfoBarStack = [ ]
	InfoBarStackSize = 0
	oldService = None

	def __init__(self, screen, eventmap):
		self.__eventmap = eventmap
		self.screen = screen
		screen.session.nav.event.append(self.__event)
		screen.onClose.append(self.__del_event)

	def __del_event(self):
		self.screen.session.nav.event.remove(self.__event)

	def __event(self, ev):
		func = self.__eventmap.get(ev)
		if func:
			set = ServiceEventTracker
			screen = self.screen
			nav = screen.session.nav
			cur_ref = nav.getCurrentlyPlayingServiceReference()
			old_service_running = set.oldRef and cur_ref and cur_ref == set.oldRef and set.oldService and set.oldService == str(nav.getCurrentService())
			if not old_service_running:
				set.oldService = None
				set.oldRef = None
#		print "old_service_running", old_service_running
			ssize = set.InfoBarStackSize
			stack = set.InfoBarStack
			if (not isinstance(screen, InfoBarBase) or # let pass all events to screens not derived from InfoBarBase
				(not old_service_running and ssize and stack[ssize-1] == screen) or # let pass events from currently running service just to current active screen (derived from InfoBarBase)
				(old_service_running and ssize > 1 and stack[ssize-2] == screen)): # let pass events from old running service just to previous active screen (derived from InfoBarBase)
				func()
#			else:
#				print "ignore event", ev, "for inactive infobar '" + str(self.screen) + "'"

	@staticmethod
	def setActiveInfoBar(infobar, old_service, old_ref):
		set = ServiceEventTracker
		set.oldRef = old_ref
		set.oldService = old_service and str(old_service)
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

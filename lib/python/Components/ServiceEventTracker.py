class ServiceEventTracker:
	"""Tracks service events into a screen"""
	
	def __init__(self, screen, eventmap):
		self.__eventmap = eventmap
		self.session = screen.session
		self.session.nav.event.append(self.__event)
		screen.onClose.append(self.__del_event)

	def __del_event(self):
		self.session.nav.event.remove(self.__event)

	def __event(self, ev):
		if ev in self.__eventmap:
			self.__eventmap[ev]()

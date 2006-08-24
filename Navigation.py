from enigma import *
import RecordTimer

import NavigationInstance
import ServiceReference

# TODO: remove pNavgation, eNavigation and rewrite this stuff in python.
class Navigation:
	def __init__(self):
		if NavigationInstance.instance is not None:
			raise NavigationInstance.instance
		
		NavigationInstance.instance = self
		self.ServiceHandler = eServiceCenter.getInstance()

		import Navigation as Nav
		Nav.navcore = self
		
		self.pnav = pNavigation()
		self.pnav.m_event.get().append(self.callEvent)
		self.event = [ ]
		self.currentlyPlayingServiceReference = None
		self.currentlyPlayingService = None
		self.state = 0
		self.RecordTimer = RecordTimer.RecordTimer()

	def callEvent(self, i):
		self.state = i != 1
		for x in self.event:
			x(i)

	def playService(self, ref):
		print "playing", ref and ref.toString()
		self.currentlyPlayingServiceReference = None
		self.currentlyPlayingService = None
		if ref is None:
			self.stopService()
			return 0
		
		if self.pnav and not self.pnav.playService(ref):
			self.currentlyPlayingServiceReference = ref
			return 0
		return 1
	
	def getCurrentlyPlayingServiceReference(self):
		return self.currentlyPlayingServiceReference
	
	def recordService(self, ref):
		print "recording service: %s" % (str(ref))
		if isinstance(ref, ServiceReference.ServiceReference):
			ref = ref.ref
		service = self.pnav and self.pnav.recordService(ref)
		
		if service is None:
			print "record returned non-zero"
			return None
		else:
			return service

	def getCurrentService(self):
		if self.state:
			if not self.currentlyPlayingService:
				self.currentlyPlayingService = self.pnav and self.pnav.getCurrentService()
			return self.currentlyPlayingService
		return None

	def stopService(self):
		print "stopService"
		if self.pnav:
			self.pnav.stopService()
		self.currentlyPlayingService = None
		self.currentlyPlayingServiceReference = None

	def pause(self, p):
		return self.pnav and self.pnav.pause(p)

	def recordWithTimer(self, ref, begin, end, name, description, eit):
		if isinstance(ref, eServiceReference):
			ref = ServiceReference.ServiceReference(ref)
		entry = RecordTimer.RecordTimerEntry(ref, begin, end, name, description, eit)
		self.RecordTimer.record(entry)
		return entry
	
	def shutdown(self):
		self.RecordTimer.shutdown()
		self.ServiceHandler = None
		self.pnav = None

	def stopUserServices(self):
		self.stopService()

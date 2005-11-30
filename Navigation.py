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
		self.currentlyPlayingService = None
		self.currentlyPlayingServiceReference = None
		
		self.RecordTimer = RecordTimer.RecordTimer()

	def callEvent(self, i):
		for x in self.event:
			x(i)
	
	def playService(self, ref):
		self.currentlyPlayingServiceReference = None
		if ref is None:
			self.stopService()
			return 0
		
		if not self.pnav.playService(ref):
			self.currentlyPlayingServiceReference = ref
			return 0
		return 1
	
	def getCurrentlyPlayingServiceReference(self):
		return self.currentlyPlayingServiceReference
	
	def recordService(self, ref):
		print "recording service: %s" % (str(ref))
		if isinstance(ref, ServiceReference.ServiceReference):
			ref = ref.ref
		service = self.pnav.recordService(ref)
		
		if service is None:
			print "record returned non-zero"
			return None
		else:
			return service
	
	def enqueueService(self, ref):
		return self.pnav.enqueueService(ref)
	
	def getCurrentService(self):
		service = self.pnav.getCurrentService()
		
		if service is None:
			return None
		
		return service
	
	def stopService(self):
		self.pnav.stopService()
	
	def getPlaylist(self):
		playlist = ePlaylistPtr()
		if self.pnav.getPlaylist(playlist):
			return None
		return playlist
	
	def pause(self, p):
		return self.pnav.pause(p)
	
	def recordWithTimer(self, begin, end, ref, epg, description):
		if isinstance(ref, eServiceReference):
			ref = ServiceReference.ServiceReference(ref)
		entry = RecordTimer.RecordTimerEntry(begin, end, ref, epg, description)
		self.RecordTimer.record(entry)
		return entry
	
	def shutdown(self):
		self.RecordTimer.shutdown()

	def stopUserServices(self):
		self.stopService()

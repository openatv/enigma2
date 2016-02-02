from enigma import eServiceCenter, eServiceReference, eTimer, pNavigation, getBestPlayableServiceReference, iPlayableService, eActionMap, setPreferredTuner, eStreamServer
from Components.ParentalControl import parentalControl
from Components.SystemInfo import SystemInfo
from Components.config import config, configfile
from Components.PluginComponent import plugins
from Plugins.Plugin import PluginDescriptor
from Tools.BoundFunction import boundFunction
from Tools.StbHardware import setFPWakeuptime, getFPWakeuptime, getFPWasTimerWakeup
from Tools import Notifications
from time import time, localtime
import RecordTimer
import Screens.Standby
import NavigationInstance
import ServiceReference
from Screens.InfoBar import InfoBar
from sys import maxint

# TODO: remove pNavgation, eNavigation and rewrite this stuff in python.
class Navigation:
	def __init__(self, nextRecordTimerAfterEventActionAuto=False):
		if NavigationInstance.instance is not None:
			raise NavigationInstance.instance

		NavigationInstance.instance = self
		self.ServiceHandler = eServiceCenter.getInstance()

		import Navigation as Nav
		Nav.navcore = self

		self.pnav = pNavigation()
		self.pnav.m_event.get().append(self.dispatchEvent)
		self.pnav.m_record_event.get().append(self.dispatchRecordEvent)
		self.event = [ ]
		self.record_event = [ ]
		self.currentlyPlayingServiceReference = None
		self.currentlyPlayingServiceOrGroup = None
		self.currentlyPlayingService = None
		
		self.RecordTimer = None
		for p in plugins.getPlugins(PluginDescriptor.WHERE_RECORDTIMER):
			self.RecordTimer = p()
			if self.RecordTimer:
				break
		if not self.RecordTimer:
			self.RecordTimer = RecordTimer.RecordTimer()
		self.nextRecordTimerAfterEventActionAuto = nextRecordTimerAfterEventActionAuto
		self.__wasTimerWakeup = False
		self.__wasRecTimerWakeup = False
		self.syncCount = 0

		wasTimerWakeup = getFPWasTimerWakeup()
		if not wasTimerWakeup: #work-around for boxes where driver not sent was_timer_wakeup signal to e2
			print"[NAVIGATION] getNextRecordingTime= %s" % self.RecordTimer.getNextRecordingTime()
			print"[NAVIGATION] current Time=%s" % time()
			print"[NAVIGATION] timediff=%s" % abs(self.RecordTimer.getNextRecordingTime() - time())

			if time() <= 31536000: # check for NTP-time sync, if no sync, wait for transponder time
				self.timesynctimer = eTimer()
				self.timesynctimer.callback.append(self.TimeSynctimer)
				self.timesynctimer.start(5000, True)
				print"[NAVIGATION] wait for time sync"
				
			elif abs(self.RecordTimer.getNextRecordingTime() - time()) <= 360: # if there is a recording sheduled in the next 5 mins, set the wasTimerWakeup flag
				wasTimerWakeup = True
				f = open("/tmp/was_timer_wakeup_workaround.txt", "w")
				file = f.write(str(wasTimerWakeup))
				f.close()

		print"[NAVIGATION] wasTimerWakeup = %s" % wasTimerWakeup

		if wasTimerWakeup:
			self.__wasTimerWakeup = True
			if time() <= 31536000:
				self.timesynctimer = eTimer()
				self.timesynctimer.callback.append(self.TimeSynctimer)
				self.timesynctimer.start(5000, True)
				print"[NAVIGATION] wait for time sync"
	
			elif nextRecordTimerAfterEventActionAuto and abs(self.RecordTimer.getNextRecordingTime() - time()) <= 360:
				self.__wasRecTimerWakeup = True
				print 'RECTIMER: wakeup to standby detected.'
				f = open("/tmp/was_rectimer_wakeup", "w")
				f.write('1')
				f.close()
				# as we woke the box to record, place the box in standby.
				self.standbytimer = eTimer()
				self.standbytimer.callback.append(self.gotostandby)
				self.standbytimer.start(15000, True)

	def wasTimerWakeup(self):
		return self.__wasTimerWakeup

	def wasRecTimerWakeup(self):
		return self.__wasRecTimerWakeup

	def TimeSynctimer(self):
		self.syncCount += 1
		if self.nextRecordTimerAfterEventActionAuto and abs(self.RecordTimer.getNextRecordingTime() - time()) <= 360:
			self.__wasRecTimerWakeup = True
			print 'RECTIMER: wakeup to standby detected.'
			print"[NAVIGATION] getNextRecordingTime= %s" % self.RecordTimer.getNextRecordingTime()
			print"[NAVIGATION] current Time=%s" % time()
			print"[NAVIGATION] timediff=%s" % abs(self.RecordTimer.getNextRecordingTime() - time())
			f = open("/tmp/was_rectimer_wakeup", "w")
			f.write('1')
			f.close()
			self.gotostandby()
		else:
			if self.syncCount <= 24 and time() <= 31536000: # max 2 mins or when time is in sync
				self.timesynctimer.start(5000, True)
			else:
				print"[NAVIGATION] No Recordings found, end work-around"

		print"[NAVIGATION] wasTimerWakeup after time sync = %s, sync time = %s sec." % (self.__wasRecTimerWakeup, self.syncCount * 5)

	def gotostandby(self):
		from Tools import Notifications
		Notifications.AddNotification(Screens.Standby.Standby)

	def checkShutdownAfterRecording(self):
		if len(self.getRecordings()) or abs(self.RecordTimer.getNextRecordingTime() - time()) <= 360:
			if not Screens.Standby.inTryQuitMainloop: # not a shutdown messagebox is open
				RecordTimer.RecordTimerEntry.TryQuitMainloop(False) # start shutdown handling

	def dispatchEvent(self, i):
		for x in self.event:
			x(i)
		if i == iPlayableService.evEnd:
			self.currentlyPlayingServiceReference = None
			self.currentlyPlayingServiceOrGroup = None
			self.currentlyPlayingService = None

	def dispatchRecordEvent(self, rec_service, event):
#		print "record_event", rec_service, event
		for x in self.record_event:
			x(rec_service, event)

	def playService(self, ref, checkParentalControl=True, forceRestart=False, adjust=True):
		oldref = self.currentlyPlayingServiceOrGroup
		if ref and oldref and ref == oldref and not forceRestart:
			print "ignore request to play already running service(1)"
			return 1
		print "playing", ref and ref.toString()
		if ref is None:
			self.stopService()
			return 0
		from Components.ServiceEventTracker import InfoBarCount
		InfoBarInstance = InfoBarCount == 1 and InfoBar.instance
		if not checkParentalControl or parentalControl.isServicePlayable(ref, boundFunction(self.playService, checkParentalControl=False, forceRestart=forceRestart, adjust=adjust)):
			if ref.flags & eServiceReference.isGroup:
				oldref = self.currentlyPlayingServiceReference or eServiceReference()
				playref = getBestPlayableServiceReference(ref, oldref)
				print "playref", playref
				if playref and oldref and playref == oldref and not forceRestart:
					print "ignore request to play already running service(2)"
					return 1
				if not playref:
					alternativeref = getBestPlayableServiceReference(ref, eServiceReference(), True)
					self.stopService()
					if alternativeref and self.pnav:
						self.currentlyPlayingServiceReference = alternativeref
						self.currentlyPlayingServiceOrGroup = ref
						if self.pnav.playService(alternativeref):
							print "Failed to start", alternativeref
							self.currentlyPlayingServiceReference = None
							self.currentlyPlayingServiceOrGroup = None
					return 0
				elif checkParentalControl and not parentalControl.isServicePlayable(playref, boundFunction(self.playService, checkParentalControl = False)):
					if self.currentlyPlayingServiceOrGroup and InfoBarInstance and InfoBarInstance.servicelist.servicelist.setCurrent(self.currentlyPlayingServiceOrGroup, adjust):
						self.currentlyPlayingServiceOrGroup = InfoBarInstance.servicelist.servicelist.getCurrent()
					return 1
			else:
				playref = ref
			if self.pnav:
				self.pnav.stopService()
				self.currentlyPlayingServiceReference = playref
				self.currentlyPlayingServiceOrGroup = ref
				if InfoBarInstance and InfoBarInstance.servicelist.servicelist.setCurrent(ref, adjust):
					self.currentlyPlayingServiceOrGroup = InfoBarInstance.servicelist.servicelist.getCurrent()
				setPriorityFrontend = False
				if SystemInfo["DVB-T_priority_tuner_available"] or SystemInfo["DVB-C_priority_tuner_available"] or SystemInfo["DVB-S_priority_tuner_available"]:
					str_service = playref.toString()
					if '%3a//' not in str_service and not str_service.rsplit(":", 1)[1].startswith("/"):
						type_service = playref.getUnsignedData(4) >> 16
						if type_service == 0xEEEE:
							if config.usage.frontend_priority_dvbt.value != "-2":
								if config.usage.frontend_priority_dvbt.value != config.usage.frontend_priority.value:
									setPreferredTuner(int(config.usage.frontend_priority_dvbt.value))
									setPriorityFrontend = True
						elif type_service == 0xFFFF:
							if config.usage.frontend_priority_dvbc.value != "-2":
								if config.usage.frontend_priority_dvbc.value != config.usage.frontend_priority.value:
									setPreferredTuner(int(config.usage.frontend_priority_dvbc.value))
									setPriorityFrontend = True
						else:
							if config.usage.frontend_priority_dvbs.value != "-2":
								if config.usage.frontend_priority_dvbs.value != config.usage.frontend_priority.value:
									setPreferredTuner(int(config.usage.frontend_priority_dvbs.value))
									setPriorityFrontend = True
				if self.pnav.playService(playref):
					print "Failed to start", playref
					self.currentlyPlayingServiceReference = None
					self.currentlyPlayingServiceOrGroup = None
				if setPriorityFrontend:
					setPreferredTuner(int(config.usage.frontend_priority.value))
				return 0
		elif oldref and InfoBarInstance and InfoBarInstance.servicelist.servicelist.setCurrent(oldref, adjust):
			self.currentlyPlayingServiceOrGroup = InfoBarInstance.servicelist.servicelist.getCurrent()
		return 1

	def getCurrentlyPlayingServiceReference(self):
		return self.currentlyPlayingServiceReference

	def getCurrentlyPlayingServiceOrGroup(self):
		return self.currentlyPlayingServiceOrGroup

	def recordService(self, ref, simulate=False):
		service = None
		if not simulate: print "recording service: %s" % (str(ref))
		if isinstance(ref, ServiceReference.ServiceReference):
			ref = ref.ref
		if ref:
			if ref.flags & eServiceReference.isGroup:
				ref = getBestPlayableServiceReference(ref, eServiceReference(), simulate)
			service = ref and self.pnav and self.pnav.recordService(ref, simulate)
			if service is None:
				print "record returned non-zero"
		return service

	def stopRecordService(self, service):
		ret = self.pnav and self.pnav.stopRecordService(service)
		return ret

	def getRecordings(self, simulate=False):
		return self.pnav and self.pnav.getRecordings(simulate)

	def getCurrentService(self):
		if not self.currentlyPlayingService:
			self.currentlyPlayingService = self.pnav and self.pnav.getCurrentService()
		return self.currentlyPlayingService

	def stopService(self):
		if self.pnav:
			self.pnav.stopService()
		self.currentlyPlayingServiceReference = None
		self.currentlyPlayingServiceOrGroup = None

	def pause(self, p):
		return self.pnav and self.pnav.pause(p)

	def shutdown(self):
		self.RecordTimer.shutdown()
		self.ServiceHandler = None
		self.pnav = None

	def stopUserServices(self):
		self.stopService()

	def getClientsStreaming(self):
		return eStreamServer.getInstance() and eStreamServer.getInstance().getConnectedClients()

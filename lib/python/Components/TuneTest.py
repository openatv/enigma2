from enigma import eDVBFrontendParametersSatellite, eDVBFrontendParameters, eDVBResourceManager, eTimer

class Tuner:
	def __init__(self, frontend):
		self.frontend = frontend
	
	# transponder = (frequency, symbolrate, polarisation, fec, inversion, orbpos, system, modulation)
	#                    0         1             2         3       4         5       6        7
	def tune(self, transponder):
		if self.frontend:
			print "tuning to transponder with data", transponder
			parm = eDVBFrontendParametersSatellite()
			parm.frequency = transponder[0] * 1000
			parm.symbol_rate = transponder[1] * 1000
			parm.polarisation = transponder[2]
			parm.fec = transponder[3]
			parm.inversion = transponder[4]
			parm.orbital_position = transponder[5]
			parm.system = 0  # FIXMEE !! HARDCODED DVB-S (add support for DVB-S2)
			parm.modulation = 1 # FIXMEE !! HARDCODED QPSK 
			feparm = eDVBFrontendParameters()
			feparm.setDVBS(parm)
			self.lastparm = feparm
			self.frontend.tune(feparm)
	
	def retune(self):
		if self.frontend:
			self.frontend.tune(self.lastparm)

# tunes a list of transponders and checks, if they lock and optionally checks the onid/tsid combination
# 1) add transponders with addTransponder()
# 2) call run(<checkPIDs = True>)
# 3) finishedChecking() is called, when the run is finished
class TuneTest:
	def __init__(self, feid, stopOnSuccess = False, stopOnError = False):
		self.stopOnSuccess = stopOnSuccess
		self.stopOnError = stopOnError
		self.feid = feid
		self.transponderlist = []
		self.currTuned = None
		print "TuneTest for feid %d" % self.feid
		if not self.openFrontend():
			self.oldref = self.session.nav.getCurrentlyPlayingServiceReference()
			self.session.nav.stopService() # try to disable foreground service
			if not self.openFrontend():
				if self.session.pipshown: # try to disable pip
					self.session.pipshown = False
					del self.session.pip
					if not self.openFrontend():
						self.frontend = None # in normal case this should not happen
		self.tuner = Tuner(self.frontend)
		self.timer = eTimer()
		self.timer.callback.append(self.updateStatus)
			
	def updateStatus(self):
		dict = {}
		self.frontend.getFrontendStatus(dict)
		print "status:", dict

		stop = False
		
		if dict["tuner_state"] == "TUNING":
			self.timer.start(100, True)
			self.progressCallback((len(self.transponderlist), self.tuningtransponder, self.STATUS_TUNING, self.currTuned))
		elif self.checkPIDs and self.pidStatus == self.INTERNAL_PID_STATUS_NOOP:
			if dict["tuner_state"] == "LOCKED":
				print "acquiring TSID/ONID"
				# TODO start getting TSID/ONID
				self.pidStatus = self.INTERNAL_PID_STATUS_WAITING
			else:
				self.pidStatus = self.INTERNAL_PID_STATUS_FAILED
		elif self.checkPIDs and self.pidStatus == self.INTERNAL_PID_STATUS_WAITING:
			print "waiting for pids"			
		else:
			if dict["tuner_state"] == "LOSTLOCK" or dict["tuner_state"] == "FAILED":
				self.tuningtransponder = self.nextTransponder()
				self.failedTune.append([self.currTuned, self.oldTuned, "tune_failed"])
				if self.stopOnError == True:
					stop = True
			elif dict["tuner_state"] == "LOCKED":
				pidsFailed = False
				if self.checkPIDs:
					tsid = 0 # TODO read values
					onid = 0 # TODO read values
					if tsid != self.currTuned[8] or onid != self.currTuned[9]:
						self.failedTune.append([self.currTuned, self.oldTuned, "pids_failed"])
						pidsFailes = True
				elif not self.checkPIDs or (self.checkPids and not pidsFailed):  
					self.successfullyTune.append([self.currTuned, self.oldTuned])
					if self.stopOnSuccess == True:
						stop = True
				self.tuningtransponder = self.nextTransponder()
			else:
				print "************* tuner_state:", dict["tuner_state"]
				
			self.progressCallback((len(self.transponderlist), self.tuningtransponder, self.STATUS_NOOP, self.currTuned))
			
			if not stop:
				self.tune()
		if self.tuningtransponder < len(self.transponderlist) and not stop:
			self.timer.start(100, True)
			print "restart timer"
		else:
			self.progressCallback((len(self.transponderlist), self.tuningtransponder, self.STATUS_DONE, self.currTuned))
			print "finishedChecking"
			self.finishedChecking()
				
	def firstTransponder(self):
		print "firstTransponder:"
		index = 0
		if self.checkPIDs:
			print "checkPIDs-loop"
			# check for tsid != -1 and onid != -1 
			print "index:", index
			print "len(self.transponderlist):", len(self.transponderlist)
			while (index < len(self.transponderlist) and (self.transponderlist[index][8] == -1 or self.transponderlist[index][9] == -1)):
			 	index += 1
		print "FirstTransponder final index:", index
		return index
	
	def nextTransponder(self):
		index = self.tuningtransponder + 1
		if self.checkPIDs:
			# check for tsid != -1 and onid != -1 
			while (index < len(self.transponderlist) and self.transponderlist[index][8] != -1 and self.transponderlist[index][9] != -1):
			 	index += 1

		return index
	
	def finishedChecking(self):
		print "finished testing"
		print "successfull:", self.successfullyTune
		print "failed:", self.failedTune
	
	def openFrontend(self):
		res_mgr = eDVBResourceManager.getInstance()
		if res_mgr:
			self.raw_channel = res_mgr.allocateRawChannel(self.feid)
			if self.raw_channel:
				self.frontend = self.raw_channel.getFrontend()
				if self.frontend:
					return True
				else:
					print "getFrontend failed"
			else:
				print "getRawChannel failed"
		else:
			print "getResourceManager instance failed"
		return False

	def tune(self):
		print "tuning to", self.tuningtransponder
		if self.tuningtransponder < len(self.transponderlist):
			self.pidStatus = self.INTERNAL_PID_STATUS_NOOP
			self.oldTuned = self.currTuned
			self.currTuned = self.transponderlist[self.tuningtransponder]
			self.tuner.tune(self.transponderlist[self.tuningtransponder])		

	INTERNAL_PID_STATUS_NOOP = 0
	INTERNAL_PID_STATUS_WAITING = 1
	INTERNAL_PID_STATUS_SUCCESSFUL = 2
	INTERNAL_PID_STATUS_FAILED = 3
	
	def run(self, checkPIDs = False):
		self.checkPIDs = checkPIDs
		self.pidStatus = self.INTERNAL_PID_STATUS_NOOP
		self.failedTune = []
		self.successfullyTune = []
		self.tuningtransponder = self.firstTransponder()
		self.tune()
		self.progressCallback((len(self.transponderlist), self.tuningtransponder, self.STATUS_START, self.currTuned))
		self.timer.start(100, True)
	
	# transponder = (frequency, symbolrate, polarisation, fec, inversion, orbpos, <system>, <modulation>, <tsid>, <onid>)
	#                    0         1             2         3       4         5       6        7              8      9
	def addTransponder(self, transponder):
		self.transponderlist.append(transponder)
		
	def clearTransponder(self):
		self.transponderlist = []
		
	STATUS_START = 0
	STATUS_TUNING = 1
	STATUS_DONE = 2
	STATUS_NOOP = 3
	# can be overwritten
	# progress = (range, value, status, transponder)
	def progressCallback(self, progress):
		pass
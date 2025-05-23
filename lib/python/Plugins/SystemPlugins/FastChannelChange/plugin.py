from glob import glob
from os import access, W_OK
from enigma import iPlayableService, eTimer, eServiceReference, iRecordableService, eFCCServiceManager
from Components.config import config, ConfigSubsection, ConfigYesNo, ConfigSelection
from Components.ServiceEventTracker import ServiceEventTracker
from Components.SystemInfo import BoxInfo
from Plugins.Plugin import PluginDescriptor
from Screens.InfoBar import InfoBar
from Screens.Setup import Setup
from Screens.InfoBarGenerics import streamrelay

max_fcc = len(glob('/dev/fcc?'))
default_fcc = (max_fcc) > 5 and 5 or max_fcc

config.plugins.fccsetup = ConfigSubsection()
config.plugins.fccsetup.activate = ConfigYesNo(default=False)
config.plugins.fccsetup.maxfcc = ConfigSelection(default=default_fcc, choices=[(n, str(n)) for n in range(2, max_fcc + 1)])
config.plugins.fccsetup.zapupdown = ConfigYesNo(default=True)
config.plugins.fccsetup.history = ConfigYesNo(default=False)
config.plugins.fccsetup.priority = ConfigSelection(default="zapupdown", choices={"zapupdown": _("Zap Up/Down"), "historynextback": _("History Prev/Next")})
config.plugins.fccsetup.disableforrec = ConfigYesNo(default=True)

FccInstance = None


def FCCChanged():
	if FccInstance:
		FccInstance.FCCSetupChanged()


class FCCSupport:
	def __init__(self, session):
		self.session = session
		self.fccmgr = eFCCServiceManager.getInstance()
		self.fccList = []
		self.eventList = []
		self.createListTimer = eTimer()
		self.createListTimer.callback.append(self.FCCCreateList)
		self.getSrefTimer = eTimer()
		self.getSrefTimer.callback.append(self.FCCGetCurSref)
		self.fccEventTimer = eTimer()
		self.fccEventTimer.callback.append(self.FCCApplyEvent)
		self.fccForceStartTimer = eTimer()
		self.fccForceStartTimer.callback.append(self.FCCForceStart)
		self.fccResetTimer = eTimer()
		self.fccResetTimer.callback.append(self.FCCResetTimerForREC)
		self.activating = False
		self.hasfcc = max_fcc > 0
		self.fccSetupActivate = self.hasfcc and config.plugins.fccsetup.activate.value
		self.maxFCC = config.plugins.fccsetup.maxfcc.value
		self.zapdownEnable = config.plugins.fccsetup.zapupdown.value
		self.historyEnable = config.plugins.fccsetup.history.value
		self.priority = config.plugins.fccsetup.priority.value
		self.disableforrec = config.plugins.fccsetup.disableforrec.value
		self.fccmgr.setFCCEnable(int(self.fccSetupActivate))

		self.setProcFCC(self.fccSetupActivate)
		self.fccTimeoutTimer = eTimer()
		self.fccTimeoutTimer.callback.append(self.FCCTimeout)
		self.fccTimeoutEventCode = 0x102
		self.fccTimeoutWait = None

		self.fccmgr.m_fcc_event.get().append(self.FCCGetEvent)

		self.getRecordings()

		self.__event_tracker = None
		self.onClose = []
		self.changeEventTracker()
		BoxInfo.setMutableItem("FCCactive", self.fccSetupActivate)

#		from Screens.PictureInPicture import on_pip_start_stop
#		on_pip_start_stop.append(self.FCCForceStopforPIP)

	def setProcFCC(self, value):
		procPath = "/proc/stb/frontend/fbc/fcc"
		if access(procPath, W_OK):
			open(procPath, 'w').write(value and "enable" or "disable")
		else:
			print("[FCCSupport] write fail! : ", procPath)

	def gotRecordEvent(self, service, event):
		if self.disableforrec:
			if (not self.recordings) and (event == iRecordableService.evTuneStart):
				self.getRecordings()
				if self.recordings:
					self.FCCForceStopForREC()

			elif event == iRecordableService.evEnd:
				self.getRecordings()
				if not self.recordings:
					self.FCCForceStart()
		else:
			if event == iRecordableService.evTuneStart:
				self.FCCForceStopAndStart()

			elif event == iRecordableService.evEnd:
				self.fccForceStartTimer.stop()
				self.fccResetTimer.start(2000, True)

	def FCCForceStart(self):
		self.enableEventTracker(True)
		self.getEvStart()
		self.getEvTunedIn()

	def FCCForceStop(self):
		self.enableEventTracker(False)
		self.FCCDisableServices()
		self.FCCStopAllServices()

	def FCCForceStopAndStart(self):
		self.fccResetTimer.stop()
		self.FCCForceStop()
		self.fccForceStartTimer.start(2000, True)

	def FCCForceStopforPIP(self):
		self.FCCForceStopAndStart()

	def FCCForceStopForREC(self):
		self.FCCForceStop()

	def FCCResetTimerForREC(self):
		self.FCCForceStopForREC()
		self.FCCForceStart()

	def FCCSetupChanged(self):
		fcc_changed = False

		newFccSetupActivate = self.hasfcc and config.plugins.fccsetup.activate.value
		if self.fccSetupActivate != newFccSetupActivate:
			self.fccSetupActivate = newFccSetupActivate
			self.setProcFCC(self.fccSetupActivate)
			fcc_changed = True

		if config.plugins.fccsetup.maxfcc.value != self.maxFCC:
			self.maxFCC = config.plugins.fccsetup.maxfcc.value
			fcc_changed = True

		if self.zapdownEnable != config.plugins.fccsetup.zapupdown.value:
			self.zapdownEnable = config.plugins.fccsetup.zapupdown.value
			fcc_changed = True

		if self.historyEnable != config.plugins.fccsetup.history.value:
			self.historyEnable = config.plugins.fccsetup.history.value
			fcc_changed = True

		if self.priority != config.plugins.fccsetup.priority.value:
			self.priority = config.plugins.fccsetup.priority.value
			fcc_changed = True

		if self.disableforrec != config.plugins.fccsetup.disableforrec.value:
			self.disableforrec = config.plugins.fccsetup.disableforrec.value
			fcc_changed = True

		self.getRecordings()
		self.changeEventTracker()

		if (not self.fccSetupActivate) or (self.disableforrec and self.recordings):
			self.FCCDisableServices()

		if fcc_changed:
			self.fccmgr.setFCCEnable(int(self.fccSetupActivate))
			BoxInfo.setMutableItem("FCCactive", self.fccSetupActivate)

			curPlaying = self.session.nav.getCurrentlyPlayingServiceReference()
			if curPlaying:
				self.session.nav.stopService()
				self.session.nav.playService(curPlaying)

	# get current recording state
	def getRecordings(self):
		self.recordings = self.session.nav.getAnyRecordingsCount() > 0

	def addRecordEventCallback(self, enable=True):
		if enable:
			if self.gotRecordEvent not in self.session.nav.record_event:
				self.session.nav.record_event.append(self.gotRecordEvent)
		else:
			if self.gotRecordEvent in self.session.nav.record_event:
				self.session.nav.record_event.remove(self.gotRecordEvent)

	def changeEventTracker(self):
		if self.fccSetupActivate:
			self.addRecordEventCallback(True)
			if self.disableforrec and self.recordings:
				self.enableEventTracker(False)
			else:
				self.enableEventTracker(True)
		else:
			self.addRecordEventCallback(False)
			self.enableEventTracker(False)

	def enableEventTracker(self, activate):
		if activate:
			if not self.__event_tracker:
				self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
					iPlayableService.evStart: self.getEvStart,
					iPlayableService.evEnd: self.getEvEnd,
					iPlayableService.evTunedIn: self.getEvTunedIn,
					iPlayableService.evTuneFailed: self.getEvTuneFailed
					})

		elif self.__event_tracker:
			# run ServiceEventTracker.__del_event()
			for x in self.onClose:
				x()

			self.onClose = []
			self.__event_tracker = None

	def getEvStart(self):
		self.createListTimer.start(0, True)

	def getEvEnd(self):
		self.FCCDisableServices()

	def getEvTunedIn(self):
		self.FCCTryStart()

	def getEvTuneFailed(self):
		self.FCCTryStart()

	def isPlayableFCC(self, sref):
		playable = True
		if isinstance(sref, str):
			sref = eServiceReference(sref)

		if sref.type != 1:
			playable = False

		elif sref.getPath():  # is PVR? or streaming?
			playable = False

		elif int(sref.getData(0)) in (2, 10):  # is RADIO?
			playable = False

		playable = playable and not streamrelay.checkService(sref)

		return playable

	def getZapUpDownList(self):
		fccZapUpDownList = []
		serviceList = InfoBar.instance.servicelist.servicelist.getList()
		curServiceRef = InfoBar.instance.servicelist.servicelist.getCurrent().toString()

		serviceRefList = []
		for idx in range(len(serviceList)):
			sref = serviceList[idx].toString()
			if (sref.split(':')[1] == '0') and self.isPlayableFCC(sref):  # remove marker
				serviceRefList.append(sref)

		if curServiceRef in serviceRefList:
			serviceRefListSize = len(serviceRefList)
			curServiceIndex = serviceRefList.index(curServiceRef)

			for x in range(self.maxFCC - 1):
				if x > (serviceRefListSize - 2):  # if not ((x+1) <= (serviceRefListSize-1))
					break

				idx = (x // 2) + 1
				if x % 2:
					idx *= -1  # idx : [ 1, -1, 2, -2, 3, -3, 4, -4 ....]
				idx = (curServiceIndex + idx) % serviceRefListSize  # calc wraparound
				try:
					fccZapUpDownList.append(serviceRefList[idx])
				except:
					print("[FCCCreateList] append error, idx : %d" % idx)
					break

		return fccZapUpDownList

	def getHistoryPrevNextList(self):
		historyList = []
		history = InfoBar.instance.servicelist.history[:]
		history_pos = InfoBar.instance.servicelist.history_pos
		history_len = len(history)

		if history_len > 1 and history_pos > 0:
			historyPrev = history[history_pos - 1][:][-1].toString()
			if self.isPlayableFCC(historyPrev):
				historyList.append(historyPrev)

		if history_len > 1 and history_pos < (history_len - 1):
			historyNext = history[history_pos + 1][:][-1].toString()
			if self.isPlayableFCC(historyNext):
				historyList.append(historyNext)

		return historyList

	def FCCCreateList(self):
		if (not self.fccSetupActivate) or (self.disableforrec and self.recordings):
			return

		if InfoBar.instance:
			self.fccList = []
			fccZapUpDownList = []
			historyList = []

			if self.zapdownEnable:
				fccZapUpDownList = self.getZapUpDownList()

			if self.historyEnable:
				historyList = self.getHistoryPrevNextList()

			if self.priority == "zapupdown":
				fccZapDownLen = len(fccZapUpDownList)
				if fccZapDownLen:
					size = fccZapDownLen > 2 and 2 or fccZapDownLen
					self.fccList = fccZapUpDownList[:size]
					fccZapUpDownList = fccZapUpDownList[size:]

				self.addFCCList(historyList)
				self.addFCCList(fccZapUpDownList)
			else:
				self.addFCCList(historyList)
				self.addFCCList(fccZapUpDownList)

			self.FCCReconfigureFccList()

	def addFCCList(self, newlist):
		fccListMaxLen = self.maxFCC - 1
		for sref in newlist:
			if len(self.fccList) >= fccListMaxLen:
				break

			if sref not in self.fccList:
				self.fccList.append(sref)

	def FCCReconfigureFccList(self):
		stopFCCList = []
		currentFCCList = self.fccmgr.getFCCServiceList()

		for (sref, value) in currentFCCList.items():
			state = value[0]

			if state == 2:  # fcc_state_failed
				stopFCCList.append(sref)

			elif sref in self.fccList:  # check conflict FCC channel (decoder/prepare)
				self.fccList.remove(sref)

			elif state == 0:  # fcc_state_preparing
				stopFCCList.append(sref)

		for sref in stopFCCList:
			self.fccmgr.stopFCCService(eServiceReference(sref))

	def FCCTryStart(self):
		self.getSrefTimer.start(0, True)

	def FCCGetCurSref(self):
		if (not self.fccSetupActivate) or (self.disableforrec and self.recordings):
			return

		if self.createListTimer.isActive():
			self.createListTimer.stop()
			self.FCCCreateList()

		curSref = self.session.nav.getCurrentlyPlayingServiceReference()

		if curSref and self.isPlayableFCC(curSref):
			self.FCCStart()
		else:
			print("[FCCSupport] FCCGetCurSref get current serviceReference failed!!")

	def FCCStart(self):
		self.activating = True
		self.FCCGetEvent(iPlayableService.evTunedIn)

	def FCCGetEvent(self, event):
		if self.activating and event in (iPlayableService.evTunedIn, iPlayableService.evTuneFailed, iPlayableService.evFccFailed, self.fccTimeoutEventCode):
			self.eventList.append(event)
			self.fccEventTimer.start(0, True)

	def FCCApplyEvent(self):
		if not self.activating:
			return

		while self.eventList:
			event = self.eventList.pop(0)

			self.FCCTimeoutTimerStop()

			if event in (iPlayableService.evTuneFailed, iPlayableService.evFccFailed):
				self.fccmgr.stopFCCService()  # stop FCC Services in failed state

			if not self.FCCCheckAndTimerStart() and len(self.fccList):
				sref = self.fccList.pop(0)
				if self.isPlayableFCC(sref):  # remove PVR, streaming, radio channels
					self.fccmgr.playFCCService(eServiceReference(sref))
					self.FCCTimeoutTimerStart(sref)

	def FCCStopAllServices(self):
		self.FCCTimeoutTimerStop()
		fccServiceList = self.fccmgr.getFCCServiceList()
		for (sref, value) in fccServiceList.items():
			state = value[0]
			if state != 1:  # 1  : fcc_state_decoding
				self.fccmgr.stopFCCService(eServiceReference(sref))

	def FCCDisableServices(self):
		self.FCCTimeoutTimerStop()
		self.getSrefTimer.stop()
		self.activating = False
		self.fccList = []
		self.fccEventTimer.stop()
		self.fccmgr.stopFCCService()
		self.eventList = []

	def FCCCheckNoLocked(self):
		for (sref, value) in self.fccmgr.getFCCServiceList().items():
			state = value[0]
			locked = value[1]
			if state != 1 and locked == 0:  # no fcc decoding and no locked
				return sref
		return None

	def FCCTimeout(self):
		sref = self.FCCCheckNoLocked()
		if sref and sref == self.fccTimeoutWait:
			self.fccmgr.stopFCCService(eServiceReference(sref))
			self.FCCGetEvent(self.fccTimeoutEventCode)

	def FCCCheckAndTimerStart(self):
		sref = self.FCCCheckNoLocked()
		if sref:
			self.FCCTimeoutTimerStart(sref)
			return True
		return False

	def FCCTimeoutTimerStart(self, sref):
		self.fccTimeoutWait = sref
		self.fccTimeoutTimer.start(5000, True)

	def FCCTimeoutTimerStop(self):
		self.fccTimeoutWait = None
		self.fccTimeoutTimer.stop()


class FCCSetup(Setup):
	def __init__(self, session):
		Setup.__init__(self, session, "fcc", plugin="SystemPlugins/FastChannelChange")

	def changedEntry(self):
		if self.getCurrentItem() in (config.plugins.fccsetup.zapupdown, config.plugins.fccsetup.history):
			if not (config.plugins.fccsetup.zapupdown.value or config.plugins.fccsetup.history.value):
				if self.getCurrentItem() == config.plugins.fccsetup.history:
					config.plugins.fccsetup.zapupdown.value = True
				else:
					config.plugins.fccsetup.history.value = True
			elif (config.plugins.fccsetup.zapupdown.value and config.plugins.fccsetup.history.value):
				if config.plugins.fccsetup.maxfcc.value < 5:
					config.plugins.fccsetup.maxfcc.value = max_fcc if max_fcc < 5 else 5
		Setup.changedEntry(self)

	def keySave(self):
		Setup.keySave(self)
		FCCChanged()


def ToggleUpdate():
	if config.plugins.fccsetup.activate.value:
		config.plugins.fccsetup.activate.value = False
	else:
		config.plugins.fccsetup.activate.value = True
	config.plugins.fccsetup.activate.save()
	FCCChanged()


def FCCSupportInit(reason, **kwargs):
	if "session" in kwargs:
		global FccInstance
		FccInstance = FCCSupport(kwargs["session"])


def showFCCExtentionMenu():
	currentScreenName = None
	if FccInstance:
		currentScreenName = FccInstance.session.current_dialog.__class__.__name__
	return (currentScreenName == "InfoBar")


def getExtensionName():
	return _("Disable Fast Channel Change") if config.plugins.fccsetup.activate.value else _("Enable Fast Channel Change")


def addExtentions(infobarExtensions):
	infobarExtensions.addExtension((getExtensionName, ToggleUpdate, showFCCExtentionMenu), None)


def FCCStart(session, **kwargs):
	session.open(FCCSetup)


def main(menuid, **kwargs):
	if menuid == "scan":
		return [(_("Fast Channel Change"), FCCStart, "FCCSetup", 5)]
	else:
		return []


def Plugins(**kwargs):
	list = []

	if max_fcc > 0:
		list.append(
			PluginDescriptor(name="FCCSupport",
			description="Fast Channel Change support",
			where=[PluginDescriptor.WHERE_SESSIONSTART],
			fnc=FCCSupportInit))

		list.append(
			PluginDescriptor(name="FCCExtensionMenu",
			description="Fast Channel Change menu",
			where=[PluginDescriptor.WHERE_EXTENSIONSINGLE],
			fnc=addExtentions))

		list.append(
			PluginDescriptor(name="FCCSetup",
			description=_("Fast Channel Change Setup"),
			where=[PluginDescriptor.WHERE_MENU],
			needsRestart=False,
			fnc=main))

	return list

from ChannelSelection import ChannelSelection, BouquetSelector

from Components.ActionMap import ActionMap, HelpableActionMap
from Components.ActionMap import NumberActionMap
from Components.BlinkingPixmap import BlinkingPixmapConditional
from Components.Harddisk import harddiskmanager
from Components.Input import Input
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.PluginComponent import plugins
from Components.ServiceEventTracker import ServiceEventTracker
from Components.Sources.Source import ObsoleteSource
from Components.Sources.Boolean import Boolean
from Components.config import config, ConfigBoolean, ConfigClock
from Components.SystemInfo import SystemInfo
from EpgSelection import EPGSelection
from Plugins.Plugin import PluginDescriptor

from Screen import Screen
from Screens.ChoiceBox import ChoiceBox
from Screens.Dish import Dish
from Screens.EventView import EventViewEPGSelect, EventViewSimple
from Screens.InputBox import InputBox
from Screens.MessageBox import MessageBox
from Screens.MinuteInput import MinuteInput
from Screens.TimerSelection import TimerSelection
from Screens.PictureInPicture import PictureInPicture
from Screens.SubtitleDisplay import SubtitleDisplay
from Screens.RdsDisplay import RdsInfoDisplay, RassInteractive
from Screens.SleepTimerEdit import SleepTimerEdit
from Screens.TimeDateInput import TimeDateInput
from ServiceReference import ServiceReference

from Tools import Notifications
from Tools.Directories import SCOPE_HDD, resolveFilename

from enigma import eTimer, eServiceCenter, eDVBServicePMTHandler, iServiceInformation, \
	iPlayableService, eServiceReference, eDVBResourceManager, iFrontendInformation, eEPGCache

from time import time, localtime, strftime
from os import stat as os_stat
from bisect import insort

# hack alert!
from Menu import MainMenu, mdom

class InfoBarDish:
	def __init__(self):
		self.dishDialog = self.session.instantiateDialog(Dish)

class InfoBarShowHide:
	""" InfoBar show/hide control, accepts toggleShow and hide actions, might start
	fancy animations. """
	STATE_HIDDEN = 0
	STATE_HIDING = 1
	STATE_SHOWING = 2
	STATE_SHOWN = 3

	def __init__(self):
		self["ShowHideActions"] = ActionMap( ["InfobarShowHideActions"] ,
			{
				"toggleShow": self.toggleShow,
				"hide": self.hide,
			}, 1) # lower prio to make it possible to override ok and cancel..

		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
			{
				iPlayableService.evStart: self.serviceStarted,
			})

		self.__state = self.STATE_SHOWN
		self.__locked = 0

		self.hideTimer = eTimer()
		self.hideTimer.callback.append(self.doTimerHide)
		self.hideTimer.start(5000, True)

		self.onShow.append(self.__onShow)
		self.onHide.append(self.__onHide)

	def serviceStarted(self):
		if self.execing:
			if config.usage.show_infobar_on_zap.value:
				self.doShow()

	def __onShow(self):
		self.__state = self.STATE_SHOWN
		self.startHideTimer()

	def startHideTimer(self):
		if self.__state == self.STATE_SHOWN and not self.__locked:
			idx = config.usage.infobar_timeout.index
			if idx:
				self.hideTimer.start(idx*1000, True)

	def __onHide(self):
		self.__state = self.STATE_HIDDEN

	def doShow(self):
		self.show()
		self.startHideTimer()

	def doTimerHide(self):
		self.hideTimer.stop()
		if self.__state == self.STATE_SHOWN:
			self.hide()

	def toggleShow(self):
		if self.__state == self.STATE_SHOWN:
			self.hide()
			self.hideTimer.stop()
		elif self.__state == self.STATE_HIDDEN:
			self.show()

	def lockShow(self):
		self.__locked = self.__locked + 1
		if self.execing:
			self.show()
			self.hideTimer.stop()

	def unlockShow(self):
		self.__locked = self.__locked - 1
		if self.execing:
			self.startHideTimer()

#	def startShow(self):
#		self.instance.m_animation.startMoveAnimation(ePoint(0, 600), ePoint(0, 380), 100)
#		self.__state = self.STATE_SHOWN
#
#	def startHide(self):
#		self.instance.m_animation.startMoveAnimation(ePoint(0, 380), ePoint(0, 600), 100)
#		self.__state = self.STATE_HIDDEN

class NumberZap(Screen):
	def quit(self):
		self.Timer.stop()
		self.close(0)

	def keyOK(self):
		self.Timer.stop()
		self.close(int(self["number"].getText()))

	def keyNumberGlobal(self, number):
		self.Timer.start(3000, True)		#reset timer
		self.field = self.field + str(number)
		self["number"].setText(self.field)
		if len(self.field) >= 4:
			self.keyOK()

	def __init__(self, session, number):
		Screen.__init__(self, session)
		self.field = str(number)

		self["channel"] = Label(_("Channel:"))

		self["number"] = Label(self.field)

		self["actions"] = NumberActionMap( [ "SetupActions" ],
			{
				"cancel": self.quit,
				"ok": self.keyOK,
				"1": self.keyNumberGlobal,
				"2": self.keyNumberGlobal,
				"3": self.keyNumberGlobal,
				"4": self.keyNumberGlobal,
				"5": self.keyNumberGlobal,
				"6": self.keyNumberGlobal,
				"7": self.keyNumberGlobal,
				"8": self.keyNumberGlobal,
				"9": self.keyNumberGlobal,
				"0": self.keyNumberGlobal
			})

		self.Timer = eTimer()
		self.Timer.callback.append(self.keyOK)
		self.Timer.start(3000, True)

class InfoBarNumberZap:
	""" Handles an initial number for NumberZapping """
	def __init__(self):
		self["NumberActions"] = NumberActionMap( [ "NumberActions"],
			{
				"1": self.keyNumberGlobal,
				"2": self.keyNumberGlobal,
				"3": self.keyNumberGlobal,
				"4": self.keyNumberGlobal,
				"5": self.keyNumberGlobal,
				"6": self.keyNumberGlobal,
				"7": self.keyNumberGlobal,
				"8": self.keyNumberGlobal,
				"9": self.keyNumberGlobal,
				"0": self.keyNumberGlobal,
			})

	def keyNumberGlobal(self, number):
#		print "You pressed number " + str(number)
		if number == 0:
			if isinstance(self, InfoBarPiP) and self.pipHandles0Action():
				self.pipDoHandle0Action()
			else:
				self.servicelist.recallPrevService()
		else:
			if self.has_key("TimeshiftActions") and not self.timeshift_enabled:
				self.session.openWithCallback(self.numberEntered, NumberZap, number)

	def numberEntered(self, retval):
#		print self.servicelist
		if retval > 0:
			self.zapToNumber(retval)

	def searchNumberHelper(self, serviceHandler, num, bouquet):
		servicelist = serviceHandler.list(bouquet)
		if not servicelist is None:
			while num:
				serviceIterator = servicelist.getNext()
				if not serviceIterator.valid(): #check end of list
					break
				playable = not (serviceIterator.flags & (eServiceReference.isMarker|eServiceReference.isDirectory))
				if playable:
					num -= 1;
			if not num: #found service with searched number ?
				return serviceIterator, 0
		return None, num

	def zapToNumber(self, number):
		bouquet = self.servicelist.bouquet_root
		service = None
		serviceHandler = eServiceCenter.getInstance()
		if not config.usage.multibouquet.value:
			service, number = self.searchNumberHelper(serviceHandler, number, bouquet)
		else:
			bouquetlist = serviceHandler.list(bouquet)
			if not bouquetlist is None:
				while number:
					bouquet = bouquetlist.getNext()
					if not bouquet.valid(): #check end of list
						break
					if bouquet.flags & eServiceReference.isDirectory:
						service, number = self.searchNumberHelper(serviceHandler, number, bouquet)
		if not service is None:
			if self.servicelist.getRoot() != bouquet: #already in correct bouquet?
				self.servicelist.clearPath()
				if self.servicelist.bouquet_root != bouquet:
					self.servicelist.enterPath(self.servicelist.bouquet_root)
				self.servicelist.enterPath(bouquet)
			self.servicelist.setCurrentSelection(service) #select the service in servicelist
			self.servicelist.zap()

config.misc.initialchannelselection = ConfigBoolean(default = True)

class InfoBarChannelSelection:
	""" ChannelSelection - handles the channelSelection dialog and the initial
	channelChange actions which open the channelSelection dialog """
	def __init__(self):
		#instantiate forever
		self.servicelist = self.session.instantiateDialog(ChannelSelection)

		if config.misc.initialchannelselection.value:
			self.onShown.append(self.firstRun)

		self["ChannelSelectActions"] = HelpableActionMap(self, "InfobarChannelSelection",
			{
				"switchChannelUp": (self.switchChannelUp, _("open servicelist(up)")),
				"switchChannelDown": (self.switchChannelDown, _("open servicelist(down)")),
				"zapUp": (self.zapUp, _("previous channel")),
				"zapDown": (self.zapDown, _("next channel")),
				"historyBack": (self.historyBack, _("previous channel in history")),
				"historyNext": (self.historyNext, _("next channel in history")),
				"openServiceList": (self.openServiceList, _("open servicelist")),
			})

	def showTvChannelList(self, zap=False):
		self.servicelist.setModeTv()
		if zap:
			self.servicelist.zap()
		self.session.execDialog(self.servicelist)

	def showRadioChannelList(self, zap=False):
		self.servicelist.setModeRadio()
		if zap:
			self.servicelist.zap()
		self.session.execDialog(self.servicelist)

	def firstRun(self):
		self.onShown.remove(self.firstRun)
		config.misc.initialchannelselection.value = False
		config.misc.initialchannelselection.save()
		self.switchChannelDown()

	def historyBack(self):
		self.servicelist.historyBack()

	def historyNext(self):
		self.servicelist.historyNext()

	def switchChannelUp(self):
		self.servicelist.moveUp()
		self.session.execDialog(self.servicelist)

	def switchChannelDown(self):
		self.servicelist.moveDown()
		self.session.execDialog(self.servicelist)

	def openServiceList(self):
		self.session.execDialog(self.servicelist)

	def zapUp(self):
		if self.servicelist.inBouquet():
			prev = self.servicelist.getCurrentSelection()
			if prev:
				prev = prev.toString()
				while True:
					if config.usage.quickzap_bouquet_change.value:
						if self.servicelist.atBegin():
							self.servicelist.prevBouquet()
					self.servicelist.moveUp()
					cur = self.servicelist.getCurrentSelection()
					if not cur or (not (cur.flags & 64)) or cur.toString() == prev:
						break
		else:
			self.servicelist.moveUp()
		self.servicelist.zap()

	def zapDown(self):
		if self.servicelist.inBouquet():
			prev = self.servicelist.getCurrentSelection()
			if prev:
				prev = prev.toString()
				while True:
					if config.usage.quickzap_bouquet_change.value and self.servicelist.atEnd():
						self.servicelist.nextBouquet()
					else:
						self.servicelist.moveDown()
					cur = self.servicelist.getCurrentSelection()
					if not cur or (not (cur.flags & 64)) or cur.toString() == prev:
						break
		else:
			self.servicelist.moveDown()
		self.servicelist.zap()

class InfoBarMenu:
	""" Handles a menu action, to open the (main) menu """
	def __init__(self):
		self["MenuActions"] = HelpableActionMap(self, "InfobarMenuActions",
			{
				"mainMenu": (self.mainMenu, _("Enter main menu...")),
			})
		self.session.infobar = None

	def mainMenu(self):
		print "loading mainmenu XML..."
		menu = mdom.childNodes[0]
		assert menu.tagName == "menu", "root element in menu must be 'menu'!"

		self.session.infobar = self
		# so we can access the currently active infobar from screens opened from within the mainmenu
		# at the moment used from the SubserviceSelection

		self.session.openWithCallback(self.mainMenuClosed, MainMenu, menu, menu.childNodes)

	def mainMenuClosed(self, *val):
		self.session.infobar = None

class InfoBarSimpleEventView:
	""" Opens the Eventview for now/next """
	def __init__(self):
		self["EPGActions"] = HelpableActionMap(self, "InfobarEPGActions",
			{
				"showEventInfo": (self.openEventView, _("show event details")),
			})

	def openEventView(self):
		self.epglist = [ ]
		service = self.session.nav.getCurrentService()
		ref = self.session.nav.getCurrentlyPlayingServiceReference()
		info = service.info()
		ptr=info.getEvent(0)
		if ptr:
			self.epglist.append(ptr)
		ptr=info.getEvent(1)
		if ptr:
			self.epglist.append(ptr)
		if len(self.epglist) > 0:
			self.session.open(EventViewSimple, self.epglist[0], ServiceReference(ref), self.eventViewCallback)

	def eventViewCallback(self, setEvent, setService, val): #used for now/next displaying
		if len(self.epglist) > 1:
			tmp = self.epglist[0]
			self.epglist[0]=self.epglist[1]
			self.epglist[1]=tmp
			setEvent(self.epglist[0])

class InfoBarEPG:
	""" EPG - Opens an EPG list when the showEPGList action fires """
	def __init__(self):
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
			{
				iPlayableService.evUpdatedEventInfo: self.__evEventInfoChanged,
			})

		self.is_now_next = False
		self.dlg_stack = [ ]
		self.bouquetSel = None
		self.eventView = None
		self["EPGActions"] = HelpableActionMap(self, "InfobarEPGActions",
			{
				"showEventInfo": (self.openEventView, _("show EPG...")),
				"showSingleServiceEPG": (self.openSingleServiceEPG, _("show single service EPG...")),
				"showInfobarOrEpgWhenInfobarAlreadyVisible": self.showEventInfoWhenNotVisible,
			})

	def showEventInfoWhenNotVisible(self):
		if self.shown:
			self.openEventView()
		else:
			self.toggleShow()
			return 1

	def zapToService(self, service):
		if not service is None:
			if self.servicelist.getRoot() != self.epg_bouquet: #already in correct bouquet?
				self.servicelist.clearPath()
				if self.servicelist.bouquet_root != self.epg_bouquet:
					self.servicelist.enterPath(self.servicelist.bouquet_root)
				self.servicelist.enterPath(self.epg_bouquet)
			self.servicelist.setCurrentSelection(service) #select the service in servicelist
			self.servicelist.zap()

	def getBouquetServices(self, bouquet):
		services = [ ]
		servicelist = eServiceCenter.getInstance().list(bouquet)
		if not servicelist is None:
			while True:
				service = servicelist.getNext()
				if not service.valid(): #check if end of list
					break
				if service.flags & (eServiceReference.isDirectory | eServiceReference.isMarker): #ignore non playable services
					continue
				services.append(ServiceReference(service))
		return services

	def openBouquetEPG(self, bouquet, withCallback=True):
		services = self.getBouquetServices(bouquet)
		if len(services):
			self.epg_bouquet = bouquet
			if withCallback:
				self.dlg_stack.append(self.session.openWithCallback(self.closed, EPGSelection, services, self.zapToService, None, self.changeBouquetCB))
			else:
				self.session.open(EPGSelection, services, self.zapToService, None, self.changeBouquetCB)

	def changeBouquetCB(self, direction, epg):
		if self.bouquetSel:
			if direction > 0:
				self.bouquetSel.down()
			else:
				self.bouquetSel.up()
			bouquet = self.bouquetSel.getCurrent()
			services = self.getBouquetServices(bouquet)
			if len(services):
				self.epg_bouquet = bouquet
				epg.setServices(services)

	def closed(self, ret=False):
		closedScreen = self.dlg_stack.pop()
		if self.bouquetSel and closedScreen == self.bouquetSel:
			self.bouquetSel = None
		elif self.eventView and closedScreen == self.eventView:
			self.eventView = None
		if ret:
			dlgs=len(self.dlg_stack)
			if dlgs > 0:
				self.dlg_stack[dlgs-1].close(dlgs > 1)

	def openMultiServiceEPG(self, withCallback=True):
		bouquets = self.servicelist.getBouquetList()
		if bouquets is None:
			cnt = 0
		else:
			cnt = len(bouquets)
		if cnt > 1: # show bouquet list
			if withCallback:
				self.bouquetSel = self.session.openWithCallback(self.closed, BouquetSelector, bouquets, self.openBouquetEPG, enableWrapAround=True)
				self.dlg_stack.append(self.bouquetSel)
			else:
				self.bouquetSel = self.session.open(BouquetSelector, bouquets, self.openBouquetEPG, enableWrapAround=True)
		elif cnt == 1:
			self.openBouquetEPG(bouquets[0][1], withCallback)

	def openSingleServiceEPG(self):
		ref=self.session.nav.getCurrentlyPlayingServiceReference()
		self.session.open(EPGSelection, ref)

	def openSimilarList(self, eventid, refstr):
		self.session.open(EPGSelection, refstr, None, eventid)

	def getNowNext(self):
		self.epglist = [ ]
		service = self.session.nav.getCurrentService()
		info = service and service.info()
		ptr = info and info.getEvent(0)
		if ptr:
			self.epglist.append(ptr)
		ptr = info and info.getEvent(1)
		if ptr:
			self.epglist.append(ptr)

	def __evEventInfoChanged(self):
		if self.is_now_next and len(self.dlg_stack) == 1:
			self.getNowNext()
			assert self.eventView
			if len(self.epglist):
				self.eventView.setEvent(self.epglist[0])

	def openEventView(self):
		ref = self.session.nav.getCurrentlyPlayingServiceReference()
		self.getNowNext()
		if len(self.epglist) == 0:
			self.is_now_next = False
			epg = eEPGCache.getInstance()
			ptr = ref and ref.valid() and epg.lookupEventTime(ref, -1)
			if ptr:
				self.epglist.append(ptr)
				ptr = epg.lookupEventTime(ref, ptr.getBeginTime(), +1)
				if ptr:
					self.epglist.append(ptr)
		else:
			self.is_now_next = True
		if len(self.epglist) > 0:
			self.eventView = self.session.openWithCallback(self.closed, EventViewEPGSelect, self.epglist[0], ServiceReference(ref), self.eventViewCallback, self.openSingleServiceEPG, self.openMultiServiceEPG, self.openSimilarList)
			self.dlg_stack.append(self.eventView)
		else:
			print "no epg for the service avail.. so we show multiepg instead of eventinfo"
			self.openMultiServiceEPG(False)

	def eventViewCallback(self, setEvent, setService, val): #used for now/next displaying
		if len(self.epglist) > 1:
			tmp = self.epglist[0]
			self.epglist[0]=self.epglist[1]
			self.epglist[1]=tmp
			setEvent(self.epglist[0])

class InfoBarTuner:
	"""provides a snr/agc/ber display"""
	def __init__(self):
		self["FrontendStatus"] = ObsoleteSource(new_source = "session.FrontendStatus", removal_date = "2008-01")

class InfoBarEvent:
	"""provides a current/next event info display"""
	def __init__(self):
		self["Event_Now"] = ObsoleteSource(new_source = "session.Event_Now", removal_date = "2008-01")
		self["Event_Next"] = ObsoleteSource(new_source = "session.Event_Next", removal_date = "2008-01")

class InfoBarRdsDecoder:
	"""provides RDS and Rass support/display"""
	def __init__(self):
		self.rds_display = self.session.instantiateDialog(RdsInfoDisplay)
		self.rass_interactive = None

		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
			{
				iPlayableService.evEnd: self.__serviceStopped,
				iPlayableService.evUpdatedRassSlidePic: self.RassSlidePicChanged
			})

		self["RdsActions"] = ActionMap(["InfobarRdsActions"],
		{
			"startRassInteractive": self.startRassInteractive
		},-1)

		self["RdsActions"].setEnabled(False)

		self.onLayoutFinish.append(self.rds_display.show)
		self.rds_display.onRassInteractivePossibilityChanged.append(self.RassInteractivePossibilityChanged)

	def RassInteractivePossibilityChanged(self, state):
		self["RdsActions"].setEnabled(state)

	def RassSlidePicChanged(self):
		if not self.rass_interactive:
			service = self.session.nav.getCurrentService()
			decoder = service and service.rdsDecoder()
			if decoder:
				decoder.showRassSlidePicture()

	def __serviceStopped(self):
		if self.rass_interactive is not None:
			rass_interactive = self.rass_interactive
			self.rass_interactive = None
			rass_interactive.close()

	def startRassInteractive(self):
		self.rds_display.hide()
		self.rass_interactive = self.session.openWithCallback(self.RassInteractiveClosed, RassInteractive)

	def RassInteractiveClosed(self, *val):
		if self.rass_interactive is not None:
			self.rass_interactive = None
			self.RassSlidePicChanged()
		self.rds_display.show()

class InfoBarServiceName:
	def __init__(self):
		self["CurrentService"] = ObsoleteSource(new_source = "session.CurrentService", removal_date = "2008-01")

class InfoBarSeek:
	"""handles actions like seeking, pause"""

	SEEK_STATE_PLAY = (0, 0, 0, ">")
	SEEK_STATE_PAUSE = (1, 0, 0, "||")
	SEEK_STATE_EOF = (1, 0, 0, "END")

	def __init__(self, actionmap = "InfobarSeekActions"):
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
			{
				iPlayableService.evSeekableStatusChanged: self.__seekableStatusChanged,
				iPlayableService.evStart: self.__serviceStarted,

				iPlayableService.evEOF: self.__evEOF,
				iPlayableService.evSOF: self.__evSOF,
			})
		self.eofState = 0
		self.eofTimer = eTimer()
		self.eofTimer.timeout.get().append(self.doEof)
		self.eofInhibitTimer = eTimer()
		self.eofInhibitTimer.timeout.get().append(self.inhibitEof)

		self.minSpeedBackward = 16

		class InfoBarSeekActionMap(HelpableActionMap):
			def __init__(self, screen, *args, **kwargs):
				HelpableActionMap.__init__(self, screen, *args, **kwargs)
				self.screen = screen

			def action(self, contexts, action):
				print "action:", action
				if action[:5] == "seek:":
					time = int(action[5:])
					self.screen.doSeekRelative(time * 90000)
					return 1
				elif action[:8] == "seekdef:":
					key = int(action[8:])
					time = [-config.seek.selfdefined_13.value, False, config.seek.selfdefined_13.value,
						-config.seek.selfdefined_46.value, False, config.seek.selfdefined_46.value,
						-config.seek.selfdefined_79.value, False, config.seek.selfdefined_79.value][key-1]
					self.screen.doSeekRelative(time * 90000)
					return 1					
				else:
					return HelpableActionMap.action(self, contexts, action)

		self["SeekActions"] = InfoBarSeekActionMap(self, actionmap,
			{
				"playpauseService": self.playpauseService,
				"pauseService": (self.pauseService, _("pause")),
				"unPauseService": (self.unPauseService, _("continue")),

				"seekFwd": (self.seekFwd, _("skip forward")),
				"seekFwdManual": (self.seekFwdManual, _("skip forward (enter time)")),
				"seekBack": (self.seekBack, _("skip backward")),
				"seekBackManual": (self.seekBackManual, _("skip backward (enter time)"))
			}, prio=-1)
			# give them a little more priority to win over color buttons

		self["SeekActions"].setEnabled(False)

		self.seekstate = self.SEEK_STATE_PLAY
		self.lastseekstate = self.SEEK_STATE_PLAY

		self.onPlayStateChanged = [ ]

		self.lockedBecauseOfSkipping = False

		self.__seekableStatusChanged()

	def makeStateForward(self, n):
		minspeed = config.seek.stepwise_minspeed.value
		repeat = int(config.seek.stepwise_repeat.value)
		if minspeed != "Never" and n >= int(minspeed) and repeat > 1:
			return (0, n * repeat, repeat, ">> %dx" % n)
		else:
			return (0, n, 0, ">> %dx" % n)

	def makeStateBackward(self, n):
		minspeed = config.seek.stepwise_minspeed.value
		repeat = int(config.seek.stepwise_repeat.value)
		if n < self.minSpeedBackward:
			r = (self.minSpeedBackward - 1)/ n + 1
			if minspeed != "Never" and n >= int(minspeed) and repeat > 1:
				r = max(r, repeat)
			return (0, -n * r, r, "<< %dx" % n)
		elif minspeed != "Never" and n >= int(minspeed) and repeat > 1:
			return (0, -n * repeat, repeat, "<< %dx" % n)
		else:
			return (0, -n, 0, "<< %dx" % n)

	def makeStateSlowMotion(self, n):
		return (0, 0, n, "/%d" % n)

	def isStateForward(self, state):
		return state[1] > 1

	def isStateBackward(self, state):
		return state[1] < 0

	def isStateSlowMotion(self, state):
		return state[1] == 0 and state[2] > 1

	def getHigher(self, n, lst):
		for x in lst:
			if x > n:
				return x
		return False

	def getLower(self, n, lst):
		lst = lst+[]
		lst.reverse()
		for x in lst:
			if x < n:
				return x
		return False

	def showAfterSeek(self):
		if isinstance(self, InfoBarShowHide):
			self.doShow()

	def up(self):
		pass

	def down(self):
		pass

	def getSeek(self):
		service = self.session.nav.getCurrentService()
		if service is None:
			return None

		seek = service.seek()

		if seek is None or not seek.isCurrentlySeekable():
			return None

		return seek

	def isSeekable(self):
		if self.getSeek() is None:
			return False
		return True

	def __seekableStatusChanged(self):
		print "seekable status changed!"
		if not self.isSeekable():
			self["SeekActions"].setEnabled(False)
			print "not seekable, return to play"
			self.setSeekState(self.SEEK_STATE_PLAY)
		else:
			self["SeekActions"].setEnabled(True)
			print "seekable"

	def __serviceStarted(self):
		self.seekstate = self.SEEK_STATE_PLAY
		self.__seekableStatusChanged()
		if self.eofState != 0:
			self.eofTimer.stop()
		self.eofState = 0

	def setSeekState(self, state):
		service = self.session.nav.getCurrentService()

		if service is None:
			return False

		if not self.isSeekable():
			if state not in [self.SEEK_STATE_PLAY, self.SEEK_STATE_PAUSE]:
				state = self.SEEK_STATE_PLAY

		pauseable = service.pause()

		if pauseable is None:
			print "not pauseable."
			state = self.SEEK_STATE_PLAY

		oldstate = self.seekstate
		self.seekstate = state

		for i in range(3):
			if oldstate[i] != self.seekstate[i]:
				(self.session.nav.pause, pauseable.setFastForward, pauseable.setSlowMotion)[i](self.seekstate[i])

		for c in self.onPlayStateChanged:
			c(self.seekstate)

		self.checkSkipShowHideLock()

		return True

	def playpauseService(self):
		if self.seekstate != self.SEEK_STATE_PLAY:
			self.unPauseService()
		else:
			self.pauseService()

	def pauseService(self):
		if self.seekstate == self.SEEK_STATE_PAUSE:
			if config.seek.on_pause.value == "play":
				self.unPauseService()
			elif config.seek.on_pause.value == "step":
				self.doSeekRelative(0)
			elif config.seek.on_pause.value == "last":
				self.setSeekState(self.lastseekstate)
				self.lastseekstate = self.SEEK_STATE_PLAY
		else:
			if self.seekstate != self.SEEK_STATE_EOF:
				self.lastseekstate = self.seekstate
			self.setSeekState(self.SEEK_STATE_PAUSE);

	def unPauseService(self):
		print "unpause"
		if self.seekstate == self.SEEK_STATE_PLAY:
			return 0
		self.setSeekState(self.SEEK_STATE_PLAY)

	def doSeek(self, pts):
		seekable = self.getSeek()
		if seekable is None:
			return
		prevstate = self.seekstate
		if self.eofState == 1:
			self.eofState = 2
			self.inhibitEof()
		if self.seekstate == self.SEEK_STATE_EOF:
			if prevstate == self.SEEK_STATE_PAUSE:
				self.setSeekState(self.SEEK_STATE_PAUSE)
			else:
				self.setSeekState(self.SEEK_STATE_PLAY)
		self.eofInhibitTimer.start(200, True)
		seekable.seekTo(pts)

	def doSeekRelative(self, pts):
		seekable = self.getSeek()
		if seekable is None:
			return
		prevstate = self.seekstate
		if self.eofState == 1:
			self.eofState = 2
			self.inhibitEof()
		if self.seekstate == self.SEEK_STATE_EOF:
			if prevstate == self.SEEK_STATE_PAUSE:
				self.setSeekState(self.SEEK_STATE_PAUSE)
			else:
				self.setSeekState(self.SEEK_STATE_PLAY)
		self.eofInhibitTimer.start(200, True)
		seekable.seekRelative(pts<0 and -1 or 1, abs(pts))
		if abs(pts) > 100 and config.usage.show_infobar_on_skip.value:
			self.showAfterSeek()

	def seekFwd(self):
		if self.seekstate == self.SEEK_STATE_PLAY:
			self.setSeekState(self.makeStateForward(int(config.seek.enter_forward.value)))
		elif self.seekstate == self.SEEK_STATE_PAUSE:
			if config.seek.speeds_slowmotion:
				self.setSeekState(self.makeStateSlowMotion(config.seek.speeds_slowmotion.value[-1]))
			else:
				self.setSeekState(self.makeStateForward(int(config.seek.enter_forward.value)))
		elif self.seekstate == self.SEEK_STATE_EOF:
			pass
		elif self.isStateForward(self.seekstate):
			speed = self.seekstate[1]
			if self.seekstate[2]:
				speed /= self.seekstate[2]
			speed = self.getHigher(speed, config.seek.speeds_forward.value) or config.seek.speeds_forward.value[-1]
			self.setSeekState(self.makeStateForward(speed))
		elif self.isStateBackward(self.seekstate):
			speed = -self.seekstate[1]
			if self.seekstate[2]:
				speed /= self.seekstate[2]
			speed = self.getLower(speed, config.seek.speeds_backward.value)
			if speed:
				self.setSeekState(self.makeStateBackward(speed))
			else:
				self.setSeekState(self.SEEK_STATE_PLAY)
		elif self.isStateSlowMotion(self.seekstate):
			speed = self.getLower(self.seekstate[2], config.seek.speeds_slowmotion.value) or config.seek.speeds_slowmotion.value[0]
			self.setSeekState(self.makeStateSlowMotion(speed))

	def seekBack(self):
		if self.seekstate == self.SEEK_STATE_PLAY:
			self.setSeekState(self.makeStateBackward(int(config.seek.enter_backward.value)))
		elif self.seekstate == self.SEEK_STATE_EOF:
			self.setSeekState(self.makeStateBackward(int(config.seek.enter_backward.value)))
			self.doSeekRelative(-6)
		elif self.seekstate == self.SEEK_STATE_PAUSE:
			self.doSeekRelative(-3)
		elif self.isStateForward(self.seekstate):
			speed = self.seekstate[1]
			if self.seekstate[2]:
				speed /= self.seekstate[2]
			speed = self.getLower(speed, config.seek.speeds_forward.value)
			if speed:
				self.setSeekState(self.makeStateForward(speed))
			else:
				self.setSeekState(self.SEEK_STATE_PLAY)
		elif self.isStateBackward(self.seekstate):
			speed = -self.seekstate[1]
			if self.seekstate[2]:
				speed /= self.seekstate[2]
			speed = self.getHigher(speed, config.seek.speeds_backward.value) or config.seek.speeds_backward.value[-1]
			self.setSeekState(self.makeStateBackward(speed))
		elif self.isStateSlowMotion(self.seekstate):
			speed = self.getHigher(self.seekstate[2], config.seek.speeds_slowmotion.value)
			if speed:
				self.setSeekState(self.makeStateSlowMotion(speed))
			else:
				self.setSeekState(self.SEEK_STATE_PAUSE)

	def seekFwdManual(self):
		self.session.openWithCallback(self.fwdSeekTo, MinuteInput)

	def fwdSeekTo(self, minutes):
		print "Seek", minutes, "minutes forward"
		self.doSeekRelative(minutes * 60 * 90000)

	def seekBackManual(self):
		self.session.openWithCallback(self.rwdSeekTo, MinuteInput)

	def rwdSeekTo(self, minutes):
		print "rwdSeekTo"
		self.doSeekRelative(-minutes * 60 * 90000)

	def checkSkipShowHideLock(self):
		wantlock = self.seekstate != self.SEEK_STATE_PLAY

		if config.usage.show_infobar_on_skip.value:
			if self.lockedBecauseOfSkipping and not wantlock:
				self.unlockShow()
				self.lockedBecauseOfSkipping = False

			if wantlock and not self.lockedBecauseOfSkipping:
				self.lockShow()
				self.lockedBecauseOfSkipping = True

	def calcRemainingTime(self):
		seekable = self.getSeek()
		if seekable is not None:
			len = seekable.getLength()
			try:
				tmp = self.cueGetEndCutPosition()
				if tmp:
					len = [False, tmp]
			except:
				pass
			pos = seekable.getPlayPosition()
			speednom = self.seekstate[1] or 1
			speedden = self.seekstate[2] or 1
			if not len[0] and not pos[0]:
				if len[1] <= pos[1]:
					return 0
				time = (len[1] - pos[1])*speedden/(90*speednom)
				return time
		return False
		
	def __evEOF(self):
		if self.eofState == 0 and self.seekstate != self.SEEK_STATE_EOF:
			self.eofState = 1
			time = self.calcRemainingTime()
			if not time:
				time = 3000   # Failed to calc, use default
			elif time == 0:
				time = 300    # Passed end, shortest wait
			elif time > 15000:
				self.eofState = -2  # Too long, block eof
				time = 15000
			else:
				time += 1000  # Add margin
			self.eofTimer.start(time, True)

	def inhibitEof(self):
		if self.eofState >= 1:
			self.eofState = -self.eofState
			self.eofTimer.stop()
			self.doEof()

	def doEof(self):
		if self.seekstate == self.SEEK_STATE_EOF:
			return
		if self.eofState == -2 or self.isStateBackward(self.seekstate):
			self.eofState = 0
			return

		# if we are seeking, we try to end up ~1s before the end, and pause there.
		eofstate = self.eofState
		seekstate = self.seekstate
		self.eofState = 0
		if not self.seekstate == self.SEEK_STATE_PAUSE:
			self.setSeekState(self.SEEK_STATE_EOF)
		if eofstate == -1 or not seekstate in [self.SEEK_STATE_PLAY, self.SEEK_STATE_PAUSE]:
			seekable = self.getSeek()
			if seekable is not None:
				seekable.seekTo(-1)
		if eofstate == 1 and seekstate == self.SEEK_STATE_PLAY:
			self.doEofInternal(True)
		else:
			self.doEofInternal(False)

	def doEofInternal(self, playing):
		pass		# Defined in subclasses

	def __evSOF(self):
		self.setSeekState(self.SEEK_STATE_PLAY)
		self.doSeek(0)

from Screens.PVRState import PVRState, TimeshiftState

class InfoBarPVRState:
	def __init__(self, screen=PVRState):
		self.onPlayStateChanged.append(self.__playStateChanged)
		self.pvrStateDialog = self.session.instantiateDialog(screen)
		self.onShow.append(self._mayShow)
		self.onHide.append(self.pvrStateDialog.hide)

	def _mayShow(self):
		if self.execing and self.seekstate != self.SEEK_STATE_PLAY:
			self.pvrStateDialog.show()

	def __playStateChanged(self, state):
		playstateString = state[3]
		self.pvrStateDialog["state"].setText(playstateString)
		self._mayShow()

class InfoBarTimeshiftState(InfoBarPVRState):
	def __init__(self):
		InfoBarPVRState.__init__(self, screen=TimeshiftState)

	def _mayShow(self):
		if self.execing and self.timeshift_enabled:
			self.pvrStateDialog.show()

class InfoBarShowMovies:

	# i don't really like this class.
	# it calls a not further specified "movie list" on up/down/movieList,
	# so this is not more than an action map
	def __init__(self):
		self["MovieListActions"] = HelpableActionMap(self, "InfobarMovieListActions",
			{
				"movieList": (self.showMovies, _("movie list")),
				"up": (self.showMovies, _("movie list")),
				"down": (self.showMovies, _("movie list"))
			})

# InfoBarTimeshift requires InfoBarSeek, instantiated BEFORE!

# Hrmf.
#
# Timeshift works the following way:
#                                         demux0   demux1                    "TimeshiftActions" "TimeshiftActivateActions" "SeekActions"
# - normal playback                       TUNER    unused      PLAY               enable                disable              disable
# - user presses "yellow" button.         FILE     record      PAUSE              enable                disable              enable
# - user presess pause again              FILE     record      PLAY               enable                disable              enable
# - user fast forwards                    FILE     record      FF                 enable                disable              enable
# - end of timeshift buffer reached       TUNER    record      PLAY               enable                enable               disable
# - user backwards                        FILE     record      BACK  # !!         enable                disable              enable
#

# in other words:
# - when a service is playing, pressing the "timeshiftStart" button ("yellow") enables recording ("enables timeshift"),
# freezes the picture (to indicate timeshift), sets timeshiftMode ("activates timeshift")
# now, the service becomes seekable, so "SeekActions" are enabled, "TimeshiftEnableActions" are disabled.
# - the user can now PVR around
# - if it hits the end, the service goes into live mode ("deactivates timeshift", it's of course still "enabled")
# the service looses it's "seekable" state. It can still be paused, but just to activate timeshift right
# after!
# the seek actions will be disabled, but the timeshiftActivateActions will be enabled
# - if the user rewinds, or press pause, timeshift will be activated again

# note that a timeshift can be enabled ("recording") and
# activated (currently time-shifting).

class InfoBarTimeshift:
	def __init__(self):
		self["TimeshiftActions"] = HelpableActionMap(self, "InfobarTimeshiftActions",
			{
				"timeshiftStart": (self.startTimeshift, _("start timeshift")),  # the "yellow key"
				"timeshiftStop": (self.stopTimeshift, _("stop timeshift"))      # currently undefined :), probably 'TV'
			}, prio=1)
		self["TimeshiftActivateActions"] = ActionMap(["InfobarTimeshiftActivateActions"],
			{
				"timeshiftActivateEnd": self.activateTimeshiftEnd, # something like "rewind key"
				"timeshiftActivateEndAndPause": self.activateTimeshiftEndAndPause  # something like "pause key"
			}, prio=-1) # priority over record

		self.timeshift_enabled = 0
		self.timeshift_state = 0
		self.ts_rewind_timer = eTimer()
		self.ts_rewind_timer.callback.append(self.rewindService)

		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
			{
				iPlayableService.evStart: self.__serviceStarted,
				iPlayableService.evSeekableStatusChanged: self.__seekableStatusChanged
			})

	def getTimeshift(self):
		service = self.session.nav.getCurrentService()
		return service and service.timeshift()

	def startTimeshift(self):
		print "enable timeshift"
		ts = self.getTimeshift()
		if ts is None:
			self.session.open(MessageBox, _("Timeshift not possible!"), MessageBox.TYPE_ERROR)
			print "no ts interface"
			return 0

		if self.timeshift_enabled:
			print "hu, timeshift already enabled?"
		else:
			if not ts.startTimeshift():
				self.timeshift_enabled = 1

				# we remove the "relative time" for now.
				#self.pvrStateDialog["timeshift"].setRelative(time.time())

				# PAUSE.
				#self.setSeekState(self.SEEK_STATE_PAUSE)
				self.activateTimeshiftEnd(False)

				# enable the "TimeshiftEnableActions", which will override
				# the startTimeshift actions
				self.__seekableStatusChanged()
			else:
				print "timeshift failed"

	def stopTimeshift(self):
		if not self.timeshift_enabled:
			return 0
		print "disable timeshift"
		ts = self.getTimeshift()
		if ts is None:
			return 0
		self.session.openWithCallback(self.stopTimeshiftConfirmed, MessageBox, _("Stop Timeshift?"), MessageBox.TYPE_YESNO)

	def stopTimeshiftConfirmed(self, confirmed):
		if not confirmed:
			return

		ts = self.getTimeshift()
		if ts is None:
			return

		ts.stopTimeshift()
		self.timeshift_enabled = 0

		# disable actions
		self.__seekableStatusChanged()

	# activates timeshift, and seeks to (almost) the end
	def activateTimeshiftEnd(self, back = True):
		ts = self.getTimeshift()
		print "activateTimeshiftEnd"

		if ts is None:
			return

		if ts.isTimeshiftActive():
			print "!! activate timeshift called - but shouldn't this be a normal pause?"
			self.pauseService()
		else:
			print "play, ..."
			ts.activateTimeshift() # activate timeshift will automatically pause
			self.setSeekState(self.SEEK_STATE_PAUSE)

		if back:
			self.doSeek(-5) # seek some gops before end
			self.ts_rewind_timer.start(200, 1)
		else:
			self.doSeek(-1) # seek 1 gop before end

	def rewindService(self):
		self.setSeekState(self.makeStateBackward(int(config.seek.enter_backward.value)))

	# same as activateTimeshiftEnd, but pauses afterwards.
	def activateTimeshiftEndAndPause(self):
		print "activateTimeshiftEndAndPause"
		#state = self.seekstate
		self.activateTimeshiftEnd(False)

	def __seekableStatusChanged(self):
		enabled = False

		print "self.isSeekable", self.isSeekable()
		print "self.timeshift_enabled", self.timeshift_enabled

		# when this service is not seekable, but timeshift
		# is enabled, this means we can activate
		# the timeshift
		if not self.isSeekable() and self.timeshift_enabled:
			enabled = True

		print "timeshift activate:", enabled
		self["TimeshiftActivateActions"].setEnabled(enabled)

	def __serviceStarted(self):
		self.timeshift_enabled = False
		self.__seekableStatusChanged()

from Screens.PiPSetup import PiPSetup

class InfoBarExtensions:
	EXTENSION_SINGLE = 0
	EXTENSION_LIST = 1

	def __init__(self):
		self.list = []

		self["InstantExtensionsActions"] = HelpableActionMap(self, "InfobarExtensions",
			{
				"extensions": (self.showExtensionSelection, _("view extensions...")),
			})

	def addExtension(self, extension, key = None, type = EXTENSION_SINGLE):
		self.list.append((type, extension, key))

	def updateExtension(self, extension, key = None):
		self.extensionsList.append(extension)
		if key is not None:
			if self.extensionKeys.has_key(key):
				key = None

		if key is None:
			for x in self.availableKeys:
				if not self.extensionKeys.has_key(x):
					key = x
					break

		if key is not None:
			self.extensionKeys[key] = len(self.extensionsList) - 1

	def updateExtensions(self):
		self.extensionsList = []
		self.availableKeys = [ "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "red", "green", "yellow", "blue" ]
		self.extensionKeys = {}
		for x in self.list:
			if x[0] == self.EXTENSION_SINGLE:
				self.updateExtension(x[1], x[2])
			else:
				for y in x[1]():
					self.updateExtension(y[0], y[1])


	def showExtensionSelection(self):
		self.updateExtensions()
		extensionsList = self.extensionsList[:]
		keys = []
		list = []
		for x in self.availableKeys:
			if self.extensionKeys.has_key(x):
				entry = self.extensionKeys[x]
				extension = self.extensionsList[entry]
				if extension[2]():
					name = str(extension[0]())
					list.append((extension[0](), extension))
					keys.append(x)
					extensionsList.remove(extension)
				else:
					extensionsList.remove(extension)
		for x in extensionsList:
			list.append((x[0](), x))
		keys += [""] * len(extensionsList)
		self.session.openWithCallback(self.extensionCallback, ChoiceBox, title=_("Please choose an extension..."), list = list, keys = keys)

	def extensionCallback(self, answer):
		if answer is not None:
			answer[1][1]()

from Tools.BoundFunction import boundFunction

# depends on InfoBarExtensions
from Components.PluginComponent import plugins

class InfoBarPlugins:
	def __init__(self):
		self.addExtension(extension = self.getPluginList, type = InfoBarExtensions.EXTENSION_LIST)

	def getPluginName(self, name):
		return name

	def getPluginList(self):
		list = []
		for p in plugins.getPlugins(where = PluginDescriptor.WHERE_EXTENSIONSMENU):
			list.append(((boundFunction(self.getPluginName, p.name), boundFunction(self.runPlugin, p), lambda: True), None))
		return list

	def runPlugin(self, plugin):
		plugin(session = self.session, servicelist = self.servicelist)

# depends on InfoBarExtensions
class InfoBarSleepTimer:
	def __init__(self):
		self.addExtension((self.getSleepTimerName, self.showSleepTimerSetup, self.available), "1")

	def available(self):
		return True

	def getSleepTimerName(self):
		return _("Sleep Timer")

	def showSleepTimerSetup(self):
		self.session.open(SleepTimerEdit)

# depends on InfoBarExtensions
class InfoBarPiP:
	def __init__(self):
		self.session.pipshown = False
		if SystemInfo.get("NumVideoDecoders", 1) > 1:
			self.addExtension((self.getShowHideName, self.showPiP, self.available), "blue")
			self.addExtension((self.getMoveName, self.movePiP, self.pipShown), "green")
			self.addExtension((self.getSwapName, self.swapPiP, self.pipShown), "yellow")

	def available(self):
		return SystemInfo.get("NumVideoDecoders", 1) > 1

	def pipShown(self):
		return self.session.pipshown

	def pipHandles0Action(self):
		return self.pipShown() and config.usage.pip_zero_button.value != "standard"

	def getShowHideName(self):
		if self.session.pipshown:
			return _("Disable Picture in Picture")
		else:
			return _("Activate Picture in Picture")

	def getSwapName(self):
		return _("Swap Services")

	def getMoveName(self):
		return _("Move Picture in Picture")

	def showPiP(self):
		if self.session.pipshown:
			del self.session.pip
			self.session.pipshown = False
		else:
			self.session.pip = self.session.instantiateDialog(PictureInPicture)
			self.session.pip.show()
			newservice = self.session.nav.getCurrentlyPlayingServiceReference()
			if self.session.pip.playService(newservice):
				self.session.pipshown = True
				self.session.pip.servicePath = self.servicelist.getCurrentServicePath()
			else:
				self.session.pipshown = False
				del self.session.pip
			self.session.nav.playService(newservice)

	def swapPiP(self):
		swapservice = self.session.nav.getCurrentlyPlayingServiceReference()
		if self.session.pip.servicePath:
			servicepath = self.servicelist.getCurrentServicePath()
			ref=servicepath[len(servicepath)-1]
			pipref=self.session.pip.getCurrentService()
			self.session.pip.playService(swapservice)
			self.servicelist.setCurrentServicePath(self.session.pip.servicePath)
			if pipref.toString() != ref.toString(): # is a subservice ?
				self.session.nav.stopService() # stop portal
				self.session.nav.playService(pipref) # start subservice
			self.session.pip.servicePath=servicepath

	def movePiP(self):
		self.session.open(PiPSetup, pip = self.session.pip)

	def pipDoHandle0Action(self):
		use = config.usage.pip_zero_button.value
		if "swap" == use:
			self.swapPiP()
		elif "swapstop" == use:
			self.swapPiP()
			self.showPiP()
		elif "stop" == use:
			self.showPiP()

from RecordTimer import parseEvent

class InfoBarInstantRecord:
	"""Instant Record - handles the instantRecord action in order to
	start/stop instant records"""
	def __init__(self):
		self["InstantRecordActions"] = HelpableActionMap(self, "InfobarInstantRecord",
			{
				"instantRecord": (self.instantRecord, _("Instant Record...")),
			})
		self.recording = []
#### DEPRECATED CODE ####
		self["BlinkingPoint"] = BlinkingPixmapConditional()
		self["BlinkingPoint"].setConnect(self.session.nav.RecordTimer.isRecording)
		self["BlinkingPoint"].deprecationInfo = (
			"session.RecordState source, Pixmap renderer and "
			"ConditionalShowHide/Blink Converter", "2008-02")
#########################

	def stopCurrentRecording(self, entry = -1):
		if entry is not None and entry != -1:
			self.session.nav.RecordTimer.removeEntry(self.recording[entry])
			self.recording.remove(self.recording[entry])

	def startInstantRecording(self, limitEvent = False):
		serviceref = self.session.nav.getCurrentlyPlayingServiceReference()

		# try to get event info
		event = None
		try:
			service = self.session.nav.getCurrentService()
			epg = eEPGCache.getInstance()
			event = epg.lookupEventTime(serviceref, -1, 0)
			if event is None:
				info = service.info()
				ev = info.getEvent(0)
				event = ev
		except:
			pass

		begin = time()
		end = time() + 3600 * 10
		name = "instant record"
		description = ""
		eventid = None

		if event is not None:
			curEvent = parseEvent(event)
			name = curEvent[2]
			description = curEvent[3]
			eventid = curEvent[4]
			if limitEvent:
				end = curEvent[1]
		else:
			if limitEvent:
				self.session.open(MessageBox, _("No event info found, recording indefinitely."), MessageBox.TYPE_INFO)

		data = (begin, end, name, description, eventid)

		recording = self.session.nav.recordWithTimer(serviceref, *data)
		recording.dontSave = True
		self.recording.append(recording)

#### DEPRECATED CODE ####
		self["BlinkingPoint"].setConnect(lambda: self.recording.isRunning())
#########################

	def isInstantRecordRunning(self):
		print "self.recording:", self.recording
		if len(self.recording) > 0:
			for x in self.recording:
				if x.isRunning():
					return True
		return False

	def recordQuestionCallback(self, answer):
		print "pre:\n", self.recording

		if answer is None or answer[1] == "no":
			return
		list = []
		recording = self.recording[:]
		for x in recording:
			if not x in self.session.nav.RecordTimer.timer_list:
				self.recording.remove(x)
			elif x.dontSave and x.isRunning():
				list.append((x, False))

		if answer[1] == "changeduration":
			if len(self.recording) == 1:
				self.changeDuration(0)
			else:
				self.session.openWithCallback(self.changeDuration, TimerSelection, list)
		elif answer[1] == "changeendtime":
			if len(self.recording) == 1:
				self.setEndtime(0)
			else:
				self.session.openWithCallback(self.setEndtime, TimerSelection, list)
		elif answer[1] == "stop":
			if len(self.recording) == 1:
				self.stopCurrentRecording(0)
			else:
				self.session.openWithCallback(self.stopCurrentRecording, TimerSelection, list)
		elif answer[1] in ( "indefinitely" , "manualduration", "manualendtime", "event"):
			self.startInstantRecording(limitEvent = answer[1] in ("event", "manualendtime") or False)
			if answer[1] == "manualduration":
				self.changeDuration(len(self.recording)-1)
			elif answer[1] == "manualendtime":
				self.setEndtime(len(self.recording)-1)
		print "after:\n", self.recording

	def setEndtime(self, entry):
		if entry is not None:
			self.selectedEntry = entry
			self.endtime=ConfigClock(default = self.recording[self.selectedEntry].end)
			dlg = self.session.openWithCallback(self.TimeDateInputClosed, TimeDateInput, self.endtime)
			dlg.setTitle(_("Please change recording endtime"))

	def TimeDateInputClosed(self, ret):
		if len(ret) > 1:
			if ret[0]:
				localendtime = localtime(ret[1])
				print "stopping recording at", strftime("%c", localendtime)
				self.recording[self.selectedEntry].end = ret[1]
				self.session.nav.RecordTimer.timeChanged(self.recording[self.selectedEntry])

	def changeDuration(self, entry):
		if entry is not None:
			self.selectedEntry = entry
			self.session.openWithCallback(self.inputCallback, InputBox, title=_("How many minutes do you want to record?"), text="5", maxSize=False, type=Input.NUMBER)

	def inputCallback(self, value):
		if value is not None:
			print "stopping recording after", int(value), "minutes."
			self.recording[self.selectedEntry].end = time() + 60 * int(value)
			self.session.nav.RecordTimer.timeChanged(self.recording[self.selectedEntry])

	def instantRecord(self):
		try:
			stat = os_stat(resolveFilename(SCOPE_HDD))
		except:
			self.session.open(MessageBox, _("No HDD found or HDD not initialized!"), MessageBox.TYPE_ERROR)
			return

		if self.isInstantRecordRunning():
			self.session.openWithCallback(self.recordQuestionCallback, ChoiceBox, \
				title=_("A recording is currently running.\nWhat do you want to do?"), \
				list=[(_("stop recording"), "stop"), \
				(_("change recording (duration)"), "changeduration"), \
				(_("change recording (endtime)"), "changeendtime"), \
				(_("add recording (indefinitely)"), "indefinitely"), \
				(_("add recording (stop after current event)"), "event"), \
				(_("add recording (enter recording duration)"), "manualduration"), \
				(_("add recording (enter recording endtime)"), "manualendtime"), \
				(_("do nothing"), "no")])
		else:
			self.session.openWithCallback(self.recordQuestionCallback, ChoiceBox, \
				title=_("Start recording?"), \
				list=[(_("add recording (indefinitely)"), "indefinitely"), \
				(_("add recording (stop after current event)"), "event"), \
				(_("add recording (enter recording duration)"), "manualduration"), \
				(_("add recording (enter recording endtime)"), "manualendtime"), \
				(_("don't record"), "no")])

from Tools.ISO639 import LanguageCodes

class InfoBarAudioSelection:
	def __init__(self):
		self["AudioSelectionAction"] = HelpableActionMap(self, "InfobarAudioSelectionActions",
			{
				"audioSelection": (self.audioSelection, _("Audio Options...")),
			})

	def audioSelection(self):
		service = self.session.nav.getCurrentService()
		audio = service and service.audioTracks()
		self.audioTracks = audio
		n = audio and audio.getNumberOfTracks() or 0
		keys = [ "red", "", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0"] + [""]*n
		tlist = []
		if n > 0:
			self.audioChannel = service.audioChannel()

			for x in range(n):
				i = audio.getTrackInfo(x)
				language = i.getLanguage()
				description = i.getDescription()

				if LanguageCodes.has_key(language):
					language = LanguageCodes[language][0]

				if len(description):
					description += " (" + language + ")"
				else:
					description = language

				tlist.append((description, x))

			selectedAudio = audio.getCurrentTrack()
			tlist.sort(key=lambda x: x[0])

			selection = 2
			for x in tlist:
				if x[1] != selectedAudio:
					selection += 1
				else:
					break

			tlist = [([_("Left"), _("Stereo"), _("Right")][self.audioChannel.getCurrentChannel()], "mode"), ("--", "")] + tlist
			self.session.openWithCallback(self.audioSelected, ChoiceBox, title=_("Select audio track"), list = tlist, selection = selection, keys = keys)
		else:
			del self.audioTracks

	def audioSelected(self, audio):
		if audio is not None:
			if isinstance(audio[1], str):
				if audio[1] == "mode":
					keys = ["red", "green", "yellow"]
					selection = self.audioChannel.getCurrentChannel()
					tlist = [(_("left"), 0), (_("stereo"), 1), (_("right"), 2)]
					self.session.openWithCallback(self.modeSelected, ChoiceBox, title=_("Select audio mode"), list = tlist, selection = selection, keys = keys)
			else:
				del self.audioChannel
				if self.session.nav.getCurrentService().audioTracks().getNumberOfTracks() > audio[1]:
					self.audioTracks.selectTrack(audio[1])
		else:
			del self.audioChannel
		del self.audioTracks

	def modeSelected(self, mode):
		if mode is not None:
			self.audioChannel.selectChannel(mode[1])
		del self.audioChannel

class InfoBarSubserviceSelection:
	def __init__(self):
		self["SubserviceSelectionAction"] = HelpableActionMap(self, "InfobarSubserviceSelectionActions",
			{
				"subserviceSelection": (self.subserviceSelection, _("Subservice list...")),
			})

		self["SubserviceQuickzapAction"] = HelpableActionMap(self, "InfobarSubserviceQuickzapActions",
			{
				"nextSubservice": (self.nextSubservice, _("Switch to next subservice")),
				"prevSubservice": (self.prevSubservice, _("Switch to previous subservice"))
			}, -1)
		self["SubserviceQuickzapAction"].setEnabled(False)

		self.session.nav.event.append(self.checkSubservicesAvail) # we like to get service events

		self.bsel = None

	def checkSubservicesAvail(self, ev):
		if ev == iPlayableService.evUpdatedEventInfo:
			service = self.session.nav.getCurrentService()
			subservices = service and service.subServices()
			if not subservices or subservices.getNumberOfSubservices() == 0:
				self["SubserviceQuickzapAction"].setEnabled(False)

	def nextSubservice(self):
		self.changeSubservice(+1)

	def prevSubservice(self):
		self.changeSubservice(-1)

	def changeSubservice(self, direction):
		service = self.session.nav.getCurrentService()
		subservices = service and service.subServices()
		n = subservices and subservices.getNumberOfSubservices()
		if n and n > 0:
			selection = -1
			ref = self.session.nav.getCurrentlyPlayingServiceReference()
			for x in range(n):
				if subservices.getSubservice(x).toString() == ref.toString():
					selection = x
			if selection != -1:
				selection += direction
				if selection >= n:
					selection=0
				elif selection < 0:
					selection=n-1
				newservice = subservices.getSubservice(selection)
				if newservice.valid():
					del subservices
					del service
					self.session.nav.playService(newservice)

	def subserviceSelection(self):
		service = self.session.nav.getCurrentService()
		subservices = service and service.subServices()
		self.bouquets = self.servicelist.getBouquetList()
		n = subservices and subservices.getNumberOfSubservices()
		selection = 0
		if n and n > 0:
			ref = self.session.nav.getCurrentlyPlayingServiceReference()
			tlist = []
			for x in range(n):
				i = subservices.getSubservice(x)
				if i.toString() == ref.toString():
					selection = x
				tlist.append((i.getName(), i))

			if self.bouquets and len(self.bouquets):
				keys = ["red", "green", "",  "0", "1", "2", "3", "4", "5", "6", "7", "8", "9" ] + [""] * n
				if config.usage.multibouquet.value:
					tlist = [(_("Quickzap"), "quickzap", service.subServices()), (_("Add to bouquet"), "CALLFUNC", self.addSubserviceToBouquetCallback), ("--", "")] + tlist
				else:
					tlist = [(_("Quickzap"), "quickzap", service.subServices()), (_("Add to favourites"), "CALLFUNC", self.addSubserviceToBouquetCallback), ("--", "")] + tlist
				selection += 3
			else:
				tlist = [(_("Quickzap"), "quickzap", service.subServices()), ("--", "")] + tlist
				keys = ["red", "",  "0", "1", "2", "3", "4", "5", "6", "7", "8", "9" ] + [""] * n
				selection += 2

			self.session.openWithCallback(self.subserviceSelected, ChoiceBox, title=_("Please select a subservice..."), list = tlist, selection = selection, keys = keys)

	def subserviceSelected(self, service):
		del self.bouquets
		if not service is None:
			if isinstance(service[1], str):
				if service[1] == "quickzap":
					from Screens.SubservicesQuickzap import SubservicesQuickzap
					self.session.open(SubservicesQuickzap, service[2])
			else:
				self["SubserviceQuickzapAction"].setEnabled(True)
				self.session.nav.playService(service[1])

	def addSubserviceToBouquetCallback(self, service):
		if len(service) > 1 and isinstance(service[1], eServiceReference):
			self.selectedSubservice = service
			if self.bouquets is None:
				cnt = 0
			else:
				cnt = len(self.bouquets)
			if cnt > 1: # show bouquet list
				self.bsel = self.session.openWithCallback(self.bouquetSelClosed, BouquetSelector, self.bouquets, self.addSubserviceToBouquet)
			elif cnt == 1: # add to only one existing bouquet
				self.addSubserviceToBouquet(self.bouquets[0][1])
				self.session.open(MessageBox, _("Service has been added to the favourites."), MessageBox.TYPE_INFO)

	def bouquetSelClosed(self, confirmed):
		self.bsel = None
		del self.selectedSubservice
		if confirmed:
			self.session.open(MessageBox, _("Service has been added to the selected bouquet."), MessageBox.TYPE_INFO)

	def addSubserviceToBouquet(self, dest):
		self.servicelist.addServiceToBouquet(dest, self.selectedSubservice[1])
		if self.bsel:
			self.bsel.close(True)
		else:
			del self.selectedSubservice

class InfoBarAdditionalInfo:
	def __init__(self):

		self["RecordingPossible"] = Boolean(fixed=harddiskmanager.HDDCount() > 0)
		self["TimeshiftPossible"] = self["RecordingPossible"]
		self["ExtensionsAvailable"] = Boolean(fixed=1)

######### DEPRECATED CODE ##########
		self["NimA"] = Pixmap()
		self["NimA"].deprecationInfo = (
			"session.TunerInfo source, Pixmap renderer, TunerInfo/UseMask Converter"
			", ValueBitTest(1) Converter and ConditionalShowHide Converter", "2008-02")
		self["NimB"] = Pixmap()
		self["NimB"].deprecationInfo = (
			"session.TunerInfo source, Pixmap renderer, TunerInfo/UseMask Converter"
			", ValueBitTest(2) Converter and ConditionalShowHide Converter", "2008-02")
		self["NimA_Active"] = Pixmap()
		self["NimA_Active"].deprecationInfo = (
			"session.FrontendInfo source, Pixmap renderer, FrontendInfo/NUMBER Converter"
			", ValueRange(1,1) Converter and ConditionalShowHide Converter", "2008-02")
		self["NimB_Active"] = Pixmap()
		self["NimB_Active"].deprecationInfo = (
			"session.FrontendInfo source, Pixmap renderer, FrontendInfo/NUMBER Converter"
			", ValueRange(1,1) Converter and ConditionalShowHide Converter", "2008-02")

		res_mgr = eDVBResourceManager.getInstance()
		if res_mgr:
			res_mgr.frontendUseMaskChanged.get().append(self.tunerUseMaskChanged)

		self.session.nav.event.append(self.gotServiceEvent) # we like to get service events

	def tunerUseMaskChanged(self, mask):
		if mask&1:
			self["NimA_Active"].show()
		else:
			self["NimA_Active"].hide()
		if mask&2:
			self["NimB_Active"].show()
		else:
			self["NimB_Active"].hide()

	def checkTunerState(self, service):
		info = service and service.frontendInfo()
		feNumber = info and info.getFrontendInfo(iFrontendInformation.frontendNumber)
		if feNumber is None:
			self["NimA"].hide()
			self["NimB"].hide()
		elif feNumber == 0:
			self["NimB"].hide()
			self["NimA"].show()
		elif feNumber == 1:
			self["NimA"].hide()
			self["NimB"].show()

	def gotServiceEvent(self, ev):
		service = self.session.nav.getCurrentService()
		if ev == iPlayableService.evUpdatedInfo or ev == iPlayableService.evEnd:
			self.checkTunerState(service)
####################################

class InfoBarNotifications:
	def __init__(self):
		self.onExecBegin.append(self.checkNotifications)
		Notifications.notificationAdded.append(self.checkNotificationsIfExecing)
		self.onClose.append(self.__removeNotification)

	def __removeNotification(self):
		Notifications.notificationAdded.remove(self.checkNotificationsIfExecing)

	def checkNotificationsIfExecing(self):
		if self.execing:
			self.checkNotifications()

	def checkNotifications(self):
		if len(Notifications.notifications):
			n = Notifications.notifications[0]

			Notifications.notifications = Notifications.notifications[1:]
			cb = n[0]

			if n[3].has_key("onSessionOpenCallback"):
				n[3]["onSessionOpenCallback"]()
				del n[3]["onSessionOpenCallback"]

			if cb is not None:
				dlg = self.session.openWithCallback(cb, n[1], *n[2], **n[3])
			else:
				dlg = self.session.open(n[1], *n[2], **n[3])

			# remember that this notification is currently active
			d = (n[4], dlg)
			Notifications.current_notifications.append(d)
			dlg.onClose.append(boundFunction(self.__notificationClosed, d))

	def __notificationClosed(self, d):
		Notifications.current_notifications.remove(d)

class InfoBarServiceNotifications:
	def __init__(self):
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
			{
				iPlayableService.evEnd: self.serviceHasEnded
			})

	def serviceHasEnded(self):
		print "service end!"

		try:
			self.setSeekState(self.SEEK_STATE_PLAY)
		except:
			pass

class InfoBarCueSheetSupport:
	CUT_TYPE_IN = 0
	CUT_TYPE_OUT = 1
	CUT_TYPE_MARK = 2
	CUT_TYPE_LAST = 3

	ENABLE_RESUME_SUPPORT = False

	def __init__(self, actionmap = "InfobarCueSheetActions"):
		self["CueSheetActions"] = HelpableActionMap(self, actionmap,
			{
				"jumpPreviousMark": (self.jumpPreviousMark, _("jump to previous marked position")),
				"jumpNextMark": (self.jumpNextMark, _("jump to next marked position")),
				"toggleMark": (self.toggleMark, _("toggle a cut mark at the current position"))
			}, prio=1)

		self.cut_list = [ ]
		self.is_closing = False
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
			{
				iPlayableService.evStart: self.__serviceStarted,
			})

	def __serviceStarted(self):
		if self.is_closing:
			return
		print "new service started! trying to download cuts!"
		self.downloadCuesheet()

		if self.ENABLE_RESUME_SUPPORT:
			last = None

			for (pts, what) in self.cut_list:
				if what == self.CUT_TYPE_LAST:
					last = pts

			if last is not None:
				self.resume_point = last
				if config.usage.on_movie_start.value == "ask":
					Notifications.AddNotificationWithCallback(self.playLastCB, MessageBox, _("Do you want to resume this playback?"), timeout=10)
				elif config.usage.on_movie_start.value == "resume":
# TRANSLATORS: The string "Resuming playback" flashes for a moment
# TRANSLATORS: at the start of a movie, when the user has selected
# TRANSLATORS: "Resume from last position" as start behavior.
# TRANSLATORS: The purpose is to notify the user that the movie starts
# TRANSLATORS: in the middle somewhere and not from the beginning.
# TRANSLATORS: (Some translators seem to have interpreted it as a
# TRANSLATORS: question or a choice, but it is a statement.)
					Notifications.AddNotificationWithCallback(self.playLastCB, MessageBox, _("Resuming playback"), timeout=2, type=MessageBox.TYPE_INFO)

	def playLastCB(self, answer):
		if answer == True:
			self.doSeek(self.resume_point)
		self.hideAfterResume()

	def hideAfterResume(self):
		if isinstance(self, InfoBarShowHide):
			self.hide()

	def __getSeekable(self):
		service = self.session.nav.getCurrentService()
		if service is None:
			return None
		return service.seek()

	def cueGetCurrentPosition(self):
		seek = self.__getSeekable()
		if seek is None:
			return None
		r = seek.getPlayPosition()
		if r[0]:
			return None
		return long(r[1])

	def cueGetEndCutPosition(self):
		ret = False
		isin = True
		for cp in self.cut_list:
			if cp[1] == self.CUT_TYPE_OUT:
				if isin:
					isin = False
					ret = cp[0]
			elif cp[1] == self.CUT_TYPE_IN:
				isin = True
		return ret
		
	def jumpPreviousNextMark(self, cmp, start=False):
		current_pos = self.cueGetCurrentPosition()
		if current_pos is None:
 			return False
		mark = self.getNearestCutPoint(current_pos, cmp=cmp, start=start)
		if mark is not None:
			pts = mark[0]
		else:
			return False

		self.doSeek(pts)
		return True

	def jumpPreviousMark(self):
		# we add 2 seconds, so if the play position is <2s after
		# the mark, the mark before will be used
		self.jumpPreviousNextMark(lambda x: -x-5*90000, start=True)

	def jumpNextMark(self):
		if not self.jumpPreviousNextMark(lambda x: x):
			self.doSeek(-1)

	def getNearestCutPoint(self, pts, cmp=abs, start=False):
		# can be optimized
		beforecut = False
		nearest = None
		if start:
			beforecut = True
			bestdiff = cmp(0 - pts)
			if bestdiff >= 0:
				nearest = [0, False]
		for cp in self.cut_list:
			if beforecut and cp[1] in [self.CUT_TYPE_IN, self.CUT_TYPE_OUT]:
				beforecut = False
				if cp[1] == self.CUT_TYPE_IN:  # Start is here, disregard previous marks
					diff = cmp(cp[0] - pts)
					if diff >= 0:
						nearest = cp
						bestdiff = diff
					else:
						nearest = None
			if cp[1] in [self.CUT_TYPE_MARK, self.CUT_TYPE_LAST]:
				diff = cmp(cp[0] - pts)
				if diff >= 0 and (nearest is None or bestdiff > diff):
					nearest = cp
					bestdiff = diff
		return nearest

	def toggleMark(self, onlyremove=False, onlyadd=False, tolerance=5*90000, onlyreturn=False):
		current_pos = self.cueGetCurrentPosition()
		if current_pos is None:
			print "not seekable"
			return

		nearest_cutpoint = self.getNearestCutPoint(current_pos)

		if nearest_cutpoint is not None and abs(nearest_cutpoint[0] - current_pos) < tolerance:
			if onlyreturn:
				return nearest_cutpoint
			if not onlyadd:
				self.removeMark(nearest_cutpoint)
		elif not onlyremove and not onlyreturn:
			self.addMark((current_pos, self.CUT_TYPE_MARK))

		if onlyreturn:
			return None

	def addMark(self, point):
		insort(self.cut_list, point)
		self.uploadCuesheet()
		self.showAfterCuesheetOperation()

	def removeMark(self, point):
		self.cut_list.remove(point)
		self.uploadCuesheet()
		self.showAfterCuesheetOperation()

	def showAfterCuesheetOperation(self):
		if isinstance(self, InfoBarShowHide):
			self.doShow()

	def __getCuesheet(self):
		service = self.session.nav.getCurrentService()
		if service is None:
			return None
		return service.cueSheet()

	def uploadCuesheet(self):
		cue = self.__getCuesheet()

		if cue is None:
			print "upload failed, no cuesheet interface"
			return
		cue.setCutList(self.cut_list)

	def downloadCuesheet(self):
		cue = self.__getCuesheet()

		if cue is None:
			print "download failed, no cuesheet interface"
			self.cut_list = [ ]
		else:
			self.cut_list = cue.getCutList()

class InfoBarSummary(Screen):
	skin = """
	<screen position="0,0" size="132,64">
		<widget source="global.CurrentTime" render="Label" position="62,46" size="82,18" font="Regular;16" >
			<convert type="ClockToText">WithSeconds</convert>
		</widget>
		<widget source="session.RecordState" render="FixedLabel" text=" " position="62,46" size="82,18" zPosition="1" >
			<convert type="ConfigEntryTest">config.usage.blinking_display_clock_during_recording,True,CheckSourceBoolean</convert>
			<convert type="ConditionalShowHide">Blink</convert>
		</widget>
		<widget source="session.CurrentService" render="Label" position="6,4" size="120,42" font="Regular;18" >
			<convert type="ServiceName">Name</convert>
		</widget>
		<widget source="session.Event_Now" render="Progress" position="6,46" size="46,18" borderWidth="1" >
			<convert type="EventTime">Progress</convert>
		</widget>
	</screen>"""

# for picon:  (path="piconlcd" will use LCD picons)
#		<widget source="session.CurrentService" render="Picon" position="6,0" size="120,64" path="piconlcd" >
#			<convert type="ServiceName">Reference</convert>
#		</widget>

	def __init__(self, session, parent):
		Screen.__init__(self, session, parent = parent)

class InfoBarSummarySupport:
	def __init__(self):
		pass

	def createSummary(self):
		return InfoBarSummary

class InfoBarMoviePlayerSummary(Screen):
	skin = """
	<screen position="0,0" size="132,64">
		<widget source="global.CurrentTime" render="Label" position="62,46" size="64,18" font="Regular;16" halign="right" >
			<convert type="ClockToText">WithSeconds</convert>
		</widget>
		<widget source="session.RecordState" render="FixedLabel" text=" " position="62,46" size="64,18" zPosition="1" >
			<convert type="ConfigEntryTest">config.usage.blinking_display_clock_during_recording,True,CheckSourceBoolean</convert>
			<convert type="ConditionalShowHide">Blink</convert>
		</widget>
		<widget source="session.CurrentService" render="Label" position="6,4" size="120,42" font="Regular;18" >
			<convert type="ServiceName">Name</convert>
		</widget>
		<widget source="session.CurrentService" render="Progress" position="6,46" size="56,18" borderWidth="1" >
			<convert type="ServicePosition">Position</convert>
		</widget>
	</screen>"""

	def __init__(self, session, parent):
		Screen.__init__(self, session)

class InfoBarMoviePlayerSummarySupport:
	def __init__(self):
		pass

	def createSummary(self):
		return InfoBarMoviePlayerSummary

class InfoBarTeletextPlugin:
	def __init__(self):
		self.teletext_plugin = None

		for p in plugins.getPlugins(PluginDescriptor.WHERE_TELETEXT):
			self.teletext_plugin = p

		if self.teletext_plugin is not None:
			self["TeletextActions"] = HelpableActionMap(self, "InfobarTeletextActions",
				{
					"startTeletext": (self.startTeletext, _("View teletext..."))
				})
		else:
			print "no teletext plugin found!"

	def startTeletext(self):
		self.teletext_plugin(session=self.session, service=self.session.nav.getCurrentService())

class InfoBarSubtitleSupport(object):
	def __init__(self):
		object.__init__(self)
		self.subtitle_window = self.session.instantiateDialog(SubtitleDisplay)
		self.__subtitles_enabled = False

		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
			{
				iPlayableService.evEnd: self.__serviceStopped,
				iPlayableService.evUpdatedInfo: self.__updatedInfo
			})
		self.cached_subtitle_checked = False
		self.__selected_subtitle = None

	def __serviceStopped(self):
		self.subtitle_window.hide()
		self.__subtitles_enabled = False
		self.cached_subtitle_checked = False

	def __updatedInfo(self):
		if not self.cached_subtitle_checked:
			subtitle = self.getCurrentServiceSubtitle()
			self.cached_subtitle_checked = True
			self.__selected_subtitle = subtitle and subtitle.getCachedSubtitle()
			if self.__selected_subtitle:
				subtitle.enableSubtitles(self.subtitle_window.instance, self.selected_subtitle)
				self.subtitle_window.show()
				self.__subtitles_enabled = True

	def getCurrentServiceSubtitle(self):
		service = self.session.nav.getCurrentService()
		return service and service.subtitle()

	def setSubtitlesEnable(self, enable=True):
		subtitle = self.getCurrentServiceSubtitle()
		if enable and self.__selected_subtitle is not None:
			if subtitle and not self.__subtitles_enabled:
				subtitle.enableSubtitles(self.subtitle_window.instance, self.selected_subtitle)
				self.subtitle_window.show()
				self.__subtitles_enabled = True
		else:
			if subtitle:
				subtitle.disableSubtitles(self.subtitle_window.instance)
			self.__subtitles_enabled = False
			self.subtitle_window.hide()

	def setSelectedSubtitle(self, subtitle):
		self.__selected_subtitle = subtitle

	subtitles_enabled = property(lambda self: self.__subtitles_enabled, setSubtitlesEnable)
	selected_subtitle = property(lambda self: self.__selected_subtitle, setSelectedSubtitle)

class InfoBarServiceErrorPopupSupport:
	def __init__(self):
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
			{
				iPlayableService.evTuneFailed: self.__tuneFailed,
				iPlayableService.evStart: self.__serviceStarted
			})
		self.__serviceStarted()

	def __serviceStarted(self):
		self.last_error = None
		Notifications.RemovePopup(id = "ZapError")

	def __tuneFailed(self):
		service = self.session.nav.getCurrentService()
		info = service and service.info()
		error = info and info.getInfo(iServiceInformation.sDVBState)

		if error == self.last_error:
			error = None
		else:
			self.last_error = error

		errors = {
			eDVBServicePMTHandler.eventNoResources: _("No free tuner!"),
			eDVBServicePMTHandler.eventTuneFailed: _("Tune failed!"),
			eDVBServicePMTHandler.eventNoPAT: _("No data on transponder!\n(Timeout reading PAT)"),
			eDVBServicePMTHandler.eventNoPATEntry: _("Service not found!\n(SID not found in PAT)"),
			eDVBServicePMTHandler.eventNoPMT: _("Service invalid!\n(Timeout reading PMT)"),
			eDVBServicePMTHandler.eventNewProgramInfo: None,
			eDVBServicePMTHandler.eventTuned: None,
			eDVBServicePMTHandler.eventSOF: None,
			eDVBServicePMTHandler.eventEOF: None,
			eDVBServicePMTHandler.eventMisconfiguration: _("Service unavailable!\nCheck tuner configuration!"),
		}

		error = errors.get(error) #this returns None when the key not exist in the dict

		if error is not None:
			Notifications.AddPopup(text = error, type = MessageBox.TYPE_ERROR, timeout = 5, id = "ZapError")
		else:
			Notifications.RemovePopup(id = "ZapError")

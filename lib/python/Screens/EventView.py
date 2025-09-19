from time import localtime, strftime

from enigma import eEPGCache, eTimer, eServiceReference

from RecordTimer import RecordTimerEntry, parseEvent
from Components.ActionMap import HelpableActionMap
from Components.config import config
from Components.Label import Label
from Components.ScrollLabel import ScrollLabel
from Components.Pixmap import Pixmap
from Components.PluginComponent import plugins
from Components.UsageConfig import preferredTimerPath
from Components.Sources.Event import Event
from Components.Sources.ServiceEvent import ServiceEvent
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.ChoiceBox import ChoiceBox
from Screens.Screen import Screen
from Screens.TimerEntry import TimerEntry
from Tools.BoundFunction import boundFunction


class EventViewBase:
	ADD_TIMER = 0
	REMOVE_TIMER = 1
	NO_ACTION = 2

	def __init__(self, event, serviceRef, callback=None, similarEPGCB=None):
		self.event = event
		self.serviceRef = serviceRef
		self.callbackMethod = callback
		if similarEPGCB is None:
			self.similarBroadcastTimer = None
		else:
			self.similarBroadcastTimer = eTimer()
			self.similarBroadcastTimer.callback.append(self.getSimilarEvents)
		self.similarEPGCB = similarEPGCB
		self.isRecording = (not serviceRef.ref.flags & eServiceReference.isGroup) and serviceRef.ref.getPath() and "%3a//" not in serviceRef.ref.toString()
		self["Service"] = ServiceEvent()
		self["Event"] = Event()
		self["epg_description"] = ScrollLabel()
		self["FullDescription"] = ScrollLabel()
		self["key_menu"] = StaticText(_("MENU"))
		self["key_info"] = StaticText(_("INFO"))
		self["key_red"] = StaticText("")
		self["summary_description"] = StaticText()
		self["datetime"] = Label()
		self["channel"] = Label()
		self["duration"] = Label()
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "EventViewActions"], {
			"cancel": (self.close, _("Close screen")),
			"ok": (self.close, _("Close screen")),
			"contextMenu": (self.doContext, _("Open context menu")),
			"info": (self.close, _("Close screen")),
			"pageUp": (self.pageUp, _("Show previous page")),
			"pageDown": (self.pageDown, _("Show next page"))
		}, prio=0, description=_("Event View Actions"))
		self["eventActions"] = HelpableActionMap(self, ["EventViewActions"], {
			"prevEvent": (self.prevEvent, _("Show previous event")),
			"nextEvent": (self.nextEvent, _("Show next event"))
		}, prio=0, description=_("Event View Actions"))
		self["eventActions"].setEnabled(callback is not None)
		self["similarActions"] = HelpableActionMap(self, ["EventViewActions"], {
			"openSimilarList": (self.openSimilarList, _("Find similar events in the EPG"))
		}, prio=0, description=_("Event View Actions"))
		self["similarActions"].setEnabled(False)
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setService(self.serviceRef)
		self.setEvent(self.event)

	def pageUp(self):
		self["epg_description"].pageUp()
		self["FullDescription"].pageUp()

	def pageDown(self):
		self["epg_description"].pageDown()
		self["FullDescription"].pageDown()

	def prevEvent(self):
		self.callbackMethod(self.setEvent, self.setService, -1)

	def nextEvent(self):
		self.callbackMethod(self.setEvent, self.setService, +1)

	def getCurrentService(self):
		return self.serviceRef

	currentService = property(getCurrentService)  # currentService property to support 3rd party plugins

	def setService(self, service):
		self.serviceRef = service
		self["Service"].newService(service.ref)
		serviceName = service.getServiceName()
		self["channel"].setText("%s%s" % (serviceName if serviceName else _("Unknown Service"), " - %s" % _("Recording") if self.isRecording else ""))

	def setEvent(self, event):
		if event is None or not hasattr(event, "getEventName"):
			return
		self["Event"].newEvent(event)
		self.event = event
		text = event.getEventName()
		self.setTitle(text)
		short = event.getShortDescription()
		extended = event.getExtendedDescription()
		if short == text:
			short = ""
		if short and extended and extended.replace("\n", "") == short.replace("\n", ""):
			pass  # extended = extended
		elif short and extended:
			extended = "%s\n%s" % (short, extended)
		elif short:
			extended = short
		if text and extended:
			text += "\n\n"
		text += extended
		self["epg_description"].setText(text)
		self["FullDescription"].setText(extended)
		self["summary_description"].setText(extended)
		beginTime = event.getBeginTime()
		if not beginTime:
			return
		begin = localtime(beginTime)
		end = localtime(beginTime + event.getDuration())
		self["datetime"].setText("%s - %s" % (strftime("%s, %s" % (config.usage.date.short.value, config.usage.time.short.value), begin), strftime(config.usage.time.short.value, end)))
		self["duration"].setText(_("%d min") % (event.getDuration() / 60))
		if self.similarBroadcastTimer:
			self.similarBroadcastTimer.start(400, True)
		if self.keyGreenAction != self.NO_ACTION:
			self.setTimerState()

	def editTimer(self, timer):
		self.session.open(TimerEntry, timer)

	def timerAdd(self):
		if self.isRecording:
			return
		event = self.event
		serviceref = self.serviceRef
		if event is None:
			return
		eventid = event.getEventId()
		refstr = ":".join(serviceref.ref.toString().split(":")[:11])
		for timer in self.session.nav.RecordTimer.timer_list:
			if timer.eit == eventid and ":".join(timer.service_ref.ref.toString().split(":")[:11]) == refstr:
				# Disable dialog box -> Workaround for non closed dialog when press key GREEN for Delete Timer.  (Crash when again GREEN, BLUE or OK key was pressed.)
				self.editTimer(timer)
				break
		else:
			newEntry = RecordTimerEntry(self.serviceRef, checkOldTimers=True, dirname=preferredTimerPath(), *parseEvent(self.event))
			self.session.openWithCallback(self.finishedAdd, TimerEntry, newEntry)

	def finishedAdd(self, answer):
		print("[EventView] Finished add.")
		if isinstance(answer, bool) and answer:  # Special case for close recursive
			self.close(True)
			return
		if answer[0]:
			entry = answer[1]
			simulTimerList = self.session.nav.RecordTimer.record(entry)
			if simulTimerList is not None:
				for x in simulTimerList:
					if x.setAutoincreaseEnd(entry):
						self.session.nav.RecordTimer.timeChanged(x)
				simulTimerList = self.session.nav.RecordTimer.record(entry)
				if simulTimerList is not None:
					if not entry.repeated and not config.recording.margin_before.value and not config.recording.margin_after.value and len(simulTimerList) > 1:
						change_time = False
						conflict_begin = simulTimerList[1].begin
						conflict_end = simulTimerList[1].end
						if conflict_begin == entry.end:
							entry.end -= 30
							change_time = True
						elif entry.begin == conflict_end:
							entry.begin += 30
							change_time = True
						if change_time:
							simulTimerList = self.session.nav.RecordTimer.record(entry)
					if simulTimerList is not None:
						try:
							from Screens.TimerEdit import TimerSanityConflict
						except Exception:  # maybe already been imported from another module
							pass
						self.session.openWithCallback(self.finishSanityCorrection, TimerSanityConflict, simulTimerList)
			self["key_green"].setText(_("Change Timer"))
			self.keyGreenAction = self.REMOVE_TIMER
		else:
			self["key_green"].setText(_("Add Timer"))
			self.keyGreenAction = self.ADD_TIMER
			print("[EventView] Timer edit aborted.")

	def finishSanityCorrection(self, answer):
		self.finishedAdd(answer)

	def setTimerState(self):
		isRecordEvent = self.doesTimerExist()
		if isRecordEvent and self.keyGreenAction != self.REMOVE_TIMER:
			self["key_green"].setText(_("Change Timer"))
			self.keyGreenAction = self.REMOVE_TIMER
		elif not isRecordEvent and self.keyGreenAction != self.ADD_TIMER:
			self["key_green"].setText(_("Add Timer"))
			self.keyGreenAction = self.ADD_TIMER

	def doesTimerExist(self):
		eventId = self.event.getEventId()
		# begin = self.event.getBeginTime()
		# end = begin + self.event.getDuration()
		refStr = ":".join(self.serviceRef.ref.toString().split(":")[:11])
		isRecordEvent = False
		for timer in self.session.nav.RecordTimer.timer_list:
			neededRef = ":".join(timer.service_ref.ref.toString().split(":")[:11]) == refStr
			# if neededRef and (timer.eit == eventId and (begin < timer.begin <= end or timer.begin <= begin <= timer.end) or timer.repeated and self.session.nav.RecordTimer.isInRepeatTimer(timer, self.event)):
			if neededRef and timer.eit == eventId:
				isRecordEvent = True
				break
		return isRecordEvent

	def getSimilarEvents(self):
		if not self.event:
			return
		serviceRef = str(self.serviceRef)
		id = self.event.getEventId()
		epgcache = eEPGCache.getInstance()
		results = epgcache.search(("NB", 100, eEPGCache.SIMILAR_BROADCASTINGS_SEARCH, serviceRef, id))
		if results:
			similar = [_("Similar broadcasts:")]
			timeFormat = "%s, %s" % (config.usage.date.dayshort.value, config.usage.time.short.value)
			for result in sorted(results, key=lambda x: x[1]):
				similar.append("%s  -  %s" % (strftime(timeFormat, localtime(result[1])), result[0]))
			self["epg_description"].setText("%s\n\n%s" % (self["epg_description"].getText(), "\n".join(similar)))
			self["FullDescription"].setText("%s\n\n%s" % (self["FullDescription"].getText(), "\n".join(similar)))
			if self.similarEPGCB:
				self["key_red"].setText(_("Similar"))
				self["similarActions"].setEnabled(True)

	def openSimilarList(self):
		id = self.event and self.event.getEventId()
		serviceRef = str(self.serviceRef)
		if id:
			self.similarEPGCB(id, serviceRef)

	def doContext(self):
		if self.event:
			menu = []
			for p in plugins.getPlugins(PluginDescriptor.WHERE_EVENTINFO):
				# Only list service or event specific eventinfo plugins here, no servelist plugins.
				if "servicelist" not in p.__call__.__code__.co_varnames:
					menu.append((p.name, boundFunction(self.runPlugin, p)))
			if menu:
				def boxAction(choice):
					if choice:
						choice[1]()

				text = "%s: %s" % (_("Select action"), self.event.getEventName())
				self.session.openWithCallback(boxAction, ChoiceBox, title=text, list=menu, windowTitle=_("Event View Context Menu"), skin_name="EventViewContextMenuChoiceBox")

	def runPlugin(self, plugin):
		plugin(session=self.session, service=self.serviceRef, event=self.event, eventName=self.event.getEventName())


class EventViewSimple(Screen, EventViewBase):
	def __init__(self, session, event, serviceRef, callback=None, similarEPGCB=None, singleEPGCB=None, multiEPGCB=None, skin="EventViewSimple"):
		Screen.__init__(self, session, enableHelp=True)
		EventViewBase.__init__(self, event, serviceRef, callback=callback, similarEPGCB=similarEPGCB)
		self.setTitle(_("Event View"))
		self.skinName = [skin, "EventView"]
		self.keyGreenAction = self.NO_ACTION


class EventViewEPGSelect(Screen, EventViewBase):
	def __init__(self, session, event, serviceRef, callback=None, singleEPGCB=None, multiEPGCB=None, similarEPGCB=None, skinName=None):
		Screen.__init__(self, session, enableHelp=True)
		EventViewBase.__init__(self, event, serviceRef, callback=callback, similarEPGCB=similarEPGCB)
		self.keyGreenAction = self.ADD_TIMER
		self["red"] = Pixmap()  # DEBUG: Are these backgrounds still required?
		self["green"] = Pixmap()
		self["yellow"] = Pixmap()
		self["blue"] = Pixmap()
		self["epgActions1"] = HelpableActionMap(self, ["EventViewActions"], {
			"timerAdd": (self.timerAdd, _("Add a timer for the current event")),
			"openSimilarList": (self.openSimilarList, _("Find similar events in the EPG"))
		}, prio=0, description=_("Event View Actions"))
		self["key_green"] = StaticText("" if self.isRecording else _("Add Timer"))
		if singleEPGCB:
			self["key_yellow"] = StaticText(_("Single EPG"))
			self["epgActions2"] = HelpableActionMap(self, ["EventViewEPGActions"], {
				"openSingleServiceEPG": (singleEPGCB, _("Open the single service EPG view"))
			}, prio=0, description=_("EventViewEPG Actions"))
		else:
			self["key_yellow"] = StaticText("")
			self["yellow"].hide()
		if multiEPGCB:
			self["key_blue"] = StaticText(_("Multi EPG"))
			self["epgActions3"] = HelpableActionMap(self, ["EventViewEPGActions"], {
				"openMultiServiceEPG": (multiEPGCB, _("Open the multi service EPG view"))
			}, prio=0, description=_("EventViewEPG Actions"))
		else:
			self["key_blue"] = StaticText("")
			self["blue"].hide()
		self.skinName = ["EventView"]
		if skinName:
			if isinstance(skinName, str):
				self.skinName.insert(0, skinName)
			else:
				self.skinName = skinName + self.skinName


class EventViewMovieEvent(Screen):
	def __init__(self, session, name=None, ext_desc=None, dur=None):
		Screen.__init__(self, session, enableHelp=True)
		self.screentitle = _("Event View")
		self.skinName = "EventView"
		self.duration = ""
		if dur:
			self.duration = dur
		self.ext_desc = ""
		if name:
			self.ext_desc = "%s\n\n" % name
		if ext_desc:
			self.ext_desc += ext_desc
		self["key_red"] = StaticText("")
		self["key_green"] = StaticText("")
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText("")
		self["epg_description"] = ScrollLabel()
		self["datetime"] = Label()
		self["channel"] = Label()
		self["duration"] = Label()
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "EventViewActions"], {
			"cancel": (self.close, _("Close the current screen")),
			"ok": (self.close, _("Close the current screen")),
			"pageUp": (self.pageUp, _("Show previous page")),
			"pageDown": (self.pageDown, _("Show next page")),
		}, prio=0, description=_("Movie Event View Actions"))
		self.onShown.append(self.onCreate)

	def onCreate(self):
		self.setTitle(self.screentitle)
		self["epg_description"].setText(self.ext_desc)
		self["duration"].setText(self.duration)

	def pageUp(self):
		self["epg_description"].pageUp()

	def pageDown(self):
		self["epg_description"].pageDown()

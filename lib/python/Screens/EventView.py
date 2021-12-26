from time import localtime, mktime, time, strftime

from enigma import eEPGCache, ePoint, eTimer, eServiceReference

from RecordTimer import AFTEREVENT, RecordTimerEntry, parseEvent
from Components.ActionMap import HelpableActionMap
from Components.config import config
from Components.Label import Label
from Components.MenuList import MenuList
from Components.ScrollLabel import ScrollLabel
from Components.Pixmap import Pixmap
from Components.PluginComponent import plugins
from Components.UsageConfig import preferredTimerPath
from Components.Sources.Event import Event
from Components.Sources.ServiceEvent import ServiceEvent
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.ChoiceBox import ChoiceBox
from Screens.HelpMenu import HelpableScreen
from Screens.Screen import Screen
from Screens.TimerEntry import TimerEntry
from Tools.BoundFunction import boundFunction

class EventViewContextMenu(Screen, HelpableScreen):
	def __init__(self, session, menu):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		self.setTitle(_("Event View Context Menu"))
		self["actions"] = HelpableActionMap(self, ["OkCancelActions"], {
			"ok": (self.okbuttonClick, _("Run the selected menu option")),
			"cancel": (self.cancelClick, _("Close the context menu"))
		}, prio=0, description=_("OkCancel Actions"))
		try:
			if config.skin.primary_skin.value.startswith("MetrixHD/"):
				for count, entry in enumerate(menu):
					menu[count] = ("        %s" % entry[0], entry[1])
		except Exception:
			pass
		self["menu"] = MenuList(menu)

	def okbuttonClick(self):
		self["menu"].getCurrent() and self["menu"].getCurrent()[1]()

	def cancelClick(self):
		self.close(False)


class EventViewBase:
	ADD_TIMER = 1
	REMOVE_TIMER = 2

	def __init__(self, event, ref, callback=None, similarEPGCB=None):
		self.similarEPGCB = similarEPGCB
		self.cbFunc = callback
		self.currentService = ref
		self.isRecording = (not ref.ref.flags & eServiceReference.isGroup) and ref.ref.getPath()
		self.event = event
		self["Service"] = ServiceEvent()
		self["Event"] = Event()
		self["epg_description"] = ScrollLabel()
		self["FullDescription"] = ScrollLabel()
		self["summary_description"] = StaticText()
		self["datetime"] = Label()
		self["channel"] = Label()
		self["duration"] = Label()
		if similarEPGCB is not None:
			self["key_red"] = StaticText("")
			self.SimilarBroadcastTimer = eTimer()
			self.SimilarBroadcastTimer.callback.append(self.getSimilarEvents)
		else:
			self.SimilarBroadcastTimer = None
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "EventViewActions"], {
			"cancel": (self.close, _("Close screen")),
			"ok": (self.close, _("Close screen")),
			"info": (self.close, _("Close screen")),
			"pageUp": (self.pageUp, _("Show previous page")),
			"pageDown": (self.pageDown, _("Show next page")),
			"prevEvent": (self.prevEvent, _("Show previous event")),
			"nextEvent": (self.nextEvent, _("Show next event")),
			"contextMenu": (self.doContext, _("Open context menu")),
		}, prio=0, description=_("Event View Actions"))
		self["dialogactions"] = HelpableActionMap(self, ["WizardActions"], {
			"back": (self.closeChoiceBoxDialog, _("Close pop up menu"))
		}, prio=-1, description=_("Wizard Actions"))
		self["dialogactions"].csel = self
		self["dialogactions"].setEnabled(False)
		self.onLayoutFinish.append(self.onCreate)

	def onCreate(self):
		self.setService(self.currentService)
		self.setEvent(self.event)

	def prevEvent(self):
		if self.cbFunc is not None:
			self.cbFunc(self.setEvent, self.setService, -1)

	def nextEvent(self):
		if self.cbFunc is not None:
			self.cbFunc(self.setEvent, self.setService, +1)

	def editTimer(self, timer):
		self.session.open(TimerEntry, timer)

	def removeTimer(self, timer):
		self.closeChoiceBoxDialog()
		timer.afterEvent = AFTEREVENT.NONE
		self.session.nav.RecordTimer.removeEntry(timer)
		self["key_green"].setText(_("Add Timer"))
		self.key_green_choice = self.ADD_TIMER

	def timerAdd(self):
		if self.isRecording:
			return
		event = self.event
		serviceref = self.currentService
		if event is None:
			return
		eventid = event.getEventId()
		refstr = ":".join(serviceref.ref.toString().split(":")[:11])
		for timer in self.session.nav.RecordTimer.timer_list:
			if timer.eit == eventid and ":".join(timer.service_ref.ref.toString().split(":")[:11]) == refstr:
				# Disable dialog box -> Workaround for non closed dialog when press key GREEN for Delete Timer.  (Crash when again GREEN, BLUE or OK key was pressed.)
				self.editTimer(timer)
				break
				cb_func1 = lambda ret: self.removeTimer(timer)
				cb_func2 = lambda ret: self.editTimer(timer)
				menu = [
					(_("Delete Timer"), "CALLFUNC", self.ChoiceBoxCB, cb_func1),
					(_("Edit Timer"), "CALLFUNC", self.ChoiceBoxCB, cb_func2)
				]
				self.ChoiceBoxDialog = self.session.instantiateDialog(ChoiceBox, title=_("Select action for timer %s:") % event.getEventName(), list=menu, keys=["green", "blue"], skin_name="RecordTimerQuestion")
				self.ChoiceBoxDialog.instance.move(ePoint(self.instance.position().x() + self["key_green"].getPosition()[0], self.instance.position().y() + self["key_green"].getPosition()[1] - self["key_green"].instance.size().height()))
				self.showChoiceBoxDialog()
				break
		else:
			newEntry = RecordTimerEntry(self.currentService, checkOldTimers=True, dirname=preferredTimerPath(), *parseEvent(self.event))
			self.session.openWithCallback(self.finishedAdd, TimerEntry, newEntry)

	def ChoiceBoxCB(self, choice):
		if choice:
			choice(self)
		self.closeChoiceBoxDialog()

	def showChoiceBoxDialog(self):
		self["actions"].setEnabled(False)
		self["dialogactions"].setEnabled(True)
		self.ChoiceBoxDialog["actions"].execBegin()
		self.ChoiceBoxDialog.show()

	def closeChoiceBoxDialog(self):
		self["dialogactions"].setEnabled(False)
		if self.ChoiceBoxDialog:
			self.ChoiceBoxDialog["actions"].execEnd()
			self.session.deleteDialog(self.ChoiceBoxDialog)
		self["actions"].setEnabled(True)

	def finishedAdd(self, answer):
		print("[EventView] Finished add.")
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
						except: # maybe already been imported from another module
							pass
						self.session.openWithCallback(self.finishSanityCorrection, TimerSanityConflict, simulTimerList)
			self["key_green"].setText(_("Change Timer"))
			self.key_green_choice = self.REMOVE_TIMER
		else:
			self["key_green"].setText(_("Add Timer"))
			self.key_green_choice = self.ADD_TIMER
			print("[EventView] Timer edit aborted.")

	def finishSanityCorrection(self, answer):
		self.finishedAdd(answer)

	def setService(self, service):
		self.currentService = service
		self["Service"].newService(service.ref)
		if self.isRecording:
			self["channel"].setText(_("Recording"))
		else:
			name = service.getServiceName()
			if name is not None:
				self["channel"].setText(name)
			else:
				self["channel"].setText(_("Unknown Service"))

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
		beginTimeString = event.getBeginTimeString()
		if not beginTimeString:
			return
		begintime = begindate = []
		for x in beginTimeString.split(" "):
			x = x.rstrip(",").rstrip(".")
			if ":" in x:
				begintime = x.split(":")
			elif "." in x:
				begindate = x.split(".")
			elif "/" in x:
				begindate = x.split("/")
				begindate.reverse()
		# Check!
		fail = False
		try:
			if len(begintime) < 2 and len(begindate) < 2 or int(begintime[0]) > 23 or int(begintime[1]) > 59 or int(begindate[0]) > 31 or int(begindate[1]) > 12:
				fail = True
		except:
			fail = True
		if fail:
			print("[EventView] Error: Wrong time stamp detected - source = %s, date = %s, time = %s!" % (beginTimeString, begindate, begintime))
			return
		# End of check!
		nowt = time()
		now = localtime(nowt)
		begin = localtime(int(mktime((now.tm_year, int(begindate[1]), int(begindate[0]), int(begintime[0]), int(begintime[1]), 0, now.tm_wday, now.tm_yday, now.tm_isdst))))
		end = localtime(int(mktime((now.tm_year, int(begindate[1]), int(begindate[0]), int(begintime[0]), int(begintime[1]), 0, now.tm_wday, now.tm_yday, now.tm_isdst))) + event.getDuration())
		self["datetime"].setText("%s - %s" % (strftime("%s, %s" % (config.usage.date.short.value, config.usage.time.short.value), begin), strftime(config.usage.time.short.value, end)))
		self["duration"].setText(_("%d min") % (event.getDuration() / 60))
		if self.SimilarBroadcastTimer is not None:
			self.SimilarBroadcastTimer.start(400, True)
		serviceref = self.currentService
		eventid = self.event.getEventId()
		refstr = ":".join(serviceref.ref.toString().split(":")[:11])
		isRecordEvent = False
		for timer in self.session.nav.RecordTimer.timer_list:
			if timer.eit == eventid and ":".join(timer.service_ref.ref.toString().split(":")[:11]) == refstr:
				isRecordEvent = True
				break
		if isRecordEvent and self.key_green_choice and self.key_green_choice != self.REMOVE_TIMER:
			self["key_green"].setText(_("Change Timer"))
			self.key_green_choice = self.REMOVE_TIMER
		elif not isRecordEvent and self.key_green_choice and self.key_green_choice != self.ADD_TIMER:
			self["key_green"].setText(_("Add Timer"))
			self.key_green_choice = self.ADD_TIMER

	def pageUp(self):
		self["epg_description"].pageUp()
		self["FullDescription"].pageUp()

	def pageDown(self):
		self["epg_description"].pageDown()
		self["FullDescription"].pageDown()

	def getSimilarEvents(self):
		# Search for similar events.
		if not self.event:
			return
		refstr = str(self.currentService)
		id = self.event.getEventId()
		epgcache = eEPGCache.getInstance()
		ret = epgcache.search(("NB", 100, eEPGCache.SIMILAR_BROADCASTINGS_SEARCH, refstr, id))
		if ret is not None:
			text = "\n\n%s" % _("Similar broadcasts:")
			for x in sorted(ret, key=lambda x: x[1]):
				t = localtime(x[1])
				text += "\n%s - %s" % (strftime(config.usage.date.long.value + ", " + config.usage.time.short.value, t), x[0])
			descr = self["epg_description"]
			descr.setText(descr.getText() + text)
			descr = self["FullDescription"]
			descr.setText(descr.getText() + text)
			self["key_red"].setText(_("Similar"))

	def openSimilarList(self):
		if self.similarEPGCB is not None and self["key_red"].getText():
			id = self.event and self.event.getEventId()
			refstr = str(self.currentService)
			if id is not None:
				self.similarEPGCB(id, refstr)

	def doContext(self):
		if self.event:
			menu = []
			for p in plugins.getPlugins(PluginDescriptor.WHERE_EVENTINFO):
				# Only list service or event specific eventinfo plugins here, no servelist plugins.
				if "servicelist" not in p.__call__.__code__.co_varnames:
					menu.append((p.name, boundFunction(self.runPlugin, p)))
			if menu:
				self.session.open(EventViewContextMenu, menu)

	def runPlugin(self, plugin):
		plugin(session=self.session, service=self.currentService, event=self.event, eventName=self.event.getEventName())


class EventViewSimple(Screen, HelpableScreen, EventViewBase):
	def __init__(self, session, event, ref, callback=None, singleEPGCB=None, multiEPGCB=None, similarEPGCB=None, skin="EventViewSimple"):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		EventViewBase.__init__(self, event, ref, callback, similarEPGCB)
		self.setTitle(_("Event View"))
		self.skinName = [skin, "EventView"]
		self.key_green_choice = None


class EventViewEPGSelect(Screen, HelpableScreen, EventViewBase):
	def __init__(self, session, event, ref, callback=None, singleEPGCB=None, multiEPGCB=None, similarEPGCB=None):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		EventViewBase.__init__(self, event, ref, callback, similarEPGCB)
		self.skinName = "EventView"
		self.key_green_choice = self.ADD_TIMER
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


class EventViewMovieEvent(Screen, HelpableScreen):
	def __init__(self, session, name=None, ext_desc=None, dur=None):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
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

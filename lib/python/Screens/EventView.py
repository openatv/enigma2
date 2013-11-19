from Screens.Screen import Screen
from Screens.TimerEdit import TimerSanityConflict
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Components.ScrollLabel import ScrollLabel
from Components.PluginComponent import plugins
from Components.MenuList import MenuList
from Components.UsageConfig import preferredTimerPath
from Components.Pixmap import Pixmap
from Components.Sources.ServiceEvent import ServiceEvent
from Components.Sources.Event import Event
from RecordTimer import RecordTimerEntry, parseEvent, AFTEREVENT
from Screens.TimerEntry import TimerEntry
from Plugins.Plugin import PluginDescriptor
from Tools.Directories import resolveFilename, SCOPE_ACTIVE_SKIN
from Tools.BoundFunction import boundFunction
from time import localtime, mktime, time, strftime
from os import path
from enigma import eEPGCache, eTimer, eServiceReference

class EventViewContextMenu(Screen):
	def __init__(self, session, service, event):
		Screen.__init__(self, session)
		self.setTitle(_('Event view'))
		self.event = event
		self.service = service
		self.eventname = event.getEventName()

		self["actions"] = ActionMap(["OkCancelActions"],
			{
				"ok": self.okbuttonClick,
				"cancel": self.cancelClick
			})

		menu = []

		for p in plugins.getPlugins(PluginDescriptor.WHERE_EVENTINFO):
			#only list service or event specific eventinfo plugins here, no servelist plugins
			if 'servicelist' not in p.__call__.func_code.co_varnames:
				menu.append((p.name, boundFunction(self.runPlugin, p)))

		self["menu"] = MenuList(menu)

	def okbuttonClick(self):
		self["menu"].getCurrent() and self["menu"].getCurrent()[1]()

	def cancelClick(self):
		self.close(False)

	def runPlugin(self, plugin):
		plugin(session=self.session, service=self.service, event=self.event, eventName=self.eventname)

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
			self["key_red"] = Button("")
			self.SimilarBroadcastTimer = eTimer()
			self.SimilarBroadcastTimer.callback.append(self.getSimilarEvents)
		else:
			self.SimilarBroadcastTimer = None
		self["actions"] = ActionMap(["OkCancelActions", "EventViewActions"],
			{
				"cancel": self.close,
				"ok": self.close,
				"info": self.close,
				"pageUp": self.pageUp,
				"pageDown": self.pageDown,
				"prevEvent": self.prevEvent,
				"nextEvent": self.nextEvent,
				"contextMenu": self.doContext,
			})
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

	def removeTimer(self, timer):
		timer.afterEvent = AFTEREVENT.NONE
		self.session.nav.RecordTimer.removeEntry(timer)
		self["key_green"].setText(_("Add timer"))
		self.key_green_choice = self.ADD_TIMER

	def timerAdd(self):
		if self.isRecording:
			return
		event = self.event
		serviceref = self.currentService
		if event is None:
			return
		eventid = event.getEventId()
		refstr = serviceref.ref.toString()
		for timer in self.session.nav.RecordTimer.timer_list:
			if timer.eit == eventid and timer.service_ref.ref.toString() == refstr:
				cb_func = lambda ret : not ret or self.removeTimer(timer)
				self.session.openWithCallback(cb_func, MessageBox, _("Do you really want to delete %s?") % event.getEventName())
				break
		else:
			newEntry = RecordTimerEntry(self.currentService, checkOldTimers = True, dirname = preferredTimerPath(), *parseEvent(self.event))
			self.session.openWithCallback(self.finishedAdd, TimerEntry, newEntry)

	def finishedAdd(self, answer):
		print "finished add"
		if answer[0]:
			entry = answer[1]
			simulTimerList = self.session.nav.RecordTimer.record(entry)
			if simulTimerList is not None:
				for x in simulTimerList:
					if x.setAutoincreaseEnd(entry):
						self.session.nav.RecordTimer.timeChanged(x)
				simulTimerList = self.session.nav.RecordTimer.record(entry)
				if simulTimerList is not None:
					self.session.openWithCallback(self.finishSanityCorrection, TimerSanityConflict, simulTimerList)
			self["key_green"].setText(_("Remove timer"))
			self.key_green_choice = self.REMOVE_TIMER
		else:
			self["key_green"].setText(_("Add timer"))
			self.key_green_choice = self.ADD_TIMER
			print "Timeredit aborted"

	def finishSanityCorrection(self, answer):
		self.finishedAdd(answer)

	def setService(self, service):
		self.currentService=service
		self["Service"].newService(service.ref)
		if self.isRecording:
			self["channel"].setText(_("Recording"))
		else:
			name = service.getServiceName()
			if name is not None:
				self["channel"].setText(name)
			else:
				self["channel"].setText(_("unknown service"))

	def sort_func(self,x,y):
		if x[1] < y[1]:
			return -1
		elif x[1] == y[1]:
			return 0
		else:
			return 1

	def setEvent(self, event):
		if event is None or not hasattr(event, 'getEventName'):
			return

		self["Event"].newEvent(event)
		self.event = event
		text = event.getEventName()
		self.setTitle(text)

		short = event.getShortDescription()
		extended = event.getExtendedDescription()

		if short == text:
			short = ""

		if short and extended:
			extended = short + '\n' + extended
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
		if beginTimeString.find(', ') > -1:
			begintime = beginTimeString.split(', ')[1].split(':')
			begindate = beginTimeString.split(', ')[0].split('.')
		else:
			if len(beginTimeString.split(' ')) > 1:
				begintime = beginTimeString.split(' ')[1].split(':')
			else:
				return
			begindate = beginTimeString.split(' ')[0].split('.')
		nowt = time()
		now = localtime(nowt)
		test = int(mktime((now.tm_year, int(begindate[1]), int(begindate[0]), int(begintime[0]), int(begintime[1]), 0, now.tm_wday, now.tm_yday, now.tm_isdst)))
		endtime = int(mktime((now.tm_year, int(begindate[1]), int(begindate[0]), int(begintime[0]), int(begintime[1]), 0, now.tm_wday, now.tm_yday, now.tm_isdst))) + event.getDuration()
		endtime = localtime(endtime)
		self["datetime"].setText(event.getBeginTimeString() + ' - ' + strftime(_("%-H:%M"), endtime))
		self["duration"].setText(_("%d min")%(event.getDuration()/60))
		if self.SimilarBroadcastTimer is not None:
			self.SimilarBroadcastTimer.start(400, True)
			
		serviceref = self.currentService
		eventid = self.event.getEventId()
		refstr = serviceref.ref.toString()
		isRecordEvent = False
		for timer in self.session.nav.RecordTimer.timer_list:
			if timer.eit == eventid and timer.service_ref.ref.toString() == refstr:
				isRecordEvent = True
				break
		if isRecordEvent and self.key_green_choice and self.key_green_choice != self.REMOVE_TIMER:
			self["key_green"].setText(_("Remove timer"))
			self.key_green_choice = self.REMOVE_TIMER
		elif not isRecordEvent and self.key_green_choice and self.key_green_choice != self.ADD_TIMER:
			self["key_green"].setText(_("Add timer"))
			self.key_green_choice = self.ADD_TIMER


	def pageUp(self):
		self["epg_description"].pageUp()
		self["FullDescription"].pageUp()

	def pageDown(self):
		self["epg_description"].pageDown()
		self["FullDescription"].pageDown()

	def getSimilarEvents(self):
		# search similar broadcastings
		if not self.event:
			return
		refstr = str(self.currentService)
		id = self.event.getEventId()
		epgcache = eEPGCache.getInstance()
		ret = epgcache.search(('NB', 100, eEPGCache.SIMILAR_BROADCASTINGS_SEARCH, refstr, id))
		if ret is not None:
			text = '\n\n' + _('Similar broadcasts:')
			ret.sort(self.sort_func)
			for x in ret:
				t = localtime(x[1])
				text += '\n%d.%d.%d, %2d:%02d  -  %s'%(t[2], t[1], t[0], t[3], t[4], x[0])
			descr = self["epg_description"]
			descr.setText(descr.getText()+text)
			descr = self["FullDescription"]
			descr.setText(descr.getText()+text)
			self["key_red"].setText(_("Similar"))

	def openSimilarList(self):
		if self.similarEPGCB is not None and self["key_red"].getText():
			id = self.event and self.event.getEventId()
			refstr = str(self.currentService)
			if id is not None:
				self.similarEPGCB(id, refstr)

	def doContext(self):
		if self.event is not None:
			self.session.open(EventViewContextMenu, self.currentService, self.event)

class EventViewSimple(Screen, EventViewBase):
	def __init__(self, session, event, ref, callback=None, singleEPGCB=None, multiEPGCB=None, similarEPGCB=None, skin='EventViewSimple'):
		Screen.__init__(self, session)
		self.skinName = [skin,"EventView"]
		EventViewBase.__init__(self, event, ref, callback, similarEPGCB)
		self.key_green_choice = None

class EventViewEPGSelect(Screen, EventViewBase):
	def __init__(self, session, event, ref, callback=None, singleEPGCB=None, multiEPGCB=None, similarEPGCB=None):
		Screen.__init__(self, session)
		self.skinName = "EventView"
		EventViewBase.__init__(self, event, ref, callback, similarEPGCB)
		self.key_green_choice = self.ADD_TIMER

		# Background for Buttons
		self["red"] = Pixmap()
		self["green"] = Pixmap()
		self["yellow"] = Pixmap()
		self["blue"] = Pixmap()

		self["epgactions1"] = ActionMap(["OkCancelActions", "EventViewActions"],
			{

				"timerAdd": self.timerAdd,
				"openSimilarList": self.openSimilarList,

			})
		if self.isRecording:
			self["key_green"] = Button("")
		else:
			self["key_green"] = Button(_("Add timer"))

		if singleEPGCB:
			self["key_yellow"] = Button(_("Single EPG"))
			self["epgactions2"] = ActionMap(["EventViewEPGActions"],
				{
					"openSingleServiceEPG": singleEPGCB,
				})
		else:
			self["key_yellow"] = Button("")
			self["yellow"].hide()
			
		if multiEPGCB:
			self["key_blue"] = Button(_("Multi EPG"))
			self["epgactions3"] = ActionMap(["EventViewEPGActions"],
				{

					"openMultiServiceEPG": multiEPGCB,
				})
		else:
			self["key_blue"] = Button("")
			self["blue"].hide()

from Screen import Screen
from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.Label import Label
from Components.ScrollLabel import ScrollLabel
from enigma import eEPGCache, eTimer, eServiceReference
from RecordTimer import RecordTimerEntry, parseEvent
from TimerEntry import TimerEntry
from time import localtime
from Components.config import config

class EventViewBase:
	def __init__(self, Event, Ref, callback=None, similarEPGCB=None):
		self.similarEPGCB = similarEPGCB
		self.cbFunc = callback
		self.currentService=Ref
		self.isRecording = (not Ref.ref.flags & eServiceReference.isGroup) and len(Ref.ref.getPath())
		self.event = Event
		self["epg_description"] = ScrollLabel()
		self["datetime"] = Label()
		self["channel"] = Label()
		self["duration"] = Label()
		self["key_red"] = Button("")
		if similarEPGCB is not None:
			self.SimilarBroadcastTimer = eTimer()
			self.SimilarBroadcastTimer.callback.append(self.getSimilarEvents)
		else:
			self.SimilarBroadcastTimer = None
		if self.isRecording:
			self["key_green"] = Button("")
		else:
			self["key_green"] = Button(_("Add timer"))
		self["key_yellow"] = Button("")
		self["key_blue"] = Button("")
		self["actions"] = ActionMap(["OkCancelActions", "EventViewActions"],
			{
				"cancel": self.close,
				"ok": self.close,
				"pageUp": self.pageUp,
				"pageDown": self.pageDown,
				"prevEvent": self.prevEvent,
				"nextEvent": self.nextEvent,
				"timerAdd": self.timerAdd,
				"openSimilarList": self.openSimilarList
			})
		self.onShown.append(self.onCreate)

	def onCreate(self):
		self.setService(self.currentService)
		self.setEvent(self.event)

	def prevEvent(self):
		if self.cbFunc is not None:
			self.cbFunc(self.setEvent, self.setService, -1)

	def nextEvent(self):
		if self.cbFunc is not None:
			self.cbFunc(self.setEvent, self.setService, +1)

	def timerAdd(self):
		if not self.isRecording:
			newEntry = RecordTimerEntry(self.currentService, checkOldTimers = True, dirname = config.movielist.last_timer_videodir.value, *parseEvent(self.event))
			self.session.openWithCallback(self.timerEditFinished, TimerEntry, newEntry)

	def timerEditFinished(self, answer):
		if (answer[0]):
			self.session.nav.RecordTimer.record(answer[1])
		else:
			print "Timeredit aborted"

	def setService(self, service):
		self.currentService=service
		if self.isRecording:
			self["channel"].setText(_("Recording"))
		else:
			name = self.currentService.getServiceName()
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
		self.event = event
		if event is None:
			return
		text = event.getEventName()
		short = event.getShortDescription()
		ext = event.getExtendedDescription()
		if len(short) > 0 and short != text:
			text = text + '\n\n' + short
		if len(ext) > 0:
			if len(text) > 0:
				text = text + '\n\n'
			text = text + ext

		self.setTitle(event.getEventName())
		self["epg_description"].setText(text)
		self["datetime"].setText(event.getBeginTimeString())
		self["duration"].setText(_("%d min")%(event.getDuration()/60))
		self["key_red"].setText("")
		if self.SimilarBroadcastTimer is not None:
			self.SimilarBroadcastTimer.start(400,True)

	def pageUp(self):
		self["epg_description"].pageUp()

	def pageDown(self):
		self["epg_description"].pageDown()

	def getSimilarEvents(self):
	 # search similar broadcastings
		refstr = str(self.currentService)
		id = self.event.getEventId()
		epgcache = eEPGCache.getInstance()
		ret = epgcache.search(('NB', 100, eEPGCache.SIMILAR_BROADCASTINGS_SEARCH, refstr, id))
		if ret is not None:
			descr = self["epg_description"]
			text = descr.getText()
			text += '\n\n' + _('Similar broadcasts:')
			ret.sort(self.sort_func)
			for x in ret:
				t = localtime(x[1])
				text += '\n%d.%d.%d, %02d:%02d  -  %s'%(t[2], t[1], t[0], t[3], t[4], x[0])
			descr.setText(text)
			self["key_red"].setText(_("Similar"))

	def openSimilarList(self):
		if self.similarEPGCB is not None and len(self["key_red"].getText()):
			id = self.event and self.event.getEventId()
			refstr = str(self.currentService)
			if id is not None:
				self.similarEPGCB(id, refstr)

class EventViewSimple(Screen, EventViewBase):
	def __init__(self, session, Event, Ref, callback=None, similarEPGCB=None):
		Screen.__init__(self, session)
		self.skinName = "EventView"
		EventViewBase.__init__(self, Event, Ref, callback, similarEPGCB)

class EventViewEPGSelect(Screen, EventViewBase):
	def __init__(self, session, Event, Ref, callback=None, singleEPGCB=None, multiEPGCB=None, similarEPGCB=None):
		Screen.__init__(self, session)
		self.skinName = "EventView"
		EventViewBase.__init__(self, Event, Ref, callback, similarEPGCB)
		self["key_yellow"].setText(_("Single EPG"))
		self["key_blue"].setText(_("Multi EPG"))
		self["epgactions"] = ActionMap(["EventViewEPGActions"],
			{
				"openSingleServiceEPG": singleEPGCB,
				"openMultiServiceEPG": multiEPGCB,
			})

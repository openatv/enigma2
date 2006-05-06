from Screen import Screen
from Components.Button import Button
from Components.Pixmap import Pixmap
from Components.Label import Label
from Components.EpgList import *
from Components.ActionMap import ActionMap
from Components.ScrollLabel import ScrollLabel
from Screens.EventView import EventViewSimple
from TimeDateInput import TimeDateInput
from enigma import eServiceReference, eServiceEventPtr
from Screens.FixedMenu import FixedMenu
from RecordTimer import RecordTimerEntry, parseEvent
from TimerEdit import TimerEditList
from TimerEntry import TimerEntry
from ServiceReference import ServiceReference
from Components.config import config, currentConfigSelectionElement
from time import localtime, time

import xml.dom.minidom

class EPGSelection(Screen):
	def __init__(self, session, service, zapFunc=None, eventid=None, bouquetChangeCB=None):
		Screen.__init__(self, session)
		self.bouquetChangeCB = bouquetChangeCB
		self.ask_time = -1 #now
		self["key_red"] = Button("")
		self.closeRecursive = False
		if isinstance(service, str) and eventid != None:
			self.type = EPG_TYPE_SIMILAR
			self["key_yellow"] = Button()
			self["key_blue"] = Button()
			self["key_red"] = Button()
			self.currentService=service
			self.eventid = eventid
			self.zapFunc = None
		elif isinstance(service, eServiceReference) or isinstance(service, str):
			self.type = EPG_TYPE_SINGLE
			self["key_yellow"] = Button()
			self["key_blue"] = Button()
			self.currentService=ServiceReference(service)
			self.zapFunc = None
		else:
			self.skinName = "EPGSelectionMulti"
			self.type = EPG_TYPE_MULTI
			self["key_yellow"] = Button(_("Prev"))
			self["key_blue"] = Button(_("Next"))
			self["now_button"] = Pixmap()
			self["next_button"] = Pixmap()
			self["more_button"] = Pixmap()
			self["now_button_sel"] = Pixmap()
			self["next_button_sel"] = Pixmap()
			self["more_button_sel"] = Pixmap()
			self["now_text"] = Label()
			self["next_text"] = Label()
			self["more_text"] = Label()
			self["date"] = Label()
			self.services = service
			self.zapFunc = zapFunc

		self["key_green"] = Button(_("Add timer"))
		self["list"] = EPGList(type = self.type, selChangedCB = self.onSelectionChanged, timer = self.session.nav.RecordTimer)

		class ChannelActionMap(ActionMap):
			def action(self, contexts, action):
				return ActionMap.action(self, contexts, action)

		self["actions"] = ChannelActionMap(["EPGSelectActions", "OkCancelActions"],
			{
				"cancel": self.closeScreen,
				"ok": self.eventSelected,
				"timerAdd": self.timerAdd,
				"yellow": self.yellowButtonPressed,
				"blue": self.blueButtonPressed,
				"info": self.infoKeyPressed,
				"red": self.zapTo,
				"input_date_time": self.enterDateTime,
				"nextBouquet": self.nextBouquet,
				"prevBouquet": self.prevBouquet
			})
		self["actions"].csel = self

		self.onLayoutFinish.append(self.onCreate)

	def nextBouquet(self):
		if self.bouquetChangeCB:
			self.bouquetChangeCB(1, self)

	def prevBouquet(self):
		if self.bouquetChangeCB:
			self.bouquetChangeCB(-1, self)

	def enterDateTime(self):
		if self.type == EPG_TYPE_MULTI:
			self.session.openWithCallback(self.onDateTimeInputClosed, TimeDateInput)

	def onDateTimeInputClosed(self, ret):
		if len(ret) > 1:
			if ret[0]:
				self.ask_time=ret[1]
				self["list"].fillMultiEPG(self.services, ret[1])

	def closeScreen(self):
		self.close(self.closeRecursive)

	def infoKeyPressed(self):
		cur = self["list"].getCurrent()
		event = cur[0]
		service = cur[1]
		if event is not None:
			if self.type != EPG_TYPE_SIMILAR:
				self.session.open(EventViewSimple, event, service, self.eventViewCallback, self.openSimilarList)
			else:
				self.session.open(EventViewSimple, event, service, self.eventViewCallback)

	def openSimilarList(self, eventid, refstr):
		self.session.open(EPGSelection, refstr, None, eventid)

	def setServices(self, services):
		self.services = services
		self.onCreate()

	#just used in multipeg
	def onCreate(self):
		l = self["list"]
		l.recalcEntrySize()
		if self.type == EPG_TYPE_MULTI:
			l.fillMultiEPG(self.services, self.ask_time)
		elif self.type == EPG_TYPE_SINGLE:
			l.fillSingleEPG(self.currentService)
		else:
			l.fillSimilarList(self.currentService, self.eventid)

	def eventViewCallback(self, setEvent, setService, val):
		l = self["list"]
		old = l.getCurrent()
		if val == -1:
			self.moveUp()
		elif val == +1:
			self.moveDown()
		cur = l.getCurrent()
		if self.type == EPG_TYPE_MULTI and cur[0] is None and cur[1].ref != old[1].ref:
			self.eventViewCallback(setEvent, setService, val)
		else:
			setService(cur[1])
			setEvent(cur[0])

	def zapTo(self): # just used in multiepg
		if self.zapFunc and self["key_red"].getText() == "Zap":
			lst = self["list"]
			count = lst.getCurrentChangeCount()
			if count == 0:
				self.closeRecursive = True
				ref = lst.getCurrent()[1]
				self.zapFunc(ref.ref)

	def eventSelected(self):
		self.infoKeyPressed()

	def yellowButtonPressed(self):
		if self.type == EPG_TYPE_MULTI:
			self["list"].updateMultiEPG(-1)

	def blueButtonPressed(self):
		if self.type == EPG_TYPE_MULTI:
			self["list"].updateMultiEPG(1)

	def timerAdd(self):
		cur = self["list"].getCurrent()
		event = cur[0]
		serviceref = cur[1]
		if event is None:
			return
		newEntry = RecordTimerEntry(serviceref, checkOldTimers = True, *parseEvent(event))
		self.session.openWithCallback(self.timerEditFinished, TimerEntry, newEntry)

	def timerEditFinished(self, answer):
		if answer[0]:
			self.session.nav.RecordTimer.record(answer[1])
		else:
			print "Timeredit aborted"	

	def moveUp(self):
		self["list"].moveUp()

	def moveDown(self):
		self["list"].moveDown()

	def applyButtonState(self, state):
		if state == 0:
			self["now_button"].hide()
			self["now_button_sel"].hide()
			self["next_button"].hide()
			self["next_button_sel"].hide()
			self["more_button"].hide()
			self["more_button_sel"].hide()
			self["now_text"].hide()
			self["next_text"].hide()
			self["more_text"].hide()
			self["key_red"].setText("")
		else:
			if state == 1:
				self["key_red"].setText("Zap")
				self["now_button_sel"].show()
				self["now_button"].hide()
			else:
				self["now_button"].show()
				self["now_button_sel"].hide()
				self["key_red"].setText("")

			if state == 2:
				self["next_button_sel"].show()
				self["next_button"].hide()
			else:
				self["next_button"].show()
				self["next_button_sel"].hide()

			if state == 3:
				self["more_button_sel"].show()
				self["more_button"].hide()
			else:
				self["more_button"].show()
				self["more_button_sel"].hide()

	def onSelectionChanged(self):
		if self.type == EPG_TYPE_MULTI:
			count = self["list"].getCurrentChangeCount()
			if self.ask_time != -1:
				self.applyButtonState(0)
			elif count > 1:
				self.applyButtonState(3)
			elif count > 0:
				self.applyButtonState(2)
			else:
				self.applyButtonState(1)
			days = [ _("Mon"), _("Tue"), _("Wed"), _("Thu"), _("Fri"), _("Sat"), _("Sun") ]
			datastr = ""
			event = self["list"].getCurrent()[0]
			if event is not None:
				now = time()
				beg = event.getBeginTime()
				nowTime = localtime(now)
				begTime = localtime(beg)
				if nowTime[2] != begTime[2]:
					datestr = '%s %d.%d.'%(days[begTime[6]], begTime[2], begTime[1])
				else:
					datestr = '%s %d.%d.'%(_("Today"), begTime[2], begTime[1])
			self["date"].setText(datestr)

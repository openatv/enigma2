from Screen import Screen
from Components.Button import Button
from Components.EpgList import *
from Components.ActionMap import ActionMap
from Screens.EventView import EventView
from enigma import eServiceReference, eServiceEventPtr
from Screens.FixedMenu import FixedMenu
from RecordTimer import RecordTimerEntry, parseEvent
from TimerEdit import TimerEditList
from TimerEntry import TimerEntry
from ServiceReference import ServiceReference
from Components.config import config, currentConfigSelectionElement

import xml.dom.minidom

class EPGSelection(Screen):
	def __init__(self, session, service):
		Screen.__init__(self, session)

		self["key_red"] = Button("")
		self["key_green"] = Button(_("Add timer"))

		if isinstance(service, eServiceReference):
			self.type = EPG_TYPE_SINGLE
			self["key_yellow"] = Button()
			self["key_blue"] = Button()
			self.currentService=ServiceReference(service)
		else:
			self.type = EPG_TYPE_MULTI
			self["key_yellow"] = Button(_("Prev"))
			self["key_blue"] = Button(_("Next"))
			self.services = service

		self["list"] = EPGList(self.type)

		class ChannelActionMap(ActionMap):
			def action(self, contexts, action):
				ActionMap.action(self, contexts, action)

		self["actions"] = ChannelActionMap(["EPGSelectActions", "OkCancelActions"],
			{
				"cancel": self.closeScreen,
				"ok": self.eventSelected,
				"timerAdd": self.timerAdd,
				"yellow": self.yellowButtonPressed,
				"blue": self.blueButtonPressed,
				"info": self.infoKeyPressed
			})
		self["actions"].csel = self

		self.onLayoutFinish.append(self.onCreate)

	def infoKeyPressed(self):
		if currentConfigSelectionElement(config.usage.epgtoggle) == "yes":
			self.close(True)
		else:
			self.close(False)

	def closeScreen(self):
		self.close(False)


	#just used in multipeg
	def onCreate(self):
		l = self["list"]
		if self.type == EPG_TYPE_MULTI:
			l.recalcEntrySize()
			l.fillMultiEPG(self.services)
		else:
			if SINGLE_CPP == 0:
				l.recalcEntrySize()
			l.fillSingleEPG(self.currentService)

	def eventViewCallback(self, setEvent, setService, val):
		l = self["list"]
		old = l.getCurrent()
		if val == -1:
			self.moveUp()
		elif val == +1:
			self.moveDown()
		cur = l.getCurrent()
		if self.type == EPG_TYPE_SINGLE:
			setEvent(cur)
		else:
			if self.type == EPG_TYPE_MULTI and cur[0] is None and cur[1].ref != old[1].ref:
				self.eventViewCallback(setEvent, setService, val)
			else:
				setEvent(cur[0])
				setService(cur[1])

	def eventSelected(self):
		if self.type == EPG_TYPE_SINGLE:
			event = self["list"].getCurrent()
			service = self.currentService
		else: # EPG_TYPE_MULTI
			cur = self["list"].getCurrent()
			event = cur[0]
			service = cur[1]
		if event is not None:
			self.session.open(EventView, event, service, self.eventViewCallback)

	def yellowButtonPressed(self):
		if self.type == EPG_TYPE_MULTI:
			self["list"].updateMultiEPG(-1)

	def blueButtonPressed(self):
		if self.type == EPG_TYPE_MULTI:
			self["list"].updateMultiEPG(1)

	def timerAdd(self):
		if self.type == EPG_TYPE_SINGLE:
			event = self["list"].getCurrent()
			serviceref = self.currentService
		else:
			cur = self["list"].getCurrent()
			event = cur[0]
			serviceref = cur[1]
		if event is None:
			return
		newEntry = RecordTimerEntry(serviceref, *parseEvent(event))
		self.session.openWithCallback(self.timerEditFinished, TimerEntry, newEntry)

	def timerEditFinished(self, answer):
		if (answer[0]):
			self.session.nav.RecordTimer.record(answer[1])
		else:
			print "Timeredit aborted"	

	def moveUp(self):
		self["list"].moveUp()

	def moveDown(self):
		self["list"].moveDown()

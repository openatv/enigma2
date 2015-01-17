from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.Label import Label
from Components.config import config
from Components.MenuList import MenuList
from Components.TimerList import TimerList
from Components.TimerSanityCheck import TimerSanityCheck
from Components.UsageConfig import preferredTimerPath
from Components.Sources.StaticText import StaticText
from RecordTimer import RecordTimerEntry, parseEvent, AFTEREVENT
from Screens.Screen import Screen
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from ServiceReference import ServiceReference
from Screens.TimerEntry import TimerEntry, TimerLog
from Tools.BoundFunction import boundFunction
from Tools.FuzzyDate import FuzzyTime
from time import time
from timer import TimerEntry as RealTimerEntry

class TimerListButtons:

	EMPTY = 0

	def __init__(self):

		self.key_choice = {
			"red"    : self.EMPTY,
			"green"  : self.EMPTY,
			"yellow" : self.EMPTY,
			"blue"   : self.EMPTY
		}

		self["key_red"] = Button()
		self["key_green"] = Button()
		self["key_yellow"] = Button()
		self["key_blue"] = Button()

		self.buttonActions = (
			(None,                      ""),     # EMPTY = 0
		)

	def removeAction(self, descr):
		actions = self["actions"].actions
		if descr in actions:
			del actions[descr]

	def assignButton(self, colour, action):
		if self.key_choice[colour] != action:
			act = self.buttonActions[action]
			if act[0] is None:
				self.removeAction(colour)
			else:
				self["actions"].actions.update({colour:act[0]})
			self["key_"+colour].setText(act[1])
			self.key_choice[colour] = act

	def updateRedState(self, cur):
		pass

	def updateGreenState(self, cur):
		pass

	def updateYellowState(self, cur):
		pass

	def updateBlueState(self, cur):
		pass

	def updateState(self):
		self.updateRedState(None)
		self.updateGreenState(None)
		self.updateYellowState(None)
		self.updateBlueState(None)

class TimerEditList(Screen, TimerListButtons):

	DELETE = 1
	ADD = 2
	ENABLE = 3
	DISABLE = 4
	STOPDISABLE = 5
	STOP = 6
	CLEANUP = 7

	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Timer List"))
		TimerListButtons.__init__(self)

		self.onChangedEntry = [ ]
		list = [ ]
		self.list = list
		self.fillTimerList()

		self["timerlist"] = TimerList(list)

		self.buttonActions = (
			(None,                      ""),                  # EMPTY = 0
			(self.removeTimerQuestion,  _("Delete")),         # DELETE = 1
			(self.addCurrentTimer,      _("Add")),            # ADD = 2
			(self.toggleDisabledState,  _("Enable")),         # ENABLE = 3
			(self.toggleDisabledState,  _("Disable")),        # DISABLE = 4
			(self.toggleDisabledState,  _("Stop/Disable")),   # STOPDISABLE = 5
			(self.stopRecording,        _("Stop recording")), # STOP = 6
			(self.cleanupQuestion,      _("Cleanup")),        # CLEANUP = 7
		)

		self["description"] = Label()

		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ShortcutActions", "TimerEditActions"],
			{
				"ok": self.openEdit,
				"cancel": self.leave,
				"log": self.showLog,
				"left": self.left,
				"right": self.right,
				"up": self.up,
				"down": self.down
			}, -1)
		self.setTitle(_("Timer overview"))
		self.session.nav.RecordTimer.on_state_change.append(self.onStateChange)
		self.onShown.append(self.updateState)

	def createSummary(self):
		return TimerEditListSummary

	def up(self):
		self["timerlist"].instance.moveSelection(self["timerlist"].instance.moveUp)
		self.updateState()

	def down(self):
		self["timerlist"].instance.moveSelection(self["timerlist"].instance.moveDown)
		self.updateState()

	def left(self):
		self["timerlist"].instance.moveSelection(self["timerlist"].instance.pageUp)
		self.updateState()

	def right(self):
		self["timerlist"].instance.moveSelection(self["timerlist"].instance.pageDown)
		self.updateState()

	def stopRecording(self):
		cur=self["timerlist"].getCurrent()
		if cur:
			self.runningEventCallback(cur, (_("Stop current event"), "stoponlycurrent"))

	def toggleDisabledState(self):
		cur=self["timerlist"].getCurrent()
		if cur:
			t = cur
			if t.disabled:
# 				print "try to ENABLE timer"
				t.enable()
				timersanitycheck = TimerSanityCheck(self.session.nav.RecordTimer.timer_list, cur)
				if not timersanitycheck.check():
					t.disable()
					print "Sanity check failed"
					simulTimerList = timersanitycheck.getSimulTimerList()
					if simulTimerList is not None:
						self.session.openWithCallback(self.finishedEdit, TimerSanityConflict, simulTimerList)
				else:
					print "Sanity check passed"
					if timersanitycheck.doubleCheck():
						t.disable()
			else:
				if t.isRunning():
					if t.repeated:
						list = (
							(_("Stop current event but not future events"), "stoponlycurrent"),
							(_("Stop current event and disable future events"), "stopall"),
							(_("Don't stop current event but disable future events"), "stoponlyfuture")
						)
						self.session.openWithCallback(boundFunction(self.runningEventCallback, t), ChoiceBox, title=_("Repeating event currently recording... What do you want to do?"), list = list)
				else:
					t.disable()
			self.session.nav.RecordTimer.timeChanged(t)
			self.refill()
			self.updateState()

	def runningEventCallback(self, t, result):
		if result is not None:
			if result[1] == "stoponlycurrent" or result[1] == "stopall":
				t.enable()
				t.processRepeated(findRunningEvent = False)
				self.session.nav.RecordTimer.doActivate(t)
			if result[1] == "stoponlyfuture" or result[1] == "stopall":
				t.disable()
			if t.repeated:
				self.session.nav.RecordTimer.timeChanged(t)
			self.refill()
			self.updateState()

	def updateRedState(self, cur):
		col = "red"
		if cur:
			self.assignButton(col, self.DELETE)
		else:
			self.assignButton(col, self.EMPTY)

	def updateGreenState(self, cur):
		self.assignButton("green", self.ADD)

	def updateYellowState(self, cur):
		col = "yellow"
		if cur:
			if cur.disabled:
				self.assignButton(col, self.ENABLE)
			else:
				if cur.isRunning():
					if cur.repeated:
						self.assignButton(col, self.STOPDISABLE)
					else:
						self.assignButton(col, self.STOP)
				else:
					self.assignButton(col, self.DISABLE)
		else:
			self.assignButton(col, self.EMPTY)

	def updateBlueState(self, cur):
		col = "blue"
		showCleanup = True
		for x in self.list:
			if (not x[0].disabled) and (x[1] == True):
				break
		else:
			showCleanup = False

		if showCleanup:
			self.assignButton(col, self.CLEANUP)
		else:
			self.assignButton(col, self.EMPTY)

	def updateState(self):
		cur = self["timerlist"].getCurrent()

		if cur:
			self["description"].setText(cur.description)
		else:
			self["description"].setText("")

		self.updateRedState(cur)
		self.updateGreenState(cur)
		self.updateYellowState(cur)
		self.updateBlueState(cur)

		if len(self.list) == 0:
			return
		timer = self['timerlist'].getCurrent()

		if timer:
			try:
				name = str(timer.name)
				time = "%s %s ... %s" % (FuzzyTime(timer.begin)[0], FuzzyTime(timer.begin)[1], FuzzyTime(timer.end)[1])
				duration = ("(%d " + _("mins") + ")") % ((timer.end - timer.begin) / 60)
				service = str(timer.service_ref.getServiceName())

				if timer.state == RealTimerEntry.StateWaiting:
					state = _("waiting")
				elif timer.state == RealTimerEntry.StatePrepared:
					state = _("about to start")
				elif timer.state == RealTimerEntry.StateRunning:
					if timer.justplay:
						state = _("zapped")
					else:
						state = _("recording...")
				elif timer.state == RealTimerEntry.StateEnded:
					state = _("done!")
				else:
					state = _("<unknown>")
			except:
				name = ""
				time = ""
				duration = ""
				service = ""
		else:
			name = ""
			time = ""
			duration = ""
			service = ""
		for cb in self.onChangedEntry:
			cb(name, time, duration, service, state)

	def fillTimerTest(self, timer):
		return True

	def fillTimerList(self):
		#helper function to move finished timers to end of list
		def eol_compare(x, y):
			if x[0].state != y[0].state and x[0].state == RealTimerEntry.StateEnded or y[0].state == RealTimerEntry.StateEnded:
				return cmp(x[0].state, y[0].state)
			return cmp(x[0].begin, y[0].begin)

		list = self.list
		del list[:]
		list.extend([(timer, False) for timer in self.session.nav.RecordTimer.timer_list if self.fillTimerTest(timer)])
		list.extend([(timer, True) for timer in self.session.nav.RecordTimer.processed_timers if self.fillTimerTest(timer)])
		if config.usage.timerlist_finished_timer_position.index: #end of list
			list.sort(cmp = eol_compare)
		else:
			list.sort(key = lambda x: x[0].begin)

	def showLog(self):
		cur=self["timerlist"].getCurrent()
		if cur:
			self.session.openWithCallback(self.finishedEdit, TimerLog, cur)

	def openEdit(self):
		cur=self["timerlist"].getCurrent()
		if cur:
			self.session.openWithCallback(self.finishedEdit, TimerEntry, cur)

	def cleanupQuestion(self):
		self.session.openWithCallback(self.cleanupTimer, MessageBox, _("Really delete done timers?"))

	def cleanupTimer(self, delete):
		if delete:
			self.session.nav.RecordTimer.cleanup()
			self.refill()
			self.updateState()

	def removeTimerQuestion(self):
		cur = self["timerlist"].getCurrent()
		if not cur:
			return

		self.session.openWithCallback(self.removeTimer, MessageBox, _("Do you really want to delete %s?") % cur.name, default = False)

	def removeTimer(self, result):
		if not result:
			return
		list = self["timerlist"]
		cur = list.getCurrent()
		if cur:
			timer = cur
			timer.afterEvent = AFTEREVENT.NONE
			self.session.nav.RecordTimer.removeEntry(timer)
			self.refill()
			self.updateState()


	def refill(self):
		oldsize = len(self.list)
		self.fillTimerList()
		lst = self["timerlist"]
		newsize = len(self.list)
		if oldsize and oldsize != newsize:
			idx = lst.getCurrentIndex()
			lst.entryRemoved(idx)
		else:
			lst.invalidate()

	def addCurrentTimer(self):
		event = None
		service = self.session.nav.getCurrentService()
		if service is not None:
			info = service.info()
			if info is not None:
				event = info.getEvent(0)

		# FIXME only works if already playing a service
		serviceref = ServiceReference(self.session.nav.getCurrentlyPlayingServiceOrGroup())

		if event is None:
			data = (int(time()), int(time() + 60), "", "", None)
		else:
			data = parseEvent(event, description = False)

		self.addTimer(RecordTimerEntry(serviceref, checkOldTimers = True, dirname = preferredTimerPath(), *data))

	def addTimer(self, timer):
		self.session.openWithCallback(self.finishedAdd, TimerEntry, timer)


	def finishedEdit(self, answer):
# 		print "finished edit"

		if answer[0]:
# 			print "Edited timer"
			entry = answer[1]
			timersanitycheck = TimerSanityCheck(self.session.nav.RecordTimer.timer_list, entry)
			success = False
			if not timersanitycheck.check():
				simulTimerList = timersanitycheck.getSimulTimerList()
				if simulTimerList is not None:
					for x in simulTimerList:
						if x.setAutoincreaseEnd(entry):
							self.session.nav.RecordTimer.timeChanged(x)
					if not timersanitycheck.check():
						simulTimerList = timersanitycheck.getSimulTimerList()
						if simulTimerList is not None:
							self.session.openWithCallback(self.finishedEdit, TimerSanityConflict, timersanitycheck.getSimulTimerList())
					else:
						success = True
			else:
				success = True
			if success:
				print "Sanity check passed"
				self.session.nav.RecordTimer.timeChanged(entry)

			self.fillTimerList()
			self.updateState()
# 		else:
# 			print "Timeredit aborted"

	def finishedAdd(self, answer):
# 		print "finished add"
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
			self.fillTimerList()
			self.updateState()
# 		else:
# 			print "Timeredit aborted"

	def finishSanityCorrection(self, answer):
		self.finishedAdd(answer)

	def leave(self):
		self.session.nav.RecordTimer.on_state_change.remove(self.onStateChange)
		self.close()

	def onStateChange(self, entry):
		self.refill()
		self.updateState()

class TimerStopList(TimerEditList):

	DELETE = 1
	STOP = 2
	MORE = 3

	def __init__(self, session):
		TimerEditList.__init__(self, session)

                self.skinName = ["TimerEditList"]
		Screen.setTitle(self, _("Timer List"))

		self.buttonActions = (
			(None,                      ""),                  # EMPTY = 0
			(self.removeTimerQuestion,  _("Delete")),         # DELETE = 1
			(self.stopRecording,        _("Stop recording")), # STOP = 2
			(self.openTimerEdit,        _("Timer overview")), # MORE = 3
		)

		self.setTitle(_("Stop Recordings"))

	def updateGreenState(self, cur):
		pass

	def updateYellowState(self, cur):
		col = "yellow"
		if cur and cur.isRunning():
			self.assignButton(col, self.STOP)
		else:
			self.assignButton(col, self.EMPTY)

	def updateBlueState(self, cur):
		self.assignButton("blue", self.MORE)

	def openTimerEdit(self):
		self.session.open(TimerEditList)
		# Make sure any changes made in TimerEditList are reflected here
		self.refill()
		self.updateState()

	def fillTimerTest(self, timer):
		# Only include running timers
		return timer.isRunning()

class TimerSanityConflict(Screen, TimerListButtons):

	EDIT1 = 1
	EDIT2 = 2
	ENABLE = 3
	DISABLE = 4
	STOPDISABLE = 5

	def __init__(self, session, timer):
		Screen.__init__(self, session)
		TimerListButtons.__init__(self)

		self.timer = timer
		print "TimerSanityConflict"

		self["lab1"] = StaticText(_("New timer"))
		self["lab2"] = StaticText(_("Conflicting timers"))
		self["timer1"] = TimerList(self.getTimerList(timer[0]))
		self.list2 = []
		count = 0
		for x in timer:
			if count != 0:
				self.list2.append((timer[count], False))
			count += 1
		if count == 1:
			self.list.append((_("Channel not in services list")))

		self["timer2"] = TimerList(self.list2)

		self.buttonActions = (
			(None,              ""),                  # EMPTY = 0
			(self.editTimer1,   _("Edit")),           # EDIT1 = 1
			(self.editTimer2,   _("Edit")),           # EDIT2 = 2
			(self.toggleTimer,  _("Enable")),         # ENABLE = 3
			(self.toggleTimer,  _("Disable")),        # DISABLE = 4
			(self.toggleTimer,  _("Stop & Disable")), # STOPDISABLE = 5
		)

		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ShortcutActions", "TimerEditActions"],
			{
				"ok": self.leave_ok,
				"cancel": self.leave_cancel,
				"left": self.left,
				"right": self.right,
				"up": self.up,
				"down": self.down
			}, -1)
		self.setTitle(_("Timer sanity error"))
		self.onShown.append(self.updateState)

	def getTimerList(self, timer):
		return [(timer, False)]

	def editTimer1(self):
		self.session.openWithCallback(self.finishedEdit, TimerEntry, self["timer1"].getCurrent())

	def editTimer2(self):
		self.session.openWithCallback(self.finishedEdit, TimerEntry, self["timer2"].getCurrent())

	def toggleTimer(self):
		x = self["timer2"].getCurrentIndex() + 1 # the first is the new timer so we do +1 here
		if self.timer[x].disabled:
			self.timer[x].enable()
			self.session.nav.RecordTimer.timeChanged(self.timer[x])
			if self.timer[0].isRunning():
				self.timer[0].enable()
				self.timer[0].processRepeated(findRunningEvent = False)
				self.session.nav.RecordTimer.doActivate(self.timer[0])
				self.timer[0].disable()
			self.session.nav.RecordTimer.timeChanged(self.timer[0])
		else:
			if self.timer[x].isRunning():
				self.timer[x].enable()
				self.timer[x].processRepeated(findRunningEvent = False)
				self.session.nav.RecordTimer.doActivate(self.timer[x])
			self.timer[x].disable()
			self.session.nav.RecordTimer.timeChanged(self.timer[x])
			if self.timer[x].disabled:
				self.timer[0].enable()
				self.session.nav.RecordTimer.timeChanged(self.timer[0])
		self.finishedEdit((True, self.timer[0]))

	def finishedEdit(self, answer):
		self.leave_ok()

	def leave_ok(self):
		self.close((True, self.timer[0]))

	def leave_cancel(self):
		self.close((False, self.timer[0]))

	def up(self):
		self["timer2"].instance.moveSelection(self["timer2"].instance.moveUp)
		self.updateState()

	def down(self):
		self["timer2"].instance.moveSelection(self["timer2"].instance.moveDown)
		self.updateState()

	def left(self):
		self["timer2"].instance.moveSelection(self["timer2"].instance.pageUp)
		self.updateState()

	def right(self):
		self["timer2"].instance.moveSelection(self["timer2"].instance.pageDown)
		self.updateState()

	def updateRedState(self, cur):
		self.assignButton("red", self.EDIT1)

	def updateYellowState(self, cur):
		col = "yellow"
		if cur is not None:
			self.assignButton(col, self.EDIT2)
		else:
			self.assignButton(col, self.EMPTY)

	def updateBlueState(self, cur):
		col = "blue"
		if cur is not None:
			if cur.disabled:
				self.assignButton(col, self.ENABLE)
			else:
				if cur.isRunning():
					self.assignButton(col, self.STOPDISABLE)
				else:
					self.assignButton(col, self.DISABLE)
		else:
			self.assignButton(col, self.EMPTY)

	def updateState(self):
		self.updateRedState(None)

		if len(self.timer) > 1:
			x = self["timer2"].getCurrentIndex() + 1 # the first is the new timer so we do +1 here
			self.updateYellowState(self.timer[x])
			self.updateBlueState(self.timer[x])
		else:
#FIXME.... this doesnt hide the buttons self.... just the text
			self.updateYellowState(None)
			self.updateBlueState(None)

class TimerEditListSummary(Screen):
	def __init__(self, session, parent):
		Screen.__init__(self, session, parent = parent)
		self["name"] = StaticText("")
		self["service"] = StaticText("")
		self["time"] = StaticText("")
		self["duration"] = StaticText("")
		self["state"] = StaticText("")
		self.onShow.append(self.addWatcher)
		self.onHide.append(self.removeWatcher)

	def addWatcher(self):
		self.parent.onChangedEntry.append(self.selectionChanged)
		self.parent.updateState()

	def removeWatcher(self):
		self.parent.onChangedEntry.remove(self.selectionChanged)

	def selectionChanged(self, name, time, duration, service, state):
		self["name"].text = name
		self["service"].text = service
		self["time"].text = time
		self["duration"].text = duration
		self["state"].text = state


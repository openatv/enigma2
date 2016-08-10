from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.Label import Label
from Components.config import config
from Components.PowerTimerList import PowerTimerList, gettimerType, getafterEvent
from Components.Sources.StaticText import StaticText
from Components.Sources.ServiceEvent import ServiceEvent
from PowerTimer import PowerTimerEntry, AFTEREVENT
from Screens.Screen import Screen
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.PowerTimerEntry import TimerEntry, TimerLog
from Tools.BoundFunction import boundFunction
from Tools.FuzzyDate import FuzzyTime
from time import time
from timer import TimerEntry as RealTimerEntry

class PowerTimerEditList(Screen):
	EMPTY = 0
	ENABLE = 1
	DISABLE = 2
	CLEANUP = 3
	DELETE = 4

	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = "TimerEditList"
		Screen.setTitle(self, _("PowerTimer List"))

		self.onChangedEntry = [ ]
		list = [ ]
		self.list = list
		self.fillTimerList()

		self["timerlist"] = PowerTimerList(list)

		self.key_red_choice = self.EMPTY
		self.key_yellow_choice = self.EMPTY
		self.key_blue_choice = self.EMPTY

		self["key_red"] = Button(" ")
		self["key_green"] = Button(_("Add"))
		self["key_yellow"] = Button(" ")
		self["key_blue"] = Button(" ")

		self["description"] = Label()
		self["ServiceEvent"] = ServiceEvent()

		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ShortcutActions", "TimerEditActions"],
			{
				"ok": self.openEdit,
				"cancel": self.leave,
				"green": self.addCurrentTimer,
				"log": self.showLog,
				"left": self.left,
				"right": self.right,
				"up": self.up,
				"down": self.down
			}, -1)
		self.setTitle(_("PowerTimer Overview"))
		self.session.nav.PowerTimer.on_state_change.append(self.onStateChange)
		self.onShown.append(self.updateState)

	def createSummary(self):
		return PowerTimerEditListSummary

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

	def toggleDisabledState(self):
		cur=self["timerlist"].getCurrent()
		if cur:
			t = cur
			if t.disabled:
				print "try to ENABLE timer"
				t.enable()
			else:
				if t.isRunning():
					if t.repeated:
						list = (
							(_("Stop current event but not coming events"), "stoponlycurrent"),
							(_("Stop current event and disable coming events"), "stopall"),
							(_("Don't stop current event but disable coming events"), "stoponlycoming")
						)
						self.session.openWithCallback(boundFunction(self.runningEventCallback, t), ChoiceBox, title=_("Repeating event currently recording... What do you want to do?"), list = list)
				else:
					t.disable()
			self.session.nav.PowerTimer.timeChanged(t)
			self.refill()
			self.updateState()

	def runningEventCallback(self, t, result):
		if result is not None:
			if result[1] == "stoponlycurrent" or result[1] == "stopall":
				t.enable()
				t.processRepeated(findRunningEvent = False)
				self.session.nav.PowerTimer.doActivate(t)
			if result[1] == "stoponlycoming" or result[1] == "stopall":
				t.disable()
			self.session.nav.PowerTimer.timeChanged(t)
			self.refill()
			self.updateState()

	def removeAction(self, descr):
		actions = self["actions"].actions
		if descr in actions:
			del actions[descr]

	def updateState(self):
		cur = self["timerlist"].getCurrent()
		if cur:
			if self.key_red_choice != self.DELETE:
				self["actions"].actions.update({"red":self.removeTimerQuestion})
				self["key_red"].setText(_("Delete"))
				self.key_red_choice = self.DELETE

			if cur.disabled and (self.key_yellow_choice != self.ENABLE):
				self["actions"].actions.update({"yellow":self.toggleDisabledState})
				self["key_yellow"].setText(_("Enable"))
				self.key_yellow_choice = self.ENABLE
			elif cur.isRunning() and not cur.repeated and (self.key_yellow_choice != self.EMPTY):
				self.removeAction("yellow")
				self["key_yellow"].setText(" ")
				self.key_yellow_choice = self.EMPTY
			elif ((not cur.isRunning())or cur.repeated ) and (not cur.disabled) and (self.key_yellow_choice != self.DISABLE):
				self["actions"].actions.update({"yellow":self.toggleDisabledState})
				self["key_yellow"].setText(_("Disable"))
				self.key_yellow_choice = self.DISABLE
		else:
			if self.key_red_choice != self.EMPTY:
				self.removeAction("red")
				self["key_red"].setText(" ")
				self.key_red_choice = self.EMPTY
			if self.key_yellow_choice != self.EMPTY:
				self.removeAction("yellow")
				self["key_yellow"].setText(" ")
				self.key_yellow_choice = self.EMPTY

		showCleanup = True
		for x in self.list:
			if (not x[0].disabled) and (x[1] == True):
				break
		else:
			showCleanup = False

		if showCleanup and (self.key_blue_choice != self.CLEANUP):
			self["actions"].actions.update({"blue":self.cleanupQuestion})
			self["key_blue"].setText(_("Cleanup"))
			self.key_blue_choice = self.CLEANUP
		elif (not showCleanup) and (self.key_blue_choice != self.EMPTY):
			self.removeAction("blue")
			self["key_blue"].setText(" ")
			self.key_blue_choice = self.EMPTY
		if len(self.list) == 0:
			return
		timer = self['timerlist'].getCurrent()

		if timer:
			name = gettimerType(timer)
			if getafterEvent(timer) == "Nothing":
				after = ""
			else:
				after = getafterEvent(timer)
			time = "%s %s ... %s" % (FuzzyTime(timer.begin)[0], FuzzyTime(timer.begin)[1], FuzzyTime(timer.end)[1])
			duration = ("(%d " + _("mins") + ")") % ((timer.end - timer.begin) / 60)

			if timer.state == RealTimerEntry.StateWaiting:
				state = _("waiting")
			elif timer.state == RealTimerEntry.StatePrepared:
				state = _("about to start")
			elif timer.state == RealTimerEntry.StateRunning:
				state = _("running...")
			elif timer.state == RealTimerEntry.StateEnded:
				state = _("done!")
			else:
				state = _("<unknown>")
		else:
			name = ""
			after = ""
			time = ""
			duration = ""
			state = ""
		for cb in self.onChangedEntry:
			cb(name, after, time, duration, state)

	def fillTimerList(self):
		#helper function to move finished timers to end of list
		def eol_compare(x, y):
			if x[0].state != y[0].state and x[0].state == RealTimerEntry.StateEnded or y[0].state == RealTimerEntry.StateEnded:
				return cmp(x[0].state, y[0].state)
			return cmp(x[0].begin, y[0].begin)

		list = self.list
		del list[:]
		list.extend([(timer, False) for timer in self.session.nav.PowerTimer.timer_list])
		list.extend([(timer, True) for timer in self.session.nav.PowerTimer.processed_timers])
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
			self.session.nav.PowerTimer.cleanup()
			self.refill()
			self.updateState()

	def removeTimerQuestion(self):
		cur = self["timerlist"].getCurrent()
		if not cur:
			return

		self.session.openWithCallback(self.removeTimer, MessageBox, _("Do you really want to delete this timer ?"), default = False)

	def removeTimer(self, result):
		if not result:
			return
		list = self["timerlist"]
		cur = list.getCurrent()
		if cur:
			timer = cur
			timer.afterEvent = AFTEREVENT.NONE
			self.session.nav.PowerTimer.removeEntry(timer)
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
		data = (int(time() + 60), int(time() + 120))
		self.addTimer(PowerTimerEntry(checkOldTimers = True, *data))

	def addTimer(self, timer):
		self.session.openWithCallback(self.finishedAdd, TimerEntry, timer)

	def finishedEdit(self, answer):
		if answer[0]:
			entry = answer[1]
			self.session.nav.PowerTimer.timeChanged(entry)
			self.fillTimerList()
			self.updateState()
		else:
			print "PowerTimeredit aborted"

	def finishedAdd(self, answer):
		if answer[0]:
			entry = answer[1]
			simulTimerList = self.session.nav.PowerTimer.record(entry)
			self.fillTimerList()
			self.updateState()
		else:
			print "Timeredit aborted"

	def finishSanityCorrection(self, answer):
		self.finishedAdd(answer)

	def leave(self):
		self.session.nav.PowerTimer.on_state_change.remove(self.onStateChange)
		self.close()

	def onStateChange(self, entry):
		self.refill()
		self.updateState()

class PowerTimerEditListSummary(Screen):
	def __init__(self, session, parent):
		Screen.__init__(self, session, parent = parent)
		self["name"] = StaticText("")
		self["after"] = StaticText("")
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

	def selectionChanged(self, name, after, time, duration, state):
		self["name"].text = name
		self["after"].text = after
		self["time"].text = time
		self["duration"].text = duration
		self["state"].text = state


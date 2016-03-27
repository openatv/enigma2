from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.Label import Label
from Components.config import config
from Components.MenuList import MenuList
from Components.TimerList import TimerList
from Components.TimerSanityCheck import TimerSanityCheck
from Components.UsageConfig import preferredTimerPath
from RecordTimer import RecordTimerEntry, parseEvent, AFTEREVENT
from Screen import Screen
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.InputBox import PinInput
from ServiceReference import ServiceReference
from TimerEntry import TimerEntry, TimerLog
from Tools.BoundFunction import boundFunction
from time import time
from timer import TimerEntry as RealTimerEntry

class TimerEditList(Screen):
	EMPTY = 0
	ENABLE = 1
	DISABLE = 2
	CLEANUP = 3
	DELETE = 4

	def __init__(self, session):
		Screen.__init__(self, session)

		list = [ ]
		self.list = list
		self.fillTimerList()

		self["timerlist"] = TimerList(list)

		self.key_red_choice = self.EMPTY
		self.key_yellow_choice = self.EMPTY
		self.key_blue_choice = self.EMPTY

		self["key_red"] = Button(" ")
		self["key_green"] = Button(_("Add"))
		self["key_yellow"] = Button(" ")
		self["key_blue"] = Button(" ")

		self["description"] = Label(" ")

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
		self.setTitle(_("Timer overview"))
		self.session.nav.RecordTimer.on_state_change.append(self.onStateChange)
		self.onShown.append(self.updateState)
		if self.isProtected() and config.ParentalControl.servicepin[0].value:
			self.onFirstExecBegin.append(boundFunction(self.session.openWithCallback, self.pinEntered, PinInput, pinList=[x.value for x in config.ParentalControl.servicepin], triesEntry=config.ParentalControl.retries.servicepin, title=_("Please enter the correct pin code"), windowTitle=_("Enter pin code")))

	def isProtected(self):
		return config.ParentalControl.setuppinactive.value and (not config.ParentalControl.config_sections.main_menu.value or hasattr(self.session, 'infobar') and self.session.infobar is None) and config.ParentalControl.config_sections.timer_menu.value

	def pinEntered(self, result):
		if result is None:
			self.closeProtectedScreen()
		elif not result:
			self.session.openWithCallback(self.close(), MessageBox, _("The pin code you entered is wrong."), MessageBox.TYPE_ERROR, timeout=3)

	def closeProtectedScreen(self, result=None):
		self.close(None)

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
		timer_changed = True
		if cur:
			t = cur
			if t.disabled and t.repeated and t.isRunning() and not t.justplay:
				return
			if t.disabled:
				print "[TimerEditList] try to ENABLE timer"
				t.enable()
				timersanitycheck = TimerSanityCheck(self.session.nav.RecordTimer.timer_list, cur)
				if not timersanitycheck.check():
					t.disable()
					print "[TimerEditList] sanity check failed"
					simulTimerList = timersanitycheck.getSimulTimerList()
					if simulTimerList is not None:
						self.session.openWithCallback(self.finishedEdit, TimerSanityConflict, simulTimerList)
						timer_changed = False
				else:
					print "[TimerEditList] sanity check passed"
					if timersanitycheck.doubleCheck():
						t.disable()
			else:
				if t.isRunning():
					if t.repeated:
						list = (
							(_("Stop current event but not coming events"), "stoponlycurrent"),
							(_("Stop current event and disable coming events"), "stopall"),
							(_("Don't stop current event but disable coming events"), "stoponlycoming")
						)
						self.session.openWithCallback(boundFunction(self.runningEventCallback, t), ChoiceBox, title=_("Repeating event currently recording... What do you want to do?"), list = list)
						timer_changed = False
				else:
					t.disable()
			if timer_changed:
				self.session.nav.RecordTimer.timeChanged(t)
			self.refill()
			self.updateState()

	def runningEventCallback(self, t, result):
		if result is not None and t.isRunning():
			findNextRunningEvent = True
			if result[1] == "stoponlycurrent" or result[1] == "stopall":
				findNextRunningEvent = False
				t.enable()
				t.processRepeated(findRunningEvent = False)
				self.session.nav.RecordTimer.doActivate(t)
			if result[1] == "stoponlycoming" or result[1] == "stopall":
				findNextRunningEvent = True
				t.disable()
			self.session.nav.RecordTimer.timeChanged(t)
			t.findRunningEvent = findNextRunningEvent
			self.refill()
			self.updateState()

	def removeAction(self, descr):
		actions = self["actions"].actions
		if descr in actions:
			del actions[descr]

	def updateState(self):
		cur = self["timerlist"].getCurrent()
		if cur:
			text = cur.description
			if not cur.conflict_detection:
				text += _("\nConflict detection disabled!")
			self["description"].setText(text)
			if self.key_red_choice != self.DELETE:
				self["actions"].actions.update({"red":self.removeTimerQuestion})
				self["key_red"].setText(_("Delete"))
				self.key_red_choice = self.DELETE

			if cur.disabled and (self.key_yellow_choice != self.ENABLE):
				if cur.isRunning() and cur.repeated and not cur.justplay:
					self.removeAction("yellow")
					self["key_yellow"].setText(" ")
					self.key_yellow_choice = self.EMPTY
				else:
					self["actions"].actions.update({"yellow":self.toggleDisabledState})
					self["key_yellow"].setText(_("Enable"))
					self.key_yellow_choice = self.ENABLE
			elif cur.isRunning() and not cur.repeated and (self.key_yellow_choice != self.EMPTY):
				self.removeAction("yellow")
				self["key_yellow"].setText(" ")
				self.key_yellow_choice = self.EMPTY
			elif (not cur.isRunning() or cur.repeated) and not cur.disabled and (self.key_yellow_choice != self.DISABLE):
				self["actions"].actions.update({"yellow":self.toggleDisabledState})
				self["key_yellow"].setText(_("Disable"))
				self.key_yellow_choice = self.DISABLE
		else:
			self["description"].setText(" ")
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

	def fillTimerList(self):
		#helper function to move finished timers to end of list
		def eol_compare(x, y):
			if x[0].state != y[0].state and x[0].state == RealTimerEntry.StateEnded or y[0].state == RealTimerEntry.StateEnded:
				return cmp(x[0].state, y[0].state)
			return cmp(x[0].begin, y[0].begin)

		list = self.list
		del list[:]
		list.extend([(timer, False) for timer in self.session.nav.RecordTimer.timer_list])
		list.extend([(timer, True) for timer in self.session.nav.RecordTimer.processed_timers])
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

		self.session.openWithCallback(self.removeTimer, MessageBox, _("Do you really want to delete %s?") % (cur.name))

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
		print "[TimerEditList] finished edit"

		if answer[0]:
			print "[TimerEditList] edited timer"
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
				print "[TimerEditList] sanity check passed"
				self.session.nav.RecordTimer.timeChanged(entry)

			self.fillTimerList()
			self.updateState()
		else:
			print "[TimerEditList] timer edit aborted"

	def finishedAdd(self, answer):
		print "[TimerEditList] finished add"
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
		else:
			print "[TimerEditList] timer edit aborted"

	def finishSanityCorrection(self, answer):
		self.finishedAdd(answer)

	def leave(self):
		self.session.nav.RecordTimer.on_state_change.remove(self.onStateChange)
		self.close()

	def onStateChange(self, entry):
		self.refill()
		self.updateState()

class TimerSanityConflict(Screen):
	def __init__(self, session, timer):
		Screen.__init__(self, session)
		self.skinName = "TimerEditList"
		self.timer = timer

		self.list = []
		count = 0
		for x in timer:
			self.list.append((timer[count], False))
			count += 1
		if count == 1:
			self.setTitle((_("Channel not in services list")))
		else:
			self.setTitle(_("Timer sanity error"))

		self["timerlist"] = TimerList(self.list)

		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(" ")
		self["key_yellow"] = Button(" ")
		self["key_blue"] = Button(" ")

		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ShortcutActions", "TimerEditActions", "MenuActions"],
			{
				"cancel": self.leave_cancel,
				"red": self.leave_cancel,
				"green": self.editTimer,
				"ok": self.editTimer,
				"yellow": self.toggleTimer,
				"blue": self.ignoreConflict,
				"up": self.up,
				"down": self.down,
				"log": self.showLog,
				"menu": self.openExtendedSetup
			}, -1)
		self.onShown.append(self.updateState)

	def getTimerList(self, timer):
		return [(timer, False)]

	def editTimer(self):
		self.session.openWithCallback(self.editTimerCallBack, TimerEntry, self["timerlist"].getCurrent())

	def showLog(self):
		selected_timer = self["timerlist"].getCurrent()
		if selected_timer:
			self.session.openWithCallback(self.editTimerCallBack, TimerLog, selected_timer)

	def editTimerCallBack(self, answer=None):
		if answer and len(answer) > 1 and answer[0] is True:
			self.session.nav.RecordTimer.timeChanged(answer[1])
			if not answer[1].disabled:
				if not self.isResolvedConflict(answer[1]):
					self.session.open(MessageBox, _("Conflict not resolved!"), MessageBox.TYPE_INFO, timeout=3)
					return
			self.leave_ok()

	def toggleTimer(self):
		selected_timer = self["timerlist"].getCurrent()
		if selected_timer and self["key_yellow"].getText() != " " and not selected_timer.isRunning():
			selected_timer.disabled = not selected_timer.disabled
			if not selected_timer.disabled:
				if not self.isResolvedConflict(selected_timer):
					timer_text = _("\nTimer '%s' disabled!") % selected_timer.name
					selected_timer.disabled = True
					self.session.open(MessageBox, _("Conflict not resolved!") + timer_text, MessageBox.TYPE_INFO, timeout=3)
					return
			self.session.nav.RecordTimer.timeChanged(selected_timer)
			self.leave_ok()

	def ignoreConflict(self):
			selected_timer = self["timerlist"].getCurrent()
			if selected_timer and selected_timer.conflict_detection:
				if config.usage.show_timer_conflict_warning.value:
					list = [(_("yes"), True), (_("no"), False), (_("yes") + " " + _("and never ask this again"), "never")]
					self.session.openWithCallback(self.ignoreConflictConfirm, MessageBox, _("Warning!\nThis is an option for advanced users.\nReally disable timer conflict detection?"), list=list)
				else:
					self.ignoreConflictConfirm(True)

	def ignoreConflictConfirm(self, answer):
		selected_timer = self["timerlist"].getCurrent()
		if answer and selected_timer and selected_timer.conflict_detection:
			if answer == "never":
				config.usage.show_timer_conflict_warning.value = False
				config.usage.show_timer_conflict_warning.save()
			selected_timer.conflict_detection = False
			selected_timer.disabled = False
			self.session.nav.RecordTimer.timeChanged(selected_timer)
			self.leave_ok()

	def leave_ok(self):
		if self.isResolvedConflict():
			self.close((True, self.timer[0]))
		else:
			timer_text = ""
			selected_timer = self["timerlist"].getCurrent()
			if selected_timer and selected_timer == self.timer[0]:
				if not self.timer[0].isRunning() and not self.timer[0].disabled:
					self.timer[0].disabled = True
					self.session.nav.RecordTimer.timeChanged(self.timer[0])
					timer_text = _("\nTimer '%s' disabled!") % self.timer[0].name
			self.updateState()
			self.session.open(MessageBox, _("Conflict not resolved!") + timer_text, MessageBox.TYPE_ERROR, timeout=3)

	def leave_cancel(self):
		isTimerSave = self.timer[0] in self.session.nav.RecordTimer.timer_list
		if self.isResolvedConflict() or not isTimerSave:
			self.close((False, self.timer[0]))
		else:
			timer_text = ""
			if not self.timer[0].isRunning() and not self.timer[0].disabled:
				self.timer[0].disabled = True
				self.session.nav.RecordTimer.timeChanged(self.timer[0])
				timer_text = _("\nTimer '%s' disabled!") % self.timer[0].name
			self.session.openWithCallback(self.canceling, MessageBox, _("Conflict not resolved!") + timer_text, MessageBox.TYPE_INFO, timeout=3)

	def canceling(self, answer=None):
		self.close((False, self.timer[0]))

	def isResolvedConflict(self, checktimer=None):
		timer = checktimer or self.timer[0]
		timersanitycheck = TimerSanityCheck(self.session.nav.RecordTimer.timer_list, timer)
		success = False
		if not timersanitycheck.check():
			simulTimerList = timersanitycheck.getSimulTimerList()
			if simulTimerList is not None:
				for x in simulTimerList:
					if x.setAutoincreaseEnd(timer):
						self.session.nav.RecordTimer.timeChanged(x)
				if timersanitycheck.check():
					success = True
		else:
			success = True
		return success

	def openExtendedSetup(self):
		menu = []
		if not config.usage.show_timer_conflict_warning.value:
			menu.append((_("Show warning before set 'Ignore conflict'"), "blue_key_warning"))
		def showAction(choice):
			if choice is not None:
				if choice[1] == "blue_key_warning":
					config.usage.show_timer_conflict_warning.value = True
					config.usage.show_timer_conflict_warning.save()
		if menu:
			self.session.openWithCallback(showAction, ChoiceBox, title= _("Select action"), list=menu)

	def up(self):
		self["timerlist"].instance.moveSelection(self["timerlist"].instance.moveUp)
		self.updateState()

	def down(self):
		self["timerlist"].instance.moveSelection(self["timerlist"].instance.moveDown)
		self.updateState()

	def updateState(self):
		selected_timer = self["timerlist"].getCurrent()
		if selected_timer:
			self["key_green"].setText(_("Edit"))
			if selected_timer.disabled:
				self["key_yellow"].setText(_("Enable"))
			elif selected_timer.isRunning() and not selected_timer.repeated:
				self["key_yellow"].setText(" ")
			elif not selected_timer.isRunning() or selected_timer.repeated:
				self["key_yellow"].setText(_("Disable"))
			if selected_timer.conflict_detection:
				self["key_blue"].setText(_("Ignore conflict"))
			else:
				self["key_blue"].setText(" ")
		else:
			self["key_green"].setText(" ")
			self["key_yellow"].setText(" ")
			self["key_blue"].setText(" ")

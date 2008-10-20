from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.config import config
from Components.MenuList import MenuList
from Components.TimerList import TimerList
from Components.TimerSanityCheck import TimerSanityCheck
from RecordTimer import RecordTimerEntry, parseEvent, AFTEREVENT
from Screen import Screen
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from ServiceReference import ServiceReference
from TimerEntry import TimerEntry, TimerLog
from Tools.BoundFunction import boundFunction
from time import time

class TimerEditList(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		
		list = [ ]
		self.list = list
		self.fillTimerList()

		self["timerlist"] = TimerList(list)
		
		self["key_red"] = Button(_("Delete"))
		self["key_green"] = Button(_("Add"))
		self["key_yellow"] = Button("")
		self["key_blue"] = Button(_("Cleanup"))

		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ShortcutActions", "TimerEditActions"], 
			{
				"ok": self.openEdit,
				"cancel": self.leave,
				"red": self.removeTimerQuestion,
				"green": self.addCurrentTimer,
				"blue": self.cleanupQuestion,
				"yellow": self.toggleDisabledState,
				"log": self.showLog,
				"left": self.left,
				"right": self.right,
				"up": self.up,
				"down": self.down
			}, -1)
		self.session.nav.RecordTimer.on_state_change.append(self.onStateChange)
		self.onShown.append(self.updateState)

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
				print "try to enable timer"
				t.enable()
				timersanitycheck = TimerSanityCheck(self.session.nav.RecordTimer.timer_list, cur)
				if not timersanitycheck.check():
					t.disable()
					print "Sanity check failed"
					self.session.openWithCallback(self.finishedEdit, TimerSanityConflict, timersanitycheck.getSimulTimerList())
				else:
					print "Sanity check passed"
					if timersanitycheck.doubleCheck():
						t.disable()
			else:
				if t.isRunning():
					if t.repeated:
						list = []
						list.append((_("Stop current event but not coming events"), "stoponlycurrent"))
						list.append((_("Stop current event and disable coming events"), "stopall"))
						list.append((_("Don't stop current event but disable coming events"), "stoponlycoming"))
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
			if result[1] == "stoponlycoming" or result[1] == "stopall":
				t.disable()
			self.session.nav.RecordTimer.timeChanged(t)
			self.refill()
			self.updateState()
		
	def updateState(self):
		cur = self["timerlist"].getCurrent()
		if cur:
			if self["key_red"].getText()!=(_("Delete")):
				self["actions"].actions.update({"red":self.removeTimerQuestion})
				self["key_red"].setText(_("Delete"))
				self["key_red"].instance.invalidate()
			
			if cur.disabled and (self["key_yellow"].getText()!=(_("Enable"))):
				self["actions"].actions.update({"yellow":self.toggleDisabledState})
				self["key_yellow"].setText(_("Enable"))
				self["key_yellow"].instance.invalidate()
			elif cur.isRunning() and (self["key_yellow"].getText()!=(_(" "))):
				del self["actions"].actions["yellow"]
				self["key_yellow"].setText(_(" "))
				self["key_yellow"].instance.invalidate()
			elif (not cur.isRunning()) and (not cur.disabled) and (self["key_yellow"].getText()!=(_("Disable"))):
				self["actions"].actions.update({"yellow":self.toggleDisabledState})
				self["key_yellow"].setText(_("Disable"))
				self["key_yellow"].instance.invalidate()
		else:
			if self["key_red"].getText()!=(_(" ")):
				del self["actions"].actions["red"]
				self["key_red"].setText(_(" "))
				self["key_red"].instance.invalidate()
			if self["key_yellow"].getText()!=(_(" ")):
				del self["actions"].actions["yellow"]
				self["key_yellow"].setText(_(" "))
				self["key_yellow"].instance.invalidate()
		
		showCleanup = True
		for x in self.list:
			if (not x[0].disabled) and (x[1] == True):
				break
		else:
			showCleanup = False
		
		if showCleanup and (self["key_blue"].getText()!=(_("Cleanup"))):
			self["actions"].actions.update({"blue":self.cleanupQuestion})
			self["key_blue"].setText(_("Cleanup"))
			self["key_blue"].instance.invalidate()
		elif (not showCleanup) and (self["key_blue"].getText()!=(_(" "))):
			del self["actions"].actions["blue"]
			self["key_blue"].setText(_(" "))
			self["key_blue"].instance.invalidate()


	def fillTimerList(self):
		del self.list[:]
		
		for timer in self.session.nav.RecordTimer.timer_list:
			self.list.append((timer, False))
		
		for timer in self.session.nav.RecordTimer.processed_timers:
			self.list.append((timer, True))
		self.list.sort(cmp = lambda x, y: x[0].begin < y[0].begin)

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
		if not self["timerlist"].getCurrent():
			return
		self.session.openWithCallback(self.removeTimer, MessageBox, _("Really delete this timer?"))

	def removeTimer(self, result):
		if not result:
			return
		list = self["timerlist"]
		cur = list.getCurrent()
		if cur:
			timer = cur
			timer.afterEvent = AFTEREVENT.NONE
			self.session.nav.RecordTimer.removeEntry(timer)
			if not timer.dontSave:
				for timer in self.session.nav.RecordTimer.timer_list:
					if timer.dontSave and timer.autoincrease:
						timer.end = timer.begin + (3600 * 24 * 356 * 1)
						self.session.nav.RecordTimer.timeChanged(timer)
						timersanitycheck = TimerSanityCheck(self.session.nav.RecordTimer.timer_list,timer)
						if not timersanitycheck.check():
							tsc_list = timersanitycheck.getSimulTimerList()
							if len(tsc_list) > 1:
								timer.end = tsc_list[1].begin - 30
								self.session.nav.RecordTimer.timeChanged(timer)

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
		serviceref = ServiceReference(self.session.nav.getCurrentlyPlayingServiceReference())
		
		if event is None:	
			data = (int(time()), int(time() + 60), "", "", None)
		else:
			data = parseEvent(event, description = False)

		self.addTimer(RecordTimerEntry(serviceref, checkOldTimers = True, dirname = config.movielist.last_timer_videodir.value, *data))
		
	def addTimer(self, timer):
		self.session.openWithCallback(self.finishedAdd, TimerEntry, timer)
		
	def finishedEdit(self, answer):
		print "finished edit"
		
		if answer[0]:
			print "Edited timer"
			entry = answer[1]
			timersanitycheck = TimerSanityCheck(self.session.nav.RecordTimer.timer_list, entry)
			if not timersanitycheck.check():
				simulTimerList = timersanitycheck.getSimulTimerList()
				if (len(simulTimerList) == 2) and (simulTimerList[1].dontSave) and (simulTimerList[1].autoincrease):
					simulTimerList[1].end = entry.begin - 30
					self.session.nav.RecordTimer.timeChanged(simulTimerList[1])
					self.session.nav.RecordTimer.timeChanged(entry)
				else:
					print "Sanity check failed"
					self.session.openWithCallback(self.finishedEdit, TimerSanityConflict, timersanitycheck.getSimulTimerList())
			else:
				print "Sanity check passed"
				if not timersanitycheck.doubleCheck():
					self.session.nav.RecordTimer.timeChanged(entry)
			self.fillTimerList()
			self.updateState()
		else:
			print "Timeredit aborted"

	def finishedAdd(self, answer):
		print "finished add"
		if answer[0]:
			entry = answer[1]
			simulTimerList = self.session.nav.RecordTimer.record(entry)
			if simulTimerList is not None:
				if (len(simulTimerList) == 2) and (simulTimerList[1].dontSave) and (simulTimerList[1].autoincrease):
					simulTimerList[1].end = entry.begin - 30
					self.session.nav.RecordTimer.timeChanged(simulTimerList[1])
					self.session.nav.RecordTimer.record(entry)
				else:
					self.session.openWithCallback(self.finishSanityCorrection, TimerSanityConflict, simulTimerList)
			self.fillTimerList()
			self.updateState()
		else:
			print "Timeredit aborted"

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
		self.timer = timer
		print "TimerSanityConflict"
			
		self["timer1"] = TimerList(self.getTimerList(timer[0]))
		self.list = []
		self.list2 = []
		count = 0
		for x in timer:
			if count != 0:
				self.list.append((_("Conflicting timer") + " " + str(count), x))
				self.list2.append((timer[count], False))
			count += 1

		self["list"] = MenuList(self.list)
		self["timer2"] = TimerList(self.list2)

		self["key_red"] = Button("Edit")
		self["key_green"] = Button("")
		self["key_yellow"] = Button("Edit")
		self["key_blue"] = Button("")

		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ShortcutActions", "TimerEditActions"], 
			{
				"ok": self.leave_ok,
				"cancel": self.leave_cancel,
				"red": self.editTimer1,
				"green": self.toggleTimer1,
				"yellow": self.editTimer2,
				"blue": self.toggleTimer2,
				#"log": self.showLog,
				#"left": self.left,
				#"right": self.right,
				"up": self.up,
				"down": self.down
			}, -1)
		self.onShown.append(self.updateState)

	def getTimerList(self, timer):
		return [(timer, False)]

	def editTimer1(self):
		self.session.openWithCallback(self.finishedEdit, TimerEntry, self["timer1"].getCurrent())

	def toggleTimer1(self):
		if self.timer[0].disabled:
			self.timer[0].disabled = False
		else:
			if not self.timer[0].isRunning():
				self.timer[0].disabled = True
		self.finishedEdit((True, self.timer[0]))
	
	def editTimer2(self):
		self.session.openWithCallback(self.finishedEdit, TimerEntry, self["timer2"].getCurrent())

	def toggleTimer2(self):
		x = self["list"].getSelectedIndex() + 1 # the first is the new timer so we do +1 here
		if self.timer[x].disabled:
			self.timer[x].disabled = False
		elif not self.timer[x].isRunning():
				self.timer[x].disabled = True
		self.finishedEdit((True, self.timer[0]))
	
	def finishedEdit(self, answer):
		self.leave_ok()
	
	def leave_ok(self):
		self.close((True, self.timer[0]))
	
	def leave_cancel(self):
		self.close((False, self.timer[0]))

	def up(self):
		self["list"].instance.moveSelection(self["list"].instance.moveUp)
		self["timer2"].moveToIndex(self["list"].getSelectedIndex())
		
	def down(self):
		self["list"].instance.moveSelection(self["list"].instance.moveDown)
		self["timer2"].moveToIndex(self["list"].getSelectedIndex())
	
	def updateState(self):
		if self.timer[0] is not None:
			green_text = self["key_green"].getText()
			print "green_text '%s'" %(green_text)
			if self.timer[0].disabled and green_text != _("Enable"):
				self["actions"].actions.update({"green":self.toggleTimer1})
				self["key_green"].setText(_("Enable"))
				self["key_green"].instance.invalidate()
			elif self.timer[0].isRunning() and green_text != "":
				del self["actions"].actions["green"]
				self["key_green"].setText("")
				self["key_green"].instance.invalidate()
			elif not self.timer[0].disabled and green_text != _("Disable"):
				self["actions"].actions.update({"green":self.toggleTimer1})
				self["key_green"].setText(_("Disable"))
				self["key_green"].instance.invalidate()
		if len(self.timer) > 1:
			x = self["list"].getSelectedIndex()
			print "x: ",x
			print "timer[x]: ", self.timer[x]
			if self.timer[x] is not None:
				blue_text = self["key_blue"].getText()
				print "blue_text '%s'" %(blue_text)
				if self.timer[x].disabled and blue_text != _("Enable"):
					self["actions"].actions.update({"blue":self.toggleTimer2})
					self["key_blue"].setText(_("Enable"))
					self["key_blue"].instance.invalidate()
				elif self.timer[x].isRunning() and blue_text != "":
					del self["actions"].actions["blue"]
					self["key_blue"].setText("")
					self["key_blue"].instance.invalidate()
				elif not self.timer[x].disabled and blue_text != _("Disable"):
					self["actions"].actions.update({"blue":self.toggleTimer2})
					self["key_blue"].setText(_("Disable"))
					self["key_blue"].instance.invalidate()
		else:
#FIXME.... this doesnt hide the buttons self.... just the text
			del self["actions"].actions["yellow"]
			self["key_yellow"].setText("")
			self["key_yellow"].instance.invalidate()
			del self["actions"].actions["blue"]
			self["key_blue"].setText("")
			self["key_blue"].instance.invalidate()

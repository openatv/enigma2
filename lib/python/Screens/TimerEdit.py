from Screen import Screen
from Components.TimerList import TimerList, TimerEntryComponent
from Components.MenuList import MenuList
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Button import Button
from Screens.MessageBox import MessageBox
from TimerEntry import TimerEntry, TimerLog
from RecordTimer import RecordTimerEntry, parseEvent, AFTEREVENT
from time import *
from ServiceReference import ServiceReference
from Components.TimerSanityCheck import TimerSanityCheck

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
			t = cur[0]
		
			if t.disabled:
				t.enable()
			else:
				t.disable()

			self.session.nav.RecordTimer.timeChanged(t)
			self.updateState()
			self.refill()
		
	def updateState(self):
		if len(self.list) > 0:
			if self["timerlist"].getCurrent()[0].disabled:
				self["key_yellow"].setText(_("Enable"))
			else:
				self["key_yellow"].setText(_("Disable"))
			self["key_yellow"].instance.invalidate()

	def fillTimerList(self):
		del self.list[:]
		
		for timer in self.session.nav.RecordTimer.timer_list:
			self.list.append(TimerEntryComponent(timer, processed=False))
		
		for timer in self.session.nav.RecordTimer.processed_timers:
			self.list.append(TimerEntryComponent(timer, processed=True))
		self.list.sort(cmp = lambda x, y: x[0].begin < y[0].begin)

	def showLog(self):
		cur=self["timerlist"].getCurrent()
		if cur:
			self.session.openWithCallback(self.finishedEdit, TimerLog, cur[0])

	def openEdit(self):
		cur=self["timerlist"].getCurrent()
		if cur:
			self.session.openWithCallback(self.finishedEdit, TimerEntry, cur[0])

	def cleanupQuestion(self):
		self.session.openWithCallback(self.cleanupTimer, MessageBox, _("Really delete done timers?"))
	
	def cleanupTimer(self, delete):
		if delete:
			self.session.nav.RecordTimer.cleanup()
			self.refill()
	
	def removeTimerQuestion(self):
		self.session.openWithCallback(self.removeTimer, MessageBox, _("Really delete this timer?"))
		
	def removeTimer(self, result):
		if not result:
			return
		list = self["timerlist"]
		cur = list.getCurrent()
		if cur:
			timer = cur[0]
			timer.afterEvent = AFTEREVENT.NONE
			self.session.nav.RecordTimer.removeEntry(timer)
			self.refill()
	
	def refill(self):
		self.fillTimerList()
		self["timerlist"].invalidate()
	
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

		self.addTimer(RecordTimerEntry(serviceref, checkOldTimers = True, *data))
		
	def addTimer(self, timer):
		self.session.openWithCallback(self.finishedAdd, TimerEntry, timer)
		
	def finishedEdit(self, answer):
		print "finished edit"
		
		if answer[0]:
			print "Edited timer"
			timersanitycheck = TimerSanityCheck(self.session.nav.RecordTimer.timer_list, answer[1])
			if not timersanitycheck.check():
				print "Sanity check failed"
			else:
				print "Sanity check passed"
			self.session.nav.RecordTimer.timeChanged(answer[1])
			self.fillTimerList()
		else:
			print "Timeredit aborted"

	def finishedAdd(self, answer):
		print "finished add"
		if answer[0]:
			timersanitycheck = TimerSanityCheck(self.session.nav.RecordTimer.timer_list, answer[1])
			if not timersanitycheck.check():
				print "Sanity check failed"
				self.session.openWithCallback(self.finishSanityCorrection, TimerSanityConflict, timersanitycheck.getSimulTimerList())
			else:
				print "Sanity check passed"
				entry = answer[1]
				self.session.nav.RecordTimer.record(entry)
				self.fillTimerList()
		else:
			print "Timeredit aborted"		

	def finishSanityCorrection(self, answer):
		self.finishedAdd(answer)

	def leave(self):
		self.session.nav.RecordTimer.saveTimer()
		self.session.nav.RecordTimer.on_state_change.remove(self.onStateChange)
		self.close()

	def onStateChange(self, entry):
		self.refill()
		
class TimerSanityConflict(Screen):
	def __init__(self, session, timer):
		Screen.__init__(self, session)
		self.timer = timer
		print "TimerSanityConflict", timer
			
		self["timer1"] = TimerList(self.getTimerList(timer[0]))
		if len(timer) > 1:
			self["timer2"] = TimerList(self.getTimerList(timer[1]))
		else:
			self["timer2"] = TimerList([])
		
		self.list = []
		count = 0
		for x in timer:
			if count != 0:
				self.list.append((_("Conflicting timer") + " " + str(count), x))
			count += 1

		self["list"] = MenuList(self.list)
		
		self["key_red"] = Button("Edit")
		self["key_green"] = Button("Disable")
		self["key_yellow"] = Button("Edit")
		self["key_blue"] = Button("Disable")

		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ShortcutActions", "TimerEditActions"], 
			{
				"ok": self.close,
				#"cancel": self.leave,
				"red": self.editTimer1,
				"green": self.disableTimer1,
#				"yellow": self.editTimer2,
#				"blue": self.disableTimer2,
				#"log": self.showLog,
				#"left": self.left,
				#"right": self.right,
				"up": self.up,
				"down": self.down
			}, -1)

	def getTimerList(self, timer):
		return [TimerEntryComponent(timer, processed=False)]

	def editTimer1(self):
		self.session.openWithCallback(self.finishedEdit, TimerEntry, self["timer1"].getCurrent()[0])

	def disableTimer1(self):
		self.timer[0].disabled = True
		self.finishedEdit((True, self.timer[0]))

	def finishedEdit(self, answer):
		self.close((True, self.timer[0]))

	def up(self):
		self["list"].instance.moveSelection(self["list"].instance.moveUp)
		self["timer2"].l.setList(self.getTimerList(self["list"].getCurrent()[1]))
		
	def down(self):
		self["list"].instance.moveSelection(self["list"].instance.moveDown)
		self["timer2"].l.setList(self.getTimerList(self["list"].getCurrent()[1]))
			
		
from functools import cmp_to_key
from os import listdir, system
from os.path import exists, join as pathjoin, normpath, realpath
from time import localtime, time

from enigma import eEPGCache

from RecordTimer import AFTEREVENT, RecordTimerEntry, parseEvent
from ServiceReference import ServiceReference
from timer import TimerEntry as RealTimerEntry
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.config import config
from Components.MenuList import MenuList
from Components.TimerList import TimerList
from Components.TimerSanityCheck import TimerSanityCheck
from Components.UsageConfig import preferredTimerPath
from Components.Sources.Event import Event
from Components.Sources.ServiceEvent import ServiceEvent
from Components.Sources.StaticText import StaticText
from Screens.ChoiceBox import ChoiceBox
from Screens.EventView import EventViewSimple
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.TimerEntry import TimerEntry, TimerLog
from Tools.BoundFunction import boundFunction
from Tools.CopyFiles import moveFiles
from Tools.Directories import SCOPE_HDD, isPluginInstalled, resolveFilename
from Tools.FuzzyDate import FuzzyTime


class TimerEditList(Screen):
	EMPTY = 0
	ENABLE = 1
	DISABLE = 2
	CLEANUP = 3
	DELETE = 4
	STOP = 5

	def __init__(self, session):
		Screen.__init__(self, session)
		self.onChangedEntry = []
		self.list = []
		self.fillTimerList()
		self["timerlist"] = TimerList(self.list)
		self.key_red_choice = self.EMPTY
		self.key_yellow_choice = self.EMPTY
		self.key_blue_choice = self.EMPTY
		self["key_red"] = StaticText("")
		self["key_green"] = StaticText(_("Add"))
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText("")
		self["description"] = Label()
		self["ServiceEvent"] = ServiceEvent()
		self["Event"] = Event()
		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ShortcutActions", "TimerEditActions"], {
			"ok": self.openEdit,
			"cancel": self.leave,
			"green": self.addCurrentTimer,
			"log": self.showLog,
			# "top": self.moveTop,
			"left": self.pageUp,
			"up": self.moveUp,
			"down": self.moveDown,
			"right": self.pageDown,
			# "bottom": self.moveBottom
		}, prio=-1)
		self.setTitle(_("Timer Overview"))
		# Disabled because it crashes on some boxes with SSD ######################
		# self.session.nav.RecordTimer.on_state_change.append(self.onStateChange)
		# #########################################################################
		self.onShown.append(self.updateState)

	def createSummary(self):
		return TimerEditListSummary

	def moveTop(self):
		self["timerlist"].instance.moveSelection(self["timerlist"].instance.moveTop)
		self.updateState()

	def pageUp(self):
		self["timerlist"].instance.moveSelection(self["timerlist"].instance.pageUp)
		self.updateState()

	def moveUp(self):
		self["timerlist"].instance.moveSelection(self["timerlist"].instance.moveUp)
		self.updateState()

	def moveDown(self):
		self["timerlist"].instance.moveSelection(self["timerlist"].instance.moveDown)
		self.updateState()

	def pageDown(self):
		self["timerlist"].instance.moveSelection(self["timerlist"].instance.pageDown)
		self.updateState()

	def moveBottom(self):
		self["timerlist"].instance.moveSelection(self["timerlist"].instance.moveEnd)
		self.updateState()

	def toggleDisabledState(self):
		cur = self["timerlist"].getCurrent()
		if cur:
			t = cur
			if t.disabled:
				# print("[TimerEdit] Try to ENABLE the timer.")
				t.enable()
				timersanitycheck = TimerSanityCheck(self.session.nav.RecordTimer.timer_list, cur)
				if not timersanitycheck.check():
					t.disable()
					print("[TimerEdit] Sanity check failed!")
					simulTimerList = timersanitycheck.getSimulTimerList()
					if simulTimerList is not None:
						self.session.openWithCallback(self.finishedEdit, TimerSanityConflict, simulTimerList)
				else:
					print("[TimerEdit] Sanity check passed.")
					if timersanitycheck.doubleCheck():
						t.disable()
			else:
				if t.isRunning():
					if t.repeated:
						list = (
							(_("Stop current event but not future events"), "stoponlycurrent"),
							(_("Stop current event and disable future events"), "stopall"),
							(_("Don't stop current event but disable future events"), "stoponlycoming")
						)
						self.session.openWithCallback(boundFunction(self.runningEventCallback, t), ChoiceBox, title=_("Repeating event currently recording. What do you want to do?"), list=list)
				else:
					t.disable()
			self.session.nav.RecordTimer.timeChanged(t)
			self.refill()
			self.updateState()

	def runningEventCallback(self, t, result):
		if result is not None:
			if result[1] == "stoponlycurrent" or result[1] == "stopall":
				t.enable()
				t.processRepeated(findRunningEvent=False)
				self.session.nav.RecordTimer.doActivate(t)
			if result[1] == "stoponlycoming" or result[1] == "stopall":
				t.disable()
			self.session.nav.RecordTimer.timeChanged(t)
			self.refill()
			self.updateState()

	def removeAction(self, descr):
		actions = self["actions"].actions
		if descr in actions:
			del actions[descr]

	def updateState(self):
		cur = self["timerlist"].getCurrent()
		if cur:
			self["description"].setText(cur.description)
			if self.key_red_choice != self.DELETE:
				self["actions"].actions.update({"red": self.removeTimerQuestion})
				self["key_red"].setText(_("Delete"))
				self.key_red_choice = self.DELETE
			if cur.disabled and (self.key_yellow_choice != self.ENABLE):
				self["actions"].actions.update({"yellow": self.toggleDisabledState})
				self["key_yellow"].setText(_("Enable"))
				self.key_yellow_choice = self.ENABLE
			elif cur.isRunning() and not cur.repeated and (self.key_yellow_choice != self.STOP):
				self["actions"].actions.update({"yellow": self.removeTimerQuestion})
				self["key_yellow"].setText(_("Stop"))
				self.key_yellow_choice = self.STOP
			elif ((not cur.isRunning()) or cur.repeated) and (not cur.disabled) and (self.key_yellow_choice != self.DISABLE):
				self["actions"].actions.update({"yellow": self.toggleDisabledState})
				self["key_yellow"].setText(_("Disable"))
				self.key_yellow_choice = self.DISABLE
		else:
			self["description"].setText(" ")
			if self.key_red_choice != self.EMPTY:
				self.removeAction("red")
				self["key_red"].setText("")
				self.key_red_choice = self.EMPTY
			if self.key_yellow_choice != self.EMPTY:
				self.removeAction("yellow")
				self["key_yellow"].setText("")
				self.key_yellow_choice = self.EMPTY
		showCleanup = True
		for x in self.list:
			if (not x[0].disabled) and (x[1] == True):
				break
		else:
			showCleanup = False
		if showCleanup and (self.key_blue_choice != self.CLEANUP):
			self["actions"].actions.update({"blue": self.cleanupQuestion})
			self["key_blue"].setText(_("Cleanup"))
			self.key_blue_choice = self.CLEANUP
		elif (not showCleanup) and (self.key_blue_choice != self.EMPTY):
			self.removeAction("blue")
			self["key_blue"].setText("")
			self.key_blue_choice = self.EMPTY
		if len(self.list) == 0:
			return
		timer = self['timerlist'].getCurrent()
		if timer:
			try:
				name = str(timer.name)
				time = "%s %s ... %s" % (FuzzyTime(timer.begin)[0], FuzzyTime(timer.begin)[1], FuzzyTime(timer.end)[1])
				duration = ("(%d " + _("mins") + ")") % ((timer.end - timer.begin) / 60)  # FIXME: This should handle singular/plural durations!
				service = str(timer.service_ref.getServiceName())
				if timer.state == RealTimerEntry.StateWaiting:
					state = _("Waiting")
				elif timer.state == RealTimerEntry.StatePrepared:
					state = _("About to start")
				elif timer.state == RealTimerEntry.StateRunning:
					state = _("Zapped") if timer.justplay else _("Recording")
				elif timer.state == RealTimerEntry.StateEnded:
					state = _("Done")
				else:
					state = _("<Unknown>")
			except Exception:
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
		if config.usage.timerlist_show_epg.value:
			event = self.getEPGEvent(cur)
			if event:
				self["Event"].newEvent(event)
				self["ServiceEvent"].newService(cur.service_ref.ref)

	def fillTimerList(self):
		def _cmp(a, b):  # Helper function to move finished timers to end of list.
			return (a > b) - (a < b)

		def eol_compare(x, y):
			if x[0].state != y[0].state and x[0].state == RealTimerEntry.StateEnded or y[0].state == RealTimerEntry.StateEnded:
				return _cmp(x[0].state, y[0].state)
			return _cmp(x[0].begin, y[0].begin)

		_list = self.list
		del _list[:]
		_list.extend([(timer, False) for timer in self.session.nav.RecordTimer.timer_list])
		_list.extend([(timer, True) for timer in self.session.nav.RecordTimer.processed_timers])
		if config.usage.timerlist_finished_timer_position.index:  # End of list.
			_list.sort(key=cmp_to_key(eol_compare))
		else:
			_list.sort(key=lambda x: x[0].begin)

	def getEPGEvent(self, timer):
		event = None
		if timer:
			event_id = None
			epgcache = eEPGCache.getInstance()
			if hasattr(timer, "eit") and timer.eit:
				event = epgcache.lookupEventId(timer.service_ref.ref, timer.eit)
			if not event:
				ref = timer.service_ref if isinstance(timer.service_ref, str) else timer.service_ref.ref.toString()
				begin = timer.begin + config.recording.margin_before.value * 60
				duration = (timer.end - begin - config.recording.margin_after.value * 60) // 60
				if duration <= 0:
					duration = 30  # It seems to be a reminder or a justplay timer without end time, so search EPG events for the next 30 minutes.
				list = epgcache.lookupEvent(['IBDT', (ref, 0, begin, duration)])
				if len(list):
					for epgevent in list:
						if timer.name.startswith(epgevent[3]):
							event_id = epgevent[0]
							break
					if not event_id and timer.begin != timer.end:  # No match at title search --> search in time span.
						for epgevent in list:
							if timer.end >= (begin + epgevent[2]) and timer.begin <= epgevent[1]:
								event_id = epgevent[0]
								break
					if event_id:
						event = epgcache.lookupEventId(timer.service_ref.ref, event_id)
		return event

	def openEventView(self):
		event = None
		timer = self["timerlist"].getCurrent()
		if timer:
			event = self.getEPGEvent(timer)
		if event:
			self.session.openWithCallback(self.refill, EventViewSimple, event, timer.service_ref)

	def showLog(self):
		cur = self["timerlist"].getCurrent()
		if cur:
			self.session.openWithCallback(self.finishedEdit, TimerLog, cur)

	def openEdit(self):
		cur = self["timerlist"].getCurrent()
		if cur:
			self.session.openWithCallback(self.finishedEdit, TimerEntry, cur)

	def cleanupQuestion(self):
		self.session.openWithCallback(self.cleanupTimer, MessageBox, _("Really delete completed timers?"))

	def cleanupTimer(self, delete):
		if delete:
			self.session.nav.RecordTimer.cleanup()
			self.refill()
			self.updateState()

	def removeTimerQuestion(self):
		cur = self["timerlist"].getCurrent()
		service = str(cur.service_ref.getServiceName())
		t = localtime(cur.begin)
		f = str(t.tm_year) + str(t.tm_mon).zfill(2) + str(t.tm_mday).zfill(2) + " " + str(t.tm_hour).zfill(2) + str(t.tm_min).zfill(2) + " - " + service + " - " + cur.name
		f = f.replace(':', '_')
		f = f.replace(',', '_')
		f = f.replace('/', '_')
		if not cur:
			return
		onhdd = False
		self.moviename = f
		path = resolveFilename(SCOPE_HDD)
		try:
			files = listdir(path)
		except OSError as err:
			files = ""
		for file in files:
			if file.startswith(f):
				onhdd = True
				break
		curname = "'%s'" % cur.name
		if onhdd:
			message = (_("Do you really want to delete %s?") % (curname))
			choices = [
				(_("No"), "no"),
				(_("Yes, delete from timer list"), "yes"),
				(_("Yes, delete from timer list and delete recording"), "yesremove")
			]
			self.session.openWithCallback(self.startDelete, ChoiceBox, title=message, list=choices)
		else:
			self.session.openWithCallback(self.removeTimer, MessageBox, _("Do you really want to delete %s?") % (curname), default=False)

	def startDelete(self, answer):
		if not answer or not answer[1]:
			self.close()
			return
		if answer[1] == 'no':
			return
		elif answer[1] == 'yes':
			self.removeTimer(True)
		elif answer[1] == 'yesremove':
			if isPluginInstalled("EnhancedMovieCenter"):
				if config.EMC.movie_trashcan_enable.value:
					trashpath = config.EMC.movie_trashcan_path.value
					self.MoveToTrash(trashpath)
			elif config.usage.movielist_trashcan.value:
				trashpath = resolveFilename(SCOPE_HDD) + '.Trash'
				self.MoveToTrash(trashpath)
			else:
				self.session.openWithCallback(self.callbackRemoveRecording, MessageBox, _("Do you really want to delete the recording?"), default=False)

	def callbackRemoveRecording(self, answer):
		if not answer:
			return
		self.delete()

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

	def MoveToTrash(self, trashpath):
		if not exists(trashpath):
			system("mkdir -p %s" % trashpath)
		self.removeTimer(True)
		moviepath = normpath(resolveFilename(SCOPE_HDD))
		movedList = []
		files = listdir(moviepath)
		for file in files:
			if file.startswith(self.moviename):
				movedList.append((pathjoin(moviepath, file), pathjoin(trashpath, file)))
		moveFiles(movedList, None)

	def delete(self):
		item = self["timerlist"].getCurrent()
		if item is None:
			return  # Huh?
		name = item.name
		service = str(item.service_ref.getServiceName())
		t = localtime(item.begin)
		f = str(t.tm_year) + str(t.tm_mon).zfill(2) + str(t.tm_mday).zfill(2) + " " + str(t.tm_hour).zfill(2) + str(t.tm_min).zfill(2) + " - " + service + " - " + name
		f = f.replace(':', '_')
		f = f.replace(',', '_')
		f = f.replace('/', '_')
		path = resolveFilename(SCOPE_HDD)
		self.removeTimer(True)
		from enigma import eBackgroundFileEraser
		files = listdir(path)
		for file in files:
			if file.startswith(f):
				eBackgroundFileEraser.getInstance().erase(realpath(path + file))

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
		# FIXME: Only works if already playing a service!
		serviceref = ServiceReference(self.session.nav.getCurrentlyPlayingServiceOrGroup())
		if event is None:
			data = (int(time()), int(time() + 60), "", "", None)
		else:
			data = parseEvent(event, description=False)

		self.addTimer(RecordTimerEntry(serviceref, checkOldTimers=True, dirname=preferredTimerPath(), *data))

	def addTimer(self, timer):
		self.session.openWithCallback(self.finishedAdd, TimerEntry, timer)

	def finishedEdit(self, answer):
		if answer[0]:
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
				print("[TimerEdit] Sanity check passed.")
				self.session.nav.RecordTimer.timeChanged(entry)
			self.fillTimerList()
			self.updateState()

	def finishedAdd(self, answer):
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

	def finishSanityCorrection(self, answer):
		self.finishedAdd(answer)

	def leave(self):
		# Disabled because it crashes on some boxes with SSD ######################
		# self.session.nav.RecordTimer.on_state_change.append(self.onStateChange)
		# #########################################################################
		self.close()

	def onStateChange(self, entry):
		self.refill()
		self.updateState()


class TimerSanityConflict(Screen):
	EMPTY = 0
	ENABLE = 1
	DISABLE = 2
	EDIT = 3

	def __init__(self, session, timer):
		Screen.__init__(self, session)
		self.timer = timer
		print("[TimerEdit] TimerSanityConflict")
		self["timer1"] = TimerList(self.getTimerList(timer[0]))
		self.list = []
		self.list2 = []
		count = 0
		for x in timer:
			if count != 0:
				self.list.append(("%s %d" % (_("Conflicting timer"), count), x))
				self.list2.append((timer[count], False))
			count += 1
		if count == 1:
			self.list.append((_("Channel not in services list")))
		self["list"] = MenuList(self.list)
		self["timer2"] = TimerList(self.list2)
		self["key_red"] = StaticText(_("Edit New Entry"))
		self["key_green"] = StaticText("")
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText("")
		self.key_green_choice = self.EMPTY
		self.key_yellow_choice = self.EMPTY
		self.key_blue_choice = self.EMPTY
		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions", "ShortcutActions", "TimerEditActions"], {
			"ok": self.leave_ok,
			"cancel": self.leave_cancel,
			"red": self.editTimer1,
			"up": self.up,
			"down": self.down
		}, prio=-1)
		self.setTitle(_("Timer Sanity Error"))
		self.onShown.append(self.updateState)

	def getTimerList(self, timer):
		return [(timer, False)]

	def editTimer1(self):
		self.session.openWithCallback(self.finishedEdit, TimerEntry, self["timer1"].getCurrent())

	def editTimer2(self):
		self.session.openWithCallback(self.finishedEdit, TimerEntry, self["timer2"].getCurrent())

	def toggleNewTimer(self):
		if self.timer[0].disabled:
			self.timer[0].disabled = False
			self.session.nav.RecordTimer.timeChanged(self.timer[0])
		elif not self.timer[0].isRunning():
			self.timer[0].disabled = True
			self.session.nav.RecordTimer.timeChanged(self.timer[0])
		self.finishedEdit((True, self.timer[0]))

	def toggleTimer(self):
		x = self["list"].getSelectedIndex() + 1  # The first is the new timer so we do +1 here.
		if self.timer[x].disabled:
			self.timer[x].disabled = False
			self.session.nav.RecordTimer.timeChanged(self.timer[x])
			if not self.timer[0].isRunning():
				self.timer[0].disabled = True
				self.session.nav.RecordTimer.timeChanged(self.timer[0])
		elif not self.timer[x].isRunning():
			self.timer[x].disabled = True
			self.session.nav.RecordTimer.timeChanged(self.timer[x])
			if self.timer[x].disabled:
				self.timer[0].disabled = False
				self.session.nav.RecordTimer.timeChanged(self.timer[0])
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

	def removeAction(self, descr):
		actions = self["actions"].actions
		if descr in actions:
			del actions[descr]

	def updateState(self):
		if self.timer[0] is not None:
			if self.timer[0].disabled and self.key_green_choice != self.ENABLE:
				self["actions"].actions.update({"green": self.toggleTimer})
				self["key_green"].setText(_("Enable"))
				self.key_green_choice = self.ENABLE
			elif self.timer[0].isRunning() and not self.timer[0].repeated and self.key_green_choice != self.EMPTY:
				self.removeAction("green")
				self["key_green"].setText("")
				self.key_green_choice = self.EMPTY
			elif (not self.timer[0].isRunning() or self.timer[0].repeated) and self.key_green_choice != self.DISABLE:
				self["actions"].actions.update({"green": self.toggleNewTimer})
				self["key_green"].setText(_("Disable"))
				self.key_green_choice = self.DISABLE
		if len(self.timer) > 1:
			x = self["list"].getSelectedIndex() + 1  # The first is the new timer so we do +1 here.
			if self.timer[x] is not None:
				if self.key_yellow_choice == self.EMPTY:
					self["actions"].actions.update({"yellow": self.editTimer2})
					self["key_yellow"].setText(_("Edit"))
					self.key_yellow_choice = self.EDIT
				if self.timer[x].disabled and self.key_blue_choice != self.ENABLE:
					self["actions"].actions.update({"blue": self.toggleTimer})
					self["key_blue"].setText(_("Enable"))
					self.key_blue_choice = self.ENABLE
				elif self.timer[x].isRunning() and not self.timer[x].repeated and self.key_blue_choice != self.EMPTY:
					self.removeAction("blue")
					self["key_blue"].setText("")
					self.key_blue_choice = self.EMPTY
				elif (not self.timer[x].isRunning() or self.timer[x].repeated) and self.key_blue_choice != self.DISABLE:
					self["actions"].actions.update({"blue": self.toggleTimer})
					self["key_blue"].setText(_("Disable"))
					self.key_blue_choice = self.DISABLE
		else:
			# FIXME: This doesn't hide the buttons just the text!
			if self.key_yellow_choice != self.EMPTY:
				self.removeAction("yellow")
				self["key_yellow"].setText("")
				self.key_yellow_choice = self.EMPTY
			if self.key_blue_choice != self.EMPTY:
				self.removeAction("blue")
				self["key_blue"].setText("")
				self.key_blue_choice = self.EMPTY


class TimerEditListSummary(Screen):
	def __init__(self, session, parent):
		Screen.__init__(self, session, parent=parent)
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

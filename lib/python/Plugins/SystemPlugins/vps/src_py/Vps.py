from os import X_OK, access, chmod
from time import localtime, strftime, time
from enigma import eConsoleAppContainer, eEnv, eEPGCache, eServiceReference, eTimer, getBestPlayableServiceReference

import NavigationInstance
import Screens.Standby
from Components.config import config
from Components.TimerSanityCheck import TimerSanityCheck
from RecordTimer import AFTEREVENT, RecordTimerEntry, parseEvent
from Screens.MessageBox import MessageBox
from ServiceReference import ServiceReference
from timer import TimerEntry
from Tools import Notifications
from Tools.StbHardware import getFPWasTimerWakeup

vps_exe = eEnv.resolve("${libdir}/enigma2/python/Plugins/SystemPlugins/vps/vps")
if not access(vps_exe, X_OK):
	chmod(vps_exe, 493)


class vps_timer:
	def __init__(self, timer, session):
		self.timer = timer
		self.session = session
		self.program = eConsoleAppContainer()
		self.program.dataAvail.append(self.program_dataAvail)
		self.program.appClosed.append(self.program_closed)
		self.program_running = False
		self.program_try_search_running = False
		self.activated_auto_increase = False
		self.simulate_recordService = None
		self.demux = -1
		self.rec_ref = None
		self.found_pdc = False
		self.dont_restart_program = False
		self.org_timer_end = 0
		self.org_timer_begin = 0
		self.max_extending_timer = 4 * 3600
		self.next_events = []
		self.new_timer_copy = None

	def program_closed(self, retval):
		self.timer.log(0, "[VPS] stop monitoring (process terminated)")
		if self.program_running or self.program_try_search_running:
			self.program_running = False
			self.program_try_search_running = False
			self.stop_simulation()

	def program_dataAvail(self, data):
		if isinstance(data, bytes):
			data = data.decode()
		if self.timer is None or self.timer.state == TimerEntry.StateEnded or self.timer.cancelled:
			self.program_abort()
			self.stop_simulation()
			return
		if self.timer.vpsplugin_enabled is False or config.plugins.vps.enabled.value is False:
			if self.activated_auto_increase:
				self.timer.autoincrease = False
			self.program_abort()
			self.stop_simulation()
			return

		lines = data.split("\n")
		for line in lines:
			data = line.split()
			if len(data) == 0:
				continue

			self.timer.log(0, "[VPS] " + line)

			if data[0] == "RUNNING_STATUS":
				if data[1] == "0":  # undefined
					if data[2] == "FOLLOWING":
						data[1] = "1"
					else:
						data[1] = "4"

				if data[1] == "1":  # not running
					# Wenn der Eintrag im Following (Section_Number = 1) ist,
					# dann nicht beenden (Sendung begann noch gar nicht)
					if data[2] == "FOLLOWING":
						self.activate_autoincrease()
					else:
						if self.timer.state == TimerEntry.StateRunning and not self.set_next_event():
							self.activated_auto_increase = False
							self.timer.autoincrease = False

							if self.timer.vpsplugin_overwrite:
								# sofortiger Stopp
								self.timer.abort()
								self.session.nav.RecordTimer.doActivate(self.timer)
								self.stop_simulation()

							self.dont_restart_program = True
							self.program_abort()

				elif data[1] == "2":  # starts in a few seconds
					self.activate_autoincrease()
					if self.timer.state == TimerEntry.StateWaiting:
						self.session.nav.RecordTimer.doActivate(self.timer)

				elif data[1] == "3":  # pausing
					if self.timer.state == TimerEntry.StateRunning:
						self.activate_autoincrease()

				elif data[1] == "4":  # running
					if self.timer.state == TimerEntry.StateRunning:
						self.activate_autoincrease()
					elif self.timer.state == TimerEntry.StateWaiting or self.timer.state == TimerEntry.StatePrepared:
						# setze Startzeit auf jetzt
						self.timer.begin = int(time())
						self.session.nav.RecordTimer.timeChanged(self.timer)

						self.activate_autoincrease()
						self.program_abort()
						self.stop_simulation()
						vps_timers.checksoon(2000)  # Programm neu starten

				elif data[1] == "5":  # service off-air
					self.timer.vpsplugin_overwrite = False
					if self.activated_auto_increase:
						self.timer.autoincrease = False
						self.activated_auto_increase = False

			elif data[0] == "EVENT_ENDED":
				if not self.set_next_event():
					if self.timer.state == TimerEntry.StateRunning:
						self.activated_auto_increase = False
						self.timer.autoincrease = False

						if self.timer.vpsplugin_overwrite:
							# sofortiger Stopp
							self.timer.abort()
							self.session.nav.RecordTimer.doActivate(self.timer)
							self.stop_simulation()

					self.program_abort()
					self.stop_simulation()

			elif data[0] == "OTHER_TS_RUNNING_STATUS":
				if self.timer.state == TimerEntry.StateWaiting:
					self.timer.start_prepare = int(time())
					self.session.nav.RecordTimer.doActivate(self.timer)

				self.program_abort()
				self.stop_simulation()
				vps_timers.checksoon(2000)

			# PDC
			elif data[0] == "PDC_FOUND_EVENT_ID":
				self.found_pdc = True
				self.timer.eit = int(data[1])
				epgcache = eEPGCache.getInstance()
				evt = epgcache.lookupEventId(self.rec_ref, self.timer.eit)
				if evt:
					self.timer.name = evt.getEventName()
					self.timer.description = evt.getShortDescription()
				self.program_abort()
				vps_timers.checksoon(500)

			elif data[0] == "FOUND_EVENT_ON_SCHEDULE":
				starttime = int(data[1])
				duration = int(data[2])
				# Soll die Sendung laut EPG erst nach dem Ende dieses Timers beginnen?
				if (not self.timer.vpsplugin_overwrite and (self.timer.end + 300) < starttime) or (self.timer.vpsplugin_overwrite and (self.timer.end + self.max_extending_timer - 1800) < starttime):
					if self.new_timer_copy is None:
						if self.activated_auto_increase:
							self.timer.autoincrease = False
							self.activated_auto_increase = False
						self.copyTimer(starttime, duration)
						self.timer.log(0, "[VPS] copied this timer, since the event may start later than this timer ends")

				elif not self.activated_auto_increase:
					self.activate_autoincrease()

			elif data[0] == "EVENT_OVER" or data[0] == "CANNOT_FIND_EVENT":
				self.max_extending_timer = 2 * 3600
				if self.activated_auto_increase:
					self.timer.autoincrease = False
					self.activated_auto_increase = False

			elif data[0] == "PDC_MULTIPLE_FOUND_EVENT":
				self.check_and_add_event(int(data[1]))

			# Programm meldet, dass die EIT (present/following) des Senders offenbar
			# momentan fehlerhaft ist
			elif data[0] == "EIT_APPARENTLY_UNRELIABLE":
				if self.timer.vpsplugin_overwrite:
					self.timer.vpsplugin_overwrite = False
					self.timer.log(0, "[VPS] can't trust EPG currently, go to safe mode")

	def activate_autoincrease(self):
		if not self.activated_auto_increase:
			self.activated_auto_increase = True
			self.timer.autoincrease = True
			self.timer.autoincreasetime = 60

			if self.org_timer_end == 0:
				self.org_timer_end = self.timer.end
			self.timer.log(0, "[VPS] enable autoincrease")

			if self.new_timer_copy is not None and (self.new_timer_copy in self.session.nav.RecordTimer.timer_list):
				self.new_timer_copy.afterEvent = AFTEREVENT.NONE
				self.new_timer_copy.dontSave = True
				NavigationInstance.instance.RecordTimer.removeEntry(self.new_timer_copy)
				self.new_timer_copy = None
				self.timer.log(0, "[VPS] delete timer copy")

	# Noch ein Event aufnehmen?
	def set_next_event(self):
		if not self.timer.vpsplugin_overwrite and len(self.next_events) > 0:
			if not self.activated_auto_increase:
				self.activate_autoincrease()

			(starttime, neweventid) = self.next_events.pop(0)
			self.timer.eit = neweventid
			self.dont_restart_program = False
			self.program_abort()
			self.timer.log(0, "[VPS] record now event_id " + str(neweventid))
			vps_timers.checksoon(3000)
			return True
		else:
			return False

	def program_abort(self):
		if self.program_running or self.program_try_search_running:
			#self.program.sendCtrlC()
			self.program.kill()
			self.program_running = False
			self.program_try_search_running = False
			self.timer.log(0, "[VPS] stop monitoring")

	def stop_simulation(self):
		if self.simulate_recordService:
			NavigationInstance.instance.stopRecordService(self.simulate_recordService)
			self.simulate_recordService = None
			self.timer.log(0, "[VPS] stop RecordService (simulation)")

	def check_and_add_event(self, neweventid):
		if not config.plugins.vps.allow_seeking_multiple_pdc.value:
			return

		epgcache = eEPGCache.getInstance()
		evt = epgcache.lookupEventId(self.rec_ref, neweventid)

		if evt:
			evt_begin = evt.getBeginTime() + 60
			evt_end = evt.getBeginTime() + evt.getDuration() - 60

			if evt_begin < self.timer.begin:
				return

			for checktimer in self.session.nav.RecordTimer.timer_list:
				if checktimer == self.timer:
					continue
				if (checktimer.begin - evt_begin) > 3600 * 2:
					break

				compareString = checktimer.service_ref.ref.toCompareString()
				if compareString == self.timer.service_ref.ref.toCompareString() or compareString == self.rec_ref.toCompareString():
					if checktimer.eit == neweventid:
						return

					if checktimer.begin <= evt_begin and checktimer.end >= evt_end:
						if checktimer.vpsplugin_enabled is None or not checktimer.vpsplugin_enabled:
							return

						# manuell angelegter Timer mit VPS
						if checktimer.name == "" and checktimer.vpsplugin_time is not None:
							checktimer.eit = neweventid
							checktimer.name = evt.getEventName()
							checktimer.description = evt.getShortDescription()
							checktimer.vpsplugin_time = None
							checktimer.log(0, "[VPS] changed timer (found same PDC-Time as in other VPS-recording)")
							return

			# eigenen Timer überprüfen, wenn Zeiten nicht überschrieben werden dürfen
			if not self.timer.vpsplugin_overwrite and evt_begin <= self.timer.end:
				check_already_existing = [x for (x, y) in self.next_events if y == neweventid]
				if len(check_already_existing) > 0:
					start = check_already_existing.pop()
					if start == evt_begin:
						return
					else:
						self.next_events.remove((start, neweventid))
						self.timer.log(0, "[VPS] delete event_id " + str(neweventid) + " because of delay " + str(evt_begin - start))

				self.next_events.append((evt_begin, neweventid))
				self.next_events = sorted(self.next_events)
				self.timer.log(0, "[VPS] add event_id " + str(neweventid))

			else:
				newevent_data = parseEvent(evt)
				newEntry = RecordTimerEntry(ServiceReference(self.rec_ref), *newevent_data)
				newEntry.vpsplugin_enabled = True
				newEntry.vpsplugin_overwrite = True
				newEntry.dirname = self.timer.dirname
				newEntry.log(0, "[VPS] added this timer (found same PDC-Time as in other VPS-recording)")

				# Wenn kein Timer-Konflikt auftritt, wird der Timer angelegt.
				res = NavigationInstance.instance.RecordTimer.record(newEntry)
				self.timer.log(0, "[VPS] added another timer, res " + str(res))

	def copyTimer(self, start, duration):
		starttime = start - config.recording.margin_before.getValue() * 60
		endtime = start + duration + config.recording.margin_after.getValue() * 60
		self.new_timer_copy = RecordTimerEntry(ServiceReference(self.rec_ref), starttime, endtime, self.timer.name, self.timer.description, self.timer.eit, False, False, AFTEREVENT.AUTO, False, self.timer.dirname, self.timer.tags)
		self.new_timer_copy.vpsplugin_enabled = True
		self.new_timer_copy.vpsplugin_overwrite = self.timer.vpsplugin_overwrite
		self.new_timer_copy.log(0, "[VPS] added this timer")
		NavigationInstance.instance.RecordTimer.record(self.new_timer_copy)

	# startet den Hintergrundprozess

	def program_do_start(self, mode):
		if self.program_running or self.program_try_search_running:
			self.program_abort()

		if mode == 1:
			self.demux = -1
			current_service = NavigationInstance.instance.getCurrentService()
			if current_service:
				stream = current_service.stream()
				if stream:
					streamdata = stream.getStreamingData()
					if (streamdata and ('demux' in streamdata)):
						self.demux = streamdata['demux']
			if self.demux == -1:
				return

			self.program_try_search_running = True
			self.program_running = False
			mode_program = 1
		else:
			self.program_try_search_running = False
			self.program_running = True
			mode_program = 0

		sid = self.rec_ref.getData(1)
		tsid = self.rec_ref.getData(2)
		onid = self.rec_ref.getData(3)
		demux = "/dev/dvb/adapter0/demux" + str(self.demux)

		# PDC-Zeit?
		if (self.timer.name == "" or self.timer.eit is None) and self.timer.vpsplugin_time is not None and not self.found_pdc:
			mode_program += 2
			day = strftime("%d", localtime(self.timer.vpsplugin_time))
			month = strftime("%m", localtime(self.timer.vpsplugin_time))
			hour = strftime("%H", localtime(self.timer.vpsplugin_time))
			minute = strftime("%M", localtime(self.timer.vpsplugin_time))
			cmd = vps_exe + " " + demux + " " + str(mode_program) + " " + str(onid) + " " + str(tsid) + " " + str(sid) + " 0 " + day + " " + month + " " + hour + " " + minute
			self.timer.log(0, "[VPS] seek PDC-Time")
			self.program.execute(cmd)
			return

		cmd = vps_exe + " " + demux + " " + str(mode_program) + " " + str(onid) + " " + str(tsid) + " " + str(sid) + " " + str(self.timer.eit)
		self.timer.log(0, "[VPS] start monitoring running-status")
		self.program.execute(cmd)

	def program_start(self):
		self.demux = -1

		if self.dont_restart_program:
			return

		self.rec_ref = self.timer.service_ref and self.timer.service_ref.ref
		if self.rec_ref and self.rec_ref.flags & eServiceReference.isGroup:
			self.rec_ref = getBestPlayableServiceReference(self.rec_ref, eServiceReference())

		# recordService (Simulation) ggf. starten
		if self.timer.state == TimerEntry.StateWaiting:
			if self.simulate_recordService is None:
				if self.rec_ref:
					self.simulate_recordService = NavigationInstance.instance.recordService(self.rec_ref, True)
					if self.simulate_recordService:
						res = self.simulate_recordService.start()
						self.timer.log(0, "[VPS] start recordService (simulation) " + str(res))
						if res != 0 and res != -1:
							# Fehler aufgetreten (kein Tuner frei?)
							NavigationInstance.instance.stopRecordService(self.simulate_recordService)
							self.simulate_recordService = None

							# in einer Minute ggf. nochmal versuchen
							if 60 < self.nextExecution:
								self.nextExecution = 60

							# Bei Overwrite versuchen ohne Fragen auf Sender zu schalten
							if self.timer.vpsplugin_overwrite is True:
								cur_ref = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
								if cur_ref and not cur_ref.getPath() and self.rec_ref.toCompareString() != cur_ref.toCompareString():
									self.timer.log(9, "[VPS-Plugin] zap without asking (simulation)")
									Notifications.AddNotification(MessageBox, _("In order to record a timer, the TV was switched to the recording service!\n"), type=MessageBox.TYPE_INFO, timeout=20)
									NavigationInstance.instance.playService(self.rec_ref)
									if 3 < self.nextExecution:
										self.nextExecution = 3
							else:
								# ansonsten versuchen auf dem aktuellen Transponder/Kanal nach Infos zu suchen
								if not self.program_try_search_running:
									self.program_do_start(1)
						else:  # Simulation hat geklappt
							if 1 < self.nextExecution:
								self.nextExecution = 1
			else:  # Simulation läuft schon
				# hole Demux
				stream = self.simulate_recordService.stream()
				if stream:
					streamdata = stream.getStreamingData()
					if (streamdata and ('demux' in streamdata)):
						self.demux = streamdata['demux']

				if self.demux == -1:
					# ist noch nicht soweit(?), in einer Sekunde erneut versuchen
					if 1 < self.nextExecution:
						self.nextExecution = 1
				else:
					self.program_do_start(0)

		elif self.timer.state == TimerEntry.StatePrepared or self.timer.state == TimerEntry.StateRunning:
			stream = self.timer.record_service.stream()
			if stream:
				streamdata = stream.getStreamingData()
				if (streamdata and ('demux' in streamdata)):
					self.demux = streamdata['demux']
			if self.demux != -1:
				self.program_do_start(0)

	# überprüft, ob etwas zu tun ist und gibt die Sekunden zurück, bis die Funktion
	# spätestens wieder aufgerufen werden sollte
	# oder -1, um vps_timer löschen zu lassen

	def check(self):
		# Simulation ggf. stoppen
		if self.timer.state > TimerEntry.StateWaiting and self.simulate_recordService:
			self.stop_simulation()

		# VPS wurde wieder deaktiviert oder Timer wurde beendet
		if self.timer is None or self.timer.state == TimerEntry.StateEnded or self.timer.cancelled:
			self.program_abort()
			self.stop_simulation()
			return -1

		if self.timer.vpsplugin_enabled is False or config.plugins.vps.enabled.value is False:
			if self.activated_auto_increase:
				self.timer.autoincrease = False
			self.program_abort()
			self.stop_simulation()
			return -1

		self.nextExecution = 180

		if config.plugins.vps.initial_time.value < 2 and self.timer.vpsplugin_overwrite:
			initial_time = 120
		else:
			initial_time = config.plugins.vps.initial_time.value * 60

		if self.timer.vpsplugin_overwrite is True:
			if self.timer.state == TimerEntry.StateWaiting or self.timer.state == TimerEntry.StatePrepared:
				# Startzeit verschieben
				if (self.timer.begin - 60) < time():
					if self.org_timer_begin == 0:
						self.org_timer_begin = self.timer.begin
					elif (self.org_timer_begin + self.max_extending_timer) < time():
						# Sendung begann immer noch nicht -> abbrechen
						self.timer.abort()
						self.session.nav.RecordTimer.doActivate(self.timer)
						self.program_abort()
						self.stop_simulation()
						self.timer.log(0, "[VPS] abort timer, waited enough to find Event-ID")
						return -1

					self.timer.begin += 60
					if (self.timer.end - self.timer.begin) < 300:
						self.timer.end += 180
						# auf Timer-Konflikt prüfen
						timersanitycheck = TimerSanityCheck(self.session.nav.RecordTimer.timer_list, self.timer)
						if not timersanitycheck.check():
							self.timer.abort()
							self.session.nav.RecordTimer.doActivate(self.timer)
							self.program_abort()
							self.stop_simulation()
							self.timer.log(0, "[VPS] abort timer due to TimerSanityCheck")
							return -1

					self.session.nav.RecordTimer.timeChanged(self.timer)

				if 30 < self.nextExecution:
					self.nextExecution = 30

		# Programm starten
		if not self.program_running:
			if self.timer.state == TimerEntry.StateRunning:
				self.program_start()

			elif initial_time > 0:
				if (self.timer.begin - initial_time) <= time():
					self.program_start()
				else:
					n = self.timer.begin - initial_time - time()
					if n < self.nextExecution:
						self.nextExecution = n

		if self.timer.state == TimerEntry.StateRunning:
			if self.activated_auto_increase and self.org_timer_end != 0 and (self.org_timer_end + (4 * 3600)) < time():
				# Aufnahme läuft seit 4 Stunden im Autoincrease -> abbrechen
				self.timer.autoincrease = False
				self.activated_auto_increase = False
				self.dont_restart_program = True
				self.program_abort()
				self.stop_simulation()
				self.timer.log(0, "[VPS] stop recording, too much autoincrease")

			try:
				if self.timer.vpsplugin_wasTimerWakeup:
					self.timer.vpsplugin_wasTimerWakeup = False
					if not Screens.Standby.inTryQuitMainloop:
						RecordTimerEntry.TryQuitMainloop(False)
			except Exception:
				pass

		return self.nextExecution


class vps:
	def __init__(self):
		self.timer = eTimer()
		self.timer.callback.append(self.checkTimer)

		self.vpstimers = []
		self.current_timers_list = []
		self.max_activation = 900

	def checkTimer(self):
		nextExecution = self.max_activation

		# nach den Timern schauen und ggf. zur Liste hinzufügen
		if config.plugins.vps.enabled.value is True:
			now = time()
			try:
				for timer in self.session.nav.RecordTimer.timer_list:
					n = timer.begin - now - (config.plugins.vps.initial_time.value * 60) - 120
					if n <= self.max_activation:
						if timer.vpsplugin_enabled is True and timer not in self.current_timers_list and not timer.justplay and not timer.repeated and not timer.disabled:
							self.addTimerToList(timer)
					elif (timer.begin - now) > 4 * 3600:
						break
			except AttributeError:
				print("[VPS-Plugin] AttributeError in Vps.py")
				return
		else:
			nextExecution = 14400

		# eigene Timer-Liste durchgehen
		for o_timer in self.vpstimers[:]:
			newtime = int(o_timer.check())
			if newtime == -1:
				self.current_timers_list.remove(o_timer.timer)
				self.vpstimers.remove(o_timer)
			elif newtime < nextExecution:
				nextExecution = newtime

		if nextExecution <= 0:
			nextExecution = 1

		self.timer.startLongTimer(nextExecution)
		print("[VPS-Plugin] next execution in " + str(nextExecution) + " sec")

	def addTimerToList(self, timer):
		self.vpstimers.append(vps_timer(timer, self.session))
		self.current_timers_list.append(timer)

	def checksoon(self, newstart=3000):
		self.timer.start(newstart, True)

	def shutdown(self):
		for o_timer in self.vpstimers:
			o_timer.program_abort()
			o_timer.stop_simulation()

	def checkNextAfterEventAuto(self):
		if getFPWasTimerWakeup() and config.plugins.vps.allow_wakeup.value and len(self.session.nav.RecordTimer.timer_list) > 0:
			next_timer = self.session.nav.RecordTimer.timer_list[0]
			if next_timer.vpsplugin_enabled and next_timer.afterEvent == AFTEREVENT.AUTO and (next_timer.begin - (config.plugins.vps.initial_time.value * 60) - 300) < time():
				next_timer.vpsplugin_wasTimerWakeup = True

	def NextWakeup(self):
		if config.plugins.vps.enabled.value is False or config.plugins.vps.allow_wakeup.value is False:
			return -1

		try:
			for timer in self.session.nav.RecordTimer.timer_list:
				if timer.vpsplugin_enabled and timer.state == TimerEntry.StateWaiting and not timer.justplay and not timer.repeated and not timer.disabled:
					return (timer.begin - (config.plugins.vps.initial_time.value * 60))
		except Exception:
			pass

		return -1


vps_timers = vps()

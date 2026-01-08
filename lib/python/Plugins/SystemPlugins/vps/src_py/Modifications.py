from time import time
from enigma import getBestPlayableServiceReference, eServiceReference
from Components.config import config, ConfigSelection, ConfigDateTime, ConfigClock, getConfigListEntry
from Screens.InfoBarGenerics import InfoBarInstantRecord
from Screens.Timers import onRecordTimerCreate, onRecordTimerSetup, onRecordTimerSave, onRecordTimerChannelChange
from .Vps_setup import VPS_Screen_Info
from .Vps_check import Check_PDC, VPS_check_PDC_Screen, VPS_check_on_instanttimer
from .Vps import vps_timers

timerentry_vpsplugin_enabled_index = 0


def timerCreateHook(self):

	try:
		self.timerentry_vpsplugin_dontcheck_pdc = not config.plugins.vps.do_PDC_check.getValue()
		default_value = "no"

		if self.timer.vpsplugin_enabled is not None:
			self.timerentry_vpsplugin_dontcheck_pdc = self.timer.vpsplugin_enabled
			if self.timer.vpsplugin_enabled:
				default_value = {False: "yes_safe", True: "yes"}[self.timer.vpsplugin_overwrite]

		elif config.plugins.vps.vps_default.value != "no" and self.timer.eit is not None and self.timer.name != "" and self.timer not in self.session.nav.RecordTimer.timer_list and self.timer not in self.session.nav.RecordTimer.processed_timers:
			service = self.timerServiceReference.ref
			if service and service.flags & eServiceReference.isGroup:
				service = getBestPlayableServiceReference(service, eServiceReference())
			has_pdc, last_check, default_vps = Check_PDC.check_service(service)
			if has_pdc == 1 or default_vps == 1:
				self.timerentry_vpsplugin_dontcheck_pdc = True
				default_value = config.plugins.vps.vps_default.value

		self.timerentry_vpsplugin_enabled = ConfigSelection(choices=[("no", _("No")), ("yes_safe", _("Yes (safe mode)")), ("yes", _("Yes"))], default=default_value)
		self.timerentry_vpsplugin_enabled.addNotifier(timerVps_enabled_Entry_Changed, initial_call=False, extra_args=self)

		if self.timer.vpsplugin_time is not None:
			self.timerentry_vpsplugin_time_date = ConfigDateTime(default=self.timer.vpsplugin_time, formatstring=_("%d.%B %Y"), increment=86400)
			self.timerentry_vpsplugin_time_clock = ConfigClock(default=self.timer.vpsplugin_time)
		else:
			self.timerentry_vpsplugin_time_date = ConfigDateTime(default=self.timer.begin, formatstring=_("%d.%B %Y"), increment=86400)
			self.timerentry_vpsplugin_time_clock = ConfigClock(default=self.timer.begin)
	except Exception as ex:
		print(f"[VPS] timerCreateHook : {ex}")
		pass


def timerSetupHook(self):
	global timerentry_vpsplugin_enabled_index
	currentIndex = self["config"].getCurrentIndex()
	if currentIndex == 0 and timerentry_vpsplugin_enabled_index > 0:
		currentIndex = timerentry_vpsplugin_enabled_index
		timerentry_vpsplugin_enabled_index = 0
	self.timerVps_enabled_Entry = None
	try:
		if self.timerType.value != "zap" and self.timerRepeat.value == "once" and config.plugins.vps.enabled.value is True:
			self.timerVps_enabled_Entry = getConfigListEntry(_("Enable VPS"), self.timerentry_vpsplugin_enabled)
			self.list.append(self.timerVps_enabled_Entry)

			if self.timerentry_vpsplugin_enabled.value != "no":
				service = self.timerServiceReference.ref
				if service and service.flags & eServiceReference.isGroup:
					service = getBestPlayableServiceReference(service, eServiceReference())

				if self.timer.eit is None or self.timer.name == "":
					if not self.timerentry_vpsplugin_dontcheck_pdc:
						self.timerentry_vpsplugin_dontcheck_pdc = True
						has_pdc, last_check, default_vps = Check_PDC.check_service(service)
						if has_pdc != 1 or Check_PDC.recheck(has_pdc, last_check):
							self.session.open(VPS_check_PDC_Screen, service, self)

					self.list.append(getConfigListEntry(_("VPS-Time (date)"), self.timerentry_vpsplugin_time_date))
					self.list.append(getConfigListEntry(_("VPS-Time (time)"), self.timerentry_vpsplugin_time_clock))

				elif not self.timerentry_vpsplugin_dontcheck_pdc:
					self.timerentry_vpsplugin_dontcheck_pdc = True
					has_pdc, last_check, default_vps = Check_PDC.check_service(service)
					if default_vps != 1 and (has_pdc != 1 or Check_PDC.recheck(has_pdc, last_check)):
						self.session.open(VPS_check_PDC_Screen, service, self, False)

					# Hilfetext
					if config.plugins.vps.infotext.value != 2:
						config.plugins.vps.infotext.value = 2
						config.plugins.vps.infotext.save()
						self.session.open(VPS_Screen_Info)
	except Exception as ex:
		print(f"[VPS] timerSetupHook : {ex}")
		pass
	self["config"].list = self.list
	self["config"].setCurrentIndex(currentIndex)


def timerVps_enabled_Entry_Changed(configElement, self):
	global timerentry_vpsplugin_enabled_index
	timerentry_vpsplugin_enabled_index = self["config"].getCurrentIndex()
	if configElement.value == "no":
		self.timerentry_vpsplugin_dontcheck_pdc = False


def timerSaveHook(self):
	try:
		self.timer.vpsplugin_enabled = self.timerentry_vpsplugin_enabled.value != "no"
		self.timer.vpsplugin_overwrite = self.timerentry_vpsplugin_enabled.value == "yes"
		if self.timer.vpsplugin_enabled:
			vps_timers.checksoon()
			if self.timer.name == "" or self.timer.eit is None:
				self.timer.vpsplugin_time = self.getTimestamp(self.timerentry_vpsplugin_time_date.value, self.timerentry_vpsplugin_time_clock.value)
				if self.timer.vpsplugin_overwrite:
					timerbegin, timerend = self.getBeginEnd()
					if (timerbegin - 60) < time() and (self.timer.vpsplugin_time - time()) > 1800:
						self.timerentry_date.value = self.timerentry_vpsplugin_time_date.value
						self.timerentry_starttime.value = self.timerentry_vpsplugin_time_clock.value
	except Exception as ex:
		print(f"[VPS] timerSaveHook : {ex}")
		pass


def timerChannelChangeHook(self):
	try:
		if self.timerentry_vpsplugin_enabled.value != "no":
			self.timerentry_vpsplugin_dontcheck_pdc = False
			self.createSetup()
	except Exception as ex:
		print(f"[VPS] timerChannelChangeHook : {ex}")
		pass


def new_InfoBarInstantRecord_recordQuestionCallback(self, answer, *args, **kwargs):

	self._recordQuestionCallback_old_rn_vps(answer, *args, **kwargs)

	try:
		entry = len(self.recording) - 1
		if answer is not None and answer[1] == "event" and config.plugins.vps.instanttimer.value != "no" and entry is not None and entry >= 0:
# If we aren't checking PDC, just put the values in directly
#
			if not config.plugins.vps.do_PDC_check.getValue():
				if config.plugins.vps.instanttimer.value == "yes":
					self.recording[entry].vpsplugin_enabled = True
					self.recording[entry].vpsplugin_overwrite = True
					vps_timers.checksoon()
				elif config.plugins.vps.instanttimer.value == "yes_safe":
					self.recording[entry].vpsplugin_enabled = True
					self.recording[entry].vpsplugin_overwrite = False
					vps_timers.checksoon()
			else:
				rec_ref = self.recording[entry].service_ref.ref
				if rec_ref and rec_ref.flags & eServiceReference.isGroup:
					rec_ref = getBestPlayableServiceReference(rec_ref, eServiceReference())
				self.session.open(VPS_check_on_instanttimer, rec_ref, self.recording[entry])

	except Exception as ex:
		print(f"[VPS] new_InfoBarInstantRecord_recordQuestionCallback : {ex}")
		pass


def register_vps():
	onRecordTimerCreate.append(timerCreateHook)
	onRecordTimerSetup.append(timerSetupHook)
	onRecordTimerSave.append(timerSaveHook)
	onRecordTimerChannelChange.append(timerChannelChangeHook)

	InfoBarInstantRecord._recordQuestionCallback_old_rn_vps = InfoBarInstantRecord.recordQuestionCallback
	InfoBarInstantRecord.recordQuestionCallback = new_InfoBarInstantRecord_recordQuestionCallback

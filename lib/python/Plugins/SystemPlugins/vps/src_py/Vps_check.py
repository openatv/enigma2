from enigma import eTimer, eConsoleAppContainer, getDesktop
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Tools.XMLTools import stringToXML
from Tools import Directories
from time import time
from Components.config import config
from .Vps import vps_exe, vps_timers
import NavigationInstance
from xml.etree.ElementTree import parse as xml_parse

check_pdc_interval_available = 3600 * 24 * 30 * 12
check_pdc_interval_unavailable = 3600 * 24 * 30 * 2


class VPS_check_PDC:
	def __init__(self):
		self.checked_services = {}
		self.load_pdc()

	def load_pdc(self):
		try:
			doc = xml_parse(Directories.resolveFilename(Directories.SCOPE_CONFIG, "vps.xml"))
			xmlroot = doc.getroot()

			if xmlroot is not None:
				for xml in xmlroot.findall("channel"):
					serviceref = xml.get("serviceref")
					has_pdc = xml.get("has_pdc")
					last_check = xml.get("last_check")
					default_vps = xml.get("default_vps")
					self.checked_services[serviceref] = {}
					self.checked_services[serviceref]["last_check"] = int(last_check)
					self.checked_services[serviceref]["has_pdc"] = int(has_pdc)
					if default_vps and default_vps != "None":
						self.checked_services[serviceref]["default_vps"] = int(default_vps)
					else:
						self.checked_services[serviceref]["default_vps"] = 0
		except Exception:
			pass

	def save_pdc(self):
		list = []
		list.append('<?xml version="1.0" ?>\n')
		list.append('<pdc_available>\n')

		now = time()
		for ch in self.checked_services:
			if (self.checked_services[ch]["last_check"] < (now - check_pdc_interval_available)) and self.checked_services[ch]["default_vps"] != 1:
				continue
			list.append('<channel')
			list.append(' serviceref="' + stringToXML(ch) + '"')
			list.append(' has_pdc="' + str(int(self.checked_services[ch]["has_pdc"])) + '"')
			list.append(' last_check="' + str(int(self.checked_services[ch]["last_check"])) + '"')
			list.append(' default_vps="' + str(int(self.checked_services[ch]["default_vps"])) + '"')
			list.append('></channel>\n')

		list.append('</pdc_available>\n')

		file = open(Directories.resolveFilename(Directories.SCOPE_CONFIG, "vps.xml"), "w")
		for x in list:
			file.write(x)
		file.close()

	def check_service(self, service):
# If we aren't checking PDC, returns successes for "now"
#
		if not config.plugins.vps.do_PDC_check.getValue():
			return 1, time(), 1

		service_str = service.toCompareString()

		try:
			if self.checked_services[service_str] is not None:
				return self.checked_services[service_str]["has_pdc"], self.checked_services[service_str]["last_check"], self.checked_services[service_str]["default_vps"]
			else:
				return -1, 0, 0
		except Exception:
			return -1, 0, 0

	def setServicePDC(self, service, state, default_vps):
		service_str = service.toCompareString()

		if state == -1 and default_vps == 0:
			try:
				del self.checked_services[service_str]
			except Exception:
				pass
		else:
			self.checked_services[service_str] = {}
			self.checked_services[service_str]["has_pdc"] = state
			self.checked_services[service_str]["last_check"] = time()
			self.checked_services[service_str]["default_vps"] = default_vps

		self.save_pdc()

	def recheck(self, has_pdc, last_check):
		return not ((has_pdc == 1 and last_check > (time() - check_pdc_interval_available)) or (has_pdc == 0 and last_check > (time() - check_pdc_interval_unavailable)))


Check_PDC = VPS_check_PDC()


# Prüfen, ob PDC-Descriptor vorhanden ist.
class VPS_check(Screen):
	if getDesktop(0).size().width() <= 1280:
		skin = """<screen name="vpsCheck" position="center,center" size="540,110" title="VPS-Plugin">
			<widget source="infotext" render="Label" position="10,10" size="520,90" font="Regular;21" valign="center" halign="center" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
		</screen>"""
	else:
		skin = """<screen name="vpsCheck" position="center,center" size="900,200" title="VPS-Plugin">
			<widget source="infotext" render="Label" position="15,15" size="870,170" font="Regular;32" valign="center" halign="center" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
		</screen>"""

	def __init__(self, session, service):
		Screen.__init__(self, session)

		self["infotext"] = StaticText(_("VPS-Plugin checks if the channel supports VPS ..."))

		self["actions"] = ActionMap(["OkCancelActions"],
			{
				"cancel": self.finish,
			}, -1)

		if service is None or service.getPath():
			self.close()
			return

		self.service = service
		self.program = eConsoleAppContainer()
		self.program.dataAvail.append(self.program_dataAvail)
		self.program.appClosed.append(self.program_closed)
		self.check = eTimer()
		self.check.callback.append(self.doCheck)
		self.simulate_recordService = None
		self.last_serviceref = None
		self.calledfinished = False

		self.has_pdc, self.last_check, self.default_vps = Check_PDC.check_service(self.service)

		self.check.start(50, True)

	def doCheck(self):
		if not Check_PDC.recheck(self.has_pdc, self.last_check):
			self.finish()
			return

		self.demux = -1
		if self.simulate_recordService is None:
			self.simulate_recordService = NavigationInstance.instance.recordService(self.service, True)
			if self.simulate_recordService:
				res = self.simulate_recordService.start()
				if res != 0 and res != -1:
					# Fehler aufgetreten (kein Tuner frei?)
					NavigationInstance.instance.stopRecordService(self.simulate_recordService)
					self.simulate_recordService = None

					if self.last_serviceref is not None:
						self.finish()
						return
					else:
						cur_ref = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
						if cur_ref and not cur_ref.getPath():
							self.last_serviceref = cur_ref
							NavigationInstance.instance.playService(None)
							self.check.start(1500, True)
							return
				else:  # hat geklappt
					self.check.start(1000, True)
					return
		else:
			stream = self.simulate_recordService.stream()
			if stream:
				streamdata = stream.getStreamingData()
				if (streamdata and ('demux' in streamdata)):
					self.demux = streamdata['demux']
			if self.demux != -1:
				self.startProgram()
				return

		if self.simulate_recordService is not None:
			NavigationInstance.instance.stopRecordService(self.simulate_recordService)
			self.simulate_recordService = None
		if self.last_serviceref is not None:
			NavigationInstance.instance.playService(self.last_serviceref)
		self.finish()

	def startProgram(self):
		sid = self.service.getData(1)
		tsid = self.service.getData(2)
		onid = self.service.getData(3)
		demux = "/dev/dvb/adapter0/demux" + str(self.demux)

		cmd = vps_exe + " " + demux + " 10 " + str(onid) + " " + str(tsid) + " " + str(sid) + " 0"
		self.program.execute(cmd)

	def program_closed(self, retval):
		if not self.calledfinished:
			self.setServicePDC(-1)
			self.finish()

	def program_dataAvail(self, data):
		if isinstance(data, bytes):
			data = data.decode()
		lines = data.split("\n")
		for line in lines:
			if line == "PDC_AVAILABLE" and not self.calledfinished:
				self.calledfinished = True
				self.setServicePDC(1)
				self.finish()

			elif line == "NO_PDC_AVAILABLE" and not self.calledfinished:
				self.calledfinished = True
				self.setServicePDC(0)
				self.finish()

	def setServicePDC(self, state):
		Check_PDC.setServicePDC(self.service, state, self.default_vps)
		self.has_pdc = state

	def finish(self):
		self.calledfinished = True
		self.check.stop()

		if self.simulate_recordService is not None:
			NavigationInstance.instance.stopRecordService(self.simulate_recordService)
			self.simulate_recordService = None

		if self.last_serviceref is not None:
			NavigationInstance.instance.playService(self.last_serviceref)

		self.ask_user()

	def ask_user(self):
		pass


class VPS_check_PDC_Screen(VPS_check):
	def __init__(self, session, service, timer_entry, manual_timer=True):
		self.timer_entry = timer_entry
		self.manual_timer = manual_timer
		VPS_check.__init__(self, session, service)

	def ask_user(self):
		if self.manual_timer:
			if self.has_pdc == 1:  # PDC vorhanden
				self.close()
			elif self.has_pdc == 0:  # kein PDC
				#nachfragen
				self.session.openWithCallback(self.finish_callback, MessageBox, _("The selected channel doesn't support VPS for manually programmed timers!\n Do you really want to enable VPS?"), default=False)
			else:  # konnte nicht ermitteln
				self.session.openWithCallback(self.finish_callback, MessageBox, _("The VPS-Plugin couldn't check if the selected channel supports VPS for manually programmed timers!\n Do you really want to enable VPS?"), default=False)
		else:
			if self.has_pdc == 1:  # PDC vorhanden
				self.close()
			else:
				choiceList = [(_("No"), 0), (_("Yes"), 1), (_("Yes, don't ask again"), 2)]
				self.session.openWithCallback(self.finish_callback2, ChoiceBox, title=_("VPS-Plugin couldn't check if the selected channel supports VPS.\n Do you really want to enable VPS?"), list=choiceList)

	def finish_callback(self, result):
		if not result:
			self.timer_entry.timerentry_vpsplugin_enabled.value = "no"
			self.timer_entry.createSetup()
			self.timer_entry.timerentry_vpsplugin_dontcheck_pdc = False
		self.close()

	def finish_callback2(self, result):
		if result is None or result[1] == 0:
			self.finish_callback(False)
			return

		elif result[1] == 2:
			Check_PDC.setServicePDC(self.service, self.has_pdc, 1)  # nicht mehr nachfragen

		self.close()


class VPS_check_on_instanttimer(VPS_check):
	def __init__(self, session, service, timer):
		self.timer = timer
		VPS_check.__init__(self, session, service)

	def ask_user(self):
		choiceList = [(_("No"), 0), (_("Yes (safe mode)"), 1), (_("Yes"), 2)]

		if self.has_pdc == 1:
			if config.plugins.vps.instanttimer.value == "yes":
				self.enable_vps()
			elif config.plugins.vps.instanttimer.value == "yes_safe":
				self.enable_vps_safe()
			else:
				self.session.openWithCallback(self.finish_callback, ChoiceBox, title=_("The channel may support VPS\n Do you want to enable VPS?"), list=choiceList)
		else:
			self.session.openWithCallback(self.finish_callback, ChoiceBox, title=_("VPS-Plugin couldn't check if the channel supports VPS.\n Do you want to enable VPS anyway?"), list=choiceList)

	def enable_vps(self):
		self.timer.vpsplugin_enabled = True
		self.timer.vpsplugin_overwrite = True
		vps_timers.checksoon()
		self.close()

	def enable_vps_safe(self):
		self.timer.vpsplugin_enabled = True
		self.timer.vpsplugin_overwrite = False
		vps_timers.checksoon()
		self.close()

	def finish_callback(self, result):
		if result is None or result[1] == 0:
			self.close()
		elif result[1] == 1:
			self.enable_vps_safe()
		else:
			self.enable_vps()

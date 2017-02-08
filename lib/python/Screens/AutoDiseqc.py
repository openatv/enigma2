from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import ActionMap
from Components.Sources.FrontendStatus import FrontendStatus
from Components.Sources.StaticText import StaticText
from Components.config import config, configfile, getConfigListEntry
from Components.NimManager import nimmanager, InitNimManager
from Components.TuneTest import Tuner
from enigma import eDVBFrontendParametersSatellite, eDVBResourceManager, eTimer


class AutoDiseqc(Screen, ConfigListScreen):
	diseqc_ports = [
		"A", "B", "C", "D"
	]

	sat_frequencies = [
		# astra 192 zdf
		( 11953, 27500, \
		eDVBFrontendParametersSatellite.Polarisation_Horizontal, eDVBFrontendParametersSatellite.FEC_3_4, \
		eDVBFrontendParametersSatellite.Inversion_Off, 192, \
		eDVBFrontendParametersSatellite.System_DVB_S, eDVBFrontendParametersSatellite.Modulation_Auto, \
		eDVBFrontendParametersSatellite.RollOff_auto, eDVBFrontendParametersSatellite.Pilot_Unknown, \
		-1, 0, 0,
		1079, 1, _("Astra 1 19.2e")),

		# astra 235 astra ses
		( 12168, 27500, \
		eDVBFrontendParametersSatellite.Polarisation_Vertical, eDVBFrontendParametersSatellite.FEC_3_4, \
		eDVBFrontendParametersSatellite.Inversion_Off, 235, \
		eDVBFrontendParametersSatellite.System_DVB_S, eDVBFrontendParametersSatellite.Modulation_Auto, \
		eDVBFrontendParametersSatellite.RollOff_auto, eDVBFrontendParametersSatellite.Pilot_Unknown, \
		-1, 0, 0,
		3224, 3, _("Astra 3 23.5e")),

		# astra 282 bbc
		( 10773, 22000, \
		eDVBFrontendParametersSatellite.Polarisation_Horizontal, eDVBFrontendParametersSatellite.FEC_5_6, \
		eDVBFrontendParametersSatellite.Inversion_Off, 282, \
		eDVBFrontendParametersSatellite.System_DVB_S, eDVBFrontendParametersSatellite.Modulation_Auto, \
		eDVBFrontendParametersSatellite.RollOff_auto, eDVBFrontendParametersSatellite.Pilot_Unknown, \
		-1, 0, 0,
		2045, 2, _("Astra 2 28.2e")),

		# hotbird 130 rai
		( 10992, 27500, \
		eDVBFrontendParametersSatellite.Polarisation_Vertical, eDVBFrontendParametersSatellite.FEC_2_3, \
		eDVBFrontendParametersSatellite.Inversion_Off, 130, \
		eDVBFrontendParametersSatellite.System_DVB_S, eDVBFrontendParametersSatellite.Modulation_Auto, \
		eDVBFrontendParametersSatellite.RollOff_auto, eDVBFrontendParametersSatellite.Pilot_Unknown, \
		-1, 0, 0,
		12400, 318, _("Hotbird 13.0e")),

		# hispasat 300 tsa
		( 10890, 27500, \
		eDVBFrontendParametersSatellite.Polarisation_Vertical, eDVBFrontendParametersSatellite.FEC_3_4, \
		eDVBFrontendParametersSatellite.Inversion_Off, 3300, \
		eDVBFrontendParametersSatellite.System_DVB_S, eDVBFrontendParametersSatellite.Modulation_Auto, \
		eDVBFrontendParametersSatellite.RollOff_auto, eDVBFrontendParametersSatellite.Pilot_Unknown, \
                -1, 0, 0,
		1388, 1388, _("Hispasat 30.0w")),
	]

	SAT_TABLE_FREQUENCY = 0
	SAT_TABLE_SYMBOLRATE = 1
	SAT_TABLE_POLARISATION = 2
	SAT_TABLE_FEC = 3
	SAT_TABLE_INVERSION = 4
	SAT_TABLE_ORBPOS = 5
	SAT_TABLE_SYSTEM = 6
	SAT_TABLE_MODULATION = 7
	SAT_TABLE_ROLLOFF = 8
	SAT_TABLE_PILOT = 9
	SAT_TABLE_ISID = 10
	SAT_TABLE_PLSMODE = 11
	SAT_TABLE_PLSCODE = 12
	SAT_TABLE_TSID = 13
	SAT_TABLE_ONID = 14
	SAT_TABLE_NAME = 15

	def __init__(self, session, feid, nr_of_ports, simple_tone, simple_sat_change):
		Screen.__init__(self, session)

		self["statusbar"] = StaticText(" ")
		self["tunerstatusbar"] = StaticText(" ")

		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session)

		self["config"].list = self.list
		self["config"].l.setList(self.list)

		self["key_red"] = StaticText(_("Abort"))

		self.session.pipshown = False
		self.index = 0
		self.port_index = 0
		self.feid = feid
		self.nr_of_ports = nr_of_ports
		self.simple_tone = simple_tone
		self.simple_sat_change = simple_sat_change
		self.found_sats = []

		if not self.openFrontend():
			self.oldref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
			self.session.nav.stopService()
			if not self.openFrontend():
				if self.session.pipshown:
					if hasattr(self.session, 'infobar'):
						if self.session.infobar.servicelist and self.session.infobar.servicelist.dopipzap:
							self.session.infobar.servicelist.togglePipzap()
					if hasattr(self.session, 'pip'):
						del self.session.pip
					self.session.pipshown = False
				if not self.openFrontend():
					self.frontend = None
					self.raw_channel = None

		if self.raw_channel:
			self.raw_channel.receivedTsidOnid.get().append(self.gotTsidOnid)

		self["actions"] = ActionMap(["SetupActions"],
		{
			"cancel": self.keyCancel,
		}, -2)

		self.count = 0
		self.state = 0
		self.abort = False

		self.statusTimer = eTimer()
		self.statusTimer.callback.append(self.statusCallback)
		self.tunerStatusTimer = eTimer()
		self.tunerStatusTimer.callback.append(self.tunerStatusCallback)
		self.startStatusTimer()
		self.onClose.append(self.__onClose)

	def __onClose(self):
		if self.raw_channel:
			self.raw_channel.receivedTsidOnid.get().remove(self.gotTsidOnid)

	def keyCancel(self):
		self.abort = True

	def keyOK(self):
		return

	def keyLeft(self):
		return

	def keyRight(self):
		return

	def openFrontend(self):
		res_mgr = eDVBResourceManager.getInstance()
		if res_mgr:
			self.raw_channel = res_mgr.allocateRawChannel(self.feid)
			if self.raw_channel:
				self.frontend = self.raw_channel.getFrontend()
				if self.frontend:
					return True
		return False

	def statusCallback(self):
		if self.state == 0:
			if self.port_index == 0:
				self.clearNimEntries()
				config.Nims[self.feid].dvbs.diseqcA.value = "%d" % (self.sat_frequencies[self.index][self.SAT_TABLE_ORBPOS])
			elif self.port_index == 1:
				self.clearNimEntries()
				config.Nims[self.feid].dvbs.diseqcB.value = "%d" % (self.sat_frequencies[self.index][self.SAT_TABLE_ORBPOS])
			elif self.port_index == 2:
				self.clearNimEntries()
				config.Nims[self.feid].dvbs.diseqcC.value = "%d" % (self.sat_frequencies[self.index][self.SAT_TABLE_ORBPOS])
			elif self.port_index == 3:
				self.clearNimEntries()
				config.Nims[self.feid].dvbs.diseqcD.value = "%d" % (self.sat_frequencies[self.index][self.SAT_TABLE_ORBPOS])

			if self.nr_of_ports == 4:
				config.Nims[self.feid].dvbs.diseqcMode.value = "diseqc_a_b_c_d"
			elif self.nr_of_ports == 2:
				config.Nims[self.feid].dvbs.diseqcMode.value = "diseqc_a_b"
			else:
				config.Nims[self.feid].dvbs.diseqcMode.value = "single"

			config.Nims[self.feid].dvbs.configMode.value = "simple"
			config.Nims[self.feid].dvbs.simpleDiSEqCSetVoltageTone = self.simple_tone
			config.Nims[self.feid].dvbs.simpleDiSEqCOnlyOnSatChange = self.simple_sat_change

			self.saveAndReloadNimConfig()
			self.state += 1

		elif self.state == 1:
			InitNimManager(nimmanager)

			self.tuner = Tuner(self.frontend)
			if self.raw_channel:
				self.raw_channel.requestTsidOnid()
			self.tuner.tune(self.sat_frequencies[self.index])

			self["statusbar"].setText(_("Checking tuner %d\nDiSEqC port %s for %s") % (self.feid, self.diseqc_ports[self.port_index], self.sat_frequencies[self.index][self.SAT_TABLE_NAME]))
			self["tunerstatusbar"].setText(" ")

			self.count = 0
			self.state = 0

			self.startTunerStatusTimer()
			return

		self.startStatusTimer()

	def startStatusTimer(self):
		self.statusTimer.start(100, True)

	def setupSave(self):
		self.clearNimEntries()
		for x in self.found_sats:
			if x[0] == "A":
				config.Nims[self.feid].dvbs.diseqcA.value = "%d" % (x[1])
			elif x[0] == "B":
				config.Nims[self.feid].dvbs.diseqcB.value = "%d" % (x[1])
			elif x[0] == "C":
				config.Nims[self.feid].dvbs.diseqcC.value = "%d" % (x[1])
			elif x[0] == "D":
				config.Nims[self.feid].dvbs.diseqcD.value = "%d" % (x[1])
		self.saveAndReloadNimConfig()

	def setupClear(self):
		self.clearNimEntries()
		self.saveAndReloadNimConfig()

	def clearNimEntries(self):
		config.Nims[self.feid].dvbs.diseqcA.value = "3601"
		config.Nims[self.feid].dvbs.diseqcB.value = "3601"
		config.Nims[self.feid].dvbs.diseqcC.value = "3601"
		config.Nims[self.feid].dvbs.diseqcD.value = "3601"

	def saveAndReloadNimConfig(self):
		config.Nims[self.feid].save()
		configfile.save()
		configfile.load()
		nimmanager.sec.update()

	def tunerStatusCallback(self):
		dict = {}
		if self.frontend:
			self.frontend.getFrontendStatus(dict)
		else:
			self.tunerStopScan(False)
			return
		if dict["tuner_state"] == "TUNING":
                        self["tunerstatusbar"].setText(_("Tuner status TUNING"))

		elif dict["tuner_state"] == "FAILED":
                        self["tunerstatusbar"].setText(_("Tuner status FAILED"))

		elif dict["tuner_state"] == "LOSTLOCK":
                        self["tunerstatusbar"].setText(_("Tuner status LOSTLOCK"))

		elif dict["tuner_state"] == "LOCKED":
                        self["tunerstatusbar"].setText(_("Tuner status LOCKED"))

		elif dict["tuner_state"] == "IDLE":
                        self["tunerstatusbar"].setText(_("Tuner status IDLE"))

		elif dict["tuner_state"] == "UNKNOWN":
                        self["tunerstatusbar"].setText(_("Tuner status UNKNOWN"))
			
		if dict["tuner_state"] == "LOSTLOCK" or dict["tuner_state"] == "FAILED":
			self.tunerStopScan(False)
			return

		self.count += 1
		if self.count > 10:
			self.tunerStopScan(False)
		else:
			self.startTunerStatusTimer()

	def startTunerStatusTimer(self):
		self.tunerStatusTimer.start(1000, True)

	def gotTsidOnid(self, tsid, onid):
		self.tunerStatusTimer.stop()
		if tsid == self.sat_frequencies[self.index][self.SAT_TABLE_TSID] and onid == self.sat_frequencies[self.index][self.SAT_TABLE_ONID]:
			self.tunerStopScan(True)
		else:
			self.tunerStopScan(False)

	def tunerStopScan(self, result):
		if self.abort:
			self.setupClear()
			self.close(False)
			return
		if result:
			self.found_sats.append((self.diseqc_ports[self.port_index], self.sat_frequencies[self.index][self.SAT_TABLE_ORBPOS], self.sat_frequencies[self.index][self.SAT_TABLE_NAME]))
			self.index = 0
			self.port_index += 1
		else:
			self.index += 1
			if len(self.sat_frequencies) == self.index:
				self.index = 0
				self.port_index += 1

		if len(self.found_sats) > 0:
			self.list = []
			for x in self.found_sats:
				self.list.append(getConfigListEntry((_("DiSEqC port %s: %s") % (x[0], x[2]))))
			self["config"].l.setList(self.list)

		if self.nr_of_ports == self.port_index:
			self.state = 99
			self.setupSave()
			self.close(len(self.found_sats) > 0)
			return

		for x in self.found_sats:
			if x[1] == self.sat_frequencies[self.index][self.SAT_TABLE_ORBPOS]:
				self.tunerStopScan(False)
				return

		self.startStatusTimer()

from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.config import config, configfile, ConfigNothing
from Components.NimManager import nimmanager, InitNimManager
from Components.TuneTest import Tuner
from enigma import eDVBFrontendParametersSatellite, eDVBResourceManager, eTimer


class AutoDiseqc(ConfigListScreen, Screen):
	diseqc_ports = [
		"A", "B", "C", "D"
	]

	universal_central_sats_frequencies = [
		# Hotbird 13.0E Rai 1
		(
			10992,
			27500,
			eDVBFrontendParametersSatellite.Polarisation_Vertical,
			eDVBFrontendParametersSatellite.FEC_2_3,
			eDVBFrontendParametersSatellite.Inversion_Off,
			130,
			eDVBFrontendParametersSatellite.System_DVB_S,
			eDVBFrontendParametersSatellite.Modulation_Auto,
			eDVBFrontendParametersSatellite.RollOff_auto,
			eDVBFrontendParametersSatellite.Pilot_Unknown,
			eDVBFrontendParametersSatellite.No_Stream_Id_Filter,
			eDVBFrontendParametersSatellite.PLS_Gold,
			eDVBFrontendParametersSatellite.PLS_Default_Gold_Code,
			eDVBFrontendParametersSatellite.No_T2MI_PLP_Id,
			eDVBFrontendParametersSatellite.T2MI_Default_Pid,
			12400,
			318,
			"Hotbird 13.0°E"
		),
		# Astra 19.2E ZDF
		(
			11954,
			27500,
			eDVBFrontendParametersSatellite.Polarisation_Horizontal,
			eDVBFrontendParametersSatellite.FEC_3_4,
			eDVBFrontendParametersSatellite.Inversion_Off,
			192,
			eDVBFrontendParametersSatellite.System_DVB_S,
			eDVBFrontendParametersSatellite.Modulation_Auto,
			eDVBFrontendParametersSatellite.RollOff_auto,
			eDVBFrontendParametersSatellite.Pilot_Unknown,
			eDVBFrontendParametersSatellite.No_Stream_Id_Filter,
			eDVBFrontendParametersSatellite.PLS_Gold,
			eDVBFrontendParametersSatellite.PLS_Default_Gold_Code,
			eDVBFrontendParametersSatellite.No_T2MI_PLP_Id,
			eDVBFrontendParametersSatellite.T2MI_Default_Pid,
			1079,
			1,
			"Astra 1 19.2°E"
		),
		# Astra 23.5E Astra SES
		(
			12168,
			27500,
			eDVBFrontendParametersSatellite.Polarisation_Vertical,
			eDVBFrontendParametersSatellite.FEC_3_4,
			eDVBFrontendParametersSatellite.Inversion_Off,
			235,
			eDVBFrontendParametersSatellite.System_DVB_S,
			eDVBFrontendParametersSatellite.Modulation_Auto,
			eDVBFrontendParametersSatellite.RollOff_auto,
			eDVBFrontendParametersSatellite.Pilot_Unknown,
			eDVBFrontendParametersSatellite.No_Stream_Id_Filter,
			eDVBFrontendParametersSatellite.PLS_Gold,
			eDVBFrontendParametersSatellite.PLS_Default_Gold_Code,
			eDVBFrontendParametersSatellite.No_T2MI_PLP_Id,
			eDVBFrontendParametersSatellite.T2MI_Default_Pid,
			3224,
			3,
			"Astra 3 23.5°E"
		),
		# Astra 28.2E EPG background audio
		(
			11778,
			27500,
			eDVBFrontendParametersSatellite.Polarisation_Vertical,
			eDVBFrontendParametersSatellite.FEC_2_3,
			eDVBFrontendParametersSatellite.Inversion_Off,
			282,
			eDVBFrontendParametersSatellite.System_DVB_S,
			eDVBFrontendParametersSatellite.Modulation_Auto,
			eDVBFrontendParametersSatellite.RollOff_auto,
			eDVBFrontendParametersSatellite.Pilot_Unknown,
			eDVBFrontendParametersSatellite.No_Stream_Id_Filter,
			eDVBFrontendParametersSatellite.PLS_Gold,
			eDVBFrontendParametersSatellite.PLS_Default_Gold_Code,
			eDVBFrontendParametersSatellite.No_T2MI_PLP_Id,
			eDVBFrontendParametersSatellite.T2MI_Default_Pid,
			2004,
			2,
			"Astra 2 28.2°E"
		),
	]

	universal_east_sats_frequencies = [
		# Astra 4A 4.8 Home 3
		(
			11785,
			27500,
			eDVBFrontendParametersSatellite.Polarisation_Vertical,
			eDVBFrontendParametersSatellite.FEC_5_6,
			eDVBFrontendParametersSatellite.Inversion_Off,
			48,
			eDVBFrontendParametersSatellite.System_DVB_S2,
			eDVBFrontendParametersSatellite.Modulation_8PSK,
			eDVBFrontendParametersSatellite.RollOff_auto,
			eDVBFrontendParametersSatellite.Pilot_Unknown,
			eDVBFrontendParametersSatellite.No_Stream_Id_Filter,
			eDVBFrontendParametersSatellite.PLS_Gold,
			eDVBFrontendParametersSatellite.PLS_Default_Gold_Code,
			eDVBFrontendParametersSatellite.No_T2MI_PLP_Id,
			eDVBFrontendParametersSatellite.T2MI_Default_Pid,
			201,
			85,
			"Astra 4A 4.8°E"
		),
		# Eutelsat 9.0E CCTV 4 Europe
		(
			11996,
			27500,
			eDVBFrontendParametersSatellite.Polarisation_Vertical,
			eDVBFrontendParametersSatellite.FEC_3_4,
			eDVBFrontendParametersSatellite.Inversion_Off,
			90,
			eDVBFrontendParametersSatellite.System_DVB_S,
			eDVBFrontendParametersSatellite.Modulation_Auto,
			eDVBFrontendParametersSatellite.RollOff_auto,
			eDVBFrontendParametersSatellite.Pilot_Unknown,
			eDVBFrontendParametersSatellite.No_Stream_Id_Filter,
			eDVBFrontendParametersSatellite.PLS_Gold,
			eDVBFrontendParametersSatellite.PLS_Default_Gold_Code,
			eDVBFrontendParametersSatellite.No_T2MI_PLP_Id,
			eDVBFrontendParametersSatellite.T2MI_Default_Pid,
			1,
			1,
			"Eutelsat 9B 9.0°E"
		),
		# Eutelsat 16.0E CGTN
		(
			11595,
			30000,
			eDVBFrontendParametersSatellite.Polarisation_Horizontal,
			eDVBFrontendParametersSatellite.FEC_3_4,
			eDVBFrontendParametersSatellite.Inversion_Off,
			160,
			eDVBFrontendParametersSatellite.System_DVB_S2,
			eDVBFrontendParametersSatellite.Modulation_8PSK,
			eDVBFrontendParametersSatellite.RollOff_auto,
			eDVBFrontendParametersSatellite.Pilot_Unknown,
			eDVBFrontendParametersSatellite.No_Stream_Id_Filter,
			eDVBFrontendParametersSatellite.PLS_Gold,
			eDVBFrontendParametersSatellite.PLS_Default_Gold_Code,
			eDVBFrontendParametersSatellite.No_T2MI_PLP_Id,
			eDVBFrontendParametersSatellite.T2MI_Default_Pid,
			2,
			64,
			"Eutelsat 16A 16.0°E"
		),

	]

	universal_west_sats_frequencies = [
		# Thor 0.8W Sky News
		(
			12418,
			28000,
			eDVBFrontendParametersSatellite.Polarisation_Vertical,
			eDVBFrontendParametersSatellite.FEC_7_8,
			eDVBFrontendParametersSatellite.Inversion_Off,
			3592,
			eDVBFrontendParametersSatellite.System_DVB_S,
			eDVBFrontendParametersSatellite.Modulation_Auto,
			eDVBFrontendParametersSatellite.RollOff_auto,
			eDVBFrontendParametersSatellite.Pilot_Unknown,
			eDVBFrontendParametersSatellite.No_Stream_Id_Filter,
			eDVBFrontendParametersSatellite.PLS_Gold,
			eDVBFrontendParametersSatellite.PLS_Default_Gold_Code,
			eDVBFrontendParametersSatellite.No_T2MI_PLP_Id,
			eDVBFrontendParametersSatellite.T2MI_Default_Pid,
			20,
			70,
			"Thor 5/6/7 0.8°W"
		),
		# Eutelsat 5.0W Fransat
		(
			11054,
			29950,
			eDVBFrontendParametersSatellite.Polarisation_Vertical,
			eDVBFrontendParametersSatellite.FEC_2_3,
			eDVBFrontendParametersSatellite.Inversion_Off,
			3550,
			eDVBFrontendParametersSatellite.System_DVB_S2,
			eDVBFrontendParametersSatellite.Modulation_8PSK,
			eDVBFrontendParametersSatellite.RollOff_auto,
			eDVBFrontendParametersSatellite.Pilot_Unknown,
			eDVBFrontendParametersSatellite.No_Stream_Id_Filter,
			eDVBFrontendParametersSatellite.PLS_Gold,
			eDVBFrontendParametersSatellite.PLS_Default_Gold_Code,
			eDVBFrontendParametersSatellite.No_T2MI_PLP_Id,
			eDVBFrontendParametersSatellite.T2MI_Default_Pid,
			20500,
			1375,
			"Eutelsat 5 West B 5.0°W"
		),
		# Hispasat 30.0W TVI
		(
			10770,
			30000,
			eDVBFrontendParametersSatellite.Polarisation_Horizontal,
			eDVBFrontendParametersSatellite.FEC_5_6,
			eDVBFrontendParametersSatellite.Inversion_Off,
			3300,
			eDVBFrontendParametersSatellite.System_DVB_S2,
			eDVBFrontendParametersSatellite.Modulation_8PSK,
			eDVBFrontendParametersSatellite.RollOff_auto,
			eDVBFrontendParametersSatellite.Pilot_Unknown,
			eDVBFrontendParametersSatellite.No_Stream_Id_Filter,
			eDVBFrontendParametersSatellite.PLS_Gold,
			eDVBFrontendParametersSatellite.PLS_Default_Gold_Code,
			eDVBFrontendParametersSatellite.No_T2MI_PLP_Id,
			eDVBFrontendParametersSatellite.T2MI_Default_Pid,
			6,
			6,
			"Hispasat 30.0°W"
		),
	]

	circular_sats_frequencies = [
		# Express AMU1 36.0E NTV Plus
		(
			11785,
			27500,
			eDVBFrontendParametersSatellite.Polarisation_CircularRight,
			eDVBFrontendParametersSatellite.FEC_3_4,
			eDVBFrontendParametersSatellite.Inversion_Off,
			360,
			eDVBFrontendParametersSatellite.System_DVB_S2,
			eDVBFrontendParametersSatellite.Modulation_8PSK,
			eDVBFrontendParametersSatellite.RollOff_auto,
			eDVBFrontendParametersSatellite.Pilot_Unknown,
			eDVBFrontendParametersSatellite.No_Stream_Id_Filter,
			eDVBFrontendParametersSatellite.PLS_Gold,
			eDVBFrontendParametersSatellite.PLS_Default_Gold_Code,
			eDVBFrontendParametersSatellite.No_T2MI_PLP_Id,
			eDVBFrontendParametersSatellite.T2MI_Default_Pid,
			13,
			112,
			"Express AMU1 36.0°E"
		),
		# Express AT1 56.0E NTV Plus Vostok
		(
			12054,
			27500,
			eDVBFrontendParametersSatellite.Polarisation_CircularRight,
			eDVBFrontendParametersSatellite.FEC_3_4,
			eDVBFrontendParametersSatellite.Inversion_Off,
			560,
			eDVBFrontendParametersSatellite.System_DVB_S2,
			eDVBFrontendParametersSatellite.Modulation_8PSK,
			eDVBFrontendParametersSatellite.RollOff_auto,
			eDVBFrontendParametersSatellite.Pilot_Unknown,
			eDVBFrontendParametersSatellite.No_Stream_Id_Filter,
			eDVBFrontendParametersSatellite.PLS_Gold,
			eDVBFrontendParametersSatellite.PLS_Default_Gold_Code,
			eDVBFrontendParametersSatellite.No_T2MI_PLP_Id,
			eDVBFrontendParametersSatellite.T2MI_Default_Pid,
			566,
			112,
			"Express AT1 56.0°E"
		),
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
	SAT_TABLE_IS_ID = 10
	SAT_TABLE_PLS_MODE = 11
	SAT_TABLE_PLS_CODE = 12
	SAT_TABLE_T2MI_PLP_ID = 13
	SAT_TABLE_T2MI_PID = 14
	SAT_TABLE_TSID = 15
	SAT_TABLE_ONID = 16
	SAT_TABLE_NAME = 17

	def __init__(self, session, feid, nr_of_ports, simple_tone, simple_sat_change, order="all"):
		Screen.__init__(self, session)

		self["statusbar"] = StaticText(" ")
		self["tunerstatusbar"] = StaticText(" ")

		ConfigListScreen.__init__(self, [], session=session)

		self["key_red"] = StaticText(_("Abort"))

		self.session.pipshown = False
		self.index = 0
		self.port_index = 0
		self.feid = feid
		self.nr_of_ports = nr_of_ports
		self.simple_tone = simple_tone
		self.simple_sat_change = simple_sat_change
		self.found_sats = []
		self.circular_setup = 0
		if order == "all":
			self.sat_frequencies = self.universal_central_sats_frequencies[:] + self.universal_east_sats_frequencies[:] + self.universal_west_sats_frequencies[:]
			if nr_of_ports == 1:
				self.sat_frequencies += self.circular_sats_frequencies[:]
		elif order == "astra":
			self.sat_frequencies = self.universal_central_sats_frequencies[:]
		elif order == "east":
			self.sat_frequencies = self.universal_central_sats_frequencies[:] + self.universal_east_sats_frequencies[:]
			if nr_of_ports == 1:
				self.sat_frequencies += self.circular_sats_frequencies[:]
		elif order == "west":
			self.sat_frequencies = self.universal_west_sats_frequencies[:]
		elif order == "circular":
			self.sat_frequencies = self.circular_sats_frequencies[:]

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

		self.diseqc = [
			config.Nims[self.feid].dvbs.diseqcA.value,
			config.Nims[self.feid].dvbs.diseqcB.value,
			config.Nims[self.feid].dvbs.diseqcC.value,
			config.Nims[self.feid].dvbs.diseqcD.value,
		]

		self.statusTimer = eTimer()
		self.statusTimer.callback.append(self.statusCallback)
		self.waitCloseTimer = eTimer()
		self.waitCloseTimer.callback.append(self.waitClose)
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
			if self.port_index == 0 and self.diseqc[0] == 3600:
				self.clearNimEntries()
				config.Nims[self.feid].dvbs.diseqcA.value = int(self.sat_frequencies[self.index][self.SAT_TABLE_ORBPOS])
			elif self.port_index == 1 and self.diseqc[1] == 3600:
				self.clearNimEntries()
				config.Nims[self.feid].dvbs.diseqcB.value = int(self.sat_frequencies[self.index][self.SAT_TABLE_ORBPOS])
			elif self.port_index == 2 and self.diseqc[2] == 3600:
				self.clearNimEntries()
				config.Nims[self.feid].dvbs.diseqcC.value = int(self.sat_frequencies[self.index][self.SAT_TABLE_ORBPOS])
			elif self.port_index == 3 and self.diseqc[3] == 3600:
				self.clearNimEntries()
				config.Nims[self.feid].dvbs.diseqcD.value = int(self.sat_frequencies[self.index][self.SAT_TABLE_ORBPOS])

			if self.nr_of_ports == 4:
				config.Nims[self.feid].dvbs.diseqcMode.value = "diseqc_a_b_c_d"
			elif self.nr_of_ports == 2:
				config.Nims[self.feid].dvbs.diseqcMode.value = "diseqc_a_b"
			else:
				config.Nims[self.feid].dvbs.diseqcMode.value = "single"
				if self.sat_frequencies[self.index][self.SAT_TABLE_ORBPOS] == 360 and not self.found_sats:
					config.Nims[self.feid].dvbs.simpleDiSEqCSetCircularLNB.value = True
					self.circular_setup = 1
				if self.sat_frequencies[self.index][self.SAT_TABLE_ORBPOS] == 560 and not self.found_sats:
					config.Nims[self.feid].dvbs.simpleDiSEqCSetCircularLNB.value = True
					self.circular_setup = 2

			config.Nims[self.feid].dvbs.configMode.value = "simple"
			config.Nims[self.feid].dvbs.simpleDiSEqCSetVoltageTone = self.simple_tone
			config.Nims[self.feid].dvbs.simpleDiSEqCOnlyOnSatChange = self.simple_sat_change

			self.saveAndReloadNimConfig()
			self.state += 1

		elif self.state == 1:
			if self.diseqc[self.port_index] != 3600:
				self.statusTimer.stop()
				self.count = 0
				self.state = 0
				self.index = len(self.sat_frequencies) - 1
				self.tunerStopScan(False)
				return

			if self.circular_setup == 1:
				if self.raw_channel:
					self.raw_channel.receivedTsidOnid.get().remove(self.gotTsidOnid)
				del self.frontend
				del self.raw_channel
				if not self.openFrontend():
					self.frontend = None
					self.raw_channel = None
				if self.raw_channel:
					self.raw_channel.receivedTsidOnid.get().append(self.gotTsidOnid)

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
				config.Nims[self.feid].dvbs.diseqcA.value = int(x[1])
			elif x[0] == "B":
				config.Nims[self.feid].dvbs.diseqcB.value = int(x[1])
			elif x[0] == "C":
				config.Nims[self.feid].dvbs.diseqcC.value = int(x[1])
			elif x[0] == "D":
				config.Nims[self.feid].dvbs.diseqcD.value = int(x[1])
		self.saveAndReloadNimConfig()

	def setupClear(self):
		self.clearNimEntries()
		self.saveAndReloadNimConfig()

	def clearNimEntries(self):
		config.Nims[self.feid].dvbs.diseqcA.value = 3601 if self.diseqc[0] == 3600 else self.diseqc[0]
		config.Nims[self.feid].dvbs.diseqcB.value = 3601 if self.diseqc[1] == 3600 else self.diseqc[1]
		config.Nims[self.feid].dvbs.diseqcC.value = 3601 if self.diseqc[2] == 3600 else self.diseqc[2]
		config.Nims[self.feid].dvbs.diseqcD.value = 3601 if self.diseqc[3] == 3600 else self.diseqc[3]

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

		if dict["tuner_state"] in ("LOSTLOCK", "FAILED"):
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

	def waitClose(self):
		self.close(len(self.found_sats) > 0)

	def tunerStopScan(self, result):
		if self.waitCloseTimer.isActive():
			return

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
			lst = []
			for x in self.found_sats:
				lst.append((_("DiSEqC port %s: %s") % (x[0], x[2]), ConfigNothing()))
			self["config"].list = lst
			self["config"].setCurrentIndex(len(self.found_sats) - 1)

		if self.nr_of_ports == self.port_index:
			self.state = 99
			self.setupSave()
			if len(self.found_sats) > 0:
				self.waitCloseTimer.start(4000, True)
			else:
				self.close(False)
			return

		for x in self.found_sats:
			if x[1] == self.sat_frequencies[self.index][self.SAT_TABLE_ORBPOS]:
				self.tunerStopScan(False)
				return

		self.startStatusTimer()

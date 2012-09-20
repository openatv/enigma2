from Screens.Satconfig import NimSelection
from Screens.Screen import Screen
from Plugins.Plugin import PluginDescriptor
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import ActionMap, NumberActionMap
from Components.ResourceManager import resourcemanager
from Components.Sources.FrontendStatus import FrontendStatus
from Components.Sources.StaticText import StaticText
from Components.config import config, configfile, getConfigListEntry, ConfigSelection, ConfigYesNo
from Components.NimManager import nimmanager, InitNimManager
from Components.TuneTest import Tuner
from enigma import eDVBFrontendParametersSatellite, eDVBFrontendParameters, eDVBResourceManager, eTimer


class AutoDiseqc(Screen, ConfigListScreen):
	def __init__(self, session, args = None):
		Screen.__init__(self, session)

		self.tuner_idx = args
		self.list = []
		ConfigListScreen.__init__(self, self.list)

		self.enabled = ConfigYesNo(default = True)
		diseqc_modes = {2: _("diseqc_a_b"), 4: _("diseqc_a_b_c_d")}
		self.menu_type = ConfigSelection(choices = diseqc_modes, default = 2)
		self.simple_tone = ConfigYesNo(True)
		self.simple_sat_change = ConfigYesNo(False)

		self.createMenu()
		
	def createMenu(self):
		self.list = []
		self.list.append(getConfigListEntry(_("Use AutoDiseqc"), self.enabled))
		if self.enabled.value:
			self.list.append(getConfigListEntry(_("Diseqc mode"), self.menu_type))
			self.list.append(getConfigListEntry(_("Set Voltage and 22KHz"), self.simple_tone))
			self.list.append(getConfigListEntry(_("Send DiSEqC only on satellite change"), self.simple_sat_change))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.createMenu()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.createMenu()

	def run(self):
		if self.enabled.value:
			self.session.open(AutoDiseqcRun, self.tuner_idx, self.menu_type.value, self.simple_tone, self.simple_sat_change)


class AutoDiseqcWorker(Screen):
	skin = """
	<screen position="c-250,c-100" size="500,120" title=" ">
		<widget source="statusbar" render="Label" position="c-490,e-100" zPosition="10" size="e-10,e-40" halign="center" valign="center" font="Regular;22" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
	</screen>"""

	def __init__(self, session, frontend, raw_channel, transponder, name, tuner_idx, port):
		self.skin = AutoDiseqcWorker.skin
		Screen.__init__(self, session)

		self["statusbar"] = StaticText( _("AutoDiseqc tesing %s\n\nTuner %d port %s") % (name, tuner_idx, port))

		self.statusTimer = eTimer()
		self.statusTimer.callback.append(self.statusCallback)
		self.statusTimer.start(2500)

		self.frontend = frontend
		self.raw_channel = raw_channel

		InitNimManager(nimmanager)

		self.tuner = Tuner(self.frontend)

		self.transponder = (( \
			transponder[0], transponder[1], transponder[2], transponder[3], \
			transponder[4], transponder[5], transponder[6], transponder[7], \
			transponder[8], transponder[9], -1, -1))

		self.tsid = transponder[10]
		self.onid = transponder[11]
		self.tuner.tune(self.transponder)

		self.setTitle(" ")

	def statusCallback(self):
		dict = {}
		self.frontend.getFrontendStatus(dict)
		if dict["tuner_state"] == "LOCKED":
			self.raw_channel.requestTsidOnid(self.gotTsidOnid)

		if dict["tuner_state"] == "LOSTLOCK" or dict["tuner_state"] == "FAILED":
			self.close(False)

	def gotTsidOnid(self, tsid, onid):
		if tsid == self.tsid and onid == self.onid:
			self.close(True)
		else:
			self.close(False)


class AutoDiseqcRun(Screen):
	skin = """
	<screen position="c-250,c-100" size="500,120" title=" ">
		<widget source="statusbar" render="Label" position="c-490,e-100" zPosition="10" size="e-10,e-40" halign="center" valign="center" font="Regular;22" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
	</screen>"""

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
		1079, 1, \
		"192", "Astra 1 19.2e"),

		# astra 235 astra ses
		( 12168, 27500, \
		eDVBFrontendParametersSatellite.Polarisation_Vertical, eDVBFrontendParametersSatellite.FEC_3_4, \
		eDVBFrontendParametersSatellite.Inversion_Off, 235, \
		eDVBFrontendParametersSatellite.System_DVB_S, eDVBFrontendParametersSatellite.Modulation_Auto, \
		eDVBFrontendParametersSatellite.RollOff_auto, eDVBFrontendParametersSatellite.Pilot_Unknown, \
		3224, 3, \
		"235", "Astra 3 23.5e"),

		# astra 282 bbc
		( 10776, 22000, \
		eDVBFrontendParametersSatellite.Polarisation_Horizontal, eDVBFrontendParametersSatellite.FEC_Auto, \
		eDVBFrontendParametersSatellite.Inversion_Unknown, 282, \
		eDVBFrontendParametersSatellite.System_DVB_S, eDVBFrontendParametersSatellite.Modulation_Auto, \
		eDVBFrontendParametersSatellite.RollOff_auto, eDVBFrontendParametersSatellite.Pilot_Unknown, \
		2045, 2, \
		"282", "Astra 2 28.2e"),

		# hotbird 130 rai
		( 10992, 27500, \
		eDVBFrontendParametersSatellite.Polarisation_Vertical, eDVBFrontendParametersSatellite.FEC_2_3, \
		eDVBFrontendParametersSatellite.Inversion_Off, 130, \
		eDVBFrontendParametersSatellite.System_DVB_S, eDVBFrontendParametersSatellite.Modulation_Auto, \
		eDVBFrontendParametersSatellite.RollOff_auto, eDVBFrontendParametersSatellite.Pilot_Unknown, \
		12400, 318, \
		"130", "Hotbird 13.0e"),
	]

	def __init__(self, session, feid, nr_of_ports, simple_tone, simple_sat_change):
		self.skin = AutoDiseqcRun.skin
		Screen.__init__(self, session)

		self["statusbar"] = StaticText(" ")

		self.index = 0
		self.port_index = 0
		self.feid = feid
		self.nr_of_ports = nr_of_ports
		self.simple_tone = simple_tone
		self.simple_sat_change = simple_sat_change
		self.found_sats = []

		if not self.openFrontend():
			self.oldref = self.session.nav.getCurrentlyPlayingServiceReference()
			self.session.nav.stopService()
			if not self.openFrontend():
				if self.session.pipshown:
					self.session.pipshown = False
					del self.session.pip
					if not self.openFrontend():
						self.frontend = None
		self.frontend.closeFrontend()

		self["actions"] = ActionMap(["SetupActions"],
		{
			"ok": self.keyGo,
		}, -2)

		self.state = 0
		self.statusTimer = eTimer()
		self.statusTimer.callback.append(self.statusCallback)
		self.statusTimer.start(10)

	def keyGo(self):
		if self.state == 99:
			self.close()

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
				config.Nims[self.feid].diseqcA.value = self.sat_frequencies[self.index][12]
				config.Nims[self.feid].diseqcB.value = '0'
				if self.nr_of_ports == 4:
					config.Nims[self.feid].diseqcC.value = '0'
					config.Nims[self.feid].diseqcD.value = '0'
			elif self.port_index == 1:
				config.Nims[self.feid].diseqcA.value = '0'
				config.Nims[self.feid].diseqcB.value = self.sat_frequencies[self.index][12]
				if self.nr_of_ports == 4:
					config.Nims[self.feid].diseqcC.value = '0'
					config.Nims[self.feid].diseqcD.value = '0'
			elif self.port_index == 2:
				config.Nims[self.feid].diseqcA.value = '0'
				config.Nims[self.feid].diseqcB.value = '0'
				config.Nims[self.feid].diseqcC.value = self.sat_frequencies[self.index][12]
				config.Nims[self.feid].diseqcD.value = '0'
			elif self.port_index == 3:
				config.Nims[self.feid].diseqcA.value = '0'
				config.Nims[self.feid].diseqcB.value = '0'
				config.Nims[self.feid].diseqcC.value = '0'
				config.Nims[self.feid].diseqcD.value = self.sat_frequencies[self.index][12]

			if self.nr_of_ports == 4:
				config.Nims[self.feid].diseqcMode.value = "diseqc_a_b_c_d"
			else:
				config.Nims[self.feid].diseqcMode.value = "diseqc_a_b"

			config.Nims[self.feid].configMode.value = "simple"
			config.Nims[self.feid].simpleDiSEqCSetVoltageTone = self.simple_tone
			config.Nims[self.feid].simpleDiSEqCOnlyOnSatChange = self.simple_sat_change

			config.Nims[self.feid].save()
			configfile.save()
			configfile.load()
			self.state += 1

		elif self.state == 1:
			if self.openFrontend():
				self.state += 1

		elif self.state == 2:
			self.statusTimer.stop()
			self.session.openWithCallback(self.tuneCallback, AutoDiseqcWorker, \
				self.frontend, self.raw_channel, self.sat_frequencies[self.index], \
				self.sat_frequencies[self.index][13], self.feid, self.diseqc_ports[self.port_index])
			self.state = 0
			return

		self.statusTimer.start(10)

	def tuneCallback(self, ret):
		if ret:
			self.found_sats.append((self.diseqc_ports[self.port_index], self.sat_frequencies[self.index][12]))
			self.index = len(self.sat_frequencies)
		else:
			self.index += 1

		if len(self.sat_frequencies) == self.index:
			self.index = 0
			self.port_index += 1

		self.frontend.closeFrontend()

		if self.nr_of_ports == self.port_index:
			self.setupConfig()
			self.state = 99
			return

		for x in self.found_sats:
			if x[1] == self.sat_frequencies[self.index][12]:
				self.tuneCallback(False)

		self.statusTimer.start(10)

	def setupConfig(self):
		if self.nr_of_ports == len(self.found_sats):
			if self.feid == 0:
				config.misc.startwizard.autodiseqc_a.value = True
			elif self.feid == 1:
				config.misc.startwizard.autodiseqc_b.value = True
			elif self.feid == 2:
				config.misc.startwizard.autodiseqc_c.value = True
			elif self.feid == 3:
				config.misc.startwizard.autodiseqc_d.value = True

			for x in self.found_sats:
				if x[0] == 'A':
					config.Nims[self.feid].diseqcA.value = x[1]
				elif x[0] == 'B':
					config.Nims[self.feid].diseqcB.value = x[1]
				elif x[0] == 'C':
					config.Nims[self.feid].diseqcC.value = x[1]
				elif x[0] == 'D':
					config.Nims[self.feid].diseqcD.value = x[1]
			self["statusbar"].setText( _("AutoDiseqc finished\n\nPlease press OK to continue"))
		else:
			config.Nims[self.feid].diseqcA.value = '0'
			config.Nims[self.feid].diseqcB.value = '0'
			if self.nr_of_ports == 4:
				config.Nims[self.feid].diseqcC.value = '0'
				config.Nims[self.feid].diseqcD.value = '0'
			config.Nims[self.feid].diseqcMode.value = "diseqc_a_b"
			config.Nims[self.feid].configMode.value = "nothing"
			config.Nims[self.feid].simpleDiSEqCSetVoltageTone.value = True
			config.Nims[self.feid].simpleDiSEqCOnlyOnSatChange.value = False
			self["statusbar"].setText( _("AutoDiseqc failed\nFound only %d position(s) of %d total\nPlease press OK to continue") % (len(self.found_sats), self.nr_of_ports))

		config.Nims[self.feid].save()
		configfile.save()
		configfile.load()

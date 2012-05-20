from Plugins.Plugin import PluginDescriptor

from Screens.Screen import Screen
from Screens.ServiceScan import ServiceScan
from Screens.MessageBox import MessageBox
from Screens.DefaultWizard import DefaultWizard

from Components.Label import Label
from Components.TuneTest import Tuner
from Components.ConfigList import ConfigListScreen
from Components.Sources.StaticText import StaticText
from Components.ActionMap import NumberActionMap, ActionMap
from Components.NimManager import nimmanager, getConfigSatlist
from Components.config import config, ConfigSubsection, ConfigSelection, ConfigYesNo, ConfigInteger, getConfigListEntry, ConfigSlider, ConfigEnableDisable
from Components.Sources.Boolean import Boolean
from Components.Sources.StaticText import StaticText
from Components.Pixmap import Pixmap

from Tools.HardwareInfo import HardwareInfo
from Tools.Directories import resolveFilename, SCOPE_DEFAULTPARTITIONMOUNTDIR, SCOPE_DEFAULTDIR, SCOPE_DEFAULTPARTITION

from enigma import eTimer, eDVBFrontendParametersSatellite, eComponentScan, eDVBSatelliteEquipmentControl, eDVBFrontendParametersTerrestrial, eDVBFrontendParametersCable, eConsoleAppContainer, eDVBResourceManager

#used for the XML file
from time import strftime, time
from Components.About import about
XML_BLINDSCAN_DIR = "/tmp"

class Blindscan(ConfigListScreen, Screen):
	skin="""
		<screen name="Blindscan" position="center,center" size="560,290" title="Blindscan">
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="config" position="5,50" size="550,200" scrollbarMode="showOnDemand" />
			<widget name="introduction" position="0,265" size="560,20" font="Regular;20" halign="center" />
		</screen>
		"""
	def __init__(self, session):
		Screen.__init__(self, session)
		self.setup_title = _("Blindscan")
		Screen.setTitle(self, _(self.setup_title))
		self.skinName = "Setup"
		self.current_play_service = self.session.nav.getCurrentlyPlayingServiceReference()

		self.onChangedEntry = [ ]
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["VKeyIcon"] = Boolean(False)
		self['footnote'] = Label("")
		self["status"] = StaticText()

		# update sat list
		self.satList = []
		for slot in nimmanager.nim_slots:
			if slot.isCompatible("DVB-S"):
				self.satList.append(nimmanager.getSatListForNim(slot.slot))
			else:
				self.satList.append(None)

		# make config
		self.createConfig()

		self.list = []
		self.status = ""

		ConfigListScreen.__init__(self, self.list)
		if self.scan_nims.value != None and self.scan_nims.value != "" :
			self["actions"] = ActionMap(["ColorActions", "SetupActions", 'DirectionActions'],
			{
				"red": self.keyCancel,
				"green": self.keyGo,
				"ok": self.keyGo,
				"cancel": self.keyCancel,
			}, -2)
			self["key_red"] = StaticText(_("Exit"))
			self["key_green"] = StaticText(_("Scan"))
			self["introduction"] = Label(_("Press Green/OK to start the scan"))
			self.createSetup()
		else :
			self["actions"] = ActionMap(["ColorActions", "SetupActions", 'DirectionActions'],
			{
				"red": self.keyCancel,
				"green": self.keyNone,
				"ok": self.keyNone,
				"cancel": self.keyCancel,
			}, -2)
			self["key_red"] = StaticText(_("Exit"))
			self["key_green"] = StaticText(" ")
			self["introduction"] = Label(_("Please setup your tuner configuration."))

		self.i2c_mapping_table = None
		self.makeNimSocket()

		if not self.selectionChanged in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def selectionChanged(self):
 		self["status"].setText(self["config"].getCurrent()[2])

	# for summary:
	def changedEntry(self):
		for x in self.onChangedEntry:
			x()
	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]
	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())
	def createSummary(self):
		from Screens.Setup import SetupSummary
		return SetupSummary


	def makeNimSocket(self):
		self.i2c_mapping_table = {0:2, 1:3, 2:1, 3:0}

	def getNimSocket(self, slot_number):
		if slot_number < 0 or slot_number > 3:
			return -1
		return self.i2c_mapping_table[slot_number]

	def keyNone(self):
		None

	def callbackNone(self, *retval):
		None

	def openFrontend(self):
		res_mgr = eDVBResourceManager.getInstance()
		if res_mgr:
			self.raw_channel = res_mgr.allocateRawChannel(self.feid)
			if self.raw_channel:
				self.frontend = self.raw_channel.getFrontend()
				if self.frontend:
					return True
				else:
					print "getFrontend failed"
			else:
				print "getRawChannel failed"
		else:
			print "getResourceManager instance failed"
		return False

	def createConfig(self):
		self.feinfo = None
		frontendData = None
		defaultSat = {
			"orbpos": 192,
			"system": eDVBFrontendParametersSatellite.System_DVB_S,
			"frequency": 11836,
			"inversion": eDVBFrontendParametersSatellite.Inversion_Unknown,
			"symbolrate": 27500,
			"polarization": eDVBFrontendParametersSatellite.Polarisation_Horizontal,
			"fec": eDVBFrontendParametersSatellite.FEC_Auto,
			"fec_s2": eDVBFrontendParametersSatellite.FEC_9_10,
			"modulation": eDVBFrontendParametersSatellite.Modulation_QPSK
		}

		self.service = self.session.nav.getCurrentService()
		if self.service is not None:
			self.feinfo = self.service.frontendInfo()
			frontendData = self.feinfo and self.feinfo.getAll(True)
		if frontendData is not None:
			ttype = frontendData.get("tuner_type", "UNKNOWN")
			if ttype == "DVB-S":
				defaultSat["system"] = frontendData.get("system", eDVBFrontendParametersSatellite.System_DVB_S)
				defaultSat["frequency"] = frontendData.get("frequency", 0) / 1000
				defaultSat["inversion"] = frontendData.get("inversion", eDVBFrontendParametersSatellite.Inversion_Unknown)
				defaultSat["symbolrate"] = frontendData.get("symbol_rate", 0) / 1000
				defaultSat["polarization"] = frontendData.get("polarization", eDVBFrontendParametersSatellite.Polarisation_Horizontal)
				if defaultSat["system"] == eDVBFrontendParametersSatellite.System_DVB_S2:
					defaultSat["fec_s2"] = frontendData.get("fec_inner", eDVBFrontendParametersSatellite.FEC_Auto)
					defaultSat["rolloff"] = frontendData.get("rolloff", eDVBFrontendParametersSatellite.RollOff_alpha_0_35)
					defaultSat["pilot"] = frontendData.get("pilot", eDVBFrontendParametersSatellite.Pilot_Unknown)
				else:
					defaultSat["fec"] = frontendData.get("fec_inner", eDVBFrontendParametersSatellite.FEC_Auto)
				defaultSat["modulation"] = frontendData.get("modulation", eDVBFrontendParametersSatellite.Modulation_QPSK)
				defaultSat["orbpos"] = frontendData.get("orbital_position", 0)
		del self.feinfo
		del self.service
		del frontendData

		self.scan_sat = ConfigSubsection()
		self.scan_networkScan = ConfigYesNo(default = False)

		#ConfigYesNo(default = True)
		self.blindscan_start_frequency = ConfigInteger(default = 10700, limits = (1, 99999))
		self.blindscan_stop_frequency = ConfigInteger(default = 12750, limits = (1, 99999))
		self.blindscan_start_symbol = ConfigInteger(default = 2, limits = (1, 99))
		self.blindscan_stop_symbol = ConfigInteger(default = 45, limits = (1, 99))
		self.scan_clearallservices = ConfigYesNo(default = False)
		self.scan_onlyfree = ConfigYesNo(default = False)
		self.dont_scan_known_tps = ConfigYesNo(default = False)
		self.filter_off_adjacent_satellites = ConfigSelection(default = 0, choices = [
			(0, _("no")),
			(1, _("up to 1 degree")),
			(2, _("up to 2 degrees")),
			(3, _("up to 3 degrees"))])
		self.search_type = ConfigSelection(default = 0, choices = [
			(0, _("scan for channels")),
			(1, _("save to XML file"))])


		# collect all nims which are *not* set to "nothing"
		nim_list = []
		for n in nimmanager.nim_slots:
			if n.config_mode == "nothing":
				continue
			if n.config_mode == "advanced" and len(nimmanager.getSatListForNim(n.slot)) < 1:
				continue
			if n.config_mode in ("loopthrough", "satposdepends"):
				root_id = nimmanager.sec.getRoot(n.slot_id, int(n.config.connectedTo.value))
				if n.type == nimmanager.nim_slots[root_id].type: # check if connected from a DVB-S to DVB-S2 Nim or vice versa
					continue
			if n.isCompatible("DVB-S"):
				nim_list.append((str(n.slot), n.friendly_full_description))
		self.scan_nims = ConfigSelection(choices = nim_list)

		# sat
		self.scan_sat.frequency = ConfigInteger(default = defaultSat["frequency"], limits = (1, 99999))
		self.scan_sat.polarization = ConfigSelection(default = eDVBFrontendParametersSatellite.Polarisation_CircularRight + 1, choices = [
			(eDVBFrontendParametersSatellite.Polarisation_CircularRight + 1, _("vertical and horizontal")),
			(eDVBFrontendParametersSatellite.Polarisation_Vertical, _("vertical")),
			(eDVBFrontendParametersSatellite.Polarisation_Horizontal, _("horizontal")),
			(eDVBFrontendParametersSatellite.Polarisation_CircularRight + 2, _("circular right and circular left")),
			(eDVBFrontendParametersSatellite.Polarisation_CircularRight, _("circular right")),
			(eDVBFrontendParametersSatellite.Polarisation_CircularLeft, _("circular left"))])
		self.scan_scansat = {}
		for sat in nimmanager.satList:
			self.scan_scansat[sat[0]] = ConfigYesNo(default = False)

		self.scan_satselection = []
		for slot in nimmanager.nim_slots:
			if slot.isCompatible("DVB-S"):
				self.scan_satselection.append(getConfigSatlist(defaultSat["orbpos"], self.satList[slot.slot]))
		return True

	def getSelectedSatIndex(self, v):
		index    = 0
		none_cnt = 0
		for n in self.satList:
			if self.satList[index] == None:
				none_cnt = none_cnt + 1
			if index == int(v):
				return (index-none_cnt)
			index = index + 1
		return -1

	def createSetup(self):
		self.list = []
		self.multiscanlist = []
		index_to_scan = int(self.scan_nims.value)
		print "ID: ", index_to_scan

		self.tunerEntry = getConfigListEntry(_("Tuner"), self.scan_nims,_('Select a tuner that is configured for the satellite you wish to search'))
		self.list.append(self.tunerEntry)

		if self.scan_nims == [ ]:
			return

		self.systemEntry = None
		self.modulationEntry = None
		nim = nimmanager.nim_slots[index_to_scan]

		self.scan_networkScan.value = False
		if nim.isCompatible("DVB-S") :
			self.list.append(getConfigListEntry(_('Satellite'), self.scan_satselection[self.getSelectedSatIndex(index_to_scan)],_('Select the satellite you wish to search')))
			self.list.append(getConfigListEntry(_('Scan start frequency'), self.blindscan_start_frequency,_('Frequency values must be between 10700 and 12750 (or 3000 and 4200 in the case of C-band satellites)')))
			self.list.append(getConfigListEntry(_('Scan stop frequency'), self.blindscan_stop_frequency,_('Frequency values must be between 10700 and 12750 (or 3000 and 4200 in the case of C-band satellites)')))
			self.list.append(getConfigListEntry(_("Polarisation"), self.scan_sat.polarization,_('If you are not sure what polarisations the satellite you wish to search transmits, select "vertical and horizontal"')))
			self.list.append(getConfigListEntry(_('Scan start symbolrate'), self.blindscan_start_symbol,_('Symbol rate values are in megasymbols; enter a value between 1 and 44')))
			self.list.append(getConfigListEntry(_('Scan stop symbolrate'), self.blindscan_stop_symbol,_('Symbol rate values are in megasymbols; enter a value between 2 and 45')))
			self.list.append(getConfigListEntry(_("Clear before scan"), self.scan_clearallservices,_('If you select "yes" all channels on the satellite being search will be deleted before starting the current search')))
			self.list.append(getConfigListEntry(_("Only free scan"), self.scan_onlyfree,_('If you select "yes" the scan will only save channels that are not encrypted; "no" will find encrypted and non-encrypted channels')))
			self.list.append(getConfigListEntry(_("Only scan unknown transponders"), self.dont_scan_known_tps,_('If you select "yes" the scan will only search transponders not listed in satellites.xml')))
			self.list.append(getConfigListEntry(_("Filter out adjacent satellites"), self.filter_off_adjacent_satellites,_('When a neighbouring satellite is very strong this avoids searching transponders known to be coming from the neighbouring satellite')))
			self.list.append(getConfigListEntry(_("Search type"), self.search_type,_('"channel scan" searches for channels and saves them to your STB_BOX; "save to XML file" does a transponder search and saves found transponders to an XML file in satellites.xml format')))
			self["config"].list = self.list
			self["config"].l.setList(self.list)

	def newConfig(self):
		cur = self["config"].getCurrent()
		print "cur is", cur
		if cur == self.tunerEntry or \
			cur == self.systemEntry or \
			(self.modulationEntry and self.systemEntry[1].value == eDVBFrontendParametersSatellite.System_DVB_S2 and cur == self.modulationEntry):
			self.createSetup()

	def checkSettings(self, orb):
		self.ku_band_lower_limit = 10700
		self.is_c_band_scan = False
		band = self.SatBandCheck(orb)
		if band :
			if band == 'C' :
				self.is_c_band_scan = True
		else:
			if self.blindscan_start_frequency.value < 4200 :
				self.is_c_band_scan = True
		if self.blindscan_start_symbol.value < 1 or self.blindscan_start_symbol.value > 44 :
			self.session.open(MessageBox, _("Invalid parameters entered. Please correct and try again.\nStart symbol rate must be between 1MHz and 44MHz."), MessageBox.TYPE_ERROR)
			return False
		if self.blindscan_stop_symbol.value < 2 or self.blindscan_stop_symbol.value > 45 :
			self.session.open(MessageBox, _("Invalid parameters entered. Please correct and try again.\nStop symbol rate must be between 2MHz and 45MHz."), MessageBox.TYPE_ERROR)
			return False
		if self.blindscan_start_symbol.value > self.blindscan_stop_symbol.value :
			self.session.open(MessageBox, _("Invalid parameters entered. Please correct and try again.\nSymbol rate start value is larger than stop value."), MessageBox.TYPE_ERROR)
			return False
		if self.blindscan_start_frequency.value > self.blindscan_stop_frequency.value :
			self.session.open(MessageBox, _("Invalid parameters entered. Please correct and try again.\nFrequency start value is larger than stop value."), MessageBox.TYPE_ERROR)
			return False
		if self.is_c_band_scan and band == 'C' :
			if self.blindscan_start_frequency.value < 3000 :
				self.session.open(MessageBox, _("Invalid parameters entered. Please correct and try again.\nThat is a C-band satellite so frequency values \nneed to be between 3000MHz and 4200MHz."), MessageBox.TYPE_ERROR)
				return False
			if self.blindscan_stop_frequency.value > 4200 :
				self.session.open(MessageBox, _("Invalid parameters entered. Please correct and try again.\nThat is a C-band satellite so frequency values \nneed to be between 3000MHz and 4200MHz."), MessageBox.TYPE_ERROR)
				return False
			return True
		if self.is_c_band_scan :
			if self.blindscan_start_frequency.value < 3000 :
				self.session.open(MessageBox, _("Invalid parameters entered. Please correct and try again.\nStart frequency must be between 10700MHz and 12750MHz.\n(Or 3000MHz and 4200MHz in the case of c-band)."), MessageBox.TYPE_ERROR)
				return False
			if self.blindscan_stop_frequency.value > 4200 :
				self.session.open(MessageBox, _("Invalid parameters entered. Please correct and try again.\nFor C-band searches stop frequency must be between 3000MHz and 4200MHz."), MessageBox.TYPE_ERROR)
				return False
			return True
		if band == 'Ku' :
			if self.blindscan_start_frequency.value < 10700 or self.blindscan_start_frequency.value > 12750 :
				self.session.open(MessageBox, _("Invalid parameters entered. Please correct and try again.\nThat is a Ku-band satellite so frequency values \nneed to be between 10700MHz and 12750MHz."), MessageBox.TYPE_ERROR)
				return False
			if self.blindscan_stop_frequency.value < 10700 or self.blindscan_stop_frequency.value > 12750 :
				self.session.open(MessageBox, _("Invalid parameters entered. Please correct and try again.\nThat is a Ku-band satellite so frequency values \nneed to be between 10700MHz and 12750MHz."), MessageBox.TYPE_ERROR)
				return False
		if self.blindscan_start_frequency.value < 10700 or self.blindscan_start_frequency.value > 12750 :
			self.session.open(MessageBox, _("Invalid parameters entered. Please correct and try again.\nStart frequency must be between 10700MHz and 12750MHz.\n(Or 3000MHz and 4200MHz in the case of c-band)."), MessageBox.TYPE_ERROR)
			return False
		if self.blindscan_stop_frequency.value < 10700 or self.blindscan_stop_frequency.value > 12750 :
			self.session.open(MessageBox, _("Invalid parameters entered. Please correct and try again.\nStop frequency must be between 10700MHz and 12750MHz.\n(Or 3000MHz and 4200MHz in the case of c-band)."), MessageBox.TYPE_ERROR)
			return False
		return True

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.newConfig()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.newConfig()

	def keyCancel(self):
		self.session.nav.playService(self.current_play_service)
		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def keyGo(self):

		tab_pol = {
			eDVBFrontendParametersSatellite.Polarisation_Horizontal : "horizontal",
			eDVBFrontendParametersSatellite.Polarisation_Vertical : "vertical",
			eDVBFrontendParametersSatellite.Polarisation_CircularLeft : "circular left",
			eDVBFrontendParametersSatellite.Polarisation_CircularRight : "circular right",
			eDVBFrontendParametersSatellite.Polarisation_CircularRight + 1 : "horizontal and vertical",
			eDVBFrontendParametersSatellite.Polarisation_CircularRight + 2 : "circular left and circular right"
		}

		self.tmp_tplist=[]
		tmp_pol = []
		tmp_band = []
		idx_selected_sat = int(self.getSelectedSatIndex(self.scan_nims.value))
		tmp_list=[self.satList[int(self.scan_nims.value)][self.scan_satselection[idx_selected_sat].index]]
		orb = tmp_list[0][0]

		if self.checkSettings(orb) == False:
			return

		uni_lnb_cutoff = 11700
		if self.blindscan_start_frequency.value < uni_lnb_cutoff and self.blindscan_stop_frequency.value > uni_lnb_cutoff :
			tmp_band=["low","high"]
		elif self.blindscan_start_frequency.value < uni_lnb_cutoff :
			tmp_band=["low"]
		else :
			tmp_band=["high"]

		if self.scan_sat.polarization.value >  eDVBFrontendParametersSatellite.Polarisation_CircularRight : # must be searching both polarisations, either V and H, or R and L
			tmp_pol=["vertical", "horizontal"]
		elif self.scan_sat.polarization.value ==  eDVBFrontendParametersSatellite.Polarisation_CircularRight :
			tmp_pol=["vertical"]
		elif self.scan_sat.polarization.value ==  eDVBFrontendParametersSatellite.Polarisation_CircularLeft :
			tmp_pol=["horizontal"]
		else:
			tmp_pol=[tab_pol[self.scan_sat.polarization.value]]

		self.doRun(tmp_list, tmp_pol, tmp_band)


	def doRun(self, tmp_list, tmp_pol, tmp_band):
		self.full_data = ""
		self.total_list=[]
		for x in tmp_list:
			for y in tmp_pol:
				for z in tmp_band:
					self.total_list.append([x,y,z])
					print "add scan item : ", x, ", ", y, ", ", z

		self.max_count = len(self.total_list)
		self.is_runable = True
		self.running_count = 0
		self.clockTimer = eTimer()
		self.clockTimer.callback.append(self.doClock)
		self.clockTimer.start(1000)

	def doClock(self):
		is_scan = False
		if self.is_runable :
			if self.running_count >= self.max_count:
				self.clockTimer.stop()
				del self.clockTimer
				self.clockTimer = None
				print "Done"
				return
			orb = self.total_list[self.running_count][0]
			pol = self.total_list[self.running_count][1]
			band = self.total_list[self.running_count][2]
			self.running_count = self.running_count + 1
			print "running status-[%d] : [%d][%s][%s]" %(self.running_count, orb[0], pol, band)
			if self.running_count == self.max_count:
				is_scan = True
			self.prepareScanData(orb, pol, band, is_scan)

	def prepareScanData(self, orb, pol, band, is_scan):
		self.is_runable = False
		self.orb_position = orb[0]
		self.sat_name = orb[1]
		self.feid = int(self.scan_nims.value)
		tab_hilow = {"high" : 1, "low" : 0}
		tab_pol = {
			"horizontal" : eDVBFrontendParametersSatellite.Polarisation_Horizontal,
			"vertical" : eDVBFrontendParametersSatellite.Polarisation_Vertical,
			"circular left" : eDVBFrontendParametersSatellite.Polarisation_CircularLeft,
			"circular right" : eDVBFrontendParametersSatellite.Polarisation_CircularRight
		}

		returnvalue = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

		if not self.openFrontend():
			self.oldref = self.session.nav.getCurrentlyPlayingServiceReference()
			self.session.nav.stopService()
			if not self.openFrontend():
				if self.session.pipshown:
					self.session.pipshown = False
					del self.session.pip
					if not self.openFrontend():
						self.frontend = None
		self.tuner = Tuner(self.frontend)

		if self.is_c_band_scan :
			self.scan_sat.frequency.value = 3600
		else:
			if tab_hilow[band]:
				self.scan_sat.frequency.value = 12515
			else:
				self.scan_sat.frequency.value = 11015
		returnvalue = (self.scan_sat.frequency.value,
					 0,
					 tab_pol[pol],
					 0,
					 0,
					 orb[0],
					 eDVBFrontendParametersSatellite.System_DVB_S,
					 0,
					 0,
					 0)
		self.tuner.tune(returnvalue)

		if self.getNimSocket(self.feid) < 0:
			print "can't find i2c number!!"
			return

		c_band_loc_osc = 5150
		uni_lnb_loc_osc = {"high" : 10600, "low" : 9750}
		uni_lnb_cutoff = 11700
		if self.is_c_band_scan :
			temp_start_int_freq = c_band_loc_osc - self.blindscan_stop_frequency.value
			temp_end_int_freq = c_band_loc_osc - self.blindscan_start_frequency.value
			status_box_start_freq = c_band_loc_osc - temp_end_int_freq
			status_box_end_freq = c_band_loc_osc - temp_start_int_freq

		else:
			if tab_hilow[band] :
				if self.blindscan_start_frequency.value < uni_lnb_cutoff :
					temp_start_int_freq = uni_lnb_cutoff - uni_lnb_loc_osc[band]
				else:
					temp_start_int_freq = self.blindscan_start_frequency.value - uni_lnb_loc_osc[band]
				temp_end_int_freq = self.blindscan_stop_frequency.value - uni_lnb_loc_osc[band]
			else:
				if self.blindscan_stop_frequency.value > uni_lnb_cutoff :
					temp_end_int_freq = uni_lnb_cutoff - uni_lnb_loc_osc[band]
				else:
					temp_end_int_freq = self.blindscan_stop_frequency.value - uni_lnb_loc_osc[band]
				temp_start_int_freq = self.blindscan_start_frequency.value - uni_lnb_loc_osc[band]
			status_box_start_freq = temp_start_int_freq + uni_lnb_loc_osc[band]
			status_box_end_freq = temp_end_int_freq + uni_lnb_loc_osc[band]

		if config.misc.boxtype.value.startswith('vu'):
			cmd = "vuplus_blindscan %d %d %d %d %d %d %d %d" % (temp_start_int_freq, temp_end_int_freq, self.blindscan_start_symbol.value, self.blindscan_stop_symbol.value, tab_pol[pol], tab_hilow[band], self.feid, self.getNimSocket(self.feid)) # commented out by Huevos cmd = "vuplus_blindscan %d %d %d %d %d %d %d %d" % (self.blindscan_start_frequency.value/1000000, self.blindscan_stop_frequency.value/1000000, self.blindscan_start_symbol.value, self.blindscan_stop_symbol.value, tab_pol[pol], tab_hilow[band], self.feid, self.getNimSocket(self.feid))
		elif config.misc.boxtype.value.startswith('et'):
			cmd = "avl_xtrend_blindscan %d %d %d %d %d %d %d %d" % (temp_start_int_freq, temp_end_int_freq, self.blindscan_start_symbol.value, self.blindscan_stop_symbol.value, tab_pol[pol], tab_hilow[band], self.feid, self.getNimSocket(self.feid)) # commented out by Huevos cmd = "avl_xtrend_blindscan %d %d %d %d %d %d %d %d" % (self.blindscan_start_frequency.value/1000000, self.blindscan_stop_frequency.value/1000000, self.blindscan_start_symbol.value, self.blindscan_stop_symbol.value, tab_pol[pol], tab_hilow[band], self.feid, self.getNimSocket(self.feid))
		print "prepared command : [%s]" % (cmd)

		self.thisRun = [] # used to check result corresponds with values used above
		self.thisRun.append(int(temp_start_int_freq))
		self.thisRun.append(int(temp_end_int_freq))
		self.thisRun.append(int(tab_hilow[band]))

		self.blindscan_container = eConsoleAppContainer()
		self.blindscan_container.appClosed.append(self.blindscanContainerClose)
		self.blindscan_container.dataAvail.append(self.blindscanContainerAvail)
		self.blindscan_container.execute(cmd)

		display_pol = pol # Display the correct polarisation in the MessageBox below
		if self.scan_sat.polarization.value == eDVBFrontendParametersSatellite.Polarisation_CircularRight :
			display_pol = _("circular right")
		elif self.scan_sat.polarization.value == eDVBFrontendParametersSatellite.Polarisation_CircularLeft :
			display_pol = _("circular left")
		elif  self.scan_sat.polarization.value == eDVBFrontendParametersSatellite.Polarisation_CircularRight + 2 :
			if pol == "horizontal" :
				display_pol = _("circular left")
			else:
				display_pol = _("circular right")

		tmpstr = _("Looking for available transponders.\nThis will take a short while.\n\n   Current Status : %d/%d\n   Satellite : %s\n   Polarization : %s\n   Frequency range : %d - %d MHz\n   Symbol rates : %d - %d MHz") %(self.running_count, self.max_count, orb[1], display_pol, status_box_start_freq, status_box_end_freq, self.blindscan_start_symbol.value, self.blindscan_stop_symbol.value)
		if is_scan :
			self.blindscan_session = self.session.openWithCallback(self.blindscanSessionClose, MessageBox, tmpstr, MessageBox.TYPE_INFO)
		else:
			self.blindscan_session = self.session.openWithCallback(self.blindscanSessionNone, MessageBox, tmpstr, MessageBox.TYPE_INFO)

	def blindscanContainerClose(self, retval):
		lines = self.full_data.split('\n')
		self.full_data = "" # Clear this string so we don't get duplicates on subsequent runs
		for line in lines:
			data = line.split()
			print "cnt :", len(data), ", data :", data
			if len(data) >= 10 and self.dataIsGood(data) :
				if data[0] == 'OK':
					parm = eDVBFrontendParametersSatellite()
					sys = { "DVB-S" : eDVBFrontendParametersSatellite.System_DVB_S,
						"DVB-S2" : eDVBFrontendParametersSatellite.System_DVB_S2}
					qam = { "QPSK" : parm.Modulation_QPSK,
						"8PSK" : parm.Modulation_8PSK}
					inv = { "INVERSION_OFF" : parm.Inversion_Off,
						"INVERSION_ON" : parm.Inversion_On,
						"INVERSION_AUTO" : parm.Inversion_Unknown}
					fec = { "FEC_AUTO" : parm.FEC_Auto,
						"FEC_1_2" : parm.FEC_1_2,
						"FEC_2_3" : parm.FEC_2_3,
						"FEC_3_4" : parm.FEC_3_4,
						"FEC_5_6": parm.FEC_5_6,
						"FEC_7_8" : parm.FEC_7_8,
						"FEC_8_9" : parm.FEC_8_9,
						"FEC_3_5" : parm.FEC_3_5,
						"FEC_9_10" : parm.FEC_9_10,
						"FEC_NONE" : parm.FEC_None}
					roll ={ "ROLLOFF_20" : parm.RollOff_alpha_0_20,
						"ROLLOFF_25" : parm.RollOff_alpha_0_25,
						"ROLLOFF_35" : parm.RollOff_alpha_0_35}
					pilot={ "PILOT_ON" : parm.Pilot_On,
						"PILOT_OFF" : parm.Pilot_Off}
					pol = {	"HORIZONTAL" : parm.Polarisation_Horizontal,
						"VERTICAL" : parm.Polarisation_Vertical}
					parm.orbital_position = self.orb_position
					parm.polarisation = pol[data[1]]
					parm.frequency = int(data[2])
					parm.symbol_rate = int(data[3])
					parm.system = sys[data[4]]
					parm.inversion = inv[data[5]]
					parm.pilot = pilot[data[6]]
					parm.fec = fec[data[7]]
					parm.modulation = qam[data[8]]
					parm.rolloff = roll[data[9]]
					self.tmp_tplist.append(parm)
		self.blindscan_session.close(True)

	def blindscanContainerAvail(self, str):
		print str
		#if str.startswith("OK"):
		self.full_data = self.full_data + str

	def blindscanSessionNone(self, *val):
		import time
		self.blindscan_container.sendCtrlC()
		self.blindscan_container = None
		time.sleep(2)

		if self.frontend:
			self.frontend = None
			del self.raw_channel

		if val[0] == False:
			self.tmp_tplist = []
			self.running_count = self.max_count

		self.is_runable = True


	def blindscanSessionClose(self, *val):
		self.blindscanSessionNone(val[0])

		if self.tmp_tplist != None and self.tmp_tplist != []:
			self.tmp_tplist = self.correctBugsCausedByDriver(self.tmp_tplist)

			# Sync with or remove transponders that exist in satellites.xml
			self.known_transponders = self.getKnownTransponders(self.orb_position)
			if self.dont_scan_known_tps.value :
				self.tmp_tplist = self.removeKnownTransponders(self.tmp_tplist, self.known_transponders)
			else:
				self.tmp_tplist = self.syncWithKnownTransponders(self.tmp_tplist, self.known_transponders)

			# Filter off transponders on neighbouring satellites
			if self.filter_off_adjacent_satellites.value :
				 self.tmp_tplist = self.filterOffAdjacentSatellites(self.tmp_tplist, self.orb_position, self.filter_off_adjacent_satellites.value)

			# Process transponders still in list
			if self.tmp_tplist != [] :
				for p in self.tmp_tplist:
					print "data : [%d][%d][%d][%d][%d][%d][%d][%d][%d][%d]" % (p.orbital_position, p.polarisation, p.frequency, p.symbol_rate, p.system, p.inversion, p.pilot, p.fec, p.modulation, p.modulation)

				if self.search_type.value == 0 : # Do a service scan
					self.startScan(self.tmp_tplist, self.feid)
				else: # Save transponder data to file. No service scan.
					self.tmp_tplist = sorted(self.tmp_tplist, key=lambda transponder: transponder.frequency)
					xml_location = self.createSatellitesXMLfile(self.tmp_tplist, XML_BLINDSCAN_DIR)
					msg = _("Search completed. %d transponders found.\n\nDetails saved in:\n%s")%(len(self.tmp_tplist), xml_location)
					self.session.openWithCallback(self.callbackNone, MessageBox, msg, MessageBox.TYPE_INFO, timeout=300)
			else:
				msg = _("No new transponders found! \n\nOnly transponders already listed in satellites.xml \nhave been found for those search parameters!")
				self.session.openWithCallback(self.callbackNone, MessageBox, msg, MessageBox.TYPE_INFO, timeout=60)

		else:
			msg = _("No transponders were found for those search parameters!")
			if val[0] == False:
				msg = _("The blindscan run was cancelled by the user.")
			self.session.openWithCallback(self.callbackNone, MessageBox, msg, MessageBox.TYPE_INFO, timeout=60)
			self.tmp_tplist = []

	def startScan(self, tlist, feid, networkid = 0):
		self.scan_session = None

		flags = 0
		if self.scan_clearallservices.value:
			flags |= eComponentScan.scanRemoveServices
		else:
			flags |= eComponentScan.scanDontRemoveUnscanned
		if self.scan_onlyfree.value:
			flags |= eComponentScan.scanOnlyFree
		self.session.open(ServiceScan, [{"transponders": tlist, "feid": feid, "flags": flags, "networkid": networkid}])

	def getKnownTransponders(self, pos):
		tlist = []
		list = nimmanager.getTransponders(pos)
		for x in list:
			if x[0] == 0:
				parm = eDVBFrontendParametersSatellite()
				parm.frequency = x[1]
				parm.symbol_rate = x[2]
				parm.polarisation = x[3]
				parm.fec = x[4]
				parm.inversion = x[7]
				parm.orbital_position = pos
				parm.system = x[5]
				parm.modulation = x[6]
				parm.rolloff = x[8]
				parm.pilot = x[9]
				tlist.append(parm)
		return tlist

	def syncWithKnownTransponders(self, tplist, knowntp) :
		tolerance = 5
		multiplier = 1000
		x = 0
		for t in tplist :
			for k in knowntp :
				if (t.polarisation % 2) == (k.polarisation % 2) and \
					abs(t.frequency - k.frequency) < (tolerance*multiplier) and \
					abs(t.symbol_rate - k.symbol_rate) < (tolerance*multiplier) :
					tplist[x] = k
					break
			x += 1
		return tplist

	def removeKnownTransponders(self, tplist, knowntp) :
		new_tplist = []
		tolerance = 5
		multiplier = 1000
		x = 0
		isnt_known = True
		for t in tplist :
			for k in knowntp :
				if (t.polarisation % 2) == (k.polarisation % 2) and \
					abs(t.frequency - k.frequency) < (tolerance*multiplier) and \
					abs(t.symbol_rate - k.symbol_rate) < (tolerance*multiplier) :
					isnt_known = False
					break
			x += 1
			if isnt_known :
				new_tplist.append(t)
			else:
				isnt_known = True
		return new_tplist

	def filterOffAdjacentSatellites(self, tplist, pos, degrees) :
		neighbours = []
		tenths_of_degrees = degrees * 10
		for sat in nimmanager.satList :
			if sat[0] != pos and self.positionDiff(pos, sat[0]) <= tenths_of_degrees :
				neighbours.append(sat[0])
		for neighbour in neighbours :
			tplist = self.removeKnownTransponders(tplist, self.getKnownTransponders(neighbour))
		return tplist

	def correctBugsCausedByDriver(self, tplist) :
		if self.is_c_band_scan : # for some reason a c-band scan (with a Vu+) returns the transponder frequencies in Ku band format so they have to be converted back to c-band numbers before the subsequent service search
			x = 0
			for transponders in tplist :
				if tplist[x].frequency > (4200*1000) :
					tplist[x].frequency = (5150*1000) - (tplist[x].frequency - (9750*1000))
				x += 1

		x = 0
		for transponders in tplist :
			if tplist[x].system == 0 : # convert DVB-S transponders to auto fec as for some reason the tuner incorrectly returns 3/4 FEC for all transmissions
				tplist[x].fec = 0
			if self.scan_sat.polarization.value == eDVBFrontendParametersSatellite.Polarisation_CircularRight : # Return circular transponders to correct polarisation
				tplist[x].polarisation = eDVBFrontendParametersSatellite.Polarisation_CircularRight
			elif self.scan_sat.polarization.value == eDVBFrontendParametersSatellite.Polarisation_CircularLeft : # Return circular transponders to correct polarisation
				tplist[x].polarisation = eDVBFrontendParametersSatellite.Polarisation_CircularLeft
			elif self.scan_sat.polarization.value == eDVBFrontendParametersSatellite.Polarisation_CircularRight + 2: # Return circular transponders to correct polarisation
				if tplist[x].polarisation == eDVBFrontendParametersSatellite.Polarisation_Horizontal : # Return circular transponders to correct polarisation
					tplist[x].polarisation = eDVBFrontendParametersSatellite.Polarisation_CircularLeft
				else:
					tplist[x].polarisation = eDVBFrontendParametersSatellite.Polarisation_CircularRight
			x += 1
		return tplist

	def positionDiff(self, pos1, pos2) :
		diff = pos1 - pos2
		return min(abs(diff % 3600), 3600 - abs(diff % 3600))

	def dataIsGood(self, data) : # check output of the binary for nonsense values
		good = False
		low_lo = 9750
		high_lo = 10600
		c_lo = 5150
		lower_freq = self.thisRun[0]
		upper_freq = self.thisRun[1]
		high_band = self.thisRun[2]
		data_freq = int(int(data[2])/1000)
		data_symbol = int(data[3])
		lower_symbol = (self.blindscan_start_symbol.value * 1000000) - 200000
		upper_symbol = (self.blindscan_stop_symbol.value * 1000000) + 200000

		if high_band :
			data_if_freq = data_freq - high_lo
		elif self.is_c_band_scan and data_freq > 2999 and data_freq < 4201 :
			data_if_freq = c_lo - data_freq
		else :
			data_if_freq = data_freq - low_lo

		if data_if_freq >= lower_freq and data_if_freq <= upper_freq :
			good = True

		if data_symbol < lower_symbol or data_symbol > upper_symbol :
			good = False

		if good == False :
			print "Data returned by the binary is not good...\n	Data: Frequency [%d], Symbol rate [%d]" % (int(data[2]), int(data[3]))

		return good

	def createSatellitesXMLfile(self, tp_list, save_xml_dir) :
		pos = self.orb_position
		if pos > 1800 :
			pos -= 3600
		if pos < 0 :
			pos_name = '%dW' % (abs(int(pos))/10)
		else :
			pos_name = '%dE' % (abs(int(pos))/10)
		location = '%s/blindscan_%s_%s.xml' %(save_xml_dir, pos_name, strftime("%d-%m-%Y_%H-%M-%S"))
		tuner = ['A', 'B', 'C']
		polarisation = ['horizontal', 'vertical', 'circular left', 'circular right', 'vertical and horizontal', 'circular right and circular left']
		adjacent = ['no', 'up to 1 degree', 'up to 2 degrees', 'up to 3 degrees']
		known_txp = 'no'
		if self.filter_off_adjacent_satellites.value :
			known_txp ='yes'
		xml = ['<?xml version="1.0" encoding="iso-8859-1"?>\n\n']
		xml.append('<!--\n')
		xml.append('	File created on %s\n' % (strftime("%A, %d of %B %Y, %H:%M:%S")))
		xml.append('	using %s receiver running VIX image, version %s,\n' % (config.misc.boxtype.value, about.getImageVersionString()))
		xml.append('	build %s, with the blindscan plugin updated by Huevos\n\n' % (about.getBuildVersionString()))
		xml.append('	Search parameters:\n')
		xml.append('		Tuner: %s\n' % (tuner[self.feid]))
		xml.append('		Satellite: %s\n' % (self.sat_name))
		xml.append('		Start frequency: %dMHz\n' % (self.blindscan_start_frequency.value))
		xml.append('		Stop frequency: %dMHz\n' % (self.blindscan_stop_frequency.value))
		xml.append('		Polarization: %s\n' % (polarisation[self.scan_sat.polarization.value]))
		xml.append('		Lower symbol rate: %d\n' % (self.blindscan_start_symbol.value * 1000))
		xml.append('		Upper symbol rate: %d\n' % (self.blindscan_stop_symbol.value * 1000))
		xml.append('		Only save unknown tranponders: %s\n' % (known_txp))
		xml.append('		Filter out adjacent satellites: %s\n' % (adjacent[self.filter_off_adjacent_satellites.value]))
		xml.append('-->\n\n')
		xml.append('<satellites>\n')
		xml.append('	<sat name="%s" flags="0" position="%s">\n' % (self.sat_name, self.orb_position))
		for tp in tp_list :
			xml.append('		<transponder frequency="%d" symbol_rate="%d" polarization="%d" fec_inner="%d" system="%d" modulation="%d"/>\n' % (tp.frequency, tp.symbol_rate, tp.polarisation, tp.fec, tp.system, tp.modulation))
		xml.append('	</sat>\n')
		xml.append('</satellites>')
		open(location, "w").writelines(xml)
		return location

	def SatBandCheck(self, pos) :
		freq = 0
		band = ''
		tp_list = self.getKnownTransponders(pos)
		if len(tp_list) :
			freq = int(tp_list[0].frequency)
		if freq :
			if freq < 4201000 and freq > 2999000 :
				band = 'C'
			elif freq < 12751000 and freq > 10700000 :
				band = 'Ku'
		print "SatBandCheck band = %s" % (band)
		return band


def Plugins(path, **kwargs):
	plist = [PluginDescriptor(name=_("Blind Scan"), where=PluginDescriptor.WHERE_MENU, needsRestart = False, fnc=BlindscanSetup)]
	return plist

def main(session, **kwargs):
	session.open(Blindscan)

def BlindscanSetup(menuid, **kwargs):
	if menuid == "scan":
		return [(_("Blind Scan"), main, "blindscan", 25)]
	else:
		return []

def Plugins(**kwargs):
	if (nimmanager.hasNimType("DVB-S")):
		return PluginDescriptor(name=_("Blind Scan"), description="Scan cable provider channels", where = PluginDescriptor.WHERE_MENU, fnc=BlindscanSetup)
	else:
		return []

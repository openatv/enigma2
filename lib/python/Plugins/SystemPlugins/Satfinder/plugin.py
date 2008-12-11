from enigma import eDVBResourceManager,\
	eDVBFrontendParametersSatellite, eDVBFrontendParameters

from Screens.Screen import Screen
from Screens.ScanSetup import ScanSetup
from Screens.MessageBox import MessageBox
from Plugins.Plugin import PluginDescriptor

from Components.Label import Label
from Components.Sources.FrontendStatus import FrontendStatus
from Components.ActionMap import ActionMap
from Components.NimManager import nimmanager, getConfigSatlist
from Components.MenuList import MenuList
from Components.config import ConfigSelection, getConfigListEntry

class Tuner:
	def __init__(self, frontend):
		self.frontend = frontend
		
	def tune(self, transponder):
		if self.frontend:
			print "tuning to transponder with data", transponder
			parm = eDVBFrontendParametersSatellite()
			parm.frequency = transponder[0] * 1000
			parm.symbol_rate = transponder[1] * 1000
			parm.polarisation = transponder[2]
			parm.fec = transponder[3]
			parm.inversion = transponder[4]
			parm.orbital_position = transponder[5]
			parm.system = transponder[6]
			parm.modulation = transponder[7]
			parm.rolloff = transponder[8]
			parm.pilot = transponder[9]
			feparm = eDVBFrontendParameters()
			feparm.setDVBS(parm, True)
			self.lastparm = feparm
			self.frontend.tune(feparm)

	def retune(self):
		if self.frontend:
			self.frontend.tune(self.lastparm)

class Satfinder(ScanSetup):
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

	def __init__(self, session, feid):
		self.initcomplete = False
		self.feid = feid
		self.oldref = None

		if not self.openFrontend():
			self.oldref = session.nav.getCurrentlyPlayingServiceReference()
			session.nav.stopService() # try to disable foreground service
			if not self.openFrontend():
				if session.pipshown: # try to disable pip
					session.pipshown = False
					del session.pip
					if not self.openFrontend():
						self.frontend = None # in normal case this should not happen

		ScanSetup.__init__(self, session)
		self.tuner = Tuner(self.frontend)
		self["introduction"].setText("")
		self["Frontend"] = FrontendStatus(frontend_source = lambda : self.frontend, update_interval = 100)
		self.initcomplete = True
		self.onClose.append(self.__onClose)

	def __onClose(self):
		self.session.nav.playService(self.oldref)

	def createSetup(self):
		self.typeOfTuningEntry = None
		self.satEntry = None
		
		self.list = []

		self.typeOfTuningEntry = getConfigListEntry(_('Tune'), self.tuning_type)
		self.list.append(self.typeOfTuningEntry)
		self.satEntry = getConfigListEntry(_('Satellite'), self.tuning_sat)
		self.list.append(self.satEntry)

		nim = nimmanager.nim_slots[self.feid]

		self.systemEntry = None
		if self.tuning_type.value == "manual_transponder":
			if nim.isCompatible("DVB-S2"):
				self.systemEntry = getConfigListEntry(_('System'), self.scan_sat.system)
				self.list.append(self.systemEntry)
			else:
				# downgrade to dvb-s, in case a -s2 config was active
				self.scan_sat.system.value = "dvb-s"
			self.list.append(getConfigListEntry(_('Frequency'), self.scan_sat.frequency))
			self.list.append(getConfigListEntry(_('Inversion'), self.scan_sat.inversion))
			self.list.append(getConfigListEntry(_('Symbol Rate'), self.scan_sat.symbolrate))
			self.list.append(getConfigListEntry(_("Polarity"), self.scan_sat.polarization))
			if self.scan_sat.system.value == "dvb-s":
				self.list.append(getConfigListEntry(_("FEC"), self.scan_sat.fec))
			elif self.scan_sat.system.value == "dvb-s2":
				self.list.append(getConfigListEntry(_("FEC"), self.scan_sat.fec_s2))
				self.modulationEntry = getConfigListEntry(_('Modulation'), self.scan_sat.modulation)
				self.list.append(self.modulationEntry)
				self.list.append(getConfigListEntry(_('Rolloff'), self.scan_sat.rolloff))
				self.list.append(getConfigListEntry(_('Pilot'), self.scan_sat.pilot))
		elif self.tuning_transponder and self.tuning_type.value == "predefined_transponder":
			self.list.append(getConfigListEntry(_("Transponder"), self.tuning_transponder))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def newConfig(self):
		cur = self["config"].getCurrent()
		if cur in (self.typeOfTuningEntry, self.systemEntry):
			self.createSetup()
		elif cur == self.satEntry:
			self.updateSats()
			self.createSetup()

	def sat_changed(self, config_element):
		self.newConfig()
		self.retune(config_element)

	def retune(self, configElement):
		returnvalue = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
		satpos = int(self.tuning_sat.value)
		if self.tuning_type.value == "manual_transponder":
			if self.scan_sat.system.value == "dvb-s2":
				fec = self.scan_sat.fec_s2.value
			else:
				fec = self.scan_sat.fec.value
			returnvalue = (
				self.scan_sat.frequency.value,
				self.scan_sat.symbolrate.value,
				self.scan_sat.polarization.index,
				{ "auto": 0,
				   "1_2": 1,
				   "2_3": 2,
				   "3_4": 3,
				   "5_6": 4,
				   "7_8": 5,
				   "8_9": 6,
				   "3_5": 7,
				   "4_5": 8,
				   "9_10": 9,
				   "none": 15 }[fec],
				self.scan_sat.inversion.index,
				satpos,
				self.scan_sat.system.index,
				self.scan_sat.modulation.index == 1 and 2 or 1,
				self.scan_sat.rolloff.index,
				self.scan_sat.pilot.index)
			self.tune(returnvalue)
		elif self.tuning_type.value == "predefined_transponder":
			tps = nimmanager.getTransponders(satpos)
			l = len(tps)
			if l > self.tuning_transponder.index:
				transponder = tps[self.tuning_transponder.index]
				returnvalue = (int(transponder[1] / 1000), int(transponder[2] / 1000),
					transponder[3], transponder[4], 2, satpos, transponder[5], transponder[6], transponder[8], transponder[9])
				self.tune(returnvalue)

	def createConfig(self, foo):
		self.tuning_transponder = None
		self.tuning_type = ConfigSelection(choices = [("manual_transponder", _("Manual transponder")), ("predefined_transponder", _("Predefined transponder"))])
		self.tuning_sat = getConfigSatlist(192, nimmanager.getSatListForNim(self.feid))
		ScanSetup.createConfig(self, None)
		
		self.updateSats()

		for x in (self.tuning_type, self.tuning_sat, self.scan_sat.frequency,
			self.scan_sat.inversion, self.scan_sat.symbolrate,
			self.scan_sat.polarization, self.scan_sat.fec, self.scan_sat.pilot,
			self.scan_sat.fec_s2, self.scan_sat.fec, self.scan_sat.modulation,
			self.scan_sat.rolloff, self.scan_sat.system):
			x.addNotifier(self.retune, initial_call = False)

	def updateSats(self):
		orb_pos = self.tuning_sat.orbital_position
		if orb_pos is not None:
			transponderlist = nimmanager.getTransponders(orb_pos)
			list = []
			default = None
			for x in transponderlist:
				if x[3] == 0:
					pol = "H"
				elif x[3] == 1:
					pol = "V"
				elif x[3] == 2:
					pol = "CL"
				elif x[3] == 3:
					pol = "CR"
				else:
					pol = "??"
				if x[4] == 0:
					fec = "FEC_AUTO"
				elif x[4] == 1:
					fec = "FEC_1_2"
				elif x[4] == 2:
					fec = "FEC_2_3"
				elif x[4] == 3:
					fec = "FEC_3_4"
				elif x[4] == 4:
					fec = "FEC_5_6"
				elif x[4] == 5:
					fec = "FEC_7_8"
				elif x[4] == 6:
					fec = "FEC_8_9"
				elif x[4] == 7:
					fec = "FEC_3_5"
				elif x[4] == 8:
					fec = "FEC_4_5"
				elif x[4] == 9:
					fec = "FEC_9_10"
				elif x[4] == 15:
					fec = "FEC_None"
				else:
					fec = "FEC_Unknown"
				e = str(x[1]) + "," + str(x[2]) + "," + pol + "," + fec
				if default is None:
					default = e
				list.append(e)
			self.tuning_transponder = ConfigSelection(choices = list, default = default)
			self.tuning_transponder.addNotifier(self.retune, initial_call = False)

	def keyGo(self):
		self.retune(self.tuning_type)

	def restartPrevService(self, yesno):
		if yesno:
			if self.frontend:
				self.frontend = None
				del self.raw_channel
		else:
			self.oldref = None
		self.close(None)

	def keyCancel(self):
		if self.oldref:
			self.session.openWithCallback(self.restartPrevService, MessageBox, _("Zap back to service before satfinder?"), MessageBox.TYPE_YESNO)
		else:
			self.restartPrevService(False)

	def tune(self, transponder):
		if self.initcomplete:
			if transponder is not None:
				self.tuner.tune(transponder)

class SatNimSelection(Screen):
	skin = """
		<screen position="140,165" size="400,130" title="select Slot">
			<widget name="nimlist" position="20,10" size="360,100" />
		</screen>"""
		
	def __init__(self, session):
		Screen.__init__(self, session)

		nimlist = nimmanager.getNimListOfType("DVB-S")
		nimMenuList = []
		for x in nimlist:
			nimMenuList.append((nimmanager.nim_slots[x].friendly_full_description, x))

		self["nimlist"] = MenuList(nimMenuList)

		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"ok": self.okbuttonClick ,
			"cancel": self.close
		}, -1)

	def okbuttonClick(self):
		selection = self["nimlist"].getCurrent()[1]
		self.session.open(Satfinder, selection)

def SatfinderMain(session, **kwargs):
	nimList = nimmanager.getNimListOfType("DVB-S")
	if len(nimList) == 0:
		session.open(MessageBox, _("No satellite frontend found!!"), MessageBox.TYPE_ERROR)
	else:
		if session.nav.RecordTimer.isRecording():
			session.open(MessageBox, _("A recording is currently running. Please stop the recording before trying to start the satfinder."), MessageBox.TYPE_ERROR)
		else:
			if len(nimList) == 1:
				session.open(Satfinder, nimList[0])
			else:
				session.open(SatNimSelection)

def SatfinderStart(menuid, **kwargs):
	if menuid == "scan":
		return [(_("Satfinder"), SatfinderMain, "satfinder", None)]
	else:
		return []

def Plugins(**kwargs):
	if (nimmanager.hasNimType("DVB-S")):
		return PluginDescriptor(name=_("Satfinder"), description="Helps setting up your dish", where = PluginDescriptor.WHERE_MENU, fnc=SatfinderStart)
	else:
		return []

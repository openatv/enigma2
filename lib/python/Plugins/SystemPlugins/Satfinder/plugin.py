from enigma import eTimer, eDVBResourceManager,\
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
			parm.system = 0  # FIXMEE !! HARDCODED DVB-S (add support for DVB-S2)
			parm.modulation = 1 # FIXMEE !! HARDCODED QPSK 
			feparm = eDVBFrontendParameters()
			feparm.setDVBS(parm)
			self.lastparm = feparm
			self.frontend.tune(feparm)
	
	def retune(self):
		if self.frontend:
			self.frontend.tune(self.lastparm)

class Satfinder(ScanSetup):
	skin = """
		<screen position="90,100" size="520,400" title="Tune">
			<widget name="config" position="20,10" size="460,210" scrollbarMode="showOnDemand" />
			<widget name="introduction" position="20,360" zPosition="-10" size="350,30" font="Regular;23" />
			<eLabel text="dB:" position="23,230" size="60,22" font="Regular;21" />
			<eLabel text="SNR:" position="23,255" size="60,22" font="Regular;21" />
			<eLabel text="AGC:" position="23,280" size="60,22" font="Regular;21" />
			<eLabel text="BER:" position="23,305" size="60,22" font="Regular;21" />
			<eLabel text="Lock:" position="23,330" size="60,22" font="Regular;21" />
			<widget source="Frontend" render="Label" position="295,230" size="60,22" font="Regular;21" >
				<convert type="FrontendInfo">SNRdB</convert>
			</widget>
			<widget source="Frontend" render="Label" position="295,255" size="60,22" font="Regular;21" >
				<convert type="FrontendInfo">SNR</convert>
			</widget>
			<widget source="Frontend" render="Label" position="295,280" size="60,22" font="Regular;21" >
				<convert type="FrontendInfo">AGC</convert>
			</widget>
			<widget source="Frontend" render="Label" position="295,305" size="60,22" font="Regular;21" >
				<convert type="FrontendInfo">BER</convert>
			</widget>
			<widget source="Frontend" render="Progress" position="85,257" size="200,22" >
				<convert type="FrontendInfo">SNR</convert>
			</widget>
			<widget source="Frontend" render="Progress" position="85,282" size="200,22" >
				<convert type="FrontendInfo">AGC</convert>
			</widget>
			<widget source="Frontend" render="Progress" position="85,307" size="200,22" >
				<convert type="FrontendInfo">BER</convert>
			</widget>
			<widget source="Frontend" render="Pixmap" pixmap="key_green-fs8.png" position="295,330" zPosition="4" size="28,20" alphatest="on" >
				<convert type="FrontendInfo">LOCK</convert>
			<convert type="ConditionalShowHide" />
			</widget>
			<widget source="Frontend" render="Pixmap" pixmap="key_red-fs8.png" position="295,330" zPosition="4" size="28,20" alphatest="on" >
				<convert type="FrontendInfo">LOCK</convert>
			<convert type="ConditionalShowHide">Invert</convert>
			</widget>
		</screen>"""

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

	def createSetup(self):
		self.typeOfTuningEntry = None
		self.satEntry = None
		
		self.list = []
		self.typeOfTuningEntry = getConfigListEntry(_('Tune'), self.tuning_type)
		self.list.append(self.typeOfTuningEntry)
		self.satEntry = getConfigListEntry(_('Satellite'), self.tuning_sat)
		self.list.append(self.satEntry)
		if self.tuning_type.value == "manual_transponder":
			self.list.append(getConfigListEntry(_('Frequency'), self.scan_sat.frequency))
			self.list.append(getConfigListEntry(_('Inversion'), self.scan_sat.inversion))
			self.list.append(getConfigListEntry(_('Symbol Rate'), self.scan_sat.symbolrate))
			self.list.append(getConfigListEntry(_("Polarity"), self.scan_sat.polarization))
			self.list.append(getConfigListEntry(_("FEC"), self.scan_sat.fec))
		elif self.tuning_transponder and self.tuning_type.value == "predefined_transponder":
			self.list.append(getConfigListEntry(_("Transponder"), self.tuning_transponder))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def newConfig(self):
		if self["config"].getCurrent() == self.typeOfTuningEntry:
			self.createSetup()
		elif self["config"].getCurrent() == self.satEntry:
			self.updateSats()
			self.createSetup()

	def sat_changed(self, config_element):
		self.newConfig()
		self.retune(config_element)

	def retune(self, configElement):
		returnvalue = (0, 0, 0, 0, 0, 0, 0)
		satpos = self.tuning_sat.orbital_position
		
		if satpos is not None:
			if self.tuning_type.value == "manual_transponder":
				returnvalue = (self.scan_sat.frequency.value, self.scan_sat.symbolrate.value, self.scan_sat.polarization.index, self.scan_sat.fec.index, self.scan_sat.inversion.index, satpos)
			elif self.tuning_type.value == "predefined_transponder":
				transponder = nimmanager.getTransponders(satpos)[self.tuning_transponder.index]
				returnvalue = (int(transponder[1] / 1000), int(transponder[2] / 1000), transponder[3], transponder[4], 2, satpos)
			self.tune(returnvalue)

	def createConfig(self, foo):
		self.tuning_transponder = None
		self.tuning_type = ConfigSelection(choices = [("manual_transponder", _("Manual transponder")), ("predefined_transponder", _("Predefined transponder"))])
		self.tuning_sat = getConfigSatlist(192, nimmanager.getSatListForNim(self.feid))
		ScanSetup.createConfig(self, None)
		
		self.updateSats()
		
		self.tuning_type.addNotifier(self.retune, initial_call = False)
		self.tuning_sat.addNotifier(self.sat_changed, initial_call = False)
		self.scan_sat.frequency.addNotifier(self.retune, initial_call = False)
		self.scan_sat.inversion.addNotifier(self.retune, initial_call = False)
		self.scan_sat.symbolrate.addNotifier(self.retune, initial_call = False)
		self.scan_sat.polarization.addNotifier(self.retune, initial_call = False)
		self.scan_sat.fec.addNotifier(self.retune, initial_call = False)

	def updateSats(self):
		orb_pos = self.tuning_sat.orbital_position
		if orb_pos is not None:
			transponderlist = nimmanager.getTransponders(orb_pos)
			list = []
			for x in transponderlist:
				if x[3] == 0:
					pol = "H"
				elif x[3] == 1:
					pol = "V"
				elif x[3] == 2:
					pol = "CL"
				elif x[3] == 3:
					pol = "CR"
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
				elif x[4] == 5:
					fec = "FEC_8_9"
				elif x[4] == 6:
					fec = "FEC_None"
				list.append(str(x[1]) + "," + str(x[2]) + "," + pol + "," + fec)
			self.tuning_transponder = ConfigSelection(choices = list)
			self.tuning_transponder.addNotifier(self.retune, initial_call = False)

	def keyGo(self):
		self.retune(self.tuning_type)

	def restartPrevService(self, yesno):
		if yesno:
			if self.frontend:
				self.frontend = None
				del self.raw_channel
			self.session.nav.playService(self.oldref)
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

class NimSelection(Screen):
	skin = """
		<screen position="140,165" size="400,100" title="select Slot">
			<widget name="nimlist" position="20,10" size="360,75" />
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
				session.open(NimSelection)

def SatfinderStart(menuid, **kwargs):
	if menuid == "scan":
		return [(_("Satfinder"), SatfinderMain)]
	else:
		return []

def Plugins(**kwargs):
	if (nimmanager.hasNimType("DVB-S")):
		return PluginDescriptor(name=_("Satfinder"), description="Helps setting up your dish", where = PluginDescriptor.WHERE_SETUP, fnc=SatfinderStart)
	else:
		return []

from enigma import eTimer, eDVBSatelliteEquipmentControl, eDVBResourceManager, eDVBDiseqcCommand, eDVBResourceManagerPtr, iDVBChannelPtr, iDVBFrontendPtr, iDVBFrontend, eDVBFrontendParametersSatellite, eDVBFrontendParameters
from Screens.Screen import Screen
from Screens.ScanSetup import ScanSetup
from Screens.MessageBox import MessageBox
from Plugins.Plugin import PluginDescriptor

from Components.Label import Label
from Components.ConfigList import ConfigList
from Components.TunerInfo import TunerInfo
from Components.ActionMap import ActionMap
from Components.NimManager import nimmanager
from Components.MenuList import MenuList
from Components.config import config, ConfigSubsection, configElement_nonSave, configNothing, getConfigListEntry, configSelection, currentConfigSelectionElement, configSatlist

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
			<widget name="config" position="20,10" size="460,240" scrollbarMode="showOnDemand" />
			<widget name="introduction" position="20,360" zPosition="-10" size="350,30" font="Regular;23" />
			<widget name="snr" text="SNR:" position="0,245" size="60,22" font="Regular;21" />
			<widget name="agc" text="AGC:" position="0,270" size="60,22" font="Regular;21" />
			<widget name="ber" text="BER:" position="0,295" size="60,22" font="Regular;21" />
			<widget name="lock" text="Lock:" position="0,320" size="60,22" font="Regular;21" />
			<widget name="snr_percentage" position="220,245" size="60,22" font="Regular;21" />
			<widget name="agc_percentage" position="220,270" size="60,22" font="Regular;21" />
			<widget name="ber_value" position="220,295" size="60,22" font="Regular;21" />
			<widget name="lock_state" position="60,320" size="150,22" font="Regular;21" />
			<widget name="snr_bar" position="60,245" size="150,22" />
			<widget name="agc_bar" position="60,270" size="150,22" />
			<widget name="ber_bar" position="60,295" size="150,22" />
		</screen>"""

	def openFrontend(self):
		res_mgr = eDVBResourceManagerPtr()
		if eDVBResourceManager.getInstance(res_mgr) == 0:
			self.raw_channel = iDVBChannelPtr()
			if res_mgr.allocateRawChannel(self.raw_channel, self.feid) == 0:
				self.frontend = iDVBFrontendPtr()
				if self.raw_channel.getFrontend(self.frontend) == 0:
					return True
				else:
					print "getFrontend failed"
			else:
				print "getRawChannel failed"
		else:
			print "getResourceManager instance failed"
		return False

	def getFrontend(self):
		return self.frontend

	def __init__(self, session, feid):
		self.initcomplete = False
		self.feid = feid

		if not self.openFrontend():
			self.frontend = None

		ScanSetup.__init__(self, session)
		self.session.nav.stopService()
		self.tuner = Tuner(self.frontend)
		
		self["snr"] = Label()
		self["agc"] = Label()
		self["ber"] = Label()
		self["lock"] = Label()
		self["snr_percentage"] = TunerInfo(TunerInfo.SNR_PERCENTAGE, frontendfkt = self.getFrontend)
		self["agc_percentage"] = TunerInfo(TunerInfo.AGC_PERCENTAGE, frontendfkt = self.getFrontend)
		self["ber_value"] = TunerInfo(TunerInfo.BER_VALUE, frontendfkt = self.getFrontend)
		self["snr_bar"] = TunerInfo(TunerInfo.SNR_BAR, frontendfkt = self.getFrontend)
		self["agc_bar"] = TunerInfo(TunerInfo.AGC_BAR, frontendfkt = self.getFrontend)
		self["ber_bar"] = TunerInfo(TunerInfo.BER_BAR, frontendfkt = self.getFrontend)
		self["lock_state"] = TunerInfo(TunerInfo.LOCK_STATE, frontendfkt = self.getFrontend)

		self["introduction"].setText("")
		
		self.statusTimer = eTimer()
		self.statusTimer.timeout.get().append(self.updateStatus)
		self.statusTimer.start(50, False)

		self.initcomplete = True
		
	def updateStatus(self):
		self["snr_percentage"].update()
		self["agc_percentage"].update()
		self["ber_value"].update()
		self["snr_bar"].update()
		self["agc_bar"].update()
		self["ber_bar"].update()
		self["lock_state"].update()

	def createSetup(self):
		self.typeOfTuningEntry = None
		self.satEntry = None

		self.list = []
		self.typeOfTuningEntry = getConfigListEntry(_('Tune'), config.tuning.type)
		self.list.append(self.typeOfTuningEntry)
		self.satEntry = getConfigListEntry(_('Satellite'), config.tuning.sat)
		self.list.append(self.satEntry)
		if currentConfigSelectionElement(config.tuning.type) == "manual_transponder":
			self.list.append(getConfigListEntry(_('Frequency'), config.scan.sat.frequency))
			self.list.append(getConfigListEntry(_('Inversion'), config.scan.sat.inversion))
			self.list.append(getConfigListEntry(_('Symbol Rate'), config.scan.sat.symbolrate))
			self.list.append(getConfigListEntry(_("Polarity"), config.scan.sat.polarization))
			self.list.append(getConfigListEntry(_("FEC"), config.scan.sat.fec))
		elif currentConfigSelectionElement(config.tuning.type) == "predefined_transponder":
			self.list.append(getConfigListEntry(_("Transponder"), config.tuning.transponder))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def newConfig(self):
		if self["config"].getCurrent() == self.typeOfTuningEntry:
			self.createSetup()
		elif self["config"].getCurrent() == self.satEntry:
			self.updateSats()
			self.createSetup()

	def retune(self, configElement):
		returnvalue = (0, 0, 0, 0, 0, 0, 0)
		satpos = config.tuning.sat.vals[config.tuning.sat.value][1]
		if currentConfigSelectionElement(config.tuning.type) == "manual_transponder":
			returnvalue = (config.scan.sat.frequency.value[0], config.scan.sat.symbolrate.value[0], config.scan.sat.polarization.value, config.scan.sat.fec.value, config.scan.sat.inversion.value, satpos)
		elif currentConfigSelectionElement(config.tuning.type) == "predefined_transponder":
			transponder = nimmanager.getTransponders(config.tuning.sat.vals[config.tuning.sat.value][1])[config.tuning.transponder.value]
			returnvalue = (int(transponder[1] / 1000), int(transponder[2] / 1000), transponder[3], transponder[4], 2, config.tuning.sat.vals[config.tuning.sat.value][1], satpos)
		self.tune(returnvalue)

	def createConfig(self, foo):
		config.tuning = ConfigSubsection()
		
		config.tuning.type = configElement_nonSave("config.tuning.type", configSelection, 0, (("manual_transponder", _("Manual transponder")), ("predefined_transponder", _("Predefined satellite"))))
		config.tuning.sat = configElement_nonSave("config.tuning.sat", configSatlist, 192, nimmanager.getSatListForNim(self.feid))
		ScanSetup.createConfig(self, None)
		
		self.updateSats()

		config.tuning.type.addNotifier(self.retune)
		config.tuning.sat.addNotifier(self.retune)
		config.scan.sat.frequency.addNotifier(self.retune)
		config.scan.sat.inversion.addNotifier(self.retune)
		config.scan.sat.symbolrate.addNotifier(self.retune)
		config.scan.sat.polarization.addNotifier(self.retune)
		config.scan.sat.fec.addNotifier(self.retune)

	def updateSats(self):
		satnum = config.tuning.sat.value
		satlist = config.tuning.sat.vals
		if len(satlist):
			transponderlist = nimmanager.getTransponders(satlist[satnum][1])
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
			config.tuning.transponder = configElement_nonSave("config.tuning.transponder", configSelection, 0, list)
			config.tuning.transponder.addNotifier(self.retune)
	
	def keyGo(self):
		returnvalue = (0, 0, 0, 0, 0, 0, 0)
		satpos = config.tuning.sat.vals[config.tuning.sat.value][1]
		if currentConfigSelectionElement(config.tuning.type) == "manual_transponder":
			returnvalue = (config.scan.sat.frequency.value[0], config.scan.sat.symbolrate.value[0], config.scan.sat.polarization.value, config.scan.sat.fec.value, config.scan.sat.inversion.value, satpos)
		elif currentConfigSelectionElement(config.tuning.type) == "predefined_transponder":
			transponder = nimmanager.getTransponders(config.tuning.sat.vals[config.tuning.sat.value][1])[config.tuning.transponder.value]
			returnvalue = (int(transponder[1] / 1000), int(transponder[2] / 1000), transponder[3], transponder[4], 2, config.tuning.sat.vals[config.tuning.sat.value][1], satpos)
		self.close(returnvalue)

	def keyCancel(self):
		self.close(None)
		
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

		nimlist = nimmanager.getNimListOfType(nimmanager.nimType["DVB-S"])
		nimMenuList = []
		for x in nimlist:
			nimMenuList.append((_("NIM ") + (["A", "B", "C", "D"][x]) + ": " + nimmanager.getNimName(x) + " (" + nimmanager.getNimTypeName(x) + ")", x))
		
		self["nimlist"] = MenuList(nimMenuList)

		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"ok": self.okbuttonClick ,
			"cancel": self.close
		}, -1)

	def okbuttonClick(self):
		selection = self["nimlist"].getCurrent()
		self.session.open(Satfinder, selection[1])

def SatfinderMain(session, **kwargs):
	nimList = nimmanager.getNimListOfType(nimmanager.nimType["DVB-S"])
	if len(nimList) == 0:
		session.open(MessageBox, _("No positioner capable frontend found."), MessageBox.TYPE_ERROR)
	else:
		if session.nav.RecordTimer.isRecording():
			session.open(MessageBox, _("A recording is currently running. Please stop the recording before trying to configure the positioner."), MessageBox.TYPE_ERROR)
		else:
			if len(nimList) == 1:
				session.open(Satfinder, nimList[0])
			elif len(nimList) > 1:
				session.open(NimSelection)
			else:
				session.open(MessageBox, _("No tuner is configured for use with a diseqc positioner!"), MessageBox.TYPE_ERROR)

def Plugins(**kwargs):
	return PluginDescriptor(name="Satfinder", description="Helps setting up your dish", where = PluginDescriptor.WHERE_PLUGINMENU, fnc=SatfinderMain)

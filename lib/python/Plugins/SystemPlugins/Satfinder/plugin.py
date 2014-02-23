from enigma import eDVBResourceManager,\
	eDVBFrontendParametersSatellite, eDVBFrontendParameters

from Screens.Screen import Screen
from Screens.ScanSetup import ScanSetup
from Screens.ServiceScan import ServiceScan
from Screens.MessageBox import MessageBox
from Plugins.Plugin import PluginDescriptor

from Components.Label import Label
from Components.Sources.FrontendStatus import FrontendStatus
from Components.ActionMap import ActionMap
from Components.NimManager import nimmanager, getConfigSatlist
from Components.MenuList import MenuList
from Components.config import ConfigSelection, getConfigListEntry
from Components.TuneTest import Tuner

class Satfinder(ScanSetup, ServiceScan):
	def __init__(self, session):
		self.initcomplete = False
		self.frontendData = None
		service = session and session.nav.getCurrentService()
		feinfo = service and service.frontendInfo()
		self.frontendData = feinfo and feinfo.getAll(True)
		del feinfo
		del service

		ScanSetup.__init__(self, session)
		self.setTitle(_("Satfinder"))
		self["introduction"].setText(_("Press OK to scan"))
		self["Frontend"] = FrontendStatus(frontend_source = lambda : self.frontend, update_interval = 100)

		self["actions"] = ActionMap(["SetupActions"],
		{
			"save": self.keyGoScan,
			"ok": self.keyGoScan,
			"cancel": self.keyCancel,
		}, -3)

		self.initcomplete = True
		self.session.postScanService = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		self.onClose.append(self.__onClose)
		self.onShow.append(self.prepareFrontend)

	def openFrontend(self):
		res_mgr = eDVBResourceManager.getInstance()
		if res_mgr:
			self.raw_channel = res_mgr.allocateRawChannel(self.feid)
			if self.raw_channel:
				self.frontend = self.raw_channel.getFrontend()
				if self.frontend:
					return True
		return False

	def prepareFrontend(self):
		self.frontend = None
		if not self.openFrontend():
			self.session.nav.stopService()
			if not self.openFrontend():
				if self.session.pipshown: # try to disable pip
					if hasattr(self.session, 'infobar'):
						if self.session.infobar.servicelist.dopipzap:
							self.session.infobar.servicelist.togglePipzap()
					if hasattr(self.session, 'pip'):
						del self.session.pip
					self.session.pipshown = False
					if not self.openFrontend():
						self.frontend = None # in normal case this should not happen
		self.tuner = Tuner(self.frontend)
		self.retune(None)

	def __onClose(self):
		self.session.nav.playService(self.session.postScanService)

	def createSetup(self):
		self.list = []
		self.satfinderTunerEntry = getConfigListEntry(_("Tuner"), self.satfinder_scan_nims)
		self.list.append(self.satfinderTunerEntry)
		self.tuning_sat = self.scan_satselection[self.getSelectedSatIndex(self.feid)]
		self.satEntry = getConfigListEntry(_('Satellite'), self.tuning_sat)
		self.list.append(self.satEntry)
		self.updatePreDefTransponders()
		self.typeOfTuningEntry = getConfigListEntry(_('Tune'), self.tuning_type)
		self.list.append(self.typeOfTuningEntry)

		nim = nimmanager.nim_slots[self.feid]

		if self.tuning_type.value == "manual_transponder":
			if nim.isCompatible("DVB-S2"):
				self.systemEntry = getConfigListEntry(_('System'), self.scan_sat.system)
				self.list.append(self.systemEntry)
			else:
				# downgrade to dvb-s, in case a -s2 config was active
				self.scan_sat.system.value = eDVBFrontendParametersSatellite.System_DVB_S
			self.list.append(getConfigListEntry(_('Frequency'), self.scan_sat.frequency))
			self.list.append(getConfigListEntry(_('Polarization'), self.scan_sat.polarization))
			self.list.append(getConfigListEntry(_('Symbol rate'), self.scan_sat.symbolrate))
			self.list.append(getConfigListEntry(_('Inversion'), self.scan_sat.inversion))
			if self.scan_sat.system.value == eDVBFrontendParametersSatellite.System_DVB_S:
				self.list.append(getConfigListEntry(_("FEC"), self.scan_sat.fec))
			elif self.scan_sat.system.value == eDVBFrontendParametersSatellite.System_DVB_S2:
				self.list.append(getConfigListEntry(_("FEC"), self.scan_sat.fec_s2))
				self.modulationEntry = getConfigListEntry(_('Modulation'), self.scan_sat.modulation)
				self.list.append(self.modulationEntry)
				self.list.append(getConfigListEntry(_('Roll-off'), self.scan_sat.rolloff))
				self.list.append(getConfigListEntry(_('Pilot'), self.scan_sat.pilot))
		elif self.preDefTransponders and self.tuning_type.value == "predefined_transponder":
			self.list.append(getConfigListEntry(_("Transponder"), self.preDefTransponders))
		self["config"].list = self.list
		self["config"].l.setList(self.list)
		self.retune(None)

	def newConfig(self):
		cur = self["config"].getCurrent()
		if cur in (self.typeOfTuningEntry, self.systemEntry):
			self.createSetup()
		elif cur == self.satfinderTunerEntry:
			self.feid = int(self.satfinder_scan_nims.value)
			self.prepareFrontend()
			self.createSetup()
		elif cur == self.satEntry:
			self.createSetup()

	def retune(self, configElement):
		returnvalue = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
		if not self.tuning_sat.value:
			return
		satpos = int(self.tuning_sat.value)
		if self.tuning_type.value == "manual_transponder":
			if self.scan_sat.system.value == eDVBFrontendParametersSatellite.System_DVB_S2:
				fec = self.scan_sat.fec_s2.value
			else:
				fec = self.scan_sat.fec.value
			returnvalue = (
				self.scan_sat.frequency.value,
				self.scan_sat.symbolrate.value,
				self.scan_sat.polarization.value,
				fec,
				self.scan_sat.inversion.value,
				satpos,
				self.scan_sat.system.value,
				self.scan_sat.modulation.value,
				self.scan_sat.rolloff.value,
				self.scan_sat.pilot.value)
			self.tune(returnvalue)
		elif self.tuning_type.value == "predefined_transponder":
			tps = nimmanager.getTransponders(satpos)
			l = len(tps)
			if l > self.preDefTransponders.index:
				transponder = tps[self.preDefTransponders.index]
				returnvalue = (transponder[1] / 1000, transponder[2] / 1000,
					transponder[3], transponder[4], 2, satpos, transponder[5], transponder[6], transponder[8], transponder[9])
				self.tune(returnvalue)

	def createConfig(self, foo):
		self.preDefTransponders = None
		self.tuning_type = ConfigSelection(choices = [("manual_transponder", _("User defined transponder")), ("predefined_transponder", _("Predefined transponder"))])
		self.orbital_position = 192
		if self.frontendData and self.frontendData.has_key('orbital_position'):
			self.orbital_position = self.frontendData['orbital_position']
		ScanSetup.createConfig(self, self.frontendData)

		for x in (self.tuning_type, self.scan_sat.frequency,
			self.scan_sat.inversion, self.scan_sat.symbolrate,
			self.scan_sat.polarization, self.scan_sat.fec, self.scan_sat.pilot,
			self.scan_sat.fec_s2, self.scan_sat.fec, self.scan_sat.modulation,
			self.scan_sat.rolloff, self.scan_sat.system):
			x.addNotifier(self.retune, initial_call = False)

		satfinder_nim_list = []
		for n in nimmanager.nim_slots:
			if not n.isCompatible("DVB-S"):
				continue
			if n.config_mode  in ("loopthrough", "satposdepends", "nothing"):
				continue
			if n.config_mode == "advanced" and len(nimmanager.getSatListForNim(n.slot)) < 1:
				continue
			satfinder_nim_list.append((str(n.slot), n.friendly_full_description))
		self.satfinder_scan_nims = ConfigSelection(choices = satfinder_nim_list)
		self.feid = int(self.satfinder_scan_nims.value)

		self.satList = []
		self.scan_satselection = []
		for slot in nimmanager.nim_slots:
			if slot.isCompatible("DVB-S"):
				self.satList.append(nimmanager.getSatListForNim(slot.slot))
				self.scan_satselection.append(getConfigSatlist(self.orbital_position, self.satList[slot.slot]))
			else:
				self.satList.append(None)

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

	def updatePreDefTransponders(self):
		ScanSetup.predefinedTranspondersList(self, self.tuning_sat.orbital_position)
		if self.preDefTransponders:
			self.preDefTransponders.addNotifier(self.retune, initial_call=False)

	def keyGoScan(self):
		self.frontend = None
		del self.raw_channel
		tlist = []
		self.addSatTransponder(tlist,
			self.transponder[0], # frequency
			self.transponder[1], # sr
			self.transponder[2], # pol
			self.transponder[3], # fec
			self.transponder[4], # inversion
			self.tuning_sat.orbital_position,
			self.transponder[6], # system
			self.transponder[7], # modulation
			self.transponder[8], # rolloff
			self.transponder[9]  # pilot
		)
		self.startScan(tlist, self.feid)

	def startScan(self, tlist, feid):
		flags = 0
		networkid = 0
		self.session.openWithCallback(self.startScanCallback, ServiceScan, [{"transponders": tlist, "feid": feid, "flags": flags, "networkid": networkid}])

	def startScanCallback(self, answer):
		if answer:
			self.doCloseRecursive()

	def keyCancel(self):
		if self.session.postScanService and self.frontend:
			self.frontend = None
			del self.raw_channel
		self.close(False)

	def doCloseRecursive(self):
		if self.session.postScanService and self.frontend:
			self.frontend = None
			del self.raw_channel
		self.close(True)

	def tune(self, transponder):
		if self.initcomplete:
			if transponder is not None:
				self.tuner.tune(transponder)
				self.transponder = transponder

def SatfinderMain(session, close=None, **kwargs):
	nims = nimmanager.getNimListOfType("DVB-S")

	nimList = []
	for x in nims:
		if nimmanager.getNimConfig(x).configMode.value in ("loopthrough", "satposdepends", "nothing"):
			continue
		if nimmanager.getNimConfig(x).configMode.value == "advanced" and len(nimmanager.getSatListForNim(x)) < 1:
			continue
		nimList.append(x)

	if len(nimList) == 0:
		session.open(MessageBox, _("No satellites configured. Plese check your tuner setup."), MessageBox.TYPE_ERROR)
	else:
		if session.nav.RecordTimer.isRecording():
			session.open(MessageBox, _("A recording is currently running. Please stop the recording before trying to start the satfinder."), MessageBox.TYPE_ERROR)
		else:
			session.openWithCallback(close, Satfinder)

def SatfinderStart(menuid, **kwargs):
	if menuid == "scan":
		return [(_("Satfinder"), SatfinderMain, "satfinder", None)]
	else:
		return []

def Plugins(**kwargs):
	if (nimmanager.hasNimType("DVB-S")):
		return PluginDescriptor(name=_("Satfinder"), description=_("Helps setting up your dish"), where = PluginDescriptor.WHERE_MENU, needsRestart = False, fnc=SatfinderStart)
	else:
		return []

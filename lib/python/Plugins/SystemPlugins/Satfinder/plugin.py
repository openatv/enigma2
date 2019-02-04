from enigma import eDVBResourceManager,\
	eDVBFrontendParametersSatellite, eDVBFrontendParametersTerrestrial, eDVBFrontendParametersATSC, iDVBFrontend

from Screens.ScanSetup import ScanSetup, buildTerTransponder
from Screens.ServiceScan import ServiceScan
from Screens.MessageBox import MessageBox
from Plugins.Plugin import PluginDescriptor

from Components.Sources.FrontendStatus import FrontendStatus
from Components.ActionMap import ActionMap
from Components.NimManager import nimmanager, getConfigSatlist
from Components.config import config, ConfigSelection, getConfigListEntry
from Components.TuneTest import Tuner
from Tools.Transponder import getChannelNumber, channel2frequency

class Satfinder(ScanSetup, ServiceScan):
	def __init__(self, session):
		self.initcomplete = False
		service = session and session.nav.getCurrentService()
		feinfo = service and service.frontendInfo()
		self.frontendData = feinfo and feinfo.getAll(True)
		del feinfo
		del service


		self.systemEntry = None
		self.systemEntryATSC = None
		self.satfinderTunerEntry = None
		self.satEntry = None
		self.frequencyEntry = None
		self.polarizationEntry = None
		self.symbolrateEntry = None
		self.inversionEntry = None
		self.rolloffEntry = None
		self.pilotEntry = None
		self.fecEntry = None
		self.transponder = None

		ScanSetup.__init__(self, session)
		self.setTitle(_("Signal Finder"))
		self["introduction"].setText(_("Press OK to scan"))
		self["Frontend"] = FrontendStatus(frontend_source = lambda : self.frontend, update_interval = 100)

		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
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
			fe_id = int(self.scan_nims.value)
			self.raw_channel = res_mgr.allocateRawChannel(fe_id)
			if self.raw_channel:
				self.frontend = self.raw_channel.getFrontend()
				if self.frontend:
					return True
		return False

	def prepareFrontend(self):
		self.frontend = None
		try:
			if not self.openFrontend():
				self.session.nav.stopService()
				if not self.openFrontend():
					if self.session.pipshown:
						from Screens.InfoBar import InfoBar
						InfoBar.instance and hasattr(InfoBar.instance, "showPiP") and InfoBar.instance.showPiP()
						if not self.openFrontend():
							self.frontend = None # in normal case this should not happen
			self.tuner = Tuner(self.frontend)
			self.createSetup()
			self.retune()
		except:
			pass

	def __onClose(self):
		self.session.nav.playService(self.session.postScanService)

	def newConfig(self):
#		self.transponder = None
		cur = self["config"].getCurrent()
		print"cur ", cur

		if cur == self.tunerEntry:
			self.feid = int(self.scan_nims.value)
			self.prepareFrontend()
			if self.frontend == None and self.session.nav.RecordTimer.isRecording():
				slot = nimmanager.nim_slots[self.feid]
				msg = _("%s not available.") % slot.getSlotName()
				msg += _("\nRecording in progress.")
				self.session.open(MessageBox, msg, MessageBox.TYPE_ERROR)
		else:
			ScanSetup.newConfig(self)
		if cur[1].value == "single_transponder":
			self.retune()


	def createSetup(self):
		ScanSetup.createSetup(self)

#manipulate "config", remove "self.scan_networkScan", "self.scan_clearallservices" and "self.scan_onlyfree"
		tlist = self["config"].getList()
		for x in (self.scan_networkScan, self.scan_clearallservices, self.scan_onlyfree):
			for y in tlist:
				if x == y[1]:
					tlist.remove(y)
		self["config"].list = tlist
		self["config"].l.setList(tlist)

#manipulate choices, we need only "single_transponder","predefined_transponder"
		for scan_type in (self.scan_type, self.scan_typecable, self.scan_typeterrestrial, self.scan_typeatsc):
			slist = scan_type.choices.choices
			dlist = []
			for x in slist:
				if x[0] in ("single_transponder","predefined_transponder"):
					dlist.append(x)
			scan_type.choices.choices = dlist

	def TunerTypeChanged(self):
		fe_id = int(self.scan_nims.value)
		multiType = config.Nims[fe_id].multiType
		system = multiType.getText()
		if (system in ('DVB-S','DVB-S2') and config.Nims[fe_id].dvbs.configMode.value == "nothing") or \
			(system in ('DVB-T','DVB-T2') and config.Nims[fe_id].dvbt.configMode.value == "nothing") or \
			(system in ('DVB-C') and config.Nims[fe_id].dvbc.configMode.value == "nothing") or \
			(system in ('ATSC') and config.Nims[fe_id].atsc.configMode.value == "nothing") :
			return
		slot = nimmanager.nim_slots[fe_id]
		print "dvb_api_version ",iDVBFrontend.dvb_api_version
		self.frontend = None
		if not self.openFrontend():
			self.session.nav.stopService()
			if not self.openFrontend():
				if self.session.pipshown:
					from Screens.InfoBar import InfoBar
					InfoBar.instance and hasattr(InfoBar.instance, "showPiP") and InfoBar.instance.showPiP()
					if not self.openFrontend():
						self.frontend = None # in normal case this should not happen
		self.tuner = Tuner(self.frontend)

		if slot.isMultiType():
			eDVBResourceManager.getInstance().setFrontendType(slot.frontend_id, "dummy", False) #to force a clear of m_delsys_whitelist
			types = slot.getMultiTypeList()
			for FeType in types.itervalues():
				if FeType in ("DVB-S", "DVB-S2", "DVB-S2X") and config.Nims[slot.slot].dvbs.configMode.value == "nothing":
					continue
				elif FeType in ("DVB-T", "DVB-T2") and config.Nims[slot.slot].dvbt.configMode.value == "nothing":
					continue
				elif FeType in ("DVB-C", "DVB-C2") and config.Nims[slot.slot].dvbc.configMode.value == "nothing":
					continue
				elif FeType in ("ATSC") and config.Nims[slot.slot].atsc.configMode.value == "nothing":
					continue
				eDVBResourceManager.getInstance().setFrontendType(slot.frontend_id, FeType, True)
		else:
			eDVBResourceManager.getInstance().setFrontendType(slot.frontend_id, slot.getType())


#			if not path.exists("/proc/stb/frontend/%d/mode" % fe_id) and iDVBFrontend.dvb_api_version >= 5:
		print "api >=5 and new style tuner driver"
		if self.frontend:
			if system == 'DVB-C':
				ret = self.frontend.changeType(iDVBFrontend.feCable)
			elif system in ('DVB-T','DVB-T2'):
				ret = self.frontend.changeType(iDVBFrontend.feTerrestrial)
			elif system in ('DVB-S','DVB-S2'):
				ret = self.frontend.changeType(iDVBFrontend.feSatellite)
			elif system == 'ATSC':
				ret = self.frontend.changeType(iDVBFrontend.feATSC)
			else:
				ret = False
			if not ret:
				print "%d: tunerTypeChange to '%s' failed" %(fe_id, system)
			else:
				print "new system ",system
		else:
			print "%d: tunerTypeChange to '%s' failed (BUSY)" %(fe_id, multiType.getText())
		self.retune()

	def createConfig(self):
		ScanSetup.createConfig(self)
		for x in (
			self.scan_sat.frequency,
			self.scan_satselection[int(self.scan_nims.value)],
			self.scan_sat.symbolrate,
			self.scan_sat.is_id,
			self.scan_sat.pls_mode,
			self.scan_sat.pls_code,
			self.scan_sat.t2mi_pid,
			self.scan_sat.t2mi_plp,
			self.scan_ter.channel,
			self.scan_ter.frequency,
			self.scan_ter.inversion,
			self.scan_ter.bandwidth, self.scan_ter.fechigh, self.scan_ter.feclow,
			self.scan_ter.modulation, self.scan_ter.transmission,
			self.scan_ter.guard, self.scan_ter.hierarchy,
			self.scan_ter.plp_id,
			self.scan_cab.frequency, self.scan_cab.inversion, self.scan_cab.symbolrate,
			self.scan_cab.modulation, self.scan_cab.fec,
			self.scan_ats.frequency, self.scan_ats.modulation, self.scan_ats.inversion,
			self.scan_ats.system,

			):
			if x is not None:
				x.clearNotifiers()
				x.addNotifier(self.TriggeredByConfigElement, initial_call = False)

	def TriggeredByConfigElement(self, configElement):
		self.retune()

	def retune(self):
		nim = nimmanager.nim_slots[int(self.scan_nims.value)]
		if nim.isCompatible("DVB-S") and nim.config.dvbs.configMode.value != "nothing":
			return self.retuneSat()
		if nim.isCompatible("DVB-T") and nim.config.dvbt.configMode.value != "nothing":
			return self.retuneTerr()
		if nim.isCompatible("DVB-C") and nim.config.dvbc.configMode.value != "nothing":
			return self.retuneCab()
		if nim.isCompatible("ATSC") and nim.config.atsc.configMode.value != "nothing":
			return self.retuneATSC()
		self.frontend = None
		self.raw_channel = None
		print "error: tuner not enabled/supported", nim.getType()

	def retuneCab(self):
		if self.initcomplete:
			if self.scan_typecable.value == "single_transponder":
				transponder = (
					self.scan_cab.frequency.value*1000,
					self.scan_cab.symbolrate.value*1000,
					self.scan_cab.modulation.value,
					self.scan_cab.fec.value,
					self.scan_cab.inversion.value
				)
				self.tuner.tuneCab(transponder)
				self.transponder = transponder
			elif self.scan_typecable.value == "predefined_transponder":
				if self.CableTransponders is not None:
					tps = nimmanager.getTranspondersCable(int(self.scan_nims.value))
					if len(tps) > self.CableTransponders.index :
						tp = tps[self.CableTransponders.index]
						# tp = 0 transponder type, 1 freq, 2 sym, 3 mod, 4 fec, 5 inv, 6 sys
						transponder = (tp[1], tp[2], tp[3], tp[4], tp[5])
						self.tuner.tuneCab(transponder)
						self.transponder = transponder

	def retuneTerr(self):
		if self.initcomplete:
			if self.scan_input_as.value == "channel":
				frequency = channel2frequency(self.scan_ter.channel.value, self.ter_tnumber)
			else:
				frequency = self.scan_ter.frequency.value * 1000
			if self.scan_typeterrestrial.value == "single_transponder":
				transponder = [
					2, #TERRESTRIAL
					frequency,
					self.scan_ter.bandwidth.value,
					self.scan_ter.modulation.value,
					self.scan_ter.fechigh.value,
					self.scan_ter.feclow.value,
					self.scan_ter.guard.value,
					self.scan_ter.transmission.value,
					self.scan_ter.hierarchy.value,
					self.scan_ter.inversion.value,
					self.scan_ter.system.value,
					self.scan_ter.plp_id.value]
				self.tuner.tuneTerr(transponder[1], transponder[9], transponder[2], transponder[4], transponder[5], transponder[3], transponder[7], transponder[6], transponder[8], transponder[10], transponder[11])
				self.transponder = transponder
			elif self.scan_typeterrestrial.value == "predefined_transponder":
				if self.TerrestrialTransponders is not None:
					region = nimmanager.getTerrestrialDescription(int(self.scan_nims.value))
					tps = nimmanager.getTranspondersTerrestrial(region)
					if len(tps) > self.TerrestrialTransponders.index :
						transponder = tps[self.TerrestrialTransponders.index]
						# frequency 1, inversion 9, bandwidth 2, fechigh 4, feclow 5, modulation 3, transmission 7, guard 6, hierarchy 8, system 10, plp_id 11
						self.tuner.tuneTerr(transponder[1], transponder[9], transponder[2], transponder[4], transponder[5], transponder[3], transponder[7], transponder[6], transponder[8], transponder[10], transponder[11])
						self.transponder = transponder

	def retuneSat(self):
		fe_id = int(self.scan_nims.value)
		nimsats = self.satList[fe_id]
		selsatidx = self.scan_satselection[fe_id].index
		if len(nimsats):
			orbpos = nimsats[selsatidx][0]
			if self.initcomplete:
				if self.scan_type.value == "single_transponder":
					if self.scan_sat.system.value == eDVBFrontendParametersSatellite.System_DVB_S2:
						fec = self.scan_sat.fec_s2.value
					else:
						fec = self.scan_sat.fec.value

					if self.scan_sat.t2mi_pid.value > 0 and self.scan_sat.t2mi_plp.value >= 0:
						t2mi_plp_id = (self.scan_sat.t2mi_pid.value<<16)|self.scan_sat.t2mi_plp.value
					else:
						t2mi_plp_id = eDVBFrontendParametersSatellite.No_T2MI_PLP_Id
						
					transponder = (
						self.scan_sat.frequency.value,
						self.scan_sat.symbolrate.value,
						self.scan_sat.polarization.value,
						fec,
						self.scan_sat.inversion.value,
						orbpos,
						self.scan_sat.system.value,
						self.scan_sat.modulation.value,
						self.scan_sat.rolloff.value,
						self.scan_sat.pilot.value,
						self.scan_sat.is_id.value,
						self.scan_sat.pls_mode.value,
						self.scan_sat.pls_code.value,
						t2mi_plp_id)
					self.tuner.tune(transponder)
					self.transponder = transponder
				elif self.scan_type.value == "predefined_transponder":
					tps = nimmanager.getTransponders(orbpos)
					if len(tps) > self.preDefTransponders.index:
						tp = tps[self.preDefTransponders.index]
						transponder = (tp[1] / 1000, tp[2] / 1000,
							tp[3], tp[4], 2, orbpos, tp[5], tp[6], tp[8], tp[9], tp[10], tp[11], tp[12], tp[13])
						self.tuner.tune(transponder)
						self.transponder = transponder

	def retuneATSC(self):
		if self.initcomplete:
			if self.scan_typeatsc.value == "single_transponder":
				transponder = (
					self.scan_ats.frequency.value*1000,
					self.scan_ats.modulation.value,
					self.scan_ats.inversion.value,
					self.scan_ats.system.value,
				)
				if self.initcomplete:
					self.tuner.tuneATSC(transponder)
				self.transponder = transponder
			elif self.scan_typeatsc.value == "predefined_transponder":
				tps = nimmanager.getTranspondersATSC(int(self.scan_nims.value))
				if tps and len(tps) > self.ATSCTransponders.index:
					tp = tps[self.ATSCTransponders.index]
					transponder = (tp[1], tp[2], tp[3], tp[4])
					if self.initcomplete:
						self.tuner.tuneATSC(transponder)
					self.transponder = transponder

	def keyGoScan(self):
		if self.transponder is None:
			print "error: no transponder data"
			return
		fe_id = int(self.scan_nims.value)
		nim = nimmanager.nim_slots[fe_id]
		self.frontend = None
		if self.raw_channel:
			self.raw_channel = None
		tlist = []
		if nim.isCompatible("DVB-S"):
			nimsats = self.satList[fe_id]
			selsatidx = self.scan_satselection[fe_id].index
			if len(nimsats):
				orbpos = nimsats[selsatidx][0]
				self.addSatTransponder(tlist,
					self.transponder[0], # frequency
					self.transponder[1], # sr
					self.transponder[2], # pol
					self.transponder[3], # fec
					self.transponder[4], # inversion
					orbpos,
					self.transponder[6], # system
					self.transponder[7], # modulation
					self.transponder[8], # rolloff
					self.transponder[9], # pilot
					self.transponder[10],# input stream id
					self.transponder[11],# pls mode
					self.transponder[12], # pls code
					self.transponder[13] # t2mi_plp_id
				)
		elif nim.isCompatible("DVB-T"):
			parm = buildTerTransponder(
				self.transponder[1],  # frequency
				self.transponder[9],  # inversion
				self.transponder[2],  # bandwidth
				self.transponder[4],  # fechigh
				self.transponder[5],  # feclow
				self.transponder[3],  # modulation
				self.transponder[7],  # transmission
				self.transponder[6],  # guard
				self.transponder[8],  # hierarchy
				self.transponder[10], # system
				self.transponder[11]  # plp_id
			)
			tlist.append(parm)
		elif nim.isCompatible("DVB-C"):
			self.addCabTransponder(tlist,
				self.transponder[0], # frequency
				self.transponder[1], # sr
				self.transponder[2], # modulation
				self.transponder[3], # fec_inner
				self.transponder[4]  # inversion
			)
		elif nim.isCompatible("ATSC"):
			self.addATSCTransponder(tlist,
				self.transponder[0], # frequency
				self.transponder[1], # modulation
				self.transponder[2], # inversion
				self.transponder[3]  # system
			)
		else:
			print "error: tuner not enabled/supported", nim.getType()
		self.startScan(tlist, fe_id)

	def startScan(self, tlist, feid):
		flags = 0
		networkid = 0
		self.session.openWithCallback(self.startScanCallback, ServiceScan, [{"transponders": tlist, "feid": feid, "flags": flags, "networkid": networkid}])

	def startScanCallback(self, answer=None):
		if answer:
			self.doCloseRecursive()

	def keyCancel(self):
		if self.session.postScanService and self.frontend:
			self.frontend = None
			self.raw_channel = None
		self.close(False)

	def doCloseRecursive(self):
		if self.session.postScanService and self.frontend:
			self.frontend = None
			self.raw_channel = None
		self.close(True)

def SatfinderMain(session, close=None, **kwargs):
	nims = nimmanager.nim_slots
	nimList = []
	for n in nims:
		if n.isMultiType():
			if not (n.isCompatible("DVB-S") or n.isCompatible("DVB-T") or n.isCompatible("DVB-C") or n.isCompatible("ATSC")):
				continue
		else:
			if not (n.isCompatible("DVB-S") or n.isCompatible("DVB-T") or n.isCompatible("DVB-C") or n.isCompatible("ATSC")):
				continue
			if n.isCompatible("DVB-S") and n.config.dvbs.configMode.value  in ("loopthrough", "satposdepends", "nothing"):
				continue
			if n.isCompatible("DVB-S") and n.config.dvbs.configMode.value == "advanced" and len(nimmanager.getSatListForNim(n.slot)) < 1:
				continue
		nimList.append(n)

	if len(nimList) == 0:
		session.open(MessageBox, _("No satellite, terrestrial or cable tuner is configured. Please check your tuner setup."), MessageBox.TYPE_ERROR)
	else:
		session.openWithCallback(close, Satfinder)

def SatfinderStart(menuid, **kwargs):
	if menuid == "scan":
		return [(_("Signal Finder"), SatfinderMain, "satfinder", None)]
	else:
		return []

def Plugins(**kwargs):
	if nimmanager.hasNimType("DVB-S") or nimmanager.hasNimType("DVB-T") or nimmanager.hasNimType("DVB-C") or nimmanager.hasNimType("ATSC"):
		return PluginDescriptor(name=_("Signal Finder"), description=_("Helps setting up your signal"), where = PluginDescriptor.WHERE_MENU, needsRestart = False, fnc=SatfinderStart)
	else:
		return []

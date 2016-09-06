from enigma import eComponentScan, iDVBFrontend, eTimer
from Components.NimManager import nimmanager as nimmgr
from Components.Converter.ChannelNumbers import channelnumbers

class ServiceScan:

	Idle = 1
	Running = 2
	Done = 3
	Error = 4
	DonePartially = 5

	Errors = {
		0: _("error starting scanning"),
		1: _("error while scanning"),
		2: _("no resource manager"),
		3: _("no channel list")
		}

	def scanStatusChanged(self):
		if self.state == self.Running:
			self.progressbar.setValue(self.scan.getProgress())
			self.lcd_summary.updateProgress(self.scan.getProgress())
			if self.scan.isDone():
				errcode = self.scan.getError()

				if errcode == 0:
					self.state = self.DonePartially
					self.servicelist.listAll()
				else:
					self.state = self.Error
					self.errorcode = errcode
				self.network.setText("")
				self.transponder.setText("")
			else:
				result = self.foundServices + self.scan.getNumServices()
				percentage = self.scan.getProgress()
				if percentage > 99:
					percentage = 99
				#TRANSLATORS: The stb is performing a channel scan, progress percentage is printed in '%d' (and '%%' will show a single '%' symbol)
				message = ngettext("Scanning - %d%% completed", "Scanning - %d%% completed", percentage) % percentage
				message += ", "
				#TRANSLATORS: Intermediate scanning result, '%d' channel(s) have been found so far
				message += ngettext("%d channel found", "%d channels found", result) % result
				self.text.setText(message)
				transponder = self.scan.getCurrentTransponder()
				network = ""
				tp_text = ""
				if transponder:
					tp_type = transponder.getSystem()
					if tp_type == iDVBFrontend.feSatellite:
						network = _("Satellite")
						tp = transponder.getDVBS()
						orb_pos = tp.orbital_position
						try:
							sat_name = str(nimmgr.getSatDescription(orb_pos))
						except KeyError:
							sat_name = ""
						if orb_pos > 1800: # west
							orb_pos = 3600 - orb_pos
							h = _("W")
						else:
							h = _("E")
						if ("%d.%d" % (orb_pos/10, orb_pos%10)) in sat_name:
							network = sat_name
						else:
							network = "%s %d.%d %s" % (sat_name, orb_pos / 10, orb_pos % 10, h)
						tp_text = { tp.System_DVB_S : "DVB-S", tp.System_DVB_S2 : "DVB-S2" }.get(tp.system, "")
						if tp_text == "DVB-S2":
							tp_text = "%s %s" % ( tp_text,
								{ tp.Modulation_Auto : "Auto", tp.Modulation_QPSK : "QPSK",
									tp.Modulation_8PSK : "8PSK", tp.Modulation_QAM16 : "QAM16",
									tp.Modulation_16APSK : "16APSK", tp.Modulation_32APSK : "32APSK" }.get(tp.modulation, ""))
						tp_text = "%s %d%c / %d / %s" % ( tp_text, tp.frequency/1000,
							{ tp.Polarisation_Horizontal : 'H', tp.Polarisation_Vertical : 'V', tp.Polarisation_CircularLeft : 'L',
								tp.Polarisation_CircularRight : 'R' }.get(tp.polarisation, ' '),
							tp.symbol_rate/1000,
							{ tp.FEC_Auto : "AUTO", tp.FEC_1_2 : "1/2", tp.FEC_2_3 : "2/3",
								tp.FEC_3_4 : "3/4", tp.FEC_5_6 : "5/6", tp.FEC_7_8 : "7/8",
								tp.FEC_8_9 : "8/9", tp.FEC_3_5 : "3/5", tp.FEC_4_5 : "4/5",
								tp.FEC_9_10 : "9/10", tp.FEC_None : "NONE" }.get(tp.fec, ""))
						if tp.is_id > -1 and tp.system == tp.System_DVB_S2:
							tp_text = ("%s IS %d") % (tp_text, tp.is_id)
					elif tp_type == iDVBFrontend.feCable:
						network = _("Cable")
						tp = transponder.getDVBC()
						tp_text = "DVB-C %s %d / %d / %s" %( { tp.Modulation_Auto : "AUTO",
							tp.Modulation_QAM16 : "QAM16", tp.Modulation_QAM32 : "QAM32",
							tp.Modulation_QAM64 : "QAM64", tp.Modulation_QAM128 : "QAM128",
							tp.Modulation_QAM256 : "QAM256" }.get(tp.modulation, ""),
							tp.frequency,
							tp.symbol_rate/1000,
							{ tp.FEC_Auto : "AUTO", tp.FEC_1_2 : "1/2", tp.FEC_2_3 : "2/3",
								tp.FEC_3_4 : "3/4", tp.FEC_5_6 : "5/6", tp.FEC_7_8 : "7/8",
								tp.FEC_8_9 : "8/9", tp.FEC_3_5 : "3/5", tp.FEC_4_5 : "4/5", tp.FEC_9_10 : "9/10", tp.FEC_None : "NONE" }.get(tp.fec_inner, ""))
					elif tp_type == iDVBFrontend.feTerrestrial:
						network = _("Terrestrial")
						tp = transponder.getDVBT()
						channel = channelnumbers.getChannelNumber(tp.frequency, self.scanList[self.run]["feid"])
						if channel:
							channel = _("CH") + "%s " % channel
						freqMHz = "%0.1f MHz" % (tp.frequency/1000000.)
						tp_text = "%s %s %s %s" %(
							{
								tp.System_DVB_T_T2 : "DVB-T/T2",
								tp.System_DVB_T : "DVB-T",
								tp.System_DVB_T2 : "DVB-T2"
							}.get(tp.system, ""),
							{
								tp.Modulation_QPSK : "QPSK",
								tp.Modulation_QAM16 : "QAM16", tp.Modulation_QAM64 : "QAM64",
								tp.Modulation_Auto : "AUTO", tp.Modulation_QAM256 : "QAM256"
							}.get(tp.modulation, ""),
							"%s%s" % (channel, freqMHz.replace(".0","")),
							{
								tp.Bandwidth_8MHz : "Bw 8MHz", tp.Bandwidth_7MHz : "Bw 7MHz", tp.Bandwidth_6MHz : "Bw 6MHz",
								tp.Bandwidth_Auto : "Bw Auto", tp.Bandwidth_5MHz : "Bw 5MHz",
								tp.Bandwidth_1_712MHz : "Bw 1.712MHz", tp.Bandwidth_10MHz : "Bw 10MHz"
							}.get(tp.bandwidth, ""))
					elif tp_type == iDVBFrontend.feATSC:
						network = _("ATSC")
						tp = transponder.getATSC()
						freqMHz = "%0.1f MHz" % (tp.frequency/1000000.)
						tp_text = ("%s %s %s %s") % (
							{
								tp.System_ATSC : _("ATSC"),
								tp.System_DVB_C_ANNEX_B : _("DVB-C ANNEX B")
							}.get(tp.system, ""),
							{
								tp.Modulation_Auto : _("Auto"),
								tp.Modulation_QAM16 : "QAM16",
								tp.Modulation_QAM32 : "QAM32",
								tp.Modulation_QAM64 : "QAM64",
								tp.Modulation_QAM128 : "QAM128",
								tp.Modulation_QAM256 : "QAM256",
								tp.Modulation_VSB_8 : "8VSB",
								tp.Modulation_VSB_16 : "16VSB"
							}.get(tp.modulation, ""),
							freqMHz.replace(".0",""),
							{
								tp.Inversion_Off : _("Off"),
								tp.Inversion_On :_("On"),
								tp.Inversion_Unknown : _("Auto")
							}.get(tp.inversion, ""))
					else:
						print "unknown transponder type in scanStatusChanged"
				self.network.setText(network)
				self.transponder.setText(tp_text)

		if self.state == self.DonePartially:
			self.foundServices += self.scan.getNumServices()
			self.text.setText(ngettext("Scanning completed, %d channel found", "Scanning completed, %d channels found", self.foundServices) % self.foundServices)

		if self.state == self.Error:
			self.text.setText(_("ERROR - failed to scan (%s)!") % (self.Errors[self.errorcode]) )

		if self.state == self.DonePartially or self.state == self.Error:
			self.delaytimer.start(100, True)

	def __init__(self, progressbar, text, servicelist, passNumber, scanList, network, transponder, frontendInfo, lcd_summary):
		self.foundServices = 0
		self.progressbar = progressbar
		self.text = text
		self.servicelist = servicelist
		self.passNumber = passNumber
		self.scanList = scanList
		self.frontendInfo = frontendInfo
		self.transponder = transponder
		self.network = network
		self.run = 0
		self.lcd_summary = lcd_summary
		self.scan = None
		self.delaytimer = eTimer()
		self.delaytimer.callback.append(self.execEnd)

	def doRun(self):
		self.scan = eComponentScan()
		self.frontendInfo.frontend_source = lambda : self.scan.getFrontend()
		self.feid = self.scanList[self.run]["feid"]
		self.flags = self.scanList[self.run]["flags"]
		self.networkid = 0
		if self.scanList[self.run].has_key("networkid"):
			self.networkid = self.scanList[self.run]["networkid"]
		self.state = self.Idle
		self.scanStatusChanged()

		for x in self.scanList[self.run]["transponders"]:
			self.scan.addInitial(x)

	def updatePass(self):
		size = len(self.scanList)
		if size > 1:
			self.passNumber.setText(_("pass") + " " + str(self.run + 1) + "/" + str(size) + " (" + _("Tuner") + " " + str(chr(ord("A") + self.scanList[self.run]["feid"])) + ")")

	def execBegin(self):
		self.doRun()
		self.updatePass()
		self.scan.statusChanged.get().append(self.scanStatusChanged)
		self.scan.newService.get().append(self.newService)
		self.servicelist.clear()
		self.state = self.Running
		err = self.scan.start(self.feid, self.flags, self.networkid)
		self.frontendInfo.updateFrontendData()
		if err:
			self.state = self.Error
			self.errorcode = 0
		self.scanStatusChanged()

	def execEnd(self):
		if self.scan is None:
			if not self.isDone():
				print "*** warning *** scan was not finished!"
			return
		self.scan.statusChanged.get().remove(self.scanStatusChanged)
		self.scan.newService.get().remove(self.newService)
		self.scan = None
		if self.run != len(self.scanList) - 1:
			self.run += 1
			self.execBegin()
		else:
			self.state = self.Done

	def isDone(self):
		return self.state == self.Done or self.state == self.Error

	def newService(self):
		newServiceName = self.scan.getLastServiceName()
		newServiceRef = self.scan.getLastServiceRef()
		self.servicelist.addItem((newServiceName, newServiceRef))
		self.lcd_summary.updateService(newServiceName)

	def destroy(self):
		self.state = self.Idle
		if self.scan is not None:
			self.scan.statusChanged.get().remove(self.scanStatusChanged)
			self.scan.newService.get().remove(self.newService)
			self.scan = None

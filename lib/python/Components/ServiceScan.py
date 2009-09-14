from enigma import eComponentScan, iDVBFrontend
from Components.NimManager import nimmanager as nimmgr

class ServiceScan:
	
	Idle = 1
	Running = 2
	Done = 3
	Error = 4
	
	Errors = { 
		0: "error starting scanning",
		1: "error while scanning",
		2: "no resource manager",
		3: "no channel list"
		}
	
	def scanStatusChanged(self):
		if self.state == self.Running:
			self.progressbar.setValue(self.scan.getProgress())
			self.lcd_summary.updateProgress(self.scan.getProgress())
			if self.scan.isDone():
				errcode = self.scan.getError()
				
				if errcode == 0:
					self.state = self.Done
				else:
					self.state = self.Error
					self.errorcode = errcode
				self.network.setText("")
				self.transponder.setText("")
			else:
				self.text.setText(_("scan in progress - %d%% done!") % self.scan.getProgress() + ' ' + _("%d services found!") % (self.foundServices + self.scan.getNumServices()))
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
						if sat_name.find("%d.%d" % (orb_pos/10, orb_pos%10)) != -1:
							network = sat_name
						else:
							network = ("%s %d.%d %s") % (sat_name, orb_pos / 10, orb_pos % 10, h)
						tp_text = ("%s %s %d%c / %d / %s") %( { tp.System_DVB_S : "DVB-S",
							tp.System_DVB_S2 : "DVB-S2" }.get(tp.system, tp.System_DVB_S),
							{ tp.Modulation_Auto : "Auto", tp.Modulation_QPSK : "QPSK",
								tp.Modulation_8PSK : "8PSK", tp.Modulation_QAM16 : "QAM16" }.get(tp.modulation, tp.Modulation_QPSK),
							tp.frequency/1000,
							{ tp.Polarisation_Horizontal : 'H', tp.Polarisation_Vertical : 'V', tp.Polarisation_CircularLeft : 'L',
								tp.Polarisation_CircularRight : 'R' }.get(tp.polarisation, tp.Polarisation_Horizontal),
							tp.symbol_rate/1000,
							{ tp.FEC_Auto : "AUTO", tp.FEC_1_2 : "1/2", tp.FEC_2_3 : "2/3",
								tp.FEC_3_4 : "3/4", tp.FEC_5_6 : "5/6", tp.FEC_7_8 : "7/8",
								tp.FEC_8_9 : "8/9", tp.FEC_3_5 : "3/5", tp.FEC_4_5 : "4/5",
								tp.FEC_9_10 : "9/10", tp.FEC_None : "NONE" }.get(tp.fec, tp.FEC_Auto))
					elif tp_type == iDVBFrontend.feCable:
						network = _("Cable")
						tp = transponder.getDVBC()
						tp_text = ("DVB-C %s %d / %d / %s") %( { tp.Modulation_Auto : "AUTO",
							tp.Modulation_QAM16 : "QAM16", tp.Modulation_QAM32 : "QAM32",
							tp.Modulation_QAM64 : "QAM64", tp.Modulation_QAM128 : "QAM128",
							tp.Modulation_QAM256 : "QAM256" }.get(tp.modulation, tp.Modulation_Auto),
							tp.frequency,
							tp.symbol_rate/1000,
							{ tp.FEC_Auto : "AUTO", tp.FEC_1_2 : "1/2", tp.FEC_2_3 : "2/3",
								tp.FEC_3_4 : "3/4", tp.FEC_5_6 : "5/6", tp.FEC_7_8 : "7/8",
								tp.FEC_8_9 : "8/9", tp.FEC_None : "NONE" }.get(tp.fec_inner, tp.FEC_Auto))
					elif tp_type == iDVBFrontend.feTerrestrial:
						network = _("Terrestrial")
						tp = transponder.getDVBT()
						tp_text = ("DVB-T %s %d %s") %( { tp.Modulation_QPSK : "QPSK",
							tp.Modulation_QAM16 : "QAM16", tp.Modulation_QAM64 : "QAM64",
							tp.Modulation_Auto : "AUTO" }.get(tp.modulation, tp.Modulation_Auto),
							tp.frequency,
							{ tp.Bandwidth_8MHz : "Bw 8MHz", tp.Bandwidth_7MHz : "Bw 7MHz", tp.Bandwidth_6MHz : "Bw 6MHz",
								tp.Bandwidth_Auto : "Bw Auto" }.get(tp.bandwidth, tp.Bandwidth_Auto))
					else:
						print "unknown transponder type in scanStatusChanged"
				self.network.setText(network)
				self.transponder.setText(tp_text)
		
		if self.state == self.Done:
			if self.scan.getNumServices() == 0:
				self.text.setText(_("scan done!") + ' ' + _("%d services found!") % 0 )
			else:
				self.text.setText(_("scan done!") + ' ' + _("%d services found!") % (self.foundServices + self.scan.getNumServices()))
		
		if self.state == self.Error:
			self.text.setText(_("ERROR - failed to scan (%s)!") % (self.Errors[self.errorcode]) )
			
		if self.state == self.Done or self.state == self.Error:
			if self.run != len(self.scanList) - 1:
				self.foundServices += self.scan.getNumServices()
				self.execEnd()
				self.run += 1
				self.execBegin()
	
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
			self.passNumber.setText(_("pass") + " " + str(self.run + 1) + "/" + str(size) + " (" + _("Tuner") + " " + str(self.scanList[self.run]["feid"]) + ")")
		
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
		self.scan.statusChanged.get().remove(self.scanStatusChanged)
		self.scan.newService.get().remove(self.newService)
		if not self.isDone():
			print "*** warning *** scan was not finished!"
		
		del self.scan

	def isDone(self):
		return self.state == self.Done or self.state == self.Error

	def newService(self):
		newServiceName = self.scan.getLastServiceName()
		self.servicelist.addItem(newServiceName)
		self.lcd_summary.updateService(self.scan.getLastServiceName())

	def destroy(self):
		pass

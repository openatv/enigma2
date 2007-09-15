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
				self.text.setText(_("scan in progress - %d %% done!\n%d services found!") % (self.scan.getProgress(), self.foundServices + self.scan.getNumServices()))
				transponder = self.scan.getCurrentTransponder()
				network = ""
				tp_text = ""
				if transponder:
					tp_type = transponder.getSystem()
					if not tp_type[0]:
						tp_type = tp_type[1]
						if tp_type == iDVBFrontend.feSatellite:
							network = _("Satellite")
							tp = transponder.getDVBS()
							if not tp[0]:
								tp = tp[1]
								orb_pos = tp.orbital_position
								try:
									sat_name = str(nimmgr.getSatDescription(orb_pos))
								except KeyError:
									sat_name = ""
								if orb_pos > 1800: # west
									orb_pos = 3600 - orbpos
									h = _("W")
								else:
									h = _("E")
								if sat_name.find("%d.%d" % (orb_pos/10, orb_pos%10)) != -1:
									network = sat_name
								else:
									network = ("%s %d.%d %s") % (sat_name, orb_pos / 10, orb_pos % 10, h)
								tp_text = ("%s %s %d%c / %d / %s") %( { 0 : "DVB-S", 1 : "DVB-S2" }[tp.system],
									{ 0 : "Auto", 1 : "QPSK", 2 : "M8PSK", 3 : "QAM16" }[tp.modulation],
									tp.frequency/1000,
									{ 0 : 'H', 1 : 'V', 2 : 'L', 3 : 'R' }[tp.polarisation],
									tp.symbol_rate/1000,
									{ 0 : "AUTO", 1 : "1/2", 2 : "2/3", 3 : "3/4", 4 : "5/6",
									 5 : "7/8", 6 : "8/9", 7 : "3/5", 8 : "4/5", 9 : "9/10",
									 15 : "NONE" }[tp.fec] )
						elif tp_type == iDVBFrontend.feCable:
							network = _("Cable")
							tp = transponder.getDVBC()
							if not tp[0]:
								tp = tp[1]
								tp_text = ("DVB-C %s %d / %d / %s") %( { 0 : "AUTO", 1 : "QAM16", 2 : "QAM32", 3 : "QAM64", 4 : "QAM128", 5 : "QAM256" }[tp.modulation],
									tp.frequency,
									tp.symbol_rate/1000,
									{ 0 : "AUTO", 1 : "1/2", 2 : "2/3", 3 : "3/4", 4 : "5/6", 5 : "7/8", 6 : "8/9", 15 : "NONE" }[tp.fec_inner] )
						elif tp_type == iDVBFrontend.feTerrestrial:
							network = _("Terrestrial")
							tp = transponder.getDVBT()
							if not tp[0]:
								tp = tp[1]
								tp_text = ("DVB-T %s %d / %d") %( { 0 : "QPSK", 1 : "QAM16", 2 : "QAM64", 3 : "AUTO"}[tp.modulation],
									tp.frequency,
									tp.symbol_rate/1000)
						else:
							print "unknown transponder type in scanStatusChanged"
				self.network.setText(network)
				self.transponder.setText(tp_text)
		
		if self.state == self.Done:
			if self.scan.getNumServices() == 1:
				self.text.setText(_("scan done!\nOne service found!"))
			elif self.scan.getNumServices() == 0:
				self.text.setText(_("scan done!\nNo service found!"))
			else:
				self.text.setText(_("scan done!\n%d services found!") % (self.foundServices + self.scan.getNumServices()))
		
		if self.state == self.Error:
			self.text.setText(_("ERROR - failed to scan (%s)!") % (self.Errors[self.errorcode]) )
			
		if self.state == self.Done or self.state == self.Error:
			if self.run != len(self.scanList) - 1:
				self.foundServices += self.scan.getNumServices()
				self.execEnd()
				self.run += 1
				self.execBegin()
	
	def __init__(self, progressbar, text, servicelist, passNumber, scanList, network, transponder, frontendInfo):
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

	def doRun(self):
		self.scan = eComponentScan()
		self.frontendInfo.frontend_source = lambda : self.scan.getFrontend()
		self.feid = self.scanList[self.run]["feid"]
		self.flags = self.scanList[self.run]["flags"]
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
		err = self.scan.start(self.feid, self.flags)
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

	def destroy(self):
		pass

from enigma import eComponentScan, eDVBFrontendParametersSatellite, eDVBFrontendParametersCable, eDVBFrontendParametersTerrestrial

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
			else:
				self.text.setText("scan in progress - %d %% done!\n%d services found!" % (self.scan.getProgress(), self.scan.getNumServices()))
		
		if self.state == self.Done:
			self.text.setText("scan done!")
		
		if self.state == self.Error:
			self.text.setText("ERROR - failed to scan (%s)!" % (self.Errors[self.errorcode]) )
	
	def __init__(self, progressbar, text, transponders):
		self.progressbar = progressbar
		self.text = text
		self.scan = eComponentScan()
		self.state = self.Idle
		self.scanStatusChanged()
		
		
		if 1:
			parm = eDVBFrontendParametersSatellite()

			parm.frequency = 11817000
			parm.symbol_rate = 27500000
			parm.polarisation = 1 # eDVBFrontendParametersSatellite.Polarisation.Vertical
			parm.fec = 3 # eDVBFrontendParametersSatellite.FEC.f3_4;
			parm.inversion = 1 #eDVBFrontendParametersSatellite.Inversion.Off;
			parm.orbital_position = 192
		else:
			parm = eDVBFrontendParametersTerrestrial()
			
			parm.frequency = 626000000;
			parm.inversion = 2  # eDVBFrontendParametersTerrestrial.Inversion.Unknown;
			parm.bandwidth = 0  #eDVBFrontendParametersTerrestrial.Bandwidth.Bw8MHz;
			parm.code_rate_HP = parm.code_rate_LP = 6 #eDVBFrontendParametersTerrestrial.FEC.fAuto;
			parm.modulation = 1 #eDVBFrontendParametersTerrestrial.Modulation.QAM16;
			parm.transmission_mode = 1 # eDVBFrontendParametersTerrestrial.TransmissionMode.TM8k;
			parm.guard_interval = 0 # eDVBFrontendParametersTerrestrial.GuardInterval.GI_1_32;
			parm.hierarchy = 0 #eDVBFrontendParametersTerrestrial.Hierarchy.HNone;
		
		for x in transponders:
			self.scan.addInitial(x)
		
		#self.scan.addInitial(parm)
		
	def execBegin(self):
		self.scan.statusChanged.get().append(self.scanStatusChanged)
		self.state = self.Running
		err = self.scan.start()
		if err:
			self.state = self.Error
			self.errorcode = 0

		self.scanStatusChanged()
	
	def execEnd(self):
		self.scan.statusChanged.get().remove(self.scanStatusChanged)
		if not self.isDone():
			print "*** warning *** scan was not finished!"

	def isDone(self):
		print "state is %d " % (self.state)
		return self.state == self.Done or self.state == self.Error
	

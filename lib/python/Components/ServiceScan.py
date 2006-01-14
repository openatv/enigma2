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
				self.text.setText(_("scan in progress - %d %% done!\n%d services found!") % (self.scan.getProgress(), self.scan.getNumServices()))
		
		if self.state == self.Done:
			if self.scan.getNumServices() == 1:
				self.text.setText(_("scan done!\nOne service found!"))
			elif self.scan.getNumServices() == 0:
				self.text.setText(_("scan done!\nNo service found!"))
			else:
				self.text.setText(_("scan done!\n%d services found!") % (self.scan.getNumServices()))
		
		if self.state == self.Error:
			self.text.setText(_("ERROR - failed to scan (%s)!") % (self.Errors[self.errorcode]) )
	
	def __init__(self, progressbar, text, servicelist, transponders, feid, flags):
		self.progressbar = progressbar
		self.text = text
		self.scan = eComponentScan()
		self.state = self.Idle
		self.feid = feid
		self.flags = flags
		self.servicelist = servicelist
		self.scanStatusChanged()
		
		for x in transponders:
			self.scan.addInitial(x)
		
		#self.scan.addInitial(parm)
		
	def execBegin(self):
		self.scan.statusChanged.get().append(self.scanStatusChanged)
		self.scan.newService.get().append(self.newService)
		self.state = self.Running
		err = self.scan.start(self.feid, self.flags)
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

from enigma import eComponentScan

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
	
	def __init__(self, progressbar, text):
		self.progressbar = progressbar
		self.text = text
		self.scan = eComponentScan()
		self.state = self.Idle
		self.scanStatusChanged()
		
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
	

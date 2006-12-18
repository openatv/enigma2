from enigma import eConsoleAppContainer

class Ipkg:
	EVENT_INSTALL = 0
	EVENT_DOWNLOAD = 1
	EVENT_INFLATING = 2
	EVENT_CONFIGURING = 3
	EVENT_REMOVE = 4
	EVENT_UPGRADE = 5
	EVENT_LISTITEM = 9
	EVENT_DONE = 10
	EVENT_ERROR = 11
	
	CMD_INSTALL = 0
	CMD_LIST = 1
	CMD_REMOVE = 2
	CMD_UPDATE = 3
	CMD_UPGRADE = 4
	
	def __init__(self, ipkg = '/usr/bin/ipkg'):
		self.ipkg = ipkg
		
		self.cmd = eConsoleAppContainer()
		self.cmd.appClosed.get().append(self.cmdFinished)
		self.cmd.dataAvail.get().append(self.cmdData)
		self.cache = None
		
		self.callbackList = []
		self.setCurrentCommand()
		
	def setCurrentCommand(self, command = None):
		self.currentCommand = command
		
	def runCmd(self, cmd):
		print "executing", self.ipkg, cmd
		self.cmd.execute(self.ipkg + " " + cmd)
		
	def cmdFetchList(self, installed_only = False):
		self.fetchedList = []
		if installed_only:
			self.runCmd("list_installed")
		else:
			self.runCmd("list")
		self.setCurrentCommand(self.CMD_LIST)
		
	def cmdUpgrade(self, test_only = False):
		append = ""
		if test_only:
			append = " -test"
		self.runCmd("upgrade" + append)
		self.setCurrentCommand(self.CMD_UPGRADE)
		
	def cmdUpdate(self):
		self.runCmd("update")
		self.setCurrentCommand(self.CMD_UPDATE)
		
	def cmdFinished(self, retval):
		self.callCallbacks(self.EVENT_DONE)
	
	def cmdData(self, data):
		print "data:", data
		if self.cache is None:
			self.cache = data
		else:
			self.cache += data

		if '\n' in data:
			splitcache = self.cache.split('\n')
			if self.cache[-1] == '\n':
				iteration = splitcache
				self.cache = None
			else:
				iteration = splitcache[:-1]
				self.cache = splitcache[-1]
			for mydata in iteration:
				if mydata != '':
					self.parseLine(mydata)
		
	def parseLine(self, data):
		if self.currentCommand == self.CMD_LIST:
			item = data.split(' - ', 2)
			self.fetchedList.append(item)
			self.callCallbacks(self.EVENT_LISTITEM, item)
		else:
			if data.find('Downloading') == 0:
				self.callCallbacks(self.EVENT_DOWNLOAD, data.split(' ', 5)[1].strip())
			elif data.find('Upgrading') == 0:
				self.callCallbacks(self.EVENT_UPGRADE, data.split('    ', 1)[1].split(' ')[0])
			elif data.find('Installing') == 0:
				self.callCallbacks(self.EVENT_INSTALL, data.split(' ', 1)[1].split(' ')[0])
			elif data.find('Configuring') == 0:
				self.callCallbacks(self.EVENT_CONFIGURING, data.split(' ', 1)[1].split(' ')[0])
			elif data.find('An error occurred') == 0:
				self.callCallbacks(self.EVENT_ERROR, None)
			elif data.find('Failed to download') == 0:
				self.callCallbacks(self.EVENT_ERROR, None)
			elif data.find('ipkg_download: ERROR:') == 0:
				self.callCallbacks(self.EVENT_ERROR, None)
	def callCallbacks(self, event, param = None):
		for callback in self.callbackList:
			callback(event, param)

	def addCallback(self, callback):
		self.callbackList.append(callback)
		
	def getFetchedList(self):
		return self.fetchedList
	
	def stop(self):
		self.cmd.kill()
		
	def isRunning(self):
		return self.cmd.running()

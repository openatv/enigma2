from Components.config import config

#for scheduler
from time import mktime, strftime, time, localtime
from enigma import eTimer

#for downloader
import os, re, urllib2
from enigma import eServiceReference, eDVBDB

autoClientModeTimer = None
def autostart():
	global autoClientModeTimer
	now = int(time())
	print "[ClientModeScheduler][ClientModeautostart] AutoStart Enabled"
	if autoClientModeTimer is None:
		autoClientModeTimer = AutoClientModeTimer()

class AutoClientModeTimer:
	instance = None
	def __init__(self):
		self.clientmodetimer = eTimer()
		self.clientmodetimer.callback.append(self.ClientModeonTimer)
		self.clientmodeactivityTimer = eTimer()
		self.clientmodeactivityTimer.timeout.get().append(self.clientmodedatedelay)
		now = int(time())
		self.doautostartscan() # import at boot time

		global ClientModeTime
		if config.clientmode.enableSchedule.value:
			print "[ClientModeScheduler][AutoClientModeTimer] Schedule Enabled at ", strftime("%c", localtime(now))
			if now > 1262304000:
				self.clientmodedate()
			else:
				print "[ClientModeScheduler][AutoClientModeTimer] Time not yet set."
				ClientModeTime = 0
				self.clientmodeactivityTimer.start(36000)
		else:
			ClientModeTime = 0
			print "[ClientModeScheduler][AutoClientModeTimer] Schedule Disabled at", strftime("%c", localtime(now))
			self.clientmodeactivityTimer.stop()

		assert AutoClientModeTimer.instance is None, "class AutoClientModeTimer is a singleton class and just one instance of this class is allowed!"
		AutoClientModeTimer.instance = self

	def __onClose(self):
		AutoClientModeTimer.instance = None

	def clientmodedatedelay(self):
		self.clientmodeactivityTimer.stop()
		self.clientmodedate()

	def getClientModeTime(self):
		backupclock = config.clientmode.scheduletime.value
		nowt = time()
		now = localtime(nowt)
		if config.clientmode.scheduleRepeatInterval.value.isdigit(): # contains wait time in minutes
			repeatIntervalMinutes = int(config.clientmode.scheduleRepeatInterval.value)
			return int(mktime((now.tm_year, now.tm_mon, now.tm_mday, now.tm_hour, now.tm_min + repeatIntervalMinutes, 0, now.tm_wday, now.tm_yday, now.tm_isdst)))
		return int(mktime((now.tm_year, now.tm_mon, now.tm_mday, backupclock[0], backupclock[1], 0, now.tm_wday, now.tm_yday, now.tm_isdst)))

	def clientmodedate(self, atLeast = 0):
		self.clientmodetimer.stop()
		global ClientModeTime
		ClientModeTime = self.getClientModeTime()
		now = int(time())
		if ClientModeTime > 0:
			if ClientModeTime < now + atLeast:
				if config.clientmode.scheduleRepeatInterval.value.isdigit(): # contains wait time in minutes
					ClientModeTime = now + (60 * int(config.clientmode.scheduleRepeatInterval.value))
					while (int(ClientModeTime)-30) < now:
						ClientModeTime += 60 * int(config.clientmode.scheduleRepeatInterval.value)
				elif config.clientmode.scheduleRepeatInterval.value == "daily":
					ClientModeTime += 24*3600
					while (int(ClientModeTime)-30) < now:
						ClientModeTime += 24*3600
				elif config.clientmode.scheduleRepeatInterval.value == "weekly":
					ClientModeTime += 7*24*3600
					while (int(ClientModeTime)-30) < now:
						ClientModeTime += 7*24*3600
				elif config.clientmode.scheduleRepeatInterval.value == "monthly":
					ClientModeTime += 30*24*3600
					while (int(ClientModeTime)-30) < now:
						ClientModeTime += 30*24*3600
			next = ClientModeTime - now
			self.clientmodetimer.startLongTimer(next)
		else:
			ClientModeTime = -1
		print "[ClientModeScheduler][clientmodedate] Time set to", strftime("%c", localtime(ClientModeTime)), strftime("(now=%c)", localtime(now))
		return ClientModeTime

	def backupstop(self):
		self.clientmodetimer.stop()

	def ClientModeonTimer(self):
		self.clientmodetimer.stop()
		now = int(time())
		wake = self.getClientModeTime()
		# If we're close enough, we're okay...
		atLeast = 0
		if wake - now < 60:
			atLeast = 60
			print "[ClientModeScheduler][ClientModeonTimer] onTimer occured at", strftime("%c", localtime(now))
			self.doClientMode(True)
		self.clientmodedate(atLeast)

	def doClientMode(self, answer):
		now = int(time())
		self.timer = eTimer()
		self.timer.callback.append(self.doautostartscan)
		print "[ClientModeScheduler][doClientMode] Running ClientMode", strftime("%c", localtime(now))
		self.timer.start(100, 1)

	def doautostartscan(self):
		ChannelsImporter()

	def doneConfiguring(self):
		now = int(time())
		if config.clientmode.enableSchedule.value:
			if autoClientModeTimer is not None:
				print "[ClientModeScheduler][doneConfiguring] Schedule Enabled at", strftime("%c", localtime(now))
				autoClientModeTimer.clientmodedate()
		else:
			if autoClientModeTimer is not None:
				global ClientModeTime
				ClientModeTime = 0
				print "[ClientModeScheduler][doneConfiguring] Schedule Disabled at", strftime("%c", localtime(now))
				autoClientModeTimer.backupstop()
		if ClientModeTime > 0:
			t = localtime(ClientModeTime)
			clientmodetext = strftime(_("%a %e %b  %-H:%M"), t)
		else:
			clientmodetext = ""

class ChannelsImporter():
	DIR_ENIGMA2 = '/etc/enigma2/'
	DIR_TMP = '/tmp/'
	def __init__(self):
		self.fetchRemoteBouquets()

	def fetchRemoteBouquets(self):
		print "[ChannelsImporter] Fetch bouquets.tv and bouquets.radio"
		self.readIndex = 0
		self.workList = []
		self.workList.append('bouquets.tv')
		self.workList.append('bouquets.radio')
		print "[ChannelsImporter][fetchRemoteBouquets] Downloading channel indexes..."
		print "[ChannelsImporter][fetchRemoteBouquets] %d/%d" % (self.readIndex + 1, len(self.workList))
		result = self.FTPdownloadFile(self.DIR_ENIGMA2, self.workList[self.readIndex], self.workList[self.readIndex])
		if result:
			self.fetchRemoteBouquetsCallback()
		else:
			print "[ChannelsImporter][fetchRemoteBouquets] Error fetching. Stopping script."

	def fetchRemoteBouquetsCallback(self):
		self.readIndex += 1
		if self.readIndex < len(self.workList):
			print "[ChannelsImporter][fetchRemoteBouquetsCallback] %d/%d" % (self.readIndex + 1, len(self.workList))
			result = self.FTPdownloadFile(self.DIR_ENIGMA2, self.workList[self.readIndex], self.workList[self.readIndex])
			if result:
				self.fetchRemoteBouquetsCallback()
			else:
				print "[ChannelsImporter][fetchRemoteBouquetsCallback] Error fetching. Stopping script."
		else:
			self.readBouquets()

	def getBouquetsList(self, bouquetFilenameList, bouquetfile):
		file = open(bouquetfile)
		lines = file.readlines()
		file.close()
		if len(lines) > 0:
			for line in lines:
				result = re.match("^.*FROM BOUQUET \"(.+)\" ORDER BY.*$", line) or re.match("[#]SERVICE[:] (?:[0-9a-f]+[:])+([^:]+[.](?:tv|radio))$", line, re.IGNORECASE)
				if result is None:
					continue
				bouquetFilenameList.append(result.group(1))

	def readBouquets(self):
		bouquetFilenameList = []
		self.getBouquetsList(bouquetFilenameList, self.DIR_TMP + 'bouquets.tv')
		self.getBouquetsList(bouquetFilenameList, self.DIR_TMP + 'bouquets.radio')
		self.readIndex = 0
		self.workList = []
		for listindex in range(len(bouquetFilenameList)):
			self.workList.append(bouquetFilenameList[listindex])
		self.workList.append('lamedb')
		print "[ChannelsImporter][readBouquets] Downloading bouquets..."
		print "[ChannelsImporter][readBouquets] %d/%d" % (self.readIndex + 1, len(self.workList))
		result = self.FTPdownloadFile(self.DIR_ENIGMA2, self.workList[self.readIndex], self.workList[self.readIndex])
		if result:
			self.readBouquetsCallback()
		else:
			print "[ChannelsImporter][readBouquets] Error fetching. Stopping script."

	def readBouquetsCallback(self):
		self.readIndex += 1
		if self.readIndex < len(self.workList):
			print "[ChannelsImporter][readBouquetsCallback] %d/%d" % (self.readIndex + 1, len(self.workList))
			result = self.FTPdownloadFile(self.DIR_ENIGMA2, self.workList[self.readIndex], self.workList[self.readIndex])
			if result:
				self.readBouquetsCallback()
			else:
				print "[ChannelsImporter][readBouquetsCallback] Error fetching. Stopping script."
		elif len(self.workList) > 0:
			# Download alternatives files where services have alternatives
			print "[ChannelsImporter][readBouquetsCallback] Checking for alternatives..."
			self.findAlternatives()
			self.alternativesCounter = 0
			if len(self.alternatives) > 0:
				print "[ChannelsImporter][readBouquetsCallback] Downloading alternatives..."
				print "[ChannelsImporter][readBouquetsCallback] %d/%d" % (self.alternativesCounter + 1, len(self.alternatives))
				result = self.FTPdownloadFile(self.DIR_ENIGMA2, self.alternatives[self.alternativesCounter], self.alternatives[self.alternativesCounter])
				if result:
					self.downloadAlternativesCallback()
				else:
					print "[ChannelsImporter][readBouquetsCallback] Error fetching. Stopping script."
					return
			self.processFiles()
		else:
			print "[ChannelsImporter][readBouquetsCallback] There were no remote bouquets to download"

	def downloadAlternativesCallback(self):
		self.alternativesCounter += 1
		if self.alternativesCounter < len(self.alternatives):
			print "[ChannelsImporter][downloadAlternativesCallback] %d/%d" % (self.alternativesCounter + 1, len(self.alternatives))
			result = self.FTPdownloadFile(self.DIR_ENIGMA2, self.alternatives[self.alternativesCounter], self.alternatives[self.alternativesCounter])
			if result:
				self.downloadAlternativesCallback()

	def processFiles(self):
		allFiles = self.workList + self.alternatives + ["bouquets.tv", "bouquets.radio"]
		print "[ChannelsImporter][processFiles] Removing current channel list..."
		for target in ["lamedb", "bouquets.", "userbouquet."]:
			self.removeFiles(self.DIR_ENIGMA2, target)
		print "[ChannelsImporter][processFiles] Loading new channel list..."
		for filename in allFiles:
			self.copyFile(self.DIR_TMP + filename, self.DIR_ENIGMA2 + filename)
			self.removeFiles(self.DIR_TMP, filename)
		db = eDVBDB.getInstance()
		db.reloadServicelist()
		db.reloadBouquets()
		print "[ChannelsImporter][processFiles] New channel list loaded."
		self.checkEPG()

	def checkEPG(self):
		print "[ChannelsImporter][checkEPG] Force EPG save on remote receiver..."
		self.forceSaveEPGonRemoteReceiver()
		print "[ChannelsImporter][checkEPG] Searching for epg.dat..."
		result = self.FTPdownloadFile(self.DIR_ENIGMA2, "settings", "settings")
		if result:
			self.checkEPGCallback()
		else:
			print "[ChannelsImporter][checkEPG] Error fetching 'settings' file. Stopping script."

	def checkEPGCallback(self):
		file = open(self.DIR_TMP + "settings")
		lines = file.readlines()
		file.close()
		self.remoteEPGpath = self.DIR_ENIGMA2
		self.remoteEPGfile = "epg"
		for line in lines:
			if "config.misc.epgcachepath" in line:
				self.remoteEPGpath = line.strip().split("=")[1]
			if "config.misc.epgcachefilename" in line:
				self.remoteEPGfile = "%s" % line.strip().split("=")[1]
		self.remoteEPGfile = "%s.dat" % self.remoteEPGfile.replace('.dat','')
		print "[ChannelsImporter] Remote EPG filename. '%s%s'" % (self.remoteEPGpath, self.remoteEPGfile)
		self.removeFiles(self.DIR_TMP, "settings")
		result = self.FTPdownloadFile(self.remoteEPGpath, self.remoteEPGfile, "epg.dat")
		if result:
			self.importEPGCallback()
		else:
			print "[ChannelsImporter][checkEPGCallback] Download epg.dat from remote receiver failed. Check file exists on remote receiver."

	def importEPGCallback(self):
		print "[ChannelsImporter][importEPGCallback] '%s%s' downloaded successfully. " % (self.remoteEPGpath, self.remoteEPGfile)
		print "[ChannelsImporter][importEPGCallback] Removing current EPG data..."
		try:
			os.remove(config.misc.epgcache_filename.value)
		except OSError:
			pass
		self.copyFile(self.DIR_TMP + "epg.dat", config.misc.epgcache_filename.value)
		self.removeFiles(self.DIR_TMP, "epg.dat")
		from enigma import eEPGCache
		epgcache = eEPGCache.getInstance()
		epgcache.load()
		print "[ChannelsImporter][importEPGCallback] New EPG data loaded..."
		print "[ChannelsImporter][importEPGCallback] Closing importer."

	def findAlternatives(self):
		print "[ChannelsImporter] Checking for alternatives"
		self.alternatives = []
		for filename in self.workList:
			if filename != "lamedb":
				try:
					fp = open(self.DIR_TMP + filename)
					lines = fp.readlines()
					fp.close()
					for line in lines:
						if '#SERVICE' in line and int(line.split()[1].split(":")[1]) & eServiceReference.mustDescent:
							result = re.match("^.*FROM BOUQUET \"(.+)\" ORDER BY.*$", line) or re.match("[#]SERVICE[:] (?:[0-9a-f]+[:])+([^:]+[.](?:tv|radio))$", line, re.IGNORECASE)
							if result is None:
								continue
							self.alternatives.append(result.group(1))
				except:
					pass

	def removeFiles(self, targetdir, target):
		targetLen = len(target)
		for root, dirs, files in os.walk(targetdir):
			for name in files:
				if target in name[:targetLen]:
					os.remove(os.path.join(root, name))

	def copyFile(self, source, dest):
		import shutil
		shutil.copy2(source, dest)

	def getRemoteAddress(self):
		if config.clientmode.serverAddressType.value == "ip":
			return '%d.%d.%d.%d' % (config.clientmode.serverIP.value[0], config.clientmode.serverIP.value[1], config.clientmode.serverIP.value[2], config.clientmode.serverIP.value[3])
		else:
			return config.clientmode.serverDomain.value

	def FTPdownloadFile(self, sourcefolder, sourcefile, destfile):
		print "[ChannelsImporter] Downloading remote file '%s'" % sourcefile
		try:
			from ftplib import FTP
			ftp = FTP()
			ftp.set_pasv(config.clientmode.passive.value)
			ftp.connect(host=self.getRemoteAddress(), port=config.clientmode.serverFTPPort.value, timeout=5)
			ftp.login(user=config.clientmode.serverFTPusername.value, passwd=config.clientmode.serverFTPpassword.value)
			ftp.cwd(sourcefolder)
			with open(self.DIR_TMP + destfile, 'wb') as f:
				result = ftp.retrbinary('RETR %s' % sourcefile, f.write)
				ftp.quit()
				f.close()
				if result.startswith("226"):
					return True
			return False
		except Exception, err:
			print "[ChannelsImporter][FTPdownloadFile] Error:", err
			return False

	def forceSaveEPGonRemoteReceiver(self):
		url = "http://%s/api/saveepg" % self.getRemoteAddress()
		print '[ChannelsImporter][saveEPGonRemoteReceiver] URL: %s' % url
		try:
			req = urllib2.Request(url)
			response = urllib2.urlopen(req)
			print '[ChannelsImporter][saveEPGonRemoteReceiver] Response: %d, %s' % (response.getcode(), response.read().strip().replace("\r","").replace("\n",""))
		except urllib2.HTTPError, err:
			print '[ChannelsImporter][saveEPGonRemoteReceiver] ERROR:',err
		except urllib2.URLError, err:
			print '[ChannelsImporter][saveEPGonRemoteReceiver] ERROR:',err.reason[0]
		except urllib2, err:
			print '[ChannelsImporter][saveEPGonRemoteReceiver] ERROR:',err
		except:
			print '[ChannelsImporter][saveEPGonRemoteReceiver] undefined error'

from Screens.Screen import Screen
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Components.ConfigList import ConfigListScreen
from Components.Sources.StaticText import StaticText
from Components.SelectionList import SelectionList
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.config import config, configfile, ConfigInteger, ConfigSubsection, ConfigText, ConfigYesNo, getConfigListEntry, ConfigIP, ConfigSelectionNumber, ConfigSelection
from enigma import eServiceCenter, eServiceReference, eDVBDB
from ServiceReference import ServiceReference
from twisted.internet import reactor
from twisted.internet.protocol import ClientCreator
from twisted.protocols.ftp import FTPClient
from urllib import quote

from FTPDownloader import FTPDownloader

DIR_ENIGMA2 = '/etc/enigma2/'
DIR_TMP = '/tmp/'

config.plugins.RemoteStreamConverter = ConfigSubsection()
config.plugins.RemoteStreamConverter.address = ConfigText(default = "", fixed_size = False)
config.plugins.RemoteStreamConverter.ip = ConfigIP(default = [0,0,0,0])
config.plugins.RemoteStreamConverter.username = ConfigText(default = "root", fixed_size = False)
config.plugins.RemoteStreamConverter.password = ConfigText(default = "", fixed_size = False)
config.plugins.RemoteStreamConverter.port = ConfigInteger(21, (0, 65535))
config.plugins.RemoteStreamConverter.passive = ConfigYesNo(False)
config.plugins.RemoteStreamConverter.telnetport = ConfigInteger(23, (0, 65535))
config.plugins.RemoteStreamConverter.advancemode = ConfigYesNo(False)

config.plugins.RemoteStreamConverter.transcoding = ConfigYesNo(False)
config.plugins.RemoteStreamConverter.bitrate = ConfigSelectionNumber(min = 100000, max = 10000000, stepwidth = 100000, default = 400000, wraparound = True)
config.plugins.RemoteStreamConverter.resolution = ConfigSelection(default = "854x480", choices = [ ("854x480", _("480p")), ("768x576", _("576p")), ("1280x720", _("720p")), ("320x240", _("320x240")), ("160x120", _("160x120")) ])
config.plugins.RemoteStreamConverter.framerate = ConfigSelection(default = "50000", choices = [("23976", "23.976 fps"), ("24000", "24 fps"), ("25000", "25 fps"), ("29970", "29.970 fps"), ("30000", "30 fps"), ("50000", "50 fps"), ("59940", "59.940 fps"), ("60000", "60 fps")])
config.plugins.RemoteStreamConverter.aspectratio = ConfigSelection(default = "2", choices = [("0", _("4x3")), ("1", _("16x9")), ("2", _("Auto")) ])
config.plugins.RemoteStreamConverter.interlaced = ConfigSelection(default = "0", choices = [ ("1", _("Yes")), ("0", _("No"))])


#text2 = "http://STB_IP:PORT/CH_REF:?bitrate=BITRATE?width=WIDTH?height=HEIGHT?aspectration=ASPECT?interlaced=0/1"

class RemoteTunerServerEditor(ConfigListScreen, Screen):
	skin = """
		<screen position="center,center" size="560,530" title="IPTV Server Editor">
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" transparent="1" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" transparent="1" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_blue" render="Label"  position="420,0" zPosition="1" size="140,40" font="Regular;20" valign="center" halign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="config" position="10,50" size="550,250" scrollbarMode="showOnDemand" />
			<widget name="text" position="0,470" zPosition="1" size="560,40" font="Regular;28" valign="center" halign="center" backgroundColor="#1f771f" transparent="1" />
		</screen>"""

	def __init__(self, session, ip = [192, 168, 1, 100], username="root", password="beyonwiz", ftpport=21, ftppassive=False):
		Screen.__init__(self, session)
		
		config.plugins.RemoteStreamConverter.ip.value = ip
		config.plugins.RemoteStreamConverter.username.value = username
		config.plugins.RemoteStreamConverter.password.value  = password
		config.plugins.RemoteStreamConverter.port.value = ftpport
		
		self["key_red"] = StaticText(_("Back"))
		self["key_green"] = StaticText(_("Advanced"))
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText("")
		self["text"] = Label(_("After You accept data please press OK to continue"))
		
		self.isIp = True
		self.list = []
		ConfigListScreen.__init__(self, self.list)
		
		if config.plugins.RemoteStreamConverter.address.value != '':
			self.createMenuAdress()
		else:
			self.createMenuIp()
			
		self["actions"] = ActionMap(["WizardActions", "ColorActions", "DirectionActions"],
			{
				"ok": self.keySave,
				"cancel": self.keyExit,
				"back": self.keyExit,
				"up": self.keyUp,
				"down": self.keyDown,
				"red": self.keyExit,
				"green": self.keyToggleMode,
				"blue": self.enterUrl,
				"yellow": self.switchMode
			}, -2)
		self.setTitle(_("IPTV Server Editor"))

	def keyToggleMode(self):
		print "[RemoteTunerServerEditor] keyToggleMode"
		if config.plugins.RemoteStreamConverter.advancemode.value:
			config.plugins.RemoteStreamConverter.advancemode.value = False
			self["key_green"].setText(_("Advanced"))
		else:
			config.plugins.RemoteStreamConverter.advancemode.value = True
			self["key_green"].setText(_("Basic"))

		if config.plugins.RemoteStreamConverter.address.value != '':
			self.createMenuAdress()
		else:
			self.createMenuIp()
			
	def keyUp(self):
		print "[RemoteTunerServerEditor] keyUp"
		if self["config"].getCurrentIndex() > 0:
			self["config"].setCurrentIndex(self["config"].getCurrentIndex() - 1)
			self.setVkeyOnOff()

	def keyDown(self):
		print "[RemoteTunerServerEditor] keyDown"
		if self["config"].getCurrentIndex() < len(self.list) - 1:
			self["config"].setCurrentIndex(self["config"].getCurrentIndex() + 1)
			self.setVkeyOnOff()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.handleKeysLeftAndRight()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.handleKeysLeftAndRight()

	def handleKeysLeftAndRight(self):
		sel = self["config"].getCurrent()[1]
		if sel == config.plugins.RemoteStreamConverter.transcoding:
				if config.plugins.RemoteStreamConverter.transcoding.value:
					config.plugins.RemoteStreamConverter.transcoding.value = True
				else:
					config.plugins.RemoteStreamConverter.transcoding.value = False
					
				if config.plugins.RemoteStreamConverter.address.value != '':
					self.createMenuAdress()
				else:
					self.createMenuIp()
  
	def switchMode(self):
		print "[RemoteTunerServerEditor] switchMode"
		if self["config"].getCurrentIndex() != 0:
			return
		config.plugins.RemoteStreamConverter.ip.value = [0, 0, 0, 0]
		config.plugins.RemoteStreamConverter.address.value = ""
		if self.isIp:
			self.createMenuAdress()
		else:
			self.createMenuIp()

	def setVkeyOnOff(self):
		print "[RemoteTunerServerEditor] setVkeyOnOff"
		if self.list[self["config"].getCurrentIndex()][2]:
			self["key_blue"].setText(_("Keyboard"))
		else:
			self["key_blue"].setText("")

		if self["config"].getCurrentIndex() == 0:
			if self.isIp:
				self["key_yellow"].setText(_("Use address"))
			else:
				self["key_yellow"].setText(_("Use IP"))
		else:
			self["key_yellow"].setText("")

	def createMenuIp(self):
		self.list = []
		self.list.append(getConfigListEntry(_("Server IP:"), config.plugins.RemoteStreamConverter.ip, False))
		self.list.append(getConfigListEntry(_("Username:"), config.plugins.RemoteStreamConverter.username, True))
		self.list.append(getConfigListEntry(_("Password:"), config.plugins.RemoteStreamConverter.password, True))
		self.list.append(getConfigListEntry(_("Use transcoding:"), config.plugins.RemoteStreamConverter.transcoding, False))
		if config.plugins.RemoteStreamConverter.advancemode.value:
			self.list.append(getConfigListEntry(_("FTP port:"), config.plugins.RemoteStreamConverter.port, False))
			self.list.append(getConfigListEntry(_("Passive:"), config.plugins.RemoteStreamConverter.passive, False))
			self.list.append(getConfigListEntry(_("Telnet port:"), config.plugins.RemoteStreamConverter.telnetport, False))
		if config.plugins.RemoteStreamConverter.transcoding.value:
			self.list.append(getConfigListEntry(_("Bitrate in bits"), config.plugins.RemoteStreamConverter.bitrate, False))
			self.list.append(getConfigListEntry(_("Framerate"), config.plugins.RemoteStreamConverter.framerate, False))
			self.list.append(getConfigListEntry(_("Resolution"), config.plugins.RemoteStreamConverter.resolution, False))
			self.list.append(getConfigListEntry(_("Aspect Ratio"), config.plugins.RemoteStreamConverter.aspectratio, False))
			self.list.append(getConfigListEntry(_("Interlaced"), config.plugins.RemoteStreamConverter.interlaced, False))
		
		  
		self["config"].list = self.list
		self["config"].l.setList(self.list)
		self.isIp = True
		self.setVkeyOnOff()

	def createMenuAdress(self):
		self.list = []
		self.list.append(getConfigListEntry(_("Server Dyn-DNS:"), config.plugins.RemoteStreamConverter.address, True))
		self.list.append(getConfigListEntry(_("Username:"), config.plugins.RemoteStreamConverter.username, True))
		self.list.append(getConfigListEntry(_("Password:"), config.plugins.RemoteStreamConverter.password, True))
		self.list.append(getConfigListEntry(_("Use transcoding:"), config.plugins.RemoteStreamConverter.transcoding, False))
		if config.plugins.RemoteStreamConverter.advancemode.value:
			self.list.append(getConfigListEntry(_("FTP port:"), config.plugins.RemoteStreamConverter.port, False))
			self.list.append(getConfigListEntry(_("Passive:"), config.plugins.RemoteStreamConverter.passive, False))
			self.list.append(getConfigListEntry(_("Telnet port:"), config.plugins.RemoteStreamConverter.telnetport, False))
		if config.plugins.RemoteStreamConverter.transcoding.value:
			self.list.append(getConfigListEntry(_("Bitrate in bits"), config.plugins.RemoteStreamConverter.bitrate, False))
			self.list.append(getConfigListEntry(_("Framerate"), config.plugins.RemoteStreamConverter.framerate, False))
			self.list.append(getConfigListEntry(_("Resolution"), config.plugins.RemoteStreamConverter.resolution, False))
			self.list.append(getConfigListEntry(_("Aspect Ratio"), config.plugins.RemoteStreamConverter.aspectratio, False))
			self.list.append(getConfigListEntry(_("Interlaced"), config.plugins.RemoteStreamConverter.interlaced, False))
		self["config"].list = self.list
		self["config"].l.setList(self.list)
		self.isIp = False
		self.setVkeyOnOff()

	POS_ADDRESS = 0
	POS_USERNAME = 1
	POS_PASSWORD = 2

	def enterUrl(self):
		if not self.list[self["config"].getCurrentIndex()][2]:
			return
		if self["config"].getCurrentIndex() == self.POS_ADDRESS and not self.isIp:
			txt = config.plugins.RemoteStreamConverter.address.value
			head = _("Enter address")
		elif self["config"].getCurrentIndex() == self.POS_USERNAME:
			txt = config.plugins.RemoteStreamConverter.username.value
			head = _("Enter username")
		elif self["config"].getCurrentIndex() == self.POS_PASSWORD:
			txt = config.plugins.RemoteStreamConverter.password.value
			head = _("Enter password")
		self.session.openWithCallback(self.urlCallback, VirtualKeyBoard, title = head, text = txt)

	def urlCallback(self, res):
		if res is not None:
			if self["config"].getCurrentIndex() == self.POS_ADDRESS:
				config.plugins.RemoteStreamConverter.address.value = res
			elif self["config"].getCurrentIndex() == self.POS_USERNAME:
				config.plugins.RemoteStreamConverter.username.value = res
			elif self["config"].getCurrentIndex() == self.POS_PASSWORD:
				config.plugins.RemoteStreamConverter.password.value = res

	def keySave(self):
		print "[RemoteTunerServerEditor] keySave"
		config.plugins.RemoteStreamConverter.address.value = config.plugins.RemoteStreamConverter.address.value.strip()
		self.saveAll()
		if self.isIp:
			config.plugins.RemoteStreamConverter.address.save()
		else:
			config.plugins.RemoteStreamConverter.ip.save()
			
		for x in self["config"].list:
			x[1].save()

		configfile.save()
		self.session.openWithCallback(self.keyExit, RemoteTunerServerDownloader)
		
	def keyExit(self, ret = False):
		if ret:
			print "[RemoteTunerServerEditor] keyExit TRUE"  
			self.close(True)
		else:
			print "[RemoteTunerServerEditor] keyExit FALSE"
			self.close(False)

class RemoteTunerServerDownloader(Screen):
	skin = """
		<screen name="RemoteTunerServerDownloader" position="center,center" size="550,450" title="Select bouquets to convert" >
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
			<widget source="key_blue" render="Label" position="420,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" />
			<widget name="config" position="5,50" size="540,360" />
			<ePixmap pixmap="skin_default/div-h.png" position="0,410" zPosition="10" size="560,2" transparent="1" alphatest="on" />
			<widget name="text" position="5,420" zPosition="10" size="550,30" halign="center" valign="center" font="Regular;22" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.session = session
		self.workList = []
		self.readIndex = 0
		self.working = False
		self.hasFiles = False
		self.list = SelectionList()
		self["config"] = self.list
		self["key_red"] = StaticText(_("Back"))
		self["key_green"] = StaticText("")
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText("")
		self["text"] = Label()
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
		{
			"ok": self.keyOk,
			"cancel": self.keyExit,
			"red": self.keyExit,
			"green": self.keyGreen,
			"blue": self.keyBlue
		}, -1)
		self.setTitle(_("Select favorite bouqets to import"))
		self.setRemoteIpCallback(True)

	def keyOk(self):
		if self.working:
			return
		if self.readIndex > 0:
			self.list.toggleSelection()

	def keyBlue(self):
		if not self.hasFiles or self.working:
			return
		if self.readIndex > 0:
			try:
				self.list.toggleAllSelection()
			except AttributeError:
				self.list.toggleSelection()

	def setRemoteIpCallback(self, ret = False):
		if ret:
			self["text"].setText(_("Testing remote connection"))
			timeout = 3000
			self.currentLength = 0
			self.total = 0
			self.working = True
			creator = ClientCreator(reactor, FTPClient, config.plugins.RemoteStreamConverter.username.value, config.plugins.RemoteStreamConverter.password.value, config.plugins.RemoteStreamConverter.passive.value)
			creator.connectTCP(self.getRemoteAdress(), config.plugins.RemoteStreamConverter.port.value, timeout).addCallback(self.controlConnectionMade).addErrback(self.connectionFailed)

	def controlConnectionMade(self, ftpclient):
		self["text"].setText(_("Connection to remote IP ok"))
		ftpclient.quit()
		self.fetchRemoteBouqets()

	def connectionFailed(self, *args):
		self.working = False
		self["text"].setText(_("Could not connect to remote server IP"))

	def fetchRemoteBouqets(self):
		self["text"].setText(_("Downloading remote services"))
		self.readIndex = 0
		self.workList = []
		self.workList.append('bouquets.tv')
		self.workList.append('bouquets.radio')
		self.download(self.workList[0]).addCallback(self.fetchRemoteBouqetsFinished).addErrback(self.fetchRemoteBouqetsFailed)

	def fetchRemoteBouqetsFailed(self, string):
		self.working = False
		self["text"].setText(_("Download from remote server failed"))

	def fetchRemoteBouqetsFinished(self, string):
		self.readIndex += 1
		if self.readIndex < len(self.workList):
			self.download(self.workList[self.readIndex]).addCallback(self.fetchRemoteBouqetsFinished).addErrback(self.fetchRemoteBouqetsFailed)
		else:
			self.parseBouqets()

	def parserWork(self, list, name):
		try:
			lines = open(name).readlines()
			for line in lines:
				tmp = line.split('userbouquet.')
				if len(tmp) > 1:
					if '\"' in line:
						tmp2 = tmp[1].split('\"')
					else:
						tmp2 = tmp[1].split('\n')
					list.append(tmp2[0])
		except:
			pass

	def parseBouqets(self):
		list = []
		self.parserWork(list, DIR_TMP + 'bouquets.tv')
		self.parserWork(list, DIR_TMP + 'bouquets.radio')
		self.readIndex = 0
		self.workList = []
		for listindex in range(len(list)):
			self.workList.append('userbouquet.' + list[listindex])
		self.workList.append('lamedb')
		self.download(self.workList[0]).addCallback(self.fetchUserBouquetsFinished).addErrback(self.fetchUserBouquetsFailed)

	def fetchUserBouquetsFailed(self, string):
		if self.readIndex < len(self.workList) and self.readIndex > 0:
			self.workList.remove(self.workList[self.readIndex])
			self.readIndex -= 1
			self.fetchUserBouquetsFinished('')
		self.working = False
		self["text"].setText(_("Download from remote server failed"))

	def fetchUserBouquetsFinished(self, string):
		self.readIndex += 1
		if self.readIndex < len(self.workList):
			self["text"].setText(_("Reading remote server services %d of %d") % (self.readIndex, len(self.workList)-1))
			self.download(self.workList[self.readIndex]).addCallback(self.fetchUserBouquetsFinished).addErrback(self.fetchUserBouquetsFailed)
		else:
			if len(self.workList) > 0:
				self["text"].setText(_("Select favorites bouqets to import by pressing OK"))
				for listindex in range(len(self.workList) - 1):
					name = self.readBouquetName(DIR_TMP + self.workList[listindex])
					self.list.addSelection(name, self.workList[listindex], listindex, False)
				self.removeFiles(DIR_TMP, "bouquets.")
				self.working = False
				self.hasFiles = True
				self["key_green"].setText(_("Download"))
				self["key_blue"].setText(_("Invert"))
				self["key_yellow"].setText("")
				self.keyBlue()

	def download(self, file, contextFactory = None, *args, **kwargs):
		client = FTPDownloader(
			self.getRemoteAdress(),
			config.plugins.RemoteStreamConverter.port.value,
			DIR_ENIGMA2 + file,
			DIR_TMP + file,
			config.plugins.RemoteStreamConverter.username.value,
			config.plugins.RemoteStreamConverter.password.value,
			*args,
			**kwargs
		)
		return client.deferred

	def convertBouquets(self):
		self.readIndex = 0
		while True:
			if 'lamedb' not in self.workList[self.readIndex]:
				filename = DIR_TMP + self.workList[self.readIndex]
				hasRemoteTag = False
				if self.checkBouquetAllreadyInList(self.workList[self.readIndex], self.workList[self.readIndex]) is True:
					self.workList[self.readIndex] = self.workList[self.readIndex].replace('userbouquet.', 'userbouquet.remote_')
					hasRemoteTag = True

				fp = open(DIR_ENIGMA2 + self.workList[self.readIndex], 'w')
				try:
					lines = open(filename).readlines()
					was_html = False
					for line in lines:
						if was_html and '#DESCRIPTION' in line:
							was_html = False
							continue
						if '#NAME' in line and hasRemoteTag:
							hasRemoteTag = False
							line = line.replace('#NAME ', '#NAME remote_')
						was_html = False
						if 'http' in line:
							was_html = True
							continue
						elif '#SERVICE' in line:
							line = line.strip('\r\n')
							line = line.strip('\n')
							tmp = line.split('#SERVICE')
							if '::' in tmp[1]:
								desc = tmp[1].split("::")
								if (len(desc)) == 2:
									tmp2 = tmp[1].split('::')
									service_ref = ServiceReference(tmp2[0] + ':')
									tag = tmp2[0][1:]
							else:
								tag = tmp[1][1:-1]
								service_ref = ServiceReference(tag)
							if config.plugins.RemoteStreamConverter.transcoding.value:
								bitrate = config.plugins.RemoteStreamConverter.bitrate.value
								resolution = config.plugins.RemoteStreamConverter.resolution.value
								(width, height) = tuple(resolution.split('x'))
								framrate = config.plugins.RemoteStreamConverter.framerate.value
								aspectratio = config.plugins.RemoteStreamConverter.aspectratio.value
								interlaced = config.plugins.RemoteStreamConverter.interlaced.value
								args = "?bitrate=%s?width=%s?height=%s?aspectratio=%s?interlaced=%s:" % (bitrate, width, height, aspectratio, interlaced)
								
								out = '#SERVICE ' + tag + ':' + quote('http://' + self.getRemoteAdress() + ':8001/' + tag) + "%3A" + args + service_ref.getServiceName() + '\n' 
							else:
								out = '#SERVICE ' + tag + ':' + quote('http://' + self.getRemoteAdress() + ':8001/' + tag) + ':' + service_ref.getServiceName() + '\n'
						else:
							out = line
						fp.write(out)
				except:
					pass
				fp.close()
			self.readIndex += 1
			if self.readIndex == len(self.workList):
				break
		self.removeFiles(DIR_TMP, "userbouquet.")

	def getTransponders(self, fp):
		step = 0
		lines = open(DIR_TMP + 'lamedb').readlines()
		for line in lines:
			if step == 0:
				if 'transponders' in line:
					step =1
			elif step == 1:
				if 'end' in line[:3]:
					fp.write(line)
					break
				else:
					fp.write(line)

	def getServices(self, fp):
		step = 0
		lines = open(DIR_TMP + 'lamedb').readlines()
		for line in lines:
			if step == 0:
				if 'services' in line[:8]:
					step =1
			elif step == 1:
				if 'end' in line[:3]:
					fp.write(line)
					break
				else:
					fp.write(line)

	def checkBouquetAllreadyInList(self, typestr, item):
		item = item.replace('userbouquet.', '')
		list = []
		if '.tv' in typestr:
			self.readBouquetList(list, '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "bouquets.tv" ORDER BY bouquet')
		else:
			self.readBouquetList(list, '1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "bouquets.radio" ORDER BY bouquet')
		if len(list) > 0:
			for x in list:
				if item in x:
					return True
		return False

	def createBouquetFile(self, target, source, matchstr, typestr):
		tmpFile = []
		fp = open(target, 'w')
		try:
			lines = open(source).readlines()
			for line in lines:
				tmpFile.append(line)
				fp.write(line)
			for item in self.workList:
				if typestr in item:
					if self.checkBouquetAllreadyInList(typestr, item) is True:
						item = item.replace('userbouquet.', 'userbouquet.remote_')
					tmp = matchstr + item + '\" ORDER BY bouquet\n'
					match = False
					for x in tmpFile:
						if tmp in x:
							match = True
					if match is not True:
						fp.write(tmp)
			fp.close()
			self.copyFile(target, source)
		except:
			pass

	def keyGreen(self):
		if not self.hasFiles:
			return
		self.workList = []
		tmpList = []
		tmpList = self.list.getSelectionsList()
		if len(tmpList) == 0:
			self["text"].setText(_("No bouquets selected"))
			return
		for item in tmpList:
			self.workList.append(item[1])
		fileValid = False
		state = 0
		fp = open(DIR_TMP + 'tmp_lamedb', 'w')
		try:
			lines = open(DIR_ENIGMA2 + 'lamedb').readlines()
			for line in lines:
				if 'eDVB services' in line:
					fileValid = True
				if state == 0:
					if 'transponders' in line[:12]:
						fp.write(line)
					elif 'end' in line[:3]:
						self.getTransponders(fp)
						state = 1
					else:
						fp.write(line)
				elif state == 1:
					if 'services' in line[:8]:
						fp.write(line)
					elif 'end' in line[:3]:
						self.getServices(fp)
						state = 2
					else:
						fp.write(line)
				elif state == 2:
					fp.write(line)
		except:
			pass
		fp.close()
		if fileValid is not True:
			self.copyFile(DIR_TMP + 'lamedb', DIR_TMP + 'tmp_lamedb')
		tv = False
		radio = False
		for item in self.workList:
			if '.tv' in item:
				tv = True
			if '.radio' in item:
				radio = True
		if radio or tv:
			if tv:
				self.createBouquetFile(DIR_TMP + 'tmp_bouquets.tv', DIR_ENIGMA2 + 'bouquets.tv', '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET \"', '.tv')
			if radio:
				self.createBouquetFile(DIR_TMP + 'tmp_bouquets.radio', DIR_ENIGMA2 + 'bouquets.radio', '#SERVICE 1:7:2:0:0:0:0:0:0:0:FROM BOUQUET \"', '.radio')
			self.copyFile(DIR_TMP + 'tmp_lamedb', DIR_ENIGMA2 + 'lamedb')
			db = eDVBDB.getInstance()
			db.reloadServicelist()
			self.convertBouquets()
			self.removeFiles(DIR_TMP, "tmp_")
			self.removeFiles(DIR_TMP, "lamedb")
			db = eDVBDB.getInstance()
			db.reloadServicelist()
			db.reloadBouquets()
		self.keyExit(True)
		
	def getRemoteAdress(self):
		if config.plugins.RemoteStreamConverter.address.value != "":
			return config.plugins.RemoteStreamConverter.address.value
		else:
			return '%d.%d.%d.%d' % (config.plugins.RemoteStreamConverter.ip.value[0], config.plugins.RemoteStreamConverter.ip.value[1], config.plugins.RemoteStreamConverter.ip.value[2], config.plugins.RemoteStreamConverter.ip.value[3])

	def readBouquetName(self, filename):
		try:
			lines = open(filename).readlines()
			for line in lines:
				if '#NAME' in line:
					tmp = line.split('#NAME ')
					if '\r' in tmp[1]:
						bouquetname = tmp[1].split('\r\n')[0]
					else:
						bouquetname = tmp[1].split('\n')[0]
					return bouquetname
		except:
			pass
		return ""

	def readBouquetList(self, list, rootstr):
		bouquet_root = eServiceReference(rootstr)
		if not bouquet_root is None:
			serviceHandler = eServiceCenter.getInstance()
			if not serviceHandler is None:
				servicelist = serviceHandler.list(bouquet_root)
				if not servicelist is None:
					while True:
						service = servicelist.getNext()
						if not service.valid():
							break
						tmp = service.toString().split('userbouquet.')
						if len(tmp[1]) > 0:
							tmp2 = tmp[1].split('\"')
							name = self.readBouquetName(DIR_ENIGMA2 + 'userbouquet.' + tmp2[0])
							list.append((name, tmp2[0]))

	def removeFiles(self, targetdir, target):
		import os
		targetLen = len(target)
		for root, dirs, files in os.walk(targetdir):
			for name in files:
				if target in name[:targetLen]:
					os.remove(os.path.join(root, name))

	def copyFile(self, source, dest):
		import shutil
		shutil.copy2(source, dest)
		
	def keyExit(self, ret = False):
		if ret:
			print "[RemoteTunerServerEditor] keyExit TRUE"  
			self.close(True)
		else:
			print "[RemoteTunerServerEditor] keyExit FALSE"  
			self.close(False)

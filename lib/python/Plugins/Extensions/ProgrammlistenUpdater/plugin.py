from glob import glob
from os import chdir, makedirs, remove
from os.path import exists, dirname, isfile, join
from re import findall, S
from shutil import rmtree, copy2
from sys import modules
from tarfile import open as taropen
from time import time, localtime, strftime
from urllib.request import urlopen, Request
from zipfile import ZipFile

from enigma import checkInternetAccess, eDVBDB, eTimer, eListboxPythonMultiContent, gFont, RT_HALIGN_LEFT, RT_HALIGN_RIGHT
from Components.config import ConfigSubsection, ConfigYesNo, ConfigText, config, configfile
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText
from Components.NimManager import nimmanager
from Components.ScrollLabel import ScrollLabel
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from skin import parameters

config.pud = ConfigSubsection()
config.pud.autocheck = ConfigYesNo(default=False)
config.pud.showmessage = ConfigYesNo(default=True)
config.pud.lastdate = ConfigText(visible_width=200)
config.pud.satname = ConfigText(visible_width=200, default="Enigma2 D 19E FTA")
config.pud.update_question = ConfigYesNo(default=False)
config.pud.just_update = ConfigYesNo(default=False)

URL = "http://www.sattechnik.de/programmlisten-update/asd.php"
HISTORY = "http://www.sattechnik.de/programmlisten-update/history.txt"  # This HISTORY may redirects to https://www.receiver-settings.de/
MODULE_NAME = __name__.split(".")[-1]
Directory = dirname(str(modules[__name__].__file__))


def downloadPUPage(url):
	liste = []
	try:
		req = Request(url)  # req.add_header('User-Agent', 'VAS')
		response = urlopen(req, timeout=10)
		link = response.read().decode()
		response.close()
		for link, name, date in findall(r'<td><a href="(.+?)">(.+?)</a></td>.*?<td>(.+?)</td>', link, flags=S):
			prelink = url.replace("asd.php", "") if not link.startswith("http://") else ""
			liste.append((date, name, f"{prelink}{link}"))
	except Exception as err:
		print(f"ERROR downloadPUPage {url}: {err}")
	return liste


def ConverDate(data):
	return f"{data[-2:]}-{data[-4:][:2]}-20{data[:2]}"


def ConverDateBack(data):
	return f"{data[-2:]}{data[-7:][:2]}{data[:2]}"


def DownloadInfo(url):
	text = ""
	try:
		req = Request(url)
		response = urlopen(req, timeout=10)
		text = response.read().decode("windows-1252")
		response.close()
	except Exception as err:
		print(f"ERROR Download History {url}: {err}")
	return text


def installPUSettings(name, link, date):
	def downloadPUSetting(link):
		req = Request(link)
		# req.add_header('User-Agent', 'VAS')
		response = urlopen(req, timeout=10)
		newlink = response.read()
		response.close()
		with open(tempZip, "wb") as fd:
			fd.write(newlink)
		if exists(tempZip):
			makedirs(tempUnzipDir, 0o755, exist_ok=True)
			try:
				with ZipFile(tempZip) as zipData:
					zipData.extractall(tempUnzipDir)
#				system("unzip -q %s -d %s" % (tempZip, tempUnzipDir))
			except Exception as err:
				print(f"ERROR unzip listE2.zip: {err}")
			if not exists(tempSettingsDir):
				makedirs(tempSettingsDir, 0o755, exist_ok=True)
				try:
					zipfilename = glob(f"{tempUnzipDir}/*.zip")[0]
					with ZipFile(zipfilename) as zipData:
						zipData.extractall(tempSettingsDir)
					#system("unzip -q %s/*.zip -d  %s" % (tempUnzipDir, tempSettingsDir))
				except Exception as err:
					print(f"ERROR unzip {name}.zip: {err}")
		return False

	settingsDir = join(Directory, "Settings", "enigma2")
	tempDir = join(Directory, "Settings", "tmp")
	tempUnzipDir = join(tempDir, "listE2_unzip")
	tempZip = join(tempDir, "listE2.zip")
	tempSettingsDir = join(tempDir, "setting")
	# remove old download if exists
	if exists(tempDir):
		rmtree(tempDir)
	# create a new empty tmp folder
	if not exists(tempDir):
		makedirs(tempDir, 0o755, exist_ok=True)
	# copy current settings
	if not exists(settingsDir):
		makedirs(settingsDir, 0o755, exist_ok=True)
	tt = strftime("%y%m%d_%H%M%S", localtime(time()))
	with taropen(f"{settingsDir}/{tt}_enigma2settingsbackup.tar.gz", "w:gz") as tar:
		for file in glob("/etc/enigma2/*.tv") + glob("/etc/enigma2/*.radio") + ["/etc/enigma2/lamedb"]:
			if isfile(file):
				tar.add(file)
#	system("tar -czvf %s/%s_enigma2settingsbackup.tar.gz -C / /etc/enigma2/*.tv /etc/enigma2/*.radio /etc/enigma2/lamedb" % (settingsDir, tt))
	if not downloadPUSetting(link):
		def getRemoveList():
			removeList = []
			inhaltfile = join(tempSettingsDir, "inhalt.lst")
			if isfile(inhaltfile):
				with open(inhaltfile) as f:
					data = f.read()
				removeList = data.splitlines()
			return [join("/etc/enigma2/", file) for file in removeList]
		for file in getRemoveList() + glob("/etc/enigma2/*.del") + ["/etc/enigma2/lamedb"]:
			if isfile(file):
				remove(file)
		# copy new settings
		for file in glob(f"{tempSettingsDir}/*.tv") + glob(f"{tempSettingsDir}/*.radio") + [f"{tempSettingsDir}/lamedb"]:
			copy2(file, "/etc/enigma2/")
		# remove /tmp folder
		if exists(tempDir):
			rmtree(tempDir)
		return True
	else:
		return False


class PUCheckTimer:
	def __init__(self):
		self.session = None
		self.UpdateTimer = eTimer()
		self.UpdateTimer.callback.append(self.startTimerSetting)

	def gotSession(self, session, url):
		self.session = session
		self.url = url
		if config.pud.autocheck.value:
			self.timerSetting(True)

	def startDownload(self, name, link, date):
		if installPUSettings(name, link, date):
			# save new name/date
			config.pud.autocheck.value = True
			config.pud.lastdate.value = date
			config.pud.satname.value = name
			config.pud.save()
			configfile.save()
			eDVBDB.getInstance().reloadServicelist()
			eDVBDB.getInstance().reloadBouquets()
			self.session.open(MessageBox, _("New Setting DXAndy ") + name + _(" of ") + date + _(" updated"), MessageBox.TYPE_INFO, timeout=15)
		else:
			self.session.open(MessageBox, _("Error Download Setting"), MessageBox.TYPE_ERROR, timeout=15)

	def stopTimer(self):
		self.UpdateTimer.stop()

	def timerSetting(self, Auto=False):
		self.stopTimer()
		now = time()
		ttime = now + 28800  # Check each 8 hours for new version
		delta1 = int(ttime - now)
		self.UpdateTimer.start(120000 if Auto else 1000 * delta1, True)  # Do Check at bootup after 2 min

	def CBupdate(self, req):
		if req:
			config.pud.update_question.value = True
			self.startDownload(self.name, self.link, ConverDate(self.date))
		else:
			config.pud.update_question.value = False
		config.pud.save()

	def startTimerSetting(self):
		if checkInternetAccess("www.google.de", 5) == 0:
			print("[Programmlisten-Updater]: CHECK FOR UPDATE")
			sList = downloadPUPage(self.url)
			for date, name, link in sList:
				if name == config.pud.satname.value:
					lastdate = config.pud.lastdate.value
					if date > ConverDateBack(lastdate):
						self.date = date
						self.name = name
						self.link = link
						yesno_default = config.pud.update_question.value
						print("[Programmlisten-Updater]: NEW SETTINGS DXANDY")
						if config.pud.just_update.value:
							# Update without information
							self.startDownload(self.name, self.link, ConverDate(self.date))
						else:
							# Auto update with confrimation
							self.session.openWithCallback(self.CBupdate, MessageBox, _("New Setting DXAndy ") + name + _(" of ") + ConverDate(date) + _(" available !!" + "\n\n" + "Do you want to install the new settings list?"), MessageBox.TYPE_YESNO, default=yesno_default, timeout=60)
					else:
						print("[Programmlisten-Updater]: NO NEW UPDATE AVAILBLE")
					break
		self.timerSetting()


class PUHistoryScreen(Screen):
	skin = """
		<screen name="PU_History" position="center,center" size="600,470">
			<ePixmap pixmap="skin_default/buttons/red.png" position="5,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="5,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" transparent="1" />
			<widget name="History" position="25,70" size="560,350" scrollbarMode="showOnDemand" />
		</screen>
		"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = "PU_History"
		self.setTitle(_("Programmlisten History"))
		self["key_red"] = StaticText(_("Exit"))
		self["History"] = ScrollLabel()
		self["Actions"] = ActionMap(
			["OkCancelActions", "ColorActions", "DirectionActions"],
			{
				"red": self.close,
				"cancel": self.close,
				"ok": self.close,
				"up": self["History"].pageUp,
				"down": self["History"].pageDown,
				"left": self["History"].pageUp,
				"right": self["History"].pageDown,
			},
		)
		self["History"].setText(DownloadInfo(HISTORY))


class PURestoreScreen(Screen):
	skin = """
		<screen name="PU_Restore" position="center,center" size="600,470">
			<ePixmap pixmap="skin_default/buttons/red.png" position="5,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="155,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="305,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="5,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_green" render="Label" position="155,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_yellow" render="Label" position="305,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" foregroundColor="#ffffff" transparent="1" />
			<widget name="ListSetting" position="25,70" size="560,350" scrollbarMode="showOnDemand" />
		</screen>
		"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self["ListSetting"] = MenuList([])
		self.skinName = "PU_Restore"
		self.setTitle(_("Programmlisten Restore"))
		self["key_red"] = StaticText(_("Exit"))
		self["key_green"] = StaticText(_("Restore"))
		self["key_yellow"] = StaticText(_("Delete"))
		self["ColorActions"] = ActionMap(
			["OkCancelActions", "ColorActions"],
			{
				"red": self.close,
				"green": self.keyGreen,
				"yellow": self.keyYellow,
				"cancel": self.close,
				"ok": self.keyGreen,
			},
		)
		self.settingsDir = join(Directory, "Settings", "enigma2")
		self.List = self.searchSettings()
		self.settingsMenu()

	def keyGreen(self):
		def keyGreenCallback(req):
			if req:
				self.doRestore()
		self.filename = self["ListSetting"].getCurrent()
		if self.filename is not None:
			self.session.openWithCallback(keyGreenCallback, MessageBox, _("Selected settings list: %s\n\nDo you want to restore this settinglist?") % (self.filename), MessageBox.TYPE_YESNO)

	def keyYellow(self):
		def keyYellowCallback(req):
			if req:
				path = join(self.settingsDir, self.filename)
				try:
					rmtree(path)
				except OSError as err:
					print(f"Error {err.errno}: Unable to remove directory tree '{path}'!  ({err.strerror})")
				self.List = self.searchSettings()
				self.settingsMenu()
		self.filename = self["ListSetting"].getCurrent()
		if self.filename is not None:
			self.session.openWithCallback(keyYellowCallback, MessageBox, _("Selected settings list: %s\n\nDo you want to delete this settinglist?") % (self.filename), MessageBox.TYPE_YESNO)

	def searchSettings(self):
		liste = []
		chdir(self.settingsDir)
		for file in glob("*backup.tar.gz"):
			liste.append(file)
		return liste

	def settingsMenu(self):
		self["ListSetting"].setList(self.List)

	def doRestore(self):
		# Set Backup date
		date = ConverDate(self.filename[:6])
		config.pud.lastdate.value = date
		config.pud.save()
		configfile.save()
		# Remove current settings list
		removeList = glob("/etc/enigma2/*.radio") + glob("/etc/enigma2/*.tv") + ["/etc/enigma2/lamedb"]
		for file in removeList:
			remove(file)
		# Restore settings list
		with taropen(join(self.settingsDir, self.filename)) as tar:
			tar.extractall("/")
#		system("tar -xzvf %s -C /" % join(self.settingsDir, self.filename))
		# Reload settings list
		eDVBDB.getInstance().reloadServicelist()
		eDVBDB.getInstance().reloadBouquets()
		self.session.open(MessageBox, _("Setting Restored ") + self.filename + _(" of ") + date, MessageBox.TYPE_INFO, timeout=15)
		self.close()


class MenuListSetting(MenuList):
	def __init__(self, list):
		MenuList.__init__(self, list, True, eListboxPythonMultiContent)
		font, size = parameters.get("ProgrammlistenUpdaterListFont", ("Regular", 25))
		self.l.setFont(0, gFont(font, size))


class PUMainScreen(Screen):
	skin = """
		<screen name="Programmlisten_Updater" position="center,center" size="710,500">
			<ePixmap pixmap="skin_default/buttons/red.png" position="5,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="155,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="305,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="5,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_green" render="Label" position="155,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" foregroundColor="#ffffff" transparent="1" />
			<widget source="key_yellow" render="Label" position="305,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" foregroundColor="#ffffff" transparent="1" />
			<widget name="MenuListSetting" position="25,70" size="660,315" itemHeight="45" scrollbarMode="showOnDemand" />
			<widget name="description" position="25,420" size="660,60" font="Regular;22" halign="center" valign="center" />
			<widget name="update" position="440,5" size="200,25" font="Regular;22" halign="center" valign="center" />
		</screen>
		"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self["description"] = Label("description")
		self["MenuListSetting"] = MenuListSetting([])
		self.skinName = "Programmlisten_Updater"
		self.setTitle(_("Programmlisten from DXAndy"))
		self["description"] = Label(_("Current installed") + ":\nn/a")
		self["update"] = Label(_("disabled"))
		self["key_red"] = StaticText(_("Exit"))
		self["key_green"] = StaticText(_("Install"))
		self["key_yellow"] = StaticText(_("AutoUpdate"))
		self["ColorActions"] = ActionMap(
			["OkCancelActions", "MenuActions", "ColorActions", "InfoActions"],
			{
				"red": self.keyCancel,
				"green": self.keyOk,
				"yellow": self.keyAutoUpdate,
				"cancel": self.keyCancel,
				"ok": self.keyOk,
				"menu": self.keyMenu,
				"info": self.keyHistory,
			},
		)
		self.settingsDir = join(Directory, "Settings", "enigma2")
		self.List = downloadPUPage(URL)
		self.settingsMenu()
		self.onShown.append(self.showInfo)
		config.pud.showmessage.value = True

	def keyMenu(self):
		if exists(self.settingsDir):
			self.session.open(PURestoreScreen)

	def keyHistory(self):
		self.session.open(PUHistoryScreen)

	def keyCancel(self):
		configfile.save()
		self.close()

	def keyAutoUpdate(self):
		puTimerClass.stopTimer()
		if config.pud.autocheck.value and config.pud.just_update.value:
			self["update"].setText(_("disabled"))
			config.pud.autocheck.value = False
		else:
			if config.pud.just_update.value:
				self["update"].setText(_("enabled"))
				config.pud.just_update.value = False
			else:
				self["update"].setText(_("update"))
				config.pud.just_update.value = True
			if config.pud.lastdate.value == "":
				self.session.open(MessageBox, _("No Settings loaded !!\n\nPlease install first a settinglist"), MessageBox.TYPE_INFO, timeout=15)
			config.pud.autocheck.value = True
			puTimerClass.timerSetting()
		config.pud.save()

	def keyOk(self):
		def keyOkCallback(req):
			if req:
				puTimerClass.startDownload(self.name, self.link, self.date)
		self.name = self["MenuListSetting"].getCurrent()[0][3]
		self.date = self["MenuListSetting"].getCurrent()[0][4]
		self.link = self["MenuListSetting"].getCurrent()[0][2]
		self.session.openWithCallback(keyOkCallback, MessageBox, _("Selected settings list:\n\nSetting: %s\nDate: %s\n\nDo you want to install this settinglist?") % (self.name, self.date), MessageBox.TYPE_YESNO)

	def showInfo(self):
		if not exists(self.settingsDir):
			makedirs(self.settingsDir, 0o755, exist_ok=True)
		if config.pud.autocheck.value:
			self["update"].setText(_("update") if config.pud.just_update.value else _("enabled"))
		else:
			self["update"].setText(_("disabled"))
		if config.pud.lastdate.value == "":
			self["description"].setText(_("Current installed") + ":\nn/a")
		else:
			self["description"].setText(_("Current installed") + f":\n{config.pud.satname.value} {config.pud.lastdate.value}")

	def ListEntryMenuSettings(self, name, date, link, name1, date1):
		res = [(name, date, link, name1, date1)]
		try:
			x, y, w1, w2, h = parameters.get("ProgrammlistenUpdaterList", (15, 7, 420, 210, 40))
		except ValueError:
			x, y, w1, w2, h = (15, 7, 420, 210, 40)
		res.append(MultiContentEntryText(pos=(x, y), size=(w1, h), font=0, text=name, flags=RT_HALIGN_LEFT))
		res.append(MultiContentEntryText(pos=(x + w1, y), size=(w2, h), font=0, color=16777215, text=date1, flags=RT_HALIGN_RIGHT))
		res.append(MultiContentEntryText(pos=(0, 0), size=(0, 0), font=0, text=link, flags=RT_HALIGN_LEFT))
		res.append(MultiContentEntryText(pos=(0, 0), size=(0, 0), font=0, text=name1, flags=RT_HALIGN_LEFT))
		res.append(MultiContentEntryText(pos=(0, 0), size=(0, 0), font=0, text=date, flags=RT_HALIGN_LEFT))
		return res

	def settingsMenu(self):
		self.listB = []
		for date, name, link in self.List:
			self.listB.append(self.ListEntryMenuSettings(str(name.title()), str(date), str(link), str(name), ConverDate(str(date))))
		if not self.listB:
			self.listB.append(self.ListEntryMenuSettings(_("Server down"), "", "", "", ""))
		self["MenuListSetting"].setList(self.listB)


puTimerClass = PUCheckTimer()


def main(session, **kwargs):
	session.open(PUMainScreen)


def sessionstart(reason, session):
	if reason == 0:
		puTimerClass.gotSession(session, URL)


def autoStart(reason, **kwargs):
	if reason == 1:
		puTimerClass.stopTimer()


def Plugins(**kwargs):
	if nimmanager.hasNimType("DVB-S"):
		return [
			PluginDescriptor(name=_("Programmlisten-Updater V") + "1.3", description=_("Programmlisten-Updater from DXAndy"), icon="plugin.png", where=PluginDescriptor.WHERE_PLUGINMENU, fnc=main),
			PluginDescriptor(where=PluginDescriptor.WHERE_SESSIONSTART, fnc=sessionstart),
			PluginDescriptor(where=PluginDescriptor.WHERE_AUTOSTART, fnc=autoStart)
		]
	else:
		return []

# -*- coding: iso-8859-1 -*-
from enigma import eConsoleAppContainer
from Components.Console import Console
from Components.About import about
from Components.PackageInfo import PackageInfoHandler
from Components.Language import language
from Components.Sources.List import List
from Components.Ipkg import IpkgComponent
from Components.Network import iNetwork
from Tools.Directories import pathExists, fileExists, resolveFilename, SCOPE_METADIR
from Tools.HardwareInfo import HardwareInfo
from time import time


class SoftwareTools(PackageInfoHandler):
	lastDownloadDate = None
	NetworkConnectionAvailable = None
	list_updating = False
	available_updates = 0
	available_updatelist  = []
	available_packetlist  = []
	installed_packetlist = {}


	def __init__(self):
		aboutInfo = about.getImageVersionString()
		if aboutInfo.startswith("dev-"):
			self.ImageVersion = 'Experimental'
		else:
			self.ImageVersion = 'Stable'
		self.language = language.getLanguage()[:2] # getLanguage returns e.g. "fi_FI" for "language_country"
		PackageInfoHandler.__init__(self, self.statusCallback, blocking = False, neededTag = 'ALL_TAGS', neededFlag = self.ImageVersion)
		self.directory = resolveFilename(SCOPE_METADIR)
		self.list = List([])
		self.NotifierCallback = None
		self.Console = Console()
		self.UpdateConsole = Console()
		self.cmdList = []
		self.unwanted_extensions = ('-dbg', '-dev', '-doc', '-staticdev', '-src')
		self.ipkg = IpkgComponent()
		self.ipkg.addCallback(self.ipkgCallback)

	def statusCallback(self, status, progress):
		pass

	def startSoftwareTools(self, callback = None):
		if callback is not None:
			self.NotifierCallback = callback
		iNetwork.checkNetworkState(self.checkNetworkCB)

	def checkNetworkCB(self,data):
		if data is not None:
			if data <= 2:
				self.NetworkConnectionAvailable = True
				self.getUpdates()
			else:
				self.NetworkConnectionAvailable = False
				self.getUpdates()

	def getUpdates(self, callback = None):
		if self.lastDownloadDate is None:
				if self.NetworkConnectionAvailable == True:
					self.lastDownloadDate = time()
					if self.list_updating is False and callback is None:
						self.list_updating = True
						self.ipkg.startCmd(IpkgComponent.CMD_UPDATE)
					elif self.list_updating is False and callback is not None:
						self.list_updating = True
						self.NotifierCallback = callback
						self.ipkg.startCmd(IpkgComponent.CMD_UPDATE)
					elif self.list_updating is True and callback is not None:
						self.NotifierCallback = callback
				else:
					self.list_updating = False
					if callback is not None:
						callback(False)
					elif self.NotifierCallback is not None:
						self.NotifierCallback(False)
		else:
			if self.NetworkConnectionAvailable == True:
				self.lastDownloadDate = time()
				if self.list_updating is False and callback is None:
					self.list_updating = True
					self.ipkg.startCmd(IpkgComponent.CMD_UPDATE)
				elif self.list_updating is False and callback is not None:
					self.list_updating = True
					self.NotifierCallback = callback
					self.ipkg.startCmd(IpkgComponent.CMD_UPDATE)
				elif self.list_updating is True and callback is not None:
					self.NotifierCallback = callback
			else:
				if self.list_updating and callback is not None:
						self.NotifierCallback = callback
						self.startIpkgListAvailable()
				else:
					self.list_updating = False
					if callback is not None:
						callback(False)
					elif self.NotifierCallback is not None:
						self.NotifierCallback(False)

	def ipkgCallback(self, event, param):
		if event == IpkgComponent.EVENT_ERROR:
			self.list_updating = False
			if self.NotifierCallback is not None:
				self.NotifierCallback(False)
		elif event == IpkgComponent.EVENT_DONE:
			if self.list_updating:
				self.startIpkgListAvailable()
		pass

	def startIpkgListAvailable(self, callback = None):
		if callback is not None:
			self.list_updating = True
		if self.list_updating:
			if not self.UpdateConsole:
				self.UpdateConsole = Console()
			cmd = self.ipkg.ipkg + " list"
			self.UpdateConsole.ePopen(cmd, self.IpkgListAvailableCB, callback)

	def IpkgListAvailableCB(self, result, retval, extra_args = None):
		(callback) = extra_args
		if result:
			if self.list_updating:
				self.available_packetlist = []
				for x in result.splitlines():
					tokens = x.split(' - ')
					name = tokens[0].strip()
					if not any(name.endswith(x) for x in self.unwanted_extensions):
						l = len(tokens)
						version = l > 1 and tokens[1].strip() or ""
						descr = l > 2 and tokens[2].strip() or ""
						self.available_packetlist.append([name, version, descr])
				if callback is None:
					self.startInstallMetaPackage()
				else:
					if self.UpdateConsole:
						if len(self.UpdateConsole.appContainers) == 0:
								callback(True)
		else:
			self.list_updating = False
			if self.UpdateConsole:
				if len(self.UpdateConsole.appContainers) == 0:
					if callback is not None:
						callback(False)

	def startInstallMetaPackage(self, callback = None):
		if callback is not None:
			self.list_updating = True
		if self.list_updating:
			if self.NetworkConnectionAvailable == True:
				if not self.UpdateConsole:
					self.UpdateConsole = Console()
				cmd = self.ipkg.ipkg + " install enigma2-meta enigma2-plugins-meta enigma2-skins-meta"
				self.UpdateConsole.ePopen(cmd, self.InstallMetaPackageCB, callback)
			else:
				self.InstallMetaPackageCB(True)

	def InstallMetaPackageCB(self, result, retval = None, extra_args = None):
		(callback) = extra_args
		if result:
			self.fillPackagesIndexList()
			if callback is None:
				self.startIpkgListInstalled()
			else:
				if self.UpdateConsole:
					if len(self.UpdateConsole.appContainers) == 0:
							callback(True)
		else:
			self.list_updating = False
			if self.UpdateConsole:
				if len(self.UpdateConsole.appContainers) == 0:
					if callback is not None:
						callback(False)

	def startIpkgListInstalled(self, callback = None):
		if callback is not None:
			self.list_updating = True
		if self.list_updating:
			if not self.UpdateConsole:
				self.UpdateConsole = Console()
			cmd = self.ipkg.ipkg + " list_installed"
			self.UpdateConsole.ePopen(cmd, self.IpkgListInstalledCB, callback)

	def IpkgListInstalledCB(self, result, retval, extra_args = None):
		(callback) = extra_args
		if result:
			self.installed_packetlist = {}
			for x in result.splitlines():
				tokens = x.split(' - ')
				name = tokens[0].strip()
				if not any(name.endswith(x) for x in self.unwanted_extensions):
					l = len(tokens)
					version = l > 1 and tokens[1].strip() or ""
					self.installed_packetlist[name] = version
			for package in self.packagesIndexlist[:]:
				if not self.verifyPrerequisites(package[0]["prerequisites"]):
					self.packagesIndexlist.remove(package)
			for package in self.packagesIndexlist[:]:
				attributes = package[0]["attributes"]
				if attributes.has_key("packagetype"):
					if attributes["packagetype"] == "internal":
						self.packagesIndexlist.remove(package)
			if callback is None:
				self.countUpdates()
			else:
				if self.UpdateConsole:
					if len(self.UpdateConsole.appContainers) == 0:
							callback(True)
		else:
			self.list_updating = False
			if self.UpdateConsole:
				if len(self.UpdateConsole.appContainers) == 0:
					if callback is not None:
						callback(False)

	def countUpdates(self, callback = None):
		self.available_updates = 0
		self.available_updatelist  = []
		for package in self.packagesIndexlist[:]:
			attributes = package[0]["attributes"]
			packagename = attributes["packagename"]
			for x in self.available_packetlist:
				if x[0] == packagename:
					if self.installed_packetlist.has_key(packagename):
						if self.installed_packetlist[packagename] != x[1]:
							self.available_updates +=1
							self.available_updatelist.append([packagename])

		self.list_updating = False
		if self.UpdateConsole:
			if len(self.UpdateConsole.appContainers) == 0:
				if callback is not None:
					callback(True)
					callback = None
				elif self.NotifierCallback is not None:
					self.NotifierCallback(True)
					self.NotifierCallback = None

	def startIpkgUpdate(self, callback = None):
		if not self.Console:
			self.Console = Console()
		cmd = self.ipkg.ipkg + " update"
		self.Console.ePopen(cmd, self.IpkgUpdateCB, callback)

	def IpkgUpdateCB(self, result, retval, extra_args = None):
		(callback) = extra_args
		if result:
			if self.Console:
				if len(self.Console.appContainers) == 0:
					if callback is not None:
						callback(True)
						callback = None

	def cleanupSoftwareTools(self):
		self.list_updating = False
		if self.NotifierCallback is not None:
			self.NotifierCallback = None
		self.ipkg.stop()
		if self.Console is not None:
			if len(self.Console.appContainers):
				for name in self.Console.appContainers.keys():
					self.Console.kill(name)
		if self.UpdateConsole is not None:
			if len(self.UpdateConsole.appContainers):
				for name in self.UpdateConsole.appContainers.keys():
					self.UpdateConsole.kill(name)

	def verifyPrerequisites(self, prerequisites):
		if prerequisites.has_key("hardware"):
			hardware_found = False
			for hardware in prerequisites["hardware"]:
				if hardware == HardwareInfo().device_name:
					hardware_found = True
			if not hardware_found:
				return False
		return True

iSoftwareTools = SoftwareTools()

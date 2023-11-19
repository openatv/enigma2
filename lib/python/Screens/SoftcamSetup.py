from enigma import eTimer
from os import listdir, readlink
from os.path import exists, isfile, islink, join, split as pathsplit
from socket import socket, AF_UNIX, SOCK_STREAM

from Screens.InfoBarGenerics import autocam
from Components.ActionMap import HelpableActionMap
from Components.config import ConfigSelection, config
from Components.ScrollLabel import ScrollLabel
from Components.Sources.StaticText import StaticText
from Components.SystemInfo import updateSysSoftCam, BoxInfo
from Screens.Setup import Setup
from ServiceReference import ServiceReference
from Tools.Directories import isPluginInstalled
from Tools.GetEcmInfo import GetEcmInfo


class CamControl:
	'''CAM convention is that a softlink named /etc/init.c/softcam.* points
	to the start/stop script.'''

	def __init__(self, name):
		self.name = name
		self.notFound = None
		self.link = join("/etc/init.d", name)
		if not exists(self.link):
			print(f"[CamControl] No softcam link: '{self.link}'")
			if islink(self.link) and exists("/etc/init.d/softcam.None"):
				target = self.current()
				if target:
					self.notFound = target
					print(f"[CamControl] wrong target '{target}' set to None")
					self.switch("None")  # wrong link target set to None

	def getList(self):
		result = []
		prefix = f"{self.name}."
		for f in listdir("/etc/init.d"):
			if f.startswith(prefix):
				result.append(f[len(prefix):])
		return result

	def current(self):
		try:
			l = readlink(self.link)
			prefix = f"{self.name}."
			return pathsplit(l)[1].split(prefix, 2)[1]
		except OSError:
			pass
		return None

	def switch(self, newcam):
		deamonSocket = socket(AF_UNIX, SOCK_STREAM)
		deamonSocket.connect("/tmp/deamon.socket")
		deamonSocket.send(f"SWITCH_{self.name.upper()},{newcam}".encode())
		deamonSocket.close()

	def restart(self):
		deamonSocket = socket(AF_UNIX, SOCK_STREAM)
		deamonSocket.connect("/tmp/deamon.socket")
		deamonSocket.send(f"RESTART,{self.name}".encode())
		deamonSocket.close()


class CamSetupCommon(Setup):
	def __init__(self, session, setup):
		self.switchTimer = eTimer()
		Setup.__init__(self, session=session, setup=setup)
		self["key_yellow"] = StaticText()
		self["restartActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.restart, _("Immediately restart selected devices."))
		}, prio=0, description=_("Softcam Actions"))

	def restart(self):
		self.camctrl.restart()
		self.switchTimer.timeout.get().append(self.switchDone)
		self.switchTimer.start(500, False)

	def switchDone(self):
		self.switchTimer.stop()
		self.saveAll()
		updateSysSoftCam()
		self.close()


class CardserverSetup(CamSetupCommon):
	def __init__(self, session):
		self.servicetype = "cardserver"
		self.camctrl = CamControl(self.servicetype)
		cardservers = self.camctrl.getList()
		defaultcardserver = self.camctrl.current()
		if not cardservers:
			cardservers = [("", _("None"))]
			defaultcardserver = ""
		config.misc.cardservers = ConfigSelection(default=defaultcardserver, choices=cardservers)
		CamSetupCommon.__init__(self, session=session, setup="Cardserver")

	def keySave(self):
		if config.misc.cardservers.value != self.camctrl.current():
			self.camctrl.switch(config.misc.cardservers.value)
			self.switchTimer.timeout.get().append(self.switchDone)
			self.switchTimer.start(500, False)


class SoftcamSetup(CamSetupCommon):
	def __init__(self, session):
		self.servicetype = "softcam"
		self.camctrl = CamControl(self.servicetype)
		self.ecminfo = GetEcmInfo()
		softcams = self.camctrl.getList()
		defaultsoftcam = self.camctrl.current()
		if not softcams:
			softcams = [("", _("None"))]
			defaultsoftcam = ""
		config.misc.softcams = ConfigSelection(default=defaultsoftcam, choices=softcams)
		if self.camctrl.notFound:
			print("[SoftcamSetup] current: '%s' not found" % self.camctrl.notFound)
			config.misc.softcams.value = "None"
			config.misc.softcams.save()
		CamSetupCommon.__init__(self, session=session, setup="Softcam")
		self["key_blue"] = StaticText()
		self["infoActions"] = HelpableActionMap(self, ["ColorActions"], {
			"blue": (self.softcamInfo, _("Display oscam information."))
		}, prio=0, description=_("Softcam Actions"))
		self["infoActions"].setEnabled(False)
		(newEcmFound, ecmInfo) = self.ecminfo.getEcm()
		self["info"] = ScrollLabel("".join(ecmInfo))
		self.EcmInfoPollTimer = eTimer()
		self.EcmInfoPollTimer.callback.append(self.setEcmInfo)
		self.EcmInfoPollTimer.start(1000)
		self.onShown.append(self.updateButtons)

	def selectionChanged(self):
		self.updateButtons()
		Setup.selectionChanged(self)

	def changedEntry(self):
		self.updateButtons()
		Setup.changedEntry(self)

	def keySave(self):
		if config.misc.softcams.value != self.camctrl.current():
			self.camctrl.switch(config.misc.softcams.value)
			self.switchTimer.timeout.get().append(self.switchDone)
			self.switchTimer.start(500, False)

	def updateButtons(self):
		if self.getCurrentItem() == config.misc.softcams and config.misc.softcams.value and config.misc.softcams.value.lower() != "none":
			self["key_blue"].setText(_("Info"))
			self["infoActions"].setEnabled(True)
		else:
			self["key_blue"].setText("")
			self["infoActions"].setEnabled(False)

	def softcamInfo(self):
		ppanelFilename = "/etc/ppanels/%s.xml" % config.misc.softcams.value
		if "oscam" in config.misc.softcams.value.lower():  # and isfile('/usr/lib/enigma2/python/Screens/OScamInfo.py'):
			from Screens.OScamInfo import OscamInfoMenu
			self.session.open(OscamInfoMenu)
		elif "cccam" in config.misc.softcams.value.lower():  # and isfile('/usr/lib/enigma2/python/Screens/CCcamInfo.py'):
			from Screens.CCcamInfo import CCcamInfoMain
			self.session.open(CCcamInfoMain)
		elif isfile(ppanelFilename) and isPluginInstalled("PPanel"):
			from Plugins.Extensions.PPanel.ppanel import PPanel
			self.session.open(PPanel, name="%s PPanel" % config.misc.softcams.value, node=None, filename=ppanelFilename, deletenode=None)

	def setEcmInfo(self):
		(newEcmFound, ecmInfo) = self.ecminfo.getEcm()
		if newEcmFound:
			self["info"].setText("".join(ecmInfo))


class AutocamSetup(Setup):
	def __init__(self, session):
		self.softcams = BoxInfo.getItem("Softcams")
		defaultsoftcam = BoxInfo.getItem("CurrentSoftcam")
		self.camitems = []
		self.services = []
		self.autocamData = autocam.data.copy()
		defaultsoftcams = [x for x in self.softcams if x != "None"]
		self.defaultautocam = config.misc.autocamDefault.value or defaultsoftcam
		self.autocamDefault = ConfigSelection(default=self.defaultautocam, choices=defaultsoftcams)
		Setup.__init__(self, session=session, setup="Autocam")
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self["addremoveActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.keyRemoveService, _("Remove service from autocam")),
			"blue": (self.keyAddService, _("Add service to autocam"))
		}, prio=0, description=_("Autocam Setup Actions"))
		self["addremoveActions"].setEnabled(False)

	def layoutFinished(self):
		Setup.layoutFinished(self)
		self.createItems()

	def createItems(self):
		self.camitems = []
		if config.misc.autocamEnabled.value:
			if self.autocamData:
				self.camitems.append(("**************************",))
			for serviceref in self.autocamData.keys():
				self.services.append(serviceref)
				cam = self.autocamData[serviceref]
				service = ServiceReference(serviceref)
				self.camitems.append((service.getServiceName(), ConfigSelection(default=cam, choices=self.softcams), serviceref))
		self.createSetup()

	def createSetup(self):  # NOSONAR silence S2638
		Setup.createSetup(self, appendItems=self.camitems)

	def selectionChanged(self):
		self.updateButtons()
		Setup.selectionChanged(self)

	def changedEntry(self):
		Setup.changedEntry(self)
		self.updateButtons()
		current = self["config"].getCurrent()
		if current:
			if current[1] == config.misc.autocamEnabled:
				self.createItems()
				return
			elif current[1] == self.autocamDefault:
				return
			newcam = current[1].value
			serviceref = current[2]
			if self.autocamData[serviceref] != newcam:
				self.autocamData[serviceref] = newcam

	def updateButtons(self):
		currentItem = self.getCurrentItem()
		if currentItem in (config.misc.autocamEnabled, self.autocamDefault):
			self["addremoveActions"].setEnabled(True)
			self["key_yellow"].setText("")
			self["key_blue"].setText("")
		else:
			self["addremoveActions"].setEnabled(True)
			self["key_yellow"].setText(_("Remove"))
			self["key_blue"].setText(_("Add service"))

	def keyRemoveService(self):
		currentItem = self.getCurrentItem()
		if currentItem in (config.misc.autocamEnabled, self.autocamDefault):
			return
		elif currentItem:
			serviceref = self["config"].getCurrent()[2]
			del self.autocamData[serviceref]
			index = self["config"].getCurrentIndex()
			self.createItems()
			self["config"].setCurrentIndex(index)

	def keyAddService(self):
		def keyAddServiceCallback(*result):
			if result:
				service = ServiceReference(result[0])
				serviceref = str(service)
				if serviceref not in self.autocamData:
					newData = {serviceref: self.defaultautocam}
					newData.update(self.autocamData)
					self.autocamData = newData
					self.createItems()
					self["config"].setCurrentIndex(2)

		from Screens.ChannelSelection import SimpleChannelSelection  # This must be here to avoid a boot loop!
		self.session.openWithCallback(keyAddServiceCallback, SimpleChannelSelection, _("Select"), currentBouquet=True)

	def keySave(self):
		if config.misc.autocamEnabled.value:
			autocam.data = self.autocamData
			config.misc.autocamDefault.value = self.autocamDefault.value
			config.misc.autocamDefault.save()
		config.misc.autocamEnabled.save()
		self.close()

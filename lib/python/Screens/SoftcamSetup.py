from enigma import eTimer
from os.path import isfile

from Screens.InfoBarGenerics import autocam
from Components.ActionMap import HelpableActionMap
from Components.config import ConfigSelection, config
from Components.ScrollLabel import ScrollLabel
from Components.Sources.StaticText import StaticText
from Components.SystemInfo import updateSysSoftCam, BoxInfo
from Screens.Setup import Setup
from ServiceReference import ServiceReference
from Tools.camcontrol import CamControl
from Tools.Directories import isPluginInstalled
from Tools.GetEcmInfo import GetEcmInfo


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
		if self["config"].getCurrentItem() == config.misc.softcams and config.misc.softcams.value and config.misc.softcams.value.lower() != "none":
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
		defaultautocam = config.misc.autocamDefault.value or defaultsoftcam
		self.autocamDefault = ConfigSelection(default=defaultautocam, choices=defaultsoftcams)
		Setup.__init__(self, session=session, setup="Autocam")
		self["key_yellow"] = StaticText()
		self["removeActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.keyRemoveItem, _("Remove service"))
		}, prio=0, description=_("Softcam Actions"))
		self["removeActions"].setEnabled(True)

	def layoutFinished(self):
		Setup.layoutFinished(self)
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

	def changedEntry(self):
		Setup.changedEntry(self)
		current = self["config"].getCurrent()
		if current:
			if current[1] in (config.misc.autocamDefault, self.autocamDefault):
				self["removeActions"].setEnabled(True)
				self["key_yellow"].setText("")
				return
			self["removeActions"].setEnabled(True)
			self["key_yellow"].setText(_("Remove"))
			newcam = current[1].value
			serviceref = current[2]
			if self.autocamData[serviceref] != newcam:
				self.autocamData[serviceref] = newcam

	def keyRemoveItem(self):
		currentItem = self["config"].getCurrentItem()
		if currentItem in (config.misc.autocamDefault, self.autocamDefault):
			return
		elif currentItem:
			currentItem.value = "None"

	def keySave(self):
		remove = [service for service, cam in self.autocamData.items() if cam == 'None']
		for service in remove:
			del self.autocamData[service]
		autocam.data = self.autocamData
		config.misc.autocamDefault.value = self.autocamDefault.value
		config.misc.autocamDefault.save()
		config.misc.autocamEnabled.save()
		self.close()

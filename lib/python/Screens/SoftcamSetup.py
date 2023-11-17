from enigma import eTimer
from os.path import isfile
from socket import socket, AF_UNIX, SOCK_STREAM

from Screens.MessageBox import MessageBox
from Components.ActionMap import HelpableActionMap
from Components.config import ConfigSelection, config
from Components.ScrollLabel import ScrollLabel
from Components.Sources.StaticText import StaticText
from Components.SystemInfo import updateSysSoftCam
from Screens.Setup import Setup
from Tools.camcontrol import CamControl
from Tools.Directories import isPluginInstalled
from Tools.GetEcmInfo import GetEcmInfo


class CamSetupCommon(Setup):
	def __init__(self, session, setup):
		self.activityTimer = eTimer()
		self.switchTimer = eTimer()
		Setup.__init__(self, session=session, setup=setup)
		self["key_yellow"] = StaticText()
		self["restartActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.restart, _("Immediately restart selected devices."))
		}, prio=0, description=_("Softcam Actions"))

	def restart(self):
		self.mbox = self.session.open(MessageBox, _("Please wait, restarting %s.") % _(self.servicetype), MessageBox.TYPE_INFO)
		self.activityTimer.timeout.get().append(self.doRestart)
		self.activityTimer.start(100, False)

	def doRestart(self):
		self.activityTimer.stop()
		self.activityTimer.timeout.get().remove(self.doRestart)
#		self.oldref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
#		self.session.nav.stopService()
		deamonSocket = socket(AF_UNIX, SOCK_STREAM)
		deamonSocket.connect("/tmp/deamon.socket")
		deamonSocket.send(f"RESTART,{self.servicetype}".encode())
		deamonSocket.close()
		self.activityTimer.timeout.get().append(self.doFinished)
		self.activityTimer.start(500, False)

	def doFinished(self):
		self.activityTimer.stop()
		self.mbox.close()
#		self.session.nav.playService(self.oldref, adjust=False)

	def switchDone(self):
		self.switchTimer.stop()
		self.saveAll()
		updateSysSoftCam()
		self.close()


class CardserverSetup(CamSetupCommon):
	def __init__(self, session):
		self.servicetype = "cardservers"
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
			deamonSocket = socket(AF_UNIX, SOCK_STREAM)
			deamonSocket.connect("/tmp/deamon.socket")
			deamonSocket.send(f"SWITCH_CARDSERVER,{config.misc.cardservers.value}".encode())
			deamonSocket.close()
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
		defaultsoftcams = [x for x in softcams if x != "None"]
		defaultautocam = config.misc.autocamDefault.value or defaultsoftcam
		self.autocamDefault = ConfigSelection(default=defaultautocam, choices=defaultsoftcams)
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
			deamonSocket = socket(AF_UNIX, SOCK_STREAM)
			deamonSocket.connect("/tmp/deamon.socket")
			deamonSocket.send(f"SWITCH_CAM,{config.misc.softcams.value}".encode())
			deamonSocket.close()
			self.switchTimer.timeout.get().append(self.switchDone)
			self.switchTimer.start(500, False)

	def updateButtons(self):
		if self["config"].getCurrent()[1] == config.misc.softcams and config.misc.softcams.value and config.misc.softcams.value.lower() != "none":
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

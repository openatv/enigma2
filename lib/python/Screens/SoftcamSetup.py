from enigma import eTimer
from os.path import isfile

from Screens.MessageBox import MessageBox
from Components.ActionMap import HelpableActionMap
from Components.config import ConfigSelection, config
from Components.ScrollLabel import ScrollLabel
from Components.Sources.StaticText import StaticText
from Components.SystemInfo import Refresh_SysSoftCam
from Screens.Setup import Setup
from Tools.camcontrol import CamControl
from Tools.Directories import isPluginInstalled
from Tools.GetEcmInfo import GetEcmInfo


class SoftcamSetup(Setup):
	def __init__(self, session):
		self.softcam = CamControl("softcam", self.commandFinished)
		self.cardserver = CamControl("cardserver", self.commandFinished)
		self.ecminfo = GetEcmInfo()
		restartOptions = [
			("", _("Don't restart")),
			("s", _("Restart softcam"))
		]
		defaultrestart = ""
		softcams = self.softcam.getList()
		defaultsoftcam = self.softcam.current()
		if len(softcams) > 1:
			defaultrestart = "s"
		else:
			softcams = [("", _("None"))]
			defaultsoftcam = ""
		config.misc.softcams = ConfigSelection(default=defaultsoftcam, choices=softcams)
		cardservers = self.cardserver.getList()
		defaultcardserver = self.cardserver.current()
		if len(cardservers) > 1:
			restartOptions.extend([("c", _("Restart cardserver")), ("sc", _("Restart both"))])
			defaultrestart += "c"
		else:
			cardservers = [("", _("None"))]
			defaultcardserver = ""
		config.misc.cardservers = ConfigSelection(default=defaultcardserver, choices=cardservers)
		config.misc.restarts = ConfigSelection(default=defaultrestart, choices=restartOptions)
		Setup.__init__(self, session=session, setup="Softcam")
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self["restartActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.restart, _("Immediately restart selected devices."))
		}, prio=0, description=_("Softcam Actions"))
		self["restartActions"].setEnabled(False)
		self["infoActions"] = HelpableActionMap(self, ["ColorActions"], {
			"blue": (self.softcamInfo, _("Display oscam information."))
		}, prio=0, description=_("Softcam Actions"))
		self["infoActions"].setEnabled(False)
		(newEcmFound, ecmInfo) = self.ecminfo.getEcm()
		self["info"] = ScrollLabel("".join(ecmInfo))
		self.EcmInfoPollTimer = eTimer()
		self.EcmInfoPollTimer.callback.append(self.setEcmInfo)
		self.EcmInfoPollTimer.start(1000)
		self.doStartCommand = False
		self.onShown.append(self.updateButtons)

	def selectionChanged(self):
		self.updateButtons()
		Setup.selectionChanged(self)

	def changedEntry(self):
		self.updateButtons()
		Setup.changedEntry(self)

	def keySave(self):
		device = ""
		if hasattr(self, "cardservers") and (config.misc.cardservers.value != self.cardserver.current()):
			device = "sc"
		elif config.misc.softcams.value != self.softcam.current():
			device = "s"
		if device:
			self.restart(device="e%s" % device)
		else:
			self.saveAll()
			Refresh_SysSoftCam()
			self.close()

	def keyCancel(self):
		Setup.keyCancel(self)

	def updateButtons(self):
		if config.misc.restarts.value:
			self["key_yellow"].setText(_("Restart"))
			self["restartActions"].setEnabled(True)
		else:
			self["key_yellow"].setText("")
			self["restartActions"].setEnabled(False)
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

	def restart(self, device=None):
		self.device = config.misc.restarts.value if device is None else device
		msg = []
		if "s" in self.device:
			msg.append(_("softcam"))
		if "c" in self.device:
			msg.append(_("cardserver"))
		msg = (" %s " % _("and")).join(msg)
		self.mbox = self.session.open(MessageBox, _("Please wait, restarting %s.") % msg, MessageBox.TYPE_INFO)
		self.activityTimer = eTimer()
		self.activityTimer.timeout.get().append(self.doStop)
		self.activityTimer.start(100, False)

	def doStop(self):
		self.activityTimer.stop()
		self.doStartCommand = True
		if "s" in self.device:
			self.softcam.command("stop")
		if "c" in self.device:
			self.cardserver.command("stop")
		self.oldref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
		self.session.nav.stopService()

	def doStart(self):
		del self.activityTimer
		if "s" in self.device:
			self.softcam.select(config.misc.softcams.value)
			self.softcam.command("start")
		if "c" in self.device:
			self.cardserver.select(config.misc.cardservers.value)
			self.cardserver.command("start")
		if self.mbox:
			self.mbox.close()
		self.session.nav.playService(self.oldref, adjust=False)

	def setEcmInfo(self):
		(newEcmFound, ecmInfo) = self.ecminfo.getEcm()
		if newEcmFound:
			self["info"].setText("".join(ecmInfo))

	def restartSoftcam(self):
		self.restart(device="s")

	def restartCardServer(self):
		if hasattr(self, "cardservers"):
			self.restart(device="c")

	def commandFinished(self):
		if self.doStartCommand:
			self.doStartCommand = False
			self.doStart()
			return
		if "e" in self.device:
			self.saveAll()
			Refresh_SysSoftCam()
			self.close()

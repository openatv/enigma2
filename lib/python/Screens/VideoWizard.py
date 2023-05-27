from Components.AVSwitch import iAVSwitch as avSwitch
from Components.config import ConfigBoolean, config, configfile
from Components.SystemInfo import BoxInfo
from Screens.HelpMenu import ShowRemoteControl
from Screens.Wizard import WizardSummary
from Screens.WizardLanguage import WizardLanguage
from Tools.Directories import SCOPE_GUISKIN, SCOPE_SKINS, resolveFilename


class VideoWizard(WizardLanguage, ShowRemoteControl):
	def __init__(self, session):
		self.xmlfile = resolveFilename(SCOPE_SKINS, "videowizard.xml")
		WizardLanguage.__init__(self, session, showSteps=False, showStepSlider=False)
		ShowRemoteControl.__init__(self)
		self.setTitle(_("Video Wizard"))
		self.avSwitch = avSwitch
		self.hasDVI = BoxInfo.getItem("dvi", False)
		self.hasJack = BoxInfo.getItem("avjack", False)
		self.hasRCA = BoxInfo.getItem("rca", False)
		self.hasSCART = BoxInfo.getItem("scart", False)
		self.portCount = 0
		self.port = None
		self.mode = None
		self.rate = None

	def listPorts(self):  # Called by wizardvideo.xml.
		ports = []
		for port in self.avSwitch.getPortList():
			if self.avSwitch.isPortUsed(port):
				descr = port
				if descr == "HDMI" and self.hasDVI:
					descr = "DVI"
				if descr == "Scart" and self.hasRCA and not self.hasSCART:
					descr = "RCA"
				if descr == "Scart" and self.hasJack and not self.hasSCART:
					descr = "Jack"
				if port != "DVI-PC":
					ports.append((descr, port))
		ports.sort(key=lambda x: x[0])
		# print("[WizardVideo] listPorts DEBUG: Ports=%s." % ports)
		return ports

	def listModes(self):  # Called by wizardvideo.xml.
		def sortKey(name):
			return {
				"2160p": 1,
				"2160p30": 2,
				"1080p": 3,
				"720p": 4,
				"1080i": 5,
				"smpte": 20
			}.get(name[0], 6)

		modes = [(mode[0], mode[0]) for mode in self.avSwitch.getModeList(self.port)]
		modes.sort(key=sortKey)
		# print("[WizardVideo] listModes DEBUG: port='%s', modes=%s." % (self.port, modes))
		return modes

	def listRates(self, mode=None):  # Called by wizardvideo.xml.
		def sortKey(name):
			return {
				"multi": 1,
				"auto": 2
			}.get(name[0], 3)

		if mode is None:
			mode = self.mode
		rates = []
		for modes in self.avSwitch.getModeList(self.port):
			if modes[0] == mode:
				for rate in modes[1]:
					if rate == "auto" and not BoxInfo.getItem("have24hz"):
						continue
					if self.port == "DVI-PC":
						# print("[WizardVideo] listModes DEBUG: rate='%s'." % rate)
						if rate == "640x480":
							rates.insert(0, (rate, rate))
							continue
					rates.append((rate, rate))
		rates.sort(key=sortKey)
		# print("[WizardVideo] listRates DEBUG: port='%s', mode='%s', rates=%s." % (self.port, mode, rates))
		return rates

	def portSelectionMade(self, index):  # Called by wizardvideo.xml.
		# print("[WizardVideo] inputSelectionMade DEBUG: index='%s'." % index)
		self.port = index
		self.portSelect(index)

	def portSelectionMoved(self):  # Called by wizardvideo.xml.
		# print("[WizardVideo] inputSelectionMoved DEBUG: self.selection='%s'." % self.selection)
		self.portSelect(self.selection)

	def portSelect(self, port):
		modeList = self.avSwitch.getModeList(self.selection)
		# print("[WizardVideo] inputSelect DEBUG: port='%s', modeList=%s." % (port, modeList))
		self.port = port
		if modeList:
			ratesList = self.listRates(modeList[0][0])
			self.avSwitch.setMode(port=port, mode=modeList[0][0], rate=ratesList[0][0])

	def modeSelectionMade(self, index):  # Called by wizardvideo.xml.
		# print("[WizardVideo] modeSelectionMade DEBUG: index='%s'." % index)
		self.mode = index
		self.modeSelect(index)

	def modeSelectionMoved(self):  # Called by wizardvideo.xml.
		# print("[WizardVideo] modeSelectionMoved DEBUG: self.selection='%s'." % self.selection)
		self.modeSelect(self.selection)

	def modeSelect(self, mode):
		rates = self.listRates(mode)
		# print("[WizardVideo] modeSelect DEBUG: rates=%s." % rates)
		if self.port == "HDMI" and mode in ("720p", "1080i", "1080p") and not BoxInfo.getItem("AmlogicFamily"):
			self.rate = "multi"
			self.avSwitch.setMode(port=self.port, mode=mode, rate="multi")
		else:
			self.avSwitch.setMode(port=self.port, mode=mode, rate=rates[0][0])

	def rateSelectionMade(self, index):  # Called by wizardvideo.xml.
		# print("[WizardVideo] rateSelectionMade DEBUG: index='%s'." % index)
		self.rate = index
		self.rateSelect(index)

	def rateSelectionMoved(self):  # Called by wizardvideo.xml.
		# print("[WizardVideo] rateSelectionMade DEBUG: self.selection='%s'." % self.selection)
		self.rateSelect(self.selection)

	def rateSelect(self, rate):
		self.avSwitch.setMode(port=self.port, mode=self.mode, rate=rate)

	def keyNumberGlobal(self, number):
		if number in (1, 2, 3):
			if number == 1:
				self.avSwitch.saveMode("HDMI", "720p", "multi")
			elif number == 2:
				self.avSwitch.saveMode("HDMI", "1080i", "multi")
			elif number == 3:
				self.avSwitch.saveMode("Scart", "Multi", "multi")
			self.avSwitch.setConfiguredMode()
			self.close()
		WizardLanguage.keyNumberGlobal(self, number)

	def saveWizardChanges(self):  # Called by wizardvideo.xml.
		self.avSwitch.saveMode(self.port, self.mode, self.rate)
		# config.misc.wizardVideoEnabled.value = 0
		# config.misc.wizardVideoEnabled.save()
		config.misc.videowizardenabled.value = 0
		config.misc.videowizardenabled.save()
		configfile.save()

	def createSummary(self):
		return WizardSummary

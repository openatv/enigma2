from Components.AVSwitch import iAVSwitch
from Components.config import config, ConfigBoolean, configfile
from Components.Pixmap import Pixmap
from Components.SystemInfo import BoxInfo
from Screens.HelpMenu import ShowRemoteControl
from Screens.Wizard import WizardSummary
from Screens.WizardLanguage import WizardLanguage
from Tools.Directories import resolveFilename, SCOPE_SKINS, SCOPE_GUISKIN


config.misc.showtestcard = ConfigBoolean(default=False)

has_scart = BoxInfo.getItem("scart", False)
has_rca = BoxInfo.getItem("rca", False)
has_jack = BoxInfo.getItem("avjack", False)
has_dvi = BoxInfo.getItem("dvi", False)


def sortkey(name):
	if name[0] == "2160p":
		return 1
	elif name[0] == "2160p30":
		return 2
	elif name[0] == "1080p":
		return 3
	elif name[0] == "720p":
		return 4
	elif name[0] == "1080i":
		return 5
	elif name[0] == "smpte":
		return 20
	elif name[0] == "multi":
		return 1
	elif name[0] == "auto":
		return 2
	else:
		return 6


class VideoWizard(WizardLanguage, ShowRemoteControl):
	skin = """
		<screen position="fill" title="Welcome..." flags="wfNoBorder" >
			<panel name="WizardMarginsTemplate"/>
			<panel name="WizardPictureLangTemplate"/>
			<panel name="RemoteControlTemplate"/>
			<panel position="left" size="10,*" />
			<panel position="right" size="10,*" />
			<panel position="fill">
				<widget name="text" position="top" size="*,270" font="Regular;23" valign="center" />
				<panel position="fill">
					<panel position="left" size="150,*">
						<widget name="portpic" position="top" zPosition="10" size="150,150" transparent="1" alphatest="on"/>
					</panel>
					<panel position="fill" layout="stack">
						<widget source="list" render="Listbox" position="fill" scrollbarMode="showOnDemand" >
							<convert type="StringList" />
						</widget>
						<!--<widget name="config" position="fill" zPosition="1" scrollbarMode="showOnDemand" />-->
					</panel>
				</panel>
			</panel>
		</screen>"""

	def __init__(self, session):
		# FIXME anyone knows how to use relative paths from the plugin's directory?
		self.xmlfile = resolveFilename(SCOPE_SKINS, "videowizard.xml")
		self.hw = iAVSwitch

		WizardLanguage.__init__(self, session, showSteps=False, showStepSlider=False)
		ShowRemoteControl.__init__(self)
		self["wizard"] = Pixmap()
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["portpic"] = Pixmap()
		self.setTitle(_("VideoWizard"))

		self.port = None
		self.mode = None
		self.rate = None

	def createSummary(self):
		return WizardSummary

	def markDone(self):
		self.hw.saveMode(self.port, self.mode, self.rate)
		config.misc.videowizardenabled.value = 0
		config.misc.videowizardenabled.save()
		configfile.save()

	def listInputChannels(self):
		ports = []

		for port in self.hw.getPortList():
			if self.hw.isPortUsed(port):
				descr = port
				if descr == 'HDMI' and has_dvi:
					descr = 'DVI'
				if descr == 'Scart' and has_rca and not has_scart:
					descr = 'RCA'
				if descr == 'Scart' and has_jack and not has_scart:
					descr = 'Jack'
				if port != "DVI-PC":
					ports.append((descr, port))
		ports.sort(key=lambda x: x[0])
		#print("listInputChannels: %s" % ports)
		return ports

	def inputSelectionMade(self, index):
		#print("inputSelectionMade: %s" % index)
		self.port = index
		self.inputSelect(index)

	def inputSelectionMoved(self):
		#print("input selection moved: %s" % self.selection)
		self.inputSelect(self.selection)
		if self["portpic"].instance is not None:
			picname = self.selection
			if picname == 'HDMI' and has_dvi:
				picname = "DVI"
			if picname == 'Scart' and has_rca:
				picname = "RCA"
			if picname == 'Scart' and has_jack:
				picname = "JACK"
			self["portpic"].instance.setPixmapFromFile(resolveFilename(SCOPE_GUISKIN, "icons/" + picname + ".png"))

	def inputSelect(self, port):
		#print("inputSelect: %s" % port)
		modeList = self.hw.getModeList(self.selection)
		#print("modeList: %s" % modeList)
		self.port = port
		if len(modeList) > 0:
			ratesList = self.listRates(modeList[0][0])
			self.hw.setMode(port=port, mode=modeList[0][0], rate=ratesList[0][0])

	def listModes(self):
		#print("modes for port %s" % self.port)
		modes = [(mode[0], mode[0]) for mode in self.hw.getModeList(self.port)]
		#print("modeslist: %s" % modes)
		return sorted(modes, key=sortkey)

	def modeSelectionMade(self, index):
		#print("modeSelectionMade: %s" % index)
		self.mode = index
		self.modeSelect(index)

	def modeSelectionMoved(self):
		#print("mode selection moved: %s" % self.selection)
		self.modeSelect(self.selection)

	def modeSelect(self, mode):
		ratesList = self.listRates(mode)
		#print("ratesList: %s" % ratesList)
		if self.port == "HDMI" and mode in ("720p", "1080i", "1080p") and not BoxInfo.getItem("AmlogicFamily"):
			self.rate = "multi"
			self.hw.setMode(port=self.port, mode=mode, rate="multi")
		else:
			self.hw.setMode(port=self.port, mode=mode, rate=ratesList[0][0])

	def listRates(self, querymode=None):
		if querymode is None:
			querymode = self.mode
		modes = []
		#print("modes for port %s and mode %s" % (self.port, querymode))
		for mode in self.hw.getModeList(self.port):
			print(mode)
			if mode[0] == querymode:
				for rate in mode[1]:
					if rate in ("auto") and not BoxInfo.getItem("have24hz"):
						continue
					if self.port == "DVI-PC":
						#print("rate: %s" % rate)
						if rate == "640x480":
							modes.insert(0, (rate, rate))
							continue
					modes.append((rate, rate))
		return sorted(modes, key=sortkey)

	def rateSelectionMade(self, index):
		#print("rateSelectionMade: %s" % index)
		self.rate = index
		self.rateSelect(index)

	def rateSelectionMoved(self):
		#print("rate selection moved: %s" % self.selection)
		self.rateSelect(self.selection)

	def rateSelect(self, rate):
		self.hw.setMode(port=self.port, mode=self.mode, rate=rate)

	def showTestCard(self, selection=None):
		if selection is None:
			selection = self.selection
		#print("set config.misc.showtestcard to %s " % {'yes': True, 'no': False}[selection])
		config.misc.showtestcard.value = selection == "yes"

	def keyNumberGlobal(self, number):
		if number in (1, 2, 3):
			if number == 1:
				self.hw.saveMode("HDMI", "720p", "multi")
			elif number == 2:
				self.hw.saveMode("HDMI", "1080i", "multi")
			elif number == 3:
				self.hw.saveMode("Scart", "Multi", "multi")
			self.hw.setConfiguredMode()
			self.close()

		WizardLanguage.keyNumberGlobal(self, number)

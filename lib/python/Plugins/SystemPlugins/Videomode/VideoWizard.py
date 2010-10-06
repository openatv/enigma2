from Screens.Wizard import WizardSummary
from Screens.WizardLanguage import WizardLanguage
from Screens.Rc import Rc
from VideoHardware import video_hw

from Components.Pixmap import Pixmap, MovingPixmap, MultiPixmap
from Components.config import config, ConfigBoolean, configfile

from Tools.Directories import resolveFilename, SCOPE_PLUGINS
from Tools.HardwareInfo import HardwareInfo

config.misc.showtestcard = ConfigBoolean(default = False)

class VideoWizardSummary(WizardSummary):
	skin = (
	"""<screen name="VideoWizardSummary" position="0,0" size="132,64" id="1">
		<widget name="text" position="6,4" size="120,40" font="Regular;12" transparent="1" />
		<widget source="parent.list" render="Label" position="6,40" size="120,21" font="Regular;14">
			<convert type="StringListSelection" />
		</widget>
		<!--widget name="pic" pixmap="%s" position="6,22" zPosition="10" size="64,64" transparent="1" alphatest="on"/-->
	</screen>""",
	"""<screen name="VideoWizardSummary" position="0,0" size="96,64" id="2">
		<widget name="text" position="0,4" size="96,40" font="Regular;12" transparent="1" />
		<widget source="parent.list" render="Label" position="0,40" size="96,21" font="Regular;14">
			<convert type="StringListSelection" />
		</widget>
		<!--widget name="pic" pixmap="%s" position="0,22" zPosition="10" size="64,64" transparent="1" alphatest="on"/-->
	</screen>""")
	#% (resolveFilename(SCOPE_PLUGINS, "SystemPlugins/Videomode/lcd_Scart.png"))
	
	def __init__(self, session, parent):
		WizardSummary.__init__(self, session, parent)
		#self["pic"] = Pixmap()
		
	def setLCDPicCallback(self):
		self.parent.setLCDTextCallback(self.setText)
		
	def setLCDPic(self, file):
		self["pic"].instance.setPixmapFromFile(file)

class VideoWizard(WizardLanguage, Rc):
	skin = """
		<screen position="0,0" size="720,576" title="Welcome..." flags="wfNoBorder" >
			<widget name="text" position="153,50" size="340,270" font="Regular;23" />
			<widget source="list" render="Listbox" position="200,300" size="290,200" scrollbarMode="showOnDemand" >
				<convert type="StringList" />
			</widget>
			<widget name="config" position="50,300" zPosition="1" size="440,200" transparent="1" scrollbarMode="showOnDemand" />
			<widget name="wizard" pixmap="skin_default/wizard.png" position="40,50" zPosition="10" size="110,174" transparent="1" alphatest="on"/>
			<ePixmap pixmap="skin_default/buttons/button_red.png" position="40,225" zPosition="0" size="15,16" transparent="1" alphatest="on" />
			<widget name="languagetext" position="55,225" size="95,30" font="Regular;18" />
			<widget name="portpic" pixmap="%s" position="50,300" zPosition="10" size="150,150" transparent="1" alphatest="on"/>
			<widget name="rc" pixmaps="skin_default/rc.png,skin_default/rcold.png" position="500,50" zPosition="10" size="154,500" transparent="1" alphatest="on"/>
			<widget name="arrowdown" pixmap="skin_default/arrowdown.png" position="0,0" zPosition="11" size="37,70" transparent="1" alphatest="on"/>
			<widget name="arrowdown2" pixmap="skin_default/arrowdown.png" position="0,0" zPosition="11" size="37,70" transparent="1" alphatest="on"/>
			<widget name="arrowup" pixmap="skin_default/arrowup.png" position="-100,-100" zPosition="11" size="37,70" transparent="1" alphatest="on"/>
			<widget name="arrowup2" pixmap="skin_default/arrowup.png" position="-100,-100" zPosition="11" size="37,70" transparent="1" alphatest="on"/>
		</screen>""" % (resolveFilename(SCOPE_PLUGINS, "SystemPlugins/Videomode/Scart.png"))
	
	def __init__(self, session):
		# FIXME anyone knows how to use relative paths from the plugin's directory?
		self.xmlfile = resolveFilename(SCOPE_PLUGINS, "SystemPlugins/Videomode/videowizard.xml")
		self.hw = video_hw
		
		WizardLanguage.__init__(self, session, showSteps = False, showStepSlider = False)
		Rc.__init__(self)
		self["wizard"] = Pixmap()
		self["portpic"] = Pixmap()
		
		self.port = None
		self.mode = None
		self.rate = None
		
		
	def createSummary(self):
		print "++++++++++++***++**** VideoWizard-createSummary"
		from Screens.Wizard import WizardSummary
		return VideoWizardSummary
		
	def markDone(self):
		config.misc.videowizardenabled.value = 0
		config.misc.videowizardenabled.save()
		configfile.save()
	
	def listInputChannels(self):
		hw_type = HardwareInfo().get_device_name()
		list = []

		for port in self.hw.getPortList():
			if self.hw.isPortUsed(port):
				descr = port
				if descr == 'DVI' and hw_type in ('dm500hd', 'dm800se'):
					descr = 'HDMI'
				if port != "DVI-PC":
					list.append((descr,port))
		list.sort(key = lambda x: x[0])
		print "listInputChannels:", list
		return list

	def inputSelectionMade(self, index):
		print "inputSelectionMade:", index
		self.port = index
		self.inputSelect(index)
		
	def inputSelectionMoved(self):
		print "input selection moved:", self.selection
		self.inputSelect(self.selection)
		if self["portpic"].instance is not None:
			picname = self.selection
			if picname == "DVI" and HardwareInfo().get_device_name() in ("dm500hd", "dm800se"):
				picname = "HDMI"
			self["portpic"].instance.setPixmapFromFile(resolveFilename(SCOPE_PLUGINS, "SystemPlugins/Videomode/" + picname + ".png"))
		
	def inputSelect(self, port):
		print "inputSelect:", port
		modeList = self.hw.getModeList(self.selection)
		print "modeList:", modeList
		self.port = port
		if (len(modeList) > 0):
			ratesList = self.listRates(modeList[0][0])
			self.hw.setMode(port = port, mode = modeList[0][0], rate = ratesList[0][0])
		
	def listModes(self):
		list = []
		print "modes for port", self.port
		for mode in self.hw.getModeList(self.port):
			#if mode[0] != "PC":
				list.append((mode[0], mode[0]))
		print "modeslist:", list
		return list
	
	def modeSelectionMade(self, index):
		print "modeSelectionMade:", index
		self.mode = index
		self.modeSelect(index)
		
	def modeSelectionMoved(self):
		print "mode selection moved:", self.selection
		self.modeSelect(self.selection)
		
	def modeSelect(self, mode):
		ratesList = self.listRates(mode)
		print "ratesList:", ratesList
		if self.port == "DVI" and mode in ("720p", "1080i"):
			self.rate = "multi"
			self.hw.setMode(port = self.port, mode = mode, rate = "multi")
		else:
			self.hw.setMode(port = self.port, mode = mode, rate = ratesList[0][0])
	
	def listRates(self, querymode = None):
		if querymode is None:
			querymode = self.mode
		list = []
		print "modes for port", self.port, "and mode", querymode
		for mode in self.hw.getModeList(self.port):
			print mode
			if mode[0] == querymode:
				for rate in mode[1]:
					if self.port == "DVI-PC":
						print "rate:", rate
						if rate == "640x480":
							list.insert(0, (rate, rate))
							continue
					list.append((rate, rate))
		return list
	
	def rateSelectionMade(self, index):
		print "rateSelectionMade:", index
		self.rate = index
		self.rateSelect(index)
		
	def rateSelectionMoved(self):
		print "rate selection moved:", self.selection
		self.rateSelect(self.selection)

	def rateSelect(self, rate):
		self.hw.setMode(port = self.port, mode = self.mode, rate = rate)

	def showTestCard(self, selection = None):
		if selection is None:
			selection = self.selection
		print "set config.misc.showtestcard to", {'yes': True, 'no': False}[selection]
		if selection == "yes":
			config.misc.showtestcard.value = True
		else:
			config.misc.showtestcard.value = False

	def keyNumberGlobal(self, number):
		if number in (1,2,3):
			if number == 1:
				self.hw.saveMode("DVI", "720p", "multi")
			elif number == 2:
				self.hw.saveMode("DVI", "1080i", "multi")
			elif number == 3:
				self.hw.saveMode("Scart", "Multi", "multi")
			self.hw.setConfiguredMode()
			self.close()

		WizardLanguage.keyNumberGlobal(self, number)

from boxbranding import getBoxType, getMachineName
from Screens.Wizard import WizardSummary
from Screens.WizardLanguage import WizardLanguage
from Screens.Rc import Rc
from Components.AVSwitch import iAVSwitch
from Screens.Screen import Screen

from Components.Pixmap import Pixmap
from Components.config import config, ConfigBoolean, configfile

from Tools.Directories import resolveFilename, SCOPE_SKIN, SCOPE_ACTIVE_SKIN
from Tools.HardwareInfo import HardwareInfo

config.misc.showtestcard = ConfigBoolean(default = False)

boxtype = getBoxType()

has_rca = False
has_dvi = False
if boxtype in ('sf3038', 'nano', 'nanoc', 'tomcat', 'zgemmash1', 'zgemmash2', 'zgemmas2s', 'zgemmass' , 'formuler3', 'enibox', 'mago', 'sf108', 'x1plus', 'x2plus', 'atemio6000', 'atemio6100', 'atemio6200', 'mbminiplus', 'vp7358ci', 'xcombo', 'gbquad', 'gbquadplus', 'et5x00', 'et6000', 'et7000', 'et7500', 'et8500', 'classm', 'axodin', 'axodinc', 'genius', 'evo', 'galaxym6', 'geniuse3hd', 'evoe3hd', 'axase3', 'axase3c', 'starsatlx', 'mixosf7', 'mixoslumi', 'tmnano', 'azboxme',  'azboxminime', 'optimussos1',  'optimussos2', 'gb800seplus', 'gb800ueplus', 'gbultrase', 'gbultraue', 'sezam1000hd', 'ixussone', 'ixusszero', 'enfinity', 'marvel1', 'bre2ze', 'force1', 'force1plus', 'worldvisionf1', 'optimussos1plus',  'optimussos2plus',  'optimussos3plus', 'formuler1', 'tmnano2super', 'vusolose', 'vuzero', 'tyrant'):
	has_rca = True
if boxtype == 'dm8000' or boxtype == 'dm800':
	has_dvi = True

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
		self.xmlfile = resolveFilename(SCOPE_SKIN, "videowizard.xml")
		self.hw = iAVSwitch

		WizardLanguage.__init__(self, session, showSteps = False, showStepSlider = False)
		Rc.__init__(self)
		self["wizard"] = Pixmap()
		self["portpic"] = Pixmap()
		Screen.setTitle(self, _("Welcome..."))

		self.port = None
		self.mode = None
		self.rate = None

	def createSummary(self):
		return VideoWizardSummary

	def markDone(self):
		self.hw.saveMode(self.port, self.mode, self.rate)
		config.misc.videowizardenabled.value = 0
		config.misc.videowizardenabled.save()
		configfile.save()

	def listInputChannels(self):
		hw_type = HardwareInfo().get_device_name()
		has_hdmi = HardwareInfo().has_hdmi()
		list = []

		for port in self.hw.getPortList():
			if self.hw.isPortUsed(port):
				descr = port
				if descr == 'HDMI' and has_dvi:
					descr = 'DVI'
				if descr == 'Scart' and has_rca:
					descr = 'RCA'					
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
		hw_type = HardwareInfo().get_device_name()
		has_hdmi = HardwareInfo().has_hdmi()
		print "input selection moved:", self.selection
		self.inputSelect(self.selection)
		if self["portpic"].instance is not None:
			picname = self.selection
			if picname == 'HDMI' and has_dvi:
				picname = "DVI"
			if picname == 'Scart' and has_rca:
				picname = "RCA"	
			self["portpic"].instance.setPixmapFromFile(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/" + picname + ".png"))

	def inputSelect(self, port):
		print "inputSelect:", port
		modeList = self.hw.getModeList(self.selection)
		print "modeList:", modeList
		self.port = port
		if len(modeList) > 0:
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
		if self.port == "HDMI" and mode in ("720p", "1080i", "1080p"):
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
				self.hw.saveMode("HDMI", "720p", "multi")
			elif number == 2:
				self.hw.saveMode("HDMI", "1080i", "multi")
			elif number == 3:
				self.hw.saveMode("Scart", "Multi", "multi")
			self.hw.setConfiguredMode()
			self.close()

		WizardLanguage.keyNumberGlobal(self, number)

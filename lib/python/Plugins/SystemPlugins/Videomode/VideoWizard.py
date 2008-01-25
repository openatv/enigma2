from Screens.Wizard import Wizard, wizardManager
import sys
from VideoHardware import video_hw

from Components.Pixmap import Pixmap, MovingPixmap
from Components.config import config, ConfigBoolean, configfile

class VideoWizard(Wizard):
	skin = """
		<screen position="0,0" size="720,576" title="Welcome..." flags="wfNoBorder" >
			<widget name="text" position="153,50" size="340,270" font="Regular;23" />
			<widget source="list" render="Listbox" position="50,300" size="440,200" scrollbarMode="showOnDemand" >
				<convert type="StringList" />
			</widget>
			<widget name="config" position="50,300" zPosition="1" size="440,200" transparent="1" scrollbarMode="showOnDemand" />			
			<widget name="stepslider" position="50,500" zPosition="1" borderWidth="2" size="440,20" backgroundColor="dark" />
			<widget name="wizard" pixmap="wizard.png" position="40,50" zPosition="10" size="110,174" transparent="1" alphatest="on"/>
			<widget name="rc" pixmap="rc.png" position="500,600" zPosition="10" size="154,475" transparent="1" alphatest="on"/>
			<widget name="arrowdown" pixmap="arrowdown.png" position="0,0" zPosition="11" size="37,70" transparent="1" alphatest="on"/>
			<widget name="arrowup" pixmap="arrowup.png" position="-100,-100" zPosition="11" size="37,70" transparent="1" alphatest="on"/>
			<widget name="arrowup2" pixmap="arrowup.png" position="-100,-100" zPosition="11" size="37,70" transparent="1" alphatest="on"/>
		</screen>"""
	
	def __init__(self, session):
		# FIXME anyone knows how to use relative paths from the plugin's directory?
		self.xmlfile = sys.path[0] + "/Plugins/SystemPlugins/Videomode/videowizard.xml"
		self.hw = video_hw
		
		Wizard.__init__(self, session, showSteps = False)
		self["wizard"] = Pixmap()
		self["rc"] = MovingPixmap()
		self["arrowdown"] = MovingPixmap()
		self["arrowup"] = MovingPixmap()
		self["arrowup2"] = MovingPixmap()
		
		self.port = None
		self.mode = None
		
	def createSummary(self):
		print "++++++++++++***++**** VideoWizard-createSummary"
		from Screens.Wizard import WizardSummary
		return WizardSummary
		
	def markDone(self):
		pass
	
	def listInputChannels(self):
		list = []

		for port in self.hw.getPortList():
			if self.hw.isPortUsed(port):
				list.append((port, port))
		return list

	def inputSelectionMade(self, index):
		print "inputSelectionMade:", index
		self.port = index
		
	def inputSelectionMoved(self):
		print "selection moved:", self.selection
		
	def listModes(self):
		list = []
		print "modes for port", self.port
		for mode in self.hw.getModeList(self.port):
			list.append((mode[0], mode[0]))
		return list
	
	def modeSelectionMade(self, index):
		print "modeSelectionMade:", index
		self.mode = index
		
	def modeSelectionMoved(self):
		print "selection moved:", self.selection
		
	def listRates(self):
		list = []
		print "modes for port", self.port
		for mode in self.hw.getModeList(self.port):
			print mode
			if mode[0] == self.mode:
				for rate in mode[1]:
					list.append((rate, rate))
		return list
	
	def rateSelectionMade(self, index):
		print "rateSelectionMade:", index
		
	def rateSelectionMoved(self):
		print "selection moved:", self.selection

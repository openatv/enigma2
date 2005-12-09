from Screen import Screen

from Screens.HelpMenu import HelpableScreen
from Components.Label import Label
from Components.Slider import Slider
from Components.ActionMap import HelpableActionMap
from Components.config import config, configElementBoolean
from Components.Pixmap import *
from Components.MenuList import MenuList
from Components.ConfigList import ConfigList
from Screens.ScanSetup import ScanSimple

from xml.sax import make_parser
from xml.sax.handler import ContentHandler

config.misc.firstrun = configElementBoolean("config.misc.firstrun", 1);

class WelcomeWizard(Screen, HelpableScreen):

	skin = """
		<screen position="0,0" size="720,560" title="Welcome..." flags="wfNoBorder" >
			<widget name="text" position="50,100" size="440,200" font="Arial;23" />
			<widget name="list" position="50,300" size="440,200" />
			<widget name="config" position="50,300" zPosition="100" size="440,200" />			
			<widget name="step" position="50,50" size="440,25" font="Arial;23" />
			<widget name="stepslider" position="50,500" zPosition="1" size="440,20" backgroundColor="dark" />
			<widget name="rc" pixmap="/usr/share/enigma2/rc.png" position="500,600" size="154,475" transparent="1" alphatest="on"/>
			<widget name="arrowdown" pixmap="/usr/share/enigma2/arrowdown.png" position="0,0" zPosition="1" size="37,70" transparent="1" alphatest="on"/>
			<widget name="arrowup" pixmap="/usr/share/enigma2/arrowup.png" position="-100,-100" zPosition="1" size="37,70" transparent="1" alphatest="on"/>
		</screen>"""

	class parseWizard(ContentHandler):
		def __init__(self, wizard):
			self.isPointsElement, self.isReboundsElement = 0, 0
			self.wizard = wizard
			self.currContent = ""
		
		def startElement(self, name, attrs):
			self.currContent = name
			if (name == "step"):
				self.lastStep = int(attrs.get('number'))
				self.wizard[self.lastStep] = {"text": "", "list": [], "config": None, "code": ""}
			elif (name == "text"):
				self.wizard[self.lastStep]["text"] = str(attrs.get('value'))
			elif (name == "listentry"):
				self.wizard[self.lastStep]["list"].append(str(attrs.get('caption')))
			elif (name == "config"):
				exec "from Screens." + str(attrs.get('module')) + " import *"
				self.wizard[self.lastStep]["config"] = eval(str(attrs.get('screen')))
				
		def endElement(self, name):
			self.currContent = ""
			if name == 'code':
				self.wizard[self.lastStep]["code"] = self.wizard[self.lastStep]["code"].strip()
				
		def characters(self, ch):
			if self.currContent == "code":
				 self.wizard[self.lastStep]["code"] = self.wizard[self.lastStep]["code"] + ch
				
	def __init__(self, session):
		self.skin = WelcomeWizard.skin

		Screen.__init__(self, session)
		HelpableScreen.__init__(self)

		self.wizard = {}
		print self.wizard
		parser = make_parser()
		print "Reading startwizard.xml"
		wizardHandler = self.parseWizard(self.wizard)
		parser.setContentHandler(wizardHandler)
		parser.parse('/usr/share/enigma2/startwizard.xml')
		
		print self.wizard
		
		self.numSteps = 4
		self.currStep = 1

		self["text"] = Label()
		self["rc"] = MovingPixmap()
		self["arrowdown"] = MovingPixmap()
		self["arrowdown"].moveTo(557, 232, 10)
		self["arrowup"] = MovingPixmap()
		self["rc"].moveTo(500, 50, 10)
		self["config"] = ConfigList([])
		
		self.onShown.append(self["arrowdown"].startMoving)
		self.onShown.append(self["rc"].startMoving)

		self["step"] = Label()
				
		self["stepslider"] = Slider(1, self.numSteps)
		
		#self.scanSetupDialog = self.session.instantiateDialog(ScanSimple)
		
		self.list = []
		#list.append(("Use wizard to set up basic features", None))
		#list.append(("Exit wizard", None))
		self["list"] = MenuList(self.list)

		self.updateValues()
		
		self["actions"] = HelpableActionMap(self, "OkCancelActions",
			{
				"ok": (self.ok, _("Close this Screen...")),
			})

	def updateValues(self):
		self["step"].setText(_("Step ") + str(self.currStep) + "/" + str(self.numSteps))
		self["stepslider"].setValue(self.currStep)

		self["text"].setText(self.wizard[self.currStep]["text"])
		
		self.list = []
		if (len(self.wizard[self.currStep]["list"]) > 0):
			for x in self.wizard[self.currStep]["list"]:
				self.list.append((x, None))
		self["list"].l.setList(self.list)
		
		if (self.wizard[self.currStep]["config"] != None):
			self.configInstance = self.session.instantiateDialog(self.wizard[self.currStep]["config"])
			self["config"].l.setList(self.configInstance["config"].list)
		else:
			self["config"].l.setList([])

		if self.wizard[self.currStep]["code"] != "":
			print self.wizard[self.currStep]["code"]
			exec(self.wizard[self.currStep]["code"])
			
	def ok(self):
		if (self.currStep == self.numSteps): # wizard finished
			config.misc.firstrun.value = 0;
			config.misc.firstrun.save()
			self.session.close()
		else:
			self.currStep += 1
			self.updateValues()

def listActiveWizards():
	wizards = [ ]

	if config.misc.firstrun.value:
		wizards.append(WelcomeWizard)
	
	return wizards

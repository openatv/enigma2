from Screen import Screen

from Screens.HelpMenu import HelpableScreen
from Components.Label import Label
from Components.Slider import Slider
from Components.ActionMap import HelpableActionMap, NumberActionMap
from Components.config import config, configElementBoolean
from Components.Pixmap import *
from Components.MenuList import MenuList
from Components.ConfigList import ConfigList

from xml.sax import make_parser
from xml.sax.handler import ContentHandler

config.misc.firstrun = configElementBoolean("config.misc.firstrun", 1);

class WelcomeWizard(Screen, HelpableScreen):

	skin = """
		<screen position="0,0" size="720,560" title="Welcome..." flags="wfNoBorder" >
			<widget name="text" position="50,100" size="440,200" font="Arial;23" />
			<widget name="list" position="50,300" zPosition="1" size="440,200" />
			<widget name="config" position="50,300" zPosition="1" size="440,200" transparent="1" />			
			<widget name="step" position="50,50" size="440,25" font="Arial;23" />
			<widget name="stepslider" position="50,500" zPosition="1" size="440,20" backgroundColor="dark" />
			<widget name="rc" pixmap="/usr/share/enigma2/rc.png" position="500,600" zPosition="10" size="154,475" transparent="1" alphatest="on"/>
			<widget name="arrowdown" pixmap="/usr/share/enigma2/arrowdown.png" position="0,0" zPosition="11" size="37,70" transparent="1" alphatest="on"/>
			<widget name="arrowup" pixmap="/usr/share/enigma2/arrowup.png" position="-100,-100" zPosition="11" size="37,70" transparent="1" alphatest="on"/>
		</screen>"""

	class parseWizard(ContentHandler):
		def __init__(self, wizard):
			self.isPointsElement, self.isReboundsElement = 0, 0
			self.wizard = wizard
			self.currContent = ""
		
		def startElement(self, name, attrs):
			print name
			self.currContent = name
			if (name == "step"):
				self.lastStep = int(attrs.get('number'))
				self.wizard[self.lastStep] = {"text": "", "list": [], "config": {"screen": None, "args": None }, "code": ""}
			elif (name == "text"):
				self.wizard[self.lastStep]["text"] = str(attrs.get('value'))
			elif (name == "listentry"):
				self.wizard[self.lastStep]["list"].append((str(attrs.get('caption')), str(attrs.get('step'))))
			elif (name == "config"):
				exec "from Screens." + str(attrs.get('module')) + " import *"
				self.wizard[self.lastStep]["config"]["screen"] = eval(str(attrs.get('screen')))
				if (attrs.has_key('args')):
					print "has args"
					self.wizard[self.lastStep]["config"]["args"] = str(attrs.get('args'))
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
		parser = make_parser()
		print "Reading startwizard.xml"
		wizardHandler = self.parseWizard(self.wizard)
		parser.setContentHandler(wizardHandler)
		parser.parse('/usr/share/enigma2/startwizard.xml')
		
		self.numSteps = len(self.wizard)
		self.currStep = 1

		self["text"] = Label()
		self["rc"] = MovingPixmap()
		self["arrowdown"] = MovingPixmap()
		self["arrowup"] = MovingPixmap()

		self["config"] = ConfigList([])

		self["step"] = Label()
				
		self["stepslider"] = Slider(1, self.numSteps)
		
		self.list = []
		self["list"] = MenuList(self.list)

		self.onShown.append(self.updateValues)
		
		self["actions"] = NumberActionMap(["WizardActions", "NumberActions"],
		{
			"ok": self.ok,
			#"cancel": self.keyCancel,
			"left": self.left,
			"right": self.right,
			"up": self.up,
			"down": self.down,
			"1": self.keyNumberGlobal,
			"2": self.keyNumberGlobal,
			"3": self.keyNumberGlobal,
			"4": self.keyNumberGlobal,
			"5": self.keyNumberGlobal,
			"6": self.keyNumberGlobal,
			"7": self.keyNumberGlobal,
			"8": self.keyNumberGlobal,
			"9": self.keyNumberGlobal,
			"0": self.keyNumberGlobal
		}, -1)
		
		#self["actions"] = HelpableActionMap(self, "OkCancelActions",
			#{
				#"ok": (self.ok, _("Close this Screen...")),
			#})

	def ok(self):
		if (self.wizard[self.currStep]["config"]["screen"] != None):
			self.configInstance.run()
		
		if (len(self.wizard[self.currStep]["list"]) > 0):
			nextStep = self.wizard[self.currStep]["list"][self["list"].l.getCurrentSelectionIndex()][1]
			if nextStep == "end":
				self.currStep = self.numSteps
			elif nextStep == "next":
				pass
			else:
				self.currStep = int(nextStep) - 1

		if (self.currStep == self.numSteps): # wizard finished
			config.misc.firstrun.value = 0;
			config.misc.firstrun.save()
			self.session.close()
		else:
			self.currStep += 1
			self.updateValues()

	def keyNumberGlobal(self, number):
		if (self.wizard[self.currStep]["config"]["screen"] != None):
			self.configInstance.keyNumberGlobal(number)
		
	def left(self):
		if (self.wizard[self.currStep]["config"]["screen"] != None):
			self.configInstance.keyLeft()
		print "left"
	
	def right(self):
		if (self.wizard[self.currStep]["config"]["screen"] != None):
			self.configInstance.keyRight()
		print "right"

	def up(self):
		if (self.wizard[self.currStep]["config"]["screen"] != None):
			self["config"].instance.moveSelection(self["config"].instance.moveUp)
		elif (len(self.wizard[self.currStep]["list"]) > 0):
			self["list"].instance.moveSelection(self["config"].instance.moveUp)
		print "up"
		
	def down(self):
		if (self.wizard[self.currStep]["config"]["screen"] != None):
			self["config"].instance.moveSelection(self["config"].instance.moveDown)
		elif (len(self.wizard[self.currStep]["list"]) > 0):
			self["list"].instance.moveSelection(self["config"].instance.moveDown)
		print "down"
		
	def updateValues(self):
		self["step"].setText(_("Step ") + str(self.currStep) + "/" + str(self.numSteps))
		self["stepslider"].setValue(self.currStep)

		self["text"].setText(self.wizard[self.currStep]["text"])
		
		self["list"].instance.setZPosition(1)
		self.list = []
		if (len(self.wizard[self.currStep]["list"]) > 0):
			self["list"].instance.setZPosition(2)
			for x in self.wizard[self.currStep]["list"]:
				self.list.append((x[0], None))
		self["list"].l.setList(self.list)

		self["config"].instance.setZPosition(1)
		if (self.wizard[self.currStep]["config"]["screen"] != None):
			self["config"].instance.setZPosition(2)
			print self.wizard[self.currStep]["config"]["screen"]
			if self.wizard[self.currStep]["config"]["args"] == None:
				self.configInstance = self.session.instantiateDialog(self.wizard[self.currStep]["config"]["screen"])
			else:
				self.configInstance = self.session.instantiateDialog(self.wizard[self.currStep]["config"]["screen"], eval(self.wizard[self.currStep]["config"]["args"]))
			self["config"].l.setList(self.configInstance["config"].list)
			self.configInstance["config"] = self["config"]
		else:
			self["config"].l.setList([])

		if self.wizard[self.currStep]["code"] != "":
			print self.wizard[self.currStep]["code"]
			exec(self.wizard[self.currStep]["code"])

def listActiveWizards():
	wizards = [ ]

	if config.misc.firstrun.value:
		wizards.append(WelcomeWizard)
	
	return wizards

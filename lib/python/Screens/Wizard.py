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

class Wizard(Screen, HelpableScreen):

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
				self.wizard[self.lastStep] = {"text": "", "list": [], "config": {"screen": None, "args": None, "type": "" }, "code": ""}
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
				self.wizard[self.lastStep]["config"]["type"] = str(attrs.get('type'))
		def endElement(self, name):
			self.currContent = ""
			if name == 'code':
				self.wizard[self.lastStep]["code"] = self.wizard[self.lastStep]["code"].strip()
				
		def characters(self, ch):
			if self.currContent == "code":
				 self.wizard[self.lastStep]["code"] = self.wizard[self.lastStep]["code"] + ch
				
	def __init__(self, session):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)

		self.wizard = {}
		parser = make_parser()
		print "Reading " + self.xmlfile
		wizardHandler = self.parseWizard(self.wizard)
		parser.setContentHandler(wizardHandler)
		parser.parse('/usr/share/enigma2/' + self.xmlfile)
		
		self.numSteps = len(self.wizard)
		self.currStep = 1

		self["text"] = Label()

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
		print "OK"
		if (self.wizard[self.currStep]["config"]["screen"] != None):
			try: # don't die, if no run() is available
				self.configInstance.run()
			except:
				print "Failed to run configInstance"
		
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
			
		print "Now: " + str(self.currStep)

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
		print "Updating values in step " + str(self.currStep)
		self["step"].setText(_("Step ") + str(self.currStep) + "/" + str(self.numSteps))
		self["stepslider"].setValue(self.currStep)

		self["text"].setText(self.wizard[self.currStep]["text"])

		if self.wizard[self.currStep]["code"] != "":
			print self.wizard[self.currStep]["code"]
			exec(self.wizard[self.currStep]["code"])
		
		self["list"].instance.setZPosition(1)
		self.list = []
		if (len(self.wizard[self.currStep]["list"]) > 0):
			self["list"].instance.setZPosition(2)
			for x in self.wizard[self.currStep]["list"]:
				self.list.append((x[0], None))
		self["list"].l.setList(self.list)

		self["config"].instance.setZPosition(1)
		if (self.wizard[self.currStep]["config"]["screen"] != None):
			if self.wizard[self.currStep]["config"]["type"] == "standalone":
				print "Type is standalone"
				self.session.openWithCallback(self.ok, self.wizard[self.currStep]["config"]["screen"])
			else:
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

class WizardManager:
	def __init__(self):
		self.wizards = []
	
	def registerWizard(self, wizard):
		self.wizards.append(wizard)
	
	def getWizards(self):
		if config.misc.firstrun.value:
			return self.wizards
		else:
			return []

wizardManager = WizardManager()

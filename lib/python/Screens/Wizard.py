from Screen import Screen

import string

from Screens.HelpMenu import HelpableScreen
from Components.Label import Label
from Components.Slider import Slider
from Components.ActionMap import HelpableActionMap, NumberActionMap
from Components.Pixmap import *
from Components.MenuList import MenuList
from Components.ConfigList import ConfigList

from xml.sax import make_parser
from xml.sax.handler import ContentHandler

class Wizard(Screen, HelpableScreen):

	class parseWizard(ContentHandler):
		def __init__(self, wizard):
			self.isPointsElement, self.isReboundsElement = 0, 0
			self.wizard = wizard
			self.currContent = ""
			self.lastStep = 0
		
		def startElement(self, name, attrs):
			print "startElement", name
			self.currContent = name
			if (name == "step"):
				self.lastStep += 1
				if attrs.has_key('id'):
					id = str(attrs.get('id'))
				else:
					id = ""
				if attrs.has_key('nextstep'):
					nextstep = str(attrs.get('nextstep'))
				else:
					nextstep = None
				self.wizard[self.lastStep] = {"id": id, "condition": "", "text": "", "list": [], "config": {"screen": None, "args": None, "type": "" }, "code": "", "codeafter": "", "nextstep": nextstep}
			elif (name == "text"):
				self.wizard[self.lastStep]["text"] = string.replace(str(attrs.get('value')), "\\n", "\n")
			elif (name == "listentry"):
				self.wizard[self.lastStep]["list"].append((str(attrs.get('caption')), str(attrs.get('step'))))
			elif (name == "config"):
				exec "from Screens." + str(attrs.get('module')) + " import *"
				self.wizard[self.lastStep]["config"]["screen"] = eval(str(attrs.get('screen')))
				if (attrs.has_key('args')):
					print "has args"
					self.wizard[self.lastStep]["config"]["args"] = str(attrs.get('args'))
				self.wizard[self.lastStep]["config"]["type"] = str(attrs.get('type'))
			elif (name == "code"):
				if attrs.has_key('pos') and str(attrs.get('pos')) == "after":
					self.codeafter = True
				else:
					self.codeafter = False
			elif (name == "condition"):
				pass
		def endElement(self, name):
			self.currContent = ""
			if name == 'code':
				if self.codeafter:
					self.wizard[self.lastStep]["codeafter"] = self.wizard[self.lastStep]["codeafter"].strip()
				else:
					self.wizard[self.lastStep]["code"] = self.wizard[self.lastStep]["code"].strip()
			elif name == 'condition':
				self.wizard[self.lastStep]["condition"] = self.wizard[self.lastStep]["condition"].strip()
								
		def characters(self, ch):
			if self.currContent == "code":
				if self.codeafter:
					self.wizard[self.lastStep]["codeafter"] = self.wizard[self.lastStep]["codeafter"] + ch
				else:
					self.wizard[self.lastStep]["code"] = self.wizard[self.lastStep]["code"] + ch
			elif self.currContent == "condition":
				 self.wizard[self.lastStep]["condition"] = self.wizard[self.lastStep]["condition"] + ch

	def __init__(self, session, showSteps = True, showStepSlider = True, showList = True, showConfig = True):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)

		self.stepHistory = []

		self.wizard = {}
		parser = make_parser()
		print "Reading " + self.xmlfile
		wizardHandler = self.parseWizard(self.wizard)
		parser.setContentHandler(wizardHandler)
		parser.parse('/usr/share/enigma2/' + self.xmlfile)

		self.showSteps = showSteps
		self.showStepSlider = showStepSlider
		self.showList = showList
		self.showConfig = showConfig

		self.numSteps = len(self.wizard)
		self.currStep = 1

		self["text"] = Label()

		if showConfig:
			self["config"] = ConfigList([])

		if self.showSteps:
			self["step"] = Label()
		
		if self.showStepSlider:
			self["stepslider"] = Slider(1, self.numSteps)
		
		if self.showList:
			self.list = []
			self["list"] = MenuList(self.list)

		self.onShown.append(self.updateValues)

		self.configInstance = None
		
		self["actions"] = NumberActionMap(["WizardActions", "NumberActions"],
		{
			"ok": self.ok,
			"back": self.back,
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

	def back(self):
		if len(self.stepHistory) > 1:
			self.currStep = self.stepHistory[-2]
			self.stepHistory = self.stepHistory[:-2]
		if self.currStep < 1:
			self.currStep = 1
		self.updateValues()
		
	def markDone(self):
		pass
	
	def getStepWithID(self, id):
		count = 0
		for x in self.wizard:
			if self.wizard[x]["id"] == id:
				return count
			count += 1
		return 0
		
	def ok(self):
		print "OK"
		currStep = self.currStep
		if self.showConfig:
			if (self.wizard[currStep]["config"]["screen"] != None):
				# TODO: don't die, if no run() is available
				# there was a try/except here, but i can't see a reason
				# for this. If there is one, please do a more specific check
				# and/or a comment in which situation there is no run()
				self.configInstance.run()
		
		if self.showList:
			if (len(self.wizard[currStep]["list"]) > 0):
				nextStep = self.wizard[currStep]["list"][self["list"].l.getCurrentSelectionIndex()][1]
				self.currStep = self.getStepWithID(nextStep)

		if (currStep == self.numSteps): # wizard finished
			self.markDone()
			self.close()
		else:
			self.runCode(self.wizard[currStep]["codeafter"])
			if self.wizard[currStep]["nextstep"] is not None:
				self.currStep = self.getStepWithID(self.wizard[currStep]["nextstep"])
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
		if (self.showConfig and self.wizard[self.currStep]["config"]["screen"] != None):
				self["config"].instance.moveSelection(self["config"].instance.moveUp)
		elif (self.showList and len(self.wizard[self.currStep]["list"]) > 0):
			self["list"].instance.moveSelection(self["list"].instance.moveUp)
		print "up"
		
	def down(self):
		if (self.showConfig and self.wizard[self.currStep]["config"]["screen"] != None):
			self["config"].instance.moveSelection(self["config"].instance.moveDown)
		elif (self.showList and len(self.wizard[self.currStep]["list"]) > 0):
			self["list"].instance.moveSelection(self["list"].instance.moveDown)
		print "down"
		
	def runCode(self, code):
		if code != "":
			print "code", code
			exec(code)
		
	def updateValues(self):
		print "Updating values in step " + str(self.currStep)
		
		self.stepHistory.append(self.currStep)
		
		if self.configInstance is not None:
			del self.configInstance["config"]
			self.configInstance.doClose()
			self.configInstance = None
		
		self.condition = True
		exec (self.wizard[self.currStep]["condition"])
		if self.condition:
			if self.showSteps:
				self["step"].setText(_("Step ") + str(self.currStep) + "/" + str(self.numSteps))
			if self.showStepSlider:
				self["stepslider"].setValue(self.currStep)
		
			print "wizard text", _(self.wizard[self.currStep]["text"])
			self["text"].setText(_(self.wizard[self.currStep]["text"]))
	
			self.runCode(self.wizard[self.currStep]["code"])
			
			if self.showList:
				self["list"].instance.setZPosition(1)
				self.list = []
				if (len(self.wizard[self.currStep]["list"]) > 0):
					self["list"].instance.setZPosition(2)
					for x in self.wizard[self.currStep]["list"]:
						self.list.append((_(x[0]), None))
				self["list"].l.setList(self.list)
	
			if self.showConfig:
				self["config"].instance.setZPosition(1)
				if (self.wizard[self.currStep]["config"]["screen"] != None):
					if self.wizard[self.currStep]["config"]["type"] == "standalone":
						print "Type is standalone"
						self.session.openWithCallback(self.ok, self.wizard[self.currStep]["config"]["screen"])
					else:
						self["config"].instance.setZPosition(2)
						print "wizard screen", self.wizard[self.currStep]["config"]["screen"]
						if self.wizard[self.currStep]["config"]["args"] == None:
							self.configInstance = self.session.instantiateDialog(self.wizard[self.currStep]["config"]["screen"])
						else:
							self.configInstance = self.session.instantiateDialog(self.wizard[self.currStep]["config"]["screen"], eval(self.wizard[self.currStep]["config"]["args"]))
						self["config"].l.setList(self.configInstance["config"].list)
						self.configInstance["config"].destroy()
						self.configInstance["config"] = self["config"]
				else:
					self["config"].l.setList([])
		else: # condition false
				self.currStep += 1
				self.updateValues()

class WizardManager:
	def __init__(self):
		self.wizards = []
	
	def registerWizard(self, wizard, precondition):
		self.wizards.append((wizard, precondition))
	
	def getWizards(self):
		list = []
		for x in self.wizards:
			if x[1] == 1: # precondition
				list.append(x[0])
		return list

wizardManager = WizardManager()

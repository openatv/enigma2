from xml.sax import make_parser
from xml.sax.handler import ContentHandler

from enigma import ePoint, eTimer

from Components.ActionMap import HelpableActionMap, HelpableNumberActionMap
from Components.config import ConfigPassword, ConfigText, KEY_0, KEY_ASCII, KEY_BACKSPACE, KEY_DELETE, KEY_LEFT, KEY_RIGHT, config
from Components.ConfigList import ConfigList
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Slider import Slider
from Components.SystemInfo import getBoxDisplayName
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen, ScreenSummary
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Tools.Directories import SCOPE_SKINS, resolveFilename


class Wizard(Screen):
	instance = None
	buttonMap = {
		"LEFT": "leftRightActions",
		"RIGHT": "leftRightActions",
		"UP": "upDownActions",
		"DOWN": "upDownActions",
		"BACKSPACE": "deleteActions",
		"DEL": "deleteActions",
		"1": "numberActions",
		"2": "numberActions",
		"3": "numberActions",
		"4": "numberActions",
		"5": "numberActions",
		"6": "numberActions",
		"7": "numberActions",
		"8": "numberActions",
		"9": "numberActions",
		"0": "numberActions",
		"RED": "redAction",
		"GREEN": "greenAction",
		"YELLOW": "yellowAction",
		"BLUE": "blueAction"
	}
	colorButtons = ["red", "green", "yellow", "blue"]

	# def __init__(self, session, xmlFile, showSteps=True, showStepSlider=True, showList=True, showConfig=True):
	def __init__(self, session, showSteps=True, showStepSlider=True, showList=True, showConfig=True):
		Screen.__init__(self, session, enableHelp=True)
		Wizard.instance = self
		self.showSteps = showSteps
		self.showStepSlider = showStepSlider
		self.showList = showList
		self.showConfig = showConfig
		self.setTitle(_("Welcome Wizard"))
		self.wizard = {}
		parser = make_parser()
		wizardHandler = self.parseWizard(self.wizard)
		parser.setContentHandler(wizardHandler)
		if not isinstance(self.xmlfile, list):  # DEBUG: Pass the XML file in via the command list and not via a shared variable.
			self.xmlfile = [self.xmlfile]
		print("[Wizard] Processing wizard script list %s." % self.xmlfile)
		for xmlFile in self.xmlfile:
			parser.parse(resolveFilename(SCOPE_SKINS, xmlFile))
		self.debugMode = False  # True if "debug" in self.wizard[0] else False
		if self.debugMode:  # Dump the wizard dictionary.
			for key in self.wizard:
				print("[Wizard] Wizard step %s - %s: Name='%s'." % (key, self.wizard[key]["type"], self.wizard[key]["name"]))
				for item in sorted(self.wizard[key]):
					if item in ("name", "type"):
						continue
					print("[Wizard]        %s: '%s'" % (item, self.wizard[key][item]))
		self["text"] = Label()
		self.displayText = ""
		if showSteps:
			self["step"] = Label()
		self.numSteps = len(self.wizard)
		if showStepSlider:
			self["stepslider"] = Slider(1, self.numSteps)
		if showList:
			self["list"] = List([])  # MenuList([])
			self["list"].onSelectionChanged.append(self.listChanged)
			self.listWidgetInstance = None
		if showConfig:
			self["config"] = ConfigList([], session=session)
			self["config"].onSelectionChanged.append(self.configChanged)
			self.configWidgetInstance = None
		self["key_red"] = StaticText()
		self["key_green"] = StaticText()
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self["key_text"] = StaticText()
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self.defaultButtons = ["HELP"]  # Should we also add "OK" to the default button list?
		# self["actions"] = HelpableNumberActionMap(self, ["WizardActions", "ColorActions", "NavigationActions", "NumberActions", "SetupActions", "InputAsciiActions", "KeyboardInputActions"], {
		# 	"ok": (self.keySelect, _("Select the currently highlighted option and move to the next step")),
		# 	"back": (self.keyStepBack, _("Go back to the previous step")),
		# 	"red": (self.keyRed, _("Select the action associated with the RED button")),
		# 	"green": (self.keyGreen, _("Select the action associated with the GREEN button")),
		# 	"yellow": (self.keyYellow, _("Select the action associated with the YELLOW button")),
		# 	"blue": (self.keyBlue, _("Select the action associated with the BLUE button")),
		# 	"up": (self.keyUp, _("Select the previous list item")),
		# 	"left": (self.keyLeft, _("Select previous option item in the option list")),
		# 	"right": (self.keyRight, _("Select next option item in the option list")),
		# 	"down": (self.keyDown, _("Select the next list item")),
		# 	"deleteBackward": (self.keyBackspace, _("BACKSPACE button")),
		# 	"deleteForward": (self.keyDelete, _("DELETE button")),
		# 	"1": (self.keyNumberGlobal, _("DIGIT button")),
		# 	"2": (self.keyNumberGlobal, _("DIGIT button")),
		# 	"3": (self.keyNumberGlobal, _("DIGIT button")),
		# 	"4": (self.keyNumberGlobal, _("DIGIT button")),
		# 	"5": (self.keyNumberGlobal, _("DIGIT button")),
		# 	"6": (self.keyNumberGlobal, _("DIGIT button")),
		# 	"7": (self.keyNumberGlobal, _("DIGIT button")),
		# 	"8": (self.keyNumberGlobal, _("DIGIT button")),
		# 	"9": (self.keyNumberGlobal, _("DIGIT button")),
		# 	"0": (self.keyNumberGlobal, _("DIGIT button")),
		# 	"gotAsciiCode": (self.keyGotAscii, _("ASCII button"))
		# }, prio=-1, description=_("Wizard Actions"))
		self["wizardActions"] = HelpableActionMap(self, ["WizardActions", "InputAsciiActions"], {
			"ok": (self.keySelect, _("Proceed to the next step")),
			"back": (self.keyStepBack, _("Go back to the previous step")),
			"gotAsciiCode": (self.keyGotAscii, _("Enter text via an attached keyboard"))
		}, prio=0, description=_("Wizard Actions"))
		self["debugActions"] = HelpableActionMap(self, ["WizardActions"], {
			# "info": (self.dumpDictionary, _("Dump the current wizard dictionary into the logs (Debug mode only)")),
			"info": (self.exit, _("Immediately exit the wizard (Debug mode only)")),
		}, prio=0, description=_("Wizard Actions"))
		self["debugActions"].setEnabled(self.debugMode)
		self["leftRightActions"] = HelpableActionMap(self, ["NavigationActions"], {
			"left": (self.keyLeft, _("View the previous item in a list")),
			"right": (self.keyRight, _("View the next item in a list"))
		}, prio=0, description=_("Wizard Actions"))
		self["leftRightActions"].setEnabled(False)
		self["upDownActions"] = HelpableActionMap(self, ["NavigationActions"], {
			"up": (self.keyUp, _("Move up a line")),
			"down": (self.keyDown, _("Move down a line"))
		}, prio=0, description=_("Wizard Actions"))
		self["upDownActions"].setEnabled(False)
		self["deleteActions"] = HelpableActionMap(self, ["SetupActions"], {
			"deleteBackward": (self.keyBackspace, _("Delete the character to the left of the cursor")),
			"deleteForward": (self.keyDelete, _("Delete the character under the cursor"))
		}, prio=0, description=_("Wizard Actions"))
		self["deleteActions"].setEnabled(False)
		self["numberActions"] = HelpableNumberActionMap(self, ["NumberActions"], {
			"1": (self.keyNumberGlobal, _("Select a menu item")),
			"2": (self.keyNumberGlobal, _("Select a menu item")),
			"3": (self.keyNumberGlobal, _("Select a menu item")),
			"4": (self.keyNumberGlobal, _("Select a menu item")),
			"5": (self.keyNumberGlobal, _("Select a menu item")),
			"6": (self.keyNumberGlobal, _("Select a menu item")),
			"7": (self.keyNumberGlobal, _("Select a menu item")),
			"8": (self.keyNumberGlobal, _("Select a menu item")),
			"9": (self.keyNumberGlobal, _("Select a menu item")),
			"0": (self.keyNumberGlobal, _("Select a menu item"))
		}, prio=0, description=_("Wizard Actions"))
		self["numberActions"].setEnabled(False)
		self["redAction"] = HelpableActionMap(self, ["ColorActions"], {
			"red": (self.keyRed, _("Process RED button action")),
		}, prio=0, description=_("Wizard Actions"))
		self["redAction"].setEnabled(False)
		self["greenAction"] = HelpableActionMap(self, ["ColorActions"], {
			"green": (self.keyGreen, _("Process GREEN button action")),
		}, prio=0, description=_("Wizard Actions"))
		self["greenAction"].setEnabled(False)
		self["yellowAction"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.keyYellow, _("Process YELLOW button action")),
		}, prio=0, description=_("Wizard Actions"))
		self["yellowAction"].setEnabled(False)
		self["blueAction"] = HelpableActionMap(self, ["ColorActions"], {
			"blue": (self.keyBlue, _("Process BLUE button action")),
		}, prio=0, description=_("Wizard Actions"))
		self["blueAction"].setEnabled(False)
		self["VirtualKB"] = HelpableActionMap(self, ["VirtualKeyboardActions"], {
			"showVirtualKeyboard": (self.keyText, _("Open the VirtualKeyBoard for text entry"))
		}, prio=0, description=_("Wizard Actions"))
		self["VirtualKB"].setEnabled(False)
		self.screenInstance = None
		self.disableKeys = False
		self.isLastWizard = False  # Can be used to skip a "goodbye" screen in a wizard.
		self.onTextChanged = []
		self.onListChanged = []
		self.onConfigChanged = []
		self.stepHistory = []
		self.currStep = self.findStepByName("start") + 1
		self.timeoutTimer = eTimer()
		self.timeoutTimer.callback.append(self.timerTimeout)
		self.timerCount = 0
		self.onShown.append(self.updateValues)
		self.onLayoutFinish.append(self.layoutFinished)

	class parseWizard(ContentHandler):
		def __init__(self, wizard):
			# self.isPointsElement = 0
			# self.isReboundsElement = 0
			self.wizard = wizard
			self.tag = None
			self.step = 0

		def startElement(self, tag, attributes):  # Process and initialize tags.
			# print("[Wizard] startElement '%s'." % tag)
			self.tag = tag
			# if tag == "wizard":
			# 	self.wizard[0] = {}
			# 	self.wizard[0]["type"] = "Wizard"
			# 	self.wizard[0]["name"] = "WizardMain"
			# 	self.wizard[0]["id"] = "WizardMain"
			# 	# self.createString("name", None, attributes, "WizardMain")
			# 	# self.createString("title", None, attributes)
			# 	# self.createBoolean("forceTitle", None, attributes, "False")
			# 	# self.createBoolean("showSteps", None, attributes, "False")
			# 	# self.createBoolean("debug", None, attributes, "False")
			if tag == "step":
				self.step += 1
				self.wizard[self.step] = {}
				self.wizard[self.step]["type"] = "None"
				self.wizard[self.step] = {
					"type": "None",
					"name": attributes.get("name", attributes.get("id", "")),
					"condition": "",
					"text": "",
					"timeout": int(attributes.get("timeout", 0)),
					"timeoutAction": attributes.get("timeoutaction", "nextpage"),
					"timeoutStep": attributes.get("timeoutstep", ""),
					"list": [],
					"config": {
						"screen": None,
						"args": None,
						"type": ""
					},
					"code": "",
					"codeAfter": "",
					"codeAsync": "",
					"codeAfterAsync": "",
					"nextStep": attributes.get("nextstep", None)
				}
				if "laststep" in attributes:
					self.wizard[self.step]["lastStep"] = attributes.get("laststep")
			elif tag == "text":
				self.wizard[self.step]["text"] = attributes.get("value", "").replace("\\n", "\n")
			elif tag == "displaytext":
				self.wizard[self.step]["display"] = attributes.get("value", "").replace("\\n", "\n")
			elif tag == "display":
				self.wizard[self.step]["display"] = attributes.get("value", "").replace("\\n", "\n")
			elif tag == "list":
				self.wizard[self.step]["type"] = "List"
				if "type" in attributes:
					if attributes["type"] == "dynamic":
						self.wizard[self.step]["dynamicList"] = attributes.get("source")
				if "evaluation" in attributes:
					self.wizard[self.step]["listEvaluation"] = attributes.get("evaluation")
				if "onselect" in attributes:
					self.wizard[self.step]["onSelect"] = attributes.get("onselect")
			elif tag == "listentry":
				self.wizard[self.step]["list"].append((attributes.get("caption", ""), attributes.get("step", "")))
			elif tag == "config":
				self.wizard[self.step]["type"] = "Config"
				type = str(attributes.get("type", None))
				self.wizard[self.step]["config"]["type"] = type
				if type in ("ConfigList", "standalone"):
					try:
						exec("from Screens.%s import *" % attributes.get("module", "None"), globals())
					except ImportError:
						exec("from %s import *" % attributes.get("module", "None"), globals())
					self.wizard[self.step]["config"]["screen"] = eval(attributes.get("screen", "None"))
					if "args" in attributes:
						self.wizard[self.step]["config"]["args"] = attributes.get("args", "None")
				elif type == "dynamic":
					self.wizard[self.step]["config"]["source"] = attributes.get("source", "None")
					if "evaluation" in attributes:
						self.wizard[self.step]["config"]["evaluation"] = attributes.get("evaluation", "None")
			elif tag == "code":
				self.async_code = attributes.get("async", "") == "yes"
				self.codeAfter = attributes.get("pos", "") == "after"
			elif tag == "condition":
				pass
			elif tag == "buttons":
				self.wizard[self.step]["buttons"] = [x.upper() for x in attributes.get("enable", "").replace(" ", "").split(",") if x]
			elif tag == "colorButtonLabels":
				buttons = {}
				for button in Wizard.colorButtons:
					text = attributes.get(button, "")
					if text:
						text = _(text)
					buttons[button] = text
				self.wizard[self.step]["colorButtonLabels"] = buttons

		def endElement(self, tag):  # Clean up (strip) the block tags and delete empty block tags.
			self.tag = ""
			if tag == "code":
				if self.async_code:
					if self.codeAfter:
						self.wizard[self.step]["codeAfterAsync"] = self.wizard[self.step]["codeAfterAsync"].strip()  # Should these be rstrip()?
					else:
						self.wizard[self.step]["codeAsync"] = self.wizard[self.step]["codeAsync"].strip()
				else:
					if self.codeAfter:
						self.wizard[self.step]["codeAfter"] = self.wizard[self.step]["codeAfter"].strip()
					else:
						self.wizard[self.step]["code"] = self.wizard[self.step]["code"].strip()
			elif tag == "condition":
				self.wizard[self.step]["condition"] = self.wizard[self.step]["condition"].strip()
			elif tag == "step":
				# print("[Wizard] Step number %d: '%s'." % (self.step, self.wizard[self.step]))
				pass

		def characters(self, text):  # Capture the data between block tags.  Data with no value will be deleted in the endElement code.
			if self.tag == "code":
				if self.async_code:
					if self.codeAfter:
						self.wizard[self.step]["codeAfterAsync"] = "%s%s" % (self.wizard[self.step]["codeAfterAsync"], text)
					else:
						self.wizard[self.step]["codeAsync"] = "%s%s" % (self.wizard[self.step]["codeAsync"], text)
				else:
					if self.codeAfter:
						self.wizard[self.step]["codeAfter"] = "%s%s" % (self.wizard[self.step]["codeAfter"], text)
					else:
						self.wizard[self.step]["code"] = "%s%s" % (self.wizard[self.step]["code"], text)
			elif self.tag == "condition":
				self.wizard[self.step]["condition"] = "%s%s" % (self.wizard[self.step]["condition"], text)

	def layoutFinished(self):
		if self.showList:
			for renderer in self.renderer:
				rootRenderer = renderer
				while renderer.source:
					if renderer.source is self["list"]:
						self.listWidgetInstance = rootRenderer.instance
					renderer = renderer.source
			self.listWidgetInstance.enableAutoNavigation(False)
		if self.showConfig:
			self.configWidgetInstance = self["config"].instance
			self.configWidgetInstance.enableAutoNavigation(False)

	def textChanged(self, text):
		self.displayText = text
		for callback in self.onTextChanged:
			callback()

	def listChanged(self):
		print("[Wizard] DEBUG: List selection changed in step %d." % self.currStep)
		if self.wizard[self.currStep]["evaluatedList"] and "onSelect" in self.wizard[self.currStep]:
			self.selection = self["list"].current[-1]
			print("[Wizard] self.selection: %s" % str(self.selection))
			exec("self.%s()" % self.wizard[self.currStep]["onSelect"])
		for callback in self.onListChanged:
			callback()

	def configChanged(self):
		for callback in self.onConfigChanged:
			callback()

	def keySelect(self):
		print("[Wizard] DEBUG: OK button pressed in step %d." % self.currStep)
		if self.disableKeys:
			print("[Wizard] DEBUG: Button disabled!")
			return
		currStep = self.currStep
		if self.showConfig and self.wizard[currStep]["config"]["screen"]:
			# TODO: Don't die, if no run() is available. There was a try/except here,
			# but i can't see a reason for this. If there is one, please do a more
			# specific check and/or comment in which situation there is no run().
			if callable(getattr(self.screenInstance, "runAsync", None)):
				if self.updateValues in self.onShown:
					self.onShown.remove(self.updateValues)
				self.screenInstance.runAsync(self.finished)
				return
			elif self.screenInstance:
				self.screenInstance.run()
		self.finished()

	def back(self):  # temporary fix for Satconfig.py
		self.keyStepBack()

	def keyStepBack(self):
		# def keyCancelCallback(answer):  # The exitWizardQuestion() method is required by the AutoTimer plugin!
		# 	print("[Wizard] Exiting the wizard %s." % answer)
		# 	if answer:
		# 		self.markDone()
		# 		self.exit()

		print("[Wizard] DEBUG: EXIT button pressed in step %d." % self.currStep)
		if self.disableKeys:
			print("[Wizard] DEBUG: Button disabled!")
			return
		print("[Wizard] The starting step is %d and the current step history is %s." % (self.currStep, self.stepHistory))
		if len(self.stepHistory) > 1:
			self.currStep = self.stepHistory[-2]
			self.stepHistory = self.stepHistory[:-2]
		else:
			self.session.openWithCallback(self.exitWizardQuestion, MessageBox, (_("Are you sure you want to exit this wizard?")), windowTitle=self.getTitle())
		if self.currStep < 1:
			self.currStep = 1
		print("[Wizard] The current step is %d and the current step history is %s." % (self.currStep, self.stepHistory))
		self.updateValues()
		print("[Wizard] The ending is %d and the current step history is %s." % (self.currStep, self.stepHistory))

	def exitWizardQuestion(self, answer):  # This method is required by the AutoTimer plugin!
		print("[Wizard] Exiting the wizard %s." % answer)
		if answer:
			self.markDone()
			self.exit()

	def keyRed(self):
		print("[Wizard] DEBUG: RED button pressed in step %d." % self.currStep)
		if self.wizard[self.currStep]["config"]["screen"] and hasattr(self.screenInstance, "red") and callable(self.screenInstance.red):
			self.screenInstance.red()

	def keyGreen(self):
		print("[Wizard] DEBUG: GREEN button pressed in step %d." % self.currStep)
		if self.wizard[self.currStep]["config"]["screen"] and hasattr(self.screenInstance, "green") and callable(self.screenInstance.green):
			self.screenInstance.green()

	def keyYellow(self):
		print("[Wizard] DEBUG: YELLOW button pressed in step %d." % self.currStep)
		if self.wizard[self.currStep]["config"]["screen"] and hasattr(self.screenInstance, "yellow") and callable(self.screenInstance.yellow):
			self.screenInstance.yellow()

	def keyBlue(self):
		print("[Wizard] DEBUG: BLUE button pressed in step %d." % self.currStep)
		if self.wizard[self.currStep]["config"]["screen"] and hasattr(self.screenInstance, "blue") and callable(self.screenInstance.blue):
			self.screenInstance.blue()

	def keyBackspace(self):
		print("[Wizard] DEBUG: BACKSPACE button pressed in step %d." % self.currStep)
		self.timerReset()
		if self.wizard[self.currStep]["config"]["screen"]:
			self.screenInstance.keyBackspace()
		elif self.wizard[self.currStep]["config"]["type"] == "dynamic":
			self["config"].handleKey(KEY_BACKSPACE)

	def keyDelete(self):
		print("[Wizard] DEBUG: DELETE button pressed in step %d." % self.currStep)
		self.timerReset()
		if self.wizard[self.currStep]["config"]["screen"]:
			self.screenInstance.keyDelete()
		elif self.wizard[self.currStep]["config"]["type"] == "dynamic":
			self["config"].handleKey(KEY_DELETE)

	def keyUp(self):
		print("[Wizard] DEBUG: UP button pressed in step %d." % self.currStep)
		self.timerReset()
		if self.showConfig and self.wizard[self.currStep]["config"]["screen"] or self.wizard[self.currStep]["config"]["type"] == "dynamic":
			# self["config"].instance.goLineUp()
			self.configWidgetInstance.goLineUp()
			self.handleInputHelpers()
		elif self.showList and len(self.wizard[self.currStep]["evaluatedList"]) > 0:
			self["list"].goLineUp()
			if "onSelect" in self.wizard[self.currStep]:
				# print("[Wizard] current: %s" % str(self["list"].current))
				# self.selection = self.wizard[self.currStep]["evaluatedList"][self["list"].getCurrentSelectionIndex()][1]
				self.selection = self["list"].current[-1]
				exec("self.%s()" % self.wizard[self.currStep]["onSelect"])

	def keyLeft(self):
		print("[Wizard] DEBUG: LEFT button pressed in step %d." % self.currStep)
		self.timerReset()
		if self.wizard[self.currStep]["config"]["screen"]:
			self.screenInstance.keyLeft()
		elif self.wizard[self.currStep]["config"]["type"] == "dynamic":
			self["config"].handleKey(KEY_LEFT)
		self.configChanged()  # This shouldn't be called for lists.  I should be fixed when the action map is fixed!

	def keyRight(self):
		print("[Wizard] DEBUG: RIGHT button pressed in step %d." % self.currStep)
		self.timerReset()
		if self.wizard[self.currStep]["config"]["screen"]:
			self.screenInstance.keyRight()
		elif self.wizard[self.currStep]["config"]["type"] == "dynamic":
			self["config"].handleKey(KEY_RIGHT)
		self.configChanged()  # This shouldn't be called for lists.  I should be fixed when the action map is fixed!

	def keyDown(self):
		print("[Wizard] DEBUG: DOWN button pressed in step %d." % self.currStep)
		self.timerReset()
		if self.showConfig and self.wizard[self.currStep]["config"]["screen"] or self.wizard[self.currStep]["config"]["type"] == "dynamic":
			# self["config"].instance.goLineDown()
			self.configWidgetInstance.goLineDown()
			self.handleInputHelpers()
		elif self.showList and len(self.wizard[self.currStep]["evaluatedList"]) > 0:
			# self.listWidgetInstance.goLineDown()
			self["list"].goLineDown()
			if "onSelect" in self.wizard[self.currStep]:
				# print("current: '%s'." % self["list"].current)
				# self.selection = self.wizard[self.currStep]["evaluatedList"][self["list"].getCurrentSelectionIndex()][1]
				self.selection = self["list"].current[-1]  # IanSav: Should this be +1?
				exec("self.%s()" % self.wizard[self.currStep]["onSelect"])

	def handleInputHelpers(self):
		enabled = False
		if self["config"].getCurrent():
			if isinstance(self["config"].getCurrent()[1], (ConfigText, ConfigPassword)):
				if self.__class__.__name__ != "NetworkWizard":  # This is a temporary hack to fix a problem with VirtualKeyBoard input.
					enabled = True
				if "HelpWindow" in self:
					if self["config"].getCurrent()[1].help_window.instance:
						helpWindowPosition = self["HelpWindow"].getPosition()
						self["config"].getCurrent()[1].help_window.instance.move(ePoint(helpWindowPosition[0], helpWindowPosition[1]))
		if "VKeyIcon" in self:
			self["key_text"].setText(_("TEXT") if enabled else "")
			self["VirtualKB"].setEnabled(enabled)
			self["VKeyIcon"].boolean = enabled

	def keyNumberGlobal(self, digit):
		if self.wizard[self.currStep]["config"]["screen"]:
			self.screenInstance.keyNumberGlobal(digit)
		elif self.wizard[self.currStep]["config"]["type"] == "dynamic":
			self["config"].handleKey(KEY_0 + digit)

	def keyText(self):
		def keyTextCallback(text):
			if text:
				current = self["config"].getCurrent()
				if isinstance(current[1], (ConfigText, ConfigPassword)) and "HelpWindow" in self and current[1].help_window.instance:
					helpWindowPosition = self["HelpWindow"].getPosition()
					current[1].help_window.instance.move(ePoint(helpWindowPosition[0], helpWindowPosition[1]))
				self.configWidgetInstance.moveSelectionTo(configIndex)
				self["config"].setCurrentIndex(configIndex)
				self["config"].getCurrent()[1].setValue(text)
				self["config"].invalidate(self["config"].getCurrent())

		configIndex = self["config"].getCurrentIndex()
		self.session.openWithCallback(keyTextCallback, VirtualKeyBoard, title=self["config"].getCurrent()[0], text=self["config"].getCurrent()[1].value)

	def keyGotAscii(self):
		if self.wizard[self.currStep]["config"]["screen"]:
			self["config"].handleKey(KEY_ASCII)
		elif self.wizard[self.currStep]["config"]["type"] == "dynamic":
			self["config"].handleKey(KEY_ASCII)

	# def findStepByNameBad(self, name):
	# 	for key in self.wizard.keys():
	# 		if self.wizard[key]["name"] == name:
	# 			print("[Wizard] Step name '%s' evaluates to step number %d." % (name, key))
	# 			return key
	# 	print("[Wizard] Step name '%s' not found!" % name)
	# 	return 0

	def findStepByName(self, name):
		for count, key in enumerate(self.wizard.keys()):
			if self.wizard[key]["name"] == name:
				# print("[Wizard] Step name '%s' evaluates to step number %d." % (name, count))
				return count
		print("[Wizard] Step name '%s' not found!" % name)
		return 0

	def getStepWithID(self, id):  # Legacy interface.
		return self.findStepByName(id)

	def timerReset(self):
		self.timerCount = self.wizard[self.currStep]["timeout"] or 0  # TODO: The "or 0" should not be needed when the parser is fixed.

	def timerTimeout(self):
		self.timerCount -= 1
		# print("[Wizard] Timeout timer is %d." % self.timerCount)
		if self.timerCount == 0:
			if self.wizard[self.currStep]["timeoutAction"] == "selectnext":
				# print("[Wizard] Timeout fired, moving to next item.")
				self.keyDown()
			elif self.wizard[self.currStep]["timeoutAction"] == "changestep":
				self.finished(gotoStep=self.wizard[self.currStep]["timeoutStep"])
		self.updateText()

	def updateValues(self):
		# Calling a step which doesn't exist can only happen if the condition in the last
		# step is not fulfilled. If a non-existing step is called, end the wizard.
		if self.currStep > len(self.wizard):
			self.markDone()
			self.exit()
			return
		stepName = self.wizard[self.currStep].get("name", "* Unknown *")
		print("[Wizard] Preparing step %d (%s)." % (self.currStep, stepName))
		self.timeoutTimer.stop()
		# if stepName == "scanquestion":  # Enable this block to debug a specified step.
		# 	for key in self.wizard[self.currStep].keys():
		# 		print("[Wizard] DEBUG: Key %s: '%s'." % (key, self.wizard[self.currStep][key]))
		if self.screenInstance:  # Remove callbacks.
			self.screenInstance["config"].onSelectionChanged = []
			del self.screenInstance["config"]
			self.screenInstance.doClose()
			self.screenInstance = None
		self.condition = True
		exec(self.wizard[self.currStep]["condition"])
		if self.condition:
			if len(self.stepHistory) == 0 or self.stepHistory[-1] != self.currStep:
				self.stepHistory.append(self.currStep)
			self.enableButtons(self.wizard[self.currStep]["buttons"] if "buttons" in self.wizard[self.currStep] else None)
			self.setButtonLabels(self.wizard[self.currStep]["colorButtonLabels"] if "colorButtonLabels" in self.wizard[self.currStep] else {})
			self.updateText(firstSet=True)
			if "display" in self.wizard[self.currStep]:  # IanSav: Should this be repeated?
				displayText = self.getTranslation(self.wizard[self.currStep]["display"])
				print("[Wizard] Setting display text to '%s'." % displayText)
				self.textChanged(displayText)
			if self.showSteps:
				self["step"].setText("%s %d/%d" % (_("Step"), self.currStep, self.numSteps))  # IanSav: Translation change "Step " to "Step".
			if self.showStepSlider:
				self["stepslider"].setValue(self.currStep)
			if self.wizard[self.currStep]["timeout"]:
				self.timerReset()
				self.timeoutTimer.start(1000)
			self.codeAfter = False
			self.runCode(self.wizard[self.currStep]["code"])
			if self.runCode(self.wizard[self.currStep]["codeAsync"]):
				if self.updateValues in self.onShown:
					self.onShown.remove(self.updateValues)
			else:
				self.afterAsyncCode()
		else:
			if "lastStep" in self.wizard[self.currStep]:  # Exit wizard, if condition of laststep doesn't hold.
				self.markDone()
				self.exit()
				return
			else:
				self.currStep += 1
				self.updateValues()

	def enableButtons(self, buttonList):
		self.clearSelectedKeys()
		default = buttonList is None  # Enable all action maps for older wizard XML files that don't use the "buttons" tag.
		actions = set()
		for button in Wizard.buttonMap.keys():
			actions.add(Wizard.buttonMap[button])
		for action in actions:
			self[action].setEnabled(default)
		if buttonList is not None:
			if not isinstance(buttonList, list):
				buttonList = [buttonList]
			print("[Wizard] Allowed buttons are %s." % ", ".join(buttonList + self.defaultButtons))
			actions = set()
			for button in buttonList + self.defaultButtons:
				self.selectKey(button)
				action = Wizard.buttonMap.get(button, None)
				if action:
					actions.add(action)
			for action in actions:
				self[action].setEnabled(True)

	def setButtonLabels(self, labelDictionary):
		for button in Wizard.colorButtons:
			self["key_%s" % button].setText(labelDictionary.get(button, ""))

	def updateText(self, firstSet=False):
		text = self.getTranslation(self.wizard[self.currStep]["text"] if "text" in self.wizard[self.currStep] else "")
		if "[timeout]" in text:
			text = text.replace("[timeout]", str(self.timerCount))
			self["text"].setText(text)
		else:
			if firstSet:
				self["text"].setText(text)

	def getTranslation(self, text):
		text = _(text)
		box = "%s %s" % getBoxDisplayName()
		timeout = ngettext("%d Second", "%d Seconds", self.timerCount) % self.timerCount if "timeout" in self.wizard[self.currStep] else _("inactive")
		if "[TUNER]" in text and self.currStep and self.currStep in self.wizard:
			currStep = self.wizard[self.currStep].get("name", "")
			tuner = currStep[-1].upper() if len(currStep) == 4 and currStep.startswith("nim") else _("N/A")
		else:
			tuner = ""
		textSubstitutions = [
			("%s %s", box),
			("[BOX]", box),
			("[STEP]", str(self.currStep)),
			("[STEPS]", str(self.numSteps)),
			("[TIMEOUT]", timeout),
			("[TITLE]", self.getTitle()),
			("[TUNER]", tuner)
		]
		for marker, substitute in textSubstitutions:
			text = text.replace(marker, substitute)
		return text

	def markDone(self):
		print("[Wizard] Running helper 'wizardDone()' code.")

	def exit(self):
		Wizard.instance = None
		self.close()

	def finished(self, gotoStep=None, *args, **kwargs):
		print("[Wizard] Running finished() code.")
		currStep = self.currStep
		if self.updateValues not in self.onShown:
			self.onShown.append(self.updateValues)
		if self.showConfig:
			if self.wizard[currStep]["config"]["type"] == "dynamic":
				eval("self.%s" % self.wizard[currStep]["config"]["evaluation"])()
		if self.showList:
			if len(self.wizard[currStep]["evaluatedList"]) > 0:
				# print("[Wizard] current: '%s'." % self["list"].current)
				nextStep = self["list"].current[1]
				if "listEvaluation" in self.wizard[currStep]:
					exec("self.%s('%s')" % (self.wizard[self.currStep]["listEvaluation"], nextStep))
				else:
					self.currStep = self.findStepByName(nextStep)
		# printNow = True
		if (currStep == self.numSteps and self.wizard[currStep]["nextStep"] is None) or self.wizard[currStep]["name"] == "end":  # wizard finished
			# print("[Wizard] wizard finished")
			self.markDone()
			self.exit()
		else:
			self.codeAfter = True
			self.runCode(self.wizard[currStep]["codeAfter"])
			self.prevStep = currStep
			self.gotoStep = gotoStep
			if not self.runCode(self.wizard[currStep]["codeAfterAsync"]):
				self.afterAsyncCode()
			else:
				if self.updateValues in self.onShown:
					self.onShown.remove(self.updateValues)
		# if printNow:
		# 	print("[Wizard] Now: '%s'." % self.currStep)

	def runCode(self, code):
		if code != "":
			print("[Wizard] Running script code: '%s'." % code)
			exec(code)
			return True
		return False

	def afterAsyncCode(self):
		if self.updateValues not in self.onShown:
			self.onShown.append(self.updateValues)
		if self.codeAfter:
			if self.wizard[self.prevStep]["nextStep"]:
				self.currStep = self.findStepByName(self.wizard[self.prevStep]["nextStep"])
			if self.gotoStep:
				self.currStep = self.findStepByName(self.gotoStep)
			self.currStep += 1
			self.updateValues()
		else:
			if self.showList:
				self.listWidgetInstance.setZPosition(1)
				newList = []
				if "dynamicList" in self.wizard[self.currStep]:
					dynamicList = self.wizard[self.currStep]["dynamicList"]
					print("[Wizard] Generating dynamic list by calling '%s'." % dynamicList)
					dynamicList = eval("self.%s()" % dynamicList)
					for entry, step in dynamicList:
						print("[Wizard] DEBUG: Adding dynamic item '%s' to list." % entry)
						newList.append((entry, step))
					# del self.wizard[self.currStep]["dynamicList"]
				if self.wizard[self.currStep]["list"]:
					for entry, step in self.wizard[self.currStep]["list"]:
						entry = self.getTranslation(entry)
						print("[Wizard] DEBUG: Adding XML item '%s' to list." % entry)
						newList.append((entry, step))
				self.wizard[self.currStep]["evaluatedList"] = newList
				self["list"].setList(newList)
				self["list"].setCurrentIndex(0)
				# if self.configWidgetInstance:
				# 	self.configWidgetInstance.hide()
				# self.listWidgetInstance.show()
			if self.showConfig:
				if self.wizard[self.currStep]["config"]["type"] == "dynamic":
					print("[Wizard] Generating dynamic config by calling %s." % self.wizard[self.currStep]["config"]["source"])
					self.configWidgetInstance.setZPosition(2)
					self["config"].setList(eval("self.%s" % self.wizard[self.currStep]["config"]["source"])())
				elif self.wizard[self.currStep]["config"]["screen"]:
					if self.wizard[self.currStep]["config"]["type"] == "standalone":
						def screenCallback(*retVal):
							self.keySelect()
						print("[Wizard] Loading an external config screen %s." % self.wizard[self.currStep]["config"]["screen"])
						if self.updateValues in self.onShown:
							self.onShown.remove(self.updateValues)
						self.session.openWithCallback(screenCallback, self.wizard[self.currStep]["config"]["screen"])
					else:
						print("[Wizard] Extracting 'Config' widget from external screen %s." % self.wizard[self.currStep]["config"]["screen"])
						self.configWidgetInstance.setZPosition(2)
						if self.wizard[self.currStep]["config"]["args"] is None:
							self.screenInstance = self.session.instantiateDialog(self.wizard[self.currStep]["config"]["screen"])
						else:
							self.screenInstance = self.session.instantiateDialog(self.wizard[self.currStep]["config"]["screen"], eval(self.wizard[self.currStep]["config"]["args"]))
						self.screenInstance.setAnimationMode(0)
						self["config"].setList(self.screenInstance["config"].getList())
						callbacks = self.screenInstance["config"].onSelectionChanged[:]
						self.screenInstance["config"].destroy()
						# print("[Wizard] DEBUG: clearConfigList %s %s" % (str(self.screenInstance["config"]), str(self["config"])))
						self.screenInstance["config"] = self["config"]
						self.screenInstance["config"].onSelectionChanged = callbacks
						if self.configChanged not in self.screenInstance["config"].onSelectionChanged:
							self.screenInstance["config"].onSelectionChanged.append(self.configChanged)
						# print("[Wizard] DEBUG: clearConfigList %s %s" % (str(self.screenInstance["config"]), str(self["config"])))
				else:
					self["config"].setList([])
				self["config"].setCurrentIndex(0)
				self.handleInputHelpers()
				# if self.listWidgetInstance:
				# 	self.listWidgetInstance.hide()
				# self.configWidgetInstance.show()

	def createSummary(self):
		return WizardSummary


class WizardSummary(ScreenSummary):
	def __init__(self, session, parent):
		ScreenSummary.__init__(self, session, parent)
		self.skinName = ["WizardSummary"]
		self["text"] = StaticText("")
		self["entry"] = StaticText("")
		self["value"] = StaticText("")
		if self.addWatcher not in self.onShow:
			self.onShow.append(self.addWatcher)
		if self.removeWatcher not in self.onHide:
			self.onHide.append(self.removeWatcher)

	def addWatcher(self):
		if self.textChanged not in self.parent.onTextChanged:
			self.parent.onTextChanged.append(self.textChanged)
		if self.listChanged not in self.parent.onListChanged:
			self.parent.onListChanged.append(self.listChanged)
		if self.configChanged not in self.parent.onConfigChanged:
			self.parent.onConfigChanged.append(self.configChanged)
		self.textChanged()
		self.listChanged()
		self.configChanged()

	def removeWatcher(self):
		if self.textChanged in self.parent.onTextChanged:
			self.parent.onTextChanged.remove(self.textChanged)
		if self.listChanged in self.parent.onListChanged:
			self.parent.onListChanged.remove(self.listChanged)
		if self.configChanged in self.parent.onConfigChanged:
			self.parent.onConfigChanged.remove(self.configChanged)

	def textChanged(self):
		self["text"].setText(self.parent.displayText)

	def listChanged(self):
		current = self.parent["list"].getCurrent()
		self["entry"].setText(current[0] if current else "")
		self["value"].setText("")

	def configChanged(self):
		current = self.parent["config"].getCurrent()
		self["entry"].setText(current[0] if current else "")
		# If current[1] is a class or hasattr(current[1], "toDisplayString") then it must be a ConfigList item.
		self["value"].setText(current[1].toDisplayString(current[1].value) if current else "")


class WizardManager:
	def __init__(self):
		self.wizards = []

	def registerWizard(self, wizard, preCondition, priority=0):
		print("[Wizard] registerWizard DEBUG: wizard=%s, preCondition=%s, priority=%d." % (str(wizard), preCondition, priority))
		self.wizards.append((wizard, preCondition, priority))

	def getWizards(self):
		for wizard in self.wizards:  # For self.wizards, x[0]=wizard, x[1]=preCondition and x[2]=priority.
			print("[Wizard] getWizards DEBUG: Defined wizard=%s, preCondition=%s, priority=%d." % (wizard[0], wizard[1], wizard[2]))
			wizard[0].isLastWizard = False
		if len(self.wizards) > 0:
			self.wizards[-1][0].isLastWizard = True
		wizards = [(x[2], x[0]) for x in self.wizards if x[1]]  # For wizards, x[0]=priority and x[1]=wizard. The wizards will be sorted in StartEnigma.py.
		for wizard in wizards:
			print("[Wizard] getWizards DEBUG: Active priority=%d, wizard=%s." % (wizard[0], wizard[1]))
		return wizards


wizardManager = WizardManager()

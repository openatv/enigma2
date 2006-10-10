from Screen import Screen
from Components.ConfigList import ConfigList, ConfigListScreen
from Components.ActionMap import NumberActionMap
from Components.config import config, getConfigListEntry, ConfigNothing, NoSave, ConfigPIN
from Components.ServiceList import ServiceList
from Components.ParentalControlList import ParentalControlEntryComponent, ParentalControlList 
from Components.ParentalControl import parentalControl
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.InputBox import InputBox, Input, PinInput
from Screens.ChannelSelection import service_types_tv
from Tools.Directories import resolveFilename, SCOPE_CONFIG
from Tools.BoundFunction import boundFunction
from ServiceReference import ServiceReference
from enigma import eServiceCenter, eServiceReference
import os
import operator

class ProtectedScreen:
	def __init__(self):
		if self.isProtected():
			self.onFirstExecBegin.append(boundFunction(self.session.openWithCallback, self.pinEntered, PinInput, pinList = [self.protectedWithPin()], title = self.getPinText(), windowTitle = _("Change pin code")))

	def getPinText(self):
		return _("Please enter the correct pin code")
	
	def isProtected(self):
		return True
	
	def protectedWithPin(self):
		return config.ParentalControl.setuppin.value
	
	def pinEntered(self, result):
		if result[0] is None:
			self.close()
		if not result[0]:
			print result, "-", self.protectedWithPin()
			self.session.openWithCallback(self.close, MessageBox, _("The pin code you entered is wrong."), MessageBox.TYPE_ERROR)

class ParentalControlSetup(Screen, ConfigListScreen, ProtectedScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		
		ProtectedScreen.__init__(self)
		
		self["actions"] = NumberActionMap(["SetupActions"],
		{
			"cancel": self.keyCancel
		}, -2)
		
		self.list = []
		ConfigListScreen.__init__(self, self.list)
		self.createSetup()
	
	def isProtected(self):
		return config.ParentalControl.setuppinactive.value
	
	def createSetup(self):
		self.editListEntry = None
		self.changePin = None
		self.changeSetupPin = None
		
		self.list = []
		self.list.append(getConfigListEntry(_("Enable parental control"), config.ParentalControl.configured))
		print "config.ParentalControl.configured.value", config.ParentalControl.configured.value
		if config.ParentalControl.configured.value:
			#self.list.append(getConfigListEntry(_("Configuration mode"), config.ParentalControl.mode))
			self.list.append(getConfigListEntry(_("Protect setup"), config.ParentalControl.setuppinactive))
			if config.ParentalControl.setuppinactive.value:
				self.changeSetupPin = getConfigListEntry(_("Change setup pin"), NoSave(ConfigNothing()))
				self.list.append(self.changeSetupPin)
			self.list.append(getConfigListEntry(_("Protect services"), config.ParentalControl.servicepinactive))
			if config.ParentalControl.servicepinactive.value:
				self.list.append(getConfigListEntry(_("Parental control type"), config.ParentalControl.type))
				if config.ParentalControl.mode.value == "complex":
					self.changePin = getConfigListEntry(_("Change service pins"), NoSave(ConfigNothing()))
					self.list.append(self.changePin)
				elif config.ParentalControl.mode.value == "simple":	
					self.changePin = getConfigListEntry(_("Change service pin"), NoSave(ConfigNothing()))
					self.list.append(self.changePin)
				self.list.append(getConfigListEntry(_("Remember service pin"), config.ParentalControl.storeservicepin))	
				self.editListEntry = getConfigListEntry(_("Edit services list"), NoSave(ConfigNothing()))
				self.list.append(self.editListEntry)
				
		self["config"].list = self.list
		self["config"].setList(self.list)
		
	def keyOK(self):
		print "self[\"config\"].l.getCurrentSelection()", self["config"].l.getCurrentSelection()
		if self["config"].l.getCurrentSelection() == self.editListEntry:
			self.session.open(ParentalControlEditor)
		elif self["config"].l.getCurrentSelection() == self.changePin:
			if config.ParentalControl.mode.value == "complex":
				pass
			else:
				self.session.open(ParentalControlChangePin, config.ParentalControl.servicepin[0], _("service pin"))
		elif self["config"].l.getCurrentSelection() == self.changeSetupPin:
			self.session.open(ParentalControlChangePin, config.ParentalControl.setuppin, _("setup pin"))
		else:
			ConfigListScreen.keyRight(self)
			print "current selection:", self["config"].l.getCurrentSelection()
			self.createSetup()
			
	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		print "current selection:", self["config"].l.getCurrentSelection()
		self.createSetup()		
			
	def keyRight(self):
		ConfigListScreen.keyRight(self)
		print "current selection:", self["config"].l.getCurrentSelection()
		self.createSetup()
	
	def keyCancel(self):
		for x in self["config"].list:
			x[1].save()
		self.close()
	
	def keyNumberGlobal(self, number):
		pass

class ParentalControlEditor(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		self.list = []
		self.servicelist = ParentalControlList(self.list)
		self["servicelist"] = self.servicelist;
		
		#self.onShown.append(self.chooseLetter)
		self.currentLetter = ''
		
		self.readServiceList()
		
		self["actions"] = NumberActionMap(["DirectionActions", "ColorActions", "OkCancelActions", "NumberActions"],
		{
			"ok": self.select,
			"cancel": self.cancel,
			"red": self.chooseLetter,
			#"left": self.keyLeft,
			#"right": self.keyRight,
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
		
	def cancel(self):
		parentalControl.save()
		self.close()
		
	def select(self):
		self.servicelist.toggleSelectedLock()
	
	def keyNumberGlobal(self, number):
		pass
	
	def readServiceList(self):
		serviceHandler = eServiceCenter.getInstance()
		refstr = '%s ORDER BY name' % (service_types_tv)
		self.root = eServiceReference(refstr)
		
		self.servicesList = {}
		
		list = serviceHandler.list(self.root)
		if list is not None:
			services = list.getContent("CN", True) #(servicecomparestring, name)
			for s in services:
				if s[1][0]=='\xc2' and s[1][1]=='\x86': # ignore shortname brackets
					key = s[1].lower()[2]
				else:
					key = s[1].lower()[0]
				if key < 'a' or key > 'z':
					key = '&'
				#key = str(key)
				if not self.servicesList.has_key(key):
					self.servicesList[key] = []
				self.servicesList[key].append(s)

	def chooseLetter(self):
		print "choose letter"
		list = []
		for x in self.servicesList.keys():
			if x == '&':
				x = ("special characters", x)
			else:
				x = (x, x)
			list.append(x)
		print "sorted list:", sorted(list, key=operator.itemgetter(1))
		print self.servicesList.keys()
		self.session.openWithCallback(self.letterChosen, ChoiceBox, title=_("Show services beginning with"), list=list)
		
	def letterChosen(self, result):
		if result is not None:
			print "result:", result
			self.currentLetter = result[1]
			self.list = []
			for x in self.servicesList[result[1]]:
				self.list.append(ParentalControlEntryComponent(x[0], x[1], parentalControl.getProtectionLevel(x[0]) != -1))
			self.servicelist.setList(self.list)			

class ParentalControlChangePin(Screen, ConfigListScreen, ProtectedScreen):
	def __init__(self, session, pin, pinname):
		Screen.__init__(self, session)

		self.pin = pin

		self.list = []
		self.pin1 = ConfigPIN(default = 1111, censor = "*")
		self.pin2 = ConfigPIN(default = 1112, censor = "*")
		self.list.append(getConfigListEntry(_("New pin"), NoSave(self.pin1)))
		self.list.append(getConfigListEntry(_("Reenter new pin"), NoSave(self.pin2)))
		ConfigListScreen.__init__(self, self.list)
		
#		print "old pin:", pin
		#if pin.value != "aaaa":
			#self.onFirstExecBegin.append(boundFunction(self.session.openWithCallback, self.pinEntered, PinInput, pinList = [self.pin.value], title = _("please enter the old pin"), windowTitle = _("Change pin code")))
		ProtectedScreen.__init__(self)
		
		self["actions"] = NumberActionMap(["DirectionActions", "ColorActions", "OkCancelActions"],
		{
			"cancel": self.cancel,
		}, -1)
		
	def getPinText(self):
		return _("Please enter the old pin code")

	def isProtected(self):
		return (self.pin.value != "aaaa")

	def protectedWithPin(self):
		return self.pin.value
		
#	def pinEntered(self, result):
		#if result[0] is None:
			#self.close()
		#if not result[0]:
			#print result, "-", self.pin.value
			#self.session.openWithCallback(self.close, MessageBox, _("The pin code you entered is wrong."), MessageBox.TYPE_ERROR)
	
	def keyOK(self):
		if self.pin1.value == self.pin2.value:
			self.pin.value = self.pin1.value
			self.pin.save()
			self.session.openWithCallback(self.close, MessageBox, _("The pin code has been changed successfully."), MessageBox.TYPE_INFO)
		else:
			self.session.open(MessageBox, _("The pin codes you entered are different."), MessageBox.TYPE_ERROR)
	
	def cancel(self):
		self.close(None)
	
	def keyNumberGlobal(self, number):
		ConfigListScreen.keyNumberGlobal(self, number)
		

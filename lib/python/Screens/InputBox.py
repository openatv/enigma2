from enigma import *
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import NumberActionMap
from Components.Label import Label
from Components.Input import Input
from Components.GUIComponent import *
from Tools.BoundFunction import boundFunction

import os

class InputBox(Screen):
	def __init__(self, session, title = "", windowTitle = _("Input"), **kwargs):
		Screen.__init__(self, session)

		self["text"] = Label(title)
		self["input"] = Input(**kwargs)
		self.onShown.append(boundFunction(self.setTitle, windowTitle))

		self["actions"] = NumberActionMap(["WizardActions", "InputBoxActions", "InputAsciiActions", "KeyboardInputActions"], 
		{
			"gotAsciiCode": self.gotAsciiCode,
			"ok": self.go,
			"back": self.cancel,
			"left": self.keyLeft,
			"right": self.keyRight,
			"delete": self.keyDelete,
			"moveLeft": self.keyLeft,
			"moveRight": self.keyRight,
			"moveHome": self.keyHome,
			"moveEnd": self.keyEnd,
			"deleteForward": self.keyDelete,
			"deleteBackward": self.keyBackspace,
			"tab": self.keyTab,
			"toggleOverwrite": self.keyInsert,
			"accept": self.go,
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
		rcinput = eRCInput.getInstance()
		rcinput.setKeyboardMode(rcinput.kmAscii)

	def gotAsciiCode(self):
		self["input"].handleAscii(getPrevAsciiCode())

	def keyLeft(self):
		self["input"].left()

	def keyRight(self):
		self["input"].right()

	def keyNumberGlobal(self, number):
		self["input"].number(number)

	def keyDelete(self):
		self["input"].delete()

	def go(self):
		rcinput = eRCInput.getInstance()
		rcinput.setKeyboardMode(rcinput.kmNone)
		self.close(self["input"].getText())

	def cancel(self):
		rcinput = eRCInput.getInstance()
		rcinput.setKeyboardMode(rcinput.kmNone)
		self.close(None)

	def keyHome(self):
		self["input"].home()

	def keyEnd(self):
		self["input"].end()

	def keyBackspace(self):
		self["input"].deleteBackward()

	def keyTab(self):
		self["input"].tab()

	def keyInsert(self):
		self["input"].toggleOverwrite()

class PinInput(InputBox):
	def __init__(self, session, service = "", tries = 1, pinList = [], *args, **kwargs):
		InputBox.__init__(self, session = session, text="9876", maxSize=True, type=Input.PIN, *args, **kwargs)
		
		self.showTries = True
		if tries == 1:
			self.showTries = False

		self.pinList = pinList
		self["service"] = Label(service)
		
		self["tries"] = Label("")
		self.onShown.append(boundFunction(self.setTries, tries))
				
	def keyNumberGlobal(self, number):
		if self["input"].currPos == len(self["input"]) - 1:
			InputBox.keyNumberGlobal(self, number)
			self.go()
		else:
			InputBox.keyNumberGlobal(self, number)
		
	def checkPin(self, pin):
		if pin is not None and int(pin) in self.pinList:
			return True
		return False
		
	def go(self):
		if self.checkPin(self["input"].getText()):
			self.close((True, self.tries))
		else:
			self.keyHome()
			self.setTries(self.tries - 1)
			if self.tries == 0:
				self.close((False, self.tries))
			else:
				pass
			
	def cancel(self):
		rcinput = eRCInput.getInstance()
		rcinput.setKeyboardMode(rcinput.kmNone)
		self.close((None, self.tries))
	
	def setTries(self, tries):
		self.tries = tries
		if self.showTries:
			self["tries"].setText(_("Tries left:") + " " + str(tries))
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import NumberActionMap
from Components.Input import Input
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.config import config, ConfigInteger
from SleepTimer import SleepTimer

config.SleepTimer.defaulttime = ConfigInteger(default = 30)

class SleepTimerEdit(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		
		self["red"] = Pixmap()
		self["green"] = Pixmap()
		self["yellow"] = Pixmap()
		self["blue"] = Pixmap()
		self["red_text"] = Label()
		self["green_text"] = Label()
		self["yellow_text"] = Label()
		self["blue_text"] = Label()
		self["current_status"] = Label()
		self.is_active = self.session.nav.SleepTimer.isActive()
		if self.is_active:
			self["current_status"].setText(_("Timer status:") + " " + _("Enabled"))
		else:
			self["current_status"].setText(_("Timer status:") + " " + _("Disabled"))
		
		if self.is_active:
			self.time = self.session.nav.SleepTimer.getCurrentSleepTime()
		else:
			self.time = config.SleepTimer.defaulttime.value
		self["input"] = Input(text = str(self.time), maxSize = False, type = Input.NUMBER)
		
		self.status = True
		self.updateColors()
		
		
		self["pretext"] = Label(_("Shutdown Dreambox after"))
		self["aftertext"] = Label(_("minutes"))
		
		self["actions"] = NumberActionMap(["SleepTimerEditorActions", "TextEntryActions", "KeyboardInputActions"], 
		{
			"exit": self.cancel,
			"select": self.select,
			"1": self.keyNumberGlobal,
			"2": self.keyNumberGlobal,
			"3": self.keyNumberGlobal,
			"4": self.keyNumberGlobal,
			"5": self.keyNumberGlobal,
			"6": self.keyNumberGlobal,
			"7": self.keyNumberGlobal,
			"8": self.keyNumberGlobal,
			"9": self.keyNumberGlobal,
			"0": self.keyNumberGlobal,
			"selectLeft": self.selectLeft,
			"selectRight": self.selectRight,
			"left": self.selectLeft,
			"right": self.selectRight,
			"home": self.selectHome,
			"end": self.selectEnd,
			"deleteForward": self.deleteForward,
			"deleteBackward": self.deleteBackward,
			"disableTimer": self.disableTimer,
			"toggleAction": self.toggleAction,
			"toggleAsk": self.toggleAsk
		}, -1)

	def updateColors(self):
		if self.status:
			self["red_text"].setText(_("Action:") + " " + _("Enable timer"))
		else:
			self["red_text"].setText(_("Action:") + " " + _("Disable timer"))
		
		if config.SleepTimer.action.value == "shutdown":
			self["green_text"].setText(_("Sleep timer action:") + " " + _("Deep Standby"))
		elif config.SleepTimer.action.value == "standby":
			self["green_text"].setText(_("Sleep timer action:") + " " + _("Standby"))
		
		if config.SleepTimer.ask.value:
			self["yellow_text"].setText(_("Ask before shutdown:") + " " + _("yes"))
		else:
			self["yellow_text"].setText(_("Ask before shutdown:") + " " + _("no"))
		self["blue_text"].setText(_("Settings"))

	def cancel(self):
		config.SleepTimer.ask.cancel()
		config.SleepTimer.action.cancel()
		self.close()

	def select(self):
		if self.status:
			time = int(self["input"].getText())
			config.SleepTimer.defaulttime.setValue(time)
			self.session.nav.SleepTimer.setSleepTime(time)
			self.session.openWithCallback(self.close, MessageBox, _("The sleep timer has been activated."), MessageBox.TYPE_INFO)
		else:
			self.session.nav.SleepTimer.clear()
			self.session.openWithCallback(self.close, MessageBox, _("The sleep timer has been disabled."), MessageBox.TYPE_INFO)

	def keyNumberGlobal(self, number):
		self["input"].number(number)

	def selectLeft(self):
		self["input"].left()

	def selectRight(self):
		self["input"].right()

	def selectHome(self):
		self["input"].home()
	
	def selectEnd(self):
		self["input"].end()
	
	def deleteForward(self):
		self["input"].delete()
	
	def deleteBackward(self):
		self["input"].deleteBackward()
	
	def disableTimer(self):
		self.status = not self.status
		self.updateColors()

	def toggleAction(self):
		if config.SleepTimer.action.value == "shutdown":
			config.SleepTimer.action.value = "standby"
		elif config.SleepTimer.action.value == "standby":
			config.SleepTimer.action.value = "shutdown"
		self.updateColors()

	def toggleAsk(self):
		config.SleepTimer.ask.value = not config.SleepTimer.ask.value
		self.updateColors()

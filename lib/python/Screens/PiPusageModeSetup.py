from Screens.Screen import Screen
from Components.ActionMap import NumberActionMap, ActionMap
from Components.Label import Label
from Components.config import config, configfile, ConfigSelection

class PiPusageModeSetup(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		
		self.choicelist = [("standard", _("Standard")), ("noadspip", _("Ads filtering mode")), ("byside", _("Side by side mode"))]
		config.usage.pip_mode = ConfigSelection(default = "standard", choices = self.choicelist)

		self.mode = self.getMode()
		self.orgmode = self.mode

		self.helptext = _("OK - go back to the TV mode  |  EXIT - cancel  |   <  >  -  change usage mode")
		self.modetext = _("PiP mode") + ":   %s"

		self.setTitle(_("PiPSetup"))
		self["text"] = Label(self.modetext % self.getModeName())
		self["text_desc"] = Label(self.helptext)

		self["actions"] = ActionMap(["PiPusageModeSetupActions"],
		{
			"ok": self.go,
			"cancel": self.cancel,
			"left": self.left,
			"right": self.right
		}, -1)

	def go(self):
		self.close()

	def cancel(self):
		self.mode = self.orgmode
		self.setMode(self.mode)
		self.close()

	def left(self):
		self.togglePiPMode(False)
		self.mode = self.getMode()
		self["text"].setText((self.modetext % self.getModeName()))

	def right(self):
		self.togglePiPMode(True)
		self.mode = self.getMode()
		self["text"].setText((self.modetext % self.getModeName()))

	def getMode(self):
		return config.usage.pip_mode.value

	def getModeName(self):
		return self.choicelist[config.usage.pip_mode.index][1]
		
	def setMode(self, mode):
		config.usage.pip_mode.value = mode
		config.usage.pip_mode.save()
		configfile.save()
		
	def togglePiPMode(self, mod=True):
		if mod:
			self.setMode(config.usage.pip_mode.choices[(config.usage.pip_mode.index + 1) % len(config.usage.pip_mode.choices)])
		else:
			self.setMode(config.usage.pip_mode.choices[(config.usage.pip_mode.index - 1) % len(config.usage.pip_mode.choices)])


from Screens.Screen import Screen
from Components.ActionMap import NumberActionMap, ActionMap
from Components.Label import Label
from Components.config import config, configfile, ConfigSelection, ConfigInteger
from time import time

class MyPiPmode(Screen):
	skin = """<screen name="MyPiPmode" position="center,center" size="700,160" backgroundColor="transparent" zPosition="2">
		<widget name="text" position="0,0" size="700,100" font="Regular;22" foregroundColor="white" backgroundColor="black" zPosition="2" halign="center" valign="center" />
		<widget name="text_desc" position="0,100" size="700,60" font="Regular;20" foregroundColor="white" backgroundColor="black" zPosition="2" halign="center" />
	</screen>"""

class PiPusageModeSetup(Screen):
	def __init__(self, session):
		self.skin = MyPiPmode.skin
		Screen.__init__(self, session)
		self.skinName = "MyPiPmode"
		
		self.choicelist = [("standard", _("Standard")), ("noadspip", _("Ads filtering mode")), ("byside", _("Side by side mode"))]
		config.usage.pip_mode = ConfigSelection(default = "standard", choices = self.choicelist)
		
		self.usageModeChecking()

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
		config.usage.pip_lastusage = ConfigInteger(default = int(time()))
		config.usage.pip_lastusage.setValue(int(time())+1000)
		config.usage.pip_lastusage.save()
		configfile.save()
		self.close()

	def cancel(self):
		self.mode = self.orgmode
		self.setMode(self.mode)
		self.go()

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
			
	def usageModeChecking(self):
		try:
			config.usage.noadspip_default_mode_time = ConfigSelection(default = "180", choices = [
				("0", _("Setting by user")), ("180", _("After 3 minutes")), ("300", _("After 5 minutes")), ("1800", _("After 30 minutes")) ])
			config.usage.pip_lastusage = ConfigInteger(default = int(time()))
			if config.usage.noadspip_default_mode_time.value == "0":
				return
			time_config = int(config.usage.pip_lastusage.value)
			time_now = int(time())
			diff_time = time_now - time_config
			if diff_time > int(config.usage.noadspip_default_mode_time.value):
				config.usage.pip_mode.setValue('noadspip')
				config.usage.pip_mode.save()
				configfile.save()
		except:
			return
		
	def setMode(self, mode):
		config.usage.pip_mode.value = mode
		config.usage.pip_mode.save()
		configfile.save()
		
	def togglePiPMode(self, mod=True):
		if mod:
			self.setMode(config.usage.pip_mode.choices[(config.usage.pip_mode.index + 1) % len(config.usage.pip_mode.choices)])
		else:
			self.setMode(config.usage.pip_mode.choices[(config.usage.pip_mode.index - 1) % len(config.usage.pip_mode.choices)])


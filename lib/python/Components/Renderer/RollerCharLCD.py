from enigma import eLabel, eTimer

from Components.config import config
from Components.SystemInfo import BoxInfo
from Components.VariableText import VariableText
from Components.Renderer.Renderer import Renderer


class RollerCharLCD(VariableText, Renderer):
	GUI_WIDGET = eLabel

	def __init__(self):
		Renderer.__init__(self)
		VariableText.__init__(self)
		self.moveTimerText = eTimer()
		self.moveTimerText.callback.append(self.moveTimerTextRun)
		self.delayTimer = eTimer()
		self.delayTimer.callback.append(self.delayTimergo)
		self.stringlength = 16 if BoxInfo.getItem("machinebuild") in ("vuduo", "sf4008", "beyonwizu4") else 12

	def connect(self, source):
		Renderer.connect(self, source)
		self.changed((self.CHANGED_DEFAULT,))

	def changed(self, what):
		self.moveTimerText.stop()
		self.delayTimer.stop()
		if what[0] == self.CHANGED_CLEAR:
			self.text = ""
		else:
			self.text = self.source.text
		if len(self.text) > self.stringlength:
			self.text = self.source.text + " " * self.stringlength + self.source.text[:self.stringlength + 1]
			self.x = len(self.text) - self.stringlength
			self.idx = 0
			self.backtext = self.text
			self.moveTimerText.start(2000)
		else:
			self.text = self.source.text
			self.x = len(self.text)
			self.idx = 0
			self.backtext = self.text

	def moveTimerTextRun(self):
		self.moveTimerText.stop()
		if self.x > 0:
			txttmp = self.backtext[self.idx:]
			self.text = txttmp[:self.stringlength]
			self.idx += 1
			self.x -= 1
		if self.x == 0:
			self.text = self.backtext
			if config.lcd.scrollDelay.value:
				self.delayTimer.start(config.lcd.scrollDelay.value * 1000, True)
		else:
			self.moveTimerText.start(config.lcd.scrollSpeed.value)

	def delayTimergo(self):
		self.delayTimer.stop()
		self.changed((self.CHANGED_DEFAULT,))

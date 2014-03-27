from Components.config import config
from Renderer import Renderer
from enigma import eLabel, eTimer
from boxbranding import getBoxType
from Components.VariableText import VariableText

class RollerCharLCD(VariableText, Renderer):

	def __init__(self):
		Renderer.__init__(self)
		VariableText.__init__(self)
		if getBoxType() == 'vuduo':
			self.stringlength = 16
		else:
			self.stringlength = 12

	GUI_WIDGET = eLabel

	def connect(self, source):
		Renderer.connect(self, source)
		self.changed((self.CHANGED_DEFAULT,))

	def changed(self, what):
		if what[0] == self.CHANGED_CLEAR:
			self.text = ''
		else:
			self.text = self.source.text
		if len(self.text) > self.stringlength:
			self.text = self.source.text + ' ' * self.stringlength + self.source.text[:self.stringlength + 1]
			self.x = len(self.text) - self.stringlength
			self.idx = 0
			self.backtext = self.text
			self.status = 'start'
			self.moveTimerText = eTimer()
			self.moveTimerText.timeout.get().append(self.moveTimerTextRun)
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
			self.status = 'end'
			self.text = self.backtext
		if self.status != 'end':
			self.scrollspeed = int(config.lcd.scroll_speed.value)
			self.moveTimerText.start(self.scrollspeed)
		if config.lcd.scroll_delay.value != 'noscrolling':
			self.scrolldelay = int(config.lcd.scroll_delay.value)
			self.delayTimer = eTimer()
			self.delayTimer.timeout.get().append(self.delayTimergo)
			self.delayTimer.start(self.scrolldelay)

	def delayTimergo(self):
		self.delayTimer.stop()
		self.changed((self.CHANGED_DEFAULT,))
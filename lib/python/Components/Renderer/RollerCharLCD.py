from Components.config import config
from Renderer import Renderer
from enigma import eLabel, eTimer
from Components.VariableText import VariableText

class RollerCharLCD(VariableText, Renderer):
	SCROLL_START_DELAY = 2000

	def __init__(self):
		Renderer.__init__(self)
		VariableText.__init__(self)
		self.spacewidth = None
		self.width = None
		self.padding = None
		self.origtext = self.text
		self.textwidth = None

	GUI_WIDGET = eLabel

	def connect(self, source):
		Renderer.connect(self, source)
		self.changed((self.CHANGED_DEFAULT,))

	def changed(self, what):
		if self.instance is None:
			return

		if self.spacewidth is None:
			self.text = ' '
			self.spacewidth = max(self.instance.calculateSize().width(), 5)
		if self.width is None:
			self.width = self.instance.size().width()
			self.padding = (self.width + self.spacewidth - 1) / self.spacewidth
		if what[0] == self.CHANGED_CLEAR:
			self.origtext = ''
		else:
			self.origtext = self.source.text
		if self.textwidth is None or self.origtext != self.text:
			self.text = self.origtext
			self.textwidth = self.instance.calculateSize().width()

		# self.textwidth can't be greater than self.width, so we're
		# forced to use a test that will scroll when the text
		# fits exactly

		if self.textwidth >= self.width:
			self.text = self.origtext + ' ' * self.padding + self.origtext
			self.x = len(self.origtext) + self.padding
			self.idx = 0
			self.status = 'start'
			self.moveTimerText = eTimer()
			self.moveTimerText.timeout.get().append(self.moveTimerTextRun)
			self.moveTimerText.start(self.SCROLL_START_DELAY)
		else:
			self.x = len(self.text)
			self.idx = 0
		self.backtext = self.text

	def moveTimerTextRun(self):
		self.moveTimerText.stop()
		if self.x > 0:
			self.text = self.backtext[self.idx:]
			self.idx += 1
			self.x -= 1
		if self.x == 0:
			self.status = 'end'
			self.text = self.origtext
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

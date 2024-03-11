from enigma import eTimer

from Components.Converter.Converter import Converter


class ConditionalShowHide(Converter):
	def __init__(self, tokens):
		Converter.__init__(self, tokens)
		tokenDictionary = {
			"Blink": ("blink", True),
			"Invert": ("invert", True)
		}
		self.blink = False
		self.invert = False
		self.blinkTime = 500
		parse = ","
		tokens.replace(";", parse)  # Some builds use ";" as a separator, most use ",".
		tokens = [x.strip() for x in tokens.split(parse)]
		for token in tokens:
			if token.isdigit():
				self.blinkTime = int(token)
				continue
			variable, value = tokenDictionary.get(token, (None, None))
			if variable:
				setattr(self, variable, value)
			elif token:
				print(f"[ConditionalShowHide] Error: Converter argument '{token}' is invalid!")
		if self.blink:
			self.timer = eTimer()
			self.timer.callback.append(self.blinker)
		else:
			self.timer = None
		# print(f"[ConditionalShowHide] DEBUG: Converter init {tokens} result is blink={self.blink}, invert={self.invert}, blinkTime={self.blinkTime}.")

	def __getattr__(self, name):  # Make ConditionalShowHide transparent to upstream attribute requests.
		return getattr(self.source, name)

	def blinker(self):
		if self.blinking:
			for element in self.downstream_elements:
				element.visible = not element.visible

	def startBlinking(self):
		self.blinking = True
		self.timer.start(self.blinkTime)

	def stopBlinking(self):
		self.blinking = False
		self.timer.stop()
		for element in self.downstream_elements:
			if element.visible:
				element.hide()

	def calcVisibility(self):
		visibility = self.source.boolean
		if visibility is None:
			visibility = False
		visibility ^= self.invert
		return visibility

	def changed(self, what):
		visibility = self.calcVisibility()
		if self.blink:
			if visibility:
				self.startBlinking()
			else:
				self.stopBlinking()
		else:
			for element in self.downstream_elements:
				element.visible = visibility
		super(Converter, self).changed(what)

	def connectDownstream(self, downstream):
		Converter.connectDownstream(self, downstream)
		visibility = self.calcVisibility()
		if self.blink:
			if visibility:
				self.startBlinking()
			else:
				self.stopBlinking()
		else:
			downstream.visible = self.calcVisibility()

	def destroy(self):
		if self.timer:
			self.timer.callback.remove(self.blinker)

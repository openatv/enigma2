#
# ConverterRotator Converter for Enigma2 (ConverterRotator.py)
# Coded by vlamo (c) 2012
#
# Version: 0.1 (26.01.2012 04:05)
# Support: http://dream.altmaster.net/
#
from Components.Converter.Converter import Converter
from Components.Converter.Poll import Poll
from Components.Element import cached


class ConverterRotator(Poll, Converter):
	"""Static Text Converter Rotator"""

	def __init__(self, tokens):
		Poll.__init__(self)
		Converter.__init__(self, tokens)
		self.mainstream = None
		self.sourceList = []
		self.sourceIndex = -1
		if tokens and tokens.isdigit():
			self.poll_interval = int(tokens) * 1000

	def changed(self, what, parent=None):
		if what[0] == self.CHANGED_DEFAULT and not len(self.sourceList):
			upstream = self.source
			while upstream:
				self.sourceList.insert(0, (upstream, hasattr(upstream, "poll_enabled")))
				upstream = upstream.source
			if len(self.sourceList):
				self.mainstream = self.sourceList.pop(0)[0]
		self.downstream_elements.changed(what)

	def doSuspend(self, suspended):
		if self.mainstream and len(self.sourceList) != 0:
			if suspended:
				self.poll_enabled = False
			else:
				self.sourceIndex = len(self.sourceList) - 1
				self.poll_enabled = True
				self.poll()

	@cached
	def getText(self):
		result = ""
		if self.poll_enabled:
			prevSource = self.sourceList[self.sourceIndex][0].source
			self.sourceList[self.sourceIndex][0].source = self.mainstream
			result = self.sourceList[self.sourceIndex][0].text or ""
			self.sourceList[self.sourceIndex][0].source = prevSource
		return result

	text = property(getText)

	def poll(self):
		self.sourceIndex = (self.sourceIndex + 1) % len(self.sourceList)
		self.downstream_elements.changed((self.CHANGED_POLL,))

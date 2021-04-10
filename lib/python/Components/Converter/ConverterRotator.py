#
# ConverterRotator Converter for Enigma2 (ConverterRotator.py)
# Coded by vlamo (c) 2012
#
# Version: 0.1 (26.01.2012 04:05)
# Support: http://dream.altmaster.net/
#
from Converter import Converter
from Poll import Poll
from Components.Element import cached


class ConverterRotator(Poll, Converter, object):
	"""Static Text Converter Rotator"""

	def __init__(self, type):
		Poll.__init__(self)
		Converter.__init__(self, type)
		self.mainstream = None
		self.sourceList = []
		self.sourceIndex = -1
		if type and type.isdigit():
			self.poll_interval = int(type) * 1000

	def poll(self):
		self.sourceIndex = (self.sourceIndex + 1) % len(self.sourceList)
		self.downstream_elements.changed((self.CHANGED_POLL,))

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
			prev_source = self.sourceList[self.sourceIndex][0].source
			self.sourceList[self.sourceIndex][0].source = self.mainstream
			result = self.sourceList[self.sourceIndex][0].text or ""
			self.sourceList[self.sourceIndex][0].source = prev_source
		return result

	text = property(getText)

	def changed(self, what, parent=None):
		if what[0] == self.CHANGED_DEFAULT and not len(self.sourceList):
			upstream = self.source
			while upstream:
				self.sourceList.insert(0, (upstream, hasattr(upstream, 'poll_enabled')))
				upstream = upstream.source
			if len(self.sourceList):
				self.mainstream = self.sourceList.pop(0)[0]
		#if what[0] == self.CHANGED_POLL and \
		#   self.poll_enabled and \
		#   not self.sourceList[self.sourceIndex][1]:
		#	return
		self.downstream_elements.changed(what)

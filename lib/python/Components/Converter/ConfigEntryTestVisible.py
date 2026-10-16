from Components.Converter.ConfigEntryTest import ConfigEntryTest
from Components.Converter.Converter import Converter


class ConfigEntryTestVisible(ConfigEntryTest):
	def __init__(self, tokens):
		ConfigEntryTest.__init__(self, tokens)

	def changed(self, what):
		visibility = self.getBoolean()
		for element in self.downstream_elements:
			element.visible = visibility
		super(Converter, self).changed(what)

	def connectDownstream(self, downstream):
		Converter.connectDownstream(self, downstream)
		downstream.visible = self.getBoolean()

	def __getattr__(self, name):  # Make ConfigEntryTestVisible transparent to upstream attribute requests.
		return getattr(self.source, name)

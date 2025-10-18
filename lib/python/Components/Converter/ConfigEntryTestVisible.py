from Components.Converter.Converter import Converter
from Components.Converter.ConfigEntryTest import ConfigEntryTest


class ConfigEntryTestVisible(ConfigEntryTest):
	def __init__(self, args):
		ConfigEntryTest.__init__(self, args)

	def __getattr__(self, name):  # Make ConfigEntryTestVisible transparent to upstream attribute requests.
		return getattr(self.source, name)

	def changed(self, what):
		visibility = self.getBoolean()
		for element in self.downstream_elements:
			element.visible = visibility
		super(Converter, self).changed(what)

	def connectDownstream(self, downstream):
		Converter.connectDownstream(self, downstream)
		downstream.visible = self.getBoolean()

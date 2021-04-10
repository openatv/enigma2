from Components.Element import Element


class Converter(Element):
	def __init__(self, arguments):
		Element.__init__(self)
		self.converter_arguments = arguments

	def __repr__(self):
		return str(type(self)) + "(" + self.converter_arguments + ")"

	def handleCommand(self, cmd):
		self.source.handleCommand(cmd)

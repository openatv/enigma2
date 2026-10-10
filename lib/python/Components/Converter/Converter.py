from Components.Element import Element


class Converter(Element):
	def __init__(self, tokens):
		Element.__init__(self)
		self.converter_arguments = tokens

	def handleCommand(self, cmd):
		self.source.handleCommand(cmd)

	def __repr__(self):
		return f"{str(type(self))}({self.converter_arguments})"

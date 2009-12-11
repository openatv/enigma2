from Components.Converter.Converter import Converter

class SensorToText(Converter, object):
	def __init__(self, arguments):
		Converter.__init__(self, arguments)
        
	def getText(self):
		if self.source.getValue() is None:
			return ""
		return "%d %s" % (self.source.getValue(), self.source.getUnit())
	
	text = property(getText)
        
        
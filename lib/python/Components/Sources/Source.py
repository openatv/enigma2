from Components.Element import Element

class Source(Element):
	def execBegin(self):
		pass

	def execEnd(self):
		pass

	def onShow(self):
		pass

	def onHide(self):
		pass

	def destroy(self):
		self.__dict__.clear()

class ObsoleteSource(Source):
	def __init__(self, new_source, description = None, removal_date = "as soon as possible"):
		self.new_source = new_source
		self.description = description
		self.removal_date = removal_date

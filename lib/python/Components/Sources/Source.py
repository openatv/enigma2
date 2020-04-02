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
	def __init__(self, newSource, description=None, removalDate="AS SOON AS POSSIBLE"):
		self.newSource = newSource
		self.description = description
		self.removalDate = removalDate

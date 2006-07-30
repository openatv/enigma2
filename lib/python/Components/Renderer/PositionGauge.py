from Renderer import Renderer
from enigma import ePositionGauge

class PositionGauge(Renderer):
	def __init__(self):
		Renderer.__init__(self)
		self.__position = 0
		self.__length = 0
		self.__cutlist = [ ]
	
	GUI_WIDGET = ePositionGauge
	
	def postWidgetCreate(self, instance):
		self.changed((self.CHANGED_DEFAULT,))
		self.cutlist_changed()
		instance.setInOutList(self.__cutlist)

	def changed(self, what):
		if what[0] == self.CHANGED_CLEAR:
			(self.length, self.position) = 0
		else:
			(self.length, self.position) = (self.source.length or 0, self.source.position or 0)

	def cutlist_changed(self):
		self.cutlist = self.source.cutlist or [ ]

	def getPosition(self):
		return self.__position
	
	def setPosition(self, pos):
		self.__position = pos
		if self.instance is not None:
			self.instance.setPosition(pos)
	
	position = property(getPosition, setPosition)

	def getLength(self):
		return self.__length
	
	def setLength(self, len):
		self.__length = len
		if self.instance is not None:
			self.instance.setLength(len)

	length = property(getLength, setLength)

	def getCutlist(self):
		return self.__cutlist
	
	def setCutlist(self, cutlist):
		self.__cutlist = cutlist
		if self.instance is not None:
			self.instance.setInOutList(cutlist)

	cutlist = property(getCutlist, setCutlist)

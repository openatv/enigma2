import skin

from enigma import ePoint

class GUIComponent(object):
	""" GUI component """
	
	def __init__(self):
		self.instance = None
		self.visible = 1
	
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
	
	# this works only with normal widgets - if you don't have self.instance, override this.
	def applySkin(self, desktop):
		if not self.visible:
			self.instance.hide()
		skin.applyAllAttributes(self.instance, desktop, self.skinAttributes)

	def move(self, x, y):
		self.instance.move(ePoint(int(x), int(y)))

	def show(self):
		self.__visible = 1
		if self.instance is not None:
			self.instance.show()

	def hide(self):
		self.__visible = 0
		if self.instance is not None:
			self.instance.hide()

	def getVisible(self):
		return self.__visible
	
	def setVisible(self, visible):
		if visible:
			self.show()
		else:
			self.hide()

	visible = property(getVisible, setVisible)

	def setPosition(self, x, y):
		self.instance.move(ePoint(int(x), int(y)))

	def getPosition(self):
		p = self.instance.position()
		return (p.x(), p.y())

	position = property(getPosition, setPosition)

	# default implementation for only one widget per component
	# feel free to override!
	def GUIcreate(self, parent):
		self.instance = self.createWidget(parent)
		self.postWidgetCreate(self.instance)
	
	def GUIdelete(self):
		self.preWidgetRemove(self.instance)
		self.instance = None

	# default for argumentless widget constructor
	def createWidget(self, parent):
		return self.GUI_WIDGET(parent)

	def postWidgetCreate(self, instance):
		pass
	
	def preWidgetRemove(self, instance):
		pass

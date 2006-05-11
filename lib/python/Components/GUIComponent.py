import skin

from enigma import ePoint

class GUIComponent(object):
	""" GUI component """
	
	SHOWN = 0
	HIDDEN = 1
	
	def __init__(self):
		self.instance = None
		self.state = self.SHOWN
	
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
		if self.state == self.HIDDEN:
			self.instance.hide()
		skin.applyAllAttributes(self.instance, desktop, self.skinAttributes)

	def move(self, x, y):
		self.instance.move(ePoint(int(x), int(y)))

	def show(self):
		self.__state = self.SHOWN
		if self.instance is not None:
			self.instance.show()

	def hide(self):
		self.__state = self.HIDDEN
		if self.instance is not None:
			self.instance.hide()

	def getState(self):
		return self.__state
	
	def setState(self, state):
		if state == self.SHOWN:
			self.show()
		elif state == self.HIDDEN:
			self.hide()

	state = property(getState, setState)

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

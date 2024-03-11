from enigma import ePoint, eSize

from skin import applyAllAttributes


class GUIComponent:
	"""GUI Component."""

	def __init__(self):
		self.onVisibilityChange = []
		self.instance = None
		self.visiblity = False
		self.visible = True
		self.skinAttributes = None
		self.deprecationInfo = None

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

	def applySkin(self, desktop, parent):  # This only works with normal widgets, if you don't have a self.instance override this method.
		if not self.visible:
			self.instance.hide()
		if self.skinAttributes is None:
			result = False
		else:
			# // Workaround for values from attributes the not be set.
			#
			# The order of some attributes is crucial if they are applied. Also, an attribute may be responsible that another does not take effect and occurs at different skins.
			# It was noticed at "scrollbarSliderBorderWidth" and "scrollbarSliderForegroundColor".
			#
			# if config.skin.primary_skin.value.split("/")[0] not in ("DMConcinnity-HD"):
			# 	self.skinAttributes.sort()
			#
			# NOTE: The code above is invalid. It always returns False! It is being removed until it's need is confirmed.
			# To be correct the code could/should be one of, depending on the original intention:
			# 	if config.skin.primary_skin.value.split("/")[0] != "DMConcinnity-HD":
			# 	if config.skin.primary_skin.value.split("/")[0] == "DMConcinnity-HD":
			#
			# //
			applyAllAttributes(self.instance, desktop, self.skinAttributes, parent.scale)
			result = True
		return result

	def move(self, xPos, yPos=None):  # Assuming that xPos is already an ePoint.
		self.instance.move(xPos if yPos is None else ePoint(int(xPos), int(yPos)))

	def resize(self, width, height=None):
		self.width = width
		self.height = height
		self.instance.resize(width if height is None else eSize(int(width), int(height)))

	def setZPosition(self, zPosition):
		self.instance.setZPosition(zPosition)

	def show(self):
		current = self.visiblity
		self.visiblity = True
		if self.instance is not None:
			self.instance.show()
		if current != self.visiblity:
			for callback in self.onVisibilityChange:
				callback(True)

	def hide(self):
		current = self.visiblity
		self.visiblity = False
		if self.instance is not None:
			self.instance.hide()
		if current != self.visiblity:
			for callback in self.onVisibilityChange:
				callback(False)

	def getVisible(self):
		return self.visiblity

	def setVisible(self, visible):
		if visible:
			self.show()
		else:
			self.hide()

	visible = property(getVisible, setVisible)

	def setPosition(self, xPos, yPos):
		self.instance.move(ePoint(int(xPos), int(yPos)))

	def getPosition(self):
		position = self.instance.position()
		return position.x(), position.y()

	def getWidth(self):
		return self.width

	def getHeight(self):
		return self.height

	position = property(getPosition)

	def GUIcreate(self, parent):  # Default implementation for only one widget per component.  Feel free to override!
		self.instance = self.createWidget(parent)
		self.postWidgetCreate(self.instance)

	def GUIdelete(self):
		self.preWidgetRemove(self.instance)
		self.instance = None

	def createWidget(self, parent):  # Default for argument less widget constructor.
		return self.GUI_WIDGET(parent)

	def postWidgetCreate(self, instance):
		pass

	def preWidgetRemove(self, instance):
		pass

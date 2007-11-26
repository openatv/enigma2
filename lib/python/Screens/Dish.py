from Screen import Screen

from Components.BlinkingPixmap import BlinkingPixmapConditional
from Components.Pixmap import Pixmap
from Components.config import config

from enigma import eDVBSatelliteEquipmentControl

class Dish(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self["Dishpixmap"] = BlinkingPixmapConditional()
		self["Dishpixmap"].onVisibilityChange.append(self.DishpixmapVisibilityChanged)
		#self["Dishpixmap"] = Pixmap()
		config.usage.showdish.addNotifier(self.configChanged)
		self.configChanged(config.usage.showdish)

	def configChanged(self, configElement):
		if not configElement.value:
			self["Dishpixmap"].setConnect(lambda: False)
		else:
			self["Dishpixmap"].setConnect(eDVBSatelliteEquipmentControl.getInstance().isRotorMoving)

	def DishpixmapVisibilityChanged(self, state):
		if state:
			self.show() # show complete screen
		else:
			self.hide() # hide complete screen

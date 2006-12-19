from Screen import Screen

from Components.BlinkingPixmap import BlinkingPixmapConditional
from Components.Pixmap import Pixmap
from Components.Button import Button
from Components.config import config

from enigma import eDVBSatelliteEquipmentControl

class Dish(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		
		self["transparent"] = Button("")
		self["Dishpixmap"] = BlinkingPixmapConditional()
		#self["Dishpixmap"] = Pixmap()
		if not config.usage.showdish.value:
			self["Dishpixmap"].setConnect(lambda: False)
		else:
			self["Dishpixmap"].setConnect(eDVBSatelliteEquipmentControl.getInstance().isRotorMoving)

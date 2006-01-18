from Screen import Screen

from Components.BlinkingPixmap import BlinkingPixmapConditional
from Components.Pixmap import Pixmap
from Components.Button import Button
from Components.config import config, currentConfigSelectionElement

from enigma import *

class Dish(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		
		self["transparent"] = Button("")
		self["Dishpixmap"] = BlinkingPixmapConditional()
		#self["Dishpixmap"] = Pixmap()
		if currentConfigSelectionElement(config.usage.showdish) == "no":
			self["Dishpixmap"].setConnect(lambda: False)
		else:
			self["Dishpixmap"].setConnect(eDVBSatelliteEquipmentControl.getInstance().isRotorMoving)

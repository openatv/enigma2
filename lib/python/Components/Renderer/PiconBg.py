from Renderer import Renderer
from enigma import ePixmap
from Components.config import config
from Tools.Directories import SCOPE_SKIN_IMAGE, resolveFilename

class PiconBg(Renderer):
	def __init__(self):
		Renderer.__init__(self)

	GUI_WIDGET = ePixmap

	def postWidgetCreate(self, instance):
		self.changed((self.CHANGED_DEFAULT,))

	def changed(self, what):
		if self.instance:
			pngname = resolveFilename(SCOPE_SKIN_IMAGE, "ViX_HD_Common/piconbg/"+config.usage.show_picon_bkgrn.getValue() + ".png")
			if pngname:
				self.instance.setScale(1)
				self.instance.setPixmapFromFile(pngname)
				self.instance.show()
			else:
				self.instance.hide()

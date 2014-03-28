from Renderer import Renderer
from enigma import ePixmap
from Components.config import config
from Tools.Directories import SCOPE_ACTIVE_SKIN, resolveFilename

class PiconBg(Renderer):
	def __init__(self):
		Renderer.__init__(self)
		self.pngname = ""

	GUI_WIDGET = ePixmap

	def postWidgetCreate(self, instance):
		self.changed((self.CHANGED_DEFAULT,))

	def changed(self, what):
		if self.instance:
			pngname = ""
			if what[0] == 1 or what[0] == 3:
				pngname = resolveFilename(SCOPE_ACTIVE_SKIN, "piconbg/"+config.usage.show_picon_bkgrn.value + ".png")
				if self.pngname != pngname:
					if pngname:
						self.instance.setScale(1)
						self.instance.setPixmapFromFile(pngname)
						self.instance.show()
					else:
						self.instance.hide()
					self.pngname = pngname

from enigma import eLabel
from Components.config import config
from Components.Renderer.Renderer import Renderer
from Components.VariableText import VariableText
from Tools.Directories import resolveFilename, SCOPE_SYSETC


class VtiEmuInfo(VariableText, Renderer):

	GUI_WIDGET = eLabel

	def __init__(self):
		Renderer.__init__(self)
		VariableText.__init__(self)

	def connect(self, source):
		Renderer.connect(self, source)
		self.changed((self.CHANGED_DEFAULT,))

	def changed(self, what):
		self.text = "not detected Softcam" if what[0] == self.CHANGED_CLEAR else self.getVtiEmuInfo()

	def getVtiEmuInfo(self):
		if config.misc.ecm_info.value:
			try:
				with open(resolveFilename(SCOPE_SYSETC, "/tmp/.emu.info")) as fd:
					emuversion = fd.readline()
				return emuversion
			except OSError:
				return "not detected Softcam"

		else:
			return " "

from enigma import eQRCode

from Components.GUIComponent import GUIComponent
from Components.VariableText import VariableText


class QRCode(VariableText, GUIComponent):
	GUI_WIDGET = eQRCode

	def __init__(self, text=""):
		GUIComponent.__init__(self)
		VariableText.__init__(self)
		self.setText(text)

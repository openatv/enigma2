from __future__ import absolute_import
from .Renderer import Renderer

from enigma import eLabel

class FixedLabel(Renderer):
	GUI_WIDGET = eLabel

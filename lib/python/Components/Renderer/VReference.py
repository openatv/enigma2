#######################################################################
#
#    Renderer for Enigma2
#    Coded by shamann (c)2010
#
#    This program is free software; you can redistribute it and/or
#    modify it under the terms of the GNU General Public License
#    as published by the Free Software Foundation; either version 2
#    of the License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#######################################################################

from enigma import eLabel
from Components.Renderer.Renderer import Renderer
from Components.VariableText import VariableText


class VReference(VariableText, Renderer):

	GUI_WIDGET = eLabel

	def __init__(self):
		Renderer.__init__(self)
		VariableText.__init__(self)

	def connect(self, source):
		Renderer.connect(self, source)
		self.changed((self.CHANGED_DEFAULT,))

	def changed(self, what):
		if self.instance:
			if what[0] == self.CHANGED_CLEAR:
				self.text = "Reference not found!"
			else:
				service = self.source.service
				sname = service.toString()
				pos = sname.rfind(":")
				self.text = f"Reference: {sname[:-1]}" if pos != -1 else "Reference reading error!"

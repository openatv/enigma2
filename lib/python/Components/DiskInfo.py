from GUIComponent import GUIComponent
from VariableText import VariableText
from os import statvfs

from enigma import eLabel

# TODO: Harddisk.py has similiar functions, but only similiar.
# fix this to use same code
class DiskInfo(VariableText, GUIComponent):
	FREE = 0
	USED = 1
	SIZE = 2
	
	def __init__(self, path, type, update = True):
		GUIComponent.__init__(self)
		VariableText.__init__(self)
		self.type = type
		self.path = path
		if update:
			self.update()
	
	def update(self):
		try:
			stat = statvfs(self.path)
		except OSError:
			return -1
		
		if self.type == self.FREE:
			free = stat.f_bfree / 1000 * stat.f_bsize / 1000
			self.setText(("%d MB " + _("free diskspace")) % (free))

	GUI_WIDGET = eLabel

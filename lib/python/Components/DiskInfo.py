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
			free = (stat.f_bavail * stat.f_frsize) / 1024
			total = (stat.f_blocks * stat.f_frsize) / 1024
			percent = int((float(free) / float(total)) * 100)
			percentfree = str(percent) + '%'
#			self.setText(("%d MB " + _("free diskspace")) % (free))
			self.setText(("%s " + _('(' + str(((free / 1024) / 1024)) + 'gb) free diskspace')) % (percentfree))

	GUI_WIDGET = eLabel

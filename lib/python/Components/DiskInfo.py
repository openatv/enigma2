from GUIComponent import GUIComponent
from VariableText import VariableText
from os import statvfs

from enigma import eLabel

labels = (
	_("Available:"),
	_("Used:"),
	_("Size:"),
	_("Unknown:")
)

# TODO: Harddisk.py has similiar functions, but only similiar.
# fix this to use same code
class DiskInfo(VariableText, GUIComponent):
	FREE = 0
	USED = 1
	SIZE = 2
	ILLEGAL = 3

	def __init__(self, path, type, update=True, label=None):
		GUIComponent.__init__(self)
		VariableText.__init__(self)
		self.type = type
		self.path = path

		if self.type < self.FREE and self.type > self.SIZE:
			self.type = self.ILLEGAL
		self.label = label if label is not None else labels[self.type]

		if update:
			self.update()

	def convertSize(self, size):
		if size < 10 * 10 ** 6:
			return _("%d kB") % (size >> 10)
		elif size < 10 * 10 ** 9:
			return _("%d MB") % (size >> 20)
		elif size < 10 * 10 ** 12:
			return _("%d GB") % (size >> 30)
		else:
			return _("%d TB") % (size >> 40)

	def update(self):
		try:
			stat = statvfs(self.path)
		except OSError:
			return -1

		try:
			if self.type in (self.FREE, self.USED):
				val = (stat.f_bavail if self.type == self.FREE else stat.f_blocks - stat.f_bavail)
				percent = '(' + str((100 * val) // stat.f_blocks) + '%)'
				val = self.convertSize(val * stat.f_bsize)
				text = " ".join((self.label, val, percent))
			elif self.type == self.SIZE:
				val = self.convertSize(stat.f_blocks * stat.f_bsize)
				text = " ".join((self.label, val))
			else:
				text = " ".join((self.label, "-?-"))
		except:
			# occurs when f_blocks is 0 or a similar error
			text = " ".join((self.label, "-?-"))
		self.setText(text)

	GUI_WIDGET = eLabel

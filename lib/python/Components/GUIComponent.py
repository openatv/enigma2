import skin

from enigma import ePoint

class GUIComponent:
	""" GUI component """
	
	SHOWN = 0
	HIDDEN = 1
	
	def __init__(self):
		self.state = self.SHOWN
		self.instance = None
	
	def execBegin(self):
		pass
	
	def execEnd(self):
		pass
	
	# this works only with normal widgets - if you don't have self.instance, override this.
	def applySkin(self, desktop):
		if self.state == self.HIDDEN:
			self.instance.hide()
		skin.applyAllAttributes(self.instance, desktop, self.skinAttributes)

	def move(self, x, y):
		self.instance.move(ePoint(int(x), int(y)))

	def show(self):
		self.state = self.SHOWN
		if self.instance is not None:
			self.instance.show()

	def hide(self):
		self.state = self.HIDDEN
		if self.instance is not None:
			self.instance.hide()

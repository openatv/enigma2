import skin

class GUIComponent:
	""" GUI component """
	
	def __init__(self):
		pass
	
	def execBegin(self):
		pass
	
	def execEnd(self):
		pass
	
	# this works only with normal widgets - if you don't have self.instance, override this.
	def applySkin(self, desktop):
		skin.applyAllAttributes(self.instance, desktop, self.skinAttributes)

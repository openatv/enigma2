from GUIComponent import *
from skin import applyAllAttributes

class GUISkin:
	__module__ = __name__

	def __init__(self):
		self.onLayoutFinish = [ ]
		self.summaries = [ ]

	def createGUIScreen(self, parent, desktop):
		for val in self.values() + self.renderer:
			if isinstance(val, GUIComponent):
				val.GUIcreate(parent)
				val.applySkin(desktop)

		for w in self.additionalWidgets:
			w.instance = w.widget(parent)
			# w.instance.thisown = 0
			applyAllAttributes(w.instance, desktop, w.skinAttributes)
		
		for f in self.onLayoutFinish:
			if type(f) is not type(self.close): # is this the best way to do this?
				exec(f) in globals(), locals()
			else:
				f()

	def deleteGUIScreen(self):
		for (name, val) in self.items():
			if isinstance(val, GUIComponent):
				val.GUIdelete()

	def close(self):
		self.deleteGUIScreen()

	def createSummary(self):
		return None

	def addSummary(self, summary):
		self.summaries.append(summary)

	def removeSummary(self, summary):
		self.summaries.remove(summary)

	def setTitle(self, title):
		self.instance.setTitle(title)
		self.title = title
		
		for x in self.summaries:
			x.setTitle(title)

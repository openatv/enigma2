from __future__ import print_function

class TagEditor:
	def __init__(self):
		self.preferredTagEditor = None

	def setPreferredTagEditor(self, tageditor):
		if self.preferredTagEditor is None:
			self.preferredTagEditor = tageditor
			print("[TagEditor] Preferred tag editor changed to", self.preferredTagEditor)
		else:
			print("[TagEditor] Preferred tag editor already set to", self.preferredTagEditor, "ignoring", tageditor)

	def getPreferredTagEditor(self):
		return self.preferredTagEditor

tagEditor = TagEditor()

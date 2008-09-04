from Plugins.Extensions.CutListEditor.plugin import CutListEditor

class TitleCutter(CutListEditor):
	def __init__(self, session, title):
		CutListEditor.__init__(self, session, title.source)
		#, title.cutlist)

	def exit(self):
		self.session.nav.stopService()
		self.close(self.cut_list[:])

class CutlistReader(TitleCutter):
	def __init__(self, session, title):
		TitleCutter.__init__(self, session, title)
		self.tutorial_seen = True
		self.session.nav.stopService()
		self.close(self.cut_list[:])

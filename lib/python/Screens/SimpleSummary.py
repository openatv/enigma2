from Screens.Screen import Screen

class SimpleSummary(Screen):
	skin = """
	<screen position="0,0" size="132,64">
		<widget name="Clock" position="50,46" size="82,18" font="Regular;19" />
		<widget name="Title" position="0,4" size="132,42" font="Regular;19" />
	</screen>"""
	def __init__(self, session, root_screen):
		from Components.Label import Label
		from Components.Clock import Clock
		Screen.__init__(self, session)
		self["Clock"] = Clock()
		self["Title"] = Label(root_screen.title)

	def setTitle(self, title):
		self["Title"].setText(title)

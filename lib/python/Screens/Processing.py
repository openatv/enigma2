from enigma import eLabel, ePoint, eSize, eTimer, getDesktop

from Components.Label import Label
from Components.ProgressBar import ProgressBar
from Screens.Screen import Screen


class ProcessingScreen(Screen):
	skin = """
	<screen name="Processing" title="Processing" position="center,center" size="600,60" zPosition="+99">
		<widget name="progress" position="0,0" size="e,25" />
		<widget name="description" position="0,35" size="e,25" font="Regular;20" halign="center" />
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = ["Processing"]
		self["progress"] = ProgressBar()
		self["progress"].setRange((0, 100))
		self.description = ""
		self["description"] = Label(self.description)
		self.deskSize = None

	def setDescription(self, description):
		def resize(description):
			size = self.instance.csize()
			width = size.width()
			height = size.height()
			textSize = self["description"].instance.size()
			textWidth = textSize.width()
			textHeight = textSize.height()
			textFont = self["description"].instance.getFont()
			newHeight = eLabel.calculateTextSize(textFont, description, eSize(textWidth, 500), False).height()
			self["description"].instance.resize(eSize(textWidth, newHeight))
			delta = newHeight - textHeight
			self.instance.resize(eSize(width, height + delta))
			self.instance.move(ePoint((getDesktop(0).size().width() - width) // 2, (getDesktop(0).size().height() - height + delta) // 2))

		if description != self.description:
			resize(description)
		self["description"].setText(description)
		self.description = description

	def setProgress(self, progress):
		self["progress"].setValue(progress)


class Processing:
	instance = None

	def __init__(self, session):
		if Processing.instance:
			print("[Processing] Error: Only one Processing instance is allowed!")
		else:
			Processing.instance = self
			self.processingDialog = session.instantiateDialog(ProcessingScreen)
			self.processingDialog.setAnimationMode(0)
			self.timer = eTimer()
			self.timer.callback.append(self.updateProgress)
			self.progress = 0

	def showProgress(self, title=None, progress=0, endless=False):
		if title is None:
			title = _("Processing")
		self.processingDialog.setTitle(title)
		self.progress = progress
		self.processingDialog.show()
		if endless:
			self.timer.start(100)

	def updateProgress(self):
		self.progress = 0 if self.progress > 100 else self.progress + 1
		self.processingDialog.setProgress(self.progress)

	def hideProgress(self):
		self.timer.stop()
		self.processingDialog.hide()

	def setDescription(self, description):
		self.processingDialog.setDescription(description)

	def setProgress(self, progress):
		self.processingDialog.setProgress(progress)

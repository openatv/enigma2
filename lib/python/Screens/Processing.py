from enigma import eLabel, ePoint, eSize, eTimer, getDesktop

from Components.Label import Label
from Components.ProgressBar import ProgressBar
from Screens.Screen import Screen


class Processing(Screen):

	skin = """
		<screen name="Processing" title="" position="center,center" size="400,160" backgroundColor="#000000" flags="wfNoBorder" zPosition="+99">
			<widget source="Title" render="Label" position="10,5" size="380,20" font="Regular;20" foregroundColor="#FFFFFF" backgroundColor="#000000" halign="center" transparent="1" />
			<widget name="Progress" position="20,35" size="360,30" backgroundColor="#000000" foregroundColor="#FFFFFF" transparent="0" />
			<widget name="ProgressText" position="20,90" size="360,60" backgroundColor="#000000" font="Regular;18" foregroundColor="#FFFFFF" halign="center" transparent="1" valign="center" zPosition="+2" />
		</screen>
	"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self["Progress"] = ProgressBar()
		self["Progress"].setRange((0, 100))
		self["ProgressText"] = Label("")
		self.text = ""
		self.deskSize = None

	def setProgressValue(self, progress):
		self["Progress"].setValue(progress)

	def setProgressText(self, text):
		self["ProgressText"].text = text
		if len(text) != len(self.text):
			self.resize(text)
		self.text = text

	def resize(self, text):
		if self.deskSize is None:
			self.deskSize = getDesktop(0).size()
			self.objectSize = self.instance.size()
			self.textsize = self["ProgressText"].instance.size()
			self.textFont = self["ProgressText"].instance.getFont()
			self.div = self.objectSize.height() - self.textsize.height()
		maxheight = 400
		size = eSize(self.textsize.width(), maxheight - self.div)
		newtextheight = eLabel.calculateTextSize(self.textFont, text, size, False).height()
		if newtextheight > maxheight:
			newtextheight = maxheight
		elif newtextheight < self.textsize.height():
			newtextheight = self.textsize.height()
		textsize = (self.textsize.width(), newtextheight)
		self["ProgressText"].instance.resize(eSize(*textsize))
		wsize = (self.objectSize.width(), newtextheight + self.div)
		self.instance.resize(eSize(*wsize))
		self.instance.move(ePoint(int(self.deskSize.width() - wsize[0]) // 2, int(self.deskSize.height() - wsize[1]) // 2))


class ProcessingControl:
	instance = None

	def __init__(self, session):
		assert not ProcessingControl.instance, "[ProcessingControl] Error: Only one ProcessingControl instance is allowed!"
		ProcessingControl.instance = self
		self.ProgressDialog = session.instantiateDialog(ProcessingControl)
		self.ProgressDialog.setAnimationMode(0)
		self.progressBarTimer = eTimer()
		self.progressBarTimer.callback.append(self.updateProgress)
		self.progressValue = 0
		self.repeat = 100

	def showProgress(self, title="", endless=False):
		self.ProgressDialog.setTitle(title)
		self.ProgressDialog.show()
		if endless:
			self.progressBarTimer.start(self.repeat)

	def setProgressText(self, progressText):
		self.ProgressDialog.setProgressText(progressText)

	def setProgressValue(self, progressValue):
		self.ProgressDialog.setProgressValue(progressValue)

	def hideProgress(self):
		self.progressBarTimer.stop()
		self.ProgressDialog.hide()

	def updateProgress(self):
		self.progressValue += 1
		if self.progressValue > 100:
			self.progressValue = 1
		self.ProgressDialog.setProgressValue(self.progressValue)

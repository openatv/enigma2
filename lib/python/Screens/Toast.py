from enigma import ePoint, gRGB, eSize, eTimer

from Components.Label import Label
from Screens.Screen import Screen


class ToastScreen(Screen):
	skin = """
	<screen name="ToastScreen" position="0,640" size="1280,80" resolution="1280,720" backgroundColor="#FE000000" flags="wfNoBorder" zPosition="101">
		<widget name="text" position="0,0" size="e,e" padding="10" conditional="text" font="Regular;25" horizontalAlignment="center" verticalAlignment="center" backgroundColor="#00000000" />
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self["text"] = Label()
		self.timer = eTimer()
		self.timer.callback.append(self.dohide)
		self.fadeTimer = eTimer()
		self.fadeTimer.callback.append(self.fade)

	def showToast(self, text, timeout):
		self["text"].setText(text)
		self.timer.start(timeout * 1000)
		self.textSize = self["text"].instance.calculateSize()
		newsize = (self.textSize.width() + 20, self.textSize.height() + 20)
		self["text"].instance.resize(eSize(*newsize))
		newPos = ePoint((self.instance.size().width() - self.textSize.width()) // 2, self.instance.size().height() - self.textSize.height() - 40)
		self["text"].instance.move(newPos)
		self.fadeIn = True
		self.alpha = 255
		self["text"].instance.setBackgroundColor(gRGB(*(0, 0, 0, self.alpha)))
		self["text"].instance.setForegroundColor(gRGB(*(255, 255, 255, self.alpha)))
		self.fadeTimer.start(50)
		self.show()

	def fade(self):
		if self.fadeIn:
			self.alpha -= 5
			if self.alpha <= 0:
				self.alpha = 0
				self.fadeTimer.stop()
				self.fadeIn = False
		else:
			self.alpha += 5
			if self.alpha >= 255:
				self.alpha = 255
				self.fadeTimer.stop()
				self.hide()
		self["text"].instance.setBackgroundColor(gRGB(*(0, 0, 0, self.alpha)))
		self["text"].instance.setForegroundColor(gRGB(*(255, 255, 255, self.alpha)))

	def dohide(self):
		self.timer.stop()
		self.fadeIn = False
		self.fadeTimer.start(50)


class Toast:
	instance = None

	def __init__(self, session):
		if Toast.instance:
			print("[Toast] Error: Only one Toast instance is allowed!")
		else:
			Toast.instance = self
			self.dialog = session.instantiateDialog(ToastScreen)
			self.dialog.hide()

	def showToast(self, text, timeout):
		self.dialog.showToast(text, timeout)

	shown = property(lambda self: self.dialog.shown)

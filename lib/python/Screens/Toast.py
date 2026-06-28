from enigma import ePoint, gRGB, eSize, eTimer

from Components.Label import Label
from Screens.Screen import Screen

FADESPEED = 50
FADESTEPS = 10


class ToastScreen(Screen):
	skin = """
	<screen name="ToastScreen" position="0,0" size="1280,720" resolution="1280,720" backgroundColor="#FE000000" flags="wfNoBorder" zPosition="101">
		<widget name="border" position="0,0" size="40,40" backgroundColor="#00000000" widgetBorderColor="#FFFFFF" widgetBorderWidth="2" />
		<widget name="icon" position="0,0" size="40,40" font="enigma2icons;34" horizontalAlignment="center" verticalAlignment="center" backgroundColor="#00000000" />
		<widget name="text" position="0,0" size="e,e" font="Regular;25" horizontalAlignment="left" verticalAlignment="center" backgroundColor="#00000000" />
	</screen>"""

	ICON_CHARS = {
		0: "\uE90A",  # TYPE_INFO
		1: "\uEA59",  # TYPE_WARNING
		2: "\uEA56",  # TYPE_ERROR
	}

	def __init__(self, session):
		Screen.__init__(self, session)
		self["border"] = Label()
		self["icon"] = Label()
		self["text"] = Label()
		self._timer = eTimer()
		self._timer.callback.append(self._dohide)
		self._fadeTimer = eTimer()
		self._fadeTimer.callback.append(self._doFade)
		self._displayW = None
		self._displayH = None

	def showToast(self, text, toasttype, timeout):
		self._foregroundColor = {
			Toast.TYPE_INFO: (255, 255, 255),  # white
			Toast.TYPE_WARNING: (0, 0, 0),  # black
			Toast.TYPE_ERROR: (255, 255, 255)  # white
		}.get(toasttype, (255, 255, 255))

		self._backgroundColor = {
			Toast.TYPE_INFO: (0, 0, 0),  # black
			Toast.TYPE_WARNING: (255, 165, 0),  # orange
			Toast.TYPE_ERROR: (255, 0, 0)  # red
		}.get(toasttype, (0, 0, 0))

		self["icon"].setText(self.ICON_CHARS.get(toasttype, ""))
		self["text"].setText(text)
		self._timer.start(timeout * 1000)

		BORDER_PAD = 18
		GAP = 14
		SCREEN_MARGIN = 60

		if self._displayW is None:
			self._displayW = self.instance.size().width()
			self._displayH = self.instance.size().height()
		displayW = self._displayW
		displayH = self._displayH

		self._iconSize = self["icon"].instance.calculateSize()
		iconW = self._iconSize.width()
		iconH = self._iconSize.height()

		maxTextW = displayW - SCREEN_MARGIN * 2 - BORDER_PAD * 2 - iconW - GAP
		self["text"].instance.resize(eSize(maxTextW, displayH))
		self._textSize = self["text"].instance.calculateSize()

		textW = self._textSize.width()
		textH = self._textSize.height()
		contentH = max(iconH, textH)
		borderW = BORDER_PAD * 2 + iconW + GAP + textW
		borderH = contentH + BORDER_PAD * 2

		screenX = (displayW - borderW) // 2
		screenY = displayH - borderH - 20
		self.instance.resize(eSize(borderW, borderH))
		self.instance.move(ePoint(screenX, screenY))

		self["border"].instance.resize(eSize(borderW, borderH))
		self["border"].instance.move(ePoint(0, 0))
		self["icon"].instance.resize(eSize(iconW, contentH))
		self["icon"].instance.move(ePoint(BORDER_PAD, BORDER_PAD))
		self["text"].instance.resize(eSize(textW, textH))
		self["text"].instance.move(ePoint(BORDER_PAD + iconW + GAP, BORDER_PAD + (contentH - textH) // 2))

		self._fadeIn = True
		self._alpha = 255
		self._applyColors()
		self._fadeTimer.start(FADESPEED)
		self.show()

	def _applyColors(self):
		fg = gRGB(*(self._foregroundColor[0], self._foregroundColor[1], self._foregroundColor[2], self._alpha))
		bg = gRGB(*(self._backgroundColor[0], self._backgroundColor[1], self._backgroundColor[2], self._alpha))
		self["border"].instance.setBackgroundColor(bg)
		self["border"].instance.setWidgetBorderColor(fg)
		self["icon"].instance.setBackgroundColor(bg)
		self["icon"].instance.setForegroundColor(fg)
		self["text"].instance.setBackgroundColor(bg)
		self["text"].instance.setForegroundColor(fg)

	def _doFade(self):
		if self._fadeIn:
			self._alpha -= FADESTEPS
			if self._alpha <= 0:
				self._alpha = 0
				self._fadeTimer.stop()
				self._fadeIn = False
		else:
			self._alpha += FADESTEPS
			if self._alpha >= 255:
				self._alpha = 255
				self._fadeTimer.stop()
				self.hide()
		self._applyColors()

	def _dohide(self):
		self._timer.stop()
		self._fadeIn = False
		self._fadeTimer.start(FADESPEED)

	def forceHide(self):
		self._fadeTimer.stop()
		self._timer.stop()
		self.hide()


class Toast:
	TYPE_INFO = 0
	TYPE_WARNING = 1
	TYPE_ERROR = 2
	instance = None

	def __init__(self, session):
		if Toast.instance:
			print("[Toast] Error: Only one Toast instance is allowed!")
		else:
			Toast.instance = self
			self._dialog = session.instantiateDialog(ToastScreen)
			self._dialog.hide()
			self._queue = []
			self._nextTimer = eTimer()
			self._nextTimer.callback.append(self._showNext)
			self._dialog.onHide.append(self._scheduleNext)

	def showToast(self, text, toasttype, timeout):
		timeout = max(3, min(timeout, 10))  # Minimum 3 maximum 10
		self._queue.append((text, toasttype, timeout))
		if not self._dialog.shown and not self._nextTimer.isActive():
			self._showNext()

	def _scheduleNext(self):
		if self._queue:
			self._nextTimer.start(1000, True)  # 1000 ms Pause

	def _showNext(self):
		self._nextTimer.stop()
		if not self._dialog.shown and self._queue:
			text, toasttype, timeout = self._queue.pop(0)
			self._dialog.showToast(text, toasttype, timeout)

	def doShutdown(self):
		self._nextTimer.stop()
		if self._queue:
			self._queue = None
		if self._dialog.shown:
			self._dialog.forceHide()

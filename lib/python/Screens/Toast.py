from enigma import ePoint, eSize, eTimer, gRGB

from skin import parseColor, parseInteger
from Components.config import config
from Components.Label import Label
from Screens.Screen import Screen


class ToastScreen(Screen):
	skin = """
	<screen name="Toast" title="Toast Message" position="center,e-75" size="65,55" backgroundColors="#00000000,#00FFAF00,#00FF0000" expand="up" foregroundColors="#00FFFFFF,#00000000,#00FFFFFF" flags="wfNoBorder,wfModal" maxWidth="800" resolution="1280,720" widgetBorderColors="#00FFFFFF,#00000000,#00FFFFFF" zPosition="101">
		<widget name="background" position="0,0" size="e,e" widgetBorderWidth="2" />
		<widget name="glyph" position="10,10" size="35,35" font="enigma2icons;35" horizontalAlignment="center" verticalAlignment="center" />
		<widget name="text" position="55,10" size="0,35" font="Regular;25" horizontalAlignment="left" verticalAlignment="center" wrap="on" />
	</screen>
	"""

	def __init__(self, session):
		Screen.__init__(self, session, mandatoryWidgets=["background", "glyph", "text"])
		self.skinName = ["Toast"]
		self["background"] = Label()
		self["glyph"] = Label()
		self["text"] = Label()
		self.defaultTimeout = 10  # Default timeout/hide in 10 seconds.
		self.fadeSpeed = 50  # Timer between fade steps.
		self.toastGlyphs = {
			0: "\uE90A",  # TYPE_INFO
			1: "\uEA59",  # TYPE_WARNING
			2: "\uEA56"  # TYPE_ERROR
		}
		self.hideTimer = eTimer()
		self.hideTimer.callback.append(self.hideToast)
		self.fadeTimer = eTimer()
		self.fadeTimer.callback.append(self.fadeToast)
		self.onLayoutFinish.append(self.layoutFinished)

	def applySkin(self):
		def parseColors(value, defaults):
			values = [x.strip() for x in value.split(",")]
			colors = []
			if len(values) == len(defaults):
				for index, item in enumerate(values):
					colors.append(parseColor(item, defaults[index]))
			else:
				colors = defaults
			return colors

		# Reset to the defaults so a skin change does not inherit values from the previous skin.
		self.widgetBorderColors = (gRGB(0x00FFFFFF), gRGB(0x00000000), gRGB(0x00FFFFFF))  # White, Black, White.
		self.backgroundColors = (gRGB(0x00000000), gRGB(0x00FFAF00), gRGB(0x00FF0000))  # Black, Orange, Red.
		self.foregroundColors = (gRGB(0x00FFFFFF), gRGB(0x00000000), gRGB(0x00FFFFFF))  # White, Black, White.
		self.expansion = 0
		maxWidth = None
		screenAttributes = []
		if self.skinAttributes:
			for attribute, value in self.skinAttributes:
				match attribute:
					case "backgroundColors":
						self.backgroundColors = parseColors(value, self.backgroundColors)  # Black, Orange, Red.
					case "foregroundColors":
						self.foregroundColors = parseColors(value, self.foregroundColors)  # White, Black, White.
					case "expand":
						self.expansion = {
							"center": 0,
							"left": 1,
							"up": 2,
							"right": 3,
							"down": 4
						}.get(value, 0)
					case "maxWidth":
						maxWidth = parseInteger(value, 0)
					case "widgetBorderColors":
						self.widgetBorderColors = parseColors(value, self.widgetBorderColors)  # White, Black, White.
					case _:
						screenAttributes.append((attribute, value))
			self.skinAttributes = screenAttributes
		Screen.applySkin(self)
		# Scale maxWidth from skin to desktop resolution, default is two thirds of the screen width.
		self.maxWidth = maxWidth * self.scale[0][0] // self.scale[0][1] if maxWidth else self.desktop.size().width() * 2 // 3

	def layoutFinished(self):
		self.toastX = self.instance.position().x()
		self.toastY = self.instance.position().y()
		self.toastW = self.instance.size().width()
		self.toastH = self.instance.size().height()
		self.centerX = self.toastX + (self.toastW // 2)
		self.centerY = self.toastY + (self.toastH // 2)
		self.glyphX = self["glyph"].instance.position().x()
		self.glyphY = self["glyph"].instance.position().y()
		self.glyphW = self["glyph"].instance.size().width()
		self.glyphH = self["glyph"].instance.size().height()
		self.textX = self["text"].instance.position().x()
		self.textY = self["text"].instance.position().y()
		self.textW = self["text"].instance.size().width()
		self.textH = self["text"].instance.size().height()
		self.rightPadding = self.toastW - self.textX - self.textW
		self.bottomPadding = self.toastH - self.textY - self.textH
		self.minimumHeight = self.glyphY + self.glyphH + self.bottomPadding

	def showToast(self, text, toastType, timeout, customGlyph):
		self.widgetBorderColor = self.widgetBorderColors[toastType]
		self.backgroundColor = self.backgroundColors[toastType]
		self.foregroundColor = self.foregroundColors[toastType]
		self["glyph"].setText(customGlyph or self.toastGlyphs.get(toastType, ""))
		self["text"].setText(text)
		textSize = self["text"].instance.calculateTextSize(self["text"].instance.getFont(), text, eSize(10000, 10000), True)
		textWidth = textSize.width()
		textHeight = textSize.height()
		# The skin attribute maxWidth is the total width of the toast, so the text gets what remains after the glyph and padding.
		maxTextWidth = self.maxWidth - self.textX - self.rightPadding
		if textWidth > maxTextWidth:
			textSize = self["text"].instance.calculateTextSize(self["text"].instance.getFont(), text, eSize(maxTextWidth, 10000), False)
			textWidth = textSize.width()
			textHeight = textSize.height()
		width = self.textX + textWidth + self.rightPadding
		height = self.textY + textHeight + self.bottomPadding
		if height < self.minimumHeight:
			height = self.minimumHeight
		match self.expansion:
			case 1:  # Expand to the left, right edge of skin screen stays fixed.
				xPos = self.toastX + self.toastW - width
				yPos = self.centerY - (height // 2)
			case 2:  # Expand upwards, bottom edge of skin screen stays fixed.
				xPos = self.centerX - (width // 2)
				yPos = self.toastY + self.toastH - height
			case 3:  # Expand to the right, left edge of skin screen stays fixed.
				xPos = self.toastX
				yPos = self.centerY - (height // 2)
			case 4:  # Expand downwards, top edge of skin screen stays fixed.
				xPos = self.centerX - (width // 2)
				yPos = self.toastY
			case _:  # Center based on center of skin screen.
				xPos = self.centerX - (width // 2)
				yPos = self.centerY - (height // 2)
		self.instance.move(ePoint(xPos, yPos))
		self.instance.resize(eSize(width, height))
		self["background"].instance.resize(eSize(width, height))
		self["text"].instance.resize(eSize(textWidth, textHeight))
		self.hideTimer.start((timeout if timeout else self.defaultTimeout) * 1000)
		if config.misc.toastFade.value:
			self.alpha = 0xFF
			self.fadeIn = True
			self.fadeTimer.start(self.fadeSpeed)
		else:
			self.alpha = 0x00
		self.applyColors()
		self.show()

	def applyColors(self):
		alpha = self.alpha << 24
		widgetBorderColor = gRGB((self.widgetBorderColor.argb() & 0x00FFFFFF) | alpha)
		backgroundColor = gRGB((self.backgroundColor.argb() & 0x00FFFFFF) | alpha)
		foregroundColor = gRGB((self.foregroundColor.argb() & 0x00FFFFFF) | alpha)
		self["background"].instance.setBackgroundColor(backgroundColor)
		self["background"].instance.setWidgetBorderColor(widgetBorderColor)
		self["glyph"].instance.setBackgroundColor(backgroundColor)
		self["glyph"].instance.setForegroundColor(foregroundColor)
		self["text"].instance.setBackgroundColor(backgroundColor)
		self["text"].instance.setForegroundColor(foregroundColor)

	def hideToast(self):
		self.hideTimer.stop()
		if config.misc.toastFade.value:
			self.fadeIn = False
			self.fadeTimer.start(self.fadeSpeed)
		else:
			self.hide()

	def fadeToast(self):
		if self.fadeIn:
			self.alpha -= config.misc.toastFade.value
			if self.alpha <= 0x00:
				self.alpha = 0x00
				self.fadeTimer.stop()
				self.fadeIn = False
		else:
			self.alpha += config.misc.toastFade.value
			if self.alpha >= 0xFF:
				self.alpha = 0xFF
				self.fadeTimer.stop()
				self.hide()
		self.applyColors()

	def forceHide(self):
		self.fadeTimer.stop()
		self.hideTimer.stop()
		self.hide()


class Toast:
	TYPE_INFO = 0
	TYPE_WARNING = 1
	TYPE_ERROR = 2
	instance = None

	def __init__(self):
		if Toast.instance:
			print("[Toast] Error: Only one Toast instance is allowed!")
		else:
			Toast.instance = self
			self.dialog = None
			self.queue = []
			self.activeToastId = None

	def setup(self, session):
		def scheduleNext():
			self.activeToastId = None
			if self.queue:
				self.nextTimer.start(500, True)  # 500 ms pause between Toast messages.

		self.dialog = session.instantiateDialog(ToastScreen)
		self.dialog.hide()
		self.nextTimer = eTimer()
		self.nextTimer.callback.append(self.showNext)
		self.dialog.onHide.append(scheduleNext)
		if self.queue:
			self.showNext()

	def showToast(self, text, toastType, timeout, customIcon=None, replaceId=None):
		timeout = max(3, min(timeout, 60))  # Toast can be shown for a minimum 3 seconds and a maximum of 60 seconds.
		toast = (text, toastType, timeout, customIcon, replaceId)
		if replaceId is not None:
			if self.dialog and self.dialog.shown and self.activeToastId == replaceId:
				self.dialog.showToast(text, toastType, timeout, customIcon)
				return
			for index, queuedToast in enumerate(self.queue):
				if queuedToast[4] == replaceId:
					self.queue[index] = toast
					return
		self.queue.append(toast)
		print(f"[Toast] Queued '{text}', queue={len(self.queue)}, ready={self.dialog is not None}.")
		if self.dialog and not self.dialog.shown and not self.nextTimer.isActive():
			self.showNext()

	def removeToast(self, replaceId):
		if replaceId is not None:
			self.queue = [x for x in self.queue if x[4] != replaceId]
			if self.dialog and self.dialog.shown and self.activeToastId == replaceId:
				self.dialog.forceHide()
			if self.dialog and not self.queue:
				self.nextTimer.stop()

	def showNext(self):
		self.nextTimer.stop()
		if not self.dialog.shown and self.queue:
			text, toastType, timeout, customIcon, self.activeToastId = self.queue.pop(0)
			print(f"[Toast] Showing '{text}', remaining={len(self.queue)}.")
			self.dialog.showToast(text, toastType, timeout, customIcon)

	def doShutdown(self):
		self.queue = []
		if self.dialog:
			self.nextTimer.stop()
			if self.dialog.shown:
				self.dialog.forceHide()

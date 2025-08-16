from enigma import getDesktop, gRGB
from Components.config import config
from Components.Label import Label
from Screens.Screen import Screen
from skin import subtitleFonts, parseFont, getSkinFactor


class SubtitleDisplay(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.subtitlesShown = False
		self["subtitles"] = Label()
		self["subtitles"].hide()
		self.onLayoutFinish.append(self.__layoutFinished)

	def __layoutFinished(self):
		widgetInstance = self["subtitles"].instance
		fontStyle = subtitleFonts.get("Subtitle_Regular", {})
		fontSize = int(config.subtitles.subtitle_fontsize.value)
		fontFace = fontStyle.get("font", "Regular").split(";")[0]
		font = parseFont(f"{fontFace};{fontSize * getSkinFactor()}")
		widgetInstance.setFont(font)
		widgetInstance.setZPosition(1)
		widgetInstance.setWrap(0)
		widgetInstance.setHAlign(1)
		widgetInstance.setVAlign(1)
		widgetInstance.setBackgroundColor(gRGB(0xff000000))
		foreColor = config.subtitles.pango_subtitle_colors.value
		if foreColor == 2:  # yellow
			widgetInstance.setForegroundColor(gRGB(0x00ffff00))
		borderWidth = fontStyle.get("borderWidth", 0)
		borderColor = fontStyle.get("borderColor", None)
		if borderWidth and borderColor:
			widgetInstance.setBorderWidth(borderWidth)
			widgetInstance.setBorderColor(borderColor)

	def showSubtitles(self, subtitles):
		padding = (40, 10)
		widget = self["subtitles"]
		widget.setText(subtitles)
		size = widget.getSize()
		widget.resize(size[0] + padding[0] * 2, size[1] + padding[1] * 2)
		widget.move((getDesktop(0).size().width() - size[0] - padding[0]) // 2, getDesktop(0).size().height() - size[1] - padding[1] * 2 - 30)
		widget.show()
		self.subtitlesShown = True
		self.show()

	def hideSubtitles(self):
		self.subtitlesShown = False
		self["subtitles"].hide()

	def hideScreen(self):
		self.hideSubtitles()
		self.hide()

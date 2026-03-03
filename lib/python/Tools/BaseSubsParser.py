import re


class ParseError(Exception):
	pass


class NoSubtitlesParseError(ParseError):
	pass


HEX_COLORS = {
			"red": "#FF0000",
			"white": "#FFFFFF",
			"cyan": "#00FFFF",
			"silver": "#C0C0C0",
			"blue": "#0000FF",
			"gray": "#808080",
			"grey": "#808080",
			"darkblue": "#0000A0",
			"black": "#000000",
			"lightblue": "#ADD8E6",
			"orange": "#FFA500",
			"purple": "#800080",
			"brown": "#A52A2A",
			"yellow": "#FFFF00",
			"maroon": "#800000",
			"lime": "#00FF00",
			"green": "#008000",
			"magenta": "#FF00FF",
			"olive": "#808000"}


class BaseParser(object):
	parsing = ()

	@classmethod
	def canParse(cls, ext):
		return ext in cls.parsing

	def __init__(self, rowParse=False):
		self.rowParse = rowParse

	def __str__(self):
		return self.__class__.__name__

	def createSub(self, text, start, end):
		"""
		@param text: text of subtitle
		@param start: start time of subtitle in ms
		@param end: end time of subtitle in ms

		"""
		duration = int(end - start)
		# convert to pts
		start = int(start * 90)
		end = int(end * 90)
		if self.rowParse:
			rows = []
			style = newStyle = 'regular'
			color = newColor = 'default'
			for rowText in text.split('\n'):
				rowStyle, newStyle = self.getStyle(rowText, newStyle)
				rowColor, newColor = self.getColor(rowText, newColor)
				rowText = self.removeTags(rowText)
				rows.append({"text": rowText, "style": rowStyle, 'color': rowColor})
			return {'rows': rows, 'start': start, 'end': end, 'duration': duration}
		else:
			style, newStyle = self.getStyle(text)
			color, newColor = self.getColor(text)
			text = self.removeTags(text)
			return {'text': text, 'style': style, 'color': color, 'start': start, 'end': end, 'duration': duration}

	def parse(self, text, fps=None):
		"""
		parses subtitles from text into list of sub dicts
		and returns this list

		"""
		text = text.strip()

		text = text.replace('\x00', '').replace('.', '')
		text = re.sub(u'[\u064e\u064f\u0650\u0651\u0652\u064c\u064b\u064d\u0640\ufc62]', '', text)
		sublist = self._parse(text, fps)
		if len(sublist) <= 1:
			raise NoSubtitlesParseError()
		return sublist

	def getColor(self, text, color=None):
		color, newColor = self._getColor(text, color)
		return color or 'default', newColor or 'default'

	def getStyle(self, text, style=None):
		style, newStyle = self._getStyle(text, style)
		return style or 'regular', newStyle or 'regular'

	def removeTags(self, text):
		return self._removeTags(text)

	def _removeTags(self, text):
		return text

	def _getStyle(self, text, style):
		return '', ''

	def _getColor(self, text, color):
		return '', ''

	def _parse(self, text, fps):
		return []

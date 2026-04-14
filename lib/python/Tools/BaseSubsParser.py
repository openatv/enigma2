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


class BaseParser:
	parsing = ()

	@classmethod
	def canParse(cls, ext):
		return ext in cls.parsing

	def __init__(self, row_parse=False):
		self.row_parse = row_parse

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
		if self.row_parse:
			rows = []
			new_style = 'regular'
			new_color = 'default'
			for row_text in text.split('\n'):
				row_style, new_style = self.get_style(row_text, new_style)
				row_color, new_color = self.get_color(row_text, new_color)
				row_text = self.remove_tags(row_text)
				rows.append({"text": row_text, "style": row_style, 'color': row_color})
			return {'rows': rows, 'start': start, 'end': end, 'duration': duration}
		else:
			style, new_style = self.get_style(text)
			color, new_color = self.get_color(text)
			text = self.remove_tags(text)
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

	def get_color(self, text, color=None):
		color, new_color = self._get_color(text, color)
		return color or 'default', new_color or 'default'

	def get_style(self, text, style=None):
		style, new_style = self._get_style(text, style)
		return style or 'regular', new_style or 'regular'

	def remove_tags(self, text):
		return self._remove_tags(text)

	def _remove_tags(self, text):
		return text

	def _get_style(self, text, style):
		return '', ''

	def _get_color(self, text, color):
		return '', ''

	def _parse(self, text, fps):
		return []

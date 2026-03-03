import re

from .BaseSubsParser import BaseParser, ParseError, HEX_COLORS


class SubRipParser(BaseParser):
	format = "SubRip"
	parsing = ('.srt',)

	def _parse(self, text, fps):
		return self._srt_to_dict(text)

	def _removeTags(self, text):
		# Remove HTML tags
		text = re.sub('<[^>]*>', '', text)
		# Remove SSA/ASS positioning tags like {\an8}
		text = re.sub(r'\{.*?\}', '', text)
		return text

	def _getColor(self, text, color):
		newColor = color
		if color:
			if color != 'default':
				if text.find('</font>') != -1 or text.find('</Font>') != -1:
					newColor = 'default'
			else:
				colorMatch = re.search('<[Ff]ont [Cc]olor=(.+?)>', text, re.DOTALL)
				colorText = colorMatch and colorMatch.group(1)
				colorText = colorText and colorText.replace("'", "").replace('"', '')
				if text.find('</font>') != -1 or text.find('</Font>') != -1:
					newColor = 'default'
				else:
					newColor = color
		else:
			color = 'default'
			colorMatch = re.search('<[Ff]ont [Cc]olor=(.+?)>', text, re.DOTALL)
			colorText = colorMatch and colorMatch.group(1) or color
			colorText = colorText.replace("'", "").replace('"', '')

		if colorText:
			hexColor = re.search("(" + r"#" + "[0-9,a-f,A-F]{6})", colorText)
			if hexColor:
				color = hexColor.group(1)[1:]
			else:
				try:
					color = HEX_COLORS[colorText.lower()][1:]
				except KeyError:
					pass
		return color, newColor

	def _getStyle(self, text, style):
		newStyle = style
		endTag = False
		# looking for end tag
		if not style:
			if self.italicStart(text):
				style = 'italic'
				newStyle = style
				endTag = self.italicEnd(text)
			elif self.boldStart(text):
				style = 'bold'
				newStyle = style
				endTag = self.boldEnd(text)
			elif self.underlineStart(text):
				style = 'regular'
				newStyle = style
		else:
			if style == 'italic':
				endTag = self.italicEnd(text)
			elif style == 'bold':
				endTag = self.boldEnd(text)
			elif style == 'underline':
				endTag = True
			# looking for start/end tag on the same line
			else:
				if self.italicStart(text):
					style = 'italic'
					newStyle = style
					endTag = self.italicEnd(text)
				elif self.boldStart(text):
					style = 'bold'
					newStyle = style
					endTag = self.boldEnd(text)
				elif self.underlineStart(text):
					style = 'regular'
					newStyle = style

		if endTag:
			newStyle = 'regular'
		return style, newStyle

	def _srt_to_dict(self, srtText):
		subs = {}
		idx = 0
		srtText = srtText.replace('\r\n', '\n').strip() + "\n\n"
		for s in re.finditer(r'(^\d+)\s*\:\s*(\d+)\s*\:\s*(\d+)\s*\,\s*(\d+)\s*-->\s*(\d+)\s*\:\s*(\d+)\s*\:\s*(\d+)\s*\,\s*(\d+)\s*\n(.+?)(?:\n\n|\n\d+\s*\n)', srtText, re.DOTALL | re.MULTILINE):
			try:
				idx += 1
				shour, smin, ssec, smsec = int(s.group(1)), int(s.group(2)), int(s.group(3)), int(s.group(4))
				start_time = int((shour * 3600 + smin * 60 + ssec) * 1000 + smsec)
				ehour, emin, esec, emsec = int(s.group(5)), int(s.group(6)), int(s.group(7)), int(s.group(8))
				end_time = int((ehour * 3600 + emin * 60 + esec) * 1000 + emsec)
				subline = self.createSub(s.group(9), start_time, end_time)
				subs[subline["start"]] = subline
			except Exception as e:
				raise ParseError(str(e) + ', subtitle_index: %d' % idx)
		return subs

	def italicStart(self, text):
		return text.lower().find('<i>') != -1

	def italicEnd(self, text):
		return text.lower().find('</i>') != -1

	def boldStart(self, text):
		return text.lower().find('<b>') != -1

	def boldEnd(self, text):
		return text.lower().find('</b>') != -1

	def underlineStart(self, text):
		return text.lower().find('<u>') != -1

	def underlineEnd(self, text):
		return text.lower().find('</u>') != -1


parserClass = SubRipParser

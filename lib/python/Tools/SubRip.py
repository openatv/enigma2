import re

from .BaseSubsParser import BaseParser, ParseError, HEX_COLORS


class SubRipParser(BaseParser):
	format = "SubRip"
	parsing = (".srt",)

	_TAG_RE = re.compile(r"<[^>]*>")
	_SSA_RE = re.compile(r"\{[^}]*\}")
	_FONT_COLOR_RE = re.compile(r"<[Ff]ont\s+[Cc]olor=(['\"]?)([^\"'>]+)\1")

	def _parse(self, text, fps):
		return self._srt_to_dict(text)

	# ---------------------------
	# Text cleaning
	# ---------------------------
	def _remove_tags(self, text):
		text = self._TAG_RE.sub("", text)
		text = self._SSA_RE.sub("", text)
		return text

	# ---------------------------
	# Color parsing (fast path)
	# ---------------------------
	def _get_color(self, text, color):
		new_color = color or "default"

		match = self._FONT_COLOR_RE.search(text)
		color_text = match.group(2) if match else new_color

		# Normalize
		if "</font>" in text.lower():
			new_color = "default"

		parsed = self._parse_color_value(color_text)
		return parsed, new_color

	def _parse_color_value(self, value):
		if not value:
			return "default"

		if value.startswith("#") and len(value) == 7:
			return value[1:]

		try:
			return HEX_COLORS[value.lower()][1:]
		except Exception:
			return value

	# ---------------------------
	# Style parsing (branch-light)
	# ---------------------------
	def _get_style(self, text, style):
		# Fast path: no tags at all
		if "<" not in text:
			return (None, None) if not style else (style, style)

		t = text

		# Precompute tag presence (cheap and readable)
		has_i_start = "<i>" in t or "<I>" in t
		has_i_end = "</i>" in t or "</I>" in t
		has_b_start = "<b>" in t or "<B>" in t
		has_b_end = "</b>" in t or "</B>" in t
		has_u_start = "<u>" in t or "<U>" in t

		# No active style yet
		if style is None:
			if has_i_start:
				return "italic", "regular" if has_i_end else "italic"
			if has_b_start:
				return "bold", "regular" if has_b_end else "bold"
			if has_u_start:
				return "underline", "underline"
			return None, None

		# Existing style handling
		if style == "italic":
			return "italic", "regular" if has_i_end else "italic"

		if style == "bold":
			return "bold", "regular" if has_b_end else "bold"

		if style == "underline":
			return "underline", "regular"

		return style, style

	# ---------------------------
	# FAST SRT parsing (single pass)
	# ---------------------------
	def _srt_to_dict(self, srt_text):
		subs = {}
		idx = 0

		text = srt_text.replace("\r\n", "\n").strip()
		lines = text.split("\n")
		n = len(lines)
		i = 0

		while i < n:
			# Skip empty lines
			if not lines[i]:
				i += 1
				continue

			try:
				# Detect time line position
				if "-->" in lines[i]:
					time_line = lines[i]
					i += 1
				else:
					# skip index line
					i += 1
					if i >= n:
						break
					time_line = lines[i]
					i += 1

				start_time, end_time = self._parse_time_range(time_line)

				# Collect subtitle text (no joins until needed)
				text_start = i
				while i < n and lines[i]:
					i += 1

				subtitle_text = "\n".join(lines[text_start:i])

				idx += 1
				subline = self.createSub(subtitle_text, start_time, end_time)
				subs[subline["start"]] = subline

			except Exception as e:
				raise ParseError(f"{e}, subtitle_index: {idx}")

		return subs

	def _parse_time_range(self, line):
		sep = line.find("-->")
		start = line[:sep].strip()
		end = line[sep + 3:].strip()
		return self._parse_time(start), self._parse_time(end)

	def _parse_time(self, t):
		# Faster than split-heavy version
		h = int(t[0:2])
		m = int(t[3:5])
		s = int(t[6:8])
		ms = int(t[9:12])
		return (h * 3600 + m * 60 + s) * 1000 + ms

	# ---------------------------
	# Tag helpers (cheap)
	# ---------------------------
	def italicStart(self, text):
		return "<i>" in text.lower()

	def italicEnd(self, text):
		return "</i>" in text.lower()

	def boldStart(self, text):
		return "<b>" in text.lower()

	def boldEnd(self, text):
		return "</b>" in text.lower()

	def underlineStart(self, text):
		return "<u>" in text.lower()

	def underlineEnd(self, text):
		return "</u>" in text.lower()


parserClass = SubRipParser

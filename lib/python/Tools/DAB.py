from Components.International import international
from Tools.ISO639 import LanguageCodes


class DABMetadata:
	# ETSI TS 101 756, tables 9/10: DAB codes are not ISO 639 codes.
	# Reuse Enigma2's language names; only the identifier mapping is DAB-specific.
	LANGUAGE_CODES = {
		0x01: "sq", 0x02: "br", 0x03: "ca", 0x04: "hr", 0x05: "cy",
		0x06: "cs", 0x07: "da", 0x08: "de", 0x09: "en", 0x0A: "es",
		0x0B: "eo", 0x0C: "et", 0x0D: "eu", 0x0E: "fo", 0x0F: "fr",
		0x10: "fy", 0x11: "ga", 0x12: "gd", 0x13: "gl", 0x14: "is",
		0x15: "it", 0x16: "smi", 0x17: "la", 0x18: "lv", 0x19: "lb",
		0x1A: "lt", 0x1B: "hu", 0x1C: "mt", 0x1D: "nl", 0x1E: "no",
		0x1F: "oc", 0x20: "pl", 0x21: "pt", 0x22: "ro", 0x23: "rm",
		0x24: "sr", 0x25: "sk", 0x26: "sl", 0x27: "fi", 0x28: "sv",
		0x29: "tr", 0x2A: "nl", 0x2B: "wa",
		0x45: "zu", 0x46: "vi", 0x47: "uz", 0x48: "ur", 0x49: "uk",
		0x4A: "th", 0x4B: "te", 0x4C: "tt", 0x4D: "ta", 0x4E: "tg",
		0x4F: "sw", 0x51: "so", 0x52: "si", 0x53: "sn",
		0x56: "ru", 0x57: "qu", 0x58: "ps", 0x59: "pa", 0x5A: "fa",
		0x5B: "pap", 0x5C: "or", 0x5D: "ne", 0x5F: "mr", 0x60: "ro",
		0x61: "ms", 0x62: "mg", 0x63: "mk", 0x64: "lo", 0x65: "ko",
		0x66: "km", 0x67: "kk", 0x68: "kn", 0x69: "ja", 0x6A: "id",
		0x6B: "hi", 0x6C: "he", 0x6D: "ha", 0x6E: "gn", 0x6F: "gu",
		0x70: "el", 0x71: "ka", 0x72: "ff", 0x74: "cv", 0x75: "zh",
		0x76: "my", 0x77: "bg", 0x78: "bn", 0x79: "be", 0x7A: "bm",
		0x7B: "az", 0x7C: "as", 0x7D: "hy", 0x7E: "ar", 0x7F: "am"
	}

	def programmeTypeName(self, value, table):
		"""Format FIG 0/17 using the FIG 0/9 International Table Identifier.

		ETSI TS 101 756 tables 12/13 differ from RDS for codes 30 and 31.
		Do not guess a category until the ensemble's table is known.
		"""
		try:
			code, table = int(value), int(table)
		except (TypeError, ValueError):
			return ""
		if not 1 <= code <= 29:
			return ""
		# Translate on access so GUI language changes do not cache old labels.
		if table == 1:
			names = (
				"", _("News"), _("Current Affairs"), _("Information"), _("Sport"),
				_("Education"), _("Drama"), _("Culture"), _("Science"), _("Varied"),
				_("Pop Music"), _("Rock Music"), _("Easy Listening Music"),
				_("Light Classical"), _("Serious Classical"), _("Other Music"),
				_("Weather/meteorology"), _("Finance/Business"), _("Children's programmes"),
				_("Social Affairs"), _("Religion"), _("Phone In"), _("Travel"),
				_("Leisure"), _("Jazz Music"), _("Country Music"), _("National Music"),
				_("Oldies Music"), _("Folk Music"), _("Documentary")
			)
		elif table == 2:
			names = (
				"", _("News"), _("Information"), _("Sports"), _("Talk"), _("Rock"),
				_("Classic Rock"), _("Adult Hits"), _("Soft Rock"), _("Top 40"),
				_("Country"), _("Oldies"), _("Soft"), _("Nostalgia"), _("Jazz"),
				_("Classical"), _("Rhythm and Blues"), _("Soft Rhythm and Blues"),
				_("Foreign Language"), _("Religious Music"), _("Religious Talk"),
				_("Personality"), _("Public"), _("College"), "", "", "", "", "", _("Weather")
			)
		else:
			return ""
		return names[code]

	def languageName(self, value):
		try:
			code = int(value)
		except (TypeError, ValueError):
			return ""
		languageCode = self.LANGUAGE_CODES.get(code)
		if languageCode:
			languageName = international.getLanguageName(languageCode) or LanguageCodes.get(languageCode, ("", ""))[0]
			return _(languageName) if languageName else ""
		# Values absent from the shared lists, or too ambiguous to map to a
		# narrower ISO language. Translate on access, not at module import.
		match code:
			case 0x40:
				return _("Background sound/clean feed")
			case 0x50:
				return _("Sranan Tongo")
			case 0x54:
				return _("Serbo-Croatian")
			case 0x55:
				return _("Rusyn")
			case 0x5E:
				return _("Ndebele")
			case 0x73:
				return _("Dari")
		return ""


dabMetadata = DABMetadata()

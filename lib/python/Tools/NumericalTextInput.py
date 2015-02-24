# -*- coding: UTF-8 -*-
from enigma import eTimer
from Components.Language import language

# Dict languageCode -> array of strings
MAP_SEARCH = (
	u"%_0",
	u" 1",
	u"abc2",
	u"def3",
	u"ghi4",
	u"jkl5",
	u"mno6",
	u"pqrs7",
	u"tuv8",
	u"wxyz9",
	)
MAP_SEARCH_UPCASE = (
	U"0%_",
	U"1 ",
	U"ABC2",
	U"DEF3",
	U"GHI4",
	U"JKL5",
	U"MNO6",
	U"PQRS7",
	U"TUV8",
	U"WXYZ9",
	)
MAP_DEFAULT = (
	u"0,?!&@=*'+\"()$~%#",
	u" 1.:;/-_",
	u"abc2ABC",
	u"def3DEF",
	u"ghi4GHI",
	u"jkl5JKL",
	u"mno6MNO",
	u"pqrs7PQRS",
	u"tuv8TUV",
	u"wxyz9WXYZ",
	)
MAP_DE = (
	u"0,?!&@=*'+\"()$~%#",
	u" 1.:;/-_",
	u"abcä2ABCÄ",
	u"def3DEF",
	u"ghi4GHI",
	u"jkl5JKL",
	u"mnoö6MNOÖ",
	u"pqrsß7PQRSß",
	u"tuvü8TUVÜ",
	u"wxyz9WXYZ",
	)
MAP_ES = (
	u"0,?!&@=*'+\"()$~%#",
	u" 1.:;/-_",
	u"abcáà2ABCÁÀ",
	u"deéèf3DEFÉÈ",
	u"ghiíì4GHIÍÌ",
	u"jkl5JKL",
	u"mnñoóò6MNÑOÓÒ",
	u"pqrs7PQRS",
	u"tuvúù8TUVÚÙ",
	u"wxyz9WXYZ",
	)
MAP_SE = (
	u"0,?!&@=*'+\"()$~%#",
	u" 1.:;/-_",
	u"abcåä2ABCÅÄ",
	u"defé3DEFÉ",
	u"ghi4GHI",
	u"jkl5JKL",
	u"mnoö6MNOÖ",
	u"pqrs7PQRS",
	u"tuv8TUV",
	u"wxyz9WXYZ",
	)
MAP_CZ = (
	u"0,?'+\"()@$!=&*%#",
	u" 1.:;/-_",
	u"abc2áäčABCÁÄČ",
	u"def3ďéěDEFĎÉĚ",
	u"ghi4íGHIÍ",
	u"jkl5ľĺJKLĽĹ",
	u"mno6ňóöôMNOŇÓÖÔ",
	u"pqrs7řŕšPQRSŘŔŠ",
	u"tuv8ťúůüTUVŤÚŮÜ",
	u"wxyz9ýžWXYZÝŽ",
	)
MAP_PL = (
	u"0,?'+\"()@$!=&*%#",
	u" 1.:;/-_",
	u"abcąć2ABCĄĆ",
	u"defę3DEFĘ",
	u"ghi4GHI",
	u"jklł5JKLŁ",
	u"mnońó6MNOŃÓ",
	u"pqrsś7PQRSŚ",
	u"tuv8TUV",
	u"wxyzźż9WXYZŹŻ",
	)
MAP_RU = (
	u"0,?'+\"()@$!=&*%#",
	u" 1.:;/-_",
	u"abcабвг2ABCАБВГ",
	u"defдежз3DEFДЕЖЗ",
	u"ghiийкл4GHIИЙКЛ",
	u"jklмноп5JKLМНОП",
	u"mnoрсту6MNOРСТУ",
	u"pqrsфхцч7PQRSФХЦЧ",
	u"tuvшщьы8TUVШЩЬЫ",
	u"wxyzъэюя9WXYZЪЭЮЯ",
	)
MAP_NL = (
	u"0,?!&@=*'+\"()$~%#",
	u" 1.:;/-_",
	u"abc2ABC",
	u"deëf3DEËF",
	u"ghiï4GHIÏ",
	u"jkl5JKL",
	u"mno6MNO",
	u"pqrs7PQRS",
	u"tuv8TUV",
	u"wxyz9WXYZ",
	)
MAPPINGS = {
	'de_DE': MAP_DE,
	'es_ES': MAP_ES,
	'sv_SE': MAP_SE,
	'fi_FI': MAP_SE,
	'cs_CZ': MAP_CZ,
	'sk_SK': MAP_CZ,
	'pl_PL': MAP_PL,
	'ru_RU': MAP_RU,
	'nl_NL': MAP_NL,
	}

class NumericalTextInput:
	def __init__(self, nextFunc=None, handleTimeout = True, search = False, mapping = None):
		self.useableChars=None
		self.nextFunction=nextFunc
		if handleTimeout:
			self.timer = eTimer()
			self.timer.callback.append(self.timeout)
		else:
			self.timer = None
		self.lastKey = -1
		self.pos = -1
		if mapping is not None:
			self.mapping = mapping
		elif search:
			self.mapping = MAP_SEARCH
		else:
			self.mapping = MAPPINGS.get(language.getLanguage(), MAP_DEFAULT)

	def setUseableChars(self, useable):
		self.useableChars = unicode(useable)

	def getKey(self, num):
		cnt=0
		if self.lastKey != num:
			if self.lastKey != -1:
				self.nextChar()
			self.lastKey = num
			self.pos = -1
		if self.timer is not None:
			self.timer.start(1000, True)
		while True:
			self.pos += 1
			if len(self.mapping[num]) <= self.pos:
				self.pos = 0
			if self.useableChars:
				pos = self.useableChars.find(self.mapping[num][self.pos])
				if pos == -1:
					cnt += 1
					if cnt < len(self.mapping[num]):
						continue
					else:
						return None
			break
		return self.mapping[num][self.pos]

	def nextKey(self):
		if self.timer is not None:
			self.timer.stop()
		self.lastKey = -1

	def nextChar(self):
		self.nextKey()
		if self.nextFunction:
			self.nextFunction()

	def timeout(self):
		if self.lastKey != -1:
			self.nextChar()

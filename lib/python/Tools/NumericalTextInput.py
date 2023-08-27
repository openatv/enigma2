from six import PY2
from enigma import eTimer
from Components.International import international

MAP_SEARCH_UPCASE = "SearchUpper"  # NOTE: Legacy interface for previous and deprecated versions of NumericalTextInput.
MAP_SEARCH = "SearchLower"

MODES = {
	"DEFAULT": 0,
	"DEFAULTUPPER": 1,
	"DEFAULTLOWER": 2,
	"HEX": 7,
	"HEXUPPER": 8,
	"HEXLOWER": 9,
	"HEXFAST": 10,
	"HEXFASTUPPER": 11,
	"HEXFASTLOWER": 12,
	"HEXFASTLOGICAL": 13,
	"HEXFASTLOGICALUPPER": 14,
	"HEXFASTLOGICALLOWER": 15,
	"NUMBER": 6,
	"SEARCH": 3,
	"SEARCHUPPER": 4,
	"SEARCHLOWER": 5
}

PUNCTUATION0 = "0,?!'\"\\()<>[]{}~^`|"
PUNCTUATION1 = "1 .:;+-*/=_@#$%&"

MAPPINGS = (
	# Text, TextUpper, TextLower, Search, SearchUpper, SearchLower, Number, Hex, HexUpper, HexLower, HexFast, HexFastUpper, HexFastLower, HexLogical, HexLogicalUpper, HexLogicalLower
	(PUNCTUATION0, PUNCTUATION0, PUNCTUATION0, "%_0", "%_0", "%_0", "0", "0", "0", "0", "0", "0", "0", "0Aa", "0A", "0a"),
	(PUNCTUATION1, PUNCTUATION1, PUNCTUATION1, " 1", " 1", " 1", "1", "1AaBbCc", "1ABC", "1abc", "1Aa", "1A", "1a", "1Bb", "1B", "1b"),
	("abc2ABC", "ABC2", "abc2", "abc2ABC", "ABC2", "abc2", "2", "2DdEeFf", "2DEF", "2def", "2Bb", "2B", "2b", "2Cc", "2C", "2c"),
	("def3DEF", "DEF3", "def3", "def3DEF", "DEF3", "def3", "3", "3", "3", "3", "3Cc", "3C", "3c", "3Dd", "3D", "3d"),
	("ghi4GHI", "GHI4", "ghi4", "ghi4GHI", "GHI4", "ghi4", "4", "4", "4", "4", "4Dd", "4D", "4d", "4Ee", "4E", "4e"),
	("jkl5JKL", "JKL5", "jkl5", "jkl5JKL", "JKL5", "jkl5", "5", "5", "5", "5", "5Ee", "5E", "5e", "5Ff", "5F", "5f"),
	("mno6MNO", "MNO6", "mno6", "mno6MNO", "MNO6", "mno6", "6", "6", "6", "6", "6Ff", "6F", "6f", "6", "6", "6"),
	("pqrs7PQRS", "PQRS7", "pqrs7", "pqrs7PQRS", "PQRS7", "pqrs7", "7", "7", "7", "7", "7", "7", "7", "7", "7", "7"),
	("tuv8TUV", "TUV8", "tuv8", "tuv8TUV", "TUV8", "tuv8", "8", "8", "8", "8", "8", "8", "8", "8", "8", "8"),
	("wxyz9WXYZ", "WXYZ9", "wxyz9", "wxyz9WXYZ", "WXYZ9", "wxyz9", "9", "9", "9", "9", "9", "9", "9", "9", "9", "9")
)

LOCALES = {
	"cs_CZ": (
		(None, None, None),
		(None, None, None),
		("abc2\u00E1\u010DABC\u00C1\u010C", "ABC2\u00C1\u010C", "abc2\u00E1\u010D"),
		("def3\u010F\u00E9\u011BDEF\u010E\u00C9\u011A", "DEF3\u010E\u00C9\u011A", "def3\u010F\u00E9\u011B"),
		("ghi4\u00EDGHI\u00CD", "GHI4\u00CD", "ghi4\u00ED"),
		(None, None, None),
		("mno6\u0148\u00F3MNO\u0147\u00D3", "MNO6\u0147\u00D3", "mno6\u0148\u00F3"),
		("pqrs7\u0159\u0161PQRS\u0158\u0160", "PQRS7\u0158\u0160", "pqrs7\u0159\u0161"),
		("tuv8\u0165\u00FA\u016FTUV\u0164\u00DA\u016E", "TUV8\u0164\u00DA\u016E", "tuv8\u0165\u00FA\u016F"),
		("wxyz9\u00FD\u017EWXYZ\u00DD\u017D", "WXYZ9\u00DD\u017D", "wxyz9\u00FD\u017E")
	),
	"de_DE": (
		(None, None, None),
		(None, None, None),
		("abc\u00E4\u00E0\u00E5\u01012ABC\u00C4\u00C0\u00C5\u0100", "ABC\u00C42", "abc\u00E42"),
		("def\u0111\u00E9\u01133DEF\u0110\u00C9\u0112", "DEF\u0110\u00C9\u01123", "def\u0111\u00E9\u01133"),
		(None, None, None),
		(None, None, None),
		("mno\u00F66MNO\u00D6", "MNO\u00D66", "mno\u00F66"),
		("pqrs\u00DF7PQRS", "PQRS7", "pqrs\u00DF7"),
		("tuv\u00FC8TUV\u00DC", "TUV\u00DC8", "tuv\u00FC8"),
		(None, None, None)
	),
	"es_ES": (
		(None, None, None),
		(None, None, None),
		("abc\u00E1\u00E0\u00E72ABC\u00C1\u00C0\u00C7", "ABC\u00C1\u00C0\u00C72", "abc\u00E1\u00E0\u00E72"),
		("def\u00E9\u00E83DEF\u00C9\u00C8", "DEF\u00C9\u00C83", "def\u00E9\u00E83"),
		("ghi\u00ED\u00EF4GHI\u00CD\u00CF", "GHI\u00CD\u00CF4", "ghi\u00ED\u00EF4"),
		(None, None, None),
		("mno\u00F1\u00F3\u00F26MNO\u00D1\u00D3\u00D2", "MNO\u00D1\u00D3\u00D26", "mno\u00F1\u00F3\u00F26"),
		(None, None, None),
		("tuv\u00FA\u00FC8TUV\u00DA\u00DC", "TUV\u00DA\u00DC8", "tuv\u00FA\u00FC8"),
		(None, None, None)
	),
	"et_EE": (
		(None, None, None),
		(None, None, None),
		("abc\u00E42ABC\u00C4", "ABC\u00C42", "abc\u00E42"),
		(None, None, None),
		(None, None, None),
		(None, None, None),
		("mno\u00F5\u00F66MNO\u00D5\u00D6", "MNO\u00D5\u00D66", "mno\u00F5\u00F66"),
		("pqrs\u01617PQRS\u0160", "PQRS\u01607", "pqrs\u01617"),
		("tuv\u00FC8TUV\u00DC", "TUV\u00DC8", "tuv\u00FC8"),
		("wxyz\u017E9WXYZ\u017D", "WXYZ\u017D9", "wxyz\u017E9")
	),
	"fa_IR": (
		("\u06F0" + PUNCTUATION0, "\u06F0" + PUNCTUATION0, "\u06F0" + PUNCTUATION0),
		("\u06F1" + PUNCTUATION1, "\u06F1" + PUNCTUATION1, "\u06F1" + PUNCTUATION1),
		("\u0628\u067E\u062A\u0629\u062B\u06F2abc2DEF", "\u0628\u067E\u062A\u0629\u062B\u06F2ABC2", "\u0628\u067E\u062A\u0629\u062B\u06F2abc2"),
		("\u0627\u0623\u0625\u0622\u0624\u0626\u0621\u06F3def3DEF", "\u0627\u0623\u0625\u0622\u0624\u0626\u0621\u06FDEF3", "\u0627\u0623\u0625\u0622\u0624\u0626\u0621\u06F3def3"),
		("\u0633\u0634\u0635\u0636\u06F4ghi4GHI", "\u0633\u0634\u0635\u0636\u06F4GHI4", "\u0633\u0634\u0635\u0636\u06F4ghi4"),
		("\u062F\u0630\u0631\u0632\u0698\u06F5jkl5JKL", "\u062F\u0630\u0631\u0632\u0698\u06F5JKL5", "\u062F\u0630\u0631\u0632\u0698\u06F5jkl5"),
		("\u062C\u0686\u062D\u062E\u06F6mno6MNO", "\u062C\u0686\u062D\u062E\u06F6MNO6", "\u062C\u0686\u062D\u062E\u06F6mno6"),
		("\u0646\u0648\u0647\u06CC\u06F7pqrs7PQRS", "\u0646\u0648\u0647\u06CC\u06F7PQRS7", "\u0646\u0648\u0647\u06CC\u06F7pqrs7"),
		("\u0641\u0642\u06A9\u06AF\u0644\u0645\u0643\u06F8tuv8TUV", "\u0641\u0642\u06A9\u06AF\u0644\u0645\u0643\u06F8TUV8", "\u0641\u0642\u06A9\u06AF\u0644\u0645\u0643\u06F8tuv8"),
		("\u0637\u0638\u0639\u063A\u06F9wxyz9WXYZ", "\u0637\u0638\u0639\u063A\u06F9WXYZ9", "\u0637\u0638\u0639\u063A\u06F9wxyz9"),
	),
	"fi_FI": (
		(None, None, None),
		(None, None, None),
		("abc\u00E4\u00E5\u00E1\u00E2\u010D2ABC\u00C4\u00C5\u00C1\u00C2\u010C", "ABC\u00C4\u00C5\u00C1\u00C2\u010C2", "abc\u00E4\u00E5\u00E1\u00E2\u010D2"),
		("def\u00E9\u01113DEF\u00C9\u0110", "DEF\u00C9\u01103", "def\u00E9\u01113"),
		("ghi\u01E7\u01E54GHI\u01E6\u01E4", "GHI\u01E6\u01E44", "ghi\u01E7\u01E54"),
		("jkl\u01E95JKL\u01E8", "JKL\u01E85", "jkl\u01E95"),
		("mno\u00F6\u00F8\u014B\u00F56MNO\u00D6\u00D8\u014A\u00D5", "MNO\u00D6\u00D8\u014A\u00D56", "mno\u00F6\u00F8\u014B\u00F56"),
		("pqrs\u01617PQRS\u0160", "PQRS\u01607", "pqrs\u01617"),
		("tuv\u00FC\u01678TUV\u00DC\u0166", "TUV\u00DC\u01668", "tuv\u00FC\u01678"),
		("wxyz\u017E\u0292\u01EF9WXYZ\u017D\u01B7\u01EE", "WXYZ\u017D\u01B7\u01EE9", "wxyz\u017E\u0292\u01EF9")
	),
	"lv_LV": (
		(None, None, None),
		(None, None, None),
		("a\u0101bc\u010D2A\u0100BC\u010C", "A\u0100BC\u010C2", "a\u0101bc\u010D2"),
		("de\u0113f3DE\u0112F", "DE\u0112F3", "de\u0113f3"),
		("g\u0123hi\u012B4G\u0122HI\u012A", "G\u0122HI\u012A4", "g\u0123hi\u012B4"),
		("jk\u0137l\u013C5JK\u0136L\u013B", "JK\u0136L\u013B5", "jk\u0137l\u013C5"),
		("mn\u0146o6MN\u0145O", "MN\u0145O6", "mn\u0146o6"),
		("prs\u01617qPRS\u0160Q", "PRS\u01607Q", "prs\u01617q"),
		("tu\u016Bv8TU\u016AV", "TU\u016AV8", "tu\u016Bv8"),
		("z\u017E9wxyWXYZ\u017D", "Z\u017D9WXY", "z\u017E9wxy")
	),
	"nl_NL": (
		(None, None, None),
		(None, None, None),
		(None, None, None),
		("def\u00EB3DEF\u00CB", "DEF\u00CB3", "def\u00EB3"),
		("ghi\u00EF4GHI\u00CF", "GHI\u00CF4", "ghi\u00EF4"),
		(None, None, None),
		(None, None, None),
		(None, None, None),
		(None, None, None),
		(None, None, None),
	),
	"pl_PL": (
		(None, None, None),
		(None, None, None),
		("abc\u0105\u01072ABC\u0104\u0106", "ABC\u0104\u01062", "abc\u0105\u01072"),
		("def\u01193DEF\u0118", "DEF\u01183", "def\u01193"),
		(None, None, None),
		("jkl\u01425JKL\u0141", "JKL\u01415", "jkl\u01425"),
		("mno\u0144\u00F36MNO\u0143\u00D3", "MNO\u0143\u00D36", "mno\u0144\u00F36"),
		("pqrs\u015B7PQRS\u015A", "PQRS\u015A7", "pqrs\u015B7"),
		(None, None, None),
		("wxyz\u017A\u017C9WXYZ\u0179\u017B", "WXYZ\u0179\u017B9", "wxyz\u017A\u017C9")
	),
	"ru_RU": (
		(None, None, None),
		(None, None, None),
		("\u0430\u0431\u0432\u0433abc2\u0410\u0411\u0412\u0413ABC", "\u0410\u0411\u0412\u0413ABC2", "\u0430\u0431\u0432\u0433abc2"),
		("\u0434\u0435\u0451\u0436\u0437def3\u0414\u0415\u0431\u0416\u0417DEF", "\u0414\u0415\u0431\u0416\u0417DEF3", "\u0434\u0435\u0451\u0436\u0437def3"),
		("\u0438\u0439\u043A\u043Bghi4\u0418\u0419\u041A\u041BGHI", "\u0418\u0419\u041A\u041BGHI4", "\u0438\u0439\u043A\u043Bghi4"),
		("\u043C\u043D\u043E\u043Fjkl5\u041C\u041D\u041E\u041FJKL", "\u041C\u041D\u041E\u041FJKL5", "\u043C\u043D\u043E\u043Fjkl5"),
		("\u0440\u0441\u0442\u0443mno6\u0420\u0421\u0422\u0423MNO", "\u0420\u0421\u0422\u0423MNO6", "\u0440\u0441\u0442\u0443mno6"),
		("\u0444\u0445\u0446\u0447pqrs7\u0424\u0425\u0426\u0427PQRS", "\u0424\u0425\u0426\u0427PQRS7", "\u0444\u0445\u0446\u0447pqrs7"),
		("\u0448\u0449\u044A\u044Btuv8\u0428\u0429\u042C\u042BTUV", "\u0428\u0429\u042A\u042BTUV8", "\u0448\u0449\u044A\u044Btuv8"),
		("\u044C\u044D\u044E\u044Fwxyz9\u042C\u042D\u042E\u042FWXYZ", "\u042C\u042D\u042E\u042FWXYZ9", "\u044C\u044D\u044E\u044Fwxyz9")
	),
	"sv_SE": (
		(None, None, None),
		(None, None, None),
		("abc\u00E5\u00E4\u00E0\u00E6\u00E1\u010D2ABC\u00C5\u00C4\u00C0\u00C6\u00C1\u010C", "ABC\u00C5\u00C4\u00C0\u00C6\u00C1\u010C2", "abc\u00E5\u00E4\u00E0\u00E6\u00E1\u010D2"),
		("def\u00E9\u01113DEF\u00C9\u0110", "DEF\u00C9\u01103", "def\u00E9\u01113"),
		("ghi\u00EF4GHI\u00CF", "GHI\u00CF4", "ghi\u00EF4"),
		(None, None, None),
		("mno\u00F6\u00F8\u014B6MNO\u00D6\u00D8\u014A", "MNO\u00D6\u00D8\u014A6", "mno\u00F6\u00F8\u014B6"),
		("pqrs\u01617PQRS\u0160", "PQRS\u01607", "pqrs\u01617"),
		("tuv\u00FC\u01678TUV\u00DC\u0166", "TUV\u00DC\u01668", "tuv\u00FC\u01678"),
		("wxyz\u017E9WXYZ\u017D", "WXYZ\u017D9", "wxyz\u017E9")
	),
	"sk_SK": (
		(None, None, None),
		(None, None, None),
		("abc\u00E1\u010D\u00E42ABC\u00C1\u010C\u00C4", "ABC\u00C1\u010C\u00C42", "abc\u00E1\u010D\u00E42"),
		("def\u010F\u00E93DEF\u010E\u00C9", "DEF\u010E\u00C93", "def\u010F\u00E93"),
		("ghi\u00ED4GHI\u00CD", "GHI\u00CD4", "ghiGHI\u00CD4"),
		("jkl\u013A\u013E5JKL\u0139\u013D", "JKL\u0139\u013D5", "jkl\u013A\u013E5"),
		("mno\u0148\u00F3\u00F4\u00F6\u01516MNO\u0147\u00D3\u00D4\u00D6\u0150", "MNO\u0147\u00D3\u00D4\u00D6\u01506", "mno\u0148\u00F3\u00F4\u00F6\u01516"),
		("pqrs\u0155\u01617PQRS\u0154\u0160", "PQRS\u0154\u01607", "pqrs\u0155\u01617"),
		("tuv\u0165\u00FA\u00FC\u01718TUV\u0164\u00DA\u00DC\u0170", "TUV\u0164\u00DA\u00DC\u01708", "tuv\u0165\u00FA\u00FC\u01718"),
		("wxyz\u00FD\u017E9WXYZ\u00DD\u017D", "WXYZ\u00DD\u017D9", "wxyz\u00FD\u017E9")
	),
	"uk_UA": (
		(None, None, None),
		(None, None, None),
		("\u0430\u0431\u0432\u0433\u0491abc2\u0410\u0411\u0412\u0413\u0490ABC", "\u0410\u0411\u0412\u0413\u0490ABC2", "\u0430\u0431\u0432\u0433\u0491abc2"),
		("\u0434\u0435\u0454\u0436\u0437def3\u0414\u0415\u0404\u0416\u0417DEF", "\u0414\u0415\u0404\u0416\u0417\u0401DEF3", "\u0434\u0435\u0454\u0436\u0437def3"),
		("\u0438\u0456\u0457\u0439\u043A\u043Bghi4\u0418\u0406\u0407\u0419\u041A\u041BGHI", "\u0418\u0406\u0407\u0419\u041A\u041BGHI4", "\u0438\u0456\u0457\u0439\u043A\u043Bghi4"),
		("\u043C\u043D\u043E\u043Fjkl5\u041C\u041D\u041E\u041FJKL", "\u041C\u041D\u041E\u041FDJKL5", "\u043C\u043D\u043E\u043Fjkl5"),
		("\u0440\u0441\u0442\u0443mno6\u0420\u0421\u0422\u0423MNO", "\u0420\u0421\u0422\u0423MNO6", "\u0440\u0441\u0442\u0443mno6"),
		("\u0444\u0445\u0446\u0447pqrs7\u0424\u0425\u0426\u0427PQRS", "\u0424\u0425\u0426\u0427PQRS7", "\u0444\u0445\u0446\u0447pqrs7"),
		("\u0448\u0449tuv8\u0428\u0429TUV", "\u0428\u0429TUV8", "\u0448\u0449tuv8"),
		("\u044E\u044F\u044Cwxyz9\u042E\u042F\u042CWXYZ", "\u042E\u042F\u042CWXYZ9", "\u044E\u044F\u044Cwxyz9")
	)
}


# For more information about using NumericalTextInput see /doc/NUMERICALTEXTINPUT
#
class NumericalTextInput:
	def __init__(self, nextFunc=None, handleTimeout=True, search=False, mapping=None, mode=None):
		self.nextFunction = nextFunc
		if handleTimeout:
			self.timer = eTimer()
			self.timer.callback.append(self.timeout)
		else:
			self.timer = None
		if mapping and isinstance(mapping, (list, tuple)):
			self.mapping = mapping
		else:
			if mode is None:
				if search:  # NOTE: This will be removed when deprecated "search" is removed and "mode" is widely adopted.
					mode = "Search"
				if isinstance(mapping, str):  # NOTE: Legacy interface for previous and deprecated versions of NumericalTextInput.
					mode = mapping
			self.setMode(mode)
		# The key mapping lists naturally restricts character input to
		# the listed characters, this restriction is not enforced for
		# external keyboard input!
		self.useableChars = "".join(self.mapping)  # This limits data entry to only characters in the mapping lists.
		# print("[NumericalTextInput] DEBUG: Mode='%s', Index=%d, Character set: '%s'" % (mode, index, "".join(sorted(self.useableChars))))
		self.lastKey = -1
		self.pos = -1

	def setMode(self, mode):
		index = MODES.get(str(mode).upper(), 0)
		self.mapping = []
		for num in range(10):
			self.mapping.append((MAPPINGS[num][index]))
		locale = LOCALES.get(international.getLocale(), None)
		if locale is not None and index in list(range(6)):
			index = index % 3
			for num in range(10):
				if locale[num][index] is not None:
					self.mapping[num] = locale[num][index]
		self.mapping = tuple(self.mapping)

	def timeout(self):
		if self.lastKey != -1:
			self.nextChar()

	def nextChar(self):
		self.nextKey()
		if self.nextFunction:
			self.nextFunction()

	def nextKey(self):
		if self.timer is not None:
			self.timer.stop()
		self.lastKey = -1

	def getKey(self, num):
		if self.lastKey != num:
			if self.lastKey != -1:
				self.nextChar()
			self.lastKey = num
			self.pos = -1
		if self.timer is not None:
			self.timer.start(1000, True)
		length = len(self.mapping[num])
		cnt = length
		while True:
			self.pos += 1
			if self.pos >= length:
				self.pos = 0
			if not self.useableChars or self.useableChars.find(self.mapping[num][self.pos]) != -1:
				break
			cnt -= 1
			if cnt == 0:
				return None
		return self.mapping[num][self.pos]

	def setUseableChars(self, useable):
		self.useableChars = unicode(useable) if PY2 else str(useable)

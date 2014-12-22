# -*- coding: UTF-8 -*-
from enigma import eListboxPythonMultiContent, gFont, RT_HALIGN_CENTER, RT_VALIGN_CENTER, getPrevAsciiCode, getDesktop
from Screens.Screen import Screen
from Components.Language import language
from Components.ActionMap import NumberActionMap
from Components.Sources.StaticText import StaticText
from Components.Input import Input
from Components.Label import Label
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest, MultiContentEntryPixmapAlphaBlend
from Tools.Directories import resolveFilename, SCOPE_ACTIVE_SKIN
from Tools.LoadPixmap import LoadPixmap
from Tools.NumericalTextInput import NumericalTextInput

class VirtualKeyBoardList(MenuList):
	def __init__(self, list, enableWrapAround=False):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		self.l.setFont(0, gFont("Regular", 28))
		self.l.setFont(1, gFont("Regular", 34))
		self.l.setItemHeight(45)

class VirtualKeyBoardEntryComponent:
	def __init__(self):
		pass

class VirtualKeyBoard(Screen):
	def __init__(self, session, title="", **kwargs):
		Screen.__init__(self, session)
		self.setTitle(_(title))
		self.keys_list = []
		self.shiftkeys_list = []
		self.lang = language.getLanguage()
		self.nextLang = None
		self.shiftMode = False
		self.selectedKey = 0
		self.smsChar = None
		self.sms = NumericalTextInput(self.smsOK)

		self.key_bg = LoadPixmap(path=resolveFilename(SCOPE_ACTIVE_SKIN, "buttons/vkey_bg.png"))
		self.key_sel = LoadPixmap(path=resolveFilename(SCOPE_ACTIVE_SKIN, "buttons/vkey_sel.png"))
		self.key_backspace = LoadPixmap(path=resolveFilename(SCOPE_ACTIVE_SKIN, "buttons/vkey_backspace.png"))
		self.key_all = LoadPixmap(path=resolveFilename(SCOPE_ACTIVE_SKIN, "buttons/vkey_all.png"))
		self.key_clr = LoadPixmap(path=resolveFilename(SCOPE_ACTIVE_SKIN, "buttons/vkey_clr.png"))
		self.key_esc = LoadPixmap(path=resolveFilename(SCOPE_ACTIVE_SKIN, "buttons/vkey_esc.png"))
		self.key_ok = LoadPixmap(path=resolveFilename(SCOPE_ACTIVE_SKIN, "buttons/vkey_ok.png"))
		self.key_shift = LoadPixmap(path=resolveFilename(SCOPE_ACTIVE_SKIN, "buttons/vkey_shift.png"))
		self.key_shift_sel = LoadPixmap(path=resolveFilename(SCOPE_ACTIVE_SKIN, "buttons/vkey_shift_sel.png"))
		self.key_space = LoadPixmap(path=resolveFilename(SCOPE_ACTIVE_SKIN, "buttons/vkey_space.png"))
		self.key_left = LoadPixmap(path=resolveFilename(SCOPE_ACTIVE_SKIN, "buttons/vkey_left.png"))
		self.key_right = LoadPixmap(path=resolveFilename(SCOPE_ACTIVE_SKIN, "buttons/vkey_right.png"))

		self.keyImages =  {
				"BACKSPACE": self.key_backspace,
				"ALL": self.key_all,
				"EXIT": self.key_esc,
				"OK": self.key_ok,
				"SHIFT": self.key_shift,
				"SPACE": self.key_space,
				"LEFT": self.key_left,
				"RIGHT": self.key_right
			}
		self.keyImagesShift = {
				"BACKSPACE": self.key_backspace,
				"CLEAR": self.key_clr,
				"EXIT": self.key_esc,
				"OK": self.key_ok,
				"SHIFT": self.key_shift_sel,
				"SPACE": self.key_space,
				"LEFT": self.key_left,
				"RIGHT": self.key_right
			}

		self["country"] = StaticText("")
		self["header"] = Label()
		self["text"] = Input(currPos=len(kwargs.get("text", "").decode("utf-8",'ignore')), allMarked=False, **kwargs)
		self["list"] = VirtualKeyBoardList([])

		self["actions"] = NumberActionMap(["OkCancelActions", "WizardActions", "ColorActions", "KeyboardInputActions", "InputBoxActions", "InputAsciiActions"],
			{
				"gotAsciiCode": self.keyGotAscii,
				"ok": self.okClicked,
				"OKLong": self.okLongClicked,
				"cancel": self.exit,
				"left": self.left,
				"right": self.right,
				"up": self.up,
				"down": self.down,
				"red": self.exit,
				"green": self.ok,
				"yellow": self.switchLang,
				"blue": self.shiftClicked,
				"deleteBackward": self.backClicked,
				"deleteForward": self.forwardClicked,
				"back": self.exit,
				"pageUp": self.cursorRight,
				"pageDown": self.cursorLeft,
				"1": self.keyNumberGlobal,
				"2": self.keyNumberGlobal,
				"3": self.keyNumberGlobal,
				"4": self.keyNumberGlobal,
				"5": self.keyNumberGlobal,
				"6": self.keyNumberGlobal,
				"7": self.keyNumberGlobal,
				"8": self.keyNumberGlobal,
				"9": self.keyNumberGlobal,
				"0": self.keyNumberGlobal,
			}, -2)
		self.setLang()
		self.onExecBegin.append(self.setKeyboardModeAscii)
		self.onLayoutFinish.append(self.buildVirtualKeyBoard)
		self.onClose.append(self.__onClose)

	def __onClose(self):
		self.sms.timer.stop()

	def switchLang(self):
		self.lang = self.nextLang
		self.setLang()
		self.buildVirtualKeyBoard()

	def setLang(self):
		if self.lang == 'de_DE':
			self.keys_list = [
				[u"EXIT", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"BACKSPACE"],
				[u"q", u"w", u"e", u"r", u"t", u"z", u"u", u"i", u"o", u"p", u"ü", u"+"],
				[u"a", u"s", u"d", u"f", u"g", u"h", u"j", u"k", u"l", u"ö", u"ä", u"#"],
				[u"<", u"y", u"x", u"c", u"v", u"b", u"n", u"m", u",", ".", u"-", u"ALL"],
				[u"SHIFT", u"SPACE", u"@", u"ß", u"OK", u"LEFT", u"RIGHT"]]
			self.shiftkeys_list = [
				[u"EXIT", u"!", u'"', u"§", u"$", u"%", u"&", u"/", u"(", u")", u"=", u"BACKSPACE"],
				[u"Q", u"W", u"E", u"R", u"T", u"Z", u"U", u"I", u"O", u"P", u"Ü", u"*"],
				[u"A", u"S", u"D", u"F", u"G", u"H", u"J", u"K", u"L", u"Ö", u"Ä", u"'"],
				[u">", u"Y", u"X", u"C", u"V", u"B", u"N", u"M", u";", u":", u"_", u"CLEAR"],
				[u"SHIFT", u"SPACE", u"?", u"\\", u"OK", u"LEFT", u"RIGHT"]]
			self.nextLang = 'es_ES'
		elif self.lang == 'es_ES':
			#still missing keys (u"ùÙ")
			self.keys_list = [
				[u"EXIT", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"BACKSPACE"],
				[u"q", u"w", u"e", u"r", u"t", u"z", u"u", u"i", u"o", u"p", u"ú", u"+"],
				[u"a", u"s", u"d", u"f", u"g", u"h", u"j", u"k", u"l", u"ó", u"á", u"#"],
				[u"<", u"y", u"x", u"c", u"v", u"b", u"n", u"m", u",", ".", u"-", u"ALL"],
				[u"SHIFT", u"SPACE", u"@", u"Ł", u"ŕ", u"é", u"č", u"í", u"ě", u"ń", u"ň", u"OK"]]
			self.shiftkeys_list = [
				[u"EXIT", u"!", u'"', u"§", u"$", u"%", u"&", u"/", u"(", u")", u"=", u"BACKSPACE"],
				[u"Q", u"W", u"E", u"R", u"T", u"Z", u"U", u"I", u"O", u"P", u"Ú", u"*"],
				[u"A", u"S", u"D", u"F", u"G", u"H", u"J", u"K", u"L", u"Ó", u"Á", u"'"],
				[u">", u"Y", u"X", u"C", u"V", u"B", u"N", u"M", u";", u":", u"_", u"CLEAR"],
				[u"SHIFT", u"SPACE", u"?", u"\\", u"Ŕ", u"É", u"Č", u"Í", u"Ě", u"Ń", u"Ň", u"OK"]]
			self.nextLang = 'fi_FI'
		elif self.lang == 'fi_FI':
			self.keys_list = [
				[u"EXIT", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"BACKSPACE"],
				[u"q", u"w", u"e", u"r", u"t", u"z", u"u", u"i", u"o", u"p", u"é", u"+"],
				[u"a", u"s", u"d", u"f", u"g", u"h", u"j", u"k", u"l", u"ö", u"ä", u"#"],
				[u"<", u"y", u"x", u"c", u"v", u"b", u"n", u"m", u",", ".", u"-", u"ALL"],
				[u"SHIFT", u"SPACE", u"@", u"ß", u"ĺ", u"OK", u"LEFT", u"RIGHT"]]
			self.shiftkeys_list = [
				[u"EXIT", u"!", u'"', u"§", u"$", u"%", u"&", u"/", u"(", u")", u"=", u"BACKSPACE"],
				[u"Q", u"W", u"E", u"R", u"T", u"Z", u"U", u"I", u"O", u"P", u"É", u"*"],
				[u"A", u"S", u"D", u"F", u"G", u"H", u"J", u"K", u"L", u"Ö", u"Ä", u"'"],
				[u">", u"Y", u"X", u"C", u"V", u"B", u"N", u"M", u";", u":", u"_", u"CLEAR"],
				[u"SHIFT", u"SPACE", u"?", u"\\", u"Ĺ", u"OK", u"LEFT", u"RIGHT"]]
			self.nextLang = 'ru_RU'
		elif self.lang == 'ru_RU':
			self.keys_list = [
				[u"EXIT", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"BACKSPACE"],
				[u"а", u"б", u"в", u"г", u"д", u"е", u"ё", u"ж", u"з", u"и", u"й", u"+"],
				[u"к", u"л", u"м", u"н", u"о", u"п", u"р", u"с", u"т", u"у", u"ф", u"#"],
				[u"<", u"х", u"ц", u"ч", u"ш", u"щ", u"ъ", u"ы", u",", u".", u"-", u"ALL"],
				[u"SHIFT", u"SPACE", u"@", u"ь", u"э", u"ю", u"я", u"OK", u"LEFT", u"RIGHT"]]
			self.shiftkeys_list = [
				[u"EXIT", u"!", u'"', u"§", u"$", u"%", u"&", u"/", u"(", u")", u"=", u"BACKSPACE"],
				[u"А", u"Б", u"В", u"Г", u"Д", u"Е", u"Ё", u"Ж", u"З", u"И", u"Й", u"*"],
				[u"К", u"Л", u"М", u"Н", u"О", u"П", u"Р", u"С", u"Т", u"У", u"Ф", u"'"],
				[u">", u"Х", u"Ц", u"Ч", u"Ш", u"Щ", u"Ъ", u"Ы", u";", u":", u"_", u"CLEAR"],
				[u"SHIFT", u"SPACE", u"?", u"\\", u"Ь", u"Э", u"Ю", u"Я", u"OK", u"LEFT", u"RIGHT"]]
			self.nextLang = 'sv_SE'
		elif self.lang == 'sv_SE':
			self.keys_list = [
				[u"EXIT", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"BACKSPACE"],
				[u"q", u"w", u"e", u"r", u"t", u"z", u"u", u"i", u"o", u"p", u"é", u"+"],
				[u"a", u"s", u"d", u"f", u"g", u"h", u"j", u"k", u"l", u"ö", u"ä", u"#"],
				[u"<", u"y", u"x", u"c", u"v", u"b", u"n", u"m", u",", ".", u"-", u"ALL"],
				[u"SHIFT", u"SPACE", u"@", u"ß", u"ĺ", u"OK", u"LEFT", u"RIGHT"]]
			self.shiftkeys_list = [
				[u"EXIT", u"!", u'"', u"§", u"$", u"%", u"&", u"/", u"(", u")", u"=", u"BACKSPACE"],
				[u"Q", u"W", u"E", u"R", u"T", u"Z", u"U", u"I", u"O", u"P", u"É", u"*"],
				[u"A", u"S", u"D", u"F", u"G", u"H", u"J", u"K", u"L", u"Ö", u"Ä", u"'"],
				[u">", u"Y", u"X", u"C", u"V", u"B", u"N", u"M", u";", u":", u"_", u"CLEAR"],
				[u"SHIFT", u"SPACE", u"?", u"\\", u"Ĺ", u"OK", u"LEFT", u"RIGHT"]]
			self.nextLang = 'sk_SK'
		elif self.lang =='sk_SK':
			self.keys_list = [
				[u"EXIT", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"BACKSPACE"],
				[u"q", u"w", u"e", u"r", u"t", u"z", u"u", u"i", u"o", u"p", u"ú", u"+"],
				[u"a", u"s", u"d", u"f", u"g", u"h", u"j", u"k", u"l", u"ľ", u"@", u"#"],
				[u"<", u"y", u"x", u"c", u"v", u"b", u"n", u"m", u",", ".", u"-", u"ALL"],
				[u"SHIFT", u"SPACE", u"š", u"č", u"ž", u"ý", u"á", u"í", u"é", u"OK", u"LEFT", u"RIGHT"]]
			self.shiftkeys_list = [
				[u"EXIT", u"!", u'"', u"§", u"$", u"%", u"&", u"/", u"(", u")", u"=", u"BACKSPACE"],
				[u"Q", u"W", u"E", u"R", u"T", u"Z", u"U", u"I", u"O", u"P", u"ť", u"*"],
				[u"A", u"S", u"D", u"F", u"G", u"H", u"J", u"K", u"L", u"ň", u"ď", u"'"],
				[u"Á", u"É", u"Ď", u"Í", u"Ý", u"Ó", u"Ú", u"Ž", u"Š", u"Č", u"Ť", u"Ň"],
				[u">", u"Y", u"X", u"C", u"V", u"B", u"N", u"M", u";", u":", u"_", u"CLEAR"],
				[u"SHIFT", u"SPACE", u"?", u"\\", u"ä", u"ö", u"ü", u"ô", u"ŕ", u"ĺ", u"OK"]]
			self.nextLang = 'cs_CZ'
		elif self.lang == 'cs_CZ':
			self.keys_list = [
				[u"EXIT", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"BACKSPACE"],
				[u"q", u"w", u"e", u"r", u"t", u"z", u"u", u"i", u"o", u"p", u"ú", u"+"],
				[u"a", u"s", u"d", u"f", u"g", u"h", u"j", u"k", u"l", u"ů", u"@", u"#"],
				[u"<", u"y", u"x", u"c", u"v", u"b", u"n", u"m", u",", ".", u"-", u"ALL"],
				[u"SHIFT", u"SPACE", u"ě", u"š", u"č", u"ř", u"ž", u"ý", u"á", u"í", u"é", u"OK"]]
			self.shiftkeys_list = [
				[u"EXIT", u"!", u'"', u"§", u"$", u"%", u"&", u"/", u"(", u")", u"=", u"BACKSPACE"],
				[u"Q", u"W", u"E", u"R", u"T", u"Z", u"U", u"I", u"O", u"P", u"ť", u"*"],
				[u"A", u"S", u"D", u"F", u"G", u"H", u"J", u"K", u"L", u"ň", u"ď", u"'"],
				[u">", u"Y", u"X", u"C", u"V", u"B", u"N", u"M", u";", u":", u"_", u"CLEAR"],
				[u"SHIFT", u"SPACE", u"?", u"\\", u"Č", u"Ř", u"Š", u"Ž", u"Ú", u"Á", u"É", u"OK"]]
			self.nextLang = 'el_GR'
		elif self.lang == 'el_GR':
			self.keys_list = [
				[u"EXIT", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"BACKSPACE"],
				[u"=", u"ς", u"ε", u"ρ", u"τ", u"υ", u"θ", u"ι", u"ο", u"π", u"[", u"]"],
				[u"α", u"σ", u"δ", u"φ", u"γ", u"η", u"ξ", u"κ", u"λ", u";", u"'", u"-"],
				[u"\\", u"ζ", u"χ", u"ψ", u"ω", u"β", u"ν", u"μ", u",", ".", u"/", u"ALL"],
				[u"SHIFT", u"SPACE", u"ά", u"έ", u"ή", u"ί", u"ό", u"ύ", u"ώ", u"ϊ", u"ϋ", u"OK"]]
			self.shiftkeys_list = [
				[u"EXIT", u"!", u"@", u"#", u"$", u"%", u"^", u"&", u"*", u"(", u")", u"BACKSPACE"],
				[u"+", u"€", u"Ε", u"Ρ", u"Τ", u"Υ", u"Θ", u"Ι", u"Ο", u"Π", u"{", u"}"],
				[u"Α", u"Σ", u"Δ", u"Φ", u"Γ", u"Η", u"Ξ", u"Κ", u"Λ", u":", u'"', u"_"],
				[u"|", u"Ζ", u"Χ", u"Ψ", u"Ω", u"Β", u"Ν", u"Μ", u"<", u">", u"?", u"CLEAR"],
				[u"SHIFT", u"SPACE", u"Ά", u"Έ", u"Ή", u"Ί", u"Ό", u"Ύ", u"Ώ", u"Ϊ", u"Ϋ", u"OK"]]
			self.nextLang = 'pl_PL'
		elif self.lang == 'pl_PL':
			self.keys_list = [
				[u"EXIT", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"BACKSPACE"],
				[u"q", u"w", u"e", u"r", u"t", u"y", u"u", u"i", u"o", u"p", u"-", u"["],
				[u"a", u"s", u"d", u"f", u"g", u"h", u"j", u"k", u"l", u";", u"'", u"\\"],
				[u"<", u"z", u"x", u"c", u"v", u"b", u"n", u"m", u",", ".", u"/", u"ALL"],
				[u"SHIFT", u"SPACE", u"ą", u"ć", u"ę", u"ł", u"ń", u"ó", u"ś", u"ź", u"ż", u"OK"]]
			self.shiftkeys_list = [
				[u"EXIT", u"!", u"@", u"#", u"$", u"%", u"^", u"&", u"(", u")", u"=", u"BACKSPACE"],
				[u"Q", u"W", u"E", u"R", u"T", u"Y", u"U", u"I", u"O", u"P", u"*", u"]"],
				[u"A", u"S", u"D", u"F", u"G", u"H", u"J", u"K", u"L", u"?", u'"', u"|"],
				[u">", u"Z", u"X", u"C", u"V", u"B", u"N", u"M", u";", u":", u"_", u"CLEAR"],
				[u"SHIFT", u"SPACE", u"Ą", u"Ć", u"Ę", u"Ł", u"Ń", u"Ó", u"Ś", u"Ź", u"Ż", u"OK"]]
			self.nextLang = 'en_EN'
		else:
			self.keys_list = [
				[u"EXIT", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"BACKSPACE"],
				[u"q", u"w", u"e", u"r", u"t", u"y", u"u", u"i", u"o", u"p", u"-", u"["],
				[u"a", u"s", u"d", u"f", u"g", u"h", u"j", u"k", u"l", u";", u"'", u"\\"],
				[u"<", u"z", u"x", u"c", u"v", u"b", u"n", u"m", u",", ".", u"/", u"ALL"],
				[u"SHIFT", u"SPACE", u"OK", u"LEFT", u"RIGHT", u"*"]]
			self.shiftkeys_list = [
				[u"EXIT", u"!", u"@", u"#", u"$", u"%", u"^", u"&", u"(", u")", u"=", u"BACKSPACE"],
				[u"Q", u"W", u"E", u"R", u"T", u"Y", u"U", u"I", u"O", u"P", u"+", u"]"],
				[u"A", u"S", u"D", u"F", u"G", u"H", u"J", u"K", u"L", u"?", u'"', u"|"],
				[u">", u"Z", u"X", u"C", u"V", u"B", u"N", u"M", u";", u":", u"_", u"CLEAR"],
				[u"SHIFT", u"SPACE", u"OK", u"LEFT", u"RIGHT", u"~"]]
			self.lang = 'en_EN'
			self.nextLang = 'de_DE'
		self["country"].setText(self.lang)
		self.max_key=47+len(self.keys_list[4])

	def virtualKeyBoardEntryComponent(self, keys):
		screenwidth = getDesktop(0).size().width()
		key_bg_width = self.key_bg and self.key_bg.size().width() or 45
		key_images = self.shiftMode and self.keyImagesShift or self.keyImages
		res = [keys]
		text = []
		x = 0
		for key in keys:
			png = key_images.get(key, None)
			if png:
				width = png.size().width()
				if screenwidth and screenwidth == 1920:
					res.append(MultiContentEntryPixmapAlphaBlend(pos=(x, 0), size=(width, 68), png=png))
				else:
					res.append(MultiContentEntryPixmapAlphaBlend(pos=(x, 0), size=(width, 45), png=png))
			else:
				width = key_bg_width
				if screenwidth and screenwidth == 1920:
					res.append(MultiContentEntryPixmapAlphaBlend(pos=(x, 0), size=(width, 68), png=self.key_bg))
					text.append(MultiContentEntryText(pos=(x, 0), size=(width, 68), font=1, text=key.encode("utf-8"), flags=RT_HALIGN_CENTER | RT_VALIGN_CENTER))
				else:
					res.append(MultiContentEntryPixmapAlphaBlend(pos=(x, 0), size=(width, 45), png=self.key_bg))
					text.append(MultiContentEntryText(pos=(x, 0), size=(width, 45), font=0, text=key.encode("utf-8"), flags=RT_HALIGN_CENTER | RT_VALIGN_CENTER))
			x += width
		return res + text

	def buildVirtualKeyBoard(self):
		self.previousSelectedKey = None
		self.list = []
		for keys in self.shiftMode and self.shiftkeys_list or self.keys_list:
			self.list.append(self.virtualKeyBoardEntryComponent(keys))
		self.markSelectedKey()

	def markSelectedKey(self):
		screenwidth = getDesktop(0).size().width()
		if self.previousSelectedKey is not None:
			self.list[self.previousSelectedKey /12] = self.list[self.previousSelectedKey /12][:-1]
		width = self.key_sel.size().width()
		x = self.list[self.selectedKey/12][self.selectedKey % 12 + 1][1]
		if screenwidth and screenwidth == 1920:
			self.list[self.selectedKey / 12].append(MultiContentEntryPixmapAlphaBlend(pos=(x, 0), size=(width, 68), png=self.key_sel))
		else:
			self.list[self.selectedKey / 12].append(MultiContentEntryPixmapAlphaBlend(pos=(x, 0), size=(width, 45), png=self.key_sel))
		self.previousSelectedKey = self.selectedKey
		self["list"].setList(self.list)

	def backClicked(self):
		self["text"].deleteBackward()

	def forwardClicked(self):
		self["text"].deleteForward()

	def shiftClicked(self):
		self.smsChar = None
		self.shiftMode = not self.shiftMode
		self.buildVirtualKeyBoard()

	def okClicked(self):
		self.smsChar = None
		text = (self.shiftMode and self.shiftkeys_list or self.keys_list)[self.selectedKey / 12][self.selectedKey % 12].encode("UTF-8")

		if text == "EXIT":
			self.close(None)

		elif text == "BACKSPACE":
			self["text"].deleteBackward()

		elif text == "ALL":
			self["text"].markAll()

		elif text == "CLEAR":
			self["text"].deleteAllChars()
			self["text"].update()

		elif text == "SHIFT":
			self.shiftClicked()

		elif text == "SPACE":
			self["text"].char(" ".encode("UTF-8"))

		elif text == "OK":
			self.close(self["text"].getText().encode("UTF-8"))

		elif text == "LEFT":
			self["text"].left()

		elif text == "RIGHT":
			self["text"].right()

		else:
			self["text"].char(text)

	def okLongClicked(self):
		self.smsChar = None
		text = (self.shiftMode and self.shiftkeys_list or self.keys_list)[self.selectedKey / 12][self.selectedKey % 12].encode("UTF-8")

		if text == "BACKSPACE":
			self["text"].deleteAllChars()
			self["text"].update()

	def ok(self):
		self.close(self["text"].getText().encode("UTF-8"))

	def exit(self):
		self.close(None)

	def cursorRight(self):
		self["text"].right()

	def cursorLeft(self):
		self["text"].left()

	def left(self):
		self.smsChar = None
		self.selectedKey = self.selectedKey / 12 * 12 + (self.selectedKey + 11) % 12
		if self.selectedKey > self.max_key:
			self.selectedKey = self.max_key
		self.markSelectedKey()

	def right(self):
		self.smsChar = None
		self.selectedKey = self.selectedKey / 12 * 12 + (self.selectedKey + 1) % 12
		if self.selectedKey > self.max_key:
			self.selectedKey = self.selectedKey / 12 * 12
		self.markSelectedKey()

	def up(self):
		self.smsChar = None
		self.selectedKey -= 12
		if self.selectedKey < 0:
			self.selectedKey = self.max_key / 12 * 12 + self.selectedKey % 12
			if self.selectedKey > self.max_key:
				self.selectedKey -= 12
		self.markSelectedKey()

	def down(self):
		self.smsChar = None
		self.selectedKey += 12
		if self.selectedKey > self.max_key:
			self.selectedKey %= 12
		self.markSelectedKey()

	def keyNumberGlobal(self, number):
		self.smsChar = self.sms.getKey(number)
		self.selectAsciiKey(self.smsChar)

	def smsOK(self):
		if self.smsChar and self.selectAsciiKey(self.smsChar):
			print "pressing ok now"
			self.okClicked()

	def keyGotAscii(self):
		self.smsChar = None
		if self.selectAsciiKey(str(unichr(getPrevAsciiCode()).encode('utf-8'))):
			self.okClicked()

	def selectAsciiKey(self, char):
		if char == " ":
			char = "SPACE"
		for keyslist in (self.shiftkeys_list, self.keys_list):
			selkey = 0
			for keys in keyslist:
				for key in keys:
					if key == char:
						self.selectedKey = selkey
						if self.shiftMode != (keyslist is self.shiftkeys_list):
							self.shiftMode = not self.shiftMode
							self.buildVirtualKeyBoard()
						else:
							self.markSelectedKey()
						return True
					selkey += 1
		return False

# -*- coding: UTF-8 -*-
from enigma import eListboxPythonMultiContent, gFont, RT_HALIGN_CENTER, RT_VALIGN_CENTER, getPrevAsciiCode
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
import skin

class VirtualKeyBoardList(MenuList):
	def __init__(self, list, enableWrapAround=False):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		font = skin.fonts.get("VirtualKeyboard", ("Regular", 28, 45))
		self.l.setFont(0, gFont(font[0], font[1]))
		self.l.setItemHeight(font[2])

class VirtualKeyBoardEntryComponent:
	def __init__(self):
		pass

class VirtualKeyBoard(Screen):
	def __init__(self, session, title="", **kwargs):
		Screen.__init__(self, session)
		self.setTitle(_("Virtual KeyBoard"))
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
				"CLEAR": self.key_clr,
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
		self["header"] = Label(title)
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
				[u"SHIFT", u"SPACE", u"@", u"ß", u"[", u"]", u"OK", u"LEFT", u"RIGHT"]]
			self.shiftkeys_list = [
				[u"EXIT", u"!", u'"', u"§", u"$", u"%", u"&", u"/", u"(", u")", u"=", u"BACKSPACE"],
				[u"Q", u"W", u"E", u"R", u"T", u"Z", u"U", u"I", u"O", u"P", u"Ü", u"*"],
				[u"A", u"S", u"D", u"F", u"G", u"H", u"J", u"K", u"L", u"Ö", u"Ä", u"'"],
				[u">", u"Y", u"X", u"C", u"V", u"B", u"N", u"M", u";", u":", u"_", u"CLEAR"],
				[u"SHIFT", u"SPACE", u"?", u"\\",u"|",u"^", u"OK", u"LEFT", u"RIGHT"]]
			self.nextLang = 'hu_HU'
		elif self.lang == 'hu_HU':
			self.keys_list = [
				[u"EXIT", u"0", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"BACKSPACE"],
				[u"q", u"w", u"e", u"r", u"t", u"z", u"u", u"i", u"o", u"p", u"ő", u"ú"],
				[u"a", u"s", u"d", u"f", u"g", u"h", u"j", u"k", u"l", u"é", u"á", u"ű"],
				[u"í", u"y", u"x", u"c", u"v", u"b", u"n", u"m", u",", ".", u"-", u"ALL"],
				[u"SHIFT", u"SPACE", u"ö", u"ü", u"ó", u"#", u"@", u"*", u"OK", u"LEFT", u"RIGHT", u"CLEAR"]]
			self.shiftkeys_list = [
				[u"EXIT", u"§", u"'", u'"', u"+", u"!", u"%", u"/", u"=", u"(", u")", u"BACKSPACE"],
				[u"Q", u"W", u"E", u"R", u"T", u"Z", u"U", u"I", u"O", u"P", u"Ő", u"Ú"],
				[u"A", u"S", u"D", u"F", u"G", u"H", u"J", u"K", u"L", u"É", u"Á", u"Ű"],
				[u"Í", u"Y", u"X", u"C", u"V", u"B", u"N", u"M", u"?", u":", u"_", u";"],
				[u"SHIFT", u"Ö", u"Ü", u"Ó", u"&", u"<", u">", u"{", u"}", u"[", u"]", u"\\"]]
			self.nextLang = 'es_ES'
		elif self.lang == 'es_ES':
			self.keys_list = [
				[u"EXIT", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"BACKSPACE"],
				[u"q", u"w", u"e", u"r", u"t", u"y", u"u", u"i", u"o", u"p", u"¡", u"'"],
				[u"a", u"s", u"d", u"f", u"g", u"h", u"j", u"k", u"l", u"ñ", u"ç", u"+"],
				[u"<", u"z", u"x", u"c", u"v", u"b", u"n", u"m", u",", ".", u"-", u"ALL"],
				[u"SHIFT", u"SPACE", u"@", u"á", u"é", u"í", u"ó", u"ú", u"ü", u"º", u"ª", u"OK"]]
			self.shiftkeys_list = [
				[u"EXIT", u"!", u'"', u"·", u"$", u"%", u"&", u"/", u"(", u")", u"=", u"BACKSPACE"],
				[u"Q", u"W", u"E", u"R", u"T", u"Y", u"U", u"I", u"O", u"P", u"¿", u"?"],
				[u"A", u"S", u"D", u"F", u"G", u"H", u"J", u"K", u"L", u"Ñ", u"Ç", u"*"],
				[u">", u"Z", u"X", u"C", u"V", u"B", u"N", u"M", u";", u":", u"_", u"CLEAR"],
				[u"SHIFT", u"SPACE", u"€", u"Á", u"É", u"Í", u"Ó", u"Ú", u"Ü", u"[", u"]", u"OK"]]
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
			self.nextLang = 'lv_LV'
		elif self.lang == 'lv_LV':
			self.keys_list = [
				[u"EXIT", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"BACKSPACE"],
				[u"q", u"w", u"e", u"r", u"t", u"y", u"u", u"i", u"o", u"p", u"-", u"š"],
				[u"a", u"s", u"d", u"f", u"g", u"h", u"j", u"k", u"l", u";", u"'", u"ū"],
				[u"<", u"z", u"x", u"c", u"v", u"b", u"n", u"m", u",", u".", u"ž", u"ALL"],
				[u"SHIFT", u"SPACE", u"ā", u"č", u"ē", u"ģ", u"ī", u"ķ", u"ļ", u"ņ", u"LEFT", u"RIGHT"]]
			self.shiftkeys_list = [
				[u"EXIT", u"!", u"@", u"$", u"*", u"(", u")", u"_", u"=", u"/", u"\\", u"BACKSPACE"],
				[u"Q", u"W", u"E", u"R", u"T", u"Y", u"U", u"I", u"O", u"P", u"+", u"Š"],
				[u"A", u"S", u"D", u"F", u"G", u"H", u"J", u"K", u"L", u":", u'"', u"Ū"],
				[u">", u"Z", u"X", u"C", u"V", u"B", u"N", u"M", u"#", u"?", u"Ž", u"CLEAR"],
				[u"SHIFT", u"SPACE", u"Ā", u"Č", u"Ē", u"Ģ", u"Ī", u"Ķ", u"Ļ", u"Ņ", u"LEFT", u"RIGHT"]]
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
			self.nextLang = 'ar_AE'
		elif self.lang == 'ar_AE':
			self.keys_list = [
				[u"EXIT", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"BACKSPACE"],
				[u"ض", u"ص", u"ث", u"ق", u"ف", u"غ", u"ع", u"ه", u"خ", u"ح", u"ج", u"د"],
				[u"ش", u"س", u"ي", u"ب", u"ل", u"ا", u"ت", u"ن", u"م", u"ك", u"ط", u"#"],
				[u"ئ", u"ء", u"ؤ", u"ر", u"لا", u"ى", u"ة", u"و", u"ز", "ظ", u"ذ", u"ALL"],
				[u"SHIFT", u"SPACE", u"+", u"-", u"*", u"/", u".", u",", u"@", u"%", u"&", u"OK"]]
			self.shiftkeys_list = [
				[u"EXIT", u"!", u'"', u"§", u"$", u"^", u"<", u">", u"(", u")", u"=", u"BACKSPACE"],
				[u"َ", u"ً", u"ُ", u"ٌ", u"لإ", u"إ", u"‘", u"÷", u"×", u"؛", u"<", u">"],
				[u"ِ", u"ٍ", u"]", u"[", u"لأ", u"أ", u"ـ", u"،", u"/", u":", u"~", u"'"],
				[u"ْ", u"}", u"{", u"لآ", u"آ", u"’", u",", u".", u"؟", u":", u"_", u"CLEAR"],
				[u"SHIFT", u"SPACE", u"?", u"\\", u"=", u"ّ", u"~", u"OK"]]
			self.nextLang = 'th_TH'
		elif self.lang == 'th_TH':
			self.keys_list = [[u"EXIT", "\xe0\xb9\x85", "\xe0\xb8\xa0", "\xe0\xb8\x96", "\xe0\xb8\xb8", "\xe0\xb8\xb6", "\xe0\xb8\x84", "\xe0\xb8\x95", "\xe0\xb8\x88", "\xe0\xb8\x82", "\xe0\xb8\x8a", u"BACKSPACE"],
				["\xe0\xb9\x86", "\xe0\xb9\x84", "\xe0\xb8\xb3", "\xe0\xb8\x9e", "\xe0\xb8\xb0", "\xe0\xb8\xb1", "\xe0\xb8\xb5", "\xe0\xb8\xa3", "\xe0\xb8\x99", "\xe0\xb8\xa2", "\xe0\xb8\x9a", "\xe0\xb8\xa5"],
				["\xe0\xb8\x9f", "\xe0\xb8\xab", "\xe0\xb8\x81", "\xe0\xb8\x94", "\xe0\xb9\x80", "\xe0\xb9\x89", "\xe0\xb9\x88", "\xe0\xb8\xb2", "\xe0\xb8\xaa", "\xe0\xb8\xa7", "\xe0\xb8\x87", "\xe0\xb8\x83"],
				["\xe0\xb8\x9c", "\xe0\xb8\x9b", "\xe0\xb9\x81", "\xe0\xb8\xad", "\xe0\xb8\xb4", "\xe0\xb8\xb7", "\xe0\xb8\x97", "\xe0\xb8\xa1", "\xe0\xb9\x83", "\xe0\xb8\x9d", "", u"ALL"],
				[u"SHIFT", u"SPACE", u"OK", u"LEFT", u"RIGHT"]]
			self.shiftkeys_list = [[u"EXIT", "\xe0\xb9\x91", "\xe0\xb9\x92", "\xe0\xb9\x93", "\xe0\xb9\x94", "\xe0\xb8\xb9", "\xe0\xb9\x95", "\xe0\xb9\x96", "\xe0\xb9\x97", "\xe0\xb9\x98", "\xe0\xb9\x99", u"BACKSPACE"],
				["\xe0\xb9\x90", "", "\xe0\xb8\x8e", "\xe0\xb8\x91", "\xe0\xb8\x98", "\xe0\xb9\x8d", "\xe0\xb9\x8a", "\xe0\xb8\x93", "\xe0\xb8\xaf", "\xe0\xb8\x8d", "\xe0\xb8\x90", "\xe0\xb8\x85"],
				["\xe0\xb8\xa4", "\xe0\xb8\x86", "\xe0\xb8\x8f", "\xe0\xb9\x82", "\xe0\xb8\x8c", "\xe0\xb9\x87", "\xe0\xb9\x8b", "\xe0\xb8\xa9", "\xe0\xb8\xa8", "\xe0\xb8\x8b", "", "\xe0\xb8\xbf"],
				["", "", "\xe0\xb8\x89", "\xe0\xb8\xae", "\xe0\xb8\xba", "\xe0\xb9\x8c", "", "\xe0\xb8\x92", "\xe0\xb8\xac", "\xe0\xb8\xa6", "", u"CLEAR"],
				[u"SHIFT", u"SPACE", u"OK", u"LEFT", u"RIGHT"]]
			self.nextLang = 'en_US'
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
				[u"SHIFT", u"SPACE", u"|", u"^", u"OK", u"LEFT", u"RIGHT", u"~"]]
			self.lang = 'en_US'
			self.nextLang = 'de_DE'
		self["country"].setText(self.lang)

	def virtualKeyBoardEntryComponent(self, keys):
		w, h = skin.parameters.get("VirtualKeyboard",(45, 45))
		key_bg_width = self.key_bg and self.key_bg.size().width() or w
		key_images = self.shiftMode and self.keyImagesShift or self.keyImages
		res = [keys]
		text = []
		x = 0
		for key in keys:
			png = key_images.get(key, None)
			if png:
				width = png.size().width()
				res.append(MultiContentEntryPixmapAlphaTest(pos=(x, 0), size=(width, h), png=png))
			else:
				width = key_bg_width
				res.append(MultiContentEntryPixmapAlphaTest(pos=(x, 0), size=(width, h), png=self.key_bg))
				text.append(MultiContentEntryText(pos=(x, 0), size=(width, h), font=0, text=key.encode("utf-8"), flags=RT_HALIGN_CENTER | RT_VALIGN_CENTER))
			x += width
		return res + text

	def buildVirtualKeyBoard(self):
		self.previousSelectedKey = None
		self.list = []
		self.max_key = 0
		for keys in self.shiftMode and self.shiftkeys_list or self.keys_list:
			self.list.append(self.virtualKeyBoardEntryComponent(keys))
			self.max_key += len(keys)
		self.max_key -= 1
		self.markSelectedKey()

	def markSelectedKey(self):
		w, h = skin.parameters.get("VirtualKeyboard",(45, 45))
		if self.previousSelectedKey is not None:
			self.list[self.previousSelectedKey /12] = self.list[self.previousSelectedKey /12][:-1]
		width = self.key_sel.size().width()
		try:
			x = self.list[self.selectedKey/12][self.selectedKey % 12 + 1][1]
		except IndexError:
			self.selectedKey = self.max_key
			x = self.list[self.selectedKey/12][self.selectedKey % 12 + 1][1]
		self.list[self.selectedKey / 12].append(MultiContentEntryPixmapAlphaTest(pos=(x, 0), size=(width, h), png=self.key_sel))
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
			self.close(self["text"].getText())

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
		self.close(self["text"].getText())

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

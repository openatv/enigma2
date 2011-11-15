# -*- coding: UTF-8 -*-
from enigma import eListboxPythonMultiContent, gFont, RT_HALIGN_CENTER, RT_VALIGN_CENTER, getPrevAsciiCode
from Screen import Screen
from Components.Language import language
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN
from Tools.LoadPixmap import LoadPixmap

class VirtualKeyBoardList(MenuList):
	def __init__(self, list, enableWrapAround=False):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		self.l.setFont(0, gFont("Regular", 28))
		self.l.setItemHeight(45)

def VirtualKeyBoardEntryComponent(keys, selectedKey,shiftMode=False):
	key_backspace = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/vkey_backspace.png"))
	key_bg = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/vkey_bg.png"))
	key_clr = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/vkey_clr.png"))
	key_esc = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/vkey_esc.png"))
	key_ok = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/vkey_ok.png"))
	key_sel = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/vkey_sel.png"))
	key_shift = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/vkey_shift.png"))
	key_shift_sel = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/vkey_shift_sel.png"))
	key_space = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/vkey_space.png"))
	res = [ (keys) ]
	
	x = 0
	count = 0
	if shiftMode:
		shiftkey_png = key_shift_sel
	else:
		shiftkey_png = key_shift
	for key in keys:
		width = None
		if key == "EXIT":
			width = key_esc.size().width()
			res.append(MultiContentEntryPixmapAlphaTest(pos=(x, 0), size=(width, 45), png=key_esc))
		elif key == "BACKSPACE":
			width = key_backspace.size().width()
			res.append(MultiContentEntryPixmapAlphaTest(pos=(x, 0), size=(width, 45), png=key_backspace))
		elif key == "CLEAR":
			width = key_clr.size().width()
			res.append(MultiContentEntryPixmapAlphaTest(pos=(x, 0), size=(width, 45), png=key_clr))
		elif key == "SHIFT":
			width = shiftkey_png.size().width()
			res.append(MultiContentEntryPixmapAlphaTest(pos=(x, 0), size=(width, 45), png=shiftkey_png))
		elif key == "SPACE":
			width = key_space.size().width()
			res.append(MultiContentEntryPixmapAlphaTest(pos=(x, 0), size=(width, 45), png=key_space))
		elif key == "OK":
			width = key_ok.size().width()
			res.append(MultiContentEntryPixmapAlphaTest(pos=(x, 0), size=(width, 45), png=key_ok))
		#elif key == "<-":
		#	res.append(MultiContentEntryPixmapAlphaTest(pos=(x, 0), size=(45, 45), png=key_left))
		#elif key == "->":
		#	res.append(MultiContentEntryPixmapAlphaTest(pos=(x, 0), size=(45, 45), png=key_right))
		
		else:
			width = key_bg.size().width()
			res.extend((
				MultiContentEntryPixmapAlphaTest(pos=(x, 0), size=(width, 45), png=key_bg),
				MultiContentEntryText(pos=(x, 0), size=(width, 45), font=0, text=key.encode("utf-8"), flags=RT_HALIGN_CENTER | RT_VALIGN_CENTER)
			))
		
		if selectedKey == count:
			width = key_sel.size().width()
			res.append(MultiContentEntryPixmapAlphaTest(pos=(x, 0), size=(width, 45), png=key_sel))

		if width is not None:
			x += width
		else:
			x += 45
		count += 1
	
	return res


class VirtualKeyBoard(Screen):

	def __init__(self, session, title="", text=""):
		Screen.__init__(self, session)
		self.keys_list = []
		self.shiftkeys_list = []
		self.lang = language.getLanguage()
		self.nextLang = None
		self.shiftMode = False
		self.text = text
		self.selectedKey = 0
		
		self["country"] = StaticText("")
		self["header"] = Label(title)
		self["text"] = Label(self.text)
		self["list"] = VirtualKeyBoardList([])
		
		self["actions"] = ActionMap(["OkCancelActions", "WizardActions", "DirectionActions", "ColorActions", "KeyboardInputActions"],
			{
				"gotAsciiCode": self.keyGotAscii,
				"ok": self.okClicked,
				"cancel": self.exit,
				"left": self.left,
				"right": self.right,
				"up": self.up,
				"down": self.down,
				"red": self.backClicked,
				"green": self.ok,
				"yellow": self.switchLang,
				"blue": self.shiftClicked,
				"deleteBackward": self.backClicked,
				"key_minus": self.key_minus,
				"key_equal": self.key_equal,
				"key_backspace": self.key_backspace,
				"key_q": self.key_q,
				"key_w": self.key_w,
				"key_e": self.key_e,
				"key_r": self.key_r,
				"key_t": self.key_t,
				"key_y": self.key_y,
				"key_u": self.key_u,
				"key_i": self.key_i,
				"key_o": self.key_o,
				"key_p": self.key_p,
				"key_leftbrace": self.key_leftbrace,
				"key_enter": self.key_enter,
				"key_a": self.key_a,
				"key_s": self.key_s,
				"key_d": self.key_d,
				"key_f": self.key_f,
				"key_g": self.key_g,
				"key_h": self.key_h,
				"key_j": self.key_j,
				"key_k": self.key_k,
				"key_l": self.key_l,
				"key_semicolon": self.key_semicolon,
				"key_apostrophe": self.key_apostrophe,
				"key_backslash": self.key_backslash,
				"key_leftshift": self.key_leftshift,
				"key_z": self.key_z,
				"key_x": self.key_x,
				"key_c": self.key_c,
				"key_v": self.key_v,
				"key_b": self.key_b,
				"key_n": self.key_n,
				"key_m": self.key_m,
				"key_comma": self.key_comma,
				"key_dot": self.key_dot,
				"key_slash": self.key_slash,
				"key_rightshift": self.key_rightshift,
				"key_space": self.key_space,
				"key_capslock": self.key_capslock,
				"key_esc": self.key_esc,
				"back": self.exit				
			}, -2)
		self.setLang()
		self.onExecBegin.append(self.setKeyboardModeAscii)
		self.onLayoutFinish.append(self.buildVirtualKeyBoard)
	
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
				[u"<", u"y", u"x", u"c", u"v", u"b", u"n", u"m", u",", ".", u"-", u"CLEAR"],
				[u"SHIFT", u"SPACE", u"@", u"ß", u"OK"]]
			self.shiftkeys_list = [
				[u"EXIT", u"!", u'"', u"§", u"$", u"%", u"&", u"/", u"(", u")", u"=", u"BACKSPACE"],
				[u"Q", u"W", u"E", u"R", u"T", u"Z", u"U", u"I", u"O", u"P", u"Ü", u"*"],
				[u"A", u"S", u"D", u"F", u"G", u"H", u"J", u"K", u"L", u"Ö", u"Ä", u"'"],
				[u">", u"Y", u"X", u"C", u"V", u"B", u"N", u"M", u";", u":", u"_", u"CLEAR"],
				[u"SHIFT", u"SPACE", u"?", u"\\", u"OK"]]
			self.nextLang = 'es_ES'
		elif self.lang == 'es_ES':
			#still missing keys (u"ùÙ")
			self.keys_list = [
				[u"EXIT", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"BACKSPACE"],
				[u"q", u"w", u"e", u"r", u"t", u"z", u"u", u"i", u"o", u"p", u"ú", u"+"],
				[u"a", u"s", u"d", u"f", u"g", u"h", u"j", u"k", u"l", u"ó", u"á", u"#"],
				[u"<", u"y", u"x", u"c", u"v", u"b", u"n", u"m", u",", ".", u"-", u"CLEAR"],
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
				[u"<", u"y", u"x", u"c", u"v", u"b", u"n", u"m", u",", ".", u"-", u"CLEAR"],
				[u"SHIFT", u"SPACE", u"@", u"ß", u"ĺ", u"OK"]]
			self.shiftkeys_list = [
				[u"EXIT", u"!", u'"', u"§", u"$", u"%", u"&", u"/", u"(", u")", u"=", u"BACKSPACE"],
				[u"Q", u"W", u"E", u"R", u"T", u"Z", u"U", u"I", u"O", u"P", u"É", u"*"],
				[u"A", u"S", u"D", u"F", u"G", u"H", u"J", u"K", u"L", u"Ö", u"Ä", u"'"],
				[u">", u"Y", u"X", u"C", u"V", u"B", u"N", u"M", u";", u":", u"_", u"CLEAR"],
				[u"SHIFT", u"SPACE", u"?", u"\\", u"Ĺ", u"OK"]]
			self.nextLang = 'sv_SE'
		elif self.lang == 'sv_SE':
			self.keys_list = [
				[u"EXIT", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"BACKSPACE"],
				[u"q", u"w", u"e", u"r", u"t", u"z", u"u", u"i", u"o", u"p", u"é", u"+"],
				[u"a", u"s", u"d", u"f", u"g", u"h", u"j", u"k", u"l", u"ö", u"ä", u"#"],
				[u"<", u"y", u"x", u"c", u"v", u"b", u"n", u"m", u",", ".", u"-", u"CLEAR"],
				[u"SHIFT", u"SPACE", u"@", u"ß", u"ĺ", u"OK"]]
			self.shiftkeys_list = [
				[u"EXIT", u"!", u'"', u"§", u"$", u"%", u"&", u"/", u"(", u")", u"=", u"BACKSPACE"],
				[u"Q", u"W", u"E", u"R", u"T", u"Z", u"U", u"I", u"O", u"P", u"É", u"*"],
				[u"A", u"S", u"D", u"F", u"G", u"H", u"J", u"K", u"L", u"Ö", u"Ä", u"'"],
				[u">", u"Y", u"X", u"C", u"V", u"B", u"N", u"M", u";", u":", u"_", u"CLEAR"],
				[u"SHIFT", u"SPACE", u"?", u"\\", u"Ĺ", u"OK"]]
			self.nextLang = 'sk_SK'
		elif self.lang =='sk_SK':
			self.keys_list = [
				[u"EXIT", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"BACKSPACE"],
				[u"q", u"w", u"e", u"r", u"t", u"z", u"u", u"i", u"o", u"p", u"ú", u"+"],
				[u"a", u"s", u"d", u"f", u"g", u"h", u"j", u"k", u"l", u"ľ", u"@", u"#"],
				[u"<", u"y", u"x", u"c", u"v", u"b", u"n", u"m", u",", ".", u"-", u"CLEAR"],
				[u"SHIFT", u"SPACE", u"š", u"č", u"ž", u"ý", u"á", u"í", u"é", u"OK"]]
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
				[u"<", u"y", u"x", u"c", u"v", u"b", u"n", u"m", u",", ".", u"-", u"CLEAR"],
				[u"SHIFT", u"SPACE", u"ě", u"š", u"č", u"ř", u"ž", u"ý", u"á", u"í", u"é", u"OK"]]
			self.shiftkeys_list = [
				[u"EXIT", u"!", u'"', u"§", u"$", u"%", u"&", u"/", u"(", u")", u"=", u"BACKSPACE"],
				[u"Q", u"W", u"E", u"R", u"T", u"Z", u"U", u"I", u"O", u"P", u"ť", u"*"],
				[u"A", u"S", u"D", u"F", u"G", u"H", u"J", u"K", u"L", u"ň", u"ď", u"'"],
				[u">", u"Y", u"X", u"C", u"V", u"B", u"N", u"M", u";", u":", u"_", u"CLEAR"],
				[u"SHIFT", u"SPACE", u"?", u"\\", u"Č", u"Ř", u"Š", u"Ž", u"Ú", u"Á", u"É", u"OK"]]
			self.nextLang = 'en_EN'
		else:
			self.keys_list = [
				[u"EXIT", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"BACKSPACE"],
				[u"q", u"w", u"e", u"r", u"t", u"y", u"u", u"i", u"o", u"p", u"-", u"="],
				[u"a", u"s", u"d", u"f", u"g", u"h", u"j", u"k", u"l", u";", u"'", u"\\"],
				[u"[", u"z", u"x", u"c", u"v", u"b", u"n", u"m", u",", ".", u"/", u"CLEAR"],
				[u"SHIFT", u"SPACE", u"OK"]]
			self.shiftkeys_list = [
				[u"EXIT", u"!", u'"', u"§", u"$", u"%", u"&", u"/", u"(", u")", u"=", u"BACKSPACE"],
				[u"Q", u"W", u"E", u"R", u"T", u"Z", u"U", u"I", u"O", u"P", u"*"],
				[u"A", u"S", u"D", u"F", u"G", u"H", u"J", u"K", u"L", u"'", u"?"],
				[u">", u"Y", u"X", u"C", u"V", u"B", u"N", u"M", u";", u":", u"_", u"CLEAR"],
				[u"SHIFT", u"SPACE", u"OK"]]
			self.lang = 'en_EN'
			self.nextLang = 'de_DE'		
		self["country"].setText(self.lang)
		self.max_key=47+len(self.keys_list[4])

	def buildVirtualKeyBoard(self, selectedKey=0):
		list = []
		
		if self.shiftMode:
			self.k_list = self.shiftkeys_list
			for keys in self.k_list:
				if selectedKey < 12 and selectedKey > -1:
					list.append(VirtualKeyBoardEntryComponent(keys, selectedKey,True))
				else:
					list.append(VirtualKeyBoardEntryComponent(keys, -1,True))
				selectedKey -= 12
		else:
			self.k_list = self.keys_list
			for keys in self.k_list:
				if selectedKey < 12 and selectedKey > -1:
					list.append(VirtualKeyBoardEntryComponent(keys, selectedKey))
				else:
					list.append(VirtualKeyBoardEntryComponent(keys, -1))
				selectedKey -= 12
		
		self["list"].setList(list)
	
	def shiftClicked(self):
		if self.shiftMode:
			self.shiftMode = False
		else:
			self.shiftMode = True
		self.buildVirtualKeyBoard(self.selectedKey)
			
	def backClicked(self):
		self.text = self.text[:-1]
		self["text"].setText(self.text.encode("utf-8"))
			
	def okClicked(self):
		if self.shiftMode:
			list = self.shiftkeys_list
		else:
			list = self.keys_list
		
		selectedKey = self.selectedKey

		text = None

		for x in list:
			if selectedKey < 12:
				if selectedKey < len(x):
					text = x[selectedKey]
				break
			else:
				selectedKey -= 12

		if text is None:
			return

		text = text.encode("UTF-8")

		if text == "EXIT":
			self.close(None)
		
		elif text == "BACKSPACE":
			self.text = self.text[:-1]
			self["text"].setText(self.text.encode("utf-8"))
		
		elif text == "CLEAR":
			self.text = ""
			self["text"].setText(self.text.encode("utf-8"))
		
		elif text == "SHIFT":
			if self.shiftMode:
				self.shiftMode = False
			else:
				self.shiftMode = True
			
			self.buildVirtualKeyBoard(self.selectedKey)
		
		elif text == "SPACE":
			self.text += " "
			self["text"].setText(self.text.encode("utf-8"))
		
		elif text == "OK":
			self.close(self.text.encode("utf-8"))
		
		else:
			self.text += text
			self["text"].setText(self.text.encode("utf-8"))

	def key_backspace(self):
		self.selectedKey = 11
		self.okClicked()

	def key_minus(self):
		self.selectedKey = 22
		self.okClicked()

	def key_equal(self):
		self.selectedKey = 23
		self.okClicked()

	def key_q(self):
		self.selectedKey = 12
		self.okClicked()

	def key_w(self):
		self.selectedKey = 13
		self.okClicked()

	def key_e(self):
		self.selectedKey = 14
		self.okClicked()

	def key_r(self):
		self.selectedKey = 15
		self.okClicked()

	def key_t(self):
		self.selectedKey = 16
		self.okClicked()

	def key_y(self):
		self.selectedKey = 17
		self.okClicked()

	def key_u(self):
		self.selectedKey = 18
		self.okClicked()

	def key_i(self):
		self.selectedKey = 19
		self.okClicked()

	def key_o(self):
		self.selectedKey = 20
		self.okClicked()

	def key_p(self):
		self.selectedKey = 21
		self.okClicked()

	def key_leftbrace(self):
		self.selectedKey = 36
		self.okClicked()

	def key_rightbrace(self):
		self.selectedKey = 35
		self.okClicked()

	def key_enter(self):
		self.selectedKey = 23
		self.okClicked()

	def key_a(self):
		self.selectedKey = 24
		self.okClicked()

	def key_s(self):
		self.selectedKey = 25
		self.okClicked()

	def key_d(self):
		self.selectedKey = 26
		self.okClicked()

	def key_f(self):
		self.selectedKey = 27
		self.okClicked()

	def key_g(self):
		self.selectedKey = 28
		self.okClicked()

	def key_h(self):
		self.selectedKey = 29
		self.okClicked()

	def key_j(self):
		self.selectedKey = 30
		self.okClicked()

	def key_k(self):
		self.selectedKey = 31
		self.okClicked()

	def key_l(self):
		self.selectedKey = 32
		self.okClicked()

	def key_semicolon(self):
		self.selectedKey = 33
		self.okClicked()

	def key_apostrophe(self):
		self.selectedKey = 34
		self.okClicked()

	def key_grave(self):
		self.selectedKey = 35
		self.okClicked()

	def key_leftshift(self):
		self.selectedKey = 48
		self.okClicked()

	def key_backslash(self):
		self.selectedKey = 35
		self.okClicked()

	def key_z(self):
		self.selectedKey = 37
		self.okClicked()

	def key_x(self):
		self.selectedKey = 38
		self.okClicked()

	def key_c(self):
		self.selectedKey = 39
		self.okClicked()

	def key_v(self):
		self.selectedKey = 40
		self.okClicked()

	def key_b(self):
		self.selectedKey = 41
		self.okClicked()

	def key_n(self):
		self.selectedKey = 42
		self.okClicked()

	def key_m(self):
		self.selectedKey = 43
		self.okClicked()

	def key_comma(self):
		self.selectedKey = 44
		self.okClicked()

	def key_dot(self):
		self.selectedKey = 45
		self.okClicked()

	def key_slash(self):
		self.selectedKey = 46
		self.okClicked()

	def key_rightshift(self):
		self.selectedKey = 48
		self.okClicked()

	def key_space(self):
		self.selectedKey = 49
		self.okClicked()

	def key_capslock(self):
		self.selectedKey = 52
		self.okClicked()

	def key_esc(self):
		self.selectedKey = 50
		self.okClicked()

	def ok(self):
		self.close(self.text.encode("utf-8"))

	def exit(self):
		self.close(None)

	def left(self):
		self.selectedKey -= 1
		
		if self.selectedKey == -1:
			self.selectedKey = 11
		elif self.selectedKey == 11:
			self.selectedKey = 23
		elif self.selectedKey == 23:
			self.selectedKey = 35
		elif self.selectedKey == 35:
			self.selectedKey = 47
		elif self.selectedKey == 47:
			self.selectedKey = self.max_key
		
		self.showActiveKey()

	def right(self):
		self.selectedKey += 1
		
		if self.selectedKey == 12:
			self.selectedKey = 0
		elif self.selectedKey == 24:
			self.selectedKey = 12
		elif self.selectedKey == 36:
			self.selectedKey = 24
		elif self.selectedKey == 48:
			self.selectedKey = 36
		elif self.selectedKey > self.max_key:
			self.selectedKey = 48
		
		self.showActiveKey()

	def up(self):
		self.selectedKey -= 12
		
		if (self.selectedKey < 0) and (self.selectedKey > (self.max_key-60)):
			self.selectedKey += 48
		elif self.selectedKey < 0:
			self.selectedKey += 60	
		
		self.showActiveKey()

	def down(self):
		self.selectedKey += 12
		
		if (self.selectedKey > self.max_key) and (self.selectedKey > 59):
			self.selectedKey -= 60
		elif self.selectedKey > self.max_key:
			self.selectedKey -= 48
		
		self.showActiveKey()

	def showActiveKey(self):
		self.buildVirtualKeyBoard(self.selectedKey)

	def inShiftKeyList(self,key):
		for KeyList in self.shiftkeys_list:
			for char in KeyList:
				if char == key:
					return True
		return False

	def keyGotAscii(self):
		char = str(unichr(getPrevAsciiCode()).encode('utf-8'))
		if self.inShiftKeyList(char):
			self.shiftMode = True
			list = self.shiftkeys_list
		else:
			self.shiftMode = False
			list = self.keys_list	

		if char == " ":
			char = "SPACE"

		selkey = 0
		for keylist in list:
			for key in keylist:
				if key == char:
					self.selectedKey = selkey
					self.okClicked()
					self.showActiveKey()
					return
				else:
					selkey += 1

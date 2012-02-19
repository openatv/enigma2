# -*- coding: UTF-8 -*-
from enigma import eListboxPythonMultiContent, gFont, RT_HALIGN_CENTER, RT_VALIGN_CENTER, getPrevAsciiCode
from Screen import Screen
from Components.Language import language
from Components.ActionMap import NumberActionMap
from Components.Sources.StaticText import StaticText
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN
from Tools.LoadPixmap import LoadPixmap
from Tools.NumericalTextInput import NumericalTextInput

class VirtualKeyBoardList(MenuList):
	def __init__(self, list, enableWrapAround=False):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		self.l.setFont(0, gFont("Regular", 28))
		self.l.setItemHeight(45)

KEY_IMAGES =  {
		"BACKSPACE": "skin_default/vkey_backspace.png",
		"CLEAR": "skin_default/vkey_clr.png",
		"EXIT": "skin_default/vkey_esc.png",
		"OK": "skin_default/vkey_ok.png",
		"SHIFT": "skin_default/vkey_shift.png",
		"SPACE": "skin_default/vkey_space.png",
		}
KEY_IMAGES_SHIFT = {
		"BACKSPACE": "skin_default/vkey_backspace.png",
		"CLEAR": "skin_default/vkey_clr.png",
		"EXIT": "skin_default/vkey_esc.png",
		"OK": "skin_default/vkey_ok.png",
		"SHIFT": "skin_default/vkey_shift_sel.png",
		"SPACE": "skin_default/vkey_space.png",
		}
def VirtualKeyBoardEntryComponent(keys, selectedKey, shiftMode=False):
	key_bg = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/vkey_bg.png"))
	key_bg_width = key_bg.size().width()
	if shiftMode:
		key_images = KEY_IMAGES_SHIFT
	else:
		key_images = KEY_IMAGES
	res = [ (keys) ]
	x = 0
	count = 0
	for count, key in enumerate(keys):
		width = None
		png = key_images.get(key, None)
		if png:
			pixmap = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, png))
			width = pixmap.size().width()
			res.append(MultiContentEntryPixmapAlphaTest(pos=(x, 0), size=(width, 45), png=pixmap))
		else:
			width = key_bg_width
			res.extend((
				MultiContentEntryPixmapAlphaTest(pos=(x, 0), size=(width, 45), png=key_bg),
				MultiContentEntryText(pos=(x, 0), size=(width, 45), font=0, text=key.encode("utf-8"), flags=RT_HALIGN_CENTER | RT_VALIGN_CENTER)
			))
		if selectedKey == count:
			key_sel = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/vkey_sel.png"))
			width = key_sel.size().width()
			res.append(MultiContentEntryPixmapAlphaTest(pos=(x, 0), size=(width, 45), png=key_sel))
		if width is not None:
			x += width
		else:
			x += 45
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
		self.smsChar = None
		self.sms = NumericalTextInput(self.smsOK)
		
		self["country"] = StaticText("")
		self["header"] = Label(title)
		self["text"] = Label(self.text)
		self["list"] = VirtualKeyBoardList([])
		
		self["actions"] = NumberActionMap(["OkCancelActions", "WizardActions", "ColorActions", "KeyboardInputActions", "InputBoxActions", "InputAsciiActions"],
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
				"back": self.exit,
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
			self.nextLang = 'ru_RU'
		elif self.lang == 'ru_RU':
			self.keys_list = [
				[u"EXIT", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"BACKSPACE"],
				[u"й", u"ц", u"у", u"к", u"е", u"н", u"г", u"ш", u"щ", u"з", u"х", u"+"],
				[u"ф", u"ы", u"в", u"а", u"б", u"п", u"р", u"о", u"л", u"д", u"ж", u"#"],
				[u"<", u"э", u"я", u"ч", u"с", u"м", u"и", u"т", u",", ".", u"-", u"CLEAR"],
				[u"SHIFT", u"SPACE", u"@", u"ь", u"ю", u"ъ", u"OK"]]
			self.shiftkeys_list = [
				[u"EXIT", u"!", u'"', u"§", u"$", u"%", u"&", u"/", u"(", u")", u"=", u"BACKSPACE"],
				[u"Й", u"Ц", u"У", u"К", u"Е", u"Н", u"Г", u"Ш", u"Щ", u"З", u"I", u"Х", u"*"],
				[u"Ф", u"Ы", u"В", u"А", u"П", u"Р", u"О", u"О", u"Л", u"Д", u"Ж", u"'"],
				[u">", u"Э", u"Я", u"Ч", u"С", u"М", u"И", u"Т", u";", u":", u"_", u"CLEAR"],
				[u"SHIFT", u"SPACE", u"?", u"\\", u"Ь", u"Б", u"Ю",  u"Ъ", u"OK"]]
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
				[u"q", u"w", u"e", u"r", u"t", u"y", u"u", u"i", u"o", u"p", u"-", u"["],
				[u"a", u"s", u"d", u"f", u"g", u"h", u"j", u"k", u"l", u";", u"'", u"\\"],
				[u"<", u"z", u"x", u"c", u"v", u"b", u"n", u"m", u",", ".", u"/", u"CLEAR"],
				[u"SHIFT", u"SPACE", u"OK"]]
			self.shiftkeys_list = [
				[u"EXIT", u"!", u"@", u"#", u"$", u"%", u"^", u"&", u"(", u")", u"=", u"BACKSPACE"],
				[u"Q", u"W", u"E", u"R", u"T", u"Y", u"U", u"I", u"O", u"P", u"*", u"]"],
				[u"A", u"S", u"D", u"F", u"G", u"H", u"J", u"K", u"L", u"?", u'"', u"|"],
				[u">", u"Z", u"X", u"C", u"V", u"B", u"N", u"M", u";", u":", u"_", u"CLEAR"],
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
	
	def backClicked(self):
		self.smsChar = None
		self.text = self.text[:-1]
		self["text"].setText(self.text.encode("utf-8"))

	def shiftClicked(self):
		self.smsChar = None
		self.shiftMode = not self.shiftMode
		self.buildVirtualKeyBoard(self.selectedKey)

	def okClicked(self):
		self.smsChar = None
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
			ss=unicode(self["text"].getText(),"utf-8")
			ss=ss[:-1]
			self.text = str(ss.encode("utf-8"))
			self["text"].setText(self.text)
		
		elif text == "CLEAR":
			self.text = ""
			self["text"].setText(self.text.encode("utf-8"))
		
		elif text == "SHIFT":
			self.shiftClicked()
		
		elif text == "SPACE":
			self.text += " "
			self["text"].setText(self.text.encode("utf-8"))
		
		elif text == "OK":
			self.close(self.text.encode("utf-8"))
		
		else:
			self.text += text
			self["text"].setText(self.text.encode("utf-8"))

	def ok(self):
		self.close(self.text.encode("utf-8"))

	def exit(self):
		self.close(None)

	def left(self):
		self.smsChar = None
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
		self.smsChar = None
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
		self.smsChar = None
		self.selectedKey -= 12
		if (self.selectedKey < 0) and (self.selectedKey > (self.max_key-60)):
			self.selectedKey += 48
		elif self.selectedKey < 0:
			self.selectedKey += 60	
		self.showActiveKey()

	def down(self):
		self.smsChar = None
		self.selectedKey += 12
		if (self.selectedKey > self.max_key) and (self.selectedKey > 59):
			self.selectedKey -= 60
		elif self.selectedKey > self.max_key:
			self.selectedKey -= 48
		self.showActiveKey()

	def showActiveKey(self):
		self.buildVirtualKeyBoard(self.selectedKey)

	def keyNumberGlobal(self, number):
		self.smsChar = self.sms.getKey(number)
		print "SMS", number, self.smsChar
		self.selectAsciiKey(self.smsChar)

	def smsOK(self):
		print "SMS ok", self.smsChar
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
						self.shiftMode = (keyslist is self.shiftkeys_list)
						self.selectedKey = selkey
						self.showActiveKey()
						return True
					selkey += 1
		return False

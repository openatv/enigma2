from copy import copy, deepcopy

from enigma import BT_SCALE, RT_HALIGN_CENTER, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_BOTTOM, RT_VALIGN_CENTER, RT_VALIGN_TOP, eListboxPythonMultiContent, getPrevAsciiCode, gFont

from skin import fonts, parameters
from Components.ActionMap import HelpableNumberActionMap
from Components.Input import Input
from Components.Label import Label
from Components.Language import language
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaTest
from Components.Sources.StaticText import StaticText
from Screens.ChoiceBox import ChoiceBox
from Screens.HelpMenu import HelpableScreen
from Screens.Screen import Screen
from Tools.Directories import SCOPE_CURRENT_SKIN, resolveFilename
from Tools.LoadPixmap import LoadPixmap
from Tools.NumericalTextInput import NumericalTextInput

VKB_DONE_ICON = 0
VKB_ENTER_ICON = 1
VKB_OK_ICON = 2
VKB_SAVE_ICON = 3
VKB_SEARCH_ICON = 4
VKB_DONE_TEXT = 5
VKB_ENTER_TEXT = 6
VKB_OK_TEXT = 7
VKB_SAVE_TEXT = 8
VKB_SEARCH_TEXT = 9

SPACE = u"SPACEICON"  # Symbol to be used for a SPACE on the keyboard.  Must be u"SPACE" (any case), u"SPACEICON" or u"SPACEICONALT".


class VirtualKeyBoardList(MenuList):
	def __init__(self, list, enableWrapAround=False):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		font = fonts.get("VirtualKeyBoard", ("Regular", 28, 45))
		self.l.setFont(0, gFont(font[0], font[1]))
		self.l.setFont(1, gFont(font[0], font[1] * 5 // 9))  # Smaller font is 56% the height of bigger font
		self.l.setItemHeight(font[2])


class VirtualKeyBoardEntryComponent:
	def __init__(self):
		pass


# For more information about using VirtualKeyBoard see /doc/VIRTUALKEYBOARD
#
class VirtualKeyBoard(Screen, HelpableScreen):
	def __init__(self, session, title=_("Virtual KeyBoard Text:"), text="", maxSize=False, visible_width=False, type=Input.TEXT, currPos=None, allMarked=False, style=VKB_ENTER_ICON):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		self.setTitle(_("Virtual keyboard"))
		prompt = title  # Title should only be used for screen titles!
		greenLabel, self.green = {
			VKB_DONE_ICON: ("Done", u"ENTERICON"),
			VKB_ENTER_ICON: ("Enter", u"ENTERICON"),
			VKB_OK_ICON: ("OK", u"ENTERICON"),
			VKB_SAVE_ICON: ("Save", u"ENTERICON"),
			VKB_SEARCH_ICON: ("Search", u"ENTERICON"),
			VKB_DONE_TEXT: ("Done", _("Done")),
			VKB_ENTER_TEXT: ("Done", _("Enter")),
			VKB_OK_TEXT: ("OK", _("OK")),
			VKB_SAVE_TEXT: ("Save", _("Save")),
			VKB_SEARCH_TEXT: ("Search", _("Search"))
		}.get(style, ("Enter", u"ENTERICON"))
		self.bg = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_bg.png"))  # Legacy support only!
		self.bg_l = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_bg_l.png"))
		self.bg_m = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_bg_m.png"))
		self.bg_r = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_bg_r.png"))
		self.sel_l = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_sel_l.png"))
		self.sel_m = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_sel_m.png"))
		self.sel_r = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_sel_r.png"))
		key_red_l = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_red_l.png"))
		key_red_m = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_red_m.png"))
		key_red_r = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_red_r.png"))
		key_green_l = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_green_l.png"))
		key_green_m = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_green_m.png"))
		key_green_r = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_green_r.png"))
		key_yellow_l = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_yellow_l.png"))
		key_yellow_m = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_yellow_m.png"))
		key_yellow_r = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_yellow_r.png"))
		key_blue_l = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_blue_l.png"))
		key_blue_m = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_blue_m.png"))
		key_blue_r = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_blue_r.png"))
		key_backspace = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_backspace.png"))
		key_clear = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_clear.png"))
		key_delete = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_delete.png"))
		key_enter = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_enter.png"))
		key_exit = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_exit.png"))
		key_first = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_first.png"))
		key_last = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_last.png"))
		key_left = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_left.png"))
		key_locale = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_locale.png"))
		key_right = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_right.png"))
		key_shift = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_shift.png"))
		key_shift0 = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_shift0.png"))
		key_shift1 = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_shift1.png"))
		key_shift2 = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_shift2.png"))
		key_shift3 = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_shift3.png"))
		key_space = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_space.png"))
		key_space_alt = LoadPixmap(path=resolveFilename(SCOPE_CURRENT_SKIN, "buttons/vkey_space_alt.png"))
		self.keyHighlights = {  # This is a table of cell highlight components (left, middle and right)
			u"EXIT": (key_red_l, key_red_m, key_red_r),
			u"EXITICON": (key_red_l, key_red_m, key_red_r),
			u"DONE": (key_green_l, key_green_m, key_green_r),
			u"ENTER": (key_green_l, key_green_m, key_green_r),
			u"ENTERICON": (key_green_l, key_green_m, key_green_r),
			u"OK": (key_green_l, key_green_m, key_green_r),
			u"SAVE": (key_green_l, key_green_m, key_green_r),
			# u"LOC": (key_yellow_l, key_yellow_m, key_yellow_r),
			# u"LOCALE": (key_yellow_l, key_yellow_m, key_yellow_r),
			# u"LOCALEICON": (key_yellow_l, key_yellow_m, key_yellow_r),
			u"SHIFT": (key_yellow_l, key_yellow_m, key_yellow_r),
			u"SHIFTICON": (key_yellow_l, key_yellow_m, key_yellow_r),
			u"CAPS": (key_blue_l, key_blue_m, key_blue_r),
			u"LOCK": (key_blue_l, key_blue_m, key_blue_r),
			u"CAPSLOCK": (key_blue_l, key_blue_m, key_blue_r),
			u"CAPSLOCKICON": (key_blue_l, key_blue_m, key_blue_r)
		}
		self.shiftMsgs = [
			_("Lower case"),
			_("Upper case"),
			_("Special 1"),
			_("Special 2")
		]
		self.keyImages = [{
			u"BACKSPACEICON": key_backspace,
			u"CAPSLOCKICON": key_shift0,
			u"CLEARICON": key_clear,
			u"DELETEICON": key_delete,
			u"ENTERICON": key_enter,
			u"EXITICON": key_exit,
			u"FIRSTICON": key_first,
			u"LASTICON": key_last,
			u"LOCALEICON": key_locale,
			u"LEFTICON": key_left,
			u"RIGHTICON": key_right,
			u"SHIFTICON": key_shift,
			u"SPACEICON": key_space,
			u"SPACEICONALT": key_space_alt
		}, {
			u"BACKSPACEICON": key_backspace,
			u"CAPSLOCKICON": key_shift1,
			u"CLEARICON": key_clear,
			u"DELETEICON": key_delete,
			u"ENTERICON": key_enter,
			u"EXITICON": key_exit,
			u"FIRSTICON": key_first,
			u"LASTICON": key_last,
			u"LEFTICON": key_left,
			u"LOCALEICON": key_locale,
			u"RIGHTICON": key_right,
			u"SHIFTICON": key_shift,
			u"SPACEICON": key_space,
			u"SPACEICONALT": key_space_alt
		}, {
			u"BACKSPACEICON": key_backspace,
			u"CAPSLOCKICON": key_shift2,
			u"CLEARICON": key_clear,
			u"DELETEICON": key_delete,
			u"ENTERICON": key_enter,
			u"EXITICON": key_exit,
			u"FIRSTICON": key_first,
			u"LASTICON": key_last,
			u"LEFTICON": key_left,
			u"LOCALEICON": key_locale,
			u"RIGHTICON": key_right,
			u"SHIFTICON": key_shift,
			u"SPACEICON": key_space,
			u"SPACEICONALT": key_space_alt
		}, {
			u"BACKSPACEICON": key_backspace,
			u"CAPSLOCKICON": key_shift3,
			u"CLEARICON": key_clear,
			u"DELETEICON": key_delete,
			u"ENTERICON": key_enter,
			u"EXITICON": key_exit,
			u"FIRSTICON": key_first,
			u"LASTICON": key_last,
			u"LEFTICON": key_left,
			u"LOCALEICON": key_locale,
			u"RIGHTICON": key_right,
			u"SHIFTICON": key_shift,
			u"SPACEICON": key_space,
			u"SPACEICONALT": key_space_alt
		}]
		self.cmds = {
			u"": "pass",
			u"ALL": "self['text'].markAll()",
			u"ALLICON": "self['text'].markAll()",
			u"BACK": "self['text'].deleteBackward()",
			u"BACKSPACE": "self['text'].deleteBackward()",
			u"BACKSPACEICON": "self['text'].deleteBackward()",
			u"BLANK": "pass",
			u"CAPS": "self.capsLockSelected()",
			u"CAPSLOCK": "self.capsLockSelected()",
			u"CAPSLOCKICON": "self.capsLockSelected()",
			u"CLEAR": "self['text'].deleteAllChars()\nself['text'].update()",
			u"CLEARICON": "self['text'].deleteAllChars()\nself['text'].update()",
			u"CLR": "self['text'].deleteAllChars()\nself['text'].update()",
			u"DEL": "self['text'].deleteForward()",
			u"DELETE": "self['text'].deleteForward()",
			u"DELETEICON": "self['text'].deleteForward()",
			u"DONE": "self.save()",
			u"ENTER": "self.save()",
			u"ENTERICON": "self.save()",
			u"ESC": "self.cancel()",
			u"EXIT": "self.cancel()",
			u"EXITICON": "self.cancel()",
			u"FIRST": "self['text'].home()",
			u"FIRSTICON": "self['text'].home()",
			u"LAST": "self['text'].end()",
			u"LASTICON": "self['text'].end()",
			u"LEFT": "self['text'].left()",
			u"LEFTICON": "self['text'].left()",
			u"LOC": "self.localeMenu()",
			u"LOCALE": "self.localeMenu()",
			u"LOCALEICON": "self.localeMenu()",
			u"LOCK": "self.capsLockSelected()",
			u"OK": "self.save()",
			u"RIGHT": "self['text'].right()",
			u"RIGHTICON": "self['text'].right()",
			u"SAVE": "self.save()",
			u"SHIFT": "self.shiftSelected()",
			u"SHIFTICON": "self.shiftSelected()",
			u"SPACE": "self['text'].char(' '.encode('UTF-8'))",
			u"SPACEICON": "self['text'].char(' '.encode('UTF-8'))",
			u"SPACEICONALT": "self['text'].char(' '.encode('UTF-8'))"
		}
		self.footer = [u"EXITICON", u"LEFTICON", u"RIGHTICON", SPACE, SPACE, SPACE, SPACE, SPACE, SPACE, SPACE, u"SHIFTICON", u"LOCALEICON", u"CLEARICON", u"DELETEICON"]
		self.czech = [
			[
				[u";", u"+", u"\u011B", u"\u0161", u"\u010D", u"\u0159", u"\u017E", u"\u00FD", u"\u00E1", u"\u00ED", u"\u00E9", u"=", u"", u"BACKSPACEICON"],
				[u"FIRSTICON", u"q", u"w", u"e", u"r", u"t", u"z", u"u", u"i", u"o", u"p", u"\u00FA", u"(", u")"],
				[u"LASTICON", u"a", u"s", u"d", u"f", u"g", u"h", u"j", u"k", u"l", u"\u016F", u"\u00A7", self.green, self.green],
				[u"CAPSLOCKICON", u"\\", u"y", u"x", u"c", u"v", u"b", u"n", u"m", u",", ".", u"-", u"CAPSLOCKICON", u"CAPSLOCKICON"],
				self.footer
			], [
				[u".", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"%", u"'", u"BACKSPACEICON"],
				[u"FIRSTICON", u"Q", u"W", u"E", u"R", u"T", u"Z", u"U", u"I", u"O", u"P", u"/", u"(", u")"],
				[u"LASTICON", u"A", u"S", u"D", u"F", u"G", u"H", u"J", u"K", u"L", u"\"", u"!", self.green, self.green],
				[u"CAPSLOCKICON", u"|", u"Y", u"X", u"C", u"V", u"B", u"N", u"M", u"?", u":", u"_", u"CAPSLOCKICON", u"CAPSLOCKICON"],
				self.footer
			], [
				[u"\u00B0", u"~", u"\u011A", u"\u0160", u"\u010C", u"\u0158", u"\u017D", u"\u00DD", u"\u00C1", u"\u00CD", u"\u00C9", u"`", u"'", u"BACKSPACEICON"],
				[u"FIRSTICON", u"\\", u"|", u"\u20AC", u"\u0165", u"\u0164", u"\u0148", u"\u0147", u"\u00F3", u"\u00D3", u"\u00DA", u"\u00F7", u"\u00D7", u"\u00A4"],
				[u"LASTICON", u"", u"\u0111", u"\u00D0", u"[", u"]", u"\u010F", u"\u010E", u"\u0142", u"\u0141", u"\u016E", u"\u00DF", self.green, self.green],
				[u"CAPSLOCKICON", u"", u"", u"#", u"&", u"@", u"{", u"}", u"$", u"<", u">", u"*", u"CAPSLOCKICON", u"CAPSLOCKICON"],
				self.footer
			]
		]
		self.english = [
			[
				[u"`", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"-", u"=", u"BACKSPACEICON"],
				[u"FIRSTICON", u"q", u"w", u"e", u"r", u"t", u"y", u"u", u"i", u"o", u"p", u"[", u"]", u"\\"],
				[u"LASTICON", u"a", u"s", u"d", u"f", u"g", u"h", u"j", u"k", u"l", u";", u"'", self.green, self.green],
				[u"CAPSLOCKICON", u"CAPSLOCKICON", u"z", u"x", u"c", u"v", u"b", u"n", u"m", u",", u".", u"/", u"CAPSLOCKICON", u"CAPSLOCKICON"],
				self.footer
			], [
				[u"~", u"!", u"@", u"#", u"$", u"%", u"^", u"&", u"*", u"(", u")", u"_", u"+", u"BACKSPACEICON"],
				[u"FIRSTICON", u"Q", u"W", u"E", u"R", u"T", u"Y", u"U", u"I", u"O", u"P", u"{", u"}", u"|"],
				[u"LASTICON", u"A", u"S", u"D", u"F", u"G", u"H", u"J", u"K", u"L", u":", u"\"", self.green, self.green],
				[u"CAPSLOCKICON", u"CAPSLOCKICON", u"Z", u"X", u"C", u"V", u"B", u"N", u"M", u"<", u">", u"?", u"CAPSLOCKICON", u"CAPSLOCKICON"],
				self.footer
			]
		]
		self.french = [
			[
				[u"\u00B2", u"&", u"\u00E9", u"\"", u"'", u"(", u"-", u"\u00E8", u"_", u"\u00E7", u"\u00E0", u")", u"=", u"BACKSPACEICON"],
				[u"FIRSTICON", u"a", u"z", u"e", u"r", u"t", u"y", u"u", u"i", u"o", u"p", u"^", u"$", u"*"],
				[u"LASTICON", u"q", u"s", u"d", u"f", u"g", u"h", u"j", u"k", u"l", u"m", u"\u00F9", self.green, self.green],
				[u"CAPSLOCKICON", u"<", u"w", u"x", u"c", u"v", u"b", u"n", u",", u";", u":", u"!", u"CAPSLOCKICON", u"CAPSLOCKICON"],
				self.footer
			], [
				[u"", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"\u00B0", u"+", u"BACKSPACEICON"],
				[u"FIRSTICON", u"A", u"Z", u"E", u"R", u"T", u"Y", u"U", u"I", u"O", u"P", u"\u00A8", u"\u00A3", u"\u00B5"],
				[u"LASTICON", u"Q", u"S", u"D", u"F", u"G", u"H", u"J", u"K", u"L", u"M", u"%", self.green, self.green],
				[u"CAPSLOCKICON", u">", u"W", u"X", u"C", u"V", u"B", u"N", u"?", u".", u"/", u"\u00A7", u"CAPSLOCKICON", u"CAPSLOCKICON"],
				self.footer
			], [
				[u"", u"", u"~", u"#", u"{", u"[", u"|", u"`", u"\\", u"^", u"@", u"]", u"}", u"BACKSPACEICON"],
				[u"FIRSTICON", u"", u"", u"\u20AC", u"", u"", u"", u"", u"", u"", u"", u"", u"\u00A4", u""],
				[u"LASTICON", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"", self.green, self.green],
				[u"CAPSLOCKICON", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"CAPSLOCKICON", u"CAPSLOCKICON"],
				self.footer
			], [
				[u"", u"", u"\u00E2", u"\u00EA", u"\u00EE", u"\u00F4", u"\u00FB", u"\u00E4", u"\u00EB", u"\u00EF", u"\u00F6", u"\u00FC", u"", u"BACKSPACEICON"],
				[u"FIRSTICON", u"", u"\u00E0", u"\u00E8", u"\u00EC", u"\u00F2", u"\u00F9", u"\u00E1", u"\u00E9", u"\u00ED", u"\u00F3", u"\u00FA", u"", u""],
				[u"LASTICON", u"", u"\u00C2", u"\u00CA", u"\u00CE", u"\u00D4", u"\u00DB", u"\u00C4", u"\u00CB", u"\u00CF", u"\u00D6", u"\u00DC", self.green, self.green],
				[u"CAPSLOCKICON", u"", u"\u00C0", u"\u00C8", u"\u00CC", u"\u00D2", u"\u00D9", u"\u00C1", u"\u00C9", u"\u00CD", u"\u00D3", u"\u00DA", u"CAPSLOCKICON", u"CAPSLOCKICON"],
				self.footer
			]
		]
		self.german = [
			[
				[u"^", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"\u00DF", u"'", u"BACKSPACEICON"],
				[u"FIRSTICON", u"q", u"w", u"e", u"r", u"t", u"z", u"u", u"i", u"o", u"p", u"\u00FC", u"+", u"#"],
				[u"LASTICON", u"a", u"s", u"d", u"f", u"g", u"h", u"j", u"k", u"l", u"\u00F6", u"\u00E4", self.green, self.green],
				[u"CAPSLOCKICON", u"<", u"y", u"x", u"c", u"v", u"b", u"n", u"m", u",", ".", u"-", u"CAPSLOCKICON", u"CAPSLOCKICON"],
				self.footer
			], [
				[u"\u00B0", u"!", u"\"", u"\u00A7", u"$", u"%", u"&", u"/", u"(", u")", u"=", u"?", u"`", u"BACKSPACEICON"],
				[u"FIRSTICON", u"Q", u"W", u"E", u"R", u"T", u"Z", u"U", u"I", u"O", u"P", u"\u00DC", u"*", u"'"],
				[u"LASTICON", u"A", u"S", u"D", u"F", u"G", u"H", u"J", u"K", u"L", u"\u00D6", u"\u00C4", self.green, self.green],
				[u"CAPSLOCKICON", u">", u"Y", u"X", u"C", u"V", u"B", u"N", u"M", u";", u":", u"_", u"CAPSLOCKICON", U"CAPSLOCKICON"],
				self.footer
			], [
				[u"", u"", u"\u00B2", u"\u00B3", u"", u"", u"", u"{", u"[", u"]", u"}", u"\\", u"\u1E9E", u"BACKSPACEICON"],
				[u"FIRSTICON", u"@", u"", u"\u20AC", u"", u"", u"", u"", u"", u"", u"", u"", u"~", u""],
				[u"LASTICON", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"", self.green, self.green],
				[u"CAPSLOCKICON", u"|", u"", u"", u"", u"", u"", u"", u"\u00B5", u"", u"", u"", u"CAPSLOCKICON", u"CAPSLOCKICON"],
				self.footer
			]
		]
		self.greek = [
			[
				[u"`", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"-", u"=", u"BACKSPACEICON"],
				[u"FIRSTICON", u";", u"\u03C2", u"\u03B5", u"\u03C1", u"\u03C4", u"\u03C5", u"\u03B8", u"\u03B9", u"\u03BF", u"\u03C0", u"[", u"]", u"\\"],
				[u"LASTICON", u"\u03B1", u"\u03C3", u"\u03B4", u"\u03C6", u"\u03B3", u"\u03B7", u"\u03BE", u"\u03BA", u"\u03BB", u"\u0384", u"'", self.green, self.green],
				[u"CAPSLOCKICON", u"<", u"\u03B6", u"\u03C7", u"\u03C8", u"\u03C9", u"\u03B2", u"\u03BD", u"\u03BC", u",", ".", u"/", u"CAPSLOCKICON", u"CAPSLOCKICON"],
				self.footer
			], [
				[u"~", u"!", u"@", u"#", u"$", u"%", u"^", u"&", u"*", u"(", u")", u"_", u"+", u"BACKSPACEICON"],
				[u"FIRSTICON", u":", u"\u0385", u"\u0395", u"\u03A1", u"\u03A4", u"\u03A5", u"\u0398", u"\u0399", u"\u039F", u"\u03A0", u"{", u"}", u"|"],
				[u"LASTICON", u"\u0391", u"\u03A3", u"\u0394", u"\u03A6", u"\u0393", u"\u0397", u"\u039E", u"\u039A", u"\u039B", u"\u00A8", u"\"", self.green, self.green],
				[u"CAPSLOCKICON", u">", u"\u0396", u"\u03A7", u"\u03A8", u"\u03A9", u"\u0392", u"\u039D", u"\u039C", u"<", u">", u"?", u"CAPSLOCKICON", u"CAPSLOCKICON"],
				self.footer
			], [
				[u"", u"", u"\u00B2", u"\u00B3", u"\u00A3", u"\u00A7", u"\u00B6", u"", u"\u00A4", u"\u00A6", u"\u00B0", u"\u00B1", u"\u00BD", u"BACKSPACEICON"],
				[u"FIRSTICON", u"", u"\u03AC", u"\u03AD", u"\u03AE", u"\u03AF", u"\u03CC", u"\u03CD", u"\u03CE", u"\u03CA", u"\u03CB", u"\u00AB", u"\u00BB", u"\u00AC"],
				[u"LASTICON", u"", u"\u0386", u"\u0388", u"\u0389", u"\u038A", u"\u038C", u"\u038E", u"\u038F", u"\u03AA", u"\u03AB", u"\u0385", self.green, self.green],
				[u"CAPSLOCKICON", u"CAPSLOCKICON", u"", u"", u"", u"\u00A9", u"\u00AE", u"\u20AC", u"\u00A5", u"\u0390", u"\u03B0", u"\u0387", u"CAPSLOCKICON", u"CAPSLOCKICON"],
				self.footer
			]
		]
		self.latvian = [
			[
				[u"", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"-", u"f", u"BACKSPACEICON"],
				[u"FIRSTICON", u"\u016B", u"g", u"j", u"r", u"m", u"v", u"n", u"z", u"\u0113", u"\u010D", u"\u017E", u"h", u"\u0137"],
				[u"LASTICON", u"\u0161", u"u", u"s", u"i", u"l", u"d", u"a", u"t", u"e", u"c", u"\u00B4", self.green, self.green],
				[u"CAPSLOCKICON", u"\u0123", u"\u0146", u"b", u"\u012B", u"k", u"p", u"o", u"\u0101", u",", u".", u"\u013C", u"CAPSLOCKICON", u"CAPSLOCKICON"],
				self.footer
			], [
				[u"?", u"!", u"\u00AB", u"\u00BB", u"$", u"%", u"/", u"&", u"\u00D7", u"(", u")", u"_", u"F", u"BACKSPACEICON"],
				[u"FIRSTICON", u"\u016A", u"G", u"J", u"R", u"M", u"V", u"N", u"Z", u"\u0112", u"\u010C", u"\u017D", u"H", u"\u0136"],
				[u"LASTICON", u"\u0160", u"U", u"S", u"I", u"L", u"D", u"A", u"T", u"E", u"C", u"\u00B0", self.green, self.green],
				[u"CAPSLOCKICON", u"\u0122", u"\u0145", u"B", u"\u012A", u"K", u"P", u"O", u"\u0100", u";", u":", u"\u013B", u"CAPSLOCKICON", u"CAPSLOCKICON"],
				self.footer
			], [
				[u"", u"\u00AB", u"", u"", u"\u20AC", u"\"", u"'", u"", u":", u"", u"", u"\u2013", u"=", u"BACKSPACEICON"],
				[u"FIRSTICON", u"q", u"\u0123", u"", u"\u0157", u"w", u"y", u"", u"", u"", u"", u"[", u"]", u""],
				[u"LASTICON", u"", u"", u"", u"", u"", u"", u"", u"", u"\u20AC", u"", u"\u00B4", self.green, self.green],
				[u"CAPSLOCKICON", u"\\", u"", u"x", u"", u"\u0137", u"", u"\u00F5", u"", u"<", u">", u"", u"CAPSLOCKICON", u"CAPSLOCKICON"],
				self.footer
			], [
				[u"", u"", u"@", u"#", u"$", u"~", u"^", u"\u00B1", u"", u"", u"", u"\u2014", u";", u"BACKSPACEICON"],
				[u"FIRSTICON", u"Q", u"\u0122", u"", u"\u0156", u"W", u"Y", u"", u"", u"", u"", u"{", u"}", u""],
				[u"LASTICON", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"\u00A8", self.green, self.green],
				[u"CAPSLOCKICON", u"|", u"", u"X", u"", u"\u0136", u"", u"\u00D5", u"", u"", u"", u"", u"CAPSLOCKICON", u"CAPSLOCKICON"],
				self.footer
			]
		]
		self.russian = [
			[
				[u"\u0451", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"-", u"=", u"BACKSPACEICON"],
				[u"FIRSTICON", u"\u0439", u"\u0446", u"\u0443", u"\u043A", u"\u0435", u"\u043D", u"\u0433", u"\u0448", u"\u0449", u"\u0437", u"\u0445", u"\u044A", u"\\"],
				[u"LASTICON", u"\u0444", u"\u044B", u"\u0432", u"\u0430", u"\u043F", u"\u0440", u"\u043E", u"\u043B", u"\u0434", u"\u0436", u"\u044D", self.green, self.green],
				[u"CAPSLOCKICON", u"\\", u"\u044F", u"\u0447", u"\u0441", u"\u043C", u"\u0438", u"\u0442", u"\u044C", u"\u0431", u"\u044E", u".", u"CAPSLOCKICON", u"CAPSLOCKICON"],
				self.footer
			], [
				[u"\u0401", u"!", u"\"", u"\u2116", u";", u"%", u":", u"?", u"*", u"(", u")", u"_", u"+", u"BACKSPACEICON"],
				[u"FIRSTICON", u"\u0419", u"\u0426", u"\u0423", u"\u041A", u"\u0415", u"\u041D", u"\u0413", u"\u0428", u"\u0429", u"\u0417", u"\u0425", u"\u042A", u"/"],
				[u"LASTICON", u"\u0424", u"\u042B", u"\u0412", u"\u0410", u"\u041F", u"\u0420", u"\u041E", u"\u041B", u"\u0414", u"\u0416", u"\u042D", self.green, self.green],
				[u"CAPSLOCKICON", u"/", u"\u042F", u"\u0427", u"\u0421", u"\u041C", u"\u0418", u"\u0422", u"\u042C", u"\u0411", u"\u042E", u",", u"CAPSLOCKICON", u"CAPSLOCKICON"],
				self.footer
			], [
				[u"", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"BACKSPACEICON"],
				[u"FIRSTICON", u"", u"\u00A7", u"@", u"#", u"&", u"$", u"\u20BD", u"\u20AC", u"", u"", u"", u"", u""],
				[u"LASTICON", u"", u"<", u">", u"[", u"]", u"{", u"}", u"", u"", u"", u"", self.green, self.green],
				[u"CAPSLOCKICON", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"CAPSLOCKICON", u"CAPSLOCKICON"],
				self.footer
			]
		]
		self.scandinavian = [
			[
				[u"\u00A7", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"+", u"\u00B4", u"BACKSPACEICON"],
				[u"FIRSTICON", u"q", u"w", u"e", u"r", u"t", u"y", u"u", u"i", u"o", u"p", u"\u00E5", u"\u00A8", u"'"],
				[u"LASTICON", u"a", u"s", u"d", u"f", u"g", u"h", u"j", u"k", u"l", u"\u00F6", u"\u00E4", self.green, self.green],
				[u"CAPSLOCKICON", u"<", u"z", u"x", u"c", u"v", u"b", u"n", u"m", u",", ".", u"-", u"CAPSLOCKICON", u"CAPSLOCKICON"],
				self.footer
			], [
				[u"\u00BD", u"!", u"\"", u"#", u"\u00A4", u"%", u"&", u"/", u"(", u")", u"=", u"?", u"`", u"BACKSPACEICON"],
				[u"FIRSTICON", u"Q", u"W", u"E", u"R", u"T", u"Y", u"U", u"I", u"O", u"P", u"\u00C5", u"^", u"*"],
				[u"LASTICON", u"A", u"S", u"D", u"F", u"G", u"H", u"J", u"K", u"L", u"\u00D6", u"\u00C4", self.green, self.green],
				[u"CAPSLOCKICON", u">", u"Z", u"X", u"C", u"V", u"B", u"N", u"M", u";", u":", u"_", u"CAPSLOCKICON", u"CAPSLOCKICON"],
				self.footer
			], [
				[u"", u"", u"@", u"\u00A3", u"$", u"\u20AC", u"", u"{", u"[", u"]", u"}", u"\\", u"", u"BACKSPACEICON"],
				[u"FIRSTICON", u"", u"", u"\u20AC", u"", u"", u"", u"", u"", u"", u"", u"", u"~", u""],
				[u"LASTICON", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"", self.green, self.green],
				[u"CAPSLOCKICON", u"|", u"", u"", u"", u"", u"", u"", u"\u00B5", u"", u"", u"", u"CAPSLOCKICON", u"CAPSLOCKICON"],
				self.footer
			], [
				[u"", u"\u00E2", u"\u00EA", u"\u00EE", u"\u00F4", u"\u00FB", u"\u00E4", u"\u00EB", u"\u00EF", u"\u00F6", u"\u00FC", u"\u00E3", u"", u"BACKSPACEICON"],
				[u"FIRSTICON", u"\u00E0", u"\u00E8", u"\u00EC", u"\u00F2", u"\u00F9", u"\u00E1", u"\u00E9", u"\u00ED", u"\u00F3", u"\u00FA", u"\u00F5", u"", u""],
				[u"LASTICON", u"\u00C2", u"\u00CA", u"\u00CE", u"\u00D4", u"\u00DB", u"\u00C4", u"\u00CB", u"\u00CF", u"\u00D6", u"\u00DC", u"\u00C3", self.green, self.green],
				[u"CAPSLOCKICON", u"\u00C0", u"\u00C8", u"\u00CC", u"\u00D2", u"\u00D9", u"\u00C1", u"\u00C9", u"\u00CD", u"\u00D3", u"\u00DA", u"\u00D5", u"CAPSLOCKICON", u"CAPSLOCKICON"],
				self.footer
			]
		]
		self.spanish = [
			[
				[u"\u00BA", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"'", u"\u00A1", u"BACKSPACEICON"],
				[u"FIRSTICON", u"q", u"w", u"e", u"r", u"t", u"y", u"u", u"i", u"o", u"p", u"`", u"+", u"\u00E7"],
				[u"LASTICON", u"a", u"s", u"d", u"f", u"g", u"h", u"j", u"k", u"l", u"\u00F1", u"\u00B4", self.green, self.green],  # [, ]
				[u"CAPSLOCKICON", u"<", u"z", u"x", u"c", u"v", u"b", u"n", u"m", u",", ".", u"-", u"CAPSLOCKICON", u"CAPSLOCKICON"],
				self.footer
			], [
				[u"\u00AA", u"!", u"\"", u"\u00B7", u"$", u"%", u"&", u"/", u"(", u")", u"=", u"?", u"\u00BF", u"BACKSPACEICON"],
				[u"FIRSTICON", u"Q", u"W", u"E", u"R", u"T", u"Y", u"U", u"I", u"O", u"P", u"^", u"*", u"\u00C7"],
				[u"LASTICON", u"A", u"S", u"D", u"F", u"G", u"H", u"J", u"K", u"L", u"\u00D1", u"\u00A8", self.green, self.green],  # {, }
				[u"CAPSLOCKICON", u">", u"Z", u"X", u"C", u"V", u"B", u"N", u"M", u";", u":", u"_", u"CAPSLOCKICON", u"CAPSLOCKICON"],
				self.footer
			], [
				[u"\\", u"|", u"@", u"#", u"~", u"\u20AC", u"\u00AC", u"", u"", u"", u"", u"", u"", u"BACKSPACEICON"],
				[u"FIRSTICON", u"", u"\u00E1", u"\u00E9", u"\u00ED", u"\u00F3", u"\u00FA", u"\u00FC", u"", u"", u"[", u"]", u"", u""],
				[u"LASTICON", u"", u"\u00C1", u"\u00C9", u"\u00CD", u"\u00D3", u"\u00DA", u"\u00DC", u"", u"", u"{", u"}", self.green, self.green],
				[u"CAPSLOCKICON", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"CAPSLOCKICON", u"CAPSLOCKICON"],
				self.footer
			]
		]
		self.thai = [
			[
				[u"", u"", u"\u0E45", u"\u0E20", u"\u0E16", u"\u0E38", u"\u0E36", u"\u0E04", u"\u0E15", u"\u0E08", u"\u0E02", u"\u0E0A", u"", u"BACKSPACEICON"],
				[u"FIRSTICON", u"\u0E46", u"\u0E44", u"\u0E33", u"\u0E1E", u"\u0E30", u"\u0E31", u"\u0E35", u"\u0E23", u"\u0E19", u"\u0E22", u"\u0E1A", u"\u0E25", u""],
				[u"LASTICON", u"\u0E1F", u"\u0E2B", u"\u0E01", u"\u0E14", u"\u0E40", u"\u0E49", u"\u0E48", u"\u0E32", u"\u0E2A", u"\u0E27", u"\u0E07", u"\u0E03", self.green],
				[u"CAPSLOCKICON", u"CAPSLOCKICON", u"\u0E1C", u"\u0E1B", u"\u0E41", u"\u0E2D", u"\u0E34", u"\u0E37", u"\u0E17", u"\u0E21", u"\u0E43", u"\u0E1D", u"CAPSLOCKICON", u"CAPSLOCKICON"],
				self.footer
			], [
				[u"", u"", u"\u0E51", u"\u0E52", u"\u0E53", u"\u0E54", u"\u0E39", u"\u0E55", u"\u0E56", u"\u0E57", u"\u0E58", u"\u0E59", u"", u"BACKSPACEICON"],
				[u"FIRSTICON", u"\u0E50", u"", u"\u0E0E", u"\u0E11", u"\u0E18", u"\u0E4D", u"\u0E4A", u"\u0E13", u"\u0E2F", u"\u0E0D", u"\u0E10", u"\u0E05", u""],
				[u"LASTICON", u"\u0E24", u"\u0E06", u"\u0E0F", u"\u0E42", u"\u0E0C", u"\u0E47", u"\u0E4B", u"\u0E29", u"\u0E28", u"\u0E0B", u"", u"\u0E3F", self.green],
				[u"CAPSLOCKICON", u"CAPSLOCKICON", u"", u"\u0E09", u"\u0E2E", u"\u0E3A", u"\u0E4C", u"", u"\u0E12", u"\u0E2C", u"\u0E26", u"", u"CAPSLOCKICON", u"CAPSLOCKICON"],
				self.footer
			]
		]
		self.locales = {
			"ar_BH": [_("Arabic"), _("Bahrain"), self.arabic(self.english)],
			"ar_EG": [_("Arabic"), _("Egypt"), self.arabic(self.english)],
			"ar_JO": [_("Arabic"), _("Jordan"), self.arabic(self.english)],
			"ar_KW": [_("Arabic"), _("Kuwait"), self.arabic(self.english)],
			"ar_LB": [_("Arabic"), _("Lebanon"), self.arabic(self.english)],
			"ar_OM": [_("Arabic"), _("Oman"), self.arabic(self.english)],
			"ar_QA": [_("Arabic"), _("Qatar"), self.arabic(self.english)],
			"ar_SA": [_("Arabic"), _("Saudi Arabia"), self.arabic(self.english)],
			"ar_SY": [_("Arabic"), _("Syrian Arab Republic"), self.arabic(self.english)],
			"ar_AE": [_("Arabic"), _("United Arab Emirates"), self.arabic(self.english)],
			"ar_YE": [_("Arabic"), _("Yemen"), self.arabic(self.english)],
			"cs_CZ": [_("Czech"), _("Czechia"), self.czech],
			"nl_NL": [_("Dutch"), _("Netherlands"), self.dutch(self.english)],
			"en_AU": [_("English"), _("Australian"), self.english],
			"en_GB": [_("English"), _("United Kingdom"), self.unitedKingdom(self.english)],
			"en_US": [_("English"), _("United States"), self.english],
			"en_EN": [_("English"), _("Various"), self.english],
			"et_EE": [_("Estonian"), _("Estonia"), self.estonian(self.scandinavian)],
			"fi_FI": [_("Finnish"), _("Finland"), self.scandinavian],
			"fr_BE": [_("French"), _("Belgian"), self.belgian(self.french)],
			"fr_FR": [_("French"), _("France"), self.french],
			"fr_CH": [_("French"), _("Switzerland"), self.frenchSwiss(self.german)],
			"de_DE": [_("German"), _("Germany"), self.german],
			"de_CH": [_("German"), _("Switzerland"), self.germanSwiss(self.german)],
			"el_GR": [_("Greek"), _("Greece"), self.greek],
			"hu_HU": [_("Hungarian"), _("Hungary"), self.hungarian(self.german)],
			"lv_01": [_("Latvian"), _("Alternative 1"), self.latvianStandard(self.english)],
			"lv_02": [_("Latvian"), _("Alternative 2"), self.latvian],
			"lv_LV": [_("Latvian"), _("Latvia"), self.latvianQWERTY(self.english)],
			"lt_LT": [_("Lithuanian"), _("Lithuania"), self.lithuanian(self.english)],
			"nb_NO": [_("Norwegian"), _("Norway"), self.norwegian(self.scandinavian)],
			"fa_IR": [_("Persian"), _("Iran, Islamic Republic"), self.persian(self.english)],
			"pl_01": [_("Polish"), _("Alternative"), self.polish(self.german)],
			"pl_PL": [_("Polish"), _("Poland"), self.polishProgrammers(self.english)],
			"ru_RU": [_("Russian"), _("Russian Federation"), self.russian],
			"sk_SK": [_("Slovak"), _("Slovakia"), self.slovak(self.german)],
			"es_ES": [_("Spanish"), _("Spain"), self.spanish],
			"sv_SE": [_("Swedish"), _("Sweden"), self.scandinavian],
			"th_TH": [_("Thai"), _("Thailand"), self.thai],
			"uk_01": [_("Ukrainian"), _("Russian"), self.ukranian(self.russian)],
			"uk_UA": [_("Ukrainian"), _("Ukraine"), self.ukranianEnhanced(self.russian)]
		}
		self["actions"] = HelpableNumberActionMap(self, ["VirtualKeyBoardActions", "NumberActions", "TextEditActions"], {
			"cancel": (self.cancel, _("Cancel any text changes and exit")),
			"save": (self.save, _("Save / Enter text and exit")),
			"shift": (self.shiftSelected, _("Select the shifted character set for the next character only")),
			"capsLock": (self.capsLockSelected, _("Select the shifted character set")),
			"select": (self.processSelect, _("Select the character or action under the keyboard cursor")),
			"locale": (self.localeMenu, _("Select the locale from a menu")),
			"up": (self.up, _("Move the keyboard cursor up")),
			"left": (self.left, _("Move the keyboard cursor left")),
			"right": (self.right, _("Move the keyboard cursor right")),
			"down": (self.down, _("Move the keyboard cursor down")),
			"first": (self.cursorFirst, _("Move the text cursor to the first character")),
			"prev": (self.cursorLeft, _("Move the text cursor left")),
			"next": (self.cursorRight, _("Move the text cursor right")),
			"last": (self.cursorLast, _("Move the text cursor to the last character")),
			"backspace": (self.backSelected, _("Delete the character to the left of text cursor")),
			"delete": (self.forwardSelected, _("Delete the character under the text cursor")),
			"erase": (self.eraseAll, _("Delete all the text")),
			"toggleOverwrite": (self.keyToggleOW, _("Toggle new text inserts before or overwrites existing text")),
			"0": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"1": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"2": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"3": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"4": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"5": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"6": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"7": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"8": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"9": (self.keyNumberGlobal, _("Number or SMS style data entry")),
			"gotAsciiCode": (self.keyGotAscii, _("Keyboard data entry"))
		}, -2, description=_("Virtual KeyBoard Functions"))
		self.lang = language.getLanguage()
		self["prompt"] = Label(prompt)
		self["text"] = Input(text=text, maxSize=maxSize, visible_width=visible_width, type=type, currPos=len(text.decode("utf-8", "ignore")) if currPos is None else currPos, allMarked=allMarked)
		self["list"] = VirtualKeyBoardList([])
		self["mode"] = Label(_("INS"))
		self["locale"] = Label(_("Locale") + ": " + self.lang)
		self["language"] = Label(_("Language") + ": " + self.lang)
		self["key_info"] = StaticText(_("INFO"))
		self["key_red"] = StaticText(_("Exit"))
		self["key_green"] = StaticText(_(greenLabel))
		self["key_yellow"] = StaticText(_("Shift"))
		self["key_blue"] = StaticText(self.shiftMsgs[1])
		self["key_text"] = StaticText(_("TEXT"))
		self["key_help"] = StaticText(_("HELP"))
		width, height = parameters.get("VirtualKeyBoard", (45, 45))
		if self.bg_l is None or self.bg_m is None or self.bg_r is None:
			self.width = width
			self.height = height
		else:
			self.width = self.bg_l.size().width() + self.bg_m.size().width() + self.bg_r.size().width()
			self.height = self.bg_m.size().height()
		# Alignment -> (Horizontal, Vertical):
		# 	Horizontal alignment: 0=Auto, 1=Left, 2=Center, 3=Right (Auto=Left on left, Center on middle, Right on right).
		# 	Vertical alignment: 0=Auto, 1=Top, 2=Center, 3=Bottom (Auto=Center).
		self.alignment = parameters.get("VirtualKeyBoardAlignment", (0, 0))
		# Padding -> (Left/Right, Top/Botton) in pixels
		self.padding = parameters.get("VirtualKeyBoardPadding", (4, 4))
		# Text color for each shift level.  (Ensure there is a color for each shift level!)
		self.shiftColors = parameters.get("VirtualKeyBoardShiftColors", (0x00ffffff, 0x00ffffff, 0x0000ffff, 0x00ff00ff))
		self.language = None
		self.location = None
		self.keyList = []
		self.shiftLevels = 0
		self.shiftLevel = 0
		self.shiftHold = -1
		self.keyboardWidth = 0
		self.keyboardHeight = 0
		self.maxKey = 0
		self.overwrite = False
		self.selectedKey = None
		self.sms = NumericalTextInput(self.smsGotChar)
		self.smsChar = None
		self.setLocale()
		self.onExecBegin.append(self.setKeyboardModeAscii)
		self.onLayoutFinish.append(self.buildVirtualKeyBoard)

	def arabic(self, base):
		keyList = deepcopy(base)
		keyList[1][0][8] = u"\u066D"
		keyList.extend([[
			[u"\u0630", u"\u0661", u"\u0662", u"\u0663", u"\u0664", u"\u0665", u"\u0666", u"\u0667", u"\u0668", u"\u0669", u"\u0660", u"-", u"=", u"BACKSPACEICON"],
			[u"FIRSTICON", u"\u0636", u"\u0635", u"\u062B", u"\u0642", u"\u0641", u"\u063A", u"\u0639", u"\u0647", u"\u062E", u"\u062D", u"\u062C", u"\u062F", u"\\"],
			[u"LASTICON", u"\u0634", u"\u0633", u"\u064A", u"\u0628", u"\u0644", u"\u0627", u"\u062A", u"\u0646", u"\u0645", u"\u0643", u"\u0637", self.green, self.green],
			[u"CAPSLOCKICON", u"CAPSLOCKICON", u"\u0626", u"\u0621", u"\u0624", u"\u0631", u"\uFEFB", u"\u0649", u"\u0629", u"\u0648", u"\u0632", u"\u0638", u"CAPSLOCKICON", u"CAPSLOCKICON"],
			self.footer
		], [
			[u"\u0651", u"!", u"@", u"#", u"$", u"%", u"^", u"&", u"\u066D", u"(", u")", u"_", u"+", u"BACKSPACEICON"],
			[u"FIRSTICON", u"\u0636", u"\u0635", u"\u062B", u"\u0642", u"\u0641", u"\u063A", u"\u0639", u"\u00F7", u"\u00D7", u"\u061B", u">", u"<", u"|"],
			[u"LASTICON", u"\u0634", u"\u0633", u"\u064A", u"\u0628", u"\u0644", u"\u0623", u"\u0640", u"\u060C", u"/", u":", u"\"", self.green, self.green],
			[u"CAPSLOCKICON", u"CAPSLOCKICON", u"\u0626", u"\u0621", u"\u0624", u"\u0631", u"\uFEF5", u"\u0622", u"\u0629", u",", u".", u"\u061F", u"CAPSLOCKICON", u"CAPSLOCKICON"],
			self.footer
		]])
		return keyList

	def belgian(self, base):
		keyList = deepcopy(base)
		keyList[0][0][6] = u"\u00A7"
		keyList[0][0][8] = u"!"
		keyList[0][0][12] = u"-"
		keyList[0][1][13] = u"\u00B5"
		keyList[0][3][11] = u"="
		keyList[1][0][0] = u"\u00B3"
		keyList[1][0][12] = u"_"
		keyList[1][1][11] = u"\u00A8"
		keyList[1][1][12] = u"*"
		keyList[1][1][13] = u"\u00A3"
		keyList[1][3][11] = u"+"
		keyList[2][0] = [u"", u"|", u"@", u"#", u"{", u"[", u"^", u"", u"", u"{", u"}", u"", u"", u"BACKSPACEICON"]
		keyList[2][1][11] = u"["
		keyList[2][1][12] = u"]"
		keyList[2][1][13] = u"`"
		keyList[2][2][11] = u"\u00B4"
		keyList[2][3][1] = u"\\"
		keyList[2][3][11] = u"~"
		return keyList

	def dutch(self, base):
		keyList = deepcopy(base)
		keyList[0][0][0] = u"@"
		keyList[0][0][11] = u"/"
		keyList[0][0][12] = u"\u00B0"
		keyList[0][1][11] = u"\u00A8"
		keyList[0][1][12] = u"*"
		keyList[0][1][13] = u"<"
		keyList[0][2][10] = u"+"
		keyList[0][2][11] = u"\u00B4"
		keyList[0][3] = [u"CAPSLOCKICON", u"]", u"z", u"x", u"c", u"v", u"b", u"n", u"m", u",", u".", u"-", u"CAPSLOCKICON", u"CAPSLOCKICON"]
		keyList[1][0] = [u"\u00A7", u"!", u"\"", u"#", u"$", u"%", u"&", u"_", u"(", u")", u"'", u"?", u"~", u"BACKSPACEICON"]
		keyList[1][1][11] = u"^"
		keyList[1][1][12] = u"|"
		keyList[1][1][13] = u">"
		keyList[1][2][10] = u"\u00B1"
		keyList[1][2][11] = u"`"
		keyList[1][3] = [u"CAPSLOCKICON", u"[", u"Z", u"X", u"C", u"V", u"B", u"N", u"M", u";", u":", u"=", u"CAPSLOCKICON", u"CAPSLOCKICON"]
		keyList.append([
			[u"\u00AC", u"\u00B9", u"\u00B2", u"\u00B3", u"\u00BC", u"\u00BD", u"\u00BE", u"\u00A3", u"{", u"}", u"", u"\\", u"\u00B8", u"BACKSPACEICON"],
			[u"FIRSTICON", u"", u"", u"\u20AC", u"\u00B6", u"", u"\u00E1", u"\u00E9", u"\u00ED", u"\u00F3", u"\u00FA", u"", u"", u""],
			[u"LASTICON", u"", u"\u00DF", u"", u"", u"", u"\u00C1", u"\u00C9", u"\u00CD", u"\u00D3", u"\u00DA", u"", self.green, self.green],
			[u"CAPSLOCKICON", u"\u00A6", u"\u00AB", u"\u00BB", u"\u00A2", u"", u"", u"", u"\u00B5", u"", u"\u00B7", u"", u"CAPSLOCKICON", u"CAPSLOCKICON"],
			self.footer
		])
		return keyList

	def estonian(self, base):
		keyList = deepcopy(base)
		keyList[0][0][0] = u"\u02C7"
		keyList[0][1][11] = u"\u00FC"
		keyList[0][1][12] = u"\u00F5"
		keyList[1][0][0] = u"~"
		keyList[1][1][11] = u"\u00DC"
		keyList[1][1][12] = u"\u00D5"
		keyList[2][1][12] = u"\u00A7"
		keyList[2][1][13] = u"\u00BD"
		keyList[2][2][2] = u"\u0161"
		keyList[2][2][3] = u"\u0160"
		keyList[2][2][11] = u"^"
		keyList[2][3][2] = u"\u017E"
		keyList[2][3][3] = u"\u017D"
		keyList[2][3][8] = u""
		del keyList[3]
		return keyList

	def frenchSwiss(self, base):
		keyList = self.germanSwiss(base)
		keyList[0][0][11] = u"'"
		keyList[0][0][12] = u"^"
		keyList[0][1][11] = u"\u00E8"
		keyList[0][2][10] = u"\u00E9"
		keyList[0][2][11] = u"\u00E0"
		keyList[1][1][11] = u"\u00FC"
		keyList[1][2][10] = u"\u00F6"
		keyList[1][2][11] = u"\u00E4"
		return keyList

	def germanSwiss(self, base):
		keyList = deepcopy(base)
		keyList[0][0][0] = u"\u00A7"
		keyList[0][0][11] = u"'"
		keyList[0][0][12] = u"^"
		keyList[0][1][12] = u"\u00A8"
		keyList[0][1][13] = u"$"
		keyList[1][0][1] = u"+"
		keyList[1][0][3] = u"*"
		keyList[1][0][4] = u"\u00E7"
		keyList[1][0][11] = u"?"
		keyList[1][0][12] = u"`"
		keyList[1][1][11] = u"\u00E8"
		keyList[1][1][12] = u"!"
		keyList[1][1][13] = u"\u00A3"
		keyList[1][2][10] = u"\u00E9"
		keyList[1][2][11] = u"\u00E0"
		keyList[2][0] = [u"", u"\u00A6", u"@", u"#", u"\u00B0", u"\u00A7", u"\u00AC", u"|", u"\u00A2", u"", u"", u"\u00B4", u"~", u"BACKSPACEICON"]
		keyList[2][1][1] = u""
		keyList[2][1][9] = u"\u00DC"
		keyList[2][1][10] = u"\u00C8"
		keyList[2][1][11] = u"["
		keyList[2][1][12] = u"]"
		keyList[2][2][6] = u"\u00D6"
		keyList[2][2][7] = u"\u00C9"
		keyList[2][2][8] = u"\u00C4"
		keyList[2][2][9] = u"\u00C0"
		keyList[2][2][10] = u"{"
		keyList[2][2][11] = u"}"
		keyList[2][3][1] = u"\\"
		keyList[2][3][8] = u""
		return keyList

	def hungarian(self, base):
		keyList = deepcopy(base)
		keyList[0][0][0] = u"0"
		keyList[0][0][10] = u"\u00F6"
		keyList[0][0][11] = u"\u00FC"
		keyList[0][0][12] = u"\u00F3"
		keyList[0][1][11] = u"\u0151"
		keyList[0][1][12] = u"\u00FA"
		keyList[0][1][13] = u"\u0171"
		keyList[0][2][10] = u"\u00E9"
		keyList[0][2][11] = u"\u00E1"
		keyList[0][3][1] = u"\u00ED"
		keyList[1][0] = [u"\u00A7", u"'", u"\"", u"+", u"!", u"%", u"/", u"=", u"(", u")", u"\u00D6", u"\u00DC", u"\u00D3", u"BACSPACEICON"]
		keyList[1][1][11] = u"\u0150"
		keyList[1][1][12] = u"\u00DA"
		keyList[1][1][13] = u"\u0170"
		keyList[1][2][10] = u"\u00C9"
		keyList[1][2][11] = u"\u00C1"
		keyList[1][3][1] = u"\u00CD"
		keyList[1][3][9] = u"?"
		del keyList[2]
		keyList.append([
			[u"", u"~", u"\u02C7", u"^", u"\u02D8", u"\u00B0", u"\u02DB", u"`", u"\u02D9", u"\u00B4", u"\u02DD", u"\u00A8", u"\u00B8", u"BACKSPACEICON"],
			[u"FIRSTICON", u"\\", u"|", u"\u00C4", u"", u"", u"", u"\u20AC", u"\u00CD", u"", u"", u"\u00F7", u"\u00D7", u"\u00A4"],
			[u"LASTICON", u"\u00E4", u"\u0111", u"\u0110", u"[", u"]", u"", u"\u00ED", u"\u0142", u"\u0141", u"$", u"\u00DF", self.green, self.green],
			[u"CAPSLOCKICON", u"<", u">", u"#", u"&", u"@", u"{", u"}", u"<", u";", u">", u"*", u"CAPSLOCKICON", u"CAPSLOCKICON"],
			self.footer
		])
		return keyList

	def latvianQWERTY(self, base):
		keyList = self.latvianStandard(base)
		keyList[0][1][13] = u"\u00B0"
		keyList[2][1][9] = u"\u00F5"
		keyList[3][1][9] = u"\u00D5"
		return keyList

	def latvianStandard(self, base):
		keyList = deepcopy(base)
		keyList[0][3][1] = u"\\"
		keyList[1][3][1] = u"|"
		keyList.append([
			[u"", u"", u"\u00AB", u"\u00BB", u"\u20AC", u"", u"\u2019", u"", u"", u"", u"", u"\u2013", u"", u"BACKSPACEICON"],
			[u"FIRSTICON", u"", u"", u"\u0113", u"\u0157", u"", u"", u"\u016B", u"\u012B", u"\u014D", u"", u"", u"", u""],
			[u"LASTICON", u"\u0101", u"\u0161", u"", u"", u"\u0123", u"", u"", u"\u0137", u"\u013C", u"", u"\u00B4", self.green, self.green],
			[u"CAPSLOCKICON", u"", u"\u017E", u"", u"\u010D", u"", u"", u"\u0146", u"", u"", u"", u"", u"CAPSLOCKICON", u"CAPSLOCKICON"],
			self.footer
		])
		keyList.append([
			[u"", u"", u"", u"", u"\u00A7", u"\u00B0", u"", u"\u00B1", u"\u00D7", u"", u"", u"\u2014", u"", u"BACKSPACEICON"],
			[u"FIRSTICON", u"", u"", u"\u0112", u"\u0156", u"", u"", u"\u016A", u"\u012A", u"\u014C", u"", u"", u"", u""],
			[u"LASTICON", u"\u0100", u"\u0160", u"", u"", u"\u0122", u"", u"", u"\u0136", u"\u013B", u"", u"\u00A8", self.green, self.green],
			[u"CAPSLOCKICON", u"", u"\u017D", u"", u"\u010C", u"", u"", u"\u0145", u"", u"", u"", u"", u"CAPSLOCKICON", u"CAPSLOCKICON"],
			self.footer
		])
		return keyList

	def lithuanian(self, base):
		keyList = deepcopy(base)
		keyList[0][0] = [u"`", u"\u0105", u"\u010D", u"\u0119", u"\u0117", u"\u012F", u"\u0161", u"\u0173", u"\u016B", u"9", u"0", u"-", u"\u017E", u"BACKSPACEICON"]
		keyList[0][3][1] = u"\\"
		keyList[1][0] = [u"~", u"\u0104", u"\u010C", u"\u0118", u"\u0116", u"\u012E", u"\u0160", u"\u0172", u"\u016A", u"(", u")", u"_", u"\u017D", u"BACKSPACEICON"]
		keyList[1][3][1] = u"|"
		keyList.append([
			[u"", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"", u"=", u"BACKSPACEICON"],
			[u"FIRSTICON", u"!", u"@", u"#", u"$", u"%", u"^", u"&", u"*", u"", u"", u"", u"+", u""],
			[u"LASTICON", u"", u"", u"\u20AC", u"", u"", u"", u"", u"", u"", u"", u"", self.green, self.green],
			[u"CAPSLOCKICON", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"CAPSLOCKICON", u"CAPSLOCKICON"],
			self.footer
		])
		return keyList

	def norwegian(self, base):
		keyList = deepcopy(base)
		keyList[0][0][0] = u"|"
		keyList[0][0][12] = u"\\"
		keyList[0][2][10] = u"\u00F8"
		keyList[0][2][11] = u"\u00E6"
		keyList[1][0][0] = u"\u00A7"
		keyList[1][2][10] = u"\u00D8"
		keyList[1][2][11] = u"\u00C6"
		keyList[2][0][11] = u""
		keyList[2][0][12] = u"\u00B4"
		keyList[2][3][1] = u""
		return keyList

	def persian(self, base):
		keyList = deepcopy(base)
		keyList.append([
			[u"\u00F7", u"\u06F1", u"\u06F2", u"\u06F3", u"\u06F4", u"\u06F5", u"\u06F6", u"\u06F7", u"\u06F8", u"\u06F9", u"\u06F0", u"-", u"=", u"BACKSPACEICON"],
			[u"FIRSTICON", u"\u0636", u"\u0635", u"\u062B", u"\u0642", u"\u0641", u"\u063A", u"\u0639", u"\u0647", u"\u062E", u"\u062D", u"\u062C", u"\u0686", u"\u067E"],
			[u"LASTICON", u"\u0634", u"\u0633", u"\u06CC", u"\u0628", u"\u0644", u"\u0627", u"\u062A", u"\u0646", u"\u0645", u"\u06A9", u"\u06AF", self.green, self.green],
			[u"CAPSLOCKICON", u"\u0649", u"\u0638", u"\u0637", u"\u0632", u"\u0631", u"\u0630", u"\u062F", u"\u0626", u"\u0648", u".", u"/", u"CAPSLOCKICON", u"CAPSLOCKICON"],
			self.footer
		])
		keyList.append([
			[u"\u00D7", u"!", u"@", u"#", u"$", u"%", u"^", u"&", u"*", u")", u"(", u"_", u"+", u"BACKSPACEICON"],
			[u"FIRSTICON", u"\u064B", u"\u064C", u"\u064D", u"\u0631", u"\u060C", u"\u061B", u",", u"]", u"[", u"\\", u"}", u"{", u"|"],
			[u"LASTICON", u"\u064E", u"\u064F", u"\u0650", u"\u0651", u"\u06C0", u"\u0622", u"\u0640", u"\u00AB", u"\u00BB", u":", u"\"", self.green, self.green],
			[u"CAPSLOCKICON", u"|", u"\u0629", u"\u064A", u"\u0698", u"\u0624", u"\u0625", u"\u0623", u"\u0621", u"<", u">", u"\u061F", u"CAPSLOCKICON", u"CAPSLOCKICON"],
			self.footer
		])
		return keyList

	def polish(self, base):
		keyList = deepcopy(base)
		keyList[0][0][0] = u"\u02DB"
		keyList[0][0][11] = u"+"
		keyList[0][1][11] = u"\u017C"
		keyList[0][1][12] = u"\u015B"
		keyList[0][1][13] = u"\u00F3"
		keyList[0][2][10] = u"\u0142"
		keyList[0][2][11] = u"\u0105"
		keyList[1][0][0] = u"\u00B7"
		keyList[1][0][3] = u"#"
		keyList[1][0][4] = u"\u00A4"
		keyList[1][0][12] = u"*"
		keyList[1][1][11] = u"\u0144"
		keyList[1][1][12] = u"\u0107"
		keyList[1][1][13] = u"\u017A"
		keyList[1][2][10] = u"\u0141"
		keyList[1][2][11] = u"\u0119"
		del keyList[2]
		keyList.append([
			[u"", u"~", u"\u02C7", u"^", u"\u02D8", u"\u00B0", u"\u02DB", u"`", u"\u00B7", u"\u00B4", u"\u02DD", u"\u00A8", u"\u00B8", u"BACKSPACEICON"],
			[u"FIRSTICON", u"\\", u"\u00A6", u"", u"\u017B", u"\u015A", u"\u00D3", u"\u20AC", u"\u0143", u"\u0106", u"\u0179", u"\u00F7", u"\u00D7", u""],
			[u"LASTICON", u"", u"\u0111", u"\u0110", u"", u"", u"", u"", u"\u0104", u"\u0118", u"$", u"\u00DF", self.green, self.green],
			[u"CAPSLOCKICON", u"", u"", u"", u"", u"@", u"{", u"}", u"\u00A7", u"<", u">", u"", u"CAPSLOCKICON", u"CAPSLOCKICON"],
			self.footer
		])
		return keyList

	def polishProgrammers(self, base):
		keyList = deepcopy(base)
		keyList[0][3][1] = u"\\"
		keyList[1][3][1] = u"|"
		keyList.append([
			[u"", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"", u"BACKSPACEICON"],
			[u"FIRSTICON", u"", u"", u"\u0119", u"\u0118", u"", u"", u"\u20AC", u"", u"\u00F3", u"\u00D3", u"", u"", u""],
			[u"LASTICON", u"\u0105", u"\u0104", u"\u015B", u"\u015A", u"", u"", u"", u"", u"\u0142", u"\u0141", u"", self.green, self.green],
			[u"CAPSLOCKICON", u"\u017C", u"\u017B", u"\u017A", u"\u0179", u"\u0107", u"\u0106", u"\u0144", u"\u0143", u"", u"", u"", u"CAPSLOCKICON", u"CAPSLOCKICON"],
			self.footer
		])
		return keyList

	def slovak(self, base):
		keyList = deepcopy(base)
		keyList[0][0] = [u";", u"+", u"\u013E", u"\u0161", u"\u010D", u"\u0165", u"\u017E", u"\u00FD", u"\u00E1", u"\u00ED", u"\u00E9", u"=", u"\u00B4", u"BACKSPACEICON"]
		keyList[0][1][11] = u"\u00FA"
		keyList[0][1][12] = u"\u00E4"
		keyList[0][1][13] = u"\u0148"
		keyList[0][2][10] = u"\u00F4"
		keyList[0][2][11] = u"\u00A7"
		keyList[0][3][1] = u"&"
		keyList[1][0] = [u"\u00B0", u"1", u"2", u"3", u"4", u"5", u"6", u"7", u"8", u"9", u"0", u"%", u"\u02C7", u"BACKSPACEICON"]
		keyList[1][1][11] = u"/"
		keyList[1][1][12] = u"("
		keyList[1][1][13] = u")"
		keyList[1][2][10] = u"\""
		keyList[1][2][11] = u"!"
		keyList[1][3][1] = u"*"
		keyList[1][3][9] = u"?"
		del keyList[2]
		keyList.append([
			[u"", u"~", u"\u02C7", u"^", u"\u02D8", u"\u00B0", u"\u02DB", u"`", u"\u02D9", u"\u00B4", u"\u02DD", u"\u00A8", u"\u00B8", u"BACKSPACEICON"],
			[u"FIRSTICON", u"\\", u"|", u"\u20AC", u"", u"", u"", u"", u"", u"", u"'", u"\u00F7", u"\u00D7", u"\u00A4"],
			[u"LASTICON", u"", u"\u0111", u"\u0110", u"[", u"]", u"", u"", u"\u0142", u"\u0141", u"$", u"\u00DF", self.green, self.green],
			[u"CAPSLOCKICON", u"<", u">", u"#", u"&", u"@", u"{", u"}", u"", u"<", u">", u"*", u"CAPSLOCKICON", u"CAPSLOCKICON"],
			self.footer
		])
		return keyList

	def ukranian(self, base):
		keyList = deepcopy(base)
		keyList[0][1][12] = u"\u0457"
		keyList[0][1][13] = u"\\"
		keyList[0][2][11] = u"\u0454"
		keyList[0][2][2] = u"\u0456"
		keyList[0][3][1] = u"\u0491"
		keyList[1][1][12] = u"\u0407"
		keyList[1][1][13] = u"/"
		keyList[1][2][11] = u"\u0404"
		keyList[1][2][2] = u"\u0406"
		keyList[1][3][1] = u"\u0490"
		return keyList

	def ukranianEnhanced(self, base):
		keyList = self.ukranian(base)
		keyList[0][0][0] = u"\u0027"
		keyList[1][0][0] = u"\u20B4"
		return keyList

	def unitedKingdom(self, base):
		keyList = deepcopy(base)
		keyList[0][1][13] = u"#"
		keyList[0][3] = [u"CAPSLOCKICON", u"\\", u"z", u"x", u"c", u"v", u"b", u"n", u"m", u",", u".", u"/", u"CAPSLOCKICON", u"CAPSLOCKICON"]
		keyList[0][4] = copy(self.footer)
		keyList[0][4][10] = u"\u00A6"
		keyList[1][0][0] = u"\u00AC"
		keyList[1][0][2] = u"\""
		keyList[1][0][3] = u"\u00A3"
		keyList[1][1][13] = u"~"
		keyList[1][2][11] = u"@"
		keyList[1][3] = [u"CAPSLOCKICON", u"|", u"Z", u"X", u"C", u"V", u"B", u"N", u"M", u"<", u">", u"?", u"CAPSLOCKICON", u"CAPSLOCKICON"]
		keyList[1][4] = copy(self.footer)
		keyList[1][4][10] = u"\u20AC"
		return keyList

	def smsGotChar(self):
		if self.smsChar and self.selectAsciiKey(self.smsChar):
			self.processSelect()

	def setLocale(self):
		self.language, self.location, self.keyList = self.locales.get(self.lang, [None, None, None])
		if self.language is None or self.location is None or self.keyList is None:
			self.lang = "en_EN"
			self.language = _("English")
			self.location = _("Various")
			self.keyList = self.english
		self.shiftLevel = 0
		self["locale"].setText(_("Locale") + ": " + self.lang + "  (" + self.language + " - " + self.location + ")")

	def buildVirtualKeyBoard(self):
		self.shiftLevels = len(self.keyList)  # Check the current shift level is available / valid in this layout.
		if self.shiftLevel >= self.shiftLevels:
			self.shiftLevel = 0
		self.keyboardWidth = len(self.keyList[self.shiftLevel][0])  # Determine current keymap size.
		self.keyboardHeight = len(self.keyList[self.shiftLevel])
		self.maxKey = self.keyboardWidth * (self.keyboardHeight - 1) + len(self.keyList[self.shiftLevel][-1]) - 1
		# print("[VirtualKeyBoard] DEBUG: Width=%d, Height=%d, Keys=%d, maxKey=%d, shiftLevels=%d" % (self.keyboardWidth, self.keyboardHeight, self.maxKey + 1, self.maxKey, self.shiftLevels))
		self.index = 0
		self.list = []
		for keys in self.keyList[self.shiftLevel]:  # Process all the buttons in this shift level.
			self.list.append(self.virtualKeyBoardEntryComponent(keys))
		self.previousSelectedKey = None
		if self.selectedKey is None:  # Start on the first character of the second row (EXIT button).
			self.selectedKey = self.keyboardWidth
		self.markSelectedKey()

	def virtualKeyBoardEntryComponent(self, keys):
		res = [keys]
		text = []
		offset = 14 - self.keyboardWidth  # 14 represents the maximum buttons per row as defined here and in the skin (14 x self.width).
		x = self.width * offset // 2
		if offset % 2:
			x += self.width // 2
		xHighlight = x
		prevKey = None
		for key in keys:
			if key != prevKey:
				xData = x + self.padding[0]
				start, width = self.findStartAndWidth(self.index)
				if self.bg_l is None or self.bg_m is None or self.bg_r is None:  # If available display the cell background.
					x += self.width * width
				else:
					w = self.bg_l.size().width()
					res.append(MultiContentEntryPixmapAlphaTest(pos=(x, 0), size=(w, self.height), png=self.bg_l))
					x += w
					w = self.bg_m.size().width() + (self.width * (width - 1))
					res.append(MultiContentEntryPixmapAlphaTest(pos=(x, 0), size=(w, self.height), png=self.bg_m, flags=BT_SCALE))
					x += w
					w = self.bg_r.size().width()
					res.append(MultiContentEntryPixmapAlphaTest(pos=(x, 0), size=(w, self.height), png=self.bg_r))
					x += w
				highlight = self.keyHighlights.get(key.upper(), (None, None, None))  # Check if the cell needs to be highlighted.
				if highlight[0] is None or highlight[1] is None or highlight[2] is None:  # If available display the cell highlight.
					xHighlight += self.width * width
				else:
					w = highlight[0].size().width()
					res.append(MultiContentEntryPixmapAlphaTest(pos=(xHighlight, 0), size=(w, self.height), png=highlight[0]))
					xHighlight += w
					w = highlight[1].size().width() + (self.width * (width - 1))
					res.append(MultiContentEntryPixmapAlphaTest(pos=(xHighlight, 0), size=(w, self.height), png=highlight[1], flags=BT_SCALE))
					xHighlight += w
					w = highlight[2].size().width()
					res.append(MultiContentEntryPixmapAlphaTest(pos=(xHighlight, 0), size=(w, self.height), png=highlight[2]))
					xHighlight += w
				if self.alignment[0] == 1:  # Determine the cell alignment.
					alignH = RT_HALIGN_LEFT
				elif self.alignment[0] == 2:
					alignH = RT_HALIGN_CENTER
				elif self.alignment[0] == 3:
					alignH = RT_HALIGN_RIGHT
				else:
					if start == 0 and width > 1:
						alignH = RT_HALIGN_LEFT
					elif start + width == self.keyboardWidth and width > 1:
						alignH = RT_HALIGN_RIGHT
					else:
						alignH = RT_HALIGN_CENTER
				if self.alignment[1] == 1:
					alignV = RT_VALIGN_TOP
				elif self.alignment[1] == 3:
					alignV = RT_VALIGN_BOTTOM
				else:
					alignV = RT_VALIGN_CENTER
				w = (width * self.width) - (self.padding[0] * 2)  # Determine the cell data area.
				h = self.height - (self.padding[1] * 2)
				image = self.keyImages[self.shiftLevel].get(key, None)  # Check if the cell contains an image.
				if image:  # Display the cell image.
					left = xData
					wImage = image.size().width()
					if alignH == RT_HALIGN_CENTER:
						left += (w - wImage) // 2
					elif alignH == RT_HALIGN_RIGHT:
						left += w - wImage
					top = self.padding[1]
					hImage = image.size().height()
					if alignV == RT_VALIGN_CENTER:
						top += (h - hImage) // 2
					elif alignV == RT_VALIGN_BOTTOM:
						top += h - hImage
					res.append(MultiContentEntryPixmapAlphaTest(pos=(left, top), size=(wImage, hImage), png=image))
					# print("[VirtualKeyBoard] DEBUG: Left=%d, Top=%d, Width=%d, Height=%d, Image Width=%d, Image Height=%d" % (left, top, w, h, wImage, hImage))
				else:  # Display the cell text.
					if len(key) > 1:  # NOTE: UTF8 / Unicode glyphs only count as one character here.
						text.append(MultiContentEntryText(pos=(xData, self.padding[1]), size=(w, h), font=1, flags=alignH | alignV, text=key.encode("utf-8"), color=self.shiftColors[self.shiftLevel]))
					else:
						text.append(MultiContentEntryText(pos=(xData, self.padding[1]), size=(w, h), font=0, flags=alignH | alignV, text=key.encode("utf-8"), color=self.shiftColors[self.shiftLevel]))
			prevKey = key
			self.index += 1
		return res + text

	def markSelectedKey(self):
		if self.sel_l is None or self.sel_m is None or self.sel_r is None:
			return
		if self.previousSelectedKey is not None:
			del self.list[self.previousSelectedKey // self.keyboardWidth][-3:]
		if self.selectedKey > self.maxKey:
			self.selectedKey = self.maxKey
		start, width = self.findStartAndWidth(self.selectedKey)
		x = start * self.width
		w = self.sel_l.size().width()
		self.list[self.selectedKey // self.keyboardWidth].append(MultiContentEntryPixmapAlphaTest(pos=(x, 0), size=(w, self.height), png=self.sel_l))
		x += w
		w = self.sel_m.size().width() + (self.width * (width - 1))
		self.list[self.selectedKey // self.keyboardWidth].append(MultiContentEntryPixmapAlphaTest(pos=(x, 0), size=(w, self.height), png=self.sel_m, flags=BT_SCALE))
		x += w
		w = self.sel_r.size().width()
		self.list[self.selectedKey // self.keyboardWidth].append(MultiContentEntryPixmapAlphaTest(pos=(x, 0), size=(w, self.height), png=self.sel_r))
		self.previousSelectedKey = self.selectedKey
		self["list"].setList(self.list)

	def findStartAndWidth(self, key):
		if key > self.maxKey:
			key = self.maxKey
		row = key // self.keyboardWidth
		key = key % self.keyboardWidth
		start = key
		while start:
			if self.keyList[self.shiftLevel][row][start - 1] != self.keyList[self.shiftLevel][row][key]:
				break
			start -= 1
		max = len(self.keyList[self.shiftLevel][row])
		width = 1
		while width <= max:
			if start + width >= max or self.keyList[self.shiftLevel][row][start + width] != self.keyList[self.shiftLevel][row][key]:
				break
			width += 1
		# print("[VirtualKeyBoard] DEBUG: Key='%s', Position=%d, Start=%d, Width=%d" % (self.keyList[self.shiftLevel][row][key], key, start, width))
		return (start, width)

	def processSelect(self):
		self.smsChar = None
		text = self.keyList[self.shiftLevel][self.selectedKey // self.keyboardWidth][self.selectedKey % self.keyboardWidth].encode("UTF-8")
		cmd = self.cmds.get(text.upper(), None)
		if cmd is None:
			self['text'].char(text.encode('UTF-8'))
		else:
			exec(cmd)
		if text not in (u"SHIFT", u"SHIFTICON") and self.shiftHold != -1:
			self.shiftRestore()

	def cancel(self):
		self.close(None)

	def save(self):
		self.close(self["text"].getText())

	def localeMenu(self):
		languages = []
		for locale, data in self.locales.iteritems():
			languages.append((data[0] + "  -  " + data[1] + "  (" + locale + ")", locale))
		languages = sorted(languages)
		index = 0
		default = 0
		for item in languages:
			if item[1] == self.lang:
				default = index
				break
			index += 1
		self.session.openWithCallback(self.localeMenuCallback, ChoiceBox, _("Available locales are:"), list=languages, selection=default, keys=[])

	def localeMenuCallback(self, choice):
		if choice:
			self.lang = choice[1]
			self.setLocale()
			self.buildVirtualKeyBoard()

	def shiftSelected(self):
		if self.shiftHold == -1:
			self.shiftHold = self.shiftLevel
		self.capsLockSelected()

	def capsLockSelected(self):
		self.shiftLevel = (self.shiftLevel + 1) % self.shiftLevels
		self.shiftCommon()

	def shiftCommon(self):
		self.smsChar = None
		nextLevel = (self.shiftLevel + 1) % self.shiftLevels
		self["key_blue"].setText(self.shiftMsgs[nextLevel])
		self.buildVirtualKeyBoard()

	def shiftRestore(self):
		self.shiftLevel = self.shiftHold
		self.shiftHold = -1
		self.shiftCommon()

	def keyToggleOW(self):
		self["text"].toggleOverwrite()
		self.overwrite = not self.overwrite
		if self.overwrite:
			self["mode"].setText(_("OVR"))
		else:
			self["mode"].setText(_("INS"))

	def backSelected(self):
		self["text"].deleteBackward()

	def forwardSelected(self):
		self["text"].deleteForward()

	def eraseAll(self):
		self['text'].deleteAllChars()
		self['text'].update()

	def cursorFirst(self):
		self["text"].home()

	def cursorLeft(self):
		self["text"].left()

	def cursorRight(self):
		self["text"].right()

	def cursorLast(self):
		self["text"].end()

	def up(self):
		self.smsChar = None
		self.selectedKey -= self.keyboardWidth
		if self.selectedKey < 0:
			self.selectedKey = self.maxKey // self.keyboardWidth * self.keyboardWidth + self.selectedKey % self.keyboardWidth
			if self.selectedKey > self.maxKey:
				self.selectedKey -= self.keyboardWidth
		self.markSelectedKey()

	def left(self):
		self.smsChar = None
		start, width = self.findStartAndWidth(self.selectedKey)
		if width > 1:
			width = self.selectedKey % self.keyboardWidth - start + 1
		self.selectedKey = self.selectedKey // self.keyboardWidth * self.keyboardWidth + (self.selectedKey + self.keyboardWidth - width) % self.keyboardWidth
		if self.selectedKey > self.maxKey:
			self.selectedKey = self.maxKey
		self.markSelectedKey()

	def right(self):
		self.smsChar = None
		start, width = self.findStartAndWidth(self.selectedKey)
		if width > 1:
			width = start + width - self.selectedKey % self.keyboardWidth
		self.selectedKey = self.selectedKey // self.keyboardWidth * self.keyboardWidth + (self.selectedKey + width) % self.keyboardWidth
		if self.selectedKey > self.maxKey:
			self.selectedKey = self.selectedKey // self.keyboardWidth * self.keyboardWidth
		self.markSelectedKey()

	def down(self):
		self.smsChar = None
		self.selectedKey += self.keyboardWidth
		if self.selectedKey > self.maxKey:
			self.selectedKey %= self.keyboardWidth
		self.markSelectedKey()

	def keyNumberGlobal(self, number):
		self.smsChar = self.sms.getKey(number)
		self.selectAsciiKey(self.smsChar)

	def keyGotAscii(self):
		self.smsChar = None
		if self.selectAsciiKey(str(unichr(getPrevAsciiCode()).encode("utf-8"))):
			self.processSelect()

	def selectAsciiKey(self, char):
		if char == u" ":
			char = SPACE
		self.shiftLevel = -1
		for keyList in (self.keyList):
			self.shiftLevel = (self.shiftLevel + 1) % self.shiftLevels
			self.buildVirtualKeyBoard()
			selkey = 0
			for keys in keyList:
				for key in keys:
					if key == char:
						self.selectedKey = selkey
						self.markSelectedKey()
						return True
					selkey += 1
		return False

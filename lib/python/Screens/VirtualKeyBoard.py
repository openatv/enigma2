from copy import copy, deepcopy

from enigma import BT_SCALE, RT_HALIGN_CENTER, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_BOTTOM, RT_VALIGN_CENTER, RT_VALIGN_TOP, eListboxPythonMultiContent, getPrevAsciiCode, gFont

from skin import fonts, parameters
from Components.ActionMap import HelpableNumberActionMap
from Components.Input import Input
from Components.Label import Label
from Components.International import international
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryPixmapAlphaBlend, MultiContentEntryText
from Components.Sources.StaticText import StaticText
from Screens.ChoiceBox import ChoiceBox
from Screens.HelpMenu import HelpableScreen
from Screens.Screen import Screen
from Tools.Directories import SCOPE_GUISKIN, resolveFilename
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

SPACE = "SPACEICON"  # Symbol to be used for a SPACE on the keyboard.  Must be "SPACE" (any case), "SPACEICON" or "SPACEICONALT".


class VirtualKeyBoardList(MenuList):
	def __init__(self, list, enableWrapAround=False):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		font = fonts.get("VirtualKeyBoard", ("Regular", 28, 45))
		self.l.setFont(0, gFont(font[0], font[1]))
		self.l.setFont(1, gFont(font[0], int(font[1] * 5 // 9)))  # Smaller font is 56% the height of bigger font.
		self.l.setItemHeight(font[2])


# For more information about using VirtualKeyBoard see /doc/VIRTUALKEYBOARD.
#
class VirtualKeyBoard(Screen, HelpableScreen):
	def __init__(self, session, title=_("Virtual KeyBoard Text:"), text="", maxSize=False, visible_width=False, type=Input.TEXT, currPos=None, allMarked=False, style=VKB_ENTER_ICON, windowTitle=None):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		self.setTitle(_("Virtual KeyBoard") if windowTitle is None else windowTitle)
		prompt = title  # Title should only be used for screen titles!
		greenLabel, self.green = {
			VKB_DONE_ICON: ("Done", "ENTERICON"),
			VKB_ENTER_ICON: ("Enter", "ENTERICON"),
			VKB_OK_ICON: ("OK", "ENTERICON"),
			VKB_SAVE_ICON: ("Save", "ENTERICON"),
			VKB_SEARCH_ICON: ("Search", "ENTERICON"),
			VKB_DONE_TEXT: ("Done", _("Done")),
			VKB_ENTER_TEXT: ("Done", _("Enter")),
			VKB_OK_TEXT: ("OK", _("OK")),
			VKB_SAVE_TEXT: ("Save", _("Save")),
			VKB_SEARCH_TEXT: ("Search", _("Search"))
		}.get(style, ("Enter", "ENTERICON"))
		self.bg = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_bg.png"))  # Legacy support only!
		self.bg_l = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_bg_l.png"))
		self.bg_m = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_bg_m.png"))
		self.bg_r = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_bg_r.png"))
		self.sel_l = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_sel_l.png"))
		self.sel_m = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_sel_m.png"))
		self.sel_r = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_sel_r.png"))
		key_red_l = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_red_l.png"))
		key_red_m = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_red_m.png"))
		key_red_r = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_red_r.png"))
		key_green_l = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_green_l.png"))
		key_green_m = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_green_m.png"))
		key_green_r = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_green_r.png"))
		key_yellow_l = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_yellow_l.png"))
		key_yellow_m = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_yellow_m.png"))
		key_yellow_r = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_yellow_r.png"))
		key_blue_l = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_blue_l.png"))
		key_blue_m = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_blue_m.png"))
		key_blue_r = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_blue_r.png"))
		key_backspace = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_backspace.png"))
		key_clear = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_clear.png"))
		key_delete = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_delete.png"))
		key_enter = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_enter.png"))
		key_exit = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_exit.png"))
		key_first = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_first.png"))
		key_last = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_last.png"))
		key_left = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_left.png"))
		key_locale = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_locale.png"))
		key_right = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_right.png"))
		key_shift = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_shift.png"))
		key_shift0 = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_shift0.png"))
		key_shift1 = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_shift1.png"))
		key_shift2 = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_shift2.png"))
		key_shift3 = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_shift3.png"))
		key_space = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_space.png"))
		key_space_alt = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_space_alt.png"))
		self.keyHighlights = {  # This is a table of cell highlight components (left, middle and right)
			"EXIT": (key_red_l, key_red_m, key_red_r),
			"EXITICON": (key_red_l, key_red_m, key_red_r),
			"DONE": (key_green_l, key_green_m, key_green_r),
			"ENTER": (key_green_l, key_green_m, key_green_r),
			"ENTERICON": (key_green_l, key_green_m, key_green_r),
			"OK": (key_green_l, key_green_m, key_green_r),
			"SAVE": (key_green_l, key_green_m, key_green_r),
			# "LOC": (key_yellow_l, key_yellow_m, key_yellow_r),
			# "LOCALE": (key_yellow_l, key_yellow_m, key_yellow_r),
			# "LOCALEICON": (key_yellow_l, key_yellow_m, key_yellow_r),
			"SHIFT": (key_yellow_l, key_yellow_m, key_yellow_r),
			"SHIFTICON": (key_yellow_l, key_yellow_m, key_yellow_r),
			"CAPS": (key_blue_l, key_blue_m, key_blue_r),
			"LOCK": (key_blue_l, key_blue_m, key_blue_r),
			"CAPSLOCK": (key_blue_l, key_blue_m, key_blue_r),
			"CAPSLOCKICON": (key_blue_l, key_blue_m, key_blue_r)
		}
		self.shiftMsgs = [
			_("Lower case"),
			_("Upper case"),
			_("Special 1"),
			_("Special 2")
		]
		self.keyImages = [{
			# "ALLICON": key_all,
			"BACKSPACEICON": key_backspace,
			"CAPSLOCKICON": key_shift0,
			"CLEARICON": key_clear,
			"DELETEICON": key_delete,
			"ENTERICON": key_enter,
			"EXITICON": key_exit,
			"FIRSTICON": key_first,
			"LASTICON": key_last,
			"LOCALEICON": key_locale,
			"LEFTICON": key_left,
			"RIGHTICON": key_right,
			"SHIFTICON": key_shift,
			"SPACEICON": key_space,
			"SPACEICONALT": key_space_alt
		}, {
			# "ALLICON": key_all,
			"BACKSPACEICON": key_backspace,
			"CAPSLOCKICON": key_shift1,
			"CLEARICON": key_clear,
			"DELETEICON": key_delete,
			"ENTERICON": key_enter,
			"EXITICON": key_exit,
			"FIRSTICON": key_first,
			"LASTICON": key_last,
			"LEFTICON": key_left,
			"LOCALEICON": key_locale,
			"RIGHTICON": key_right,
			"SHIFTICON": key_shift,
			"SPACEICON": key_space,
			"SPACEICONALT": key_space_alt
		}, {
			# "ALLICON": key_all,
			"BACKSPACEICON": key_backspace,
			"CAPSLOCKICON": key_shift2,
			"CLEARICON": key_clear,
			"DELETEICON": key_delete,
			"ENTERICON": key_enter,
			"EXITICON": key_exit,
			"FIRSTICON": key_first,
			"LASTICON": key_last,
			"LEFTICON": key_left,
			"LOCALEICON": key_locale,
			"RIGHTICON": key_right,
			"SHIFTICON": key_shift,
			"SPACEICON": key_space,
			"SPACEICONALT": key_space_alt
		}, {
			# "ALLICON": key_all,
			"BACKSPACEICON": key_backspace,
			"CAPSLOCKICON": key_shift3,
			"CLEARICON": key_clear,
			"DELETEICON": key_delete,
			"ENTERICON": key_enter,
			"EXITICON": key_exit,
			"FIRSTICON": key_first,
			"LASTICON": key_last,
			"LEFTICON": key_left,
			"LOCALEICON": key_locale,
			"RIGHTICON": key_right,
			"SHIFTICON": key_shift,
			"SPACEICON": key_space,
			"SPACEICONALT": key_space_alt
		}]
		self.cmds = {
			"": "pass",
			"ALL": "self['text'].markAll()",
			"ALLICON": "self['text'].markAll()",
			"BACK": "self['text'].deleteBackward()",
			"BACKSPACE": "self['text'].deleteBackward()",
			"BACKSPACEICON": "self['text'].deleteBackward()",
			"BLANK": "pass",
			"CAPS": "self.capsLockSelected()",
			"CAPSLOCK": "self.capsLockSelected()",
			"CAPSLOCKICON": "self.capsLockSelected()",
			"CLEAR": "self['text'].deleteAllChars()\nself['text'].update()",
			"CLEARICON": "self['text'].deleteAllChars()\nself['text'].update()",
			"CLR": "self['text'].deleteAllChars()\nself['text'].update()",
			"DEL": "self['text'].deleteForward()",
			"DELETE": "self['text'].deleteForward()",
			"DELETEICON": "self['text'].deleteForward()",
			"DONE": "self.save()",
			"ENTER": "self.save()",
			"ENTERICON": "self.save()",
			"ESC": "self.cancel()",
			"EXIT": "self.cancel()",
			"EXITICON": "self.cancel()",
			"FIRST": "self['text'].home()",
			"FIRSTICON": "self['text'].home()",
			"LAST": "self['text'].end()",
			"LASTICON": "self['text'].end()",
			"LEFT": "self['text'].left()",
			"LEFTICON": "self['text'].left()",
			"LOC": "self.localeMenu()",
			"LOCALE": "self.localeMenu()",
			"LOCALEICON": "self.localeMenu()",
			"LOCK": "self.capsLockSelected()",
			"OK": "self.save()",
			"RIGHT": "self['text'].right()",
			"RIGHTICON": "self['text'].right()",
			"SAVE": "self.save()",
			"SHIFT": "self.shiftSelected()",
			"SHIFTICON": "self.shiftSelected()",
			"SPACE": "self['text'].char(' ')",
			"SPACEICON": "self['text'].char(' ')",
			"SPACEICONALT": "self['text'].char(' ')"
		}
		self.footer = ["EXITICON", "LEFTICON", "RIGHTICON", SPACE, SPACE, SPACE, SPACE, SPACE, SPACE, SPACE, "SHIFTICON", "LOCALEICON", "CLEARICON", "DELETEICON"]
		self.czech = [
			[
				[";", "+", "\u011B", "\u0161", "\u010D", "\u0159", "\u017E", "\u00FD", "\u00E1", "\u00ED", "\u00E9", "=", "", "BACKSPACEICON"],
				["FIRSTICON", "q", "w", "e", "r", "t", "z", "u", "i", "o", "p", "\u00FA", "(", ")"],
				["LASTICON", "a", "s", "d", "f", "g", "h", "j", "k", "l", "\u016F", "\u00A7", self.green, self.green],
				["CAPSLOCKICON", "\\", "y", "x", "c", "v", "b", "n", "m", ",", ".", "-", "CAPSLOCKICON", "CAPSLOCKICON"],
				self.footer
			], [
				[".", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "%", "'", "BACKSPACEICON"],
				["FIRSTICON", "Q", "W", "E", "R", "T", "Z", "U", "I", "O", "P", "/", "(", ")"],
				["LASTICON", "A", "S", "D", "F", "G", "H", "J", "K", "L", "\"", "!", self.green, self.green],
				["CAPSLOCKICON", "|", "Y", "X", "C", "V", "B", "N", "M", "?", ":", "_", "CAPSLOCKICON", "CAPSLOCKICON"],
				self.footer
			], [
				["\u00B0", "~", "\u011A", "\u0160", "\u010C", "\u0158", "\u017D", "\u00DD", "\u00C1", "\u00CD", "\u00C9", "`", "'", "BACKSPACEICON"],
				["FIRSTICON", "\\", "|", "\u20AC", "\u0165", "\u0164", "\u0148", "\u0147", "\u00F3", "\u00D3", "\u00DA", "\u00F7", "\u00D7", "\u00A4"],
				["LASTICON", "", "\u0111", "\u00D0", "[", "]", "\u010F", "\u010E", "\u0142", "\u0141", "\u016E", "\u00DF", self.green, self.green],
				["CAPSLOCKICON", "", "", "#", "&", "@", "{", "}", "$", "<", ">", "*", "CAPSLOCKICON", "CAPSLOCKICON"],
				self.footer
			]
		]
		self.english = [
			[
				["`", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=", "BACKSPACEICON"],
				["FIRSTICON", "q", "w", "e", "r", "t", "y", "u", "i", "o", "p", "[", "]", "\\"],
				["LASTICON", "a", "s", "d", "f", "g", "h", "j", "k", "l", ";", "'", self.green, self.green],
				["CAPSLOCKICON", "CAPSLOCKICON", "z", "x", "c", "v", "b", "n", "m", ",", ".", "/", "CAPSLOCKICON", "CAPSLOCKICON"],
				self.footer
			], [
				["~", "!", "@", "#", "$", "%", "^", "&", "*", "(", ")", "_", "+", "BACKSPACEICON"],
				["FIRSTICON", "Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "{", "}", "|"],
				["LASTICON", "A", "S", "D", "F", "G", "H", "J", "K", "L", ":", "\"", self.green, self.green],
				["CAPSLOCKICON", "CAPSLOCKICON", "Z", "X", "C", "V", "B", "N", "M", "<", ">", "?", "CAPSLOCKICON", "CAPSLOCKICON"],
				self.footer
			]
		]
		self.french = [
			[
				["\u00B2", "&", "\u00E9", "\"", "'", "(", "-", "\u00E8", "_", "\u00E7", "\u00E0", ")", "=", "BACKSPACEICON"],
				["FIRSTICON", "a", "z", "e", "r", "t", "y", "u", "i", "o", "p", "^", "$", "*"],
				["LASTICON", "q", "s", "d", "f", "g", "h", "j", "k", "l", "m", "\u00F9", self.green, self.green],
				["CAPSLOCKICON", "<", "w", "x", "c", "v", "b", "n", ",", ";", ":", "!", "CAPSLOCKICON", "CAPSLOCKICON"],
				self.footer
			], [
				["", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "\u00B0", "+", "BACKSPACEICON"],
				["FIRSTICON", "A", "Z", "E", "R", "T", "Y", "U", "I", "O", "P", "\u00A8", "\u00A3", "\u00B5"],
				["LASTICON", "Q", "S", "D", "F", "G", "H", "J", "K", "L", "M", "%", self.green, self.green],
				["CAPSLOCKICON", ">", "W", "X", "C", "V", "B", "N", "?", ".", "/", "\u00A7", "CAPSLOCKICON", "CAPSLOCKICON"],
				self.footer
			], [
				["", "", "~", "#", "{", "[", "|", "`", "\\", "^", "@", "]", "}", "BACKSPACEICON"],
				["FIRSTICON", "", "", "\u20AC", "", "", "", "", "", "", "", "", "\u00A4", ""],
				["LASTICON", "", "", "", "", "", "", "", "", "", "", "", self.green, self.green],
				["CAPSLOCKICON", "", "", "", "", "", "", "", "", "", "", "", "CAPSLOCKICON", "CAPSLOCKICON"],
				self.footer
			], [
				["", "", "\u00E2", "\u00EA", "\u00EE", "\u00F4", "\u00FB", "\u00E4", "\u00EB", "\u00EF", "\u00F6", "\u00FC", "", "BACKSPACEICON"],
				["FIRSTICON", "", "\u00E0", "\u00E8", "\u00EC", "\u00F2", "\u00F9", "\u00E1", "\u00E9", "\u00ED", "\u00F3", "\u00FA", "", ""],
				["LASTICON", "", "\u00C2", "\u00CA", "\u00CE", "\u00D4", "\u00DB", "\u00C4", "\u00CB", "\u00CF", "\u00D6", "\u00DC", self.green, self.green],
				["CAPSLOCKICON", "", "\u00C0", "\u00C8", "\u00CC", "\u00D2", "\u00D9", "\u00C1", "\u00C9", "\u00CD", "\u00D3", "\u00DA", "CAPSLOCKICON", "CAPSLOCKICON"],
				self.footer
			]
		]
		self.german = [
			[
				["^", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "\u00DF", "'", "BACKSPACEICON"],
				["FIRSTICON", "q", "w", "e", "r", "t", "z", "u", "i", "o", "p", "\u00FC", "+", "#"],
				["LASTICON", "a", "s", "d", "f", "g", "h", "j", "k", "l", "\u00F6", "\u00E4", self.green, self.green],
				["CAPSLOCKICON", "<", "y", "x", "c", "v", "b", "n", "m", ",", ".", "-", "CAPSLOCKICON", "CAPSLOCKICON"],
				self.footer
			], [
				["\u00B0", "!", "\"", "\u00A7", "$", "%", "&", "/", "(", ")", "=", "?", "`", "BACKSPACEICON"],
				["FIRSTICON", "Q", "W", "E", "R", "T", "Z", "U", "I", "O", "P", "\u00DC", "*", "'"],
				["LASTICON", "A", "S", "D", "F", "G", "H", "J", "K", "L", "\u00D6", "\u00C4", self.green, self.green],
				["CAPSLOCKICON", ">", "Y", "X", "C", "V", "B", "N", "M", ";", ":", "_", "CAPSLOCKICON", "CAPSLOCKICON"],
				self.footer
			], [
				["", "", "\u00B2", "\u00B3", "", "", "", "{", "[", "]", "}", "\\", "\u1E9E", "BACKSPACEICON"],
				["FIRSTICON", "@", "", "\u20AC", "", "", "", "", "", "", "", "", "~", ""],
				["LASTICON", "", "", "", "", "", "", "", "", "", "", "", self.green, self.green],
				["CAPSLOCKICON", "|", "", "", "", "", "", "", "\u00B5", "", "", "", "CAPSLOCKICON", "CAPSLOCKICON"],
				self.footer
			]
		]
		self.greek = [
			[
				["`", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=", "BACKSPACEICON"],
				["FIRSTICON", ";", "\u03C2", "\u03B5", "\u03C1", "\u03C4", "\u03C5", "\u03B8", "\u03B9", "\u03BF", "\u03C0", "[", "]", "\\"],
				["LASTICON", "\u03B1", "\u03C3", "\u03B4", "\u03C6", "\u03B3", "\u03B7", "\u03BE", "\u03BA", "\u03BB", "\u0384", "'", self.green, self.green],
				["CAPSLOCKICON", "<", "\u03B6", "\u03C7", "\u03C8", "\u03C9", "\u03B2", "\u03BD", "\u03BC", ",", ".", "/", "CAPSLOCKICON", "CAPSLOCKICON"],
				self.footer
			], [
				["~", "!", "@", "#", "$", "%", "^", "&", "*", "(", ")", "_", "+", "BACKSPACEICON"],
				["FIRSTICON", ":", "\u0385", "\u0395", "\u03A1", "\u03A4", "\u03A5", "\u0398", "\u0399", "\u039F", "\u03A0", "{", "}", "|"],
				["LASTICON", "\u0391", "\u03A3", "\u0394", "\u03A6", "\u0393", "\u0397", "\u039E", "\u039A", "\u039B", "\u00A8", "\"", self.green, self.green],
				["CAPSLOCKICON", ">", "\u0396", "\u03A7", "\u03A8", "\u03A9", "\u0392", "\u039D", "\u039C", "<", ">", "?", "CAPSLOCKICON", "CAPSLOCKICON"],
				self.footer
			], [
				["", "", "\u00B2", "\u00B3", "\u00A3", "\u00A7", "\u00B6", "", "\u00A4", "\u00A6", "\u00B0", "\u00B1", "\u00BD", "BACKSPACEICON"],
				["FIRSTICON", "", "\u03AC", "\u03AD", "\u03AE", "\u03AF", "\u03CC", "\u03CD", "\u03CE", "\u03CA", "\u03CB", "\u00AB", "\u00BB", "\u00AC"],
				["LASTICON", "", "\u0386", "\u0388", "\u0389", "\u038A", "\u038C", "\u038E", "\u038F", "\u03AA", "\u03AB", "\u0385", self.green, self.green],
				["CAPSLOCKICON", "CAPSLOCKICON", "", "", "", "\u00A9", "\u00AE", "\u20AC", "\u00A5", "\u0390", "\u03B0", "\u0387", "CAPSLOCKICON", "CAPSLOCKICON"],
				self.footer
			]
		]
		self.latvian = [
			[
				["", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "f", "BACKSPACEICON"],
				["FIRSTICON", "\u016B", "g", "j", "r", "m", "v", "n", "z", "\u0113", "\u010D", "\u017E", "h", "\u0137"],
				["LASTICON", "\u0161", "u", "s", "i", "l", "d", "a", "t", "e", "c", "\u00B4", self.green, self.green],
				["CAPSLOCKICON", "\u0123", "\u0146", "b", "\u012B", "k", "p", "o", "\u0101", ",", ".", "\u013C", "CAPSLOCKICON", "CAPSLOCKICON"],
				self.footer
			], [
				["?", "!", "\u00AB", "\u00BB", "$", "%", "/", "&", "\u00D7", "(", ")", "_", "F", "BACKSPACEICON"],
				["FIRSTICON", "\u016A", "G", "J", "R", "M", "V", "N", "Z", "\u0112", "\u010C", "\u017D", "H", "\u0136"],
				["LASTICON", "\u0160", "U", "S", "I", "L", "D", "A", "T", "E", "C", "\u00B0", self.green, self.green],
				["CAPSLOCKICON", "\u0122", "\u0145", "B", "\u012A", "K", "P", "O", "\u0100", ";", ":", "\u013B", "CAPSLOCKICON", "CAPSLOCKICON"],
				self.footer
			], [
				["", "\u00AB", "", "", "\u20AC", "\"", "'", "", ":", "", "", "\u2013", "=", "BACKSPACEICON"],
				["FIRSTICON", "q", "\u0123", "", "\u0157", "w", "y", "", "", "", "", "[", "]", ""],
				["LASTICON", "", "", "", "", "", "", "", "", "\u20AC", "", "\u00B4", self.green, self.green],
				["CAPSLOCKICON", "\\", "", "x", "", "\u0137", "", "\u00F5", "", "<", ">", "", "CAPSLOCKICON", "CAPSLOCKICON"],
				self.footer
			], [
				["", "", "@", "#", "$", "~", "^", "\u00B1", "", "", "", "\u2014", ";", "BACKSPACEICON"],
				["FIRSTICON", "Q", "\u0122", "", "\u0156", "W", "Y", "", "", "", "", "{", "}", ""],
				["LASTICON", "", "", "", "", "", "", "", "", "", "", "\u00A8", self.green, self.green],
				["CAPSLOCKICON", "|", "", "X", "", "\u0136", "", "\u00D5", "", "", "", "", "CAPSLOCKICON", "CAPSLOCKICON"],
				self.footer
			]
		]
		self.russian = [
			[
				["\u0451", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=", "BACKSPACEICON"],
				["FIRSTICON", "\u0439", "\u0446", "\u0443", "\u043A", "\u0435", "\u043D", "\u0433", "\u0448", "\u0449", "\u0437", "\u0445", "\u044A", "\\"],
				["LASTICON", "\u0444", "\u044B", "\u0432", "\u0430", "\u043F", "\u0440", "\u043E", "\u043B", "\u0434", "\u0436", "\u044D", self.green, self.green],
				["CAPSLOCKICON", "\\", "\u044F", "\u0447", "\u0441", "\u043C", "\u0438", "\u0442", "\u044C", "\u0431", "\u044E", ".", "CAPSLOCKICON", "CAPSLOCKICON"],
				self.footer
			], [
				["\u0401", "!", "\"", "\u2116", ";", "%", ":", "?", "*", "(", ")", "_", "+", "BACKSPACEICON"],
				["FIRSTICON", "\u0419", "\u0426", "\u0423", "\u041A", "\u0415", "\u041D", "\u0413", "\u0428", "\u0429", "\u0417", "\u0425", "\u042A", "/"],
				["LASTICON", "\u0424", "\u042B", "\u0412", "\u0410", "\u041F", "\u0420", "\u041E", "\u041B", "\u0414", "\u0416", "\u042D", self.green, self.green],
				["CAPSLOCKICON", "/", "\u042F", "\u0427", "\u0421", "\u041C", "\u0418", "\u0422", "\u042C", "\u0411", "\u042E", ",", "CAPSLOCKICON", "CAPSLOCKICON"],
				self.footer
			], [
				["", "", "", "", "", "", "", "", "", "", "", "", "", "BACKSPACEICON"],
				["FIRSTICON", "", "\u00A7", "@", "#", "&", "$", "\u20BD", "\u20AC", "", "", "", "", ""],
				["LASTICON", "", "<", ">", "[", "]", "{", "}", "", "", "", "", self.green, self.green],
				["CAPSLOCKICON", "", "", "", "", "", "", "", "", "", "", "", "CAPSLOCKICON", "CAPSLOCKICON"],
				self.footer
			]
		]
		self.scandinavian = [
			[
				["\u00A7", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "+", "\u00B4", "BACKSPACEICON"],
				["FIRSTICON", "q", "w", "e", "r", "t", "y", "u", "i", "o", "p", "\u00E5", "\u00A8", "'"],
				["LASTICON", "a", "s", "d", "f", "g", "h", "j", "k", "l", "\u00F6", "\u00E4", self.green, self.green],
				["CAPSLOCKICON", "<", "z", "x", "c", "v", "b", "n", "m", ",", ".", "-", "CAPSLOCKICON", "CAPSLOCKICON"],
				self.footer
			], [
				["\u00BD", "!", "\"", "#", "\u00A4", "%", "&", "/", "(", ")", "=", "?", "`", "BACKSPACEICON"],
				["FIRSTICON", "Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "\u00C5", "^", "*"],
				["LASTICON", "A", "S", "D", "F", "G", "H", "J", "K", "L", "\u00D6", "\u00C4", self.green, self.green],
				["CAPSLOCKICON", ">", "Z", "X", "C", "V", "B", "N", "M", ";", ":", "_", "CAPSLOCKICON", "CAPSLOCKICON"],
				self.footer
			], [
				["", "", "@", "\u00A3", "$", "\u20AC", "", "{", "[", "]", "}", "\\", "", "BACKSPACEICON"],
				["FIRSTICON", "", "", "\u20AC", "", "", "", "", "", "", "", "", "~", ""],
				["LASTICON", "", "", "", "", "", "", "", "", "", "", "", self.green, self.green],
				["CAPSLOCKICON", "|", "", "", "", "", "", "", "\u00B5", "", "", "", "CAPSLOCKICON", "CAPSLOCKICON"],
				self.footer
			], [
				["", "\u00E2", "\u00EA", "\u00EE", "\u00F4", "\u00FB", "\u00E4", "\u00EB", "\u00EF", "\u00F6", "\u00FC", "\u00E3", "", "BACKSPACEICON"],
				["FIRSTICON", "\u00E0", "\u00E8", "\u00EC", "\u00F2", "\u00F9", "\u00E1", "\u00E9", "\u00ED", "\u00F3", "\u00FA", "\u00F5", "", ""],
				["LASTICON", "\u00C2", "\u00CA", "\u00CE", "\u00D4", "\u00DB", "\u00C4", "\u00CB", "\u00CF", "\u00D6", "\u00DC", "\u00C3", self.green, self.green],
				["CAPSLOCKICON", "\u00C0", "\u00C8", "\u00CC", "\u00D2", "\u00D9", "\u00C1", "\u00C9", "\u00CD", "\u00D3", "\u00DA", "\u00D5", "CAPSLOCKICON", "CAPSLOCKICON"],
				self.footer
			]
		]
		self.spanish = [
			[
				["\u00BA", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "'", "\u00A1", "BACKSPACEICON"],
				["FIRSTICON", "q", "w", "e", "r", "t", "y", "u", "i", "o", "p", "`", "+", "\u00E7"],
				["LASTICON", "a", "s", "d", "f", "g", "h", "j", "k", "l", "\u00F1", "\u00B4", self.green, self.green],  # [, ]
				["CAPSLOCKICON", "<", "z", "x", "c", "v", "b", "n", "m", ",", ".", "-", "CAPSLOCKICON", "CAPSLOCKICON"],
				self.footer
			], [
				["\u00AA", "!", "\"", "\u00B7", "$", "%", "&", "/", "(", ")", "=", "?", "\u00BF", "BACKSPACEICON"],
				["FIRSTICON", "Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "^", "*", "\u00C7"],
				["LASTICON", "A", "S", "D", "F", "G", "H", "J", "K", "L", "\u00D1", "\u00A8", self.green, self.green],  # {, }
				["CAPSLOCKICON", ">", "Z", "X", "C", "V", "B", "N", "M", ";", ":", "_", "CAPSLOCKICON", "CAPSLOCKICON"],
				self.footer
			], [
				["\\", "|", "@", "#", "~", "\u20AC", "\u00AC", "", "", "", "", "", "", "BACKSPACEICON"],
				["FIRSTICON", "", "\u00E1", "\u00E9", "\u00ED", "\u00F3", "\u00FA", "\u00FC", "", "", "[", "]", "", ""],
				["LASTICON", "", "\u00C1", "\u00C9", "\u00CD", "\u00D3", "\u00DA", "\u00DC", "", "", "{", "}", self.green, self.green],
				["CAPSLOCKICON", "", "", "", "", "", "", "", "", "", "", "", "CAPSLOCKICON", "CAPSLOCKICON"],
				self.footer
			]
		]
		self.thai = [
			[
				["", "", "\u0E45", "\u0E20", "\u0E16", "\u0E38", "\u0E36", "\u0E04", "\u0E15", "\u0E08", "\u0E02", "\u0E0A", "", "BACKSPACEICON"],
				["FIRSTICON", "\u0E46", "\u0E44", "\u0E33", "\u0E1E", "\u0E30", "\u0E31", "\u0E35", "\u0E23", "\u0E19", "\u0E22", "\u0E1A", "\u0E25", ""],
				["LASTICON", "\u0E1F", "\u0E2B", "\u0E01", "\u0E14", "\u0E40", "\u0E49", "\u0E48", "\u0E32", "\u0E2A", "\u0E27", "\u0E07", "\u0E03", self.green],
				["CAPSLOCKICON", "CAPSLOCKICON", "\u0E1C", "\u0E1B", "\u0E41", "\u0E2D", "\u0E34", "\u0E37", "\u0E17", "\u0E21", "\u0E43", "\u0E1D", "CAPSLOCKICON", "CAPSLOCKICON"],
				self.footer
			], [
				["", "", "\u0E51", "\u0E52", "\u0E53", "\u0E54", "\u0E39", "\u0E55", "\u0E56", "\u0E57", "\u0E58", "\u0E59", "", "BACKSPACEICON"],
				["FIRSTICON", "\u0E50", "", "\u0E0E", "\u0E11", "\u0E18", "\u0E4D", "\u0E4A", "\u0E13", "\u0E2F", "\u0E0D", "\u0E10", "\u0E05", ""],
				["LASTICON", "\u0E24", "\u0E06", "\u0E0F", "\u0E42", "\u0E0C", "\u0E47", "\u0E4B", "\u0E29", "\u0E28", "\u0E0B", "", "\u0E3F", self.green],
				["CAPSLOCKICON", "CAPSLOCKICON", "", "\u0E09", "\u0E2E", "\u0E3A", "\u0E4C", "", "\u0E12", "\u0E2C", "\u0E26", "", "CAPSLOCKICON", "CAPSLOCKICON"],
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
		}, prio=0, description=_("Virtual KeyBoard Actions"))
		self.lang = international.getLocale()
		self["prompt"] = Label(prompt)
		self["text"] = Input(text=text, maxSize=maxSize, visible_width=visible_width, type=type, currPos=len(text) if currPos is None else currPos, allMarked=allMarked)
		self["list"] = VirtualKeyBoardList([])
		self["mode"] = Label(_("INS"))
		self["locale"] = Label("%s: %s" % (_("Locale"), self.lang))
		self["language"] = Label("%s: %s" % (_("Language"), self.lang))
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
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self["list"].instance.enableAutoNavigation(False)
		self.buildVirtualKeyBoard()

	def arabic(self, base):
		keyList = deepcopy(base)
		keyList[1][0][8] = "\u066D"
		keyList.extend([[
			["\u0630", "\u0661", "\u0662", "\u0663", "\u0664", "\u0665", "\u0666", "\u0667", "\u0668", "\u0669", "\u0660", "-", "=", "BACKSPACEICON"],
			["FIRSTICON", "\u0636", "\u0635", "\u062B", "\u0642", "\u0641", "\u063A", "\u0639", "\u0647", "\u062E", "\u062D", "\u062C", "\u062F", "\\"],
			["LASTICON", "\u0634", "\u0633", "\u064A", "\u0628", "\u0644", "\u0627", "\u062A", "\u0646", "\u0645", "\u0643", "\u0637", self.green, self.green],
			["CAPSLOCKICON", "CAPSLOCKICON", "\u0626", "\u0621", "\u0624", "\u0631", "\uFEFB", "\u0649", "\u0629", "\u0648", "\u0632", "\u0638", "CAPSLOCKICON", "CAPSLOCKICON"],
			self.footer
		], [
			["\u0651", "!", "@", "#", "$", "%", "^", "&", "\u066D", "(", ")", "_", "+", "BACKSPACEICON"],
			["FIRSTICON", "\u0636", "\u0635", "\u062B", "\u0642", "\u0641", "\u063A", "\u0639", "\u00F7", "\u00D7", "\u061B", ">", "<", "|"],
			["LASTICON", "\u0634", "\u0633", "\u064A", "\u0628", "\u0644", "\u0623", "\u0640", "\u060C", "/", ":", "\"", self.green, self.green],
			["CAPSLOCKICON", "CAPSLOCKICON", "\u0626", "\u0621", "\u0624", "\u0631", "\uFEF5", "\u0622", "\u0629", ",", ".", "\u061F", "CAPSLOCKICON", "CAPSLOCKICON"],
			self.footer
		]])
		return keyList

	def belgian(self, base):
		keyList = deepcopy(base)
		keyList[0][0][6] = "\u00A7"
		keyList[0][0][8] = "!"
		keyList[0][0][12] = "-"
		keyList[0][1][13] = "\u00B5"
		keyList[0][3][11] = "="
		keyList[1][0][0] = "\u00B3"
		keyList[1][0][12] = "_"
		keyList[1][1][11] = "\u00A8"
		keyList[1][1][12] = "*"
		keyList[1][1][13] = "\u00A3"
		keyList[1][3][11] = "+"
		keyList[2][0] = ["", "|", "@", "#", "{", "[", "^", "", "", "{", "}", "", "", "BACKSPACEICON"]
		keyList[2][1][11] = "["
		keyList[2][1][12] = "]"
		keyList[2][1][13] = "`"
		keyList[2][2][11] = "\u00B4"
		keyList[2][3][1] = "\\"
		keyList[2][3][11] = "~"
		return keyList

	def dutch(self, base):
		keyList = deepcopy(base)
		keyList[0][0][0] = "@"
		keyList[0][0][11] = "/"
		keyList[0][0][12] = "\u00B0"
		keyList[0][1][11] = "\u00A8"
		keyList[0][1][12] = "*"
		keyList[0][1][13] = "<"
		keyList[0][2][10] = "+"
		keyList[0][2][11] = "\u00B4"
		keyList[0][3] = ["CAPSLOCKICON", "]", "z", "x", "c", "v", "b", "n", "m", ",", ".", "-", "CAPSLOCKICON", "CAPSLOCKICON"]
		keyList[1][0] = ["\u00A7", "!", "\"", "#", "$", "%", "&", "_", "(", ")", "'", "?", "~", "BACKSPACEICON"]
		keyList[1][1][11] = "^"
		keyList[1][1][12] = "|"
		keyList[1][1][13] = ">"
		keyList[1][2][10] = "\u00B1"
		keyList[1][2][11] = "`"
		keyList[1][3] = ["CAPSLOCKICON", "[", "Z", "X", "C", "V", "B", "N", "M", ";", ":", "=", "CAPSLOCKICON", "CAPSLOCKICON"]
		keyList.append([
			["\u00AC", "\u00B9", "\u00B2", "\u00B3", "\u00BC", "\u00BD", "\u00BE", "\u00A3", "{", "}", "", "\\", "\u00B8", "BACKSPACEICON"],
			["FIRSTICON", "", "", "\u20AC", "\u00B6", "", "\u00E1", "\u00E9", "\u00ED", "\u00F3", "\u00FA", "", "", ""],
			["LASTICON", "", "\u00DF", "", "", "", "\u00C1", "\u00C9", "\u00CD", "\u00D3", "\u00DA", "", self.green, self.green],
			["CAPSLOCKICON", "\u00A6", "\u00AB", "\u00BB", "\u00A2", "", "", "", "\u00B5", "", "\u00B7", "", "CAPSLOCKICON", "CAPSLOCKICON"],
			self.footer
		])
		return keyList

	def estonian(self, base):
		keyList = deepcopy(base)
		keyList[0][0][0] = "\u02C7"
		keyList[0][1][11] = "\u00FC"
		keyList[0][1][12] = "\u00F5"
		keyList[1][0][0] = "~"
		keyList[1][1][11] = "\u00DC"
		keyList[1][1][12] = "\u00D5"
		keyList[2][1][12] = "\u00A7"
		keyList[2][1][13] = "\u00BD"
		keyList[2][2][2] = "\u0161"
		keyList[2][2][3] = "\u0160"
		keyList[2][2][11] = "^"
		keyList[2][3][2] = "\u017E"
		keyList[2][3][3] = "\u017D"
		keyList[2][3][8] = ""
		del keyList[3]
		return keyList

	def frenchSwiss(self, base):
		keyList = self.germanSwiss(base)
		keyList[0][0][11] = "'"
		keyList[0][0][12] = "^"
		keyList[0][1][11] = "\u00E8"
		keyList[0][2][10] = "\u00E9"
		keyList[0][2][11] = "\u00E0"
		keyList[1][1][11] = "\u00FC"
		keyList[1][2][10] = "\u00F6"
		keyList[1][2][11] = "\u00E4"
		return keyList

	def germanSwiss(self, base):
		keyList = deepcopy(base)
		keyList[0][0][0] = "\u00A7"
		keyList[0][0][11] = "'"
		keyList[0][0][12] = "^"
		keyList[0][1][12] = "\u00A8"
		keyList[0][1][13] = "$"
		keyList[1][0][1] = "+"
		keyList[1][0][3] = "*"
		keyList[1][0][4] = "\u00E7"
		keyList[1][0][11] = "?"
		keyList[1][0][12] = "`"
		keyList[1][1][11] = "\u00E8"
		keyList[1][1][12] = "!"
		keyList[1][1][13] = "\u00A3"
		keyList[1][2][10] = "\u00E9"
		keyList[1][2][11] = "\u00E0"
		keyList[2][0] = ["", "\u00A6", "@", "#", "\u00B0", "\u00A7", "\u00AC", "|", "\u00A2", "", "", "\u00B4", "~", "BACKSPACEICON"]
		keyList[2][1][1] = ""
		keyList[2][1][9] = "\u00DC"
		keyList[2][1][10] = "\u00C8"
		keyList[2][1][11] = "["
		keyList[2][1][12] = "]"
		keyList[2][2][6] = "\u00D6"
		keyList[2][2][7] = "\u00C9"
		keyList[2][2][8] = "\u00C4"
		keyList[2][2][9] = "\u00C0"
		keyList[2][2][10] = "{"
		keyList[2][2][11] = "}"
		keyList[2][3][1] = "\\"
		keyList[2][3][8] = ""
		return keyList

	def hungarian(self, base):
		keyList = deepcopy(base)
		keyList[0][0][0] = "0"
		keyList[0][0][10] = "\u00F6"
		keyList[0][0][11] = "\u00FC"
		keyList[0][0][12] = "\u00F3"
		keyList[0][1][11] = "\u0151"
		keyList[0][1][12] = "\u00FA"
		keyList[0][1][13] = "\u0171"
		keyList[0][2][10] = "\u00E9"
		keyList[0][2][11] = "\u00E1"
		keyList[0][3][1] = "\u00ED"
		keyList[1][0] = ["\u00A7", "'", "\"", "+", "!", "%", "/", "=", "(", ")", "\u00D6", "\u00DC", "\u00D3", "BACKSPACEICON"]
		keyList[1][1][11] = "\u0150"
		keyList[1][1][12] = "\u00DA"
		keyList[1][1][13] = "\u0170"
		keyList[1][2][10] = "\u00C9"
		keyList[1][2][11] = "\u00C1"
		keyList[1][3][1] = "\u00CD"
		keyList[1][3][9] = "?"
		del keyList[2]
		keyList.append([
			["", "~", "\u02C7", "^", "\u02D8", "\u00B0", "\u02DB", "`", "\u02D9", "\u00B4", "\u02DD", "\u00A8", "\u00B8", "BACKSPACEICON"],
			["FIRSTICON", "\\", "|", "\u00C4", "", "", "", "\u20AC", "\u00CD", "", "", "\u00F7", "\u00D7", "\u00A4"],
			["LASTICON", "\u00E4", "\u0111", "\u0110", "[", "]", "", "\u00ED", "\u0142", "\u0141", "$", "\u00DF", self.green, self.green],
			["CAPSLOCKICON", "<", ">", "#", "&", "@", "{", "}", "<", ";", ">", "*", "CAPSLOCKICON", "CAPSLOCKICON"],
			self.footer
		])
		return keyList

	def latvianQWERTY(self, base):
		keyList = self.latvianStandard(base)
		keyList[0][1][13] = "\u00B0"
		keyList[2][1][9] = "\u00F5"
		keyList[3][1][9] = "\u00D5"
		return keyList

	def latvianStandard(self, base):
		keyList = deepcopy(base)
		keyList[0][3][1] = "\\"
		keyList[1][3][1] = "|"
		keyList.append([
			["", "", "\u00AB", "\u00BB", "\u20AC", "", "\u2019", "", "", "", "", "\u2013", "", "BACKSPACEICON"],
			["FIRSTICON", "", "", "\u0113", "\u0157", "", "", "\u016B", "\u012B", "\u014D", "", "", "", ""],
			["LASTICON", "\u0101", "\u0161", "", "", "\u0123", "", "", "\u0137", "\u013C", "", "\u00B4", self.green, self.green],
			["CAPSLOCKICON", "", "\u017E", "", "\u010D", "", "", "\u0146", "", "", "", "", "CAPSLOCKICON", "CAPSLOCKICON"],
			self.footer
		])
		keyList.append([
			["", "", "", "", "\u00A7", "\u00B0", "", "\u00B1", "\u00D7", "", "", "\u2014", "", "BACKSPACEICON"],
			["FIRSTICON", "", "", "\u0112", "\u0156", "", "", "\u016A", "\u012A", "\u014C", "", "", "", ""],
			["LASTICON", "\u0100", "\u0160", "", "", "\u0122", "", "", "\u0136", "\u013B", "", "\u00A8", self.green, self.green],
			["CAPSLOCKICON", "", "\u017D", "", "\u010C", "", "", "\u0145", "", "", "", "", "CAPSLOCKICON", "CAPSLOCKICON"],
			self.footer
		])
		return keyList

	def lithuanian(self, base):
		keyList = deepcopy(base)
		keyList[0][0] = ["`", "\u0105", "\u010D", "\u0119", "\u0117", "\u012F", "\u0161", "\u0173", "\u016B", "9", "0", "-", "\u017E", "BACKSPACEICON"]
		keyList[0][3][1] = "\\"
		keyList[1][0] = ["~", "\u0104", "\u010C", "\u0118", "\u0116", "\u012E", "\u0160", "\u0172", "\u016A", "(", ")", "_", "\u017D", "BACKSPACEICON"]
		keyList[1][3][1] = "|"
		keyList.append([
			["", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "", "=", "BACKSPACEICON"],
			["FIRSTICON", "!", "@", "#", "$", "%", "^", "&", "*", "", "", "", "+", ""],
			["LASTICON", "", "", "\u20AC", "", "", "", "", "", "", "", "", self.green, self.green],
			["CAPSLOCKICON", "", "", "", "", "", "", "", "", "", "", "", "CAPSLOCKICON", "CAPSLOCKICON"],
			self.footer
		])
		return keyList

	def norwegian(self, base):
		keyList = deepcopy(base)
		keyList[0][0][0] = "|"
		keyList[0][0][12] = "\\"
		keyList[0][2][10] = "\u00F8"
		keyList[0][2][11] = "\u00E6"
		keyList[1][0][0] = "\u00A7"
		keyList[1][2][10] = "\u00D8"
		keyList[1][2][11] = "\u00C6"
		keyList[2][0][11] = ""
		keyList[2][0][12] = "\u00B4"
		keyList[2][3][1] = ""
		return keyList

	def persian(self, base):
		keyList = deepcopy(base)
		keyList.append([
			["\u00F7", "\u06F1", "\u06F2", "\u06F3", "\u06F4", "\u06F5", "\u06F6", "\u06F7", "\u06F8", "\u06F9", "\u06F0", "-", "=", "BACKSPACEICON"],
			["FIRSTICON", "\u0636", "\u0635", "\u062B", "\u0642", "\u0641", "\u063A", "\u0639", "\u0647", "\u062E", "\u062D", "\u062C", "\u0686", "\u067E"],
			["LASTICON", "\u0634", "\u0633", "\u06CC", "\u0628", "\u0644", "\u0627", "\u062A", "\u0646", "\u0645", "\u06A9", "\u06AF", self.green, self.green],
			["CAPSLOCKICON", "\u0649", "\u0638", "\u0637", "\u0632", "\u0631", "\u0630", "\u062F", "\u0626", "\u0648", ".", "/", "CAPSLOCKICON", "CAPSLOCKICON"],
			self.footer
		])
		keyList.append([
			["\u00D7", "!", "@", "#", "$", "%", "^", "&", "*", ")", "(", "_", "+", "BACKSPACEICON"],
			["FIRSTICON", "\u064B", "\u064C", "\u064D", "\u0631", "\u060C", "\u061B", ",", "]", "[", "\\", "}", "{", "|"],
			["LASTICON", "\u064E", "\u064F", "\u0650", "\u0651", "\u06C0", "\u0622", "\u0640", "\u00AB", "\u00BB", ":", "\"", self.green, self.green],
			["CAPSLOCKICON", "|", "\u0629", "\u064A", "\u0698", "\u0624", "\u0625", "\u0623", "\u0621", "<", ">", "\u061F", "CAPSLOCKICON", "CAPSLOCKICON"],
			self.footer
		])
		return keyList

	def polish(self, base):
		keyList = deepcopy(base)
		keyList[0][0][0] = "\u02DB"
		keyList[0][0][11] = "+"
		keyList[0][1][11] = "\u017C"
		keyList[0][1][12] = "\u015B"
		keyList[0][1][13] = "\u00F3"
		keyList[0][2][10] = "\u0142"
		keyList[0][2][11] = "\u0105"
		keyList[1][0][0] = "\u00B7"
		keyList[1][0][3] = "#"
		keyList[1][0][4] = "\u00A4"
		keyList[1][0][12] = "*"
		keyList[1][1][11] = "\u0144"
		keyList[1][1][12] = "\u0107"
		keyList[1][1][13] = "\u017A"
		keyList[1][2][10] = "\u0141"
		keyList[1][2][11] = "\u0119"
		del keyList[2]
		keyList.append([
			["", "~", "\u02C7", "^", "\u02D8", "\u00B0", "\u02DB", "`", "\u00B7", "\u00B4", "\u02DD", "\u00A8", "\u00B8", "BACKSPACEICON"],
			["FIRSTICON", "\\", "\u00A6", "", "\u017B", "\u015A", "\u00D3", "\u20AC", "\u0143", "\u0106", "\u0179", "\u00F7", "\u00D7", ""],
			["LASTICON", "", "\u0111", "\u0110", "", "", "", "", "\u0104", "\u0118", "$", "\u00DF", self.green, self.green],
			["CAPSLOCKICON", "", "", "", "", "@", "{", "}", "\u00A7", "<", ">", "", "CAPSLOCKICON", "CAPSLOCKICON"],
			self.footer
		])
		return keyList

	def polishProgrammers(self, base):
		keyList = deepcopy(base)
		keyList[0][3][1] = "\\"
		keyList[1][3][1] = "|"
		keyList.append([
			["", "", "", "", "", "", "", "", "", "", "", "", "", "BACKSPACEICON"],
			["FIRSTICON", "", "", "\u0119", "\u0118", "", "", "\u20AC", "", "\u00F3", "\u00D3", "", "", ""],
			["LASTICON", "\u0105", "\u0104", "\u015B", "\u015A", "", "", "", "", "\u0142", "\u0141", "", self.green, self.green],
			["CAPSLOCKICON", "\u017C", "\u017B", "\u017A", "\u0179", "\u0107", "\u0106", "\u0144", "\u0143", "", "", "", "CAPSLOCKICON", "CAPSLOCKICON"],
			self.footer
		])
		return keyList

	def slovak(self, base):
		keyList = deepcopy(base)
		keyList[0][0] = [";", "+", "\u013E", "\u0161", "\u010D", "\u0165", "\u017E", "\u00FD", "\u00E1", "\u00ED", "\u00E9", "=", "\u00B4", "BACKSPACEICON"]
		keyList[0][1][11] = "\u00FA"
		keyList[0][1][12] = "\u00E4"
		keyList[0][1][13] = "\u0148"
		keyList[0][2][10] = "\u00F4"
		keyList[0][2][11] = "\u00A7"
		keyList[0][3][1] = "&"
		keyList[1][0] = ["\u00B0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "%", "\u02C7", "BACKSPACEICON"]
		keyList[1][1][11] = "/"
		keyList[1][1][12] = "("
		keyList[1][1][13] = ")"
		keyList[1][2][10] = "\""
		keyList[1][2][11] = "!"
		keyList[1][3][1] = "*"
		keyList[1][3][9] = "?"
		del keyList[2]
		keyList.append([
			["", "~", "\u02C7", "^", "\u02D8", "\u00B0", "\u02DB", "`", "\u02D9", "\u00B4", "\u02DD", "\u00A8", "\u00B8", "BACKSPACEICON"],
			["FIRSTICON", "\\", "|", "\u20AC", "", "", "", "", "", "", "'", "\u00F7", "\u00D7", "\u00A4"],
			["LASTICON", "", "\u0111", "\u0110", "[", "]", "", "", "\u0142", "\u0141", "$", "\u00DF", self.green, self.green],
			["CAPSLOCKICON", "<", ">", "#", "&", "@", "{", "}", "", "<", ">", "*", "CAPSLOCKICON", "CAPSLOCKICON"],
			self.footer
		])
		return keyList

	def ukranian(self, base):
		keyList = deepcopy(base)
		keyList[0][1][12] = "\u0457"
		keyList[0][1][13] = "\\"
		keyList[0][2][11] = "\u0454"
		keyList[0][2][2] = "\u0456"
		keyList[0][3][1] = "\u0491"
		keyList[1][1][12] = "\u0407"
		keyList[1][1][13] = "/"
		keyList[1][2][11] = "\u0404"
		keyList[1][2][2] = "\u0406"
		keyList[1][3][1] = "\u0490"
		return keyList

	def ukranianEnhanced(self, base):
		keyList = self.ukranian(base)
		keyList[0][0][0] = "\u0027"
		keyList[1][0][0] = "\u20B4"
		return keyList

	def unitedKingdom(self, base):
		keyList = deepcopy(base)
		keyList[0][1][13] = "#"
		keyList[0][3] = ["CAPSLOCKICON", "\\", "z", "x", "c", "v", "b", "n", "m", ",", ".", "/", "CAPSLOCKICON", "CAPSLOCKICON"]
		keyList[0][4] = copy(self.footer)
		keyList[0][4][10] = "\u00A6"
		keyList[1][0][0] = "\u00AC"
		keyList[1][0][2] = "\""
		keyList[1][0][3] = "\u00A3"
		keyList[1][1][13] = "~"
		keyList[1][2][11] = "@"
		keyList[1][3] = ["CAPSLOCKICON", "|", "Z", "X", "C", "V", "B", "N", "M", "<", ">", "?", "CAPSLOCKICON", "CAPSLOCKICON"]
		keyList[1][4] = copy(self.footer)
		keyList[1][4][10] = "\u20AC"
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
		self["locale"].setText("%s: %s  (%s - %s)" % (_("Locale"), self.lang, self.language, self.location))

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
					res.append(MultiContentEntryPixmapAlphaBlend(pos=(x, 0), size=(w, self.height), png=self.bg_l))
					x += w
					w = self.bg_m.size().width() + (self.width * (width - 1))
					res.append(MultiContentEntryPixmapAlphaBlend(pos=(x, 0), size=(w, self.height), png=self.bg_m, flags=BT_SCALE))
					x += w
					w = self.bg_r.size().width()
					res.append(MultiContentEntryPixmapAlphaBlend(pos=(x, 0), size=(w, self.height), png=self.bg_r))
					x += w
				highlight = self.keyHighlights.get(key.upper(), (None, None, None))  # Check if the cell needs to be highlighted.
				if highlight[0] is None or highlight[1] is None or highlight[2] is None:  # If available display the cell highlight.
					xHighlight += self.width * width
				else:
					w = highlight[0].size().width()
					res.append(MultiContentEntryPixmapAlphaBlend(pos=(xHighlight, 0), size=(w, self.height), png=highlight[0]))
					xHighlight += w
					w = highlight[1].size().width() + (self.width * (width - 1))
					res.append(MultiContentEntryPixmapAlphaBlend(pos=(xHighlight, 0), size=(w, self.height), png=highlight[1], flags=BT_SCALE))
					xHighlight += w
					w = highlight[2].size().width()
					res.append(MultiContentEntryPixmapAlphaBlend(pos=(xHighlight, 0), size=(w, self.height), png=highlight[2]))
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
					res.append(MultiContentEntryPixmapAlphaBlend(pos=(left, top), size=(wImage, hImage), png=image))
					# print("[VirtualKeyBoard] DEBUG: Left=%d, Top=%d, Width=%d, Height=%d, Image Width=%d, Image Height=%d" % (left, top, w, h, wImage, hImage))
				else:  # Display the cell text.
					skey = key
					if len(key) > 1:  # NOTE: UTF8 / Unicode glyphs only count as one character here.
						text.append(MultiContentEntryText(pos=(xData, self.padding[1]), size=(w, h), font=1, flags=alignH | alignV, text=skey, color=self.shiftColors[self.shiftLevel]))
					else:
						text.append(MultiContentEntryText(pos=(xData, self.padding[1]), size=(w, h), font=0, flags=alignH | alignV, text=skey, color=self.shiftColors[self.shiftLevel]))
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
		self.list[self.selectedKey // self.keyboardWidth].append(MultiContentEntryPixmapAlphaBlend(pos=(x, 0), size=(w, self.height), png=self.sel_l))
		x += w
		w = self.sel_m.size().width() + (self.width * (width - 1))
		self.list[self.selectedKey // self.keyboardWidth].append(MultiContentEntryPixmapAlphaBlend(pos=(x, 0), size=(w, self.height), png=self.sel_m, flags=BT_SCALE))
		x += w
		w = self.sel_r.size().width()
		self.list[self.selectedKey // self.keyboardWidth].append(MultiContentEntryPixmapAlphaBlend(pos=(x, 0), size=(w, self.height), png=self.sel_r))
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
		text = self.keyList[self.shiftLevel][self.selectedKey // self.keyboardWidth][self.selectedKey % self.keyboardWidth]
		cmd = self.cmds.get(text.upper(), None)
		if cmd is None:
			self["text"].char(text)
		else:
			exec(cmd)
		if text not in ("SHIFT", "SHIFTICON") and self.shiftHold != -1:
			self.shiftRestore()

	def cancel(self):
		self.close(None)

	def save(self):
		self.close(self["text"].getText())

	def localeMenu(self):
		languages = []
		for locale, data in self.locales.items():
			languages.append(("%s  -  %s  (%s)" % (data[0], data[1], locale), locale))
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
		self["text"].deleteAllChars()
		self["text"].update()

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
		if self.selectAsciiKey(chr(getPrevAsciiCode())):
			self.processSelect()

	def selectAsciiKey(self, char):
		if char == " ":
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

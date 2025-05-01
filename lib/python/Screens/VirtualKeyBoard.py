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
from Screens.Screen import Screen
from Tools.Directories import SCOPE_GUISKIN, resolveFilename
from Tools.LoadPixmap import LoadPixmap
from Tools.NumericalTextInput import NumericalTextInput


class VirtualKeyboardList(MenuList):
	def __init__(self, list, enableWrapAround=False):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		font = fonts.get("VirtualKeyboard", fonts.get("VirtualKeyBoard", ("Regular", 28, 45)))
		self.l.setFont(0, gFont(font[0], font[1]))
		self.l.setFont(1, gFont(font[0], int(font[1] * 5 // 9)))  # Smaller font is 56% the height of bigger font.
		self.l.setItemHeight(font[2])


# For more information about using VirtualKeyboard see /doc/VIRTUALKEYBOARD.
#
class VirtualKeyboard(Screen):
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
	TAB_GLYPH = "\u21E5"

	def __init__(self, session, title=_("Virtual Keyboard Text:"), text="", maxSize=False, visibleWidth=False, type=Input.TEXT, currPos=None, allMarked=False, style=VKB_ENTER_ICON, windowTitle=None):
		Screen.__init__(self, session, enableHelp=True)
		self.skinName = ["VirtualKeyboard", "VirtualKeyBoard"]
		self.setTitle(_("Virtual Keyboard") if windowTitle is None else windowTitle)
		prompt = title  # Title should only be used for screen titles!
		greenLabel, self.green = {
			self.VKB_DONE_ICON: ("Done", "ENTERICON"),
			self.VKB_ENTER_ICON: ("Enter", "ENTERICON"),
			self.VKB_OK_ICON: ("OK", "ENTERICON"),
			self.VKB_SAVE_ICON: ("Save", "ENTERICON"),
			self.VKB_SEARCH_ICON: ("Search", "ENTERICON"),
			self.VKB_DONE_TEXT: ("Done", _("Done")),
			self.VKB_ENTER_TEXT: ("Done", _("Enter")),
			self.VKB_OK_TEXT: ("OK", _("OK")),
			self.VKB_SAVE_TEXT: ("Save", _("Save")),
			self.VKB_SEARCH_TEXT: ("Search", _("Search"))
		}.get(style, ("Enter", "ENTERICON"))
		# self.iconBackground = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_bg.png"))  # Legacy support only!
		self.iconBackgroundLeft = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_bg_l.png"))
		self.iconBackgroundMiddle = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_bg_m.png"))
		self.iconBackgroundRight = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_bg_r.png"))
		self.iconSelectedLeft = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_sel_l.png"))
		self.iconSelectedMiddle = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_sel_m.png"))
		self.iconSelectedRight = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_sel_r.png"))
		iconRedLeft = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_red_l.png"))
		iconRedMiddle = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_red_m.png"))
		iconRedRight = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_red_r.png"))
		iconGreenLeft = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_green_l.png"))
		iconGreenMiddle = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_green_m.png"))
		iconGreenRight = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_green_r.png"))
		iconYellowLeft = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_yellow_l.png"))
		iconYellowMiddle = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_yellow_m.png"))
		iconYellowRight = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_yellow_r.png"))
		iconBlueLeft = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_blue_l.png"))
		iconBlueMiddle = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_blue_m.png"))
		iconBlueRight = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_blue_r.png"))
		iconBackspace = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_backspace.png"))
		iconClear = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_clear.png"))
		iconDelete = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_delete.png"))
		iconEnter = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_enter.png"))
		iconExit = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_exit.png"))
		iconFirst = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_first.png"))
		iconLast = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_last.png"))
		iconLeft = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_left.png"))
		iconLocale = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_locale.png"))
		iconRight = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_right.png"))
		iconShift = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_shift.png"))
		iconShift0 = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_shift0.png"))
		iconShift1 = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_shift1.png"))
		iconShift2 = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_shift2.png"))
		iconShift3 = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_shift3.png"))
		iconSpace = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_space.png"))
		iconSpaceAlt = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_space_alt.png"))
		iconTab = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "buttons/vkey_tab.png"))
		self.iconHighlights = {  # This is a table of cell highlight components (left, middle and right)
			"EXIT": (iconRedLeft, iconRedMiddle, iconRedRight),
			"EXITICON": (iconRedLeft, iconRedMiddle, iconRedRight),
			"DONE": (iconGreenLeft, iconGreenMiddle, iconGreenRight),
			"ENTER": (iconGreenLeft, iconGreenMiddle, iconGreenRight),
			"ENTERICON": (iconGreenLeft, iconGreenMiddle, iconGreenRight),
			"OK": (iconGreenLeft, iconGreenMiddle, iconGreenRight),
			"SAVE": (iconGreenLeft, iconGreenMiddle, iconGreenRight),
			# "LOC": (iconYellowLeft, iconYellowMiddle, iconYellowRight),
			# "LOCALE": (iconYellowLeft, iconYellowMiddle, iconYellowRight),
			# "LOCALEICON": (iconYellowLeft, iconYellowMiddle, iconYellowRight),
			"SHIFT": (iconYellowLeft, iconYellowMiddle, iconYellowRight),
			"SHIFTICON": (iconYellowLeft, iconYellowMiddle, iconYellowRight),
			"CAPS": (iconBlueLeft, iconBlueMiddle, iconBlueRight),
			"LOCK": (iconBlueLeft, iconBlueMiddle, iconBlueRight),
			"CAPSLOCK": (iconBlueLeft, iconBlueMiddle, iconBlueRight),
			"CAPSLOCKICON": (iconBlueLeft, iconBlueMiddle, iconBlueRight)
		}
		self.shiftMsgs = [
			_("Lower case"),
			_("Upper case"),
			_("Special 1"),
			_("Special 2")
		]
		self.keyIcons = [{
			# "ALLICON": iconAll,
			"BACKSPACEICON": iconBackspace,
			"CAPSLOCKICON": iconShift0,
			"CLEARICON": iconClear,
			"DELETEICON": iconDelete,
			"ENTERICON": iconEnter,
			"EXITICON": iconExit,
			"FIRSTICON": iconFirst,
			"LASTICON": iconLast,
			"LOCALEICON": iconLocale,
			"LEFTICON": iconLeft,
			"RIGHTICON": iconRight,
			"SHIFTICON": iconShift,
			"SPACEICON": iconSpace,
			"SPACEICONALT": iconSpaceAlt,
			"TABICON": iconTab
		}, {
			# "ALLICON": iconAll,
			"BACKSPACEICON": iconBackspace,
			"CAPSLOCKICON": iconShift1,
			"CLEARICON": iconClear,
			"DELETEICON": iconDelete,
			"ENTERICON": iconEnter,
			"EXITICON": iconExit,
			"FIRSTICON": iconFirst,
			"LASTICON": iconLast,
			"LEFTICON": iconLeft,
			"LOCALEICON": iconLocale,
			"RIGHTICON": iconRight,
			"SHIFTICON": iconShift,
			"SPACEICON": iconSpace,
			"SPACEICONALT": iconSpaceAlt,
			"TABICON": iconTab
		}, {
			# "ALLICON": iconAll,
			"BACKSPACEICON": iconBackspace,
			"CAPSLOCKICON": iconShift2,
			"CLEARICON": iconClear,
			"DELETEICON": iconDelete,
			"ENTERICON": iconEnter,
			"EXITICON": iconExit,
			"FIRSTICON": iconFirst,
			"LASTICON": iconLast,
			"LEFTICON": iconLeft,
			"LOCALEICON": iconLocale,
			"RIGHTICON": iconRight,
			"SHIFTICON": iconShift,
			"SPACEICON": iconSpace,
			"SPACEICONALT": iconSpaceAlt,
			"TABICON": iconTab
		}, {
			# "ALLICON": iconAll,
			"BACKSPACEICON": iconBackspace,
			"CAPSLOCKICON": iconShift3,
			"CLEARICON": iconClear,
			"DELETEICON": iconDelete,
			"ENTERICON": iconEnter,
			"EXITICON": iconExit,
			"FIRSTICON": iconFirst,
			"LASTICON": iconLast,
			"LEFTICON": iconLeft,
			"LOCALEICON": iconLocale,
			"RIGHTICON": iconRight,
			"SHIFTICON": iconShift,
			"SPACEICON": iconSpace,
			"SPACEICONALT": iconSpaceAlt,
			"TABICON": iconTab
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
			"SPACEICONALT": "self['text'].char(' ')",
			"TABICON": "self['text'].char(self.TAB_GLYPH)"
		}
		self.footer = ["FIRSTICON", "LEFTICON", "RIGHTICON", "LASTICON", self.SPACE, self.SPACE, self.SPACE, self.SPACE, self.SPACE, self.SPACE, "EXITICON", "LOCALEICON", "CLEARICON", "DELETEICON"]
		self.bulgarian = [
			[
				["`", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", ".", "BACKSPACEICON"],
				["TABICON", ",", "\u0443", "\u0435", "\u0438", "\u0448", "\u0449", "\u043A", "\u0441", "\u0434", "\u0437", "\u0446", ";", "("],
				["CAPSLOCKICON", "\u044C", "\u044F", "\u0430", "\u043E", "\u0436", "\u0433", "\u0442", "\u043D", "\u0432", "\u043C", "\u0447", self.green, self.green],
				["SHIFTICON", "\\", "\u044E", "\u0439", "\u044A", "\u044D", "\u0444", "\u0445", "\u043F", "\u0440", "\u043B", "\u0431", "SHIFTICON", "SHIFTICON"],
				self.footer
			], [
				["~", "!", "?", "+", "\"", "%", "=", ":", "/", "_", "\u2116", "\u0406", "V", "BACKSPACEICON"],
				["TABICON", "\u044B", "\u0423", "\u0415", "\u0418", "\u0428", "\u0429", "\u041A", "\u0421", "\u0414", "\u0417", "\u0426", "\u00A7", ")"],
				["CAPSLOCKICON", "\u042C", "\u042F", "\u0410", "\u041E", "\u0416", "\u0413", "\u0422", "\u041D", "\u0412", "\u041C", "\u0427", self.green, self.green],
				["SHIFTICON", "|", "\u042E", "\u0419", "\u042A", "\u042D", "\u0424", "\u0425", "\u041F", "\u0420", "\u041B", "\u0411", "SHIFTICON", "SHIFTICON"],
				self.footer
			]
		]
		self.czech = [
			[
				[";", "+", "\u011B", "\u0161", "\u010D", "\u0159", "\u017E", "\u00FD", "\u00E1", "\u00ED", "\u00E9", "=", "", "BACKSPACEICON"],
				["TABICON", "q", "w", "e", "r", "t", "z", "u", "i", "o", "p", "\u00FA", "(", ")"],
				["CAPSLOCKICON", "a", "s", "d", "f", "g", "h", "j", "k", "l", "\u016F", "\u00A7", self.green, self.green],
				["SHIFTICON", "\\", "y", "x", "c", "v", "b", "n", "m", ",", ".", "-", "SHIFTICON", "SHIFTICON"],
				self.footer
			], [
				[".", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "%", "'", "BACKSPACEICON"],
				["TABICON", "Q", "W", "E", "R", "T", "Z", "U", "I", "O", "P", "/", "(", ")"],
				["CAPSLOCKICON", "A", "S", "D", "F", "G", "H", "J", "K", "L", "\"", "!", self.green, self.green],
				["SHIFTICON", "|", "Y", "X", "C", "V", "B", "N", "M", "?", ":", "_", "SHIFTICON", "SHIFTICON"],
				self.footer
			], [
				["\u00B0", "~", "\u011A", "\u0160", "\u010C", "\u0158", "\u017D", "\u00DD", "\u00C1", "\u00CD", "\u00C9", "`", "'", "BACKSPACEICON"],
				["TABICON", "\\", "|", "\u20AC", "\u0165", "\u0164", "\u0148", "\u0147", "\u00F3", "\u00D3", "\u00DA", "\u00F7", "\u00D7", "\u00A4"],
				["CAPSLOCKICON", "", "\u0111", "\u00D0", "[", "]", "\u010F", "\u010E", "\u0142", "\u0141", "\u016E", "\u00DF", self.green, self.green],
				["SHIFTICON", "", "", "#", "&", "@", "{", "}", "$", "<", ">", "*", "SHIFTICON", "SHIFTICON"],
				self.footer
			]
		]
		self.english = [
			[
				["`", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=", "BACKSPACEICON"],
				["TABICON", "q", "w", "e", "r", "t", "y", "u", "i", "o", "p", "[", "]", "\\"],
				["CAPSLOCKICON", "a", "s", "d", "f", "g", "h", "j", "k", "l", ";", "'", self.green, self.green],
				["SHIFTICON", "SHIFTICON", "z", "x", "c", "v", "b", "n", "m", ",", ".", "/", "SHIFTICON", "SHIFTICON"],
				self.footer
			], [
				["~", "!", "@", "#", "$", "%", "^", "&", "*", "(", ")", "_", "+", "BACKSPACEICON"],
				["TABICON", "Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "{", "}", "|"],
				["CAPSLOCKICON", "A", "S", "D", "F", "G", "H", "J", "K", "L", ":", "\"", self.green, self.green],
				["SHIFTICON", "SHIFTICON", "Z", "X", "C", "V", "B", "N", "M", "<", ">", "?", "SHIFTICON", "SHIFTICON"],
				self.footer
			]
		]
		self.french = [
			[
				["\u00B2", "&", "\u00E9", "\"", "'", "(", "-", "\u00E8", "_", "\u00E7", "\u00E0", ")", "=", "BACKSPACEICON"],
				["TABICON", "a", "z", "e", "r", "t", "y", "u", "i", "o", "p", "^", "$", "*"],
				["CAPSLOCKICON", "q", "s", "d", "f", "g", "h", "j", "k", "l", "m", "\u00F9", self.green, self.green],
				["SHIFTICON", "<", "w", "x", "c", "v", "b", "n", ",", ";", ":", "!", "SHIFTICON", "SHIFTICON"],
				self.footer
			], [
				["", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "\u00B0", "+", "BACKSPACEICON"],
				["TABICON", "A", "Z", "E", "R", "T", "Y", "U", "I", "O", "P", "\u00A8", "\u00A3", "\u00B5"],
				["CAPSLOCKICON", "Q", "S", "D", "F", "G", "H", "J", "K", "L", "M", "%", self.green, self.green],
				["SHIFTICON", ">", "W", "X", "C", "V", "B", "N", "?", ".", "/", "\u00A7", "SHIFTICON", "SHIFTICON"],
				self.footer
			], [
				["", "", "~", "#", "{", "[", "|", "`", "\\", "^", "@", "]", "}", "BACKSPACEICON"],
				["TABICON", "", "", "\u20AC", "", "", "", "", "", "", "", "", "\u00A4", ""],
				["CAPSLOCKICON", "", "", "", "", "", "", "", "", "", "", "", self.green, self.green],
				["SHIFTICON", "", "", "", "", "", "", "", "", "", "", "", "SHIFTICON", "SHIFTICON"],
				self.footer
			], [
				["", "", "\u00E2", "\u00EA", "\u00EE", "\u00F4", "\u00FB", "\u00E4", "\u00EB", "\u00EF", "\u00F6", "\u00FC", "", "BACKSPACEICON"],
				["TABICON", "", "\u00E0", "\u00E8", "\u00EC", "\u00F2", "\u00F9", "\u00E1", "\u00E9", "\u00ED", "\u00F3", "\u00FA", "", ""],
				["CAPSLOCKICON", "", "\u00C2", "\u00CA", "\u00CE", "\u00D4", "\u00DB", "\u00C4", "\u00CB", "\u00CF", "\u00D6", "\u00DC", self.green, self.green],
				["SHIFTICON", "", "\u00C0", "\u00C8", "\u00CC", "\u00D2", "\u00D9", "\u00C1", "\u00C9", "\u00CD", "\u00D3", "\u00DA", "SHIFTICON", "SHIFTICON"],
				self.footer
			]
		]
		self.german = [
			[
				["^", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "\u00DF", "'", "BACKSPACEICON"],
				["TABICON", "q", "w", "e", "r", "t", "z", "u", "i", "o", "p", "\u00FC", "+", "#"],
				["CAPSLOCKICON", "a", "s", "d", "f", "g", "h", "j", "k", "l", "\u00F6", "\u00E4", self.green, self.green],
				["SHIFTICON", "<", "y", "x", "c", "v", "b", "n", "m", ",", ".", "-", "SHIFTICON", "SHIFTICON"],
				self.footer
			], [
				["\u00B0", "!", "\"", "\u00A7", "$", "%", "&", "/", "(", ")", "=", "?", "`", "BACKSPACEICON"],
				["TABICON", "Q", "W", "E", "R", "T", "Z", "U", "I", "O", "P", "\u00DC", "*", "'"],
				["CAPSLOCKICON", "A", "S", "D", "F", "G", "H", "J", "K", "L", "\u00D6", "\u00C4", self.green, self.green],
				["SHIFTICON", ">", "Y", "X", "C", "V", "B", "N", "M", ";", ":", "_", "SHIFTICON", "SHIFTICON"],
				self.footer
			], [
				["", "", "\u00B2", "\u00B3", "", "", "", "{", "[", "]", "}", "\\", "\u1E9E", "BACKSPACEICON"],
				["TABICON", "@", "", "\u20AC", "", "", "", "", "", "", "", "", "~", ""],
				["CAPSLOCKICON", "", "", "", "", "", "", "", "", "", "", "", self.green, self.green],
				["SHIFTICON", "|", "", "", "", "", "", "", "\u00B5", "", "", "", "SHIFTICON", "SHIFTICON"],
				self.footer
			]
		]
		self.greek = [
			[
				["`", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=", "BACKSPACEICON"],
				["TABICON", ";", "\u03C2", "\u03B5", "\u03C1", "\u03C4", "\u03C5", "\u03B8", "\u03B9", "\u03BF", "\u03C0", "[", "]", "\\"],
				["CAPSLOCKICON", "\u03B1", "\u03C3", "\u03B4", "\u03C6", "\u03B3", "\u03B7", "\u03BE", "\u03BA", "\u03BB", "\u0384", "'", self.green, self.green],
				["SHIFTICON", "<", "\u03B6", "\u03C7", "\u03C8", "\u03C9", "\u03B2", "\u03BD", "\u03BC", ",", ".", "/", "SHIFTICON", "SHIFTICON"],
				self.footer
			], [
				["~", "!", "@", "#", "$", "%", "^", "&", "*", "(", ")", "_", "+", "BACKSPACEICON"],
				["TABICON", ":", "\u0385", "\u0395", "\u03A1", "\u03A4", "\u03A5", "\u0398", "\u0399", "\u039F", "\u03A0", "{", "}", "|"],
				["CAPSLOCKICON", "\u0391", "\u03A3", "\u0394", "\u03A6", "\u0393", "\u0397", "\u039E", "\u039A", "\u039B", "\u00A8", "\"", self.green, self.green],
				["SHIFTICON", ">", "\u0396", "\u03A7", "\u03A8", "\u03A9", "\u0392", "\u039D", "\u039C", "<", ">", "?", "SHIFTICON", "SHIFTICON"],
				self.footer
			], [
				["", "", "\u00B2", "\u00B3", "\u00A3", "\u00A7", "\u00B6", "", "\u00A4", "\u00A6", "\u00B0", "\u00B1", "\u00BD", "BACKSPACEICON"],
				["TABICON", "", "\u03AC", "\u03AD", "\u03AE", "\u03AF", "\u03CC", "\u03CD", "\u03CE", "\u03CA", "\u03CB", "\u00AB", "\u00BB", "\u00AC"],
				["CAPSLOCKICON", "", "\u0386", "\u0388", "\u0389", "\u038A", "\u038C", "\u038E", "\u038F", "\u03AA", "\u03AB", "\u0385", self.green, self.green],
				["SHIFTICON", "SHIFTICON", "", "", "", "\u00A9", "\u00AE", "\u20AC", "\u00A5", "\u0390", "\u03B0", "\u0387", "SHIFTICON", "SHIFTICON"],
				self.footer
			]
		]
		self.latvian = [
			[
				["", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "f", "BACKSPACEICON"],
				["TABICON", "\u016B", "g", "j", "r", "m", "v", "n", "z", "\u0113", "\u010D", "\u017E", "h", "\u0137"],
				["CAPSLOCKICON", "\u0161", "u", "s", "i", "l", "d", "a", "t", "e", "c", "\u00B4", self.green, self.green],
				["SHIFTICON", "\u0123", "\u0146", "b", "\u012B", "k", "p", "o", "\u0101", ",", ".", "\u013C", "SHIFTICON", "SHIFTICON"],
				self.footer
			], [
				["?", "!", "\u00AB", "\u00BB", "$", "%", "/", "&", "\u00D7", "(", ")", "_", "F", "BACKSPACEICON"],
				["TABICON", "\u016A", "G", "J", "R", "M", "V", "N", "Z", "\u0112", "\u010C", "\u017D", "H", "\u0136"],
				["CAPSLOCKICON", "\u0160", "U", "S", "I", "L", "D", "A", "T", "E", "C", "\u00B0", self.green, self.green],
				["SHIFTICON", "\u0122", "\u0145", "B", "\u012A", "K", "P", "O", "\u0100", ";", ":", "\u013B", "SHIFTICON", "SHIFTICON"],
				self.footer
			], [
				["", "\u00AB", "", "", "\u20AC", "\"", "'", "", ":", "", "", "\u2013", "=", "BACKSPACEICON"],
				["TABICON", "q", "\u0123", "", "\u0157", "w", "y", "", "", "", "", "[", "]", ""],
				["CAPSLOCKICON", "", "", "", "", "", "", "", "", "\u20AC", "", "\u00B4", self.green, self.green],
				["SHIFTICON", "\\", "", "x", "", "\u0137", "", "\u00F5", "", "<", ">", "", "SHIFTICON", "SHIFTICON"],
				self.footer
			], [
				["", "", "@", "#", "$", "~", "^", "\u00B1", "", "", "", "\u2014", ";", "BACKSPACEICON"],
				["TABICON", "Q", "\u0122", "", "\u0156", "W", "Y", "", "", "", "", "{", "}", ""],
				["CAPSLOCKICON", "", "", "", "", "", "", "", "", "", "", "\u00A8", self.green, self.green],
				["SHIFTICON", "|", "", "X", "", "\u0136", "", "\u00D5", "", "", "", "", "SHIFTICON", "SHIFTICON"],
				self.footer
			]
		]
		self.russian = [
			[
				["\u0451", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "-", "=", "BACKSPACEICON"],
				["TABICON", "\u0439", "\u0446", "\u0443", "\u043A", "\u0435", "\u043D", "\u0433", "\u0448", "\u0449", "\u0437", "\u0445", "\u044A", "\\"],
				["CAPSLOCKICON", "\u0444", "\u044B", "\u0432", "\u0430", "\u043F", "\u0440", "\u043E", "\u043B", "\u0434", "\u0436", "\u044D", self.green, self.green],
				["SHIFTICON", "\\", "\u044F", "\u0447", "\u0441", "\u043C", "\u0438", "\u0442", "\u044C", "\u0431", "\u044E", ".", "SHIFTICON", "SHIFTICON"],
				self.footer
			], [
				["\u0401", "!", "\"", "\u2116", ";", "%", ":", "?", "*", "(", ")", "_", "+", "BACKSPACEICON"],
				["TABICON", "\u0419", "\u0426", "\u0423", "\u041A", "\u0415", "\u041D", "\u0413", "\u0428", "\u0429", "\u0417", "\u0425", "\u042A", "/"],
				["CAPSLOCKICON", "\u0424", "\u042B", "\u0412", "\u0410", "\u041F", "\u0420", "\u041E", "\u041B", "\u0414", "\u0416", "\u042D", self.green, self.green],
				["SHIFTICON", "/", "\u042F", "\u0427", "\u0421", "\u041C", "\u0418", "\u0422", "\u042C", "\u0411", "\u042E", ",", "SHIFTICON", "SHIFTICON"],
				self.footer
			], [
				["", "", "", "", "", "", "", "", "", "", "", "", "", "BACKSPACEICON"],
				["TABICON", "", "\u00A7", "@", "#", "&", "$", "\u20BD", "\u20AC", "", "", "", "", ""],
				["CAPSLOCKICON", "", "<", ">", "[", "]", "{", "}", "", "", "", "", self.green, self.green],
				["SHIFTICON", "", "", "", "", "", "", "", "", "", "", "", "SHIFTICON", "SHIFTICON"],
				self.footer
			]
		]
		self.scandinavian = [
			[
				["\u00A7", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "+", "\u00B4", "BACKSPACEICON"],
				["TABICON", "q", "w", "e", "r", "t", "y", "u", "i", "o", "p", "\u00E5", "\u00A8", "'"],
				["CAPSLOCKICON", "a", "s", "d", "f", "g", "h", "j", "k", "l", "\u00F6", "\u00E4", self.green, self.green],
				["SHIFTICON", "<", "z", "x", "c", "v", "b", "n", "m", ",", ".", "-", "SHIFTICON", "SHIFTICON"],
				self.footer
			], [
				["\u00BD", "!", "\"", "#", "\u00A4", "%", "&", "/", "(", ")", "=", "?", "`", "BACKSPACEICON"],
				["TABICON", "Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "\u00C5", "^", "*"],
				["CAPSLOCKICON", "A", "S", "D", "F", "G", "H", "J", "K", "L", "\u00D6", "\u00C4", self.green, self.green],
				["SHIFTICON", ">", "Z", "X", "C", "V", "B", "N", "M", ";", ":", "_", "SHIFTICON", "SHIFTICON"],
				self.footer
			], [
				["", "", "@", "\u00A3", "$", "\u20AC", "", "{", "[", "]", "}", "\\", "", "BACKSPACEICON"],
				["TABICON", "", "", "\u20AC", "", "", "", "", "", "", "", "", "~", ""],
				["CAPSLOCKICON", "", "", "", "", "", "", "", "", "", "", "", self.green, self.green],
				["SHIFTICON", "|", "", "", "", "", "", "", "\u00B5", "", "", "", "SHIFTICON", "SHIFTICON"],
				self.footer
			], [
				["", "\u00E2", "\u00EA", "\u00EE", "\u00F4", "\u00FB", "\u00E4", "\u00EB", "\u00EF", "\u00F6", "\u00FC", "\u00E3", "", "BACKSPACEICON"],
				["TABICON", "\u00E0", "\u00E8", "\u00EC", "\u00F2", "\u00F9", "\u00E1", "\u00E9", "\u00ED", "\u00F3", "\u00FA", "\u00F5", "", ""],
				["CAPSLOCKICON", "\u00C2", "\u00CA", "\u00CE", "\u00D4", "\u00DB", "\u00C4", "\u00CB", "\u00CF", "\u00D6", "\u00DC", "\u00C3", self.green, self.green],
				["SHIFTICON", "\u00C0", "\u00C8", "\u00CC", "\u00D2", "\u00D9", "\u00C1", "\u00C9", "\u00CD", "\u00D3", "\u00DA", "\u00D5", "SHIFTICON", "SHIFTICON"],
				self.footer
			]
		]
		self.spanish = [
			[
				["\u00BA", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "'", "\u00A1", "BACKSPACEICON"],
				["TABICON", "q", "w", "e", "r", "t", "y", "u", "i", "o", "p", "`", "+", "\u00E7"],
				["CAPSLOCKICON", "a", "s", "d", "f", "g", "h", "j", "k", "l", "\u00F1", "\u00B4", self.green, self.green],  # [, ]
				["SHIFTICON", "<", "z", "x", "c", "v", "b", "n", "m", ",", ".", "-", "SHIFTICON", "SHIFTICON"],
				self.footer
			], [
				["\u00AA", "!", "\"", "\u00B7", "$", "%", "&", "/", "(", ")", "=", "?", "\u00BF", "BACKSPACEICON"],
				["TABICON", "Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P", "^", "*", "\u00C7"],
				["CAPSLOCKICON", "A", "S", "D", "F", "G", "H", "J", "K", "L", "\u00D1", "\u00A8", self.green, self.green],  # {, }
				["SHIFTICON", ">", "Z", "X", "C", "V", "B", "N", "M", ";", ":", "_", "SHIFTICON", "SHIFTICON"],
				self.footer
			], [
				["\\", "|", "@", "#", "~", "\u20AC", "\u00AC", "", "", "", "", "", "", "BACKSPACEICON"],
				["TABICON", "", "\u00E1", "\u00E9", "\u00ED", "\u00F3", "\u00FA", "\u00FC", "", "", "[", "]", "", ""],
				["CAPSLOCKICON", "", "\u00C1", "\u00C9", "\u00CD", "\u00D3", "\u00DA", "\u00DC", "", "", "{", "}", self.green, self.green],
				["SHIFTICON", "", "", "", "", "", "", "", "", "", "", "", "SHIFTICON", "SHIFTICON"],
				self.footer
			]
		]
		self.thai = [
			[
				["", "", "\u0E45", "\u0E20", "\u0E16", "\u0E38", "\u0E36", "\u0E04", "\u0E15", "\u0E08", "\u0E02", "\u0E0A", "", "BACKSPACEICON"],
				["TABICON", "\u0E46", "\u0E44", "\u0E33", "\u0E1E", "\u0E30", "\u0E31", "\u0E35", "\u0E23", "\u0E19", "\u0E22", "\u0E1A", "\u0E25", ""],
				["CAPSLOCKICON", "\u0E1F", "\u0E2B", "\u0E01", "\u0E14", "\u0E40", "\u0E49", "\u0E48", "\u0E32", "\u0E2A", "\u0E27", "\u0E07", "\u0E03", self.green],
				["SHIFTICON", "SHIFTICON", "\u0E1C", "\u0E1B", "\u0E41", "\u0E2D", "\u0E34", "\u0E37", "\u0E17", "\u0E21", "\u0E43", "\u0E1D", "SHIFTICON", "SHIFTICON"],
				self.footer
			], [
				["", "", "\u0E51", "\u0E52", "\u0E53", "\u0E54", "\u0E39", "\u0E55", "\u0E56", "\u0E57", "\u0E58", "\u0E59", "", "BACKSPACEICON"],
				["TABICON", "\u0E50", "", "\u0E0E", "\u0E11", "\u0E18", "\u0E4D", "\u0E4A", "\u0E13", "\u0E2F", "\u0E0D", "\u0E10", "\u0E05", ""],
				["CAPSLOCKICON", "\u0E24", "\u0E06", "\u0E0F", "\u0E42", "\u0E0C", "\u0E47", "\u0E4B", "\u0E29", "\u0E28", "\u0E0B", "", "\u0E3F", self.green],
				["SHIFTICON", "SHIFTICON", "", "\u0E09", "\u0E2E", "\u0E3A", "\u0E4C", "", "\u0E12", "\u0E2C", "\u0E26", "", "SHIFTICON", "SHIFTICON"],
				self.footer
			]
		]
		self.locales = {
			"ar_BH": [self.arabic(self.english), None],
			"ar_EG": [self.arabic(self.english), None],
			"ar_JO": [self.arabic(self.english), None],
			"ar_KW": [self.arabic(self.english), None],
			"ar_LB": [self.arabic(self.english), None],
			"ar_OM": [self.arabic(self.english), None],
			"ar_QA": [self.arabic(self.english), None],
			"ar_SA": [self.arabic(self.english), None],
			"ar_SY": [self.arabic(self.english), None],
			"ar_AE": [self.arabic(self.english), None],
			"ar_YE": [self.arabic(self.english), None],
			"bg_BG": [self.bulgarian, None],
			"cs_CZ": [self.czech, None],
			"nl_NL": [self.dutch(self.english), None],
			"en_AU": [self.english, None],
			"en_GB": [self.unitedKingdom(self.english), None],
			"en_US": [self.english, None],
			"en_EN": [self.english, _("Various")],
			"et_EE": [self.estonian(self.scandinavian), None],
			"fa_IR": [self.farsi(self.english), None],
			"fi_FI": [self.scandinavian, None],
			"fr_BE": [self.belgian(self.french), None],
			"fr_FR": [self.french, None],
			"fr_CH": [self.frenchSwiss(self.german), None],
			"de_DE": [self.german, None],
			"de_CH": [self.germanSwiss(self.german), None],
			"el_GR": [self.greek, None],
			"hu_HU": [self.hungarian(self.german), None],
			"lv_01": [self.latvianStandard(self.english), _("Alternative 1")],
			"lv_02": [self.latvian, _("Alternative 2")],
			"lv_LV": [self.latvianQWERTY(self.english), None],
			"lt_LT": [self.lithuanian(self.english), None],
			"nb_NO": [self.norwegian(self.scandinavian), None],
			"pl_01": [self.polish(self.german), _("Alternative")],
			"pl_PL": [self.polishProgrammers(self.english), None],
			"ru_RU": [self.russian, None],
			"sk_SK": [self.slovak(self.german), None],
			"es_ES": [self.spanish, None],
			"sv_SE": [self.scandinavian, None],
			"th_TH": [self.thai, None],
			"uk_01": [self.ukranian(self.russian), _("Russian")],
			"uk_UA": [self.ukranianEnhanced(self.russian), None]
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
		}, prio=0, description=_("Virtual Keyboard Actions"))
		self.locale = international.getLocale()
		self["prompt"] = Label(prompt)
		self["text"] = Input(text=text.replace("\t", self.TAB_GLYPH), maxSize=maxSize, visible_width=visibleWidth, type=type, currPos=len(text) if currPos is None else currPos, allMarked=allMarked)
		self["list"] = VirtualKeyboardList([])
		self["mode"] = Label(_("INS"))
		self["locale"] = Label(f"{_('Locale')}: {self.locale}")
		self["language"] = Label(f"{_('Language')}: {self.locale}")
		self["key_info"] = StaticText(_("INFO"))
		self["key_red"] = StaticText(_("Exit"))
		self["key_green"] = StaticText(_(greenLabel))
		self["key_yellow"] = StaticText(_("Shift"))
		self["key_blue"] = StaticText(self.shiftMsgs[1])
		self["key_text"] = StaticText(_("TEXT"))
		self["key_help"] = StaticText(_("HELP"))
		width, height = parameters.get("VirtualKeyboard", parameters.get("VirtualKeyBoard", (45, 45)))
		if self.iconBackgroundLeft is None or self.iconBackgroundMiddle is None or self.iconBackgroundRight is None:
			self.width = width
			self.height = height
		else:
			self.width = self.iconBackgroundLeft.size().width() + self.iconBackgroundMiddle.size().width() + self.iconBackgroundRight.size().width()
			self.height = self.iconBackgroundMiddle.size().height()
		# Alignment -> (Horizontal, Vertical):
		# 	Horizontal alignment: 0=Auto, 1=Left, 2=Center, 3=Right (Auto=Left on left, Center on middle, Right on right).
		# 	Vertical alignment: 0=Auto, 1=Top, 2=Center, 3=Bottom (Auto=Center).
		self.alignment = parameters.get("VirtualKeyboardAlignment", parameters.get("VirtualKeyBoardAlignment", (0, 0)))
		# Padding -> (Left/Right, Top/Botton) in pixels
		self.padding = parameters.get("VirtualKeyboardPadding", parameters.get("VirtualKeyBoardPadding", (4, 4)))
		# Text color for each shift level.  (Ensure there is a color for each shift level!)
		self.shiftColors = parameters.get("VirtualKeyboardShiftColors", parameters.get("VirtualKeyBoardShiftColors", (0x00ffffff, 0x00ffffff, 0x0000ffff, 0x00ff00ff)))
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
		self["list"].enableAutoNavigation(False)
		self.buildVirtualKeyboard()

	def arabic(self, base):
		keyList = deepcopy(base)
		keyList[1][0][8] = "\u066D"
		keyList.extend([[
			["\u0630", "\u0661", "\u0662", "\u0663", "\u0664", "\u0665", "\u0666", "\u0667", "\u0668", "\u0669", "\u0660", "-", "=", "BACKSPACEICON"],
			["TABICON", "\u0636", "\u0635", "\u062B", "\u0642", "\u0641", "\u063A", "\u0639", "\u0647", "\u062E", "\u062D", "\u062C", "\u062F", "\\"],
			["CAPSLOCKICON", "\u0634", "\u0633", "\u064A", "\u0628", "\u0644", "\u0627", "\u062A", "\u0646", "\u0645", "\u0643", "\u0637", self.green, self.green],
			["SHIFTICON", "SHIFTICON", "\u0626", "\u0621", "\u0624", "\u0631", "\uFEFB", "\u0649", "\u0629", "\u0648", "\u0632", "\u0638", "SHIFTICON", "SHIFTICON"],
			self.footer
		], [
			["\u0651", "!", "@", "#", "$", "%", "^", "&", "\u066D", "(", ")", "_", "+", "BACKSPACEICON"],
			["TABICON", "\u0636", "\u0635", "\u062B", "\u0642", "\u0641", "\u063A", "\u0639", "\u00F7", "\u00D7", "\u061B", ">", "<", "|"],
			["CAPSLOCKICON", "\u0634", "\u0633", "\u064A", "\u0628", "\u0644", "\u0623", "\u0640", "\u060C", "/", ":", "\"", self.green, self.green],
			["SHIFTICON", "SHIFTICON", "\u0626", "\u0621", "\u0624", "\u0631", "\uFEF5", "\u0622", "\u0629", ",", ".", "\u061F", "SHIFTICON", "SHIFTICON"],
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
		keyList[0][3] = ["SHIFTICON", "]", "z", "x", "c", "v", "b", "n", "m", ",", ".", "-", "SHIFTICON", "SHIFTICON"]
		keyList[1][0] = ["\u00A7", "!", "\"", "#", "$", "%", "&", "_", "(", ")", "'", "?", "~", "BACKSPACEICON"]
		keyList[1][1][11] = "^"
		keyList[1][1][12] = "|"
		keyList[1][1][13] = ">"
		keyList[1][2][10] = "\u00B1"
		keyList[1][2][11] = "`"
		keyList[1][3] = ["SHIFTICON", "[", "Z", "X", "C", "V", "B", "N", "M", ";", ":", "=", "SHIFTICON", "SHIFTICON"]
		keyList.append([
			["\u00AC", "\u00B9", "\u00B2", "\u00B3", "\u00BC", "\u00BD", "\u00BE", "\u00A3", "{", "}", "", "\\", "\u00B8", "BACKSPACEICON"],
			["TABICON", "", "", "\u20AC", "\u00B6", "", "\u00E1", "\u00E9", "\u00ED", "\u00F3", "\u00FA", "", "", ""],
			["CAPSLOCKICON", "", "\u00DF", "", "", "", "\u00C1", "\u00C9", "\u00CD", "\u00D3", "\u00DA", "", self.green, self.green],
			["SHIFTICON", "\u00A6", "\u00AB", "\u00BB", "\u00A2", "", "", "", "\u00B5", "", "\u00B7", "", "SHIFTICON", "SHIFTICON"],
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

	def farsi(self, base):
		keyList = deepcopy(base)
		keyList.append([
			["\u00F7", "\u06F1", "\u06F2", "\u06F3", "\u06F4", "\u06F5", "\u06F6", "\u06F7", "\u06F8", "\u06F9", "\u06F0", "-", "=", "BACKSPACEICON"],
			["TABICON", "\u0636", "\u0635", "\u062B", "\u0642", "\u0641", "\u063A", "\u0639", "\u0647", "\u062E", "\u062D", "\u062C", "\u0686", "\u067E"],
			["CAPSLOCKICON", "\u0634", "\u0633", "\u06CC", "\u0628", "\u0644", "\u0627", "\u062A", "\u0646", "\u0645", "\u06A9", "\u06AF", self.green, self.green],
			["SHIFTICON", "\u0649", "\u0638", "\u0637", "\u0632", "\u0631", "\u0630", "\u062F", "\u0626", "\u0648", ".", "/", "SHIFTICON", "SHIFTICON"],
			self.footer
		])
		keyList.append([
			["\u00D7", "!", "@", "#", "$", "%", "^", "&", "*", ")", "(", "_", "+", "BACKSPACEICON"],
			["TABICON", "\u064B", "\u064C", "\u064D", "\u0631", "\u060C", "\u061B", ",", "]", "[", "\\", "}", "{", "|"],
			["CAPSLOCKICON", "\u064E", "\u064F", "\u0650", "\u0651", "\u06C0", "\u0622", "\u0640", "\u00AB", "\u00BB", ":", "\"", self.green, self.green],
			["SHIFTICON", "|", "\u0629", "\u064A", "\u0698", "\u0624", "\u0625", "\u0623", "\u0621", "<", ">", "\u061F", "SHIFTICON", "SHIFTICON"],
			self.footer
		])
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
			["TABICON", "\\", "|", "\u00C4", "", "", "", "\u20AC", "\u00CD", "", "", "\u00F7", "\u00D7", "\u00A4"],
			["CAPSLOCKICON", "\u00E4", "\u0111", "\u0110", "[", "]", "", "\u00ED", "\u0142", "\u0141", "$", "\u00DF", self.green, self.green],
			["SHIFTICON", "<", ">", "#", "&", "@", "{", "}", "<", ";", ">", "*", "SHIFTICON", "SHIFTICON"],
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
			["TABICON", "", "", "\u0113", "\u0157", "", "", "\u016B", "\u012B", "\u014D", "", "", "", ""],
			["CAPSLOCKICON", "\u0101", "\u0161", "", "", "\u0123", "", "", "\u0137", "\u013C", "", "\u00B4", self.green, self.green],
			["SHIFTICON", "", "\u017E", "", "\u010D", "", "", "\u0146", "", "", "", "", "SHIFTICON", "SHIFTICON"],
			self.footer
		])
		keyList.append([
			["", "", "", "", "\u00A7", "\u00B0", "", "\u00B1", "\u00D7", "", "", "\u2014", "", "BACKSPACEICON"],
			["TABICON", "", "", "\u0112", "\u0156", "", "", "\u016A", "\u012A", "\u014C", "", "", "", ""],
			["CAPSLOCKICON", "\u0100", "\u0160", "", "", "\u0122", "", "", "\u0136", "\u013B", "", "\u00A8", self.green, self.green],
			["SHIFTICON", "", "\u017D", "", "\u010C", "", "", "\u0145", "", "", "", "", "SHIFTICON", "SHIFTICON"],
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
			["TABICON", "!", "@", "#", "$", "%", "^", "&", "*", "", "", "", "+", ""],
			["CAPSLOCKICON", "", "", "\u20AC", "", "", "", "", "", "", "", "", self.green, self.green],
			["SHIFTICON", "", "", "", "", "", "", "", "", "", "", "", "SHIFTICON", "SHIFTICON"],
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
			["TABICON", "\\", "\u00A6", "", "\u017B", "\u015A", "\u00D3", "\u20AC", "\u0143", "\u0106", "\u0179", "\u00F7", "\u00D7", ""],
			["CAPSLOCKICON", "", "\u0111", "\u0110", "", "", "", "", "\u0104", "\u0118", "$", "\u00DF", self.green, self.green],
			["SHIFTICON", "", "", "", "", "@", "{", "}", "\u00A7", "<", ">", "", "SHIFTICON", "SHIFTICON"],
			self.footer
		])
		return keyList

	def polishProgrammers(self, base):
		keyList = deepcopy(base)
		keyList[0][3][1] = "\\"
		keyList[1][3][1] = "|"
		keyList.append([
			["", "", "", "", "", "", "", "", "", "", "", "", "", "BACKSPACEICON"],
			["TABICON", "", "", "\u0119", "\u0118", "", "", "\u20AC", "", "\u00F3", "\u00D3", "", "", ""],
			["CAPSLOCKICON", "\u0105", "\u0104", "\u015B", "\u015A", "", "", "", "", "\u0142", "\u0141", "", self.green, self.green],
			["SHIFTICON", "\u017C", "\u017B", "\u017A", "\u0179", "\u0107", "\u0106", "\u0144", "\u0143", "", "", "", "SHIFTICON", "SHIFTICON"],
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
			["TABICON", "\\", "|", "\u20AC", "", "", "", "", "", "", "'", "\u00F7", "\u00D7", "\u00A4"],
			["CAPSLOCKICON", "", "\u0111", "\u0110", "[", "]", "", "", "\u0142", "\u0141", "$", "\u00DF", self.green, self.green],
			["SHIFTICON", "<", ">", "#", "&", "@", "{", "}", "", "<", ">", "*", "SHIFTICON", "SHIFTICON"],
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
		keyList[0][3] = ["SHIFTICON", "\\", "z", "x", "c", "v", "b", "n", "m", ",", ".", "/", "SHIFTICON", "SHIFTICON"]
		keyList[0][4] = copy(self.footer)
		keyList[0][4][10] = "\u00A6"
		keyList[1][0][0] = "\u00AC"
		keyList[1][0][2] = "\""
		keyList[1][0][3] = "\u00A3"
		keyList[1][1][13] = "~"
		keyList[1][2][11] = "@"
		keyList[1][3] = ["SHIFTICON", "|", "Z", "X", "C", "V", "B", "N", "M", "<", ">", "?", "SHIFTICON", "SHIFTICON"]
		keyList[1][4] = copy(self.footer)
		keyList[1][4][10] = "\u20AC"
		return keyList

	def smsGotChar(self):
		if self.smsChar and self.selectAsciiKey(self.smsChar):
			self.processSelect()

	def setLocale(self):
		language = international.getLanguageTranslated(self.locale)
		country = international.getCountryTranslated(self.locale)
		self.keyList, location = self.locales.get(self.locale, [None, None])
		country = country if country else location
		if self.keyList is None:
			self.locale = "en_EN"
			self.keyList = self.english
		self.shiftLevel = 0
		self["locale"].setText(f"{_('Locale')}: {self.locale}  ({language} - {country})")

	def buildVirtualKeyboard(self):
		self.shiftLevels = len(self.keyList)  # Check the current shift level is available / valid in this layout.
		if self.shiftLevel >= self.shiftLevels:
			self.shiftLevel = 0
		self.keyboardWidth = len(self.keyList[self.shiftLevel][0])  # Determine current keymap size.
		self.keyboardHeight = len(self.keyList[self.shiftLevel])
		self.maxKey = self.keyboardWidth * (self.keyboardHeight - 1) + len(self.keyList[self.shiftLevel][-1]) - 1
		# print(f"[VirtualKeyboard] DEBUG: Width={self.keyboardWidth}, Height={self.keyboardHeight}, Keys={self.maxKey + 1}, maxKey={self.maxKey}, shiftLevels={self.shiftLevels}")
		self.index = 0
		self.keyboardList = []
		for keys in self.keyList[self.shiftLevel]:  # Process all the buttons in this shift level.
			self.keyboardList.append(self.virtualKeyboardEntryComponent(keys))
		self.previousSelectedKey = None
		if self.selectedKey is None:  # Start on the first character of the forth row (FIRSTICON button).
			self.selectedKey = self.keyboardWidth * 4
		self.markSelectedKey()

	def virtualKeyboardEntryComponent(self, keys):
		res = [keys]
		text = []
		offset = 14 - self.keyboardWidth  # 14 represents the maximum buttons per row as defined here and in the skin (14 x self.width).
		xPos = self.width * offset // 2
		if offset % 2:
			xPos += self.width // 2
		xHighlight = xPos
		prevKey = None
		for key in keys:
			if key != prevKey:
				xPadded = xPos + self.padding[0]
				start, width = self.findStartAndWidth(self.index)
				if self.iconBackgroundLeft is None or self.iconBackgroundMiddle is None or self.iconBackgroundRight is None:  # If available display the cell background.
					xPos += self.width * width
				else:
					iconWidth = self.iconBackgroundLeft.size().width()
					res.append(MultiContentEntryPixmapAlphaBlend(pos=(xPos, 0), size=(iconWidth, self.height), png=self.iconBackgroundLeft))
					xPos += iconWidth
					iconWidth = self.iconBackgroundMiddle.size().width() + (self.width * (width - 1))
					res.append(MultiContentEntryPixmapAlphaBlend(pos=(xPos, 0), size=(iconWidth, self.height), png=self.iconBackgroundMiddle, flags=BT_SCALE))
					xPos += iconWidth
					iconWidth = self.iconBackgroundRight.size().width()
					res.append(MultiContentEntryPixmapAlphaBlend(pos=(xPos, 0), size=(iconWidth, self.height), png=self.iconBackgroundRight))
					xPos += iconWidth
				highlight = self.iconHighlights.get(key.upper(), (None, None, None))  # Check if the cell needs to be highlighted.
				if highlight[0] is None or highlight[1] is None or highlight[2] is None:  # If available display the cell highlight.
					xHighlight += self.width * width
				else:
					iconWidth = highlight[0].size().width()
					res.append(MultiContentEntryPixmapAlphaBlend(pos=(xHighlight, 0), size=(iconWidth, self.height), png=highlight[0]))
					xHighlight += iconWidth
					iconWidth = highlight[1].size().width() + (self.width * (width - 1))
					res.append(MultiContentEntryPixmapAlphaBlend(pos=(xHighlight, 0), size=(iconWidth, self.height), png=highlight[1], flags=BT_SCALE))
					xHighlight += iconWidth
					iconWidth = highlight[2].size().width()
					res.append(MultiContentEntryPixmapAlphaBlend(pos=(xHighlight, 0), size=(iconWidth, self.height), png=highlight[2]))
					xHighlight += iconWidth
				if self.alignment[0] == 1:  # Determine the cell alignment.
					horizontalAlignment = RT_HALIGN_LEFT
				elif self.alignment[0] == 2:
					horizontalAlignment = RT_HALIGN_CENTER
				elif self.alignment[0] == 3:
					horizontalAlignment = RT_HALIGN_RIGHT
				else:
					if start == 0 and width > 1:
						horizontalAlignment = RT_HALIGN_LEFT
					elif start + width == self.keyboardWidth and width > 1:
						horizontalAlignment = RT_HALIGN_RIGHT
					else:
						horizontalAlignment = RT_HALIGN_CENTER
				if self.alignment[1] == 1:
					verticalAlignment = RT_VALIGN_TOP
				elif self.alignment[1] == 3:
					verticalAlignment = RT_VALIGN_BOTTOM
				else:
					verticalAlignment = RT_VALIGN_CENTER
				width = (width * self.width) - (self.padding[0] * 2)  # Determine the cell data area.
				height = self.height - (self.padding[1] * 2)
				icon = self.keyIcons[self.shiftLevel].get(key, None)  # Check if the cell contains an icon.
				if icon:  # Display the cell icon.
					left = xPadded
					iconWidth = icon.size().width()
					if horizontalAlignment == RT_HALIGN_CENTER:
						left += (width - iconWidth) // 2
					elif horizontalAlignment == RT_HALIGN_RIGHT:
						left += width - iconWidth
					top = self.padding[1]
					iconHeight = icon.size().height()
					if verticalAlignment == RT_VALIGN_CENTER:
						top += (height - iconHeight) // 2
					elif verticalAlignment == RT_VALIGN_BOTTOM:
						top += height - iconHeight
					res.append(MultiContentEntryPixmapAlphaBlend(pos=(left, top), size=(iconWidth, iconHeight), png=icon))
					# print(f"[VirtualKeyboard] DEBUG: Left={left}, Top={top}, Width={width}, Height={height}, Icon Width={iconWidth}, Icon Height={iconHeight}")
				else:  # Display the cell text.
					skey = key
					if len(key) > 1:  # NOTE: UTF8 / Unicode glyphs only count as one character here.
						text.append(MultiContentEntryText(pos=(xPadded, self.padding[1]), size=(width, height), font=1, flags=horizontalAlignment | verticalAlignment, text=skey, color=self.shiftColors[self.shiftLevel]))
					else:
						text.append(MultiContentEntryText(pos=(xPadded, self.padding[1]), size=(width, height), font=0, flags=horizontalAlignment | verticalAlignment, text=skey, color=self.shiftColors[self.shiftLevel]))
			prevKey = key
			self.index += 1
		return res + text

	def markSelectedKey(self):
		if self.iconSelectedLeft is None or self.iconSelectedMiddle is None or self.iconSelectedRight is None:
			return
		if self.previousSelectedKey is not None:
			del self.keyboardList[self.previousSelectedKey // self.keyboardWidth][-3:]
		if self.selectedKey > self.maxKey:
			self.selectedKey = self.maxKey
		start, width = self.findStartAndWidth(self.selectedKey)
		xPos = start * self.width
		iconWidth = self.iconSelectedLeft.size().width()
		self.keyboardList[self.selectedKey // self.keyboardWidth].append(MultiContentEntryPixmapAlphaBlend(pos=(xPos, 0), size=(iconWidth, self.height), png=self.iconSelectedLeft))
		xPos += iconWidth
		iconWidth = self.iconSelectedMiddle.size().width() + (self.width * (width - 1))
		self.keyboardList[self.selectedKey // self.keyboardWidth].append(MultiContentEntryPixmapAlphaBlend(pos=(xPos, 0), size=(iconWidth, self.height), png=self.iconSelectedMiddle, flags=BT_SCALE))
		xPos += iconWidth
		iconWidth = self.iconSelectedRight.size().width()
		self.keyboardList[self.selectedKey // self.keyboardWidth].append(MultiContentEntryPixmapAlphaBlend(pos=(xPos, 0), size=(iconWidth, self.height), png=self.iconSelectedRight))
		self.previousSelectedKey = self.selectedKey
		self["list"].setList(self.keyboardList)

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
		# print(f"[VirtualKeyboard] DEBUG: Key='{self.keyList[self.shiftLevel][row][key]}', Position={key}, Start={start}, Width={width}")
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
		self.sms.stopTimer()
		self.close(None)

	def save(self):
		self.smsGotChar()
		self.sms.stopTimer()
		self.close(self["text"].getText().replace(self.TAB_GLYPH, "\t"))

	def localeMenu(self):
		def localeMenuCallback(choice):
			if choice:
				self.locale = choice[1]
				self.setLocale()
				self.buildVirtualKeyboard()

		languages = []
		for locale in self.locales.keys():
			language = international.getLanguageTranslated(locale)
			country = international.getCountryTranslated(locale)
			country = country if country else self.locales[locale][1]
			languages.append((f"{language}  -  {country}  ({locale})", locale))
		languages = sorted(languages)
		default = 0
		for index, item in enumerate(languages):
			if item[1] == self.locale:
				default = index
				break
		self.session.openWithCallback(localeMenuCallback, ChoiceBox, windowTitle=_("Available locales are:"), choiceList=languages, selection=default, buttonList=[])

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
		self.buildVirtualKeyboard()

	def shiftRestore(self):
		self.shiftLevel = self.shiftHold
		self.shiftHold = -1
		self.shiftCommon()

	def keyToggleOW(self):
		self["text"].toggleOverwrite()
		self.overwrite = not self.overwrite
		self["mode"].setText(_("OVR") if self.overwrite else _("INS"))

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

	def selectAsciiKey(self, character):
		if character == " ":
			character = self.SPACE
		self.shiftLevel = -1
		for keyList in (self.keyList):
			self.shiftLevel = (self.shiftLevel + 1) % self.shiftLevels
			self.buildVirtualKeyboard()
			selKey = 0
			for keys in keyList:
				for key in keys:
					if key == character:
						self.selectedKey = selKey
						self.markSelectedKey()
						return True
					selKey += 1
		return False


class VirtualKeyBoard(VirtualKeyboard):
	def __init__(self, session, title=_("Virtual Keyboard Text:"), text="", maxSize=False, visible_width=False, type=Input.TEXT, currPos=None, allMarked=False, style=VirtualKeyboard.VKB_ENTER_ICON, windowTitle=None):
		VirtualKeyboard.__init__(self, session, title=title, text=text, maxSize=maxSize, visibleWidth=visible_width, type=type, currPos=currPos, allMarked=allMarked, style=style, windowTitle=windowTitle)

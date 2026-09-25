from enigma import RT_BLEND, RT_HALIGN_CENTER, RT_HALIGN_LEFT, RT_VALIGN_CENTER, eListboxPythonMultiContent, gFont

from skin import fonts, parameters, parseVerticalAlignment
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText
from Tools.Directories import SCOPE_GUISKIN, resolveFilename
from Tools.LoadPixmap import LoadPixmap


def nativeChoiceIcon(key):
	if not parameters.get("ChoiceListNative", 0) or key in ("dummy", "none"):
		return None
	color = colorSelected = None
	if len(key) == 1 and key in "0123456789":
		text, font = key, 0
	else:
		value = parameters.get("ChoiceListIcon_" + key)
		if value is None:
			return None
		values = value if isinstance(value, (list, tuple)) else (value,)
		try:
			codepoint = values[0]
			if not isinstance(codepoint, int) or not 0 < codepoint <= 0x10FFFF or 0xD800 <= codepoint <= 0xDFFF:
				return None
			text, font = chr(codepoint), 1
			color = values[1] if len(values) > 1 else None
			colorSelected = values[2] if len(values) > 2 else color
		except IndexError:
			return None
	x, y, w, h = parameters.get("ChoicelistIcon", (5, 0, 35, 25))
	if key in ("expanded", "verticalline"):
		x, y, w, h = parameters.get("ChoicelistIcon" + key.capitalize(), (x, y, w, h))
	return MultiContentEntryText(pos=(x, y), size=(w, h), font=font,
		flags=RT_HALIGN_CENTER | RT_VALIGN_CENTER | RT_BLEND, text=text, color=color, color_sel=colorSelected)


def ChoiceEntryComponent(key=None, text=None):
	verticalAlignment = parseVerticalAlignment(parameters.get("ChoicelistVerticalAlignment", "top")) << 4  # This is a hack until other images fix their code.
	text = ["--"] if text is None else text
	res = [text]
	if text[0] == "--":
		x, y, w, h = parameters.get("ChoicelistDash", (0, 0, 1280, 25))
		res = [None, (eListboxPythonMultiContent.TYPE_TEXT, x, y, w, h, 0, RT_HALIGN_LEFT | verticalAlignment, "\u2014" * 200)]
	else:
		if key:
			x, y, w, h = parameters.get("ChoicelistName", (45, 0, 1235, 25))
			res.append((eListboxPythonMultiContent.TYPE_TEXT, x, y, w, h, 0, RT_HALIGN_LEFT | verticalAlignment, text[0]))
			icon = nativeChoiceIcon(key)
			if icon is not None:
				res.append(icon)
				png = None
			elif key in ("dummy", "none"):
				png = None
			elif key == "expandable":
				png = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/expandable.png"))
			elif key == "expanded":
				png = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/expanded.png"))
			elif key == "verticalline":
				png = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/verticalline.png"))
			else:
				png = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "buttons/key_%s.png" % key))
			if png:
				x, y, w, h = parameters.get("ChoicelistIcon", (5, 0, 35, 25))
				if key == "verticalline" and "ChoicelistIconVerticalline" in parameters:
					x, y, w, h = parameters.get("ChoicelistIconVerticalline", (5, 0, 35, 25))
				if key == "expanded" and "ChoicelistIconExpanded" in parameters:
					x, y, w, h = parameters.get("ChoicelistIconExpanded", (5, 0, 35, 25))
				res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, x, y, w, h, png))
		else:
			x, y, w, h = parameters.get("ChoicelistNameSingle", (5, 0, 1275, 25))
			res.append((eListboxPythonMultiContent.TYPE_TEXT, x, y, w, h, 0, RT_HALIGN_LEFT | verticalAlignment, text[0]))
	return res


class ChoiceList(MenuList):
	def __init__(self, list, selection=0, enableWrapAround=False):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		font = fonts.get("ChoiceList", ("Regular", 20, 25))
		self.l.setFont(0, gFont(font[0], font[1]))
		if parameters.get("ChoiceListNative", 0):
			iconFont = fonts.get("ChoiceListIcons", ("enigma2icons", font[1]))
			self.l.setFont(1, gFont(iconFont[0], iconFont[1]))
		self.l.setItemHeight(font[2])
		self.itemHeight = font[2]
		self.selection = selection

	def postWidgetCreate(self, instance):
		MenuList.postWidgetCreate(self, instance)
		self.moveToIndex(self.selection)

	def getItemHeight(self):
		return self.itemHeight

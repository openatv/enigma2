from enigma import RT_HALIGN_LEFT, RT_VALIGN_TOP, eListboxPythonMultiContent

from skin import parseColor
from Tools.Directories import SCOPE_CURRENT_SKIN, resolveFilename
from Tools.LoadPixmap import LoadPixmap


def __resolveColor(color):
	if isinstance(color, str):
		try:
			return parseColor(color).argb()
		except Exception as err:
			print "[MultiContent] Error: Resolve color '%s'" % str(err)
		return None
	return color


def __resolvePixmap(pixmap):
	if isinstance(pixmap, str):
		try:
			return LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, pixmap))
		except Exception as err:
			print "[MultiContent] Error: Resolve pixmap '%s'" % str(err)
		return None
	return pixmap


def MultiContentTemplateColor(n):
	return 0xff000000 | n


def MultiContentEntryText(pos=(0, 0), size=(0, 0), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, text="", color=None, color_sel=None, backcolor=None, backcolor_sel=None, border_width=None, border_color=None):
	return eListboxPythonMultiContent.TYPE_TEXT, pos[0], pos[1], size[0], size[1], font, flags, text, __resolveColor(color), __resolveColor(color_sel), __resolveColor(backcolor), __resolveColor(backcolor_sel), border_width, __resolveColor(border_color)


def MultiContentEntryPixmap(pos=(0, 0), size=(0, 0), png=None, backcolor=None, backcolor_sel=None, flags=0):
	return eListboxPythonMultiContent.TYPE_PIXMAP, pos[0], pos[1], size[0], size[1], __resolvePixmap(png), __resolveColor(backcolor), __resolveColor(backcolor_sel), flags


def MultiContentEntryPixmapAlphaTest(pos=(0, 0), size=(0, 0), png=None, backcolor=None, backcolor_sel=None, flags=0):
	return eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, pos[0], pos[1], size[0], size[1], __resolvePixmap(png), __resolveColor(backcolor), __resolveColor(backcolor_sel), flags


def MultiContentEntryPixmapAlphaBlend(pos=(0, 0), size=(0, 0), png=None, backcolor=None, backcolor_sel=None, flags=0):
	return eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, pos[0], pos[1], size[0], size[1], __resolvePixmap(png), __resolveColor(backcolor), __resolveColor(backcolor_sel), flags


def MultiContentEntryProgress(pos=(0, 0), size=(0, 0), percent=None, borderWidth=None, foreColor=None, foreColorSelected=None, backColor=None, backColorSelected=None):
	return eListboxPythonMultiContent.TYPE_PROGRESS, pos[0], pos[1], size[0], size[1], percent, borderWidth, __resolveColor(foreColor), __resolveColor(foreColorSelected), __resolveColor(backColor), __resolveColor(backColorSelected)


def MultiContentEntryProgressPixmap(pos=(0, 0), size=(0, 0), percent=None, pixmap=None, borderWidth=None, foreColor=None, foreColorSelected=None, backColor=None, backColorSelected=None):
	return eListboxPythonMultiContent.TYPE_PROGRESS_PIXMAP, pos[0], pos[1], size[0], size[1], percent, __resolvePixmap(pixmap), borderWidth, __resolveColor(foreColor), __resolveColor(foreColorSelected), __resolveColor(backColor), __resolveColor(backColorSelected)

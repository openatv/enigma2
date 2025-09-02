from enigma import GRADIENT_VERTICAL, RT_HALIGN_LEFT, RT_VALIGN_TOP, eListboxPythonMultiContent

from skin import parseColor
from Tools.Directories import SCOPE_GUISKIN, resolveFilename
from Tools.LoadPixmap import LoadPixmap


def __resolveColor(color):
	if isinstance(color, str):
		try:
			return parseColor(color).argb()
		except Exception as err:
			print("[MultiContent] Error: Resolve color '%s'" % str(err))
		return None
	return color


def __resolvePixmap(pixmap):
	if isinstance(pixmap, str):
		try:
			return LoadPixmap(resolveFilename(SCOPE_GUISKIN, pixmap))
		except Exception as err:
			print("[MultiContent] Error: Resolve pixmap '%s'" % str(err))
		return None
	return pixmap


def MultiContentTemplateColor(n):
	return 0xff000000 | n


def MultiContentEntryRectangle(pos=(0, 0), size=(0, 0), backgroundColor=None, backgroundColorSelected=None, borderWidth=None, borderColor=None, borderColorSelected=None, cornerRadius=0, cornerEdges=15):
	return eListboxPythonMultiContent.TYPE_RECT, int(pos[0]), int(pos[1]), int(size[0]), int(size[1]), __resolveColor(backgroundColor), __resolveColor(backgroundColorSelected), borderWidth, __resolveColor(borderColor), __resolveColor(borderColorSelected), cornerRadius, cornerEdges


def MultiContentEntryText(pos=(0, 0), size=(0, 0), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_TOP, text="", color=None, color_sel=None, backcolor=None, backcolor_sel=None, border_width=None, border_color=None, cornerRadius=0, cornerEdges=15, textBWidth=0, textBColor=None):
	return eListboxPythonMultiContent.TYPE_TEXT, int(pos[0]), int(pos[1]), int(size[0]), int(size[1]), font, flags, text, __resolveColor(color), __resolveColor(color_sel), __resolveColor(backcolor), __resolveColor(backcolor_sel), border_width, __resolveColor(border_color), cornerRadius, cornerEdges, textBWidth, __resolveColor(textBColor)


def MultiContentEntryPixmap(pos=(0, 0), size=(0, 0), png=None, backcolor=None, backcolor_sel=None, flags=0, cornerRadius=0, cornerEdges=15):
	return eListboxPythonMultiContent.TYPE_PIXMAP, int(pos[0]), int(pos[1]), int(size[0]), int(size[1]), __resolvePixmap(png), __resolveColor(backcolor), __resolveColor(backcolor_sel), flags, cornerRadius, cornerEdges


def MultiContentEntryPixmapAlphaTest(pos=(0, 0), size=(0, 0), png=None, backcolor=None, backcolor_sel=None, flags=0, cornerRadius=0, cornerEdges=15):
	return eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, int(pos[0]), int(pos[1]), int(size[0]), int(size[1]), __resolvePixmap(png), __resolveColor(backcolor), __resolveColor(backcolor_sel), flags, cornerRadius, cornerEdges


def MultiContentEntryPixmapAlphaBlend(pos=(0, 0), size=(0, 0), png=None, backcolor=None, backcolor_sel=None, flags=0, cornerRadius=0, cornerEdges=15):
	return eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, int(pos[0]), int(pos[1]), int(size[0]), int(size[1]), __resolvePixmap(png), __resolveColor(backcolor), __resolveColor(backcolor_sel), flags, cornerRadius, cornerEdges


def MultiContentEntryProgress(pos=(0, 0), size=(0, 0), percent=None, borderWidth=None, borderColor=None, borderColorSelected=None, foreColor=None, foreColorSelected=None, backColor=None, backColorSelected=None, startColor=None, midColor=None, endColor=None, startColorSelected=None, midColorSelected=None, endColorSelected=None, cornerRadius=0, cornerEdges=15):
	return eListboxPythonMultiContent.TYPE_PROGRESS, int(pos[0]), int(pos[1]), int(size[0]), int(size[1]), percent, borderWidth, __resolveColor(foreColor), __resolveColor(foreColorSelected), __resolveColor(backColor), __resolveColor(backColorSelected), __resolveColor(borderColor), __resolveColor(borderColorSelected), __resolveColor(startColor), __resolveColor(midColor), __resolveColor(endColor), __resolveColor(startColorSelected), __resolveColor(midColorSelected), __resolveColor(endColorSelected), cornerRadius, cornerEdges


def MultiContentEntryProgressPixmap(pos=(0, 0), size=(0, 0), percent=None, pixmap=None, borderWidth=None, borderColor=None, borderColorSelected=None, foreColor=None, foreColorSelected=None, backColor=None, backColorSelected=None, cornerRadius=0, cornerEdges=15):
	return eListboxPythonMultiContent.TYPE_PROGRESS_PIXMAP, int(pos[0]), int(pos[1]), int(size[0]), int(size[1]), percent, __resolvePixmap(pixmap), borderWidth, __resolveColor(foreColor), __resolveColor(foreColorSelected), __resolveColor(backColor), __resolveColor(backColorSelected), __resolveColor(borderColor), __resolveColor(borderColorSelected), cornerRadius, cornerEdges


def MultiContentEntryLinearGradient(pos=(0, 0), size=(0, 0), direction=GRADIENT_VERTICAL, startColor=None, midColor=None, endColor=None, startColorSelected=None, midColorSelected=None, endColorSelected=None, fullSize=0, cornerRadius=0, cornerEdges=15):
    return eListboxPythonMultiContent.TYPE_LINEAR_GRADIENT, int(pos[0]), int(pos[1]), int(size[0]), int(size[1]), direction, __resolveColor(startColor), __resolveColor(midColor), __resolveColor(endColor), __resolveColor(startColorSelected), __resolveColor(midColorSelected), __resolveColor(endColorSelected), fullSize, cornerRadius, cornerEdges


def MultiContentEntryLinearGradientAlphaBlend(pos=(0, 0), size=(0, 0), direction=GRADIENT_VERTICAL, startColor=None, midColor=None, endColor=None, startColorSelected=None, midColorSelected=None, endColorSelected=None, fullSize=0, cornerRadius=0, cornerEdges=15):
    return eListboxPythonMultiContent.TYPE_LINEAR_GRADIENT_ALPHABLEND, int(pos[0]), int(pos[1]), int(size[0]), int(size[1]), direction, __resolveColor(startColor), __resolveColor(midColor), __resolveColor(endColor), __resolveColor(startColorSelected), __resolveColor(midColorSelected), __resolveColor(endColorSelected), fullSize, cornerRadius, cornerEdges

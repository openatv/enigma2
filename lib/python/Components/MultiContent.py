from enigma import eListboxPythonMultiContent, RT_HALIGN_LEFT, RT_VALIGN_TOP

def MultiContentTemplateColor(n): return 0xff000000 | n

def MultiContentEntryText(pos = (0, 0), size = (0, 0), font = 0, flags = RT_HALIGN_LEFT | RT_VALIGN_TOP, text = "", color = None, color_sel = None, backcolor = None, backcolor_sel = None, border_width = None, border_color = None):
	return eListboxPythonMultiContent.TYPE_TEXT, pos[0], pos[1], size[0], size[1], font, flags, text, color, color_sel, backcolor, backcolor_sel, border_width, border_color

def MultiContentEntryPixmap(pos = (0, 0), size = (0, 0), png = None, backcolor = None, backcolor_sel = None, flags = 0):
	return eListboxPythonMultiContent.TYPE_PIXMAP, pos[0], pos[1], size[0], size[1], png, backcolor, backcolor_sel, flags

def MultiContentEntryPixmapAlphaTest(pos = (0, 0), size = (0, 0), png = None, backcolor = None, backcolor_sel = None, flags = 0):
	return eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, pos[0], pos[1], size[0], size[1], png, backcolor, backcolor_sel, flags

def MultiContentEntryPixmapAlphaBlend(pos = (0, 0), size = (0, 0), png = None, backcolor = None, backcolor_sel = None, flags = 0):
	return eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, pos[0], pos[1], size[0], size[1], png, backcolor, backcolor_sel, flags

def MultiContentEntryProgress(pos = (0, 0), size = (0, 0), percent = None, borderWidth = None, foreColor = None, foreColorSelected = None, backColor = None, backColorSelected = None):
	return eListboxPythonMultiContent.TYPE_PROGRESS, pos[0], pos[1], size[0], size[1], percent, borderWidth, foreColor, foreColorSelected, backColor, backColorSelected

def MultiContentEntryProgressPixmap(pos = (0, 0), size = (0, 0), percent = None, pixmap = None, borderWidth = None, foreColor = None, foreColorSelected = None, backColor = None, backColorSelected = None):
	return eListboxPythonMultiContent.TYPE_PROGRESS_PIXMAP, pos[0], pos[1], size[0], size[1], percent, pixmap, borderWidth, foreColor, foreColorSelected, backColor, backColorSelected

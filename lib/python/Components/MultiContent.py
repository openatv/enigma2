from enigma import eListboxPythonMultiContent, RT_HALIGN_LEFT, RT_VALIGN_TOP

def MultiContentTemplateColor(n): return 0xff000000 | n

def MultiContentEntryText(pos = (0, 0), size = (0, 0), font = 0, flags = RT_HALIGN_LEFT | RT_VALIGN_TOP, text = "", color = None, color_sel = None, backcolor = None, backcolor_sel = None, border_width = None, border_color = None):
	return (eListboxPythonMultiContent.TYPE_TEXT, pos[0], pos[1], size[0], size[1], font, flags, text, color, color_sel, backcolor, backcolor_sel, border_width, border_color)

def MultiContentEntryPixmap(pos = (0, 0), size = (0, 0), png = None, backcolor = None, backcolor_sel = None):
	return (eListboxPythonMultiContent.TYPE_PIXMAP, pos[0], pos[1], size[0], size[1], png, backcolor, backcolor_sel)

def MultiContentEntryPixmapAlphaTest(pos = (0, 0), size = (0, 0), png = None, backcolor = None, backcolor_sel = None):
	return (eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, pos[0], pos[1], size[0], size[1], png, backcolor, backcolor_sel)

def MultiContentEntryPixmapAlphaBlend(pos = (0, 0), size = (0, 0), png = None, backcolor = None, backcolor_sel = None):
	return (eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, pos[0], pos[1], size[0], size[1], png, backcolor, backcolor_sel)

def MultiContentEntryProgress(pos = (0, 0), size = (0, 0), percent = None, borderWidth = None, foreColor = None, backColor = None, backColorSelected = None):
	return (eListboxPythonMultiContent.TYPE_PROGRESS, pos[0], pos[1], size[0], size[1], percent, borderWidth, foreColor, backColor, backColorSelected)


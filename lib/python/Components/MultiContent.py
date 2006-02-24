RT_HALIGN_LEFT = 0
RT_HALIGN_RIGHT = 1
RT_HALIGN_CENTER = 2
RT_HALIGN_BLOCK = 4

RT_VALIGN_TOP = 0
RT_VALIGN_CENTER = 8
RT_VALIGN_BOTTOM = 16

RT_WRAP = 32

from enigma import eListboxPythonMultiContent

def MultiContentEntryText(pos = (0, 0), size = (0, 0), font = 0, flags = RT_HALIGN_LEFT | RT_VALIGN_TOP, text = ""):
	return (eListboxPythonMultiContent.TYPE_TEXT, pos[0], pos[1], size[0], size[1], font, flags, text)

def MultiContentEntryPixmap(pos = (0, 0), size = (0, 0), png = None):
	return (eListboxPythonMultiContent.TYPE_PIXMAP, pos[0], pos[1], size[0], size[1], png)

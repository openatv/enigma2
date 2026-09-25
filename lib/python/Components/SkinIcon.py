from enigma import RT_BLEND, RT_HALIGN_CENTER, RT_VALIGN_CENTER

from skin import parameters
from Components.MultiContent import MultiContentEntryText
from Tools.Directories import SCOPE_GUISKIN, resolveFilename
from Tools.LoadPixmap import LoadPixmap


class SkinIcon:
	"""A list icon; unmapped or non-opted-in skins continue to receive pixmaps."""

	def __init__(self, codepoint, color=None, selectedColor=None):
		self.text = chr(codepoint)
		self.color = color
		self.selectedColor = selectedColor

	def entry(self, pos, size, font):
		return MultiContentEntryText(pos=pos, size=size, font=font,
			flags=RT_HALIGN_CENTER | RT_VALIGN_CENTER | RT_BLEND, text=self.text,
			color=self.color, color_sel=self.selectedColor)


def loadSkinIcon(component, name, filename):
	if parameters.get(f"{component}NativeIcons", 0):
		value = parameters.get(f"{component}Icon_{name}")
		values = value if isinstance(value, (tuple, list)) else (value,)
		if 1 <= len(values) <= 3:
			codepoint = values[0]
			if isinstance(codepoint, int) and 0 < codepoint <= 0x10FFFF and not 0xD800 <= codepoint <= 0xDFFF:
				return SkinIcon(*values)
	return LoadPixmap(resolveFilename(SCOPE_GUISKIN, filename))

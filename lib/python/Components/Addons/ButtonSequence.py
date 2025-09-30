from Components.Addons.GUIAddon import GUIAddon

from enigma import eListbox, eListboxPythonMultiContent, BT_ALIGN_CENTER

from skin import applySkinFactor

from Components.MultiContent import MultiContentEntryPixmapAlphaBlend
from Components.Sources.Boolean import Boolean
from Components.Sources.StaticText import StaticText

from Tools.Directories import resolveFilename, SCOPE_GUISKIN
from Tools.LoadPixmap import LoadPixmap


class ButtonSequence(GUIAddon):
	def __init__(self):
		GUIAddon.__init__(self)
		self.l = eListboxPythonMultiContent()  # noqa: E741
		self.l.setBuildFunc(self.buildEntry)
		self.l.setItemHeight(36)
		self.l.setItemWidth(36)
		self.spacing = applySkinFactor(10)
		self.orientations = {"orHorizontal": eListbox.orHorizontal, "orVertical": eListbox.orVertical}
		self.orientation = eListbox.orHorizontal
		self.alignment = "left"
		self.pixmaps = {}

	def onContainerShown(self):
		for x, val in self.sources.items():
			if self.constructButtonSequence not in val.onChanged:
				val.onChanged.append(self.constructButtonSequence)
		self.l.setItemHeight(self.instance.size().height())
		self.l.setItemWidth(self.instance.size().width())
		self.constructButtonSequence()

	GUI_WIDGET = eListbox

	def updateAddon(self, sequence):
		lList = []
		lList.append((sequence,))
		self.l.setList(lList)

	def buildEntry(self, sequence):
		xPos = self.instance.size().width() if self.alignment == "right" else 0
		yPos = 0

		res = [None]

		for x in sequence:
			if x in self.pixmaps:
				pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, self.pixmaps[x]))
				if pic:
					pixdSize = pic.size()
					pixdWidth = pixdSize.width()
					pixdHeight = pixdSize.height()
					picXPos = (xPos - pixdWidth) if self.alignment == "right" else xPos
					res.append(MultiContentEntryPixmapAlphaBlend(
						pos=(picXPos, yPos),
						size=(pixdWidth, pixdHeight),
						png=pic,
						backcolor=None, backcolor_sel=None, flags=BT_ALIGN_CENTER))
					if self.alignment == "right":
						xPos -= pixdWidth + self.spacing
					else:
						xPos += pixdWidth + self.spacing
		return res

	def postWidgetCreate(self, instance):
		instance.setSelectionEnable(False)
		instance.setContent(self.l)
		instance.allowNativeKeys(False)

	def constructButtonSequence(self):
		sequence = []
		for x, val in self.sources.items():
			if (isinstance(val, Boolean) and val.boolean) or (isinstance(val, StaticText) and val.text):
				if x not in sequence:
					sequence.append(x)

		self.updateAddon(sequence)

	def applySkin(self, desktop, parent):
		attribs = []
		for (attrib, value) in self.skinAttributes[:]:
			if attrib == "pixmaps":
				self.pixmaps = {k: v for k, v in (item.split(':') for item in value.split(','))}
			elif attrib == "spacing":
				self.spacing = self.parseScale(value)
			elif attrib == "alignment":
				self.alignment = value
			elif attrib == "orientation":
				self.orientation = self.orientations.get(value, self.orientations["orHorizontal"])
				if self.orientation == eListbox.orHorizontal:
					self.instance.setOrientation(eListbox.orVertical)
					self.l.setOrientation(eListbox.orVertical)
				else:
					self.instance.setOrientation(eListbox.orHorizontal)
					self.l.setOrientation(eListbox.orHorizontal)
			else:
				attribs.append((attrib, value))
		self.skinAttributes = attribs
		return GUIAddon.applySkin(self, desktop, parent)

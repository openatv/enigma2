from enigma import eListboxPythonMultiContent, gFont

from Components.Converter.StringList import StringList


class TemplatedMultiContent(StringList):
	"""Turns a python tuple list into a multi-content list which can be used in a listbox renderer."""

	def __init__(self, args):
		StringList.__init__(self, args)
		from enigma import BT_HALIGN_CENTER, BT_HALIGN_LEFT, BT_HALIGN_RIGHT, BT_KEEP_ASPECT_RATIO, BT_SCALE, BT_VALIGN_BOTTOM, BT_VALIGN_CENTER, BT_VALIGN_TOP, RADIUS_TOP_LEFT, RADIUS_TOP_RIGHT, RADIUS_TOP, RADIUS_BOTTOM_LEFT, RADIUS_BOTTOM_RIGHT, RADIUS_BOTTOM, RADIUS_LEFT, RADIUS_RIGHT, RADIUS_ALL, RT_BLEND, RT_ELLIPSIS, RT_HALIGN_CENTER, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_BOTTOM, RT_VALIGN_CENTER, RT_VALIGN_TOP, RT_WRAP, gFont  # noqa: F401
		from skin import getSkinFactor, parseFont  # noqa: F401
		from Components.MultiContent import MultiContentEntryLinearGradient, MultiContentEntryLinearGradientAlphaBlend, MultiContentEntryPixmap, MultiContentEntryPixmapAlphaBlend, MultiContentEntryPixmapAlphaTest, MultiContentEntryProgress, MultiContentEntryProgressPixmap, MultiContentEntryRectangle, MultiContentEntryText, MultiContentTemplateColor  # noqa: F401
		f = getSkinFactor()  # This is needed for special OpenViX skins using f in the template.
		loc = locals()
		del loc["self"]  # Cleanup locals a bit.
		del loc["args"]
		self.activeStyle = None
		self.template = eval(args, {}, loc)
		self.scale = None
		if "template" in self.template or "templates" in self.template:
			if "template" in self.template or "default" in self.template["templates"]:
				if "template" not in self.template:  # Default template can be ["template"] or ["templates"]["default"].
					self.template["itemSize"] = self.template["templates"]["default"][0]
					self.template["template"] = self.template["templates"]["default"][1]
				if "fonts" not in self.template:
					print("[TemplatedMultiContent] Error: All templates must include a 'fonts' entry!")
				if "itemHeight" not in self.template and "itemSize" not in self.template:
					print("[TemplatedMultiContent] Error: All 'template' entries must include an 'itemHeight' or 'itemSize' entry!")
			else:
				print("[TemplatedMultiContent] Error: All 'templates' must include a 'default' template!")
		else:
			print("[TemplatedMultiContent] Error: All TemplatedMultiContent converters must include either a 'template' or 'templates' entry!")

	def changed(self, what):
		def setTemplate():
			def scaleTemplate(template, itemWidth, itemHeight):
				scaleFactorVertical = self.scale[1][0] / self.scale[1][1]
				scaleFactorHorizontal = self.scale[0][0] / self.scale[0][1]
				itemWidth = int(itemWidth * scaleFactorHorizontal)
				itemHeight = int(itemHeight * scaleFactorVertical)
				scaledTemplate = []
				fonts = []
				for font in self.template["fonts"]:
					fonts.append(gFont(font.family, int(font.pointSize * scaleFactorVertical)))
				for content in template:
					elements = list(content)
					elements[1] = int(elements[1] * scaleFactorVertical)
					elements[2] = int(elements[2] * scaleFactorHorizontal)
					elements[3] = int(elements[3] * scaleFactorVertical)
					elements[4] = int(elements[4] * scaleFactorHorizontal)
					scaledTemplate.append(tuple(elements))
				return scaledTemplate, itemWidth, itemHeight, fonts

			if self.source:
				style = self.source.style
				if style == self.activeStyle:
					return
				templates = self.template.get("templates")  # If skin defined "templates", that means that it defines multiple styles in a dictionary but template should still be a default.
				template = self.template.get("template")
				if "itemHeight" in self.template:
					itemHeight = self.template["itemHeight"]
					itemWidth = itemHeight
				if "itemWidth" in self.template:
					itemWidth = self.template["itemWidth"]
				if "itemSize" in self.template:
					itemWidth = self.template["itemSize"]
					itemHeight = itemWidth
				selectionEnabled = self.template.get("selectionEnabled", None)
				scrollbarMode = self.template.get("scrollbarMode", None)
				if templates and style and style in templates:  # If we have a custom style defined in the source, and different templates in the skin, look the template up.
					template = templates[style][1]
					if isinstance(templates[style][0], tuple):
						itemWidth = templates[style][0][0]
						itemHeight = templates[style][0][1]
					else:
						itemWidth = templates[style][0]
						itemHeight = itemWidth
					if len(templates[style]) > 2:
						selectionEnabled = templates[style][2]
					if len(templates[style]) > 3:
						scrollbarMode = templates[style][3]
				if self.scale:
					template, itemWidth, itemHeight, fonts = scaleTemplate(template, itemWidth, itemHeight)
					for index, font in enumerate(fonts):
						self.content.setFont(index, font)
				self.content.setTemplate(template)
				self.content.setItemWidth(int(itemWidth))
				self.content.setItemHeight(int(itemHeight))
				if selectionEnabled is not None:
					self.selectionEnabled = selectionEnabled
				if scrollbarMode is not None:
					self.scrollbarMode = scrollbarMode
				self.activeStyle = style

		if not self.content:
			self.content = eListboxPythonMultiContent()
			for index, font in enumerate(self.template["fonts"]):  # Setup fonts (also given by source).
				self.content.setFont(index, font)
		if what[0] == self.CHANGED_SPECIFIC and what[1] == "style" and self.scale is not None:  # If only template changed, don't reload list.
			pass
		elif self.source:
			if self.scale is None and self.downstream_elements:
				listBoxRenderer = self.downstream_elements[0]
				if str(listBoxRenderer.__class__.__name__) == "Listbox":
					if hasattr(listBoxRenderer, "scale"):
						scale = listBoxRenderer.scale
						if scale and (scale[0][0] != scale[0][1] or scale[1][0] != scale[1][1]):
							self.scale = scale
							self.activeStyle = None
			try:
				contentList = []
				sourceList = self.source.list
				for item in range(len(sourceList)):
					if not isinstance(sourceList[item], (list, tuple)):
						contentList.append((sourceList[item],))
					else:
						contentList.append(sourceList[item])
			except Exception as error:
				print(f"[TemplatedMultiContent] Error: {error}.")
				contentList = self.source.list
			self.content.setList(contentList)
		setTemplate()
		self.downstream_elements.changed(what)

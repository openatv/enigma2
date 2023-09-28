from Components.Converter.StringList import StringList


class TemplatedMultiContent(StringList):
	"""Turns a python tuple list into a multi-content list which can be used in a listbox renderer."""

	def __init__(self, args):
		StringList.__init__(self, args)
		from enigma import BT_HALIGN_CENTER, BT_HALIGN_LEFT, BT_HALIGN_RIGHT, BT_KEEP_ASPECT_RATIO, BT_SCALE, BT_VALIGN_BOTTOM, BT_VALIGN_CENTER, BT_VALIGN_TOP, RADIUS_TOP_LEFT, RADIUS_TOP_RIGHT, RADIUS_TOP, RADIUS_BOTTOM_LEFT, RADIUS_BOTTOM_RIGHT, RADIUS_BOTTOM, RADIUS_LEFT, RADIUS_RIGHT, RADIUS_ALL, RT_BLEND, RT_ELLIPSIS, RT_HALIGN_CENTER, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_BOTTOM, RT_VALIGN_CENTER, RT_VALIGN_TOP, RT_WRAP, gFont
		from skin import getSkinFactor, parseFont
		from Components.MultiContent import MultiContentEntryLinearGradient, MultiContentEntryLinearGradientAlphaBlend, MultiContentEntryPixmap, MultiContentEntryPixmapAlphaBlend, MultiContentEntryPixmapAlphaTest, MultiContentEntryProgress, MultiContentEntryProgressPixmap, MultiContentEntryRectangle, MultiContentEntryText, MultiContentTemplateColor
		f = getSkinFactor()  # This is needed for special OpenViX skins using f in the template.
		loc = locals()
		del loc["self"]  # Cleanup locals a bit.
		del loc["args"]
		self.active_style = None
		self.template = eval(args, {}, loc)
		self.scale = None
		assert "fonts" in self.template, "templates must include a 'fonts' entry"
		assert "itemHeight" in self.template or "itemSize" in self.template, "templates must include an 'itemHeight' or 'itemSize' entry"
		assert "template" in self.template or "templates" in self.template, "templates must include a 'template' or 'templates' entry"
		assert "template" in self.template or "default" in self.template["templates"], "templates must include a 'default' template"  # We need to have a default template.
		if "template" not in self.template:  # Default template can be ["template"] or ["templates"]["default"].
			self.template["template"] = self.template["templates"]["default"][1]
			self.template["itemSize"] = self.template["template"][0]

	def changed(self, what):
		if not self.content:
			from enigma import eListboxPythonMultiContent
			self.content = eListboxPythonMultiContent()
			for index, font in enumerate(self.template["fonts"]):  # Setup fonts (also given by source).
				self.content.setFont(index, font)
		if what[0] == self.CHANGED_SPECIFIC and what[1] == "style":  # If only template changed, don't reload list.
			if self.downstream_elements:
				listBoxRenderer = self.downstream_elements[0]
				if str(listBoxRenderer.__class__.__name__) == "Listbox":
					if hasattr(listBoxRenderer, "scale"):
						scale = listBoxRenderer.scale
						if scale and (scale[0][0] != scale[0][1] or scale[1][0] != scale[1][1]):
							self.scale = scale
							self.active_style = None
			pass
		elif self.source:
			try:
				tmp = []
				src = self.source.list
				for x in range(len(src)):
					if not isinstance(src[x], (list, tuple)):
						tmp.append((src[x],))
					else:
						tmp.append(src[x])
			except Exception as error:
				print("[TemplatedMultiContent] Error: %s." % error)
				tmp = self.source.list
			self.content.setList(tmp)
		self.setTemplate()
		self.downstream_elements.changed(what)

	def scaleTemplate(self, template, itemWidth, itemHeight):
		from enigma import gFont
		print("[TemplatedMultiContent] DEBUG: Scale template.")
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
		return scaledTemplate, itemHeight, itemWidth, fonts

	def setTemplate(self):
		if self.source:
			style = self.source.style
			if style == self.active_style:
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
				template, itemWidth, itemHeight, fonts = self.scaleTemplate(template, itemWidth, itemHeight)
				for index, font in enumerate(fonts):
					self.content.setFont(index, font)
			self.content.setTemplate(template)
			self.content.setItemWidth(int(itemWidth))
			self.content.setItemHeight(int(itemHeight))
			if selectionEnabled is not None:
				self.selectionEnabled = selectionEnabled
			if scrollbarMode is not None:
				self.scrollbarMode = scrollbarMode
			self.active_style = style

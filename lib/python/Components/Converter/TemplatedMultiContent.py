from Components.Converter.StringList import StringList


class TemplatedMultiContent(StringList):
	"""Turns a python tuple list into a multi-content list which can be used in a listbox renderer."""

	def __init__(self, args):
		StringList.__init__(self, args)
		from enigma import BT_HALIGN_CENTER, BT_HALIGN_LEFT, BT_HALIGN_RIGHT, BT_KEEP_ASPECT_RATIO, BT_SCALE, BT_VALIGN_BOTTOM, BT_VALIGN_CENTER, BT_VALIGN_TOP, RT_HALIGN_CENTER, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_BOTTOM, RT_VALIGN_CENTER, RT_VALIGN_TOP, RT_WRAP, gFont
		from skin import getSkinFactor, parseFont
		from Components.MultiContent import MultiContentEntryPixmap, MultiContentEntryPixmapAlphaBlend, MultiContentEntryPixmapAlphaTest, MultiContentEntryProgress, MultiContentEntryProgressPixmap, MultiContentEntryText, MultiContentTemplateColor
		f = getSkinFactor()  # This is needed for special OpenViX skins using f in the template.
		loc = locals()
		del loc["self"]  # Cleanup locals a bit.
		del loc["args"]
		self.active_style = None
		self.template = eval(args, {}, loc)
		self.scale = None
		assert "fonts" in self.template, "templates must include a 'fonts' entry"
		assert "itemHeight" in self.template, "templates must include an 'itemHeight' entry"
		assert "template" in self.template or "templates" in self.template, "templates must include a 'template' or 'templates' entry"
		assert "template" in self.template or "default" in self.template["templates"], "templates must include a 'default' template"  # We need to have a default template.
		if "template" not in self.template:  # Default template can be ["template"] or ["templates"]["default"].
			self.template["template"] = self.template["templates"]["default"][1]
			self.template["itemHeight"] = self.template["template"][0]

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

	def scaleTemplate(self, template, itemheight):
		from enigma import gFont
		print("[TemplatedMultiContent] Scale template")
		scaleFactorVertical = self.scale[1][0] / self.scale[1][1]
		scaleFactorHorizontal = self.scale[0][0] / self.scale[0][1]
		itemheight = int(itemheight * scaleFactorVertical)
		scaledtemplate = []
		fonts = []
		for font in self.template["fonts"]:
			fonts.append(gFont(font.family, int(font.pointSize * scaleFactorVertical)))
		for content in template:
			elments = list(content)
			elments[1] = int(elments[1] * scaleFactorVertical)
			elments[2] = int(elments[2] * scaleFactorHorizontal)
			elments[3] = int(elments[3] * scaleFactorVertical)
			elments[4] = int(elments[4] * scaleFactorHorizontal)
			scaledtemplate.append(tuple(elments))
		return scaledtemplate, itemheight, fonts

	def setTemplate(self):
		if self.source:
			style = self.source.style
			if style == self.active_style:
				return
			templates = self.template.get("templates")  # If skin defined "templates", that means that it defines multiple styles in a dict. template should still be a default.
			template = self.template.get("template")
			itemheight = self.template["itemHeight"]
			selectionEnabled = self.template.get("selectionEnabled", True)
			scrollbarMode = self.template.get("scrollbarMode", "showOnDemand")
			if templates and style and style in templates:  # If we have a custom style defined in the source, and different templates in the skin, look it up
				template = templates[style][1]
				itemheight = templates[style][0]
				if len(templates[style]) > 2:
					selectionEnabled = templates[style][2]
				if len(templates[style]) > 3:
					scrollbarMode = templates[style][3]
			if self.scale:
				template, itemheight, fonts = self.scaleTemplate(template, itemheight)
				for index, font in enumerate(fonts):
					self.content.setFont(index, font)
			self.content.setTemplate(template)
			self.content.setItemHeight(int(itemheight))
			self.selectionEnabled = selectionEnabled
			self.scrollbarMode = scrollbarMode
			self.active_style = style

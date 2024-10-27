from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.ScrollLabel import ScrollLabel


class TextBox(Screen):
	def __init__(self, session, text="", title=None, skin_name=None, label=None):
		Screen.__init__(self, session)
		if isinstance(self.skinName, str):
			self.skinName = [self.skinName]
		if "TextBox" not in self.skinName:
			self.skinName.append("TextBox")
		if isinstance(skin_name, str):
			self.skinName.insert(0, skin_name)
		self.text = text
		self.label = "text"
		if isinstance(label, str):
			self.label = label
		self[self.label] = ScrollLabel(self.text)

		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions"],
				{
					"cancel": self.close,
					"ok": self.close,
					"up": self[self.label].pageUp,
					"down": self[self.label].pageDown,
				}, -1)

		if title:
			self.setTitle(title)

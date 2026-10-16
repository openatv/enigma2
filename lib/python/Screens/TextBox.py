from Components.ActionMap import HelpableActionMap
from Components.ScrollLabel import ScrollLabel
from Components.Sources.StaticText import StaticText
from Screens.Screen import Screen


class TextBox(Screen):
	def __init__(self, session, text="", title=None, widget=None, skinName=None, label=None, skin_name=None):
		Screen.__init__(self, session, enableHelp=True)
		if skinName is None and skin_name:
			skinName = skin_name
		if widget is None and label:
			widget = label
		self.skinName = [skinName]
		widget = widget if widget else "text"
		if "TextBox" not in self.skinName and widget == "text":
			self.skinName.append("TextBox")
		if title is None:
			title = _("Text Box")
		self.setTitle(title)
		self[widget] = ScrollLabel(text)
		self["key_red"] = StaticText(_("Close"))
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions", "NavigationActions"], {
			"ok": (self.close, _("Close the screen")),
			"cancel": (self.close, _("Close the screen")),
			"close": (self.keyCloseRecursive, _("Close the screen and exit all menus")),
			"red": (self.close, _("Close the screen")),
			"top": (self[widget].moveTop, _("Move to the first line / screen")),
			"pageUp": (self[widget].pageUp, _("Move up a screen")),
			"up": (self[widget].moveUp, _("Move up a line")),
			"down": (self[widget].moveDown, _("Move down a line")),
			"pageDown": (self[widget].pageDown, _("Move down a screen")),
			"bottom": (self[widget].moveBottom, _("Move to the last line / screen"))
		}, prio=0, description=f"{title} {_("Actions")}")

	def keyCloseRecursive(self):
		self.close(True)

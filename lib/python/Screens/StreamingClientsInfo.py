from Screen import Screen
from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.ScrollLabel import ScrollLabel
from Components.Converter.ClientsStreaming import ClientsStreaming
from Components.config import config
from Components.Sources.StaticText import StaticText
import skin


class StreamingClientsInfo(Screen):
	def __init__(self, session, menu_path = ""):
		Screen.__init__(self, session)
		screentitle = _("Streaming clients info")
		menu_path += screentitle
		if config.usage.show_menupath.value == 'large':
			title = menu_path
			self["menu_path_compressed"] = StaticText("")
		elif config.usage.show_menupath.value == 'small':
			title = screentitle
			self["menu_path_compressed"] = StaticText(menu_path + " >" if not menu_path.endswith(' / ') else menu_path[:-3] + " >" or "")
		else:
			title = screentitle
			self["menu_path_compressed"] = StaticText("")
		Screen.setTitle(self, title)
		clients = ClientsStreaming("INFO_RESOLVE")
		text = clients.getText()

		self["ScrollLabel"] = ScrollLabel(text or _("No stream clients"))

		self["key_red"] = Button(_("Close"))
		self["actions"] = ActionMap(["ColorActions", "SetupActions", "DirectionActions"],
			{
				"cancel": self.close,
				"ok": self.close,
				"red": self.close,
				"up": self["ScrollLabel"].pageUp,
				"down": self["ScrollLabel"].pageDown
			})
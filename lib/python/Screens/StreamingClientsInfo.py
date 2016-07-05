from Screen import Screen
from Components.ActionMap import ActionMap
from Components.ScrollLabel import ScrollLabel
from Components.Converter.ClientsStreaming import ClientsStreaming
from Components.config import config
import skin


class StreamingClientsInfo(Screen):
	def __init__(self, session, menu_path = ""):
		Screen.__init__(self, session)
		screentitle = _("Streaming clients info")
		menu_path += _(screentitle) or screentitle 
		if config.usage.show_menupath.value:
			title = menu_path
		else:
			title = _(screentitle)
		Screen.setTitle(self, title)
		clients = ClientsStreaming("INFO_RESOLVE")
		text = clients.getText()

		self["ScrollLabel"] = ScrollLabel(text or _("No stream clients"))

		self["actions"] = ActionMap(["ColorActions", "SetupActions", "DirectionActions"],
		{
			"cancel": self.close,
			"ok": self.close,
			"up": self["ScrollLabel"].pageUp,
			"down": self["ScrollLabel"].pageDown
		})
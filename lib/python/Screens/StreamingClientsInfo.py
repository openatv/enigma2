from Screen import Screen
from Components.ActionMap import ActionMap
from Components.ScrollLabel import ScrollLabel
from Components.Converter.ClientsStreaming import ClientsStreaming
import skin


class StreamingClientsInfo(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("StreamingClientsInfo"))
		clients = ClientsStreaming("INFO_RESOLVE")
		text = clients.getText()

		self["ScrollLabel"] = ScrollLabel(text)

		self["actions"] = ActionMap(["ColorActions", "SetupActions", "DirectionActions"],
		{
			"cancel": self.close,
			"ok": self.close,
			"up": self["ScrollLabel"].pageUp,
			"down": self["ScrollLabel"].pageDown
		})

from Screen import Screen
from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.ScrollLabel import ScrollLabel
from Components.Converter.ClientsStreaming import ClientsStreaming
from Components.config import config
from Components.Sources.StaticText import StaticText
from enigma import eTimer
import skin


class StreamingClientsInfo(Screen):
	def __init__(self, session, menu_path = ""):
		Screen.__init__(self, session)
		self.timer = eTimer()
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

		self["ScrollLabel"] = ScrollLabel()

		self["key_red"] = Button(_("Close"))
		self["actions"] = ActionMap(["ColorActions", "SetupActions", "DirectionActions"],
			{
				"cancel": self.exit,
				"ok": self.exit,
				"red": self.exit,
				"up": self["ScrollLabel"].pageUp,
				"down": self["ScrollLabel"].pageDown
			})

		self.onLayoutFinish.append(self.update_info)

	def exit(self):
		self.stop()
		self.close()

	def start(self):
		if self.update_info not in self.timer.callback:
			self.timer.callback.append(self.update_info)

	def stop(self):
		if self.update_info in self.timer.callback:
			self.timer.callback.remove(self.update_info)
		self.timer.stop()

	def update_info(self):
		clients = ClientsStreaming("INFO_RESOLVE")
		text = clients.getText()
		self["ScrollLabel"].setText(text or _("No clients streaming"))
		self.timer.startLongTimer(5)

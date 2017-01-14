from Screens.Screen import Screen
from Components.ActionMap import ActionMap, HelpableActionMap, NumberActionMap
from Components.Sources.List import List
from Components.config import config
from Screens.InfoBar import InfoBar
from Components.PluginComponent import plugins
from Plugins.Plugin import PluginDescriptor

class BoxPortal(Screen):
	skin = """
		<screen name="Extention" position="center,center" size="200,150" title="Extention">
		<widget source="menu" render="Listbox" zPosition="1" transparent="1" position="0,0" size="200,150" scrollbarMode="showOnDemand" >
			<convert type="StringList" />
		</widget>
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)

		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions"],
		{
			"ok": self.okbuttonClick,
			"back": self.exit,
			"cancel": self.exit,
			"red": self.exit,
			"green": self.exit,
			"yellow": self.exit,
			"blue": self.exit,
		})

		list = []
		if config.servicelist.lastmode.value == 'tv':
			list.append((_("Switch to Radio"), "radio", "", "50"))
		elif config.servicelist.lastmode.value == 'radio':
			list.append((_("Switch to TV"), "tv", "", "50"))
		list.append((_("Show Record Movies"), "pvr", "", "50"))
		list.append((_("Media Center"), "bmc", "", "50"))
		list.append((_("Media Player"), "mediaplayer", "", "50"))
		list.append((_("Teletext"), "teletext", "", "50"))
		self["menu"] = List(list)

	def okbuttonClick(self):
		selection = self["menu"].getCurrent()
		if selection is not None:
			if selection[1] == "radio":
				InfoBar.showRadio(InfoBar.instance)
				self.exit()
			if selection[1] == "tv":
				InfoBar.showTv(InfoBar.instance)
				self.exit()
			elif selection[1] == "pvr":
				InfoBar.showMovies(InfoBar.instance)
			elif selection[1] == "bmc":
				InfoBar.showMediaCenter(InfoBar.instance)
			elif selection[1] == "mediaplayer":
				InfoBar.showMediaPlayer(InfoBar.instance)
			elif selection[1] == "teletext":
				self.InfoBarTeletextPlugin()

	def InfoBarTeletextPlugin(self):
		self.teletext_plugin = None
		for p in plugins.getPlugins(PluginDescriptor.WHERE_TELETEXT):
			self.teletext_plugin = p

		self.teletext_plugin(session=self.session, service=self.session.nav.getCurrentService())

	def exit(self):
		self.close()

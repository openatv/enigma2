from Components.ActionMap import HelpableActionMap
from Components.config import config
from Components.PluginComponent import plugins
from Components.Sources.List import List
from Plugins.Plugin import PluginDescriptor
from Screens.InfoBar import InfoBar
from Screens.Screen import Screen


def isExtension_installed(pname):
	try:
		for plugin in plugins.getPlugins([PluginDescriptor.WHERE_PLUGINMENU, PluginDescriptor.WHERE_EXTENSIONSMENU]):
			if plugin.name == pname:
				return True
	except:
		return False


class BoxPortal(Screen):
	skin = """
		<screen name="Extension" position="center,center" size="250,200" title="Extension">
		<widget source="menu" render="Listbox" zPosition="1" transparent="1" position="0,0" size="250,200" scrollbarMode="showOnDemand" >
			<convert type="StringList" />
		</widget>
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)

		self["shortcuts"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions"],
		{
			"ok": self.okbuttonClick,
			"cancel": self.exit,
			"red": self.exit,
			"green": self.exit,
			"yellow": self.exit,
			"blue": self.exit,
		})

		list = []
		list.append((_("Show Record Movies"), "pvr", "", "50"))
		if config.servicelist.lastmode.value == 'tv':
			list.append((_("Switch to Radio"), "radio", "", "50"))
		elif config.servicelist.lastmode.value == 'radio':
			list.append((_("Switch to TV"), "tv", "", "50"))
		if isExtension_installed('Enhanced Movie Center'):
			list.append((_("Enhanced Movie Center"), "emc", "", "50"))
		if isExtension_installed('Media Center'):
			list.append((_("Media Center"), "bmc", "", "50"))
		if isExtension_installed(_("Media Player")):
			list.append((_("Media Player"), "MediaPlayer", "", "50"))
		if isExtension_installed('MediaStream'):
			list.append((_("Media Stream"), "MediaStream", "", "50"))
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
				InfoBar.showMoviePlayer(InfoBar.instance)
			elif selection[1] == "bmc":
				InfoBar.showMediaCenter(InfoBar.instance)
			elif selection[1] == "emc":
				try:
					from Plugins.Extensions.EnhancedMovieCenter.plugin import showMoviesNew
					open(showMoviesNew(InfoBar.instance))
				except Exception as e:
					print('[EMCPlayer] showMovies exception:\n' + str(e))
			elif selection[1] == "MediaStream":
				InfoBar.showPORTAL(InfoBar.instance)
			elif selection[1] == "MediaPlayer":
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

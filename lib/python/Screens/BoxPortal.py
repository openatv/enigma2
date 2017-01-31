from Screens.Screen import Screen
from Components.ActionMap import ActionMap, HelpableActionMap, NumberActionMap
from Components.Sources.List import List
from Components.config import config
from Screens.InfoBar import InfoBar
from Components.PluginComponent import plugins
from Plugins.Plugin import PluginDescriptor

from boxbranding import getBoxType

def isExtension_installed(pname):
	try:
		for plugin in plugins.getPlugins([PluginDescriptor.WHERE_PLUGINMENU,PluginDescriptor.WHERE_EXTENSIONSMENU]):
			if plugin.name == pname:
				return True
				break
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
		list.append((_("Show Record Movies"), "pvr", "", "50"))
		if config.servicelist.lastmode.value == 'tv':
			list.append((_("Switch to Radio"), "radio", "", "50"))
		elif config.servicelist.lastmode.value == 'radio':
			list.append((_("Switch to TV"), "tv", "", "50"))
		if isExtension_installed('Enhanced Movie Center'):
			list.append((_("Enhanced Movie Center"), "emc", "", "50"))
		if isExtension_installed('Media Center'):
			list.append((_("Media Center"), "bmc", "", "50"))
		if isExtension_installed(_("Media player")):
			list.append((_("Media Player"), "MediaPlayer", "", "50"))
		if isExtension_installed('MediaPortal'):
			list.append((_("Media Portal"), "MediaPortal", "", "50"))
		if isExtension_installed(_("AZPlay")):
			list.append((_("AZPlay"), "AZPlay", "", "50"))
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
			elif selection[1] == "MediaPortal":
				InfoBar.showPORTAL(InfoBar.instance)
			elif selection[1] == "MediaPlayer":
				InfoBar.showMediaPlayer(InfoBar.instance)
			elif selection[1] == "AZPlay":
				try:
					from Plugins.Extensions.AZPlay.plugin import main
					open(main(self.session))
				except Exception as e:
					print('[AZPlay] exception:\n' + str(e))					
			elif selection[1] == "teletext":
				self.InfoBarTeletextPlugin()

	def InfoBarTeletextPlugin(self):
		self.teletext_plugin = None
		for p in plugins.getPlugins(PluginDescriptor.WHERE_TELETEXT):
			self.teletext_plugin = p

		self.teletext_plugin(session=self.session, service=self.session.nav.getCurrentService())


	def exit(self):
		self.close()

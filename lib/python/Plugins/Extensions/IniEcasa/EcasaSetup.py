# GUI (Screens)
from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen

# GUI (Summary)
from Screens.Setup import SetupSummary

# GUI (Components)
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText

# Configuration
from Components.config import config, getConfigListEntry

class EcasaSetup(Screen, ConfigListScreen):
	skin = """<screen name="EcasaSetup" position="center,center" size="565,370">
		<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" alphatest="on" />
		<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		<widget source="key_blue" render="Label" position="420,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		<widget name="config" position="5,50" size="555,250" scrollbarMode="showOnDemand" />
		<ePixmap pixmap="skin_default/div-h.png" position="0,301" zPosition="1" size="565,2" />
		<widget source="help" render="Label" position="5,305" size="555,63" font="Regular;21" />
	</screen>"""

	def __init__(self, session, allowApiChange=False):
		Screen.__init__(self, session)

		# Summary
		self.setup_title = _("eCasa Setup")
		self.onChangedEntry = []

		l = [
			getConfigListEntry(_("Google Username"), config.plugins.ecasa.google_username, _("Username to use for authentication with google. Leave empty for unauthenticated use.")),
			getConfigListEntry(_("Google Password"), config.plugins.ecasa.google_password, _("Password to the google account.")),
			getConfigListEntry(_("Flickr API Key"), config.plugins.ecasa.flickr_api_key , _("API Key used to access Flickr. You can request one by logging in to Flickr from your computer.")),
			getConfigListEntry(_("Albums of"), config.plugins.ecasa.user, _("Show albums for this user by default. Use \"default\" for currently logged in user.")),
			getConfigListEntry(_("Search results"), config.plugins.ecasa.searchlimit, _("Number of search results to display at most.")),
			getConfigListEntry(_("Slideshow interval"), config.plugins.ecasa.slideshow_interval, _("Interval in slideshow before new picture is being shown.")),
			#getConfigListEntry(_("Cache directory"), config.plugins.ecasa.cache, _("Directory used to store cached images.")),
			getConfigListEntry(_("Cache size"), config.plugins.ecasa.cachesize, _("Size of local picture cache. If the maximum size is reached the cleanup process will delete the oldest existing pictured after the plugin was closed.")),
		]
		if allowApiChange:
			l.insert(
				0,
				getConfigListEntry(_("Connect to"), config.plugins.ecasa.last_backend, _("You can choose between Flickr and Picasa as site to use."))
			)
		ConfigListScreen.__init__(
			self,
			l,
			session=session,
			on_change=self.changed
		)
		def selectionChanged():
			if self["config"].current:
				self["config"].current[1].onDeselect(self.session)
			self["config"].current = self["config"].getCurrent()
			if self["config"].current:
				self["config"].current[1].onSelect(self.session)
			for x in self["config"].onSelectionChanged:
				x()
		self["config"].selectionChanged = selectionChanged
		self["config"].onSelectionChanged.append(self.updateHelp)

		# Initialize widgets
		self["key_green"] = StaticText(_("OK"))
		self["key_red"] = StaticText(_("Cancel"))
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText("")
		self["help"] = StaticText()

		# Define Actions
		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
			{
				"cancel": self.keyCancel,
				"save": self.keySave,
			}
		)

		# Trigger change
		self.changed()

		self.onLayoutFinish.append(self.setCustomTitle)

	def setCustomTitle(self):
		self.setTitle(_("eCasa Setup"))

	def updateHelp(self):
		cur = self["config"].getCurrent()
		if cur:
			self["help"].text = cur[2]

	def changed(self):
		for x in self.onChangedEntry:
			x()

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())

	def createSummary(self):
		return SetupSummary

	def close(self, *args, **kwargs):
		try: self["config"].getCurrent()[1].help_window.instance.hide()
		except AttributeError: pass
		Screen.close(self, *args, **kwargs)

from Components.ActionMap import HelpableActionMap
from Components.config import ConfigSelection, ConfigSubsection, config
from Components.Label import Label
from Components.International import international
from Components.Opkg import OpkgComponent
from Components.Pixmap import MultiPixmap
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Screens.HelpMenu import HelpableScreen, ShowRemoteControl
from Screens.MessageBox import MessageBox
from Screens.Processing import Processing
from Screens.Screen import Screen, ScreenSummary
from Screens.Setup import Setup
from Screens.Standby import QUIT_RESTART, TryQuitMainloop
from Tools.Directories import SCOPE_GUISKIN, resolveFilename
from Tools.LoadPixmap import LoadPixmap

config.locales = ConfigSubsection()
config.locales.packageLocales = ConfigSelection(default="P", choices=[
	("L", _("Packages and associated locales")),
	("P", _("Packaged locales only"))
])
config.locales.localesSortBy = ConfigSelection(default="2", choices=[
	("2", _("English name (Ascending)")),
	("20", _("English name (Descending)")),
	("1", _("Native name (Ascdending)")),
	("10", _("Native name (Descending)")),
	("3", _("Locale (Ascending)")),
	("30", _("Locale (Descending)"))
])


class LocaleSelection(Screen, HelpableScreen):
	LIST_FLAGICON = 0
	LIST_NATIVE = 1
	LIST_NAME = 2
	LIST_LOCALE = 3
	LIST_PACKAGE = 4
	LIST_STATICON = 5
	LIST_STATUS = 6
	MAX_LIST = 7

	PACK_AVAILABLE = 0
	PACK_INSTALLED = 1
	PACK_IN_USE = 2
	MAX_PACK = 3

	skin = """
	<screen name="LocaleSelection" position="center,center" size="1000,560" resolution="1280,720">
		<widget name="icons" position="0,0" size="30,27" pixmaps="icons/lock_off.png,icons/lock_on.png,icons/lock_error.png" alphatest="blend" />
		<widget source="locales" render="Listbox" position="10,10" size="e-20,442" enableWrapAround="1" scrollbarMode="showOnDemand">
			<convert type="TemplatedMultiContent">
				{
				"template":
					[
					MultiContentEntryPixmapAlphaBlend(pos = (5, 2), size = (60, 30), flags = BT_SCALE, png = 0),  # Flag.
					MultiContentEntryText(pos = (80, 0), size = (400, 34), font = 0, flags = RT_HALIGN_LEFT | RT_VALIGN_CENTER, text = 1),  # Language name (Native).
					MultiContentEntryText(pos = (490, 0), size = (330, 34), font = 0, flags = RT_HALIGN_LEFT | RT_VALIGN_CENTER, text = 2),  # Lanuage name (English).
					# MultiContentEntryText(pos = (830, 0), size = (90, 34), font = 0, flags = RT_HALIGN_LEFT | RT_VALIGN_CENTER, text = 3),  # Locale name.
					MultiContentEntryText(pos = (830, 0), size = (90, 34), font = 0, flags = RT_HALIGN_LEFT | RT_VALIGN_CENTER, text = 4),  # Package name.
					MultiContentEntryPixmapAlphaBlend(pos = (930, 3), size = (30, 27), flags = BT_SCALE, png = 5)  # Status icon.
					],
				"fonts": [parseFont("Regular;25")],
				"itemHeight": 34
				}
			</convert>
		</widget>
		<widget source="description" render="Label" position="10,e-85" size="e-20,25" font="Regular;20" valign="center" />
		<widget source="key_red" render="Label" position="10,e-50" size="140,40" backgroundColor="key_red" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="160,e-50" size="140,40" backgroundColor="key_green" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_yellow" render="Label" position="310,e-50" size="140,40" backgroundColor="key_yellow" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_menu" render="Label" position="e-450,e-50" size="140,40" backgroundColor="key_back" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_info" render="Label" position="e-300,e-50" size="140,40" backgroundColor="key_back" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-150,e-50" size="140,40" backgroundColor="key_back" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		self["key_menu"] = StaticText()
		self["key_info"] = StaticText()
		self["key_red"] = StaticText()
		self["key_green"] = StaticText()
		self["key_yellow"] = StaticText()
		self["icons"] = MultiPixmap()
		self["icons"].hide()
		self["locales"] = List(None, enableWrapAround=True)
		self["locales"].onSelectionChanged.append(self.selectionChanged)
		self["description"] = StaticText()
		self["selectionActions"] = HelpableActionMap(self, "LocaleSelectionActions", {
			"cancel": (self.keyCancel, _("Cancel any changes to the active locale/language and exit")),
			"close": (self.closeRecursive, _("Cancel any changes the active locale/language and exit all menus")),
			"save": (self.keySave, _("Apply any changes to the active locale/language and exit")),
			"select": (self.keySelect, _("Select the currently highlighted locale/language for the user interface")),
			"menu": (self.keySettings, _("Manage Locale/Language Selection settings")),
			"current": (self.keyCurrent, _("Jump to the currently active locale/language"))
		}, prio=0, description=_("Locale/Language Selection Actions"))
		self["manageActions"] = HelpableActionMap(self, "LocaleSelectionActions", {
			"manage": (self.keyManage, (_("Purge all but / Add / Delete the currently highlighted locale/language"), _("Purge all but the current and permanent locales/languages. Add the current locale/language if it is not installed. Delete the current locale/language if it is installed.")))
		}, prio=0, description=_("Locale/Language Selection Actions"))
		topItem = _("Move up to first line")
		topDesc = _("Move up to the first line in the list.")
		pageUpItem = _("Move up one screen")
		pageUpDesc = _("Move up one screen. Move to the first line of the screen if this is the first screen.")
		upItem = _("Move up one line")
		upDesc = _("Move up one line. Move to the bottom of the previous screen if this is the first line of the screen. Move to the last of the entry / list if this is the first line of the list.")
		downItem = _("Move down one line")
		downDesc = _("Move down one line. Move to the top of the next screen if this is the last line of the screen. Move to the first line of the list if this is the last line on the list.")
		pageDownItem = _("Move down one screen")
		pageDownDesc = _("Move down one screen. Move to the last line of the screen if this is the last screen.")
		bottomItem = _("Move down to last line")
		bottomDesc = _("Move down to the last line in the list.")
		self["navigationActions"] = HelpableActionMap(self, "NavigationActions", {
			"top": (self.keyTop, (topItem, topDesc)),
			"pageUp": (self.keyPageUp, (pageUpItem, pageUpDesc)),
			"up": (self.keyUp, (upItem, upDesc)),
			"first": (self.keyTop, (topItem, topDesc)),
			"last": (self.keyBottom, (bottomItem, bottomDesc)),
			"down": (self.keyDown, (downItem, downDesc)),
			"pageDown": (self.keyPageDown, (pageDownItem, pageDownDesc)),
			"bottom": (self.keyBottom, (bottomItem, bottomDesc))
		}, prio=0, description=_("List Navigation Actions"))
		self.initialLocale = international.getLocale()
		self.currentLocale = self.initialLocale
		self.inWizard = False
		self.opkgComponent = OpkgComponent()
		self.opkgComponent.addCallback(self.opkgComponentCallback)
		self.onLayoutFinish.append(self.layoutFinished)

	def selectionChanged(self):
		locale = self["locales"].getCurrent()[self.LIST_LOCALE]
		international.activateLocale(locale if locale in international.getLocaleList() else self.initialLocale, runCallbacks=False)
		self.updateText()

	def layoutFinished(self):
		while len(self["icons"].pixmaps) < self.MAX_PACK:
			self["icons"].pixmaps.append(None)
		self.updateLocaleList(self.initialLocale)
		self.moveToLocale(self.currentLocale)
		self.updateText()

	def updateLocaleList(self, inUseLoc=None):
		if inUseLoc is None:
			inUseLoc = self.currentLocale
		self.localeList = []
		for package in international.getAvailablePackages():
			installStatus = self.PACK_INSTALLED if package in international.getInstalledPackages() else self.PACK_AVAILABLE
			locales = international.packageToLocales(package)
			for locale in locales:
				language, country = international.splitLocale(locale)
				if len(locales) > 1 and f"{language}-{country.lower()}" in international.getAvailablePackages():
					continue
				png = LoadPixmap(resolveFilename(SCOPE_GUISKIN, f"countries/{country.lower()}.png"))
				if png is None:
					png = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "countries/missing.png"))
				name = f"{international.getLanguageName(language)} ({country})"
				icon = self["icons"].pixmaps[self.PACK_INSTALLED] if installStatus == self.PACK_INSTALLED else self["icons"].pixmaps[self.PACK_AVAILABLE]
				if locale == inUseLoc:
					status = self.PACK_IN_USE
					icon = self["icons"].pixmaps[self.PACK_IN_USE]
				else:
					status = installStatus
				self.localeList.append((png, international.getLanguageNative(language), name, locale, package, icon, status))
				if config.locales.packageLocales.value == "P":
					break
		if inUseLoc not in [x[self.LIST_LOCALE] for x in self.localeList]:
			language, country = international.splitLocale(inUseLoc)
			png = LoadPixmap(resolveFilename(SCOPE_GUISKIN, f"countries/{country.lower()}.png"))
			if png is None:
				png = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "countries/missing.png"))
			name = f"{international.getLanguageName(language)} ({country})"
			package = international.getPackage(inUseLoc)
			self.localeList.append((png, international.getLanguageNative(language), name, inUseLoc, package, self["icons"].pixmaps[self.PACK_IN_USE], self.PACK_IN_USE))
		sortBy = int(config.locales.localesSortBy.value)
		order = int(sortBy / 10) if sortBy > 9 else sortBy
		reverse = True if sortBy > 9 else False
		self.localeList = sorted(self.localeList, key=lambda x: x[order], reverse=reverse)
		self["locales"].updateList(self.localeList)

	def moveToLocale(self, locale):
		found = False
		for index, entry in enumerate(self.localeList):
			if entry[self.LIST_LOCALE] == locale:
				found = True
				break
		if not found:
			index = 0
		self["locales"].index = index  # This will trigger an onSelectionChanged event!

	def updateText(self):
		self.setTitle(_("Locale/Language Selection"))  # These strings are specified here to allow for all the strings to be translated in real time.
		self["key_red"].text = _("Cancel")
		self["key_green"].text = _("Save")
		self["key_menu"].text = _("MENU")
		self["key_info"].text = _("INFO")
		self["key_help"].text = _("HELP")
		current = self["locales"].getCurrent()
		locale = current[self.LIST_LOCALE]
		package = current[self.LIST_PACKAGE]
		status = current[self.LIST_STATUS]
		if international.splitPackage(package)[1] is None:
			detail = f"{international.getLanguageTranslated(locale)} - {package}"
			if status == self.PACK_AVAILABLE:
				self["description"].text = _("Press OK to install and use this language.  [%s]") % detail
			elif status == self.PACK_INSTALLED:
				self["description"].text = _("Press OK to use this language.  [%s]") % detail
			else:
				self["description"].text = _("This is the currently selected language.  [%s]") % detail
		else:
			detail = f"{international.getLanguageTranslated(locale)} ({international.getCountryTranslated(locale)}) {locale}"
			if status == self.PACK_AVAILABLE:
				self["description"].text = _("Press OK to install and use this locale.  [%s]") % detail
			elif status == self.PACK_INSTALLED:
				self["description"].text = _("Press OK to use this locale.  [%s]") % detail
			else:
				self["description"].text = _("This is the currently selected locale.  [%s]") % detail
		if package != international.getPackage(self.currentLocale):
			self["manageActions"].setEnabled(True)
			self["key_yellow"].text = _("Delete") if status == self.PACK_INSTALLED else _("Install")
		elif international.getPurgablePackages(self.currentLocale):
			self["manageActions"].setEnabled(True)
			self["key_yellow"].text = _("Purge")
		else:
			self["manageActions"].setEnabled(False)
			self["key_yellow"].text = ""

	def keyCancel(self, closeParameters=()):
		# def keyCancelCallback(answer):  # Code reserved should quit confirmation be required.
		# 	if not answer:
		# 		return
		# 	if not hasattr(self, "closeParameters"):
		# 		self.closeParameters = ()
		# 	self.close(*self.closeParameters)

		# if self["locales"].isChanged():  # Code reserved should quit confirmation be required.
		#	self.session.openWithCallback(keyCancelCallback, MessageBox, _("Really close without saving settings?"), default=False)
		# else:
		international.activateLocale(self.initialLocale, runCallbacks=False)
		self.close(*closeParameters)

	def closeRecursive(self):
		self.keyCancel((True,))

	def keySave(self):
		def keySaveCallback(answer):
			if answer:
				self.session.open(TryQuitMainloop, retvalue=QUIT_RESTART)
			self.close()

		config.osd.language.value = self.currentLocale
		config.osd.language.save()
		config.misc.locale.value = self.currentLocale
		language, country = international.splitLocale(self.currentLocale)
		config.misc.language.value = language
		config.misc.country.value = country
		config.misc.locale.save()
		config.misc.language.save()
		config.misc.country.save()
		international.activateLocale(self.currentLocale, runCallbacks=True)
		if not self.inWizard and self.currentLocale != self.initialLocale:
			self.session.openWithCallback(keySaveCallback, MessageBox, _("Restart GUI now to start using the new locale/language?"), default=True, type=MessageBox.TYPE_YESNO, windowTitle=_("Question"))
		else:
			self.close()

	def keySelect(self):
		current = self["locales"].getCurrent()
		self.currentLocale = current[self.LIST_LOCALE]
		status = current[self.LIST_STATUS]
		if status == self.PACK_AVAILABLE:
			self.keyManage()
		else:
			name = current[self.LIST_NAME]
			native = current[self.LIST_NATIVE]
			package = current[self.LIST_PACKAGE]
			self.updateLocaleList(self.currentLocale)
			if international.splitPackage(package)[1] is None:
				if status == self.PACK_AVAILABLE:
					self["description"].text = _("Language %s (%s) installed and selected.") % (native, name)
				elif status == self.PACK_INSTALLED:
					self["description"].text = _("Language %s (%s) selected.") % (native, name)
				else:
					self["description"].text = _("Language already selected.")
			else:
				if status == self.PACK_AVAILABLE:
					self["description"].text = _("Locale %s (%s) installed and selected.") % (native, name)
				elif status == self.PACK_INSTALLED:
					self["description"].text = _("Locale %s (%s) selected.") % (native, name)
				else:
					self["description"].text = _("Locale already selected.")
			if international.getPurgablePackages(self.currentLocale):
				self["manageActions"].setEnabled(True)
				self["key_yellow"].text = _("Purge")
			else:
				self["manageActions"].setEnabled(False)
				self["key_yellow"].text = ""

	def keySettings(self):
		def keySettingsCallback(status=None):
			self.updateLocaleList(self.currentLocale)
			self.moveToLocale(self.listEntry)
			self.updateText()

		self.listEntry = self["locales"].getCurrent()[self.LIST_LOCALE]
		self.session.openWithCallback(keySettingsCallback, LocaleSettings)

	def keyCurrent(self):
		self.moveToLocale(self.currentLocale)

	def keyManage(self):
		def processPurge(anwser):
			if anwser:
				print("[LocaleSelection] Purging all unused locales/languages...")
				self["description"].text = _("Purging all unused locales/languages...")
				Processing.instance.setDescription(_("Please wait while locales/languages are purged..."))
				Processing.instance.showProgress(endless=True)
				packages = international.getPurgablePackages(self.currentLocale)
				if packages:
					processDelete(packages)

		def processDelete(packages):
			opkgArguments = {
				"options": ["--autoremove", "--force-depends"],
				"arguments": [international.LOCALE_TEMPLATE % x for x in packages]
				# "testMode": True
			}
			self.opkgComponent.runCmd(self.opkgComponent.CMD_REMOVE, args=opkgArguments)

		def processDone(retVal, result):
			if status == self.PACK_AVAILABLE:
				if retVal:
					self.session.open(MessageBox, result, type=MessageBox.TYPE_ERROR, timeout=5, title=self.getTitle())
				else:
					international.activateLocale(locale, runCallbacks=False)
			elif status == self.PACK_INSTALLED:
				international.activateLocale(self.currentLocale, runCallbacks=False)
				if retVal:
					self.session.open(MessageBox, result, type=MessageBox.TYPE_ERROR, timeout=5, title=self.getTitle())
			else:
				if retVal:
					self.session.open(MessageBox, result, type=MessageBox.TYPE_ERROR, timeout=5, title=self.getTitle())

		current = self["locales"].getCurrent()
		status = current[self.LIST_STATUS]
		if current[self.LIST_LOCALE] == self.currentLocale:
			locale = current[self.LIST_LOCALE]
			permanent = ", ".join(sorted(international.getPermanentLocales(locale)))
			self.session.openWithCallback(processPurge, MessageBox, _("Do you want to purge all locales/languages except %s?") % permanent, default=False)
		else:
			name = current[self.LIST_NAME]
			native = current[self.LIST_NATIVE]
			package = current[self.LIST_PACKAGE]
			if status == self.PACK_INSTALLED:
				print(f"[LocaleSelection] Deleting locale/language {native} ({name})...")
				self["description"].text = _("Deleting %s (%s)...") % (native, name)
				Processing.instance.setDescription(_("Please wait while locales/language is deleted..."))
				Processing.instance.showProgress(endless=True)
				processDelete([package])
			elif status == self.PACK_AVAILABLE:
				print(f"[LocaleSelection] Installing locale/language {native} ({name})...")
				self["description"].text = _("Installing %s (%s)...") % (native, name)
				Processing.instance.setDescription(_("Please wait while locales/language is installed..."))
				Processing.instance.showProgress(endless=True)
				opkgArguments = {
					"options": ["--volatile-cache"],
					"arguments": [international.LOCALE_TEMPLATE % package]
					# "testMode": True
				}
				self.opkgComponent.runCmd(self.opkgComponent.CMD_INSTALL, args=opkgArguments)

	def opkgComponentCallback(self, event, parameter):
		print(f"[LocaleSelection] DEBUG: event={self.opkgComponent.getEventText(event)}, parameter={parameter}")
		if event == self.opkgComponent.EVENT_REMOVE_DONE:
			locales = "', '".join(parameter)
			international.updateInstalledPackages(parameter)
			print(f"[LocaleSelection] Locale/Language '{locales}' deleted.")
		elif event == self.opkgComponent.EVENT_CONFIGURING:
			international.updateInstalledPackages([parameter])
			print(f"[LocaleSelection] Locale/Language '{parameter}' installed.")
		if event in (self.opkgComponent.EVENT_DONE, self.opkgComponent.EVENT_ERROR):
			Processing.instance.hideProgress()
			self.updateLocaleList(self.currentLocale)
			self.updateText()

	def keyTop(self):
		self["locales"].top()

	def keyPageUp(self):
		self["locales"].pageUp()

	def keyUp(self):
		self["locales"].up()

	def keyDown(self):
		self["locales"].down()

	def keyPageDown(self):
		self["locales"].pageDown()

	def keyBottom(self):
		self["locales"].bottom()

	def run(self, justlocal=False):
		locale = self["locales"].getCurrent()[self.LIST_LOCALE]
		if locale != config.osd.language.value:
			config.osd.language.value = locale
			config.osd.language.save()
		if locale != config.misc.locale.value:
			config.misc.locale.value = locale
			language, country = international.splitLocale(locale)
			config.misc.language.value = language
			config.misc.country.value = country
			config.misc.locale.save()
			config.misc.language.save()
			config.misc.country.save()
		if justlocal:
			return
		international.activateLocale(locale, runCallbacks=True)

	def createSummary(self):
		return LocaleSelectionSummary


class LocaleSettings(Setup):
	def __init__(self, session):
		Setup.__init__(self, session=session, setup="Locale")


class LocaleSelectionSummary(ScreenSummary):
	def __init__(self, session, parent):
		ScreenSummary.__init__(self, session, parent=parent)
		self["native"] = StaticText("")
		self["name"] = StaticText("")
		self["locale"] = StaticText("")
		self["package"] = StaticText("")
		if self.addWatcher not in self.onShow:
			self.onShow.append(self.addWatcher)
		if self.removeWatcher not in self.onHide:
			self.onHide.append(self.removeWatcher)

	def addWatcher(self):
		if self.selectionChanged not in self.parent["locales"].onSelectionChanged:
			self.parent["locales"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def removeWatcher(self):
		if self.selectionChanged in self.parent["locales"].onSelectionChanged:
			self.parent["locales"].onSelectionChanged.remove(self.selectionChanged)

	def selectionChanged(self):
		current = self.parent["locales"].getCurrent()
		self["native"].text = current[self.parent.LIST_NATIVE]
		self["name"].text = current[self.parent.LIST_NAME]
		self["locale"].text = current[self.parent.LIST_LOCALE]
		self["package"].text = current[self.parent.LIST_PACKAGE]


class LocaleWizard(LocaleSelection, ShowRemoteControl):
	def __init__(self, session):
		LocaleSelection.__init__(self, session)
		ShowRemoteControl.__init__(self)
		self.inWizard = True
		saveText = _("Apply the currently highlighted locale/language and exit")
		cancelText = _("Cancel any changes to the active locale/language and exit")
		self["selectionActions"] = HelpableActionMap(self, "LocaleSelectionActions", {
			"select": (self.keySelect, saveText),
			"close": (self.keyCancel, cancelText),
			"cancel": (self.keyCancel, cancelText),
			"save": (self.keySelect, saveText),
		}, prio=0, description=_("Locale/Language Selection Actions"))
		self["manageActions"].setEnabled(False)
		self.onLayoutFinish.append(self.selectKeys)
		self["summarytext"] = StaticText()
		self["text"] = Label()

	def updateLocaleList(self, inUseLocale=None):
		if inUseLocale is None:
			inUseLocale = self.currentLocale
		self.localeList = []
		for package in international.getInstalledPackages():
			locales = international.packageToLocales(package)
			for locale in locales:
				country = international.splitLocale(locale)[1]
				png = LoadPixmap(resolveFilename(SCOPE_GUISKIN, f"countries/{country.lower()}.png"))
				if png is None:
					png = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "countries/missing.png"))
				name = f"{international.getLanguageName(locale)} ({country})"
				if locale == inUseLocale:
					status = self.PACK_IN_USE
					icon = self["icons"].pixmaps[self.PACK_IN_USE]
				else:
					status = self.PACK_INSTALLED
					icon = self["icons"].pixmaps[self.PACK_INSTALLED]
				self.localeList.append((png, international.getLanguageNative(locale), name, locale, package, icon, status))
				if config.locales.packageLocales.value == "P":
					break
		if inUseLocale not in [x[self.LIST_LOCALE] for x in self.localeList]:
			country = international.splitLocale(inUseLocale)[1]
			png = LoadPixmap(resolveFilename(SCOPE_GUISKIN, f"countries/{country.lower()}.png"))
			if png is None:
				png = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "countries/missing.png"))
			name = f"{international.getLanguageName(inUseLocale)} ({country})"
			package = international.getPackage(inUseLocale)
			self.localeList.append((png, international.getLanguageNative(inUseLocale), name, inUseLocale, package, self["icons"].pixmaps[self.PACK_IN_USE], self.PACK_IN_USE))
		sortBy = int(config.locales.localesSortBy.value)
		order = int(sortBy / 10) if sortBy > 9 else sortBy
		reverse = True if sortBy > 9 else False
		self.localeList = sorted(self.localeList, key=lambda x: x[order], reverse=reverse)
		self["locales"].updateList(self.localeList)

	def updateText(self):
		self.setTitle(_("Locale/Language Selection"))
		self["key_menu"].text = ""
		self["key_red"].text = _("Cancel")
		self["key_green"].text = _("Save")
		self["key_yellow"].text = ""
		self["key_help"].text = _("HELP")
		current = self["locales"].getCurrent()
		package = current[self.LIST_PACKAGE]
		locale = current[self.LIST_LOCALE]
		status = current[self.LIST_STATUS]
		if international.splitPackage(package)[1] is None:
			detail = f"{international.getLanguageTranslated(locale)} - {package}"
			if status == self.PACK_INSTALLED:
				self["description"].text = _("Press OK to use this language.  [%s]") % detail
			elif status == self.PACK_IN_USE:
				self["description"].text = _("This is the currently selected language.  [%s]") % detail
		else:
			detail = f"{international.getLanguageTranslated(locale)} ({international.getCountryTranslated(locale)}) {locale}"
			if status == self.PACK_INSTALLED:
				self["description"].text = _("Press OK to use this locale.  [%s]") % detail
			elif status == self.PACK_IN_USE:
				self["description"].text = _("This is the currently selected locale.  [%s]") % detail
		self["text"].setText(_("Use the UP and DOWN buttons to select your locale/language then press the OK button to continue."))
		self["summarytext"].setText(_("Use the UP and DOWN buttons to select your locale/language then press the OK button to continue."))

	def keySelect(self):
		current = self["locales"].getCurrent()
		self.currentLocale = current[self.LIST_LOCALE]
		self.updateLocaleList(self.currentLocale)
		self.keySave()

	def changed(self):
		self.run(justlocal=True)
		self.setText()

	def createSummary(self):
		return LocaleSelectionSummary

from enigma import eTimer

from Components.ActionMap import HelpableActionMap
from Components.config import config, ConfigSubsection, ConfigSelection
from Components.Label import Label
from Components.International import LANG_NAME, LANG_NATIVE, LANGUAGE_DATA, international
from Components.Pixmap import MultiPixmap
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Screens.HelpMenu import HelpableScreen, ShowRemoteControl
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen, ScreenSummary
from Screens.Setup import Setup
from Tools.Directories import SCOPE_CURRENT_SKIN, resolveFilename
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

inWizard = False


class LocaleSelection(Screen, HelpableScreen):
	LIST_FLAGICON = 0
	LIST_NATIVE = 1
	LIST_NAME = 2
	LIST_LOCALE = 3
	LIST_STATICON = 4
	LIST_STATUS = 5
	LIST_PACKAGE = 6
	MAX_LIST = 7

	PACK_INSTALLED = 0
	PACK_AVAILABLE = 1
	PACK_IN_USE = 2
	MAX_PACK = 3

	skin = """
	<screen name="LocaleSelection" position="center,center" size="1000,560" resolution="1280,720">
		<widget name="icons" position="0,0" size="30,27" pixmaps="icons/lock_on.png,icons/lock_off.png,icons/lock_error.png" alphatest="blend" />
		<widget source="locales" render="Listbox" position="10,10" size="e-20,442" enableWrapAround="1" scrollbarMode="showOnDemand">
			<convert type="TemplatedMultiContent">
				{
				"template":
					[
					MultiContentEntryPixmapAlphaBlend(pos = (5, 2), size = (60, 30), flags = BT_SCALE, png = 0),  # Flag.
					MultiContentEntryText(pos = (80, 0), size = (400, 34), font = 0, flags = RT_HALIGN_LEFT | RT_VALIGN_CENTER, text = 1),  # Language name (Native).
					MultiContentEntryText(pos = (490, 0), size = (330, 34), font = 0, flags = RT_HALIGN_LEFT | RT_VALIGN_CENTER, text = 2),  # Lanuage name (English).
					MultiContentEntryText(pos = (830, 0), size = (90, 34), font = 0, flags = RT_HALIGN_LEFT | RT_VALIGN_CENTER, text = 3),  # Locale.
					MultiContentEntryPixmapAlphaBlend(pos = (930, 3), size = (30, 27), flags = BT_SCALE, png = 4)  # Status icon.
					# MultiContentEntryText(pos = (0, 0), size = (0, 0), font = 0, flags = RT_HALIGN_LEFT | RT_VALIGN_CENTER, text = 5),  # Package name.
					],
				"fonts": [parseFont("MultiLingual;25")],
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
		<widget source="key_blue" render="Label" position="460,e-50" size="140,40" backgroundColor="key_blue" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_menu" render="Label" position="e-300,e-50" size="140,40" backgroundColor="key_back" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-150,e-50" size="140,40" backgroundColor="key_back" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		self["key_menu"] = StaticText(_("MENU"))
		self["key_red"] = StaticText()
		self["key_green"] = StaticText()
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self["icons"] = MultiPixmap()
		self["icons"].hide()
		self["locales"] = List(None, enableWrapAround=True)
		self["locales"].onSelectionChanged.append(self.selectionChanged)
		self["description"] = StaticText()
		self["selectionActions"] = HelpableActionMap(self, "LocaleSelectionActions", {
			"menu": (self.keySettings, _("Manage Locale/Language Selection settings")),
			"select": (self.keySelect, _("Select the currently highlighted locale/language to be used in the user interface")),
			"cleanup": (self.keyCleanup, _("Remove all locales/languages except the current, en, de and fr")),
			"close": (self.closeRecursive, _("Cancel any changes the active locale/language and exit all menus")),
			"cancel": (self.keyCancel, _("Cancel any changes to the active locale/language and exit")),
			"save": (self.keySave, _("Apply any changes to the active locale/langauge and exit"))
		}, prio=0, description=_("Locale/Language Selection Actions"))
		self["manageActions"] = HelpableActionMap(self, "LocaleSelectionActions", {
			"manage": (self.keyManage, _("Add / Delete the currently highlighted locale / language"))
		}, prio=0, description=_("Locale/Language Selection Actions"))
		topItem = _("Move up to first line")
		topDesc = _("Move up to the first line in the list.")
		pageUpItem = _("Move up one screen")
		pageUpDesc = _("Move up one screen.  Move to the first line of the screen if this is the first screen.")
		upItem = _("Move up one line")
		upDesc = _("Move up one line.  Move to the bottom of the previous screen if this is the first line of the screen.  Move to the last of the entry / list if this is the first line of the list.")
		downItem = _("Move down one line")
		downDesc = _("Move down one line.  Move to the top of the next screen if this is the last line of the screen.  Move to the first line of the list if this is the last line on the list.")
		pageDownItem = _("Move down one screen")
		pageDownDesc = _("Move down one screen.  Move to the last line of the screen if this is the last screen.")
		bottomItem = _("Move down to last line")
		bottomDesc = _("Move down to the last line in the list.")
		self["navigationActions"] = HelpableActionMap(self, "NavigationActions", {
			"top": (self.keyTop, (topItem, topDesc)),
			"pageUp": (self.keyPageUp, (pageUpItem, pageUpDesc)),
			"up": (self.keyUp, (upItem, upDesc)),
			"first": (self.keyTop, (topItem, topDesc)),
			"left": (self.keyPageUp, (pageUpItem, pageUpDesc)),
			"right": (self.keyPageDown, (pageDownItem, pageDownDesc)),
			"last": (self.keyBottom, (bottomItem, bottomDesc)),
			"down": (self.keyDown, (downItem, downDesc)),
			"pageDown": (self.keyPageDown, (pageDownItem, pageDownDesc)),
			"bottom": (self.keyBottom, (bottomItem, bottomDesc))
		}, prio=0, description=_("List Navigation Actions"))
		self.initialLocale = international.getLocale()
		self.currentLocale = self.initialLocale
		self.changedTimer = eTimer()
		self.changedTimer.callback.append(self.selectionChangedDone)
		self.selectTimer = eTimer()
		self.selectTimer.callback.append(self.selectDone)
		self.packageTimer = eTimer()
		self.packageTimer.callback.append(self.processPackage)
		self.packageDoneTimer = eTimer()
		self.packageDoneTimer.callback.append(self.processPackageDone)
		self.selectError = False
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		while len(self["icons"].pixmaps) < self.MAX_PACK:
			self["icons"].pixmaps.append(None) 
		self.updateLocaleList(self.initialLocale)
		self.moveToLocale(self.currentLocale)
		self.updateText(updateDescription=True)

	def updateLocaleList(self, inUseLoc=None):
		if inUseLoc is None:
			inUseLoc = self.currentLocale
		self.list = []
		for package in international.availablePackages:
			installStatus = self.PACK_INSTALLED if package in international.installedPackages else self.PACK_AVAILABLE
			locales = international.packageToLocales(package)
			for locale in locales:
				data = international.splitLocale(locale)
				if len(locales) > 1 and "%s-%s" % (data[0], data[1].lower()) in international.availablePackages:
					continue
				png = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "countries/%s.png" % data[1].lower()))
				if png is None:
					png = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "countries/missing.png"))
				name = "%s (%s)" % (LANGUAGE_DATA[data[0]][LANG_NAME], data[1])
				icon = self["icons"].pixmaps[self.PACK_INSTALLED] if installStatus == self.PACK_INSTALLED else self["icons"].pixmaps[self.PACK_AVAILABLE]
				if locale == inUseLoc:
					status = self.PACK_IN_USE
					icon = self["icons"].pixmaps[self.PACK_IN_USE]
				else:
					status = installStatus
				self.list.append((png, LANGUAGE_DATA[data[0]][LANG_NATIVE], name, locale, icon, status, package))
				if config.locales.packageLocales.value == "P":
					break
		if inUseLoc not in [x[self.LIST_LOCALE] for x in self.list]:
			data = international.splitLocale(inUseLoc)
			png = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "countries/%s.png" % data[1].lower()))
			if png is None:
				png = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "countries/missing.png"))
			name = "%s (%s)" % (LANGUAGE_DATA[data[0]][LANG_NAME], data[1])
			package = international.getPackage(inUseLoc)
			self.list.append((png, LANGUAGE_DATA[data[0]][LANG_NATIVE], name, inUseLoc, self["icons"].pixmaps[self.PACK_IN_USE], self.PACK_IN_USE, package))
		sortBy = int(config.locales.localesSortBy.value)
		order = int(sortBy / 10) if sortBy > 9 else sortBy
		reverse = True if sortBy > 9 else False
		self.list = sorted(self.list, key=lambda x: x[order], reverse=reverse)
		self["locales"].updateList(self.list)

	def selectionChanged(self):
		self.changedTimer.start(250)
		self.updateText(updateDescription=True)

	def selectionChangedDone(self):
		self.changedTimer.stop()
		locale = self["locales"].getCurrent()[self.LIST_LOCALE]
		if locale in international.localeList:
			international.activateLocale(locale, runCallbacks=False)
		else:
			international.activateLocale(self.initialLocale, runCallbacks=False)
		self.updateText(updateDescription=True)

	def updateText(self, updateDescription=True):
		Screen.setTitle(self, _("Locale/Language Selection"))
		self["key_red"].text = _("Cancel")
		self["key_green"].text = _("Save")
		self["key_blue"].text = _("Cleanup")
		self["key_menu"].text = _("MENU")
		self["key_help"].text = _("HELP")
		current = self["locales"].getCurrent()
		if current[self.LIST_PACKAGE] == international.getPackage(self.currentLocale):
			self["key_yellow"].text = ""
			self["manageActions"].setEnabled(False)
			if current[self.LIST_STATUS] == self.PACK_IN_USE:
				msg = _("This is the currently selected locale.")
			else:
				msg = _("Press OK to use this locale.")
		else:
			if international.splitPackage(current[self.LIST_PACKAGE])[1] is None:
				deleteText = _("Delete Lang")
				installText = _("Install Lang")
			else:
				deleteText = _("Delete Loc")
				installText = _("Install Loc")
			if current[self.LIST_STATUS] == self.PACK_INSTALLED:
				self["key_yellow"].text = deleteText
				msg = _("Press OK to use this locale.")
			else:
				self["key_yellow"].text = installText
				msg = _("Press OK to install and use this locale.")
			self["manageActions"].setEnabled(True)
		if updateDescription:
			self["description"].text = "%s  [%s (%s) %s]" % (msg, _(international.getLanguageName(current[self.LIST_LOCALE])), _(international.getCountryName(current[self.LIST_LOCALE])), current[self.LIST_LOCALE])

	def keySettings(self):
		self.listEntry = self["locales"].getCurrent()[self.LIST_LOCALE]
		self.session.openWithCallback(self.settingsClosed, LocaleSettings)

	def settingsClosed(self, status=None):
		self.updateLocaleList(self.currentLocale)
		self.moveToLocale(self.listEntry)
		self.updateText(updateDescription=True)

	def keySelect(self):
		self["selectionActions"].setEnabled(False)
		self["manageActions"].setEnabled(False)
		self.selectError = False
		if self["locales"].getCurrent()[self.LIST_STATUS] == self.PACK_AVAILABLE:
			self.keyManage()
			self.selectTimer.start(5000)
		else:
			self.selectDone()

	def selectDone(self):
		self.selectTimer.stop()
		current = self["locales"].getCurrent()
		if not self.selectError:
			self.currentLocale = current[self.LIST_LOCALE]
			self.updateLocaleList(self.currentLocale)
			self["key_yellow"].text = ""
			if current[self.LIST_STATUS] == self.PACK_AVAILABLE:
				self["description"].text = _("Locale %s (%s) has been installed and selected as the active locale.") % (current[self.LIST_NATIVE], current[self.LIST_NAME])
			elif current[self.LIST_STATUS] == self.PACK_INSTALLED:
				self["description"].text = _("Locale %s (%s) has been selected as the active locale.") % (current[self.LIST_NATIVE], current[self.LIST_NAME])
			else:
				self["description"].text = _("This is already the active locale.")
		self["selectionActions"].setEnabled(True)
		self["manageActions"].setEnabled(True)

	def keyManage(self):
		current = self["locales"].getCurrent()
		if current[self.LIST_LOCALE] != self.currentLocale:
			if current[self.LIST_STATUS] == self.PACK_INSTALLED:
				print("[LocaleSelection] Deleting locale/language %s (%s)..." % (current[self.LIST_NATIVE], current[self.LIST_NAME]))
				self["description"].text = _("Deleting %s (%s)...") % (current[self.LIST_NATIVE], current[self.LIST_NAME])
			elif current[self.LIST_STATUS] == self.PACK_AVAILABLE:
				print("[LocaleSelection] Installing locale/language %s (%s)..." % (current[self.LIST_NATIVE], current[self.LIST_NAME]))
				self["description"].text = _("Installing %s (%s)...") % (current[self.LIST_NATIVE], current[self.LIST_NAME])
			self.packageTimer.start(500)

	def processPackage(self):
		self.packageTimer.stop()
		current = self["locales"].getCurrent()
		if current[self.LIST_STATUS] == self.PACK_INSTALLED:
			international.activateLocale(self.currentLocale, runCallbacks=False)
			status = international.deleteLanguagePackages([current[self.LIST_PACKAGE]])
		elif current[self.LIST_STATUS] == self.PACK_AVAILABLE:
			status = international.installLanguagePackages([current[self.LIST_PACKAGE]])
			if status.startswith("Error:"):
				self.selectError = True
			else:
				international.activateLocale(self["locales"].getCurrent()[self.LIST_LOCALE], runCallbacks=False)
		else:
			status = _("No action required.")
		self["description"].text = status
		if not self.selectTimer.isActive():
			self.updateLocaleList(self.currentLocale)
		self.packageDoneTimer.start(750)

	def processPackageDone(self):
		self.packageDoneTimer.stop()
		self.updateText(updateDescription=False)

	def keyCleanup(self):
		curlang = config.osd.language.value
		self.session.openWithCallback(self.processCleanup, MessageBox, _("Do you want to delete all other languages?\nExcept English, French, German and your selection:\n\n") + _("%s") % (curlang), default=False)

	def processCleanup(self, anwser):
		if anwser:
			currentLang = config.osd.language.value
			status = international.removeLangs(currentLang=currentLang, excludeLangs=['de', 'en', 'fr'])
			self["description"].text = status
			self.packageDoneTimer.start(750)

	def moveToLocale(self, locale):
		found = False
		for index, entry in enumerate(self.list):
			if entry[self.LIST_LOCALE] == locale:
				found = True
				break
		if not found:
			index = 0
		self["locales"].index = index  # This will trigger an onSelectionChanged event!

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

	def keySave(self):
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
		self.close()

	def keyCancel(self, closeParameters=()):
		# if self["locales"].isChanged():
		#	self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"), default=False)
		# else:
		international.activateLocale(self.initialLocale, runCallbacks=False)
		self.close(*closeParameters)

	# def cancelConfirm(self, result):
	# 	if not result:
	# 		return
	# 	if not hasattr(self, "closeParameters"):
	# 		self.closeParameters = ()
	# 	self.close(*self.closeParameters)

	def closeRecursive(self):
		self.keyCancel((True,))

	def run(self, justlocal=False):
		# print("[LocaleSelection] updating locale...")
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
		international.activateLanguage(locale, runCallbacks=True)
		config.misc.languageselected.value = 0
		config.misc.languageselected.save()


class LocaleSettings(Setup):
	def __init__(self, session):
		Setup.__init__(self, session=session, setup="Locale")


class LocaleWizard(LocaleSelection, ShowRemoteControl):
	def __init__(self, session):
		LocaleSelection.__init__(self, session)
		ShowRemoteControl.__init__(self)
		global inWizard
		inWizard = True
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

	def updateLocaleList(self, inUseLoc=None):
		if inUseLoc is None:
			inUseLoc = self.currentLocale
		self.list = []
		for package in international.installedPackages:
			locales = international.packageToLocales(package)
			for locale in locales:
				data = international.splitLocale(locale)
				if len(locales) > 1 and "%s-%s" % (data[0], data[1].lower()) in international.availablePackages:  # Is this still needed?
					continue
				png = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "countries/%s.png" % data[1].lower()))
				if png is None:
					png = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "countries/missing.png"))
				name = "%s (%s)" % (LANGUAGE_DATA[data[0]][LANG_NAME], data[1])
				if locale == inUseLoc:
					status = self.PACK_IN_USE
					icon = self["icons"].pixmaps[self.PACK_IN_USE]
				else:
					status = self.PACK_INSTALLED
					icon = self["icons"].pixmaps[self.PACK_INSTALLED]
				self.list.append((png, LANGUAGE_DATA[data[0]][LANG_NATIVE], name, locale, icon, status, package))
				if config.locales.packageLocales.value == "P":
					break
		if inUseLoc not in [x[self.LIST_LOCALE] for x in self.list]:
			data = international.splitLocale(inUseLoc)
			png = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "countries/%s.png" % data[1].lower()))
			if png is None:
				png = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "countries/missing.png"))
			name = "%s (%s)" % (LANGUAGE_DATA[data[0]][LANG_NAME], data[1])
			package = international.getPackage(inUseLoc)
			self.list.append((png, LANGUAGE_DATA[data[0]][LANG_NATIVE], name, inUseLoc, self["icons"].pixmaps[self.PACK_IN_USE], self.PACK_IN_USE, package))
		sortBy = int(config.locales.localesSortBy.value)
		order = int(sortBy / 10) if sortBy > 9 else sortBy
		reverse = True if sortBy > 9 else False
		self.list = sorted(self.list, key=lambda x: x[order], reverse=reverse)
		self["locales"].updateList(self.list)

	def updateText(self, updateDescription=True):
		Screen.setTitle(self, _("Locale/Language Selection"))
		self["key_red"].text = _("Cancel")
		self["key_green"].text = _("Save")
		self["key_yellow"].text = ""
		self["key_menu"].text = ""
		self["key_help"].text = _("HELP")
		self["manageActions"].setEnabled(False)
		current = self["locales"].getCurrent()
		msg = _("This is the currently selected locale.") if current[self.LIST_STATUS] == self.PACK_IN_USE else _("Press OK to use this locale.")
		if updateDescription:
			self["description"].text = "%s  [%s (%s) %s]" % (msg, _(international.getLanguageName(current[self.LIST_LOCALE])), _(international.getCountryName(current[self.LIST_LOCALE])), current[self.LIST_LOCALE])
		self["text"].setText(_("Use the UP and DOWN buttons to select your locale/language then press the OK button to continue."))
		self["summarytext"].setText(_("Use the UP and DOWN buttons to select your locale/language then press the OK button to continue."))

	def keySelect(self):
		current = self["locales"].getCurrent()
		self.currentLocale = current[self.LIST_LOCALE]
		self.updateLocaleList(self.currentLocale)
		if current[self.LIST_STATUS] == self.PACK_INSTALLED:
			self["description"].text = _("Locale %s (%s) has been selected as the active locale.") % (current[self.LIST_NATIVE], current[self.LIST_NAME])
		else:
			self["description"].text = _("This is already the active locale.")
		self.keySave()

	def selectKeys(self):
		self.clearSelectedKeys()
		self.selectKey("UP")
		self.selectKey("DOWN")

	def changed(self):
		self.run(justlocal=True)
		self.setText()

	def createSummary(self):
		return ScreenSummary

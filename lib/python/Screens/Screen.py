from os.path import isdir, isfile

from enigma import eRCInput, eTimer, eWindow, getDesktop

from skin import GUI_SKIN_ID, applyAllAttributes, menus, screens, setups
from Components.ActionMap import ActionMap
from Components.config import config
from Components.GUIComponent import GUIComponent
from Components.Pixmap import Pixmap
from Components.Sources.Source import Source
from Components.Sources.StaticText import StaticText
from Tools.CList import CList
from Tools.Directories import SCOPE_GUISKIN, resolveFilename
from Tools.LoadPixmap import LoadPixmap


class Screen(dict):
	NO_SUSPEND = False  # Deprecated feature that may be needed for some plugins.
	SUSPEND_STOPS = True  # Deprecated feature that may be needed for some plugins.
	SUSPEND_PAUSES = True  # Deprecated feature that may be needed for some plugins.
	ALLOW_SUSPEND = True
	globalScreen = None

	def __init__(self, session, parent=None, mandatoryWidgets=None, enableHelp=False):
		dict.__init__(self)
		self.session = session
		self.parent = parent
		self.mandatoryWidgets = mandatoryWidgets
		className = self.__class__.__name__
		self.skinName = className
		self.ignoreWidgets = []
		self.onFirstExecBegin = []
		self.onExecBegin = []
		self.onExecEnd = []
		self.onClose = []
		self.onLayoutFinish = []
		self.onShown = []
		self.onShow = []
		self.onHide = []
		self.execing = False
		self.shown = True
		self.alreadyShown = False  # Already shown is false until the screen is really shown (after creation).
		self.renderer = []
		self.helpList = []  # In order to support screens *without* a help, we need the list in every screen. how ironic.
		self.closeOnNextExec = None
		self.standAlone = False  # Stand alone screens (for example web screens) don't care about having or not having focus.
		self.keyboardMode = None
		self.desktop = None
		self.instance = None
		self.summaries = CList()
		self.screenPath = ""  # This is the current screen path without the title.
		self.screenTitle = ""  # This is the current screen title without the path.
		self["ScreenPath"] = StaticText()
		self["Title"] = StaticText()
		self.screenImage = self.checkImage(className)  # This is the current screen image name.
		if self.screenImage:
			self["Image"] = Pixmap()
		if enableHelp:
			self["helpActions"] = ActionMap(["HelpActions"], {
				"displayHelp": self.showHelp
			}, prio=0)
			self["key_help"] = StaticText(_("HELP"))

	def __repr__(self):
		return str(type(self))

	def execBegin(self):
		self.activeComponents = []
		if self.closeOnNextExec is not None:
			closeOnNextExec = self.closeOnNextExec
			self.closeOnNextExec = None
			self.execing = True
			self.close(*closeOnNextExec)
		else:
			onFirstExecBegin = self.onFirstExecBegin
			self.onFirstExecBegin = []
			for method in self.onExecBegin + onFirstExecBegin:
				method()
				if not self.standAlone and self.session.current_dialog != self:
					return
			for value in list(self.values()) + self.renderer:
				value.execBegin()
				if not self.standAlone and self.session.current_dialog != self:
					return
				self.activeComponents.append(value)
			self.execing = True
			for method in self.onShown:
				method()

	def execEnd(self):
		activeComponents = self.activeComponents
		self.activeComponents = []
		for component in activeComponents:
			component.execEnd()
		self.execing = False
		for method in self.onExecEnd:
			method()

	def doClose(self):  # Never call this directly - it will be called from session!
		self.hide()
		for method in self.onClose:
			method()
		del self.helpList  # Fix up circular references.
		self.deleteGUIScreen()
		# First disconnect all renderers from their sources. We might split this out into
		# a "unskin"-call, but currently we destroy the screen afterwards anyway.
		for value in self.renderer:
			value.disconnectAll()  # Disconnect converter/sources and probably destroy them. Sources will not be destroyed.
		del self.session
		for (name, value) in list(self.items()):  # Use a copy of the self dictionary as we are changing the dictionary as we go!
			value.destroy()
			del self[name]
		self.renderer = []
		self.__dict__.clear()  # Really delete all elements now.

	def close(self, *retVal):
		if not self.execing:
			self.closeOnNextExec = retVal
		else:
			self.session.close(self, *retVal)

	def show(self):
		if not (self.shown and self.alreadyShown) and self.instance:
			self.shown = True
			self.alreadyShown = True
			self.instance.show()
			for method in self.onShow:
				method()
			for value in list(self.values()) + self.renderer:
				if isinstance(value, GUIComponent) or isinstance(value, Source):
					value.onShow()

	def hide(self):
		if self.shown and self.instance:
			self.shown = False
			self.instance.hide()
			for method in self.onHide:
				method()
			for value in list(self.values()) + self.renderer:
				if isinstance(value, GUIComponent) or isinstance(value, Source):
					value.onHide()

	def isAlreadyShown(self):  # Already shown is false until the screen is really shown (after creation).
		return self.alreadyShown

	def getStandAlone(self):  # Stand alone screens (for example web screens) don't care about having or not having focus.
		return self.standAlone

	def setStandAlone(self, value):  # Stand alone screens (for example web screens) don't care about having or not having focus.
		self.standAlone = value

	def setTitle(self, title, showPath=True):
		try:  # This protects against calls to setTitle() before being fully initialized like self.session is accessed *before* being defined.
			self.screenPath = ""
			if self.session and len(self.session.dialog_stack) > 1:
				self.screenPath = " > ".join(x[0].getTitle() for x in self.session.dialog_stack[1:])
			if self.instance:
				self.instance.setTitle(title)
			self.summaries.setTitle(title)
		except AttributeError:
			pass
		self.screenTitle = title
		if showPath and config.usage.showScreenPath.value == "large" and title:
			screenPath = ""
			screenTitle = f"{self.screenPath} > {title}" if self.screenPath else title
		elif showPath and config.usage.showScreenPath.value == "small":
			screenPath = f"{self.screenPath} >" if self.screenPath else ""
			screenTitle = title
		else:
			screenPath = ""
			screenTitle = title
		self["ScreenPath"].setText(screenPath)
		self["Title"].setText(screenTitle)

	def getTitle(self):
		return self.screenTitle

	title = property(getTitle, setTitle)

	def getScreenPath(self):
		return self.screenPath

	def checkImage(self, image, source=None):
		screenImage = None
		if image:
			images = {
				# "screen": screens,
				"menu": menus,
				"setup": setups
			}.get(source, screens)
			defaultImage = images.get("default", "")
			screenImage = images.get(image, defaultImage)
			if screenImage:
				screenImage = resolveFilename(SCOPE_GUISKIN, screenImage)
				msg = f"{'Default' if screenImage == defaultImage and image != 'default' else 'Specified'} {source if source else 'screen'} image for '{image}' is '{screenImage}'"
				if isfile(screenImage):
					print(f"[Screen] {msg}.")
				else:
					print(f"[Screen] Error: {msg} but this is not a file!")
					screenImage = None
		return screenImage

	def setImage(self, image, source=None):
		self.screenImage = self.checkImage(image, source=source)
		if self.screenImage and "Image" not in self:
			self["Image"] = Pixmap()

	def getImage(self):
		return self.screenImage

	image = property(getImage, setImage)

	def showHelp(self):
		def callHelpAction(*args):
			if args:
				(actionMap, context, action) = args
				actionMap.action(context, action)

		from Screens.HelpMenu import HelpMenu  # Import needs to be here because of a circular import.
		if hasattr(self, "secondInfoBarScreen"):
			if self.secondInfoBarScreen and self.secondInfoBarScreen.shown:
				self.secondInfoBarScreen.hide()
		self.session.openWithCallback(callHelpAction, HelpMenu, self.helpList)

	def setFocus(self, item):
		self.instance.setFocus(item.instance)

	def setKeyboardModeNone(self):
		rcinput = eRCInput.getInstance()
		rcinput.setKeyboardMode(rcinput.kmNone)

	def setKeyboardModeAscii(self):
		rcinput = eRCInput.getInstance()
		rcinput.setKeyboardMode(rcinput.kmAscii)

	def saveKeyboardMode(self):
		rcinput = eRCInput.getInstance()
		self.keyboardMode = rcinput.getKeyboardMode()

	def restoreKeyboardMode(self):
		rcinput = eRCInput.getInstance()
		if self.keyboardMode is not None:
			rcinput.setKeyboardMode(self.keyboardMode)

	def setDesktop(self, desktop):
		self.desktop = desktop

	def setAnimationMode(self, mode):
		if self.instance:
			self.instance.setAnimationMode(mode)

	def getRelatedScreen(self, name):
		match name:
			case "session":
				related = self.session.screen
			case "parent":
				related = self.parent
			case "global":
				related = self.globalScreen
			case _:
				related = None
		return related

	def callLater(self, method):
		self.__callLaterTimer = eTimer()
		self.__callLaterTimer.callback.append(method)
		self.__callLaterTimer.start(0, True)

	def applySkin(self):
		bounds = (getDesktop(GUI_SKIN_ID).size().width(), getDesktop(GUI_SKIN_ID).size().height())
		resolution = bounds
		zPosition = 0
		for (key, value) in self.skinAttributes:
			match key:
				case "ignoreWidgets":
					self.ignoreWidgets = [x.strip() for x in value.split(",")]
				case "resolution" | "baseResolution":
					resolution = tuple([int(x.strip()) for x in value.split(",")])
				case "zPosition":
					zPosition = int(value)
		if not self.instance:
			self.instance = eWindow(self.desktop, zPosition)
		if "title" not in self.skinAttributes and self.screenTitle:
			self.skinAttributes.append(("title", self.screenTitle))
		else:
			for attribute in self.skinAttributes:
				if attribute[0] == "title":
					self.setTitle(_(attribute[1]))  # This translation harvest is handled by the XML scanner.
		self.scale = ((bounds[0], resolution[0]), (bounds[1], resolution[1]))
		self.skinAttributes.sort(key=lambda a: {"position": 1}.get(a[0], 0))  # We need to make sure that certain attributes come last.
		applyAllAttributes(self.instance, self.desktop, self.skinAttributes, self.scale)
		self.createGUIScreen(self.instance, self.desktop)

	def createGUIScreen(self, parent, desktop, updateonly=False):
		for value in self.renderer:
			if isinstance(value, GUIComponent):
				if not updateonly:
					value.GUIcreate(parent)
				if not value.applySkin(desktop, self):
					print(f"[Screen] Warning: Skin is missing renderer '{value}' in {str(self)}.")
		for key in self:
			value = self[key]
			if isinstance(value, GUIComponent):
				if not updateonly:
					value.GUIcreate(parent)
				deprecated = value.deprecationInfo
				if value.applySkin(desktop, self):
					if deprecated:
						print(f"[Screen] WARNING: OBSOLETE COMPONENT '{key}' USED IN SKIN. USE '{deprecated[0]}' INSTEAD!")
						print(f"[Screen] OBSOLETE COMPONENT WILL BE REMOVED {deprecated[1]}, PLEASE UPDATE!")
				elif not deprecated and key not in self.ignoreWidgets:
					try:
						print(f"[Screen] Warning: Skin is missing element '{key}' in {str(self)} item {str(self[key])}.")
					except Exception:
						print(f"[Screen] Warning: Skin is missing element '{key}'.")
		for widget in self.additionalWidgets:
			if not updateonly:
				widget.instance = widget.widget(parent)
			applyAllAttributes(widget.instance, desktop, widget.skinAttributes, self.scale)
		if self.screenImage:
			screenImage = LoadPixmap(self.screenImage)
			self["Image"].instance.setPixmap(screenImage)
		for method in self.onLayoutFinish:
			if not isinstance(method, type(self.close)):
				exec(method, globals(), locals())
			else:
				method()

	def deleteGUIScreen(self):
		for (name, val) in list(self.items()):
			if isinstance(val, GUIComponent):
				val.GUIdelete()

	def createSummary(self):
		return None

	def addSummary(self, summary):
		if summary is not None:
			self.summaries.append(summary)

	def removeSummary(self, summary):
		if summary is not None:
			self.summaries.remove(summary)

	# These properties support legacy code that reaches into the internal variables of this class!
	#
	already_shown = property(isAlreadyShown)  # Used in CutListEditor/ui.py.
	stand_alone = property(getStandAlone, setStandAlone)  # Used in webinterface/src/WebScreens.py.


class ScreenSummary(Screen):
	skin = """
	<screen name="ScreenSummary" position="fill" flags="wfNoBorder">
		<widget source="global.CurrentTime" render="Label" position="0,0" size="e,20" font="Regular;16" halign="center" valign="center">
			<convert type="ClockToText">WithSeconds</convert>
		</widget>
		<widget source="Title" render="Label" position="0,25" size="e,45" font="Regular;18" halign="center" valign="center" />
	</screen>"""

	def __init__(self, session, parent):
		Screen.__init__(self, session, parent=parent)
		self["Title"] = StaticText(parent.getTitle())
		skinName = parent.skinName
		if not isinstance(skinName, list):
			skinName = [skinName]
		self.skinName = [f"{x}Summary" for x in skinName]
		className = self.__class__.__name__
		if className != "ScreenSummary" and className not in self.skinName:  # When a summary screen does not have the same name as the parent then add it to the list.
			self.skinName.append(className)
		self.skinName += [f"{x}_summary" for x in skinName]  # DEBUG: Old summary screens currently kept for compatibility.
		self.skinName.append("ScreenSummary")
		self.skin = parent.__dict__.get("skinSummary", self.skin)  # If parent has a "skinSummary" defined, use that as default.
		# skins = "', '".join(self.skinName)
		# print(f"[Screen] DEBUG: Skin names: '{skins}'.")
		# print(f"[Screen] DEBUG: Skin:\n{self.skin}")

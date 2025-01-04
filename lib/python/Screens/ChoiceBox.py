from Components.ActionMap import HelpableActionMap, HelpableNumberActionMap
from Components.config import ConfigSubsection, ConfigText, config
from Components.Label import Label
from Components.ChoiceList import ChoiceEntryComponent, ChoiceList
from Components.Sources.StaticText import StaticText
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen, ScreenSummary

config.misc.pluginlist = ConfigSubsection()
config.misc.pluginlist.eventinfoOrder = ConfigText(default="[]")
config.misc.pluginlist.extensionOrder = ConfigText(default="[]")
config.misc.pluginlist.fcBookmarksOrder = ConfigText(default=f"['{_("Storage Devices")}']")


class ChoiceBoxNew(Screen):
	def __init__(self, session, text="", choiceList=None, selection=0, buttonList=None, reorderConfig=None, allowCancel=True, skinName=None, windowTitle=None):
		Screen.__init__(self, session, enableHelp=True)
		self.setTitle(windowTitle if windowTitle else _("Choice Box"))
		self.skinName = ["ChoiceBox"]
		if skinName:
			if isinstance(skinName, str):
				self.skinName.insert(0, skinName)
			else:
				self.skinName = skinName + self.skinName
		choiceList = choiceList if choiceList else []
		if buttonList is None:
			buttonList = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "red", "green", "yellow", "blue", "text"] + (len(choiceList) - 14) * [""]
		else:
			buttonList = buttonList + (len(choiceList) - len(buttonList)) * [""]
		if reorderConfig:
			self.configOrder = getattr(config.misc.pluginlist, reorderConfig)
			if self.configOrder.value:
				prevList = [x for x in zip(choiceList, buttonList)]
				newList = []
				for button in eval(self.configOrder.value):
					for entry in prevList:
						if entry[0][0] == button:
							prevList.remove(entry)
							newList.append(entry)
				choiceList = [x for x in zip(*(newList + prevList))]
				choiceList, buttonList = choiceList[0], choiceList[1]
				number = 1
				newButtons = []
				for button in buttonList:
					if (not button or button.isdigit()) and number <= 10:
						newButtons.append(str(number % 10))
						number += 1
					else:
						newButtons.append(not button.isdigit() and button or "")
				buttonList = newButtons
		else:
			self.configOrder = None
		self.choiceList = []
		self.buttonMap = {}
		actionMethods = {
			"red": self.keyRed,
			"green": self.keyGreen,
			"yellow": self.keyYellow,
			"blue": self.keyBlue,
			"text": self.keyText
		}
		actions = {
			"ok": (self.keySelect, _("Select the current entry"))
		}
		for index, choice in enumerate(choiceList):
			button = str(buttonList[index])
			self.choiceList.append(ChoiceEntryComponent(key=button, text=choice))
			if button:
				self.buttonMap[button] = choiceList[index]
				actions[button] = (actionMethods.get(button, self.keyNumberGlobal), _("Select the %s entry") % button.upper())
		self["text"] = Label(text)
		self["list"] = ChoiceList(list=self.choiceList, selection=selection)
		self["actions"] = HelpableNumberActionMap(self, ["OkActions", "ColorActions", "TextActions", "NumberActions"], actions, prio=-1, description=_("Choice List Selection Actions"))  # Priority needs to be higher for instantiated versions of this screen.
		self["cancelAction"] = HelpableActionMap(self, ["OkCancelActions"], {
			"cancel": (self.keyCancel, _("Cancel the selection and exit"))
		}, prio=0, description=_("Choice List Actions"))
		self["cancelAction"].setEnabled(allowCancel)
		self["navigationActions"] = HelpableActionMap(self, ["NavigationActions"], {
			"top": (self.keyTop, _("Move to the first line / screen")),
			"pageUp": (self.keyPageUp, _("Move up a screen")),
			"up": (self.keyLineUp, _("Move up a line")),
			"down": (self.keyLineDown, _("Move down a line")),
			"pageDown": (self.keyPageDown, _("Move down a screen")),
			"bottom": (self.keyBottom, _("Move to the last line / screen"))
		}, prio=-1, description=_("Choice List Navigation Actions"))  # Priority needs to be higher for instantiated versions of this screen.
		self["navigationActions"].setEnabled(len(choiceList) > 1)
		self["moveActions"] = HelpableActionMap(self, ["PreviousNextActions", "MenuActions"], {
			"menu": (self.keyResetList, _("Reset the order of the entries")),
			"previous": (self.keyMoveItemUp, _("Move the current entry up")),
			"next": (self.keyMoveItemDown, _("Move the current entry down")),
		}, prio=0, description=_("Choice List Order Actions"))
		self["moveActions"].setEnabled(len(choiceList) > 1 and self.configOrder)
		self["summary_list"] = StaticText()  # Temporary hack to support old display skins.
		self["summary_selection"] = StaticText()  # Temporary hack to support old display skins.
		self.onLayoutFinish.append(self.layoutFinished)
		self.list = self.choiceList  # Support for old skins and plugins

	def layoutFinished(self):
		self["list"].enableAutoNavigation(False)  # Override list box navigation.

	def instantiateActionMap(self, active):
		if active:
			self["actions"].execBegin()
			self["navigationActions"].execBegin()
		else:
			self["actions"].execEnd()
			self["navigationActions"].execEnd()

	def keySelect(self):  # Run the currently selected entry.
		current = self["list"].getCurrent()
		if current:
			self.goEntry(current[0])

	def keyRed(self):  # Run a colored or labeled shortcut.
		self.goKey("red")

	def keyGreen(self):
		self.goKey("green")

	def keyYellow(self):
		self.goKey("yellow")

	def keyBlue(self):
		self.goKey("blue")

	def keyText(self):
		self.goKey("text")

	def keyNumberGlobal(self, number):  # Run a numbered shortcut.
		self.goKey(str(number))

	def goKey(self, key):  # Lookup a key in the buttonMap, then run it.
		if key in self.buttonMap:
			entry = self.buttonMap[key]
			self.goEntry(entry)

	def goEntry(self, entry):  # Run a specific entry.
		if entry and len(entry) > 3 and isinstance(entry[1], str) and entry[1] == "CALLFUNC":
			arg = entry[3]
			entry[2](arg)
		elif entry and len(entry) > 2 and isinstance(entry[1], str) and entry[1] == "CALLFUNC":
			entry[2](None)  # Should this be 'entry[2]()'?
		else:
			self.close(entry)

	def keyTop(self):
		self["list"].instance.goTop()

	def keyPageUp(self):
		self["list"].instance.goPageUp()

	def keyLineUp(self):
		self["list"].instance.goLineUp()

	def keyLineDown(self):
		self["list"].instance.goLineDown()

	def keyPageDown(self):
		self["list"].instance.goPageDown()

	def keyBottom(self):
		self["list"].instance.goBottom()

	def keyMoveItemUp(self):
		self.moveItem(-1)

	def keyMoveItemDown(self):
		self.moveItem(1)

	def moveItem(self, direction):
		currentIndex = self["list"].getSelectionIndex()
		swapIndex = (currentIndex + direction) % len(self.choiceList)
		if currentIndex == 0 and swapIndex != 1:
			self.choiceList = self.choiceList[1:] + [self.choiceList[0]]
		elif swapIndex == 0 and currentIndex != 1:
			self.choiceList = [self.choiceList[-1]] + self.choiceList[:-1]
		else:
			self.choiceList[currentIndex], self.choiceList[swapIndex] = self.choiceList[swapIndex], self.choiceList[currentIndex]
		self["list"].setList(self.choiceList)
		if direction == 1:
			self["list"].instance.goLineDown()
		else:
			self["list"].instance.goLineUp()
		self.configOrder.value = str([x[0][0] for x in self.choiceList])
		self.configOrder.save()

	def keyResetList(self):
		def keyResetListCallback(answer):
			if answer:
				self.configOrder.value = self.configOrder.default
				self.configOrder.save()

		self.session.openWithCallback(keyResetListCallback, MessageBox, _("Reset list order to the default list order?"), MessageBox.TYPE_YESNO, windowTitle=self.getTitle())

	def keyCancel(self):
		self.close(None)

	def autoResize(self):
		pass  # This method is very skin dependent.  Please use the "applet" tag in the skin screen to achieve the appropriate changes to the skin.

	def createSummary(self):
		return ChoiceBoxSummary


class ChoiceBoxSummary(ScreenSummary):
	def __init__(self, session, parent):
		ScreenSummary.__init__(self, session, parent=parent)
		self["text"] = StaticText(parent["text"].getText())
		self["entry"] = StaticText("")
		self["value"] = StaticText("")
		self.choiceList = []
		index = 0
		for item in self.parent["list"].getList():
			if item[0]:
				index += 1
				self.choiceList.append((index, item[0][0]))
			else:
				self.choiceList.append((0, None))
		if self.addWatcher not in self.onShow:
			self.onShow.append(self.addWatcher)
		if self.removeWatcher not in self.onHide:
			self.onHide.append(self.removeWatcher)

	def addWatcher(self):
		if self.selectionChanged not in self.parent["list"].onSelectionChanged:
			self.parent["list"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def removeWatcher(self):
		if self.selectionChanged in self.parent["list"].onSelectionChanged:
			self.parent["list"].onSelectionChanged.remove(self.selectionChanged)

	def selectionChanged(self):
		currentIndex = self.parent["list"].getCurrentIndex()
		choiceList = []
		for index, item in enumerate(self.choiceList):
			if item[0]:
				if index == currentIndex:
					choiceList.append(f"> {item[1]}")
					self["value"].setText(item[1])
					self.parent["summary_selection"].setText(item[1])  # Temporary hack to support old display skins.
				else:
					choiceList.append(f"{item[0]} {item[1]}")
		index = 0 if currentIndex < 2 else currentIndex - 1
		self["entry"].setText("\n".join(choiceList[index:]))
		self.parent["summary_list"].setText("\n".join(choiceList[index:]))  # Temporary hack to support old display skins.


class ChoiceBox(ChoiceBoxNew):
	def __init__(self, session, title="", list=None, keys=None, selection=0, skin_name=None, text="", reorderConfig="", windowTitle=None, allow_cancel=None, titlebartext=None, choiceList=None, buttonList=None, allowCancel=None, skinName=None):
		if title:
			# print(f"[ChoiceBox] Warning: Deprecated argument 'title' found with a value of '{title}', use 'text' and/or 'windowTitle' instead!")
			pos = title.find("\n")
			if pos == -1:
				windowTitle = title
			else:
				windowTitle = title[:pos]
				text = title[pos + 1:]
		self["windowtitle"] = StaticText(windowTitle)  # This is a hack to keep broken skins that do not use the "Title" widget working.
		if list is not None:
			# print(f"[ChoiceBox] Warning: Deprecated argument 'list' found , use 'choiceList' instead!")
			if choiceList is None:
				choiceList = list
		if keys is not None:
			# print(f"[ChoiceBox] Warning: Deprecated argument 'keys' found , use 'buttonList' instead!")
			if buttonList is None:
				buttonList = keys
		if skin_name is not None:
			# Used in InfoBarGenerics.py, MovieSelection.py, ChannelSelection.py, EventView.py.
			# /media/autofs/DATA/Enigma2/Plugins-Enigma2/werbezapper/src/WerbeZapper.py: ChoiceBox.__init__(self, session, title, list, keys, selection, skin_name)
			# print(f"[ChoiceBox] Warning: Deprecated argument 'skin_name' found with a value of '{skin_name}', use 'skinName' instead!")
			if skinName is None:
				skinName = skin_name
		if titlebartext is not None:
			# print(f"[ChoiceBox] Warning: Deprecated argument 'titlebartext' found with a value of '{titlebartext}', use 'windowTitle' instead!")
			if windowTitle is None:
				windowTitle = titlebartext
		if allow_cancel is not None:
			# print(f"[ChoiceBox] Warning: Deprecated argument 'allow_cancel' found with a value of '{allow_cancel}', use 'allowCancel' instead!")
			if allowCancel is None:
				allowCancel = allow_cancel
		if allowCancel is None:
			allowCancel = True
		ChoiceBoxNew.__init__(self, session, text=text, choiceList=choiceList, selection=selection, buttonList=buttonList, reorderConfig=reorderConfig, allowCancel=allowCancel, skinName=skinName, windowTitle=windowTitle)

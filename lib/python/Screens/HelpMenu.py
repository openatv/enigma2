from collections import defaultdict
from functools import cmp_to_key
from sys import maxsize

from enigma import eActionMap, eTimer

from keyids import KEYIDNAMES, KEYIDS
from Components.ActionMap import ActionMap, queryKeyBinding
from Components.config import config
from Components.InputDevice import remoteControl
from Components.Label import Label
from Components.Pixmap import MovingPixmap, Pixmap
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Screens.Screen import Screen
from Tools.LoadPixmap import LoadPixmap


class ShowRemoteControl:
	MAX_BUTTON_INDICATORS = 16

	class KeyIndicator:
		class KeyIndicatorPixmap(MovingPixmap):
			def __init__(self, activeYPos, pixmap):
				MovingPixmap.__init__(self)
				self.activeYPos = activeYPos
				self.pixmapName = pixmap

		def __init__(self, owner, activeYPos, pixmaps):
			self.pixmaps = []
			for yPos, pixmap in zip(activeYPos, pixmaps):
				indicatorPixmap = self.KeyIndicatorPixmap(yPos, pixmap)
				owner[pixmap] = indicatorPixmap
				self.pixmaps.append(indicatorPixmap)
			self.pixmaps.sort(key=lambda x: x.activeYPos)

		def moveTo(self, pos, rcPos, moveFrom=None, time=20):
			foundActive = False
			for index, pixmap in enumerate(self.pixmaps):
				fromX, fromY = pixmap.getPosition()
				if moveFrom:
					fromX, fromY = moveFrom.pixmaps[index].getPosition()
				toX = pos[0] + rcPos[0]
				toY = pos[1] + rcPos[1]
				if pos[1] <= pixmap.activeYPos and not foundActive:
					pixmap.move(fromX, fromY)
					pixmap.moveTo(toX, toY, self.slideTime((fromX, fromY), (toX, toY), time))
					pixmap.show()
					pixmap.startMoving()
					foundActive = True
				else:
					pixmap.move(toX, toY)

		def slideTime(self, start, end, time=20):
			result = time
			if self.pixmaps:
				dist = ((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2) ** 0.5
				slide = int(round(dist / self.pixmaps[-1].activeYPos * time))
				result = slide if slide > 0 else 1
			return result

		def hide(self):
			for pixmap in self.pixmaps:
				pixmap.hide()

	def __init__(self):
		self["rc"] = Pixmap()
		self["label"] = Label()
		self.rcPosition = None
		rcHeights = (500,) * 2
		self.selectPixmaps = []
		for indicator in range(self.MAX_BUTTON_INDICATORS):
			self.selectPixmaps.append(self.KeyIndicator(self, rcHeights, (f"indicatorU{indicator}", f"indicatorL{indicator}")))
		self.selectedKeys = 0
		self.selectedKeysPrevious = 0
		self.clearSelectedKeys()
		self.wizardConversion = {  # This dictionary converts named buttons in the Wizards to keyIds.
			"OK": KEYIDS.get("KEY_OK"),
			"EXIT": KEYIDS.get("KEY_EXIT"),
			"LEFT": KEYIDS.get("KEY_LEFT"),
			"RIGHT": KEYIDS.get("KEY_RIGHT"),
			"UP": KEYIDS.get("KEY_UP"),
			"DOWN": KEYIDS.get("KEY_DOWN"),
			"RED": KEYIDS.get("KEY_RED"),
			"GREEN": KEYIDS.get("KEY_GREEN"),
			"YELLOW": KEYIDS.get("KEY_YELLOW"),
			"BLUE": KEYIDS.get("KEY_BLUE")
		}
		self.onLayoutFinish.append(self.initRemoteControl)

	def initRemoteControl(self):
		rcPixmap = LoadPixmap(remoteControl.getRemoteControlPixmap())
		if rcPixmap:
			self["rc"].instance.setPixmap(rcPixmap)
			self.rcPosition = self["rc"].getPosition()
			rcHeight = self["rc"].getSize()[1]
			for selectPixmap in self.selectPixmaps:
				breaks = len(selectPixmap.pixmaps)
				roundup = breaks - 1
				for index, pixmap in enumerate(selectPixmap.pixmaps, start=1):
					pixmap.activeYPos = (rcHeight * index + roundup) // breaks

	def selectKey(self, keyId):
		if self.rcPosition:
			if isinstance(keyId, str):  # This test looks for named buttons in the Wizards and converts them to keyIds.
				keyId = self.wizardConversion.get(keyId, 0)
			pos = remoteControl.getRemoteControlKeyPos(keyId)
			if pos and self.selectedKeys < len(self.selectPixmaps):
				selectPixmap = self.selectPixmaps[self.selectedKeys]
				self.selectedKeys += 1
				if self.selectedKeysPrevious > 0 and self.selectedKeys > self.selectedKeysPrevious:
					selectPixmap.moveTo(pos, self.rcPosition, moveFrom=self.selectPixmaps[self.selectedKeysPrevious - 1], time=config.usage.helpAnimationSpeed.value)
				else:
					selectPixmap.moveTo(pos, self.rcPosition, time=config.usage.helpAnimationSpeed.value)

	def clearSelectedKeys(self):
		self.hideSelectPixmaps()
		self.selectedKeysPrevious = self.selectedKeys
		self.selectedKeys = 0

	def hideSelectPixmaps(self):
		for selectPixmap in self.selectPixmaps:
			selectPixmap.hide()

	# Visits all the buttons in turn, sliding between them.  Starts with
	# the top left button and finishes on the bottom right button.
	# Leaves the highlight on the bottom right button at the end of
	# the test run.  The callback method can be used to restore the
	# highlight(s) to their correct position(s) when the animation
	# completes.
	#
	def testHighlights(self, callback=None):
		def timeout():
			if buttons:
				keyId = buttons.pop(0)
				pos = remoteControl.getRemoteControlKeyPos(keyId)
				pixmap.clearPath()
				pixmap.addMovePoint(rcPos[0] + pos[0], rcPos[1] + pos[1], time=5)
				pixmap.startMoving(startTimer)
				self["label"].setText(f"{_("Key")}: {KEYIDNAMES.get(keyId, _("Unknown"))}\n{_("Label")}: {remoteControl.getRemoteControlKeyLabel(keyId)}")
				pixmap.addMovePoint(rcPos[0] + pos[0], rcPos[1] + pos[1], time=15)
				pixmap.startMoving(startTimer)
			else:
				self["label"].setText("")
				if callable(callback):
					callback()

		def startTimer():
			timer.start(0, True)

		if self.selectPixmaps and self.selectPixmaps[0].pixmaps:
			self.hideSelectPixmaps()
			pixmap = self.selectPixmaps[0].pixmaps[0]
			pixmap.show()
			rcPos = self["rc"].getPosition()
			buttons = remoteControl.getRemoteControlKeyList()[:]
			timer = eTimer()
			timer.callback.append(timeout)
			timer.start(500, True)


class HelpMenu(Screen, ShowRemoteControl):
	def __init__(self, session, helpList):
		Screen.__init__(self, session)
		ShowRemoteControl.__init__(self)
		self.setTitle(_("Help"))
		self["list"] = HelpMenuList(helpList, self.close)
		self["list"].onSelectionChanged.append(self.selectionChanged)
		self["buttonlist"] = Label("")
		self["description"] = Label("")
		self["key_help"] = StaticText(_("HELP"))
		self["helpActions"] = ActionMap(["HelpActions"], {
			"cancel": self.close,
			"select": self["list"].select,
			"displayHelp": self.showHelp,
			"displayHelpLong": self.showButtons
		}, prio=-1)
		# Wildcard binding with slightly higher priority than the wildcard bindings in
		# InfoBarGenerics.InfoBarUnhandledKey, but with a gap so that other wildcards
		# can be interposed if needed.
		eActionMap.getInstance().bindAction("", maxsize - 100, self["list"].handleButton)
		self["listboxFilterActions"] = ActionMap(["HelpMenuListboxActions"], {  # Ignore keypress breaks for the keys in the ListboxActions context.
			"ignore": lambda: 1
		}, prio=1)
		self.onClose.append(self.closeHelp)
		self.onLayoutFinish.append(self.selectionChanged)

	def selectionChanged(self):
		self.clearSelectedKeys()
		selection = self["list"].getCurrent()
		if selection:
			baseButtons = []
			longButtons = []
			shiftButtons = []
			buttonList = []
			for button in selection[3]:
				label = remoteControl.getRemoteControlKeyLabel(button[0])
				if label is None:
					label = "Note: No button defined for this action!"
				if len(button) > 1:
					if button[1] == "SHIFT":
						self.selectKey(KEYIDS.get("KEY_SHIFT"))
						shiftButtons.append(label)
					elif button[1] == "LONG":
						longButtons.append(label)
				else:
					baseButtons.append(label)
				self.selectKey(button[0])
			if baseButtons:
				buttonList.append(pgettext("Text list separator", ", ").join(sorted(baseButtons)))
			if longButtons:
				buttonList.append(_("Long press: %s") % pgettext("Text list separator", ", ").join(sorted(longButtons)))
			if shiftButtons:
				buttonList.append(_("Shift: %s") % pgettext("Text list separator", ", ").join(sorted(shiftButtons)))
			self["buttonlist"].setText("; ".join(buttonList))
			helpText = selection[4]
			self["description"].setText(isinstance(helpText, (list, tuple)) and len(helpText) > 1 and helpText[1] or "")

	def closeHelp(self):
		eActionMap.getInstance().unbindAction("", self["list"].handleButton)
		self["list"].onSelectionChanged.remove(self.selectionChanged)

	def showHelp(self):
		from Screens.MessageBox import MessageBox  # MessageBox import deferred so that MessageBox's import of HelpMenu doesn't cause an import loop.
		helpText = "\n\n".join([
			_("HELP provides brief information for buttons in your current context."),
			_("Navigate up/down with UP/DOWN buttons and page up/down with LEFT/RIGHT. OK to perform the action described in the currently highlighted help."),
			_("Other buttons will jump to the help information for that button, if there is help available."),
			_("If an action is user-configurable, its help entry will be flagged with a '(C)' suffix."),
			_("A highlight on the remote control image shows which button the help refers to. If more than one button performs the indicated function, more than one highlight will be shown. Text below the list lists the active buttons and whether the function requires a long press or SHIFT of the button(s)."),
			_("Configuration options for the HELP screen can be found in 'MENU > Setup > Usage & User Interface > Settings'."),
			_("Press EXIT to return to the help screen.")
		])
		self.session.open(MessageBox, helpText, type=MessageBox.TYPE_INFO, title=_("Help Screen Information"))

	def showButtons(self):
		self.testHighlights(self.selectionChanged)


# Helplist structure:
# [ ( actionMap, context, [(action, helpTest), (action, helpTest), ...] ), (actionMap, ... ), ... ]
#
# The helplist is ordered by the order that the Helpable[Number]ActionMaps
# are initialized.
#
# The lookup of actions is by searching the HelpableActionMaps by priority,
# then my order of initialization.
#
# The lookup of actions for a key press also stops at the first valid action
# encountered.
#
# The search for key press help is on a list sorted in priority order,
# and the search finishes when the first action/help matching matching
# the key is found.
#
# The code recognizes that more than one button can map to an action and
# places a button name list instead of a single button in the help entry.
#
# In the template for HelpMenuList:
#
# Template "default" for simple string help items
# For headings use data[1:] = [heading, None, None]
# For the help entries:
# Use data[1:] = [None, helpText, None] for non-indented text
# and data[1:] = [None, None, helpText] for indented text (indent distance set in template)
#
# Template "extended" for list/tuple help items
# For headings use data[1:] = [heading, None, None, None, None]
# For the help entries:
# Use data[1] = None
# and data[2:] = [helpText, None, extText, None] for non-indented text
# and data[2:] = [None, helpText, None, extText] for indented text
#
class HelpMenuList(List):
	HEADINGS = 1
	EXTENDED = 2

	def __init__(self, helpList, callback):
		def compare(valueA, valueB):
			return (valueA > valueB) - (valueA < valueB)

		def sortKeyAlpha(helpData):  # Convert normal help to extended help format for comparison and ignore case.
			return list(map(str.lower, helpData[1] if isinstance(helpData[1], (tuple, list)) else [helpData[1], ""]))

		def sortCmpPos(posA, posB):
			def getMinPos(pos):  # Reverse the coordinate tuple, too, to (y, x) to get ordering by y then x.
				# return min(map(lambda x: tuple(reversed(self.rcPos.getRcKeyPos(x[0]))), pos))
				return min(map(lambda x: tuple(reversed(remoteControl.getRemoteControlKeyPos(x[0]))), pos))

			return compare(getMinPos(posA[0][3]), getMinPos(posB[0][3]))

		def sortCmpInd(indexA, indexB):
			# Sort order "Flat by key group on remote" is really "Sort in order of buttons in
			# rcpositions.xml", and so the buttons need to be grouped sensibly in that file for
			# this to work properly.
			#
			def getMinInd(index):
				return min(map(lambda x: self.rcKeyIndex[x[0]], index))

			return compare(getMinInd(indexA[0][3]), getMinInd(indexB[0][3]))

		def getActionMapId():
			return getattr(actionMap, "description", None) or id(actionMap)

		def filterHelpList(item, seen):
			def mergeButtonLists(buttonList1, buttonList2):
				buttonList1.extend([x for x in buttonList2 if x not in buttonList1])

			helpItem = tuple(item[1]) if isinstance(item[1], (tuple, list)) else (item[1],)
			if helpItem in seen:
				mergeButtonLists(seen[helpItem], item[0][3])
				result = False
			else:
				seen[helpItem] = item[0][3]
				result = True
			return result

		def addListBoxContext(actionMapHelp, formatFlags):
			extended = (formatFlags & self.EXTENDED) >> 1
			headings = formatFlags & self.HEADINGS
			for index, entry in enumerate(actionMapHelp):
				helpItem = entry[1]
				entry[1:] = [None] * (1 + headings + extended)
				if isinstance(helpItem, (tuple, list)):
					entry[1 + headings] = helpItem[0]
					entry[2 + headings] = helpItem[1]
				else:
					entry[1 + headings] = helpItem
				actionMapHelp[index] = tuple(entry)

		List.__init__(self)
		self.callback = callback  # This assumes that callback is always a valid method!
		self.rcKeyIndex = None
		self.buttonMap = {}
		self.longSeen = False
		formatFlags = 0
		headings, sortCmp, sortKey = {
			"headings+alphabetic": (True, None, sortKeyAlpha),
			"flat+alphabetic": (False, None, sortKeyAlpha),
			"flat+remotepos": (False, sortCmpPos, None),
			"flat+remotegroups": (False, sortCmpInd, None)
		}.get(config.usage.helpSortOrder.value, (False, None, None))
		if remoteControl is None:
			if sortCmp in (sortCmpPos, sortCmpInd):
				sortCmp = None
		else:
			if sortCmp == sortCmpInd:
				self.rcKeyIndex = dict((x[1], x[0]) for x in enumerate(remoteControl.getRemoteControlKeyList()))
		# buttonsProcessed = set()
		helpSeen = defaultdict(list)
		sortedHelpList = sorted(helpList, key=lambda x: x[0].prio)
		actionMapHelp = defaultdict(list)
		for (actionMap, context, actions) in sortedHelpList:
			# print(f"[HelpMenu] HelpMenuList DEBUG: actionMap='{str(actionMap)}', context='{context}', actions='{str(actions)}'.")
			if not actionMap.enabled:
				# print("[HelpMenu] Action map disabled.")
				continue
			if headings and actionMap.description and not (formatFlags & self.HEADINGS):
				# print("[HelpMenu] HelpMenuList DEBUG: Headings found.")
				formatFlags |= self.HEADINGS
			for (action, helpText) in actions:  # DEBUG: Should helpText be response?
				helpTags = []  # if mapFlag else [pgettext("Abbreviation of 'Disabled'", "Disabled")]
				if callable(helpText):
					helpText = helpText()
					helpTags.append(pgettext("Abbreviation of 'Configurable'", "Configurable"))
				if helpText is None:
					# print("[HelpMenu] HelpMenuList DEBUG: No help text found.")
					# helpText = _("No help text available")
					continue
				buttons = queryKeyBinding(context, action)
				# print(f"[HelpMenu] HelpMenuList DEBUG: queryKeyBinding buttons={str(buttons)}.")
				if not buttons:  # Do not display entries which are not accessible from keys.
					# print("[HelpMenu] HelpMenuList DEBUG: No buttons allocated.")
					# helpTags.append(pgettext("Abbreviation of 'Unassigned'", "Unassigned"))
					continue
				buttonLabels = []
				for keyId, flags in buttons:
					if remoteControl.getRemoteControlKeyPos(keyId):
						buttonLabels.append((keyId, "LONG") if flags & 8 else (keyId,))  # For long keypresses, make the second tuple item "LONG".
				if not buttonLabels:  # Only show entries with keys that are available on the used rc.
					# print("[HelpMenu] HelpMenuList DEBUG: Button not available on current remote control.")
					# helpTags.append(pgettext("Abbreviation of 'No Button'", "No Button"))
					continue
				isExtended = isinstance(helpText, (list, tuple))
				if isExtended and not (formatFlags & self.EXTENDED):
					# print("[HelpMenu] HelpMenuList DEBUG: Extended help entry found.")
					formatFlags |= self.EXTENDED
				if helpTags:
					helpStr = f"{helpText[0] if isExtended else helpText}  ({pgettext("Text list separator", ", ").join(helpTags)})"
					helpText = [helpStr, helpText[1]] if isExtended else helpStr
				entry = [(actionMap, context, action, buttonLabels, helpText), helpText]
				if filterHelpList(entry, helpSeen):
					actionMapHelp[getActionMapId()].append(entry)
		helpMenuList = []
		extendedPadding = (None,) if formatFlags & self.EXTENDED else ()
		for (actionMap, context, actions) in helpList:
			actionMapId = getActionMapId()
			if headings and actionMapId in actionMapHelp and getattr(actionMap, "description", None):
				if sortCmp:
					actionMapHelp[actionMapId].sort(key=cmp_to_key(sortCmp))
				elif sortKey:
					actionMapHelp[actionMapId].sort(key=sortKey)
				addListBoxContext(actionMapHelp[actionMapId], formatFlags)
				helpMenuList.append((None, actionMap.description, None) + extendedPadding)
				helpMenuList.extend(actionMapHelp[actionMapId])
				del actionMapHelp[actionMapId]
		if actionMapHelp:
			if formatFlags & self.HEADINGS:  # Add a header if other actionMaps have descriptions.
				helpMenuList.append((None, _("Other Actions"), None) + extendedPadding)
			otherHelp = []
			for (actionMap, context, actions) in helpList:
				actionMapId = getActionMapId()
				if actionMapId in actionMapHelp:
					otherHelp.extend(actionMapHelp[actionMapId])
					del actionMapHelp[actionMapId]
			if sortCmp:
				otherHelp.sort(key=cmp_to_key(sortCmp))
			elif sortKey:
				otherHelp.sort(key=sortKey)
			addListBoxContext(otherHelp, formatFlags)
			helpMenuList.extend(otherHelp)
		ignoredKeyIds = (KEYIDS.get("KEY_OK"), KEYIDS.get("KEY_EXIT"))
		for index, entry in enumerate(helpMenuList):
			if entry[0] and entry[0][3]:  # This should not be required.
				for button in entry[0][3]:
					if button[0] not in (ignoredKeyIds):  # Ignore "break" events from OK and EXIT on return from help popup.
						self.buttonMap[button] = index
		self.style = (
			"default",
			"default+headings",
			"extended",
			"extended+headings",
		)[formatFlags]
		# [(actionMap, context, [(action, helpText), (action, helpText), ...]), ...]
		# [((ActionMap, Context, Action, [(Button, Device/Long), ...], HelpText), HelpText), ...]
		self.setList(helpMenuList)

	def getCurrent(self):
		selection = super(HelpMenuList, self).getCurrent()
		return selection and selection[0]

	def handleButton(self, keyId, flag):
		result = 0  # Report keyId not handled.
		button = (keyId, "LONG") if flag == 3 else (keyId,)
		if button in self.buttonMap:
			if flag == 3 or flag == 1 and not self.longSeen:  # Show help for pressed button for long press, or for Break if it's not a Long press.
				self.longSeen = flag == 3
				self.setIndex(self.buttonMap[button])
				result = 1  # Report keyId handled.
			if flag == 0:  # Reset the long press flag on Make.
				self.longSeen = False
		return result

	def select(self):
		item = self.getCurrent()  # A list entry has a "private" tuple as first entry...
		if item is not None:
			self.callback(item[0], item[1], item[2])  # ...containing (Actionmap, Context, Action, Buttondata). We returns this tuple to the callback.


class HelpableScreen:  # Stub for deprecated manual help definitions used by old screens and plugins.
	def __init__(self):
		if "helpActions" not in self:
			self["helpActions"] = ActionMap(["HelpActions"], {
				"displayHelp": self.showHelp
			}, prio=0)
			self["key_help"] = StaticText(_("HELP"))

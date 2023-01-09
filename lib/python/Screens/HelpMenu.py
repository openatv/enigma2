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
from Components.SystemInfo import BoxInfo
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Screens.Screen import Screen
from Tools.LoadPixmap import LoadPixmap


class HelpableScreen:
	def __init__(self):
		self["helpActions"] = ActionMap(["HelpActions"], {
			"displayHelp": self.showHelp
		}, prio=0)
		self["key_help"] = StaticText(_("HELP"))

	def showHelp(self):
		try:
			if self.secondInfoBarScreen and self.secondInfoBarScreen.shown:
				self.secondInfoBarScreen.hide()
		except:
			pass
		self.session.openWithCallback(self.callHelpAction, HelpMenu, self.helpList)

	def callHelpAction(self, *args):
		if args:
			(actionmap, context, action) = args
			actionmap.action(context, action)


class ShowRemoteControl:
	def __init__(self):
		self["rc"] = Pixmap()
		self["label"] = Label()
		self.rcPosition = None
		buttonImages = 16
		rcHeights = (500,) * 2
		self.selectPics = []
		for indicator in range(buttonImages):
			self.selectPics.append(self.KeyIndicator(self, rcHeights, ("indicatorU%d" % indicator, "indicatorL%d" % indicator)))
		self.nSelectedKeys = 0
		self.oldNSelectedKeys = 0
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

	class KeyIndicator:

		class KeyIndicatorPixmap(MovingPixmap):
			def __init__(self, activeYPos, pixmap):
				MovingPixmap.__init__(self)
				self.activeYPos = activeYPos
				self.pixmapName = pixmap

		def __init__(self, owner, activeYPos, pixmaps):
			self.pixmaps = []
			for actYpos, pixmap in zip(activeYPos, pixmaps):
				pm = self.KeyIndicatorPixmap(actYpos, pixmap)
				owner[pixmap] = pm
				self.pixmaps.append(pm)
			self.pixmaps.sort(key=lambda x: x.activeYPos)

		def slideTime(self, start, end, time=20):
			if not self.pixmaps:
				return time
			dist = ((end[0] - start[0]) ** 2 + (end[1] - start[1]) ** 2) ** 0.5
			slide = int(round(dist / self.pixmaps[-1].activeYPos * time))
			return slide if slide > 0 else 1

		def moveTo(self, pos, rcPos, moveFrom=None, time=20):
			foundActive = False
			for index, pixmap in enumerate(self.pixmaps):
				fromX, fromY = pixmap.getPosition()
				if moveFrom:
					fromX, fromY = moveFrom.pixmaps[index].getPosition()
				x = pos[0] + rcPos[0]
				y = pos[1] + rcPos[1]
				if pos[1] <= pixmap.activeYPos and not foundActive:
					pixmap.move(fromX, fromY)
					pixmap.moveTo(x, y, self.slideTime((fromX, fromY), (x, y), time))
					pixmap.show()
					pixmap.startMoving()
					foundActive = True
				else:
					pixmap.move(x, y)

		def hide(self):
			for pixmap in self.pixmaps:
				pixmap.hide()

	def initRemoteControl(self):
		rc = LoadPixmap(BoxInfo.getItem("RCImage"))
		if rc:
			self["rc"].instance.setPixmap(rc)
			self.rcPosition = self["rc"].getPosition()
			rcHeight = self["rc"].getSize()[1]
			for selectPic in self.selectPics:
				nBreaks = len(selectPic.pixmaps)
				roundup = nBreaks - 1
				n = 1
				for pic in selectPic.pixmaps:
					pic.activeYPos = (rcHeight * n + roundup) / nBreaks
					n += 1

	def selectKey(self, keyId):
		if self.rcPosition:
			if isinstance(keyId, str):  # This test looks for named buttons in the Wizards and converts them to keyIds.
				keyId = self.wizardConversion.get(keyId, 0)
			pos = remoteControl.getRemoteControlKeyPos(keyId)
			if pos and self.nSelectedKeys < len(self.selectPics):
				selectPic = self.selectPics[self.nSelectedKeys]
				self.nSelectedKeys += 1
				if self.oldNSelectedKeys > 0 and self.nSelectedKeys > self.oldNSelectedKeys:
					selectPic.moveTo(pos, self.rcPosition, moveFrom=self.selectPics[self.oldNSelectedKeys - 1], time=int(config.usage.helpAnimationSpeed.value))
				else:
					selectPic.moveTo(pos, self.rcPosition, time=int(config.usage.helpAnimationSpeed.value))

	def clearSelectedKeys(self):
		self.hideSelectPics()
		self.oldNSelectedKeys = self.nSelectedKeys
		self.nSelectedKeys = 0

	def hideSelectPics(self):
		for selectPic in self.selectPics:
			selectPic.hide()

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
				self["label"].setText("%s: %s\n%s: %s" % (_("Key"), KEYIDNAMES.get(keyId, _("Unknown")), _("Label"), remoteControl.getRemoteControlKeyLabel(keyId)))
				pixmap.addMovePoint(rcPos[0] + pos[0], rcPos[1] + pos[1], time=15)
				pixmap.startMoving(startTimer)
			else:
				self["label"].setText("")
				callback()

		def startTimer():
			timer.start(0, True)

		if not self.selectPics or not self.selectPics[0].pixmaps:
			return
		self.hideSelectPics()
		pixmap = self.selectPics[0].pixmaps[0]
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
			"cancel": self.close,  # self.closeHelp,
			"select": self.selectItem,
			"displayHelp": self.showHelp,
			"displayHelpLong": self.showButtons
		}, prio=-1)
		# Wildcard binding with slightly higher priority than the
		# wildcard bindings in InfoBarGenerics.InfoBarUnhandledKey,
		# but with a gap so that other wildcards can be interposed
		# if needed.
		eActionMap.getInstance().bindAction("", maxsize - 100, self["list"].handleButton)
		# Ignore keypress breaks for the keys in the ListboxActions context.
		self["listboxFilterActions"] = ActionMap(["HelpMenuListboxActions"], {
			"ignore": lambda: 1
		}, prio=1)
		self.onClose.append(self.closeHelp)
		self.onLayoutFinish.append(self.selectionChanged)

	def selectItem(self):
		self["list"].select()

	def closeHelp(self):
		eActionMap.getInstance().unbindAction("", self["list"].handleButton)
		self["list"].onSelectionChanged.remove(self.selectionChanged)

	def showHelp(self):
		# MessageBox import deferred so that MessageBox's import of HelpMenu doesn't cause an import loop.
		from Screens.MessageBox import MessageBox
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


# Helplist structure:
# [ ( actionmap, context, [(action, help), (action, help), ...] ), (actionmap, ... ), ... ]
#
# The helplist is ordered by the order that the Helpable[Number]ActionMaps
# are initialised.
#
# The lookup of actions is by searching the HelpableActionMaps by priority,
# then my order of initialisation.
#
# The lookup of actions for a key press also stops at the first valid action
# encountered.
#
# The search for key press help is on a list sorted in priority order,
# and the search finishes when the first action/help matching matching
# the key is found.
#
# The code recognises that more than one button can map to an action and
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
		List.__init__(self)
		self.callback = callback
		self.rcKeyIndex = None
		self.buttonMap = {}
		self.longSeen = False
		formatFlags = 0

		def actMapId():
			return getattr(actionmap, "description", None) or id(actionmap)

		headings, sortCmp, sortKey = {
			"headings+alphabetic": (True, None, self._sortKeyAlpha),
			"flat+alphabetic": (False, None, self._sortKeyAlpha),
			"flat+remotepos": (False, self._sortCmpPos, None),
			"flat+remotegroups": (False, self._sortCmpInd, None)
		}.get(config.usage.helpSortOrder.value, (False, None, None))
		if remoteControl is None:
			if sortCmp in (self._sortCmpPos, self._sortCmpInd):
				sortCmp = None
		else:
			if sortCmp == self._sortCmpInd:
				self.rcKeyIndex = dict((x[1], x[0]) for x in enumerate(remoteControl.getRemoteControlKeyList()))
		buttonsProcessed = set()
		helpSeen = defaultdict(list)
		sortedHelpList = sorted(helpList, key=lambda hle: hle[0].prio)
		actionMapHelp = defaultdict(list)
		for (actionmap, context, actions) in sortedHelpList:
			# print("[HelpMenu] HelpMenuList DEBUG: actionmap='%s', context='%s', actions='%s'." % (str(actionmap), context, str(actions)))
			if not actionmap.enabled:
				# print("[HelpMenu] Action map disabled.")
				continue
			amId = actMapId()
			if headings and actionmap.description and not (formatFlags & self.HEADINGS):
				# print("[HelpMenu] HelpMenuList DEBUG: Headings found.")
				formatFlags |= self.HEADINGS
			for (action, help) in actions:  # DEBUG: Should help be response?
				helpTags = []  # if mapFlag else [pgettext("Abbreviation of 'Disabled'", "Disabled")]
				if callable(help):
					help = help()
					helpTags.append(pgettext("Abbreviation of 'Configurable'", "Configurable"))
				if help is None:
					# print("[HelpMenu] HelpMenuList DEBUG: No help text found.")
					# help = _("No help text available")
					continue
				buttons = queryKeyBinding(context, action)
				# print("[HelpMenu] HelpMenuList DEBUG: queryKeyBinding buttons=%s." % str(buttons))
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
				isExtended = isinstance(help, (list, tuple))
				if isExtended and not (formatFlags & self.EXTENDED):
					# print("[HelpMenu] HelpMenuList DEBUG: Extended help entry found.")
					formatFlags |= self.EXTENDED
				if helpTags:
					helpStr = help[0] if isExtended else help
					tagsStr = pgettext("Text list separator", ", ").join(helpTags)
					helpStr = _("%s  (%s)") % (helpStr, tagsStr)
					help = [helpStr, help[1]] if isExtended else helpStr
				entry = [(actionmap, context, action, buttonLabels, help), help]
				if self._filterHelpList(entry, helpSeen):
					actionMapHelp[actMapId()].append(entry)
		helpMenuList = []
		extendedPadding = (None,) if formatFlags & self.EXTENDED else ()
		for (actionmap, context, actions) in helpList:
			amId = actMapId()
			if headings and amId in actionMapHelp and getattr(actionmap, "description", None):
				if sortCmp:
					actionMapHelp[amId].sort(key=cmp_to_key(sortCmp))
				elif sortKey:
					actionMapHelp[amId].sort(key=sortKey)
				self.addListBoxContext(actionMapHelp[amId], formatFlags)
				helpMenuList.append((None, actionmap.description, None) + extendedPadding)
				helpMenuList.extend(actionMapHelp[amId])
				del actionMapHelp[amId]
		if actionMapHelp:
			if formatFlags & self.HEADINGS:  # Add a header if other actionmaps have descriptions.
				helpMenuList.append((None, _("Other Actions"), None) + extendedPadding)
			otherHelp = []
			for (actionmap, context, actions) in helpList:
				amId = actMapId()
				if amId in actionMapHelp:
					otherHelp.extend(actionMapHelp[amId])
					del actionMapHelp[amId]
			if sortCmp:
				otherHelp.sort(key=cmp_to_key(sortCmp))
			elif sortKey:
				otherHelp.sort(key=sortKey)
			self.addListBoxContext(otherHelp, formatFlags)
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
		# [(actionmap, context, [(action, help), (action, help), ...]), ...]
		# [((ActionMap, Context, Action, [(Button, Device/Long), ...], HelpText), HelpText), ...]
		self.list = helpMenuList

	# Convert normal help to extended help form for comparison and ignore case.
	#
	def _sortKeyAlpha(self, hlp):
		return list(map(str.lower, hlp[1] if isinstance(hlp[1], (tuple, list)) else [hlp[1], ""]))

	def _cmp(self, a, b):
		return (a > b) - (a < b)

	def _sortCmpPos(self, a, b):
		return self._cmp(self._getMinPos(a[0][3]), self._getMinPos(b[0][3]))

	# Reverse the coordinate tuple, too, to (y, x) to get ordering by y then x.
	#
	def _getMinPos(self, a):
		# return min(map(lambda x: tuple(reversed(self.rcPos.getRcKeyPos(x[0]))), a))
		return min(map(lambda x: tuple(reversed(remoteControl.getRemoteControlKeyPos(x[0]))), a))

	def _sortCmpInd(self, a, b):
		return self._cmp(self._getMinInd(a[0][3]), self._getMinInd(b[0][3]))

	# Sort order "Flat by key group on remote" is really
	# "Sort in order of buttons in rcpositions.xml", and so
	# the buttons need to be grouped sensibly in that file for
	# this to work properly.
	#
	def _getMinInd(self, a):
		return min(map(lambda x: self.rcKeyIndex[x[0]], a))

	def _filterHelpList(self, ent, seen):
		hlp = tuple(ent[1]) if isinstance(ent[1], (tuple, list)) else (ent[1],)
		if hlp in seen:
			self._mergeButLists(seen[hlp], ent[0][3])
			return False
		else:
			seen[hlp] = ent[0][3]
			return True

	def _mergeButLists(self, bl1, bl2):
		bl1.extend([b for b in bl2 if b not in bl1])

	def addListBoxContext(self, actionMapHelp, formatFlags):
		extended = (formatFlags & self.EXTENDED) >> 1
		headings = formatFlags & self.HEADINGS
		for index, entry in enumerate(actionMapHelp):
			help = entry[1]
			entry[1:] = [None] * (1 + headings + extended)
			if isinstance(help, (tuple, list)):
				entry[1 + headings] = help[0]
				entry[2 + headings] = help[1]
			else:
				entry[1 + headings] = help
			actionMapHelp[index] = tuple(entry)

	def getCurrent(self):
		selection = super(HelpMenuList, self).getCurrent()
		return selection and selection[0]

	def handleButton(self, keyId, flag):
		button = (keyId, "LONG") if flag == 3 else (keyId,)
		if button in self.buttonMap:
			if flag == 3 or flag == 1 and not self.longSeen:  # Show help for pressed button for long press, or for Break if it's not a Long press.
				self.longSeen = flag == 3
				self.setIndex(self.buttonMap[button])
				return 1  # Report keyId handled.
			if flag == 0:  # Reset the long press flag on Make.
				self.longSeen = False
		return 0  # Report keyId not handled.

	def select(self):
		# A list entry has a "private" tuple as first entry...
		item = self.getCurrent()
		if item is None:
			return
		# ...containing (Actionmap, Context, Action, Buttondata).
		# We returns this tuple to the callback.
		self.callback(item[0], item[1], item[2])

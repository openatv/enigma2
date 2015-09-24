from GUIComponent import GUIComponent

from Components.Sources.List import List
from Tools.KeyBindings import queryKeyBinding, getKeyDescription
from Components.config import config
from collections import defaultdict

# [ ( actionmap, context, [(action, help), (action, help), ...] ), (actionmap, ... ), ... ]

# The helplist is ordered by the order that the Helpable[Number]ActionMaps
# are initialised.

# The lookup of actions is by searching the HelpableActionMaps by priority,
# then my order of initialisation.

# The lookup of actions for a key press also stops at the first valid action
# encountered.

# The search for key press help is on a list sorted in priority order,
# and the search finishes when the first action/help matching matching
# the key is found.

# The code recognises that more than one button can map to an action and
# places a button name list instead of a single button in the help entry.


class HelpMenuList(List):
	def __init__(self, helplist, callback, rcPos=None):
		List.__init__(self)
		self.onSelChanged = []
		self.callback = callback
		self.extendedHelp = False
		self.rcPos = rcPos
		self.rcKeyIndex = None
		self.buttonMap = {}
		self.longSeen = False

		self.onSelectionChanged.append(self.selChanged)

		def actMapId():
			return getattr(actionmap, "description", None) or id(actionmap)

		headings, sortCmp, sortKey = {
			"headings+alphabetic": (True, None, self._sortKeyAlpha),
			"flat+alphabetic": (False, None, self._sortKeyAlpha),
			"flat+remotepos": (False, self._sortCmpPos, None),
			"flat+remotegroups": (False, self._sortCmpInd, None)
		}.get(config.usage.help_sortorder.value, (False, None, None))

		if rcPos is None:
			if sortCmp in (self._sortCmpPos, self._sortCmpInd):
				sortCmp = None
		else:
			if sortCmp == self._sortCmpInd:
				self.rcKeyIndex = dict((x[1], x[0]) for x in enumerate(rcPos.getRcKeyList()))

		indent = 0

		if headings:
			for (actionmap, context, actions) in helplist:
				if actionmap.enabled and getattr(actionmap, "description", None):
					indent = 1
					break

		buttonsProcessed = set()
		helpSeen = defaultdict(list)
		sortedHelplist = sorted(helplist, key=lambda hle: hle[0].prio)
		actionMapHelp = defaultdict(list)

		for (actionmap, context, actions) in sortedHelplist:
			if not actionmap.enabled:
				continue

			amId = actMapId()

			from Screens.ButtonSetup import helpableButtonSetupActionMap
			isHelpableButtonSetupActionMap = isinstance(actionmap, helpableButtonSetupActionMap)

			for (action, help) in actions:
				helpTags = []
				if callable(help):
					help = help()
					# ButtonSetupButtonActions help looks as though
					# the button is configurable, but it isn't really
					if not isHelpableButtonSetupActionMap:
						helpTags.append('C')

				if help is None:
					continue

				# Ignore inactive ButtonSetupButtonActions
				if isHelpableButtonSetupActionMap and not help:
					continue

				buttons = queryKeyBinding(context, action)

				# do not display entries which are not accessible from keys
				if not buttons:
					continue

				name = None
				flags = 0

				buttonNames = []

				for n in buttons:
					(name, flags) = (getKeyDescription(n[0]), n[1])
					if name is not None and (len(name) < 2 or name[1] not in("fp", "kbd")):
						if flags & 8:  # for long keypresses, make the second tuple item "long".
							name = (name[0], "long")
						nlong = (n[0], flags & 8)
						if nlong not in buttonsProcessed:
							buttonNames.append(name)
							buttonsProcessed.add(nlong)

				# only show non-empty entries with keys that are available on the used rc
				if not (buttonNames and help):
					continue
				if isinstance(help, list):
					self.extendedHelp = True
				if helpTags:
					helpTagStr = " (" + ", ".join(helpTags) + ")"
					if isinstance(help, list):
						help[0] += helpTagStr
					else:
						help += helpTagStr

				entry = [(actionmap, context, action, buttonNames), help]
				if self._filterHelpList(entry, helpSeen):
					actionMapHelp[amId].append(entry)

		l = []
		extendedPadding = ('', '') if self.extendedHelp else ()

		for (actionmap, context, actions) in helplist:
			amId = actMapId()
			if headings and amId in actionMapHelp and getattr(actionmap, "description", None):
				if sortCmp or sortKey:
					actionMapHelp[amId].sort(cmp=sortCmp, key=sortKey)
				self.addListBoxContext(actionMapHelp[amId], indent)

				l.append((None, actionmap.description, '') + extendedPadding)
				l.extend(actionMapHelp[amId])
				del actionMapHelp[amId]

		if actionMapHelp:
			if indent:
				l.append((None, _("Other functions"), '') + extendedPadding)

			otherHelp = []
			for (actionmap, context, actions) in helplist:
				amId = actMapId()
				if amId in actionMapHelp:
					otherHelp.extend(actionMapHelp[amId])
					del actionMapHelp[amId]

			if sortCmp or sortKey:
				otherHelp.sort(cmp=sortCmp, key=sortKey)
			self.addListBoxContext(otherHelp, indent)
			l.extend(otherHelp)

		for i, ent in enumerate(l):
			if ent[0] is not None:
				for b in ent[0][3]:
					# Ignore "break" events from
					# OK and EXIT on return from
					# help popup
					if b[0] not in ('OK', 'EXIT'):
						self.buttonMap[b] = i

		if self.extendedHelp:
			self.style = "extended"

		self.list = l

	def _mergeButLists(self, bl1, bl2):
		for b in bl2:
			if b not in bl1:
				bl1.append(b)

	def _filterHelpList(self, ent, seen):
		hlp = tuple(ent[1] if isinstance(ent[1], list) else [ent[1], ''])
		if hlp in seen:
			self._mergeButLists(seen[hlp], ent[0][3])
			return False
		else:
			seen[hlp] = ent[0][3]
			return True

	def addListBoxContext(self, actionMapHelp, indent):
		for i in range(len(actionMapHelp)):
			ent = actionMapHelp[i]
			help = ent[1]
			if self.extendedHelp:
				ent[1:] = ('', '', '', '')
			else:
				ent[1:] = ('', '')
			if isinstance(help, list):
				ent[1 + indent] = help[0]
				ent[3 + indent] = help[1]
			else:
				ent[1 + indent] = help
			actionMapHelp[i] = tuple(ent)

	def _getMinPos(self, a):
		# Reverse the coordinate tuple, too, to (y, x) to get
		# ordering by y then x.
		return min(map(lambda x: tuple(reversed(self.rcPos.getRcKeyPos(x[0]))), a))

	def _sortCmpPos(self, a, b):
		return cmp(self._getMinPos(a[0][3]), self._getMinPos(b[0][3]))

	# Sort order "Flat by key group on remote" is really
	# "Sort in order of buttons in rcpositions.xml", and so
	# the buttons need to be grouped sensibly in that file for
	# this to work properly.

	def _getMinInd(self, a):
		return min(map(lambda x: self.rcKeyIndex[x[0]], a))

	def _sortCmpInd(self, a, b):
		return cmp(self._getMinInd(a[0][3]), self._getMinInd(b[0][3]))

	def _sortKeyAlpha(self, hlp):
		# Convert normal help to extended help form for comparison
		# and ignore case
		return map(str.lower, hlp[1] if isinstance(hlp[1], list) else [hlp[1], ''])

	def ok(self):
		# a list entry has a "private" tuple as first entry...
		l = self.getCurrent()
		if l is None:
			return
		# ...containing (Actionmap, Context, Action, keydata).
		# we returns this tuple to the callback.
		self.callback(l[0], l[1], l[2])

	def handleButton(self, key, flag):
		name = getKeyDescription(key)
		if name is not None and (len(name) < 2 or name[1] not in("fp", "kbd")):
			if flag == 3:  # for long keypresses, make the second tuple item "long".
				name = (name[0], "long")

			if name in self.buttonMap:
				# Show help for pressed button for
				# long press, or for break if it's not a
				# long press
				if flag == 3 or flag == 1 and not self.longSeen:
					self.longSeen = flag == 3
					self.setIndex(self.buttonMap[name])
					# Report key handled
					return 1
				# Reset the long press flag on make
				if flag == 0:
					self.longSeen = False
		# Report key not handled
		return 0

	def getCurrent(self):
		sel = super(HelpMenuList, self).getCurrent()
		return sel and sel[0]

	def selChanged(self):
		for x in self.onSelChanged:
			x()

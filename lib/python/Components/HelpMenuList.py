from GUIComponent import GUIComponent

from enigma import eListboxPythonMultiContent, eListbox, gFont
from Components.MultiContent import MultiContentEntryText
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


class HelpMenuList(GUIComponent):
	def __init__(self, helplist, callback, rcPos=None):
		GUIComponent.__init__(self)
		self.onSelChanged = []
		self.l = eListboxPythonMultiContent()
		self.callback = callback
		self.extendedHelp = False
		self.rcPos = rcPos
		self.rcKeyIndex = None

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

		width = 640
		indent = 0

		for (actionmap, context, actions) in helplist:
			if headings and actionmap.enabled and getattr(actionmap, "description", None):
				indent = 20
				break

		buttonsProcessed = set()
		helpSeen = defaultdict(list)
		sortedHelplist = sorted(helplist, key=lambda hle: hle[0].prio)
		actionMapHelp = defaultdict(list)

		for (actionmap, context, actions) in sortedHelplist:
			if not actionmap.enabled:
				continue

			for (action, help) in actions:
				if hasattr(help, '__call__'):
					help = help()

				if help is None:
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

				# only show entries with keys that are available on the used rc
				if not buttonNames:
					continue

				entry = [(actionmap, context, action, buttonNames), help]
				if self._filterHelpList(entry, helpSeen):
					actionMapHelp[context].append(entry)

		l = []
		for (actionmap, context, actions) in helplist:
			if headings and context in actionMapHelp and getattr(actionmap, "description", None):
				if sortCmp or sortKey:
					actionMapHelp[context].sort(cmp=sortCmp, key=sortKey)
				self.addListBoxContext(actionMapHelp[context], width, indent)

				l.append([None, MultiContentEntryText(pos=(0, 0), size=(width, 26), text=actionmap.description)])
				l.extend(actionMapHelp[context])
				del actionMapHelp[context]

		if actionMapHelp:
			if indent:
				l.append([None, MultiContentEntryText(pos=(0, 0), size=(width, 26), text=_("Other functions"))])

			otherHelp = []
			for (actionmap, context, actions) in helplist:
				if context in actionMapHelp:
					otherHelp.extend(actionMapHelp[context])
					del actionMapHelp[context]

			if sortCmp or sortKey:
				otherHelp.sort(cmp=sortCmp, key=sortKey)
			self.addListBoxContext(otherHelp, width, indent)
			l.extend(otherHelp)

		self.l.setList(l)

		if self.extendedHelp:
			self.l.setFont(0, gFont("Regular", 24))
			self.l.setFont(1, gFont("Regular", 18))
			self.l.setItemHeight(50)
		else:
			self.l.setFont(0, gFont("Regular", 24))
			self.l.setItemHeight(38)

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

	def addListBoxContext(self, actionMapHelp, width, indent):
		for ent in actionMapHelp:
			help = ent[1]
			if isinstance(help, list):
				self.extendedHelp = True
				ent[1:] = (
					MultiContentEntryText(pos=(indent, 0), size=(width - indent, 26), font=0, text=help[0]),
					MultiContentEntryText(pos=(indent, 28), size=(width - indent, 20), font=1, text=help[1]),
				)
			else:
				ent[1] = MultiContentEntryText(pos=(indent, 0), size=(width - indent, 28), font=0, text=help)

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

	def getCurrent(self):
		sel = self.l.getCurrentSelection()
		return sel and sel[0]

	GUI_WIDGET = eListbox

	def postWidgetCreate(self, instance):
		instance.setContent(self.l)
		instance.selectionChanged.get().append(self.selectionChanged)

	def preWidgetRemove(self, instance):
		instance.setContent(None)
		instance.selectionChanged.get().remove(self.selectionChanged)

	def selectionChanged(self):
		for x in self.onSelChanged:
			x()

from GUIComponent import GUIComponent

from enigma import eListboxPythonMultiContent, eListbox, gFont
from Components.MultiContent import MultiContentEntryText
from Tools.KeyBindings import queryKeyBinding, getKeyDescription
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
	def __init__(self, helplist, callback):
		GUIComponent.__init__(self)
		self.onSelChanged = [ ]
		self.l = eListboxPythonMultiContent()
		self.callback = callback
		self.extendedHelp = False

		width = 640
		indent = 0

		for (actionmap, context, actions) in helplist:
			if actionmap.description:
				indent = 20
				break

		buttonsProcessed = set()
		sortedHelplist = sorted(helplist, key=lambda hle: hle[0].prio)
		actionMapHelp = defaultdict(list)

		for (actionmap, context, actions) in sortedHelplist:
			if not actionmap.enabled:
				continue

			for (action, help) in actions:
				if hasattr(help, '__call__'):
					help = help()
				buttons = queryKeyBinding(context, action)

				# do not display entries which are not accessible from keys
				if not buttons:
					continue

				name = None
				flags = 0

				buttonNames = [ ]

				for n in buttons:
					(name, flags) = (getKeyDescription(n[0]), n[1])
					if name is not None and (len(name) < 2 or name[1] not in("fp", "kbd")):
						if flags & 8: # for long keypresses, make the second tuple item "long".
							name = (name[0], "long")
						if n not in buttonsProcessed:
							buttonNames.append(name)
							buttonsProcessed.add(n[0])

				# only show entries with keys that are available on the used rc
				if not buttonNames:
					print '[HelpMenuList] no valid buttons 2'
					continue
				print '[HelpMenuList] valid buttons 2', buttonNames

				entry = [ (actionmap, context, action, buttonNames ), help ]

				actionMapHelp[context].append(entry)

		l = [ ]
		for (actionmap, context, actions) in helplist:
			if context in actionMapHelp and actionmap.description:
				self.addListBoxContext(actionMapHelp[context], width, indent)

				l.append([None, MultiContentEntryText(pos=(0, 0), size=(width, 26), text=actionmap.description)])
				l.extend(actionMapHelp[context])
				del actionMapHelp[context]

		if actionMapHelp:
			if indent:
				l.append([None, MultiContentEntryText(pos=(0, 0), size=(width, 26), text=_("Other functions"))])

			for (actionmap, context, actions) in helplist:
				if context in actionMapHelp:
					self.addListBoxContext(actionMapHelp[context], width, indent)

					l.extend(actionMapHelp[context])
					del actionMapHelp[context]

		self.l.setList(l)

		if self.extendedHelp:
			self.l.setFont(0, gFont("Regular", 24))
			self.l.setFont(1, gFont("Regular", 18))
			self.l.setItemHeight(50)
		else:
			self.l.setFont(0, gFont("Regular", 24))
			self.l.setItemHeight(38)

	def addListBoxContext(self, actionMapHelp, width, indent):
		for ent in actionMapHelp:
			help = ent[1]
			if isinstance(help, list):
				self.extendedHelp = True
				print "extendedHelpEntry found"
				ent[1] = (
					MultiContentEntryText(pos=(indent, 0), size=(width-indent, 26), font=0, text=help[0]),
					MultiContentEntryText(pos=(indent, 28), size=(width-indent, 20), font=1, text=help[1]),
				)
			else:
				ent[1] = MultiContentEntryText(pos=(indent, 0), size=(width-indent, 28), font=0, text=help)

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

from GUIComponent import GUIComponent

from enigma import eListboxPythonMultiContent, eListbox, gFont

from Tools.KeyBindings import queryKeyBinding, getKeyDescription
#getKeyPositions

# [ ( actionmap, context, [(action, help), (action, help), ...] ), (actionmap, ... ), ... ]

class HelpMenuList(GUIComponent):
	def __init__(self, list, callback):
		GUIComponent.__init__(self)
		self.onSelChanged = [ ]
		self.l = eListboxPythonMultiContent()
		self.callback = callback

		l = [ ]
		for (actionmap, context, actions) in list:
			for (action, help) in actions:
				entry = [ ]

				buttons = queryKeyBinding(context, action)

				# do not display entries which are not accessible from keys
				if not len(buttons):
					continue

				name = None
				flags = 0

				for n in buttons:
					(name, flags) = (getKeyDescription(n[0]), n[1])
					if name is not None:
						break

				if flags & 8: # for long keypresses, prepend l_ into the key name.
					name = ("l_" + name[0], name[1], name[2])

				entry.append( (actionmap, context, action, name ) )
				entry.append( (eListboxPythonMultiContent.TYPE_TEXT, 0, 0, 400, 28, 0, 0, help) )

				l.append(entry)

		self.l.setList(l)

		self.l.setFont(0, gFont("Regular", 24))
		self.l.setItemHeight(38)

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

	def selectionChanged(self):
		for x in self.onSelChanged:
			x()

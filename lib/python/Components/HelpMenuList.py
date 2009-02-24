from GUIComponent import GUIComponent

from enigma import eListboxPythonMultiContent, eListbox, gFont
from Tools.KeyBindings import queryKeyBinding, getKeyDescription
#getKeyPositions

# [ ( actionmap, context, [(action, help), (action, help), ...] ), (actionmap, ... ), ... ]

class HelpMenuList(GUIComponent):
	def __init__(self, helplist, callback):
		GUIComponent.__init__(self)
		self.onSelChanged = [ ]
		self.l = eListboxPythonMultiContent()
		self.callback = callback
		self.extendedHelp = False

		l = [ ]
		for (actionmap, context, actions) in helplist:
			for (action, help) in actions:
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
					name = (name[0], "long")
					
				entry = [ (actionmap, context, action, name ) ]

				if isinstance(help, list):
					self.extendedHelp = True
					print "extendedHelpEntry found"
					entry.extend((
						(eListboxPythonMultiContent.TYPE_TEXT, 0, 0, 400, 26, 0, 0, help[0]),
						(eListboxPythonMultiContent.TYPE_TEXT, 0, 28, 400, 20, 1, 0, help[1])
					))
				else:
					entry.append( (eListboxPythonMultiContent.TYPE_TEXT, 0, 0, 400, 28, 0, 0, help) )
					
				l.append(entry)

		self.l.setList(l)
		if self.extendedHelp is True:
			self.l.setFont(0, gFont("Regular", 24))
			self.l.setFont(1, gFont("Regular", 18))
			self.l.setItemHeight(50)
		else:
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

	def preWidgetRemove(self, instance):
		instance.setContent(None)
		instance.selectionChanged.get().remove(self.selectionChanged)

	def selectionChanged(self):
		for x in self.onSelChanged:
			x()

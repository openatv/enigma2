from GUIComponent import *

from enigma import eListboxPythonMultiContent, eListbox, gFont

from Tools.KeyBindings import queryKeyBinding, getKeyDescription

# [ ( actionmap, context, [(action, help), (action, help), ...] ), (actionmap, ... ), ... ]

class HelpMenuList(GUIComponent):
	def __init__(self, list, callback):
		GUIComponent.__init__(self)
		
		self.l = eListboxPythonMultiContent()
		self.callback = callback
		
		l = [ ]
		for (actionmap, context, actions) in list:
			for (action, help) in actions:
				entry = [ ]
				
				entry.append( (actionmap, context, action) )
				buttons = queryKeyBinding(context, action)
				buttonstring = ""
	
				first = True
				for n in buttons:
					name = getKeyDescription(n)
					if name is None:
						continue

					if not first:
						buttonstring += ", or "

					first = False
					buttonstring += name

				if not first:
					buttonstring = "You can also press " + buttonstring + "."

				entry.append( (0, 0, 200, 36, 0, 0, help) )
				entry.append( (0, 40, 200, 20, 1, 0, buttonstring) )
				
				l.append(entry)
		
		self.l.setList(l)
		
		self.l.setFont(0, gFont("Arial", 36))
		self.l.setFont(1, gFont("Arial", 18))
	
	def GUIcreate(self, parent):
		self.instance = eListbox(parent)
		self.instance.setContent(self.l)
		self.instance.setItemHeight(75)
	
	def GUIdelete(self):
		self.instance.setContent(None)
		self.instance = None

	def ok(self):
		# a list entry has a "private" tuple as first entry...
		l = self.l.getCurrentSelection()[0]
		
		# ...containing (Actionmap, Context, Action).
		# we returns this tuple to the callback.
		self.callback(l[0], l[1], l[2])

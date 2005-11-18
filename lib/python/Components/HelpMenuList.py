from GUIComponent import *

from enigma import eListboxPythonMultiContent, eListbox, gFont

# [ ( actionmap, context, [(action, help), (action, help), ...] ), (actionmap, ... ), ... ]

class HelpMenuList(GUIComponent):
	def __init__(self, list, callback):
		GUIComponent.__init__(self)
		
		self.l = eListboxPythonMultiContent()
		self.callback = callback
		
		l = [ ]
		for (actionmap, context, actions) in list:
			
			print "actionmap:"  + str(actionmap)
			print "context: " + str(context)
			print "actions: " + str(actions)
			
			for (action, help) in actions:
				entry = [ ]
				
				entry.append( (actionmap, context, action) )
				entry.append( (0, 36, 200, 20, 1, 0, "you can also press a secret button") )
				entry.append( (0, 0, 200, 36, 0, 0, help) )
				
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

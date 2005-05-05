from GUIComponent import *

class GUISkin:
	def __init__(self):
		pass
	
	def createGUIScreen(self, parent):
		for (name, val) in self.items():
			if isinstance(val, GUIComponent):
				val.GUIcreate(parent, None)
	
	def deleteGUIScreen(self):
		for (name, val) in self.items():
			if isinstance(val, GUIComponent):
				val.GUIdelete()
			try:
				val.fix()
			except:
				pass
			
			# DIESER KOMMENTAR IST NUTZLOS UND MITTLERWEILE VERALTET! (glaub ich)
			# BITTE NICHT LESEN!
			# note: you'll probably run into this assert. if this happens, don't panic!
			# yes, it's evil. I told you that programming in python is just fun, and 
			# suddently, you have to care about things you don't even know.
			#
			# but calm down, the solution is easy, at least on paper:
			#
			# Each Component, which is a GUIComponent, owns references to each
			# instantiated eWidget (namely in screen.data[name]["instance"], in case
			# you care.)
			# on deleteGUIscreen, all eWidget *must* (!) be deleted (otherwise,
			# well, problems appear. I don't want to go into details too much,
			# but this would be a memory leak anyway.)
			# The assert beyond checks for that. It asserts that the corresponding
			# eWidget is about to be removed (i.e., that the refcount becomes 0 after
			# running deleteGUIscreen).
			# (You might wonder why the refcount is checked for 2 and not for 1 or 0 -
			# one reference is still hold by the local variable 'w', another one is
			# hold be the function argument to sys.getrefcount itself. So only if it's
			# 2 at this point, the object will be destroyed after leaving deleteGUIscreen.)
			#
			# Now, how to fix this problem? You're holding a reference somewhere. (References
			# can only be hold from Python, as eWidget itself isn't related to the c++
			# way of having refcounted objects. So it must be in python.)
			#
			# It could be possible that you're calling deleteGUIscreen trough a call of
			# a PSignal. For example, you could try to call screen.doClose() in response
			# to a Button::click. This will fail. (It wouldn't work anyway, as you would
			# remove a dialog while running it. It never worked - enigma1 just set a 
			# per-mainloop variable on eWidget::close() to leave the exec()...)
			# That's why Session supports delayed closes. Just call Session.close() and
			# it will work.
			#
			# Another reason is that you just stored the data["instance"] somewhere. or
			# added it into a notifier list and didn't removed it.
			#
			# If you can't help yourself, just ask me. I'll be glad to help you out.
			# Sorry for not keeping this code foolproof. I really wanted to archive
			# that, but here I failed miserably. All I could do was to add this assert.
#			assert sys.getrefcount(w) == 2, "too many refs hold to " + str(w)
	
	def close(self):
		self.deleteGUIScreen()


from Components.HTMLSkin import *
from Components.GUISkin import *

import sys

class Screen(dict, HTMLSkin, GUISkin):
	""" bla """

	def __init__(self, session):
		self.skinName = self.__class__.__name__
		self.session = session
		GUISkin.__init__(self)
		
		self.onClose = [ ]
		self.onExecBegin = [ ]
		
		# in order to support screens *without* a help,
		# we need the list in every screen. how ironic.
		self.helpList = [ ]
		
	def execBegin(self):
		for x in self.onExecBegin:
			x()
#		assert self.session == None, "a screen can only exec one per time"
#		self.session = session
		for (name, val) in self.items():
			val.execBegin()
	
	def execEnd(self):
		for (name, val) in self.items():
			val.execEnd()
#		assert self.session != None, "execEnd on non-execing screen!"
#		self.session = None
	
	# never call this directly - it will be called from the session!
	def doClose(self):
		for x in self.onClose:
			x()
		
		# fixup circular references
		del self.helpList
		GUISkin.close(self)
		
		del self.session
		for (name, val) in self.items():
			del self[name]
	
	def close(self, *retval):
		self.session.close(*retval)

	def setFocus(self, o):
		self.instance.setFocus(o.instance)

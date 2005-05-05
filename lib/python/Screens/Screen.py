from Components.HTMLSkin import *
from Components.GUISkin import *

import sys

class Screen(dict, HTMLSkin, GUISkin):
	""" bla """

	def __init__(self, session):
		self.skinName = self.__class__.__name__
		self.session = session
		GUISkin.__init__(self)
		
	def execBegin(self):
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
		GUISkin.close(self)
		
		del self.session
		for (name, val) in self.items():
			print "%s -> %d" % (name, sys.getrefcount(val))
			del self[name]
	
	def close(self, retval=None):
		self.session.close()


from __future__ import division
# shamelessly copied from BP Project

from past.utils import old_div
from Components.Converter.Converter import Converter
from Components.Element import cached
from time import localtime, strftime

class EGAnalogic(Converter, object):

	def __init__(self, type):
		Converter.__init__(self, type)
		if type == "Seconds":
			self.type = 1
		elif type == "Minutes":
			self.type = 2
		elif type == "Hours":
			self.type = 3
		else:
			self.type = -1

	@cached
	def getValue(self):
		time = self.source.time
		if time is None:
			return 0
		
		t = localtime(time)	
		
		if self.type == 1:
			return int(old_div((t.tm_sec *100),60))
		elif self.type == 2:
			return int(old_div((t.tm_min *100),60))
		elif self.type == 3:
			return int((old_div((t.tm_hour *100),12)) + (old_div(t.tm_min,8)))
		

	value = property(getValue)

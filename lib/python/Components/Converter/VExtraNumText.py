#######################################################################
#
#    Converter for Dreambox-Enigma2
#    Coded by shamann (c)2010
#
#    This program is free software; you can redistribute it and/or
#    modify it under the terms of the GNU General Public License
#    as published by the Free Software Foundation; either version 2
#    of the License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#    
#######################################################################

from Components.Converter.Converter import Converter
from Components.Element import cached
from time import localtime, strftime

class VExtraNumText(Converter, object):
	SNRNUM = 0
	AGCNUM = 1
	BERNUM = 2
	STEP = 3
	SNRTEXT = 4
	AGCTEXT = 5
	LOCK = 6
	SLOT_NUMBER = 7
	SECHAND = 8
	MINHAND = 9
	HOURHAND = 10	
	
	def __init__(self, type):
		Converter.__init__(self, type)
		if type == "SnrNum":
			self.type = self.SNRNUM	
		elif type == "AgcNum":
			self.type = self.AGCNUM	
		elif type == "BerNum":
			self.type = self.BERNUM
		elif type == "Step":
			self.type = self.STEP
		elif type == "SnrText":
			self.type = self.SNRTEXT
		elif type == "AgcText":
			self.type = self.AGCTEXT
		elif type == "NUMBER":
			self.type = self.SLOT_NUMBER
		elif type == "secHand":
			self.type = self.SECHAND
		elif type == "minHand":
			self.type = self.MINHAND
		elif type == "hourHand":
			self.type = self.HOURHAND
		else:
			self.type = self.LOCK

	@cached
	def getText(self):
		assert self.type not in (self.LOCK, self.SLOT_NUMBER), "error"
		percent = None
		if self.type == self.SNRTEXT:
			percent = self.source.snr
		elif self.type == self.AGCTEXT:
			percent = self.source.agc
		if percent is None:
			return "N/A"
		return "%d" % (percent * 100 / 65536)

	text = property(getText)

	@cached
	def getValue(self):	
		if self.type == self.SNRNUM:
			count = self.source.snr		
			if count is None:
				return 0	
			return (count * 100 / 65536)
		elif self.type == self.AGCNUM:
			count = self.source.agc			
			if count is None:
				return 0						
			return (count * 100 / 65536)
		elif self.type == self.BERNUM:
			count = self.source.ber		
			if count < 320000:
				return count
			return 320000
		elif self.type == self.STEP:
			time = self.source.time
			if time is None:
				return 0
			t = localtime(time)
			c = t.tm_sec
			
			if c < 10:
				return c
			elif c < 20:
				return (c - 10)
			elif c < 30:
				return (c - 20)
			elif c < 40:
				return (c - 30)
			elif c < 50:
				return (c - 40)
			return (c - 50)
		elif self.type == self.SECHAND:
			time = self.source.time
			if time is None:
				return 0
			t = localtime(time)
			c = t.tm_sec
			return c
		elif self.type == self.MINHAND:
			time = self.source.time
			if time is None:
				return 0
			t = localtime(time)
			c = t.tm_min
			return c			
		elif self.type == self.HOURHAND:
			time = self.source.time
			if time is None:
				return 0
			t = localtime(time)
			c = t.tm_hour
			m = t.tm_min
			if c > 11:
				c = c - 12
			val = (c * 5) + (m / 12)
			return val
		return 0

	value = property(getValue)

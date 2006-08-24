# -*- coding: latin-1 -*-
from enigma import *
from Components.Language import language

class NumericalTextInput:
	def __init__(self, nextFunc=None):
		self.mapping = []
		self.lang = language.getLanguage()
		self.useableChars=None
		self.nextFunction=nextFunc
		
		if self.lang == 'de_DE':
			self.mapping.append (u".,?'\"0-()@/:_") # 0
			self.mapping.append (u" 1") # 1
			self.mapping.append (u"aäbc2AÄBC") # 2
			self.mapping.append (u"def3DEF") # 3
			self.mapping.append (u"ghi4GHI") # 4
			self.mapping.append (u"jkl5JKL") # 5
			self.mapping.append (u"mnoö6MNOÖ") # 6
			self.mapping.append (u"pqrsß7PQRSß") # 7
			self.mapping.append (u"tuüv8TUÜV") # 8
			self.mapping.append (u"wxyz9WXYZ") # 9
		elif self.lang == 'es_ES':
			self.mapping.append (u".,?'\"0-()@/:_") # 0
			self.mapping.append (u" 1") # 1
			self.mapping.append (u"abcáà2ABCÁÀ") # 2
			self.mapping.append (u"deéèf3DEFÉÈ") # 3
			self.mapping.append (u"ghiíì4GHIÍÌ") # 4
			self.mapping.append (u"jkl5JKL") # 5
			self.mapping.append (u"mnñoóò6MNÑOÓÒ") # 6
			self.mapping.append (u"pqrs7PQRS") # 7
			self.mapping.append (u"tuvúù8TUVÚÙ") # 8
			self.mapping.append (u"wxyz9WXYZ") # 9
		else:
			self.mapping.append (u".,?'\"0-()@/:_") # 0
			self.mapping.append (u" 1") # 1
			self.mapping.append (u"abc2ABC") # 2
			self.mapping.append (u"def3DEF") # 3
			self.mapping.append (u"ghi4GHI") # 4
			self.mapping.append (u"jkl5JKL") # 5
			self.mapping.append (u"mno6MNO") # 6
			self.mapping.append (u"pqrs7PQRS") # 7
			self.mapping.append (u"tuv8TUV") # 8
			self.mapping.append (u"wxyz9WXYZ") # 9

		self.Timer = eTimer()
		self.Timer.timeout.get().append(self.nextChar)
		self.lastKey = -1
		self.pos = -1

	def setUseableChars(self, useable):
		self.useableChars = useable

	def getKey(self, num):
		cnt=0
		self.Timer.start(1000, True)
		if (self.lastKey != num):
			self.lastKey = num
			self.pos = -1
		while(True):
			self.pos += 1
			if (len(self.mapping[num]) <= self.pos):
				self.pos = 0
			if self.useableChars:
				pos = self.useableChars.find(self.mapping[num][self.pos])
				if pos == -1:
					cnt += 1
					if cnt < len(self.mapping[num]):
						continue
					else:
						return None
			break
		return self.mapping[num][self.pos]

	def nextKey(self):
		self.Timer.stop()
		self.lastKey = -1

	def nextChar(self):
		self.nextKey()
		if self.nextFunction:
			self.nextFunction()

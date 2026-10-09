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

from time import localtime
from Components.Converter.Converter import Converter
from Components.Element import cached


class VExtraNumText(Converter):
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

	def __init__(self, tokens):
		Converter.__init__(self, tokens)
		self.type = {
			"AgcNum": self.AGCNUM,
			"AgcText": self.AGCTEXT,
			"BerNum": self.BERNUM,
			"NUMBER": self.SLOT_NUMBER,
			"SnrNum": self.SNRNUM,
			"SnrText": self.SNRTEXT,
			"Step": self.STEP,
			"hourHand": self.HOURHAND,
			"minHand": self.MINHAND,
			"secHand": self.SECHAND
		}.get(tokens, self.LOCK)

	@cached
	def getText(self):
		assert self.type not in (self.LOCK, self.SLOT_NUMBER), "error"
		match self.type:
			case self.AGCTEXT:
				percent = self.source.agc
			case self.SNRTEXT:
				percent = self.source.snr
			case _:
				percent = None
		return "N/A" if percent is None else f"{int(percent * 100 / 65536)}"

	text = property(getText)

	@cached
	def getValue(self):
		value = 0
		match self.type:
			case self.AGCNUM:
				agc = self.source.agc
				if agc is not None:
					value = agc * 100 / 65536
			case self.BERNUM:
				value = min(self.source.ber, 320000)
			case self.HOURHAND | self.MINHAND | self.SECHAND | self.STEP:
				sourceTime = self.source.time
				if sourceTime is not None:
					timeStruct = localtime(sourceTime)
					match self.type:
						case self.HOURHAND:
							value = ((timeStruct.tm_hour % 12) * 5) + (timeStruct.tm_min / 12)
						case self.MINHAND:
							value = timeStruct.tm_min
						case self.SECHAND:
							value = timeStruct.tm_sec
						case self.STEP:
							value = timeStruct.tm_sec % 10
			case self.SNRNUM:
				snr = self.source.snr
				if snr is not None:
					value = snr * 100 / 65536
		return value

	value = property(getValue)

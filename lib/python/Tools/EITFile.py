# Copyright (C) 2022-2025 jbleyel
# This file is part of OpenATV enigma2 <https://github.com/openatv/enigma2>.
#
# EITFile.py is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# dogtag is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with EITFile.py.  If not, see <http://www.gnu.org/licenses/>.

from datetime import date, datetime

__version__ = "1.2"

EIT_SHORT_EVENT_DESCRIPTOR = 0x4d
EIT_EXTENDED_EVENT_DESCRIPOR = 0x4e


class Bytes:
	def __init__(self):
		self.b = bytearray()

	def len(self):
		return len(self.b)

	def append(self, b):
		self.b.append(b)

	def appends(self, bs):
		self.b.extend(bs)

	def save(self, fileName):
		try:
			with open(fileName, "wb") as stream:
				stream.write(self.b)
			return True
		except OSError as error:
			print(f"[EITFile] Unable to save '{fileName}': {error}")
			return False


class Descriptor:
	def __init__(self, lang: str):
		self.lang = lang
		self.size = 0
		self.data = Bytes()
		self.data.append(self.getTag())

	def getTag(self):
		raise NotImplementedError

	def getBytes(self):
		return self.data.b

	def addData(self, data):
		self.data.append(data)

	def addBytes(self, obj: Bytes):
		self.data.b.extend(obj.b)

	def addlang(self):
		self.data.appends(self.lang.encode("ascii"))

	def calcSize(self):
		self.size = self.data.len()


class DescriptorShort(Descriptor):
	def __init__(self, lang: str, title: str, short: str):
		Descriptor.__init__(self, lang)
		self.addData(7 + len(title) + len(short))
		self.addlang()
		for text in (title, short):
			self.addData(len(text) + 1)
			self.addData(0x15)  # DVB UTF-8 selector.
			self.data.appends(text)
		self.calcSize()

	def getTag(self):
		return EIT_SHORT_EVENT_DESCRIPTOR


class DescriptorExtended(Descriptor):
	def __init__(self, lang: str, text: str, number=0, lastNumber=0):
		Descriptor.__init__(self, lang)
		self.addData(7 + len(text))
		self.addData((number << 4) | lastNumber)
		self.addlang()
		self.addData(0)  # No item descriptions.
		self.addData(len(text) + 1)
		self.addData(0x15)
		self.data.appends(text)
		self.calcSize()

	def getTag(self):
		return EIT_EXTENDED_EVENT_DESCRIPOR


class Header:
	# Public argument names are retained for existing plugins.
	def __init__(self, event_id: int, start: datetime, event_duration: int, free_CA_mode: bool, running_status: int, descriptors_loop_length: int):
		if not 0 <= event_id <= 0xffff or not 0 <= descriptors_loop_length <= 0xfff:
			raise ValueError("Invalid EIT header")
		mjd = (start.date() - date(1858, 11, 17)).days
		if not 0 <= mjd <= 0xffff:
			raise ValueError("EIT date is outside the DVB range")
		minutes, seconds = divmod(max(0, min(int(event_duration), 359999)), 60)
		hours, minutes = divmod(minutes, 60)
		self.data = Bytes()
		self.data.appends(event_id.to_bytes(2, "big"))
		self.data.appends(mjd.to_bytes(2, "big"))
		for value in (start.hour, start.minute, start.second, hours, minutes, seconds):
			self.data.append((value // 10 << 4) | value % 10)
		self.data.append((running_status << 5) | (0x10 if free_CA_mode else 0) | (descriptors_loop_length >> 8))
		self.data.append(descriptors_loop_length & 0xff)

	def getBytes(self):
		return self.data.b


class EITFile:
	# Data and the constructor argument names are used by external plugins.
	def __init__(self, filename: str, lang: str, event_id: int, start: datetime, event_duration: int, title: str, short: str, extended: str):
		self.Data = Bytes()
		self.filename = filename
		if not title:
			raise ValueError("An EIT event needs a title")
		if len(lang) != 3 or not lang.isascii() or not lang.isalpha():
			raise ValueError("EIT language must be a three-letter ISO 639 code")
		titleBytes = self.utf8Prefix(title, 248)
		shortBytes = self.utf8Prefix(short or "", 248 - len(titleBytes))
		descriptors = [DescriptorShort(lang, titleBytes, shortBytes)]
		remaining = (extended or "").encode("utf-8")
		budget = 4095 - descriptors[0].size
		chunks = []
		while remaining and len(chunks) < 16 and budget > 9:
			chunk = remaining[:min(248, budget - 9)].decode("utf-8", errors="ignore").encode("utf-8")
			if not chunk:
				break
			chunks.append(chunk)
			remaining = remaining[len(chunk):]
			budget -= len(chunk) + 9
		descriptors.extend(DescriptorExtended(lang, chunk, index, len(chunks) - 1) for index, chunk in enumerate(chunks))
		header = Header(event_id, start, event_duration, False, 0, sum(x.size for x in descriptors))
		self.Data.b.extend(header.getBytes())
		for descriptor in descriptors:
			self.Data.b.extend(descriptor.getBytes())

	@staticmethod
	def utf8Prefix(text, limit):
		return text.encode("utf-8")[:limit].decode("utf-8", errors="ignore").encode("utf-8")

	def save(self):
		return self.Data.save(self.filename)

	def dump(self):
		for index, value in enumerate(self.Data.b):
			print(f"{index} - {value}")

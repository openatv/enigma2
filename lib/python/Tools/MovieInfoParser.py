# -*- coding: utf-8 -*-
# plnick@vuplus-support.org

from os import stat
from os.path import basename, realpath, splitext

from enigma import iDVBMetaFile


class MovieMetaInfo:
	MAX_SIZE = 1024 * 1024

	def __init__(self, path):
		self.path = path
		try:
			with open(f"{path}.meta", encoding="utf-8", errors="replace") as stream:
				data = stream.read(self.MAX_SIZE + 1)
			if len(data) > self.MAX_SIZE:
				raise ValueError(_("The recording metadata is too large; it was left unchanged."))
			self.lines = data.removesuffix("\n").split("\n") if data else []
		except FileNotFoundError:
			self.lines = []

	def get(self, field, default=""):
		return self.lines[field] if len(self.lines) > field else default

	def update(self, values, service=""):
		status = stat(self.path)
		defaults = [service, splitext(basename(self.path))[0], "", str(int(status.st_mtime)), ""]
		self.lines.extend(defaults[len(self.lines):])
		for field, value in values.items():
			self.lines[field] = str(value).replace("\r", " ").replace("\n", " ")
		text = "\n".join(self.lines) + "\n"
		if len(text) > self.MAX_SIZE:
			raise ValueError(_("The recording metadata is too large; it was left unchanged."))
		return text

	def details(self):
		return {x[0]: self.lines[x[1]] for x in (("title", iDVBMetaFile.idName), ("description", iDVBMetaFile.idDescription)) if len(self.lines) > x[1]}


def getExtendedMovieDescription(ref):
	# Plain paths let background readers reuse the same parser without Enigma objects.
	filePath = realpath(ref if isinstance(ref, str) else ref.getPath())
	basePath = splitext(filePath)[0]
	name = basename(basePath).replace("_", " ")
	description = ""
	for candidate in dict.fromkeys(f"{base}{extension}" for base in (filePath, basePath) for extension in (".txt", ".info")):
		try:
			with open(candidate, "rb") as stream:
				data = stream.read(256 * 1024)
			try:
				description = data.decode("utf-8-sig")
			except UnicodeDecodeError:
				description = data.decode("latin-1")
			break
		except OSError:
			continue
	return name, description

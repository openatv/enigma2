# -*- coding: utf-8 -*-
# plnick@vuplus-support.org

from os.path import basename, realpath, splitext


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

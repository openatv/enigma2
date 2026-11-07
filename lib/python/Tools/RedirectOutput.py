from sys import modules

from enigma import ePythonOutput


class EnigmaLog:
	def __init__(self, level):
		self.level = level
		self.line = ""

	def write(self, data):
		if isinstance(data, bytes):
			data = data.decode(encoding="UTF-8", errors="ignore")
		self.line += data
		if "\n" in data:
			line = self.line
			self.line = ""
			try:
				ePythonOutput(line, self.level)
			except (TypeError, UnicodeEncodeError):
				# Filesystem names can contain surrogate escapes rejected by SWIG.
				ePythonOutput(line.encode("UTF-8", errors="backslashreplace").decode("UTF-8"), self.level)

	def flush(self):
		pass

	def isatty(self):
		return True


class EnigmaLogDebug(EnigmaLog):
	def __init__(self):
		EnigmaLog.__init__(self, 4)  # lvlDebug = 4


class EnigmaLogFatal(EnigmaLog):
	def __init__(self):
		EnigmaLog.__init__(self, 1)  # lvlError = 1


modules["sys"].stdout = EnigmaLogDebug()
modules["sys"].stderr = EnigmaLogFatal()

import sys

from enigma import ePythonOutput


class EnigmaLog:
	def __init__(self, level):
		self.level = level
		self.line = ""

	def write(self, data):
		if isinstance(data, unicode):
			data = data.encode(encoding="UTF-8", errors="ignore")
		self.line += data
		if "\n" in data:
			# ePythonOutput(self.line, self.level)  # OpenPLi, OpenViX
			frame = sys._getframe(1)  # OpenATV
			ePythonOutput(frame.f_code.co_filename, frame.f_lineno, frame.f_code.co_name, self.line)  # OpenATV
			self.line = ""

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


sys.stdout = EnigmaLogDebug()
sys.stderr = EnigmaLogFatal()

import sys
import fcntl
import os
from enigma import ePythonOutput

class EnigmaLogDebug:

	lvlDebug = 4

	def __init__(self):
		self.line = ''

	def write(self, data):
		if isinstance(data, unicode):
			data = data.encode("UTF-8")
		self.line += data
		if '\n' in data:
			ePythonOutput(self.line, self.lvlDebug)
			self.line = ''

	def flush(self):
		pass

	def isatty(self):
		return True

class EnigmaLogFatal:

	lvlError = 1

	def __init__(self):
		self.line = ''

	def write(self, data):
		if isinstance(data, unicode):
			data = data.encode("UTF-8")
		self.line += data
		if '\n' in data:
			ePythonOutput(self.line, self.lvlError)
			self.line = ''

	def flush(self):
		pass

	def isatty(self):
		return True

fcntl.fcntl(sys.stdout, fcntl.F_SETFL, os.O_APPEND)
fcntl.fcntl(sys.stderr, fcntl.F_SETFL, os.O_APPEND)
sys.stdout = EnigmaLogDebug()
sys.stderr = EnigmaLogFatal()

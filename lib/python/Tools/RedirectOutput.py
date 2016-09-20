import sys
from enigma import ePythonOutput

class EnigmaOutput:
	def __init__(self):
		self.line = ''

	def write(self, data):
		if isinstance(data, unicode):
			data = data.encode("UTF-8")
		self.line += data
		if '\n' in data:
			ePythonOutput(self.line)
			self.line = ''

	def flush(self):
		pass

        def isatty(self):
                return True

sys.stdout = sys.stderr = EnigmaOutput()

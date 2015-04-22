import sys
from enigma import ePythonOutput

class EnigmaOutput:
	def write(self, data):
		if isinstance(data, unicode):
			data = data.encode("UTF-8")
		ePythonOutput(data)

	def flush(self):
		pass

        def isatty(self):
                return True

sys.stdout = sys.stderr = EnigmaOutput()

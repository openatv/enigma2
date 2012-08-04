import sys
from enigma import ePythonOutput

class EnigmaOutput:
	def write(self, data):
		if isinstance(data, unicode):
			data = data.encode("UTF-8")
		ePythonOutput(data)

	def flush():
		pass

sys.stdout = sys.stderr = EnigmaOutput()

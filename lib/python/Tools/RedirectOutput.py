import sys
from enigma import ePythonOutput

class EnigmaOutput:
	def __init__(self):
		pass

	def write(self, data):
		if isinstance(data, unicode):
			data = data.encode("UTF-8")
		ePythonOutput(data)

	def flush(self):
		pass

sys.stdout = sys.stderr = EnigmaOutput()

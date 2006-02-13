import sys
from enigma import ePythonOutput

class EnigmaOutput:
	def write(self, data):
		ePythonOutput(data)
	
	def flush():
		pass

sys.stdout = sys.stderr = EnigmaOutput()

import sys
from enigma import ePythonOutput

class EnigmaOutput:
	def __init__(self):
		self.buf = ''
		pass

	def write(self, data):
		if isinstance(data, unicode):
			data = data.encode("UTF-8")
		if '\n' in data:
			frame = sys._getframe(1)
			filename = frame.f_code.co_filename
			self.buf += data
			if 'BugHunting' in filename:
				ePythonOutput('',0,'',self.buf)
			else:
				if '/usr/lib/enigma2/python/' in filename:
					filename = filename.replace('/usr/lib/enigma2/python/', '')
				elif '/git/' in filename:
					filename = filename.split('/git/')[1]
				ePythonOutput(filename, frame.f_lineno, frame.f_code.co_name, self.buf)
			self.buf = ''

		else:
			self.buf += data

	def flush(self):
		pass
		
	def isatty(self):
		return True

sys.stdout = sys.stderr = EnigmaOutput()

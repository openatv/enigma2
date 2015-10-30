import sys
from enigma import ePythonOutput

class EnigmaOutput:
	def __init__(self):
		self.buf = ''
		self.isTraceback = False

	def write(self, data):
		if isinstance(data, unicode):
			data = data.encode("UTF-8")
		self.buf += data
		if '\n' in data:
			if not self.isTraceback and 'Traceback (most recent call last):\n' == self.buf:
				self.isTraceback = True
			if self.isTraceback == False:
				frame = sys._getframe(1)
				filename = frame.f_code.co_filename
				if 'BugHunting' in filename:
					ePythonOutput('',0,'',self.buf)
				else:
					if '/usr/lib/enigma2/python/' in filename:
						filename = filename.replace('/usr/lib/enigma2/python/', '')
					elif '/git/' in filename:
						filename = filename.split('/git/')[1]
					ePythonOutput(filename, frame.f_lineno, frame.f_code.co_name, self.buf)
			else:
				ePythonOutput('',0,'',self.buf)
			if self.isTraceback and self.buf[0] != ' ' and 'Traceback (most recent call last):\n' != self.buf:
				self.isTraceback = False
			self.buf = ''

	def flush(self):
		pass
		
	def isatty(self):
		return True

sys.stdout = sys.stderr = EnigmaOutput()

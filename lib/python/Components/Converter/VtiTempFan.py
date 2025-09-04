from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.Converter.Poll import Poll


class VtiTempFan(Poll, Converter):
	TEMPINFO = 1
	FANINFO = 2
	ALL = 5

	def __init__(self, type):
		Poll.__init__(self)
		Converter.__init__(self, type)
		self.type = type
		self.poll_interval = 30000
		self.poll_enabled = True
		if type == 'TempInfo':
			self.type = self.TEMPINFO
		elif type == 'FanInfo':
			self.type = self.FANINFO
		else:
			self.type = self.ALL

	@cached
	def getText(self):
		textvalue = ''
		if self.type == self.TEMPINFO:
			textvalue = self.tempfile()
		elif self.type == self.FANINFO:
			textvalue = self.fanfile()
		return textvalue

	text = property(getText)

	def tempfile(self):
		temp = ''
		unit = ''
		try:
			with open('/proc/stb/sensors/temp0/value', 'rb') as fd:
				temp = fd.readline().strip()
			with open('/proc/stb/sensors/temp0/unit', 'rb') as fd:
				unit = fd.readline().strip()
			return 'TEMP: %s %s%s' % (str(temp), '\u00B0', str(unit))
		except OSError:
			pass

	def fanfile(self):
		fan = ''
		try:
			with open('/proc/stb/fp/fan_speed', 'rb') as fd:
				fan = fd.readline().strip()
			faninfo = 'FAN: %s' % (str(fan))
			return faninfo
		except OSError:
			pass

	def changed(self, what):
		if what[0] == self.CHANGED_POLL:
			Converter.changed(self, what)

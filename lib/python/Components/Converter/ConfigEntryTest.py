from Converter import Converter
from Components.Element import cached

from Components.config import configfile

class ConfigEntryTest(Converter, object):
	def __init__(self, argstr):
		Converter.__init__(self, argstr)
		args = argstr.split(',')
		self.argerror = False
		self.checkSourceBoolean = False
		self.invert = False
		self.configKey = None
		self.configValue = None
		if len(args) < 2:
			self.argerror = True
		else:
			if args[0].find("config.") != -1:
				self.configKey = args[0]
				self.configValue = args[1]
				if len(args) > 2:
					if args[2] == 'Invert':
						self.invert = True
					elif args[2] == 'CheckSourceBoolean':
						self.checkSourceBoolean = True
					else:
						self.argerror = True
				if len(args) > 3:
					if args[3] == 'Invert':
						self.invert = True
					elif args[3] == 'CheckSourceBoolean':
						self.checkSourceBoolean = True
					else:
						self.argerror = True
			else:
				self.argerror = True
		if self.argerror:
			print "ConfigEntryTest Converter got incorrect arguments", args, "!!!\narg[0] must start with 'config.',\narg[1] is the compare string,\narg[2],arg[3] are optional arguments and must be 'Invert' or 'CheckSourceBoolean'"

	@cached
	def getBoolean(self):
		if self.argerror:
			print "ConfigEntryTest got invalid arguments", self.converter_arguments, "force True!!"
			return True
		if self.checkSourceBoolean and not self.source.boolean:
			return False
		val = configfile.getResolvedKey(self.configKey)
		ret = val == self.configValue
		return ret ^ self.invert

	boolean = property(getBoolean)

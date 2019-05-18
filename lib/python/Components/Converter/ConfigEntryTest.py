from Converter import Converter
from Components.Element import cached

from Components.config import configfile

class ConfigEntryTest(Converter, object):
	def __init__(self, argstr):
		Converter.__init__(self, argstr)
		args = argstr.split(',')
		self.argerror = False
		self.checkSourceBoolean = False
		self.checkInvertSourceBoolean = False
		self.invert = False
		self.configKey = None
		self.configValue = None
		if len(args) < 2:
			self.argerror = True
		else:
			if "config." in args[0]:
				self.configKey = args[0]
				self.configValue = args[1]
				def checkArg(arg):
					if arg == 'Invert':
						self.invert = True
					elif arg == 'CheckSourceBoolean':
						self.checkSourceBoolean = True
					elif arg == 'CheckInvertSourceBoolean':
						self.checkInvertSourceBoolean = True
					else:
						self.argerror = True
				if len(args) > 2:
					checkArg(args[2])
				if len(args) > 3:
					checkArg(args[3])
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
		if self.checkInvertSourceBoolean and self.source.boolean:
			return False
		val = configfile.getResolvedKey(self.configKey)
		ret = val == self.configValue
		return ret ^ self.invert

	boolean = property(getBoolean)

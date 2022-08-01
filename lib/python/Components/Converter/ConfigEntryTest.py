from Components.config import configfile
from Components.Element import cached
from Components.Converter.Converter import Converter


class ConfigEntryTest(Converter):
	def __init__(self, args):
		Converter.__init__(self, args)
		args = [x.strip() for x in args.split(",")]
		self.argError = False
		self.checkSourceBoolean = False
		self.checkInvertSourceBoolean = False
		self.invert = False
		self.configKey = None
		self.configValue = None
		if len(args) < 2:
			self.argError = True
		else:
			if "config." in args[0]:
				self.configKey = args[0]
				self.configValue = args[1]

				def checkArg(arg):
					if arg == "Invert":
						self.invert = True
					elif arg == "CheckSourceBoolean":
						self.checkSourceBoolean = True
					elif arg == "CheckInvertSourceBoolean":
						self.checkInvertSourceBoolean = True
					else:
						self.argError = True

				if len(args) > 2:
					checkArg(args[2])
				if len(args) > 3:
					checkArg(args[3])
			else:
				self.argError = True
		if self.argError:
			print("[ConfigEntryTest] Converter got incorrect arguments '%s'! The arg[0] must start with 'config.', arg[1] is the compare string, arg[2], arg[3] are optional arguments and must be 'Invert' or 'CheckSourceBoolean'." % str(args))

	@cached
	def getBoolean(self):
		if self.argError:
			print("[ConfigEntryTest] Got invalid arguments '%s', force True!" % self.converter_arguments)
			return True
		if self.checkSourceBoolean and not self.source.boolean:
			return False
		if self.checkInvertSourceBoolean and self.source.boolean:
			return False
		retVal = configfile.getResolvedKey(self.configKey, silent=True) == self.configValue  # Invalid/non-existent keys will return None.
		return retVal ^ self.invert

	boolean = property(getBoolean)

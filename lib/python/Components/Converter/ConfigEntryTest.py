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
		self.ignore = False
		self.configKey = None
		self.configValue = None
		if len(args) < 2:
			self.argError = True
		else:
			if "config." in args[0]:
				self.configKey = args[0]
				self.configValue = args[1]
				argMap = {
					"Invert": "invert",
					"Ignore": "ignore",
					"CheckSourceBoolean": "checkSourceBoolean",
					"CheckInvertSourceBoolean": "checkInvertSourceBoolean"
				}

				for arg in args[2:5]:  # check args[2], args[3], args[4]
					if arg in argMap:
						setattr(self, argMap[arg], True)
					else:
						self.argError = True
			else:
				self.argError = True
		if self.argError:
			print(f"[ConfigEntryTest] Converter got incorrect arguments '{str(args)}'! The arg[0] must start with 'config.', arg[1] is the compare string, arg[2] - arg[4] are optional arguments and must be 'Invert', 'Ignore', 'CheckSourceBoolean' or 'CheckInvertSourceBoolean'.")

	@cached
	def getBoolean(self):
		if self.argError:
			print(f"[ConfigEntryTest] Got invalid arguments '{self.converter_arguments}', force True!")
			return True
		if self.checkSourceBoolean and not self.source.boolean:
			return False
		if self.checkInvertSourceBoolean and self.source.boolean:
			return False
		value = configfile.getResolvedKey(self.configKey, silent=True)  # Invalid/non-existent keys will return None.
		if value is None and not self.ignore:
			print(f"[ConfigEntryTest] Converter argument '{self.configKey}' is missing or invalid!")
		retVal = value == self.configValue
		return retVal ^ self.invert

	boolean = property(getBoolean)

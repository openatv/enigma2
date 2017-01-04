LOG_TYPE_DEBUG = "D/ "
LOG_TYPE_INFO = "I/ "
LOG_TYPE_WARNING = "W/ "
LOG_TYPE_ERROR = "E/ "

LOG_LEVEL_ERROR = 0
LOG_LEVEL_WARNING = 1
LOG_LEVEL_INFO = 2
LOG_LEVEL_DEBUG = 3

class LogConfig(object):
	_initialized = False

	@staticmethod
	def init():
		if LogConfig._initialized:
			return
		else:
			from Components.config import config, ConfigSubsection, ConfigOnOff, ConfigSelection
			config.log = ConfigSubsection()
			config.log.level = ConfigSelection(
				choices={ str(LOG_LEVEL_DEBUG) : "DEBUG", str(LOG_LEVEL_INFO) : "INFO", str(LOG_LEVEL_WARNING) : "WARNING", str(LOG_LEVEL_ERROR) : "ERROR",  }, default=str(LOG_LEVEL_INFO))
			config.log.verbose = ConfigOnOff(default=False)
			config.log.colored = ConfigOnOff(default=True)
			LogConfig._initialized = True

	@staticmethod
	def level():
		from Components.config import config
		return int(config.log.level.value)

	@staticmethod
	def verbose():
		from Components.config import config
		return config.log.verbose.value

	@staticmethod
	def colored():
		from Components.config import config
		return config.log.colored.value

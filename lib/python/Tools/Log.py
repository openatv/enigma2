from sys import _getframe
from LogConfig import LogConfig, LOG_TYPE_DEBUG, LOG_TYPE_INFO, LOG_TYPE_WARNING, LOG_TYPE_ERROR, LOG_LEVEL_ERROR, LOG_LEVEL_WARNING, LOG_LEVEL_INFO, LOG_LEVEL_DEBUG

class Log(object):
	@staticmethod
	def e(text=""):
		#ERROR
		LogConfig.init()
		if LogConfig.level() >= LOG_LEVEL_ERROR:
			callframe = _getframe(1)
			Log._log(LOG_TYPE_ERROR, text, callframe)

	@staticmethod
	def w(text=""):
		#WARNING
		LogConfig.init()
		if LogConfig.level() >= LOG_LEVEL_WARNING:
			callframe = _getframe(1)
			Log._log(LOG_TYPE_WARNING, text, callframe)

	@staticmethod
	def i(text=""):
		#INFO
		LogConfig.init()
		if LogConfig.level() >= LOG_LEVEL_INFO:
			callframe = _getframe(1)
			Log._log(LOG_TYPE_INFO, text, callframe)

	@staticmethod
	def d(text=""):
		#DEBUG
		LogConfig.init()
		if LogConfig.level() >= LOG_LEVEL_DEBUG:
			callframe = _getframe(1)
			Log._log(LOG_TYPE_DEBUG, text, callframe)

	@staticmethod
	def _log(type, text, callframe=None):
		LogConfig.init()
		if callframe is None:
			callframe = _getframe(1)

		func = callframe.f_code.co_name
		cls = callframe.f_locals.get('self', None)

		msg = ""
		if not text:
			text = "<no detail>"
		if cls != None:
			cls = cls.__class__.__name__
			msg = "%s [%s.%s] :: %s" % (type, cls, func, text)
		else:
			msg = "%s [%s] :: %s" % (type, func, text)

		if LogConfig.verbose():
			line = callframe.f_lineno
			filename = callframe.f_code.co_filename
			msg = "%s {%s:%s}" % (msg, filename, line)
		if LogConfig.colored():
			if type == LOG_TYPE_ERROR:
				msg = "\033[0;31m%s\033[1;m" % msg
			elif type == LOG_TYPE_WARNING:
				msg = "\033[1;33m%s\033[1;m" % msg
			elif type == LOG_TYPE_DEBUG:
				msg = "\033[0;37m%s\033[1;m" % msg

		print msg

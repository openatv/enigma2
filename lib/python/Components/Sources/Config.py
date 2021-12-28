from Components.Sources.Source import Source


class Config(Source):
	def __init__(self, config):
		Source.__init__(self)
		self.__config = config

	def getConfig(self):
		return self.__config

	config = property(getConfig)

	def getHTML(self, id):
		print("[Config] getHTML %s %s" % (str(self), str(id)))
		return self.__config.getHTML(id)

	def handleCommand(self, cmd):
		print("[Config] ASSIGN: %s" % str(cmd))
		self.__config.unsafeAssign(cmd)

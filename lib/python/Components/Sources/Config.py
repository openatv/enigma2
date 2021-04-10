from Source import Source


class Config(Source):
	def __init__(self, config):
		Source.__init__(self)
		self.__config = config

	def getConfig(self):
		return self.__config

	config = property(getConfig)

	def getHTML(self, id):
		print "getHTML", self, id
		return self.__config.getHTML(id)

	def handleCommand(self, cmd):
		print "ASSIGN:", cmd
		self.__config.unsafeAssign(cmd)

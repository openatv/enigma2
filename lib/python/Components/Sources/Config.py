from Components.Sources.Source import Source


class Config(Source):
	def __init__(self, config):
		Source.__init__(self)
		self.myConfig = config

	def getConfig(self):
		return self.myConfig

	config = property(getConfig)

	def handleCommand(self, cmd):
		print("[Config] ASSIGN: '%s'." % str(cmd))
		self.myConfig.unsafeAssign(cmd)

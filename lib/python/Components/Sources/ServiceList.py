from enigma import eServiceCenter, eServiceReference

from Components.Sources.Source import Source


class ServiceList(Source):
	def __init__(self, root, command_func=None, validate_commands=True):
		Source.__init__(self)
		self.root = root
		self.commandFunction = command_func
		self.validateCommands = validate_commands

	def getServicesAsList(self, format="SN"):
		services = self.getServiceList()
		return services and services.getContent(format, True)

	def getServiceList(self):
		serviceHandler = eServiceCenter.getInstance()
		return serviceHandler.list(self.root)

	def validateReference(self, reference):
		return reference in self.getServicesAsList("S")

	list = property(getServicesAsList)

	lut = {
		"Reference": 0,
		"Name": 1
	}

	def getRoot(self):
		return self.__root

	def setRoot(self, root):
		assert isinstance(root, eServiceReference)
		self.__root = root
		self.changed()

	root = property(getRoot, setRoot)

	def handleCommand(self, cmd):
		print("[ServiceList] Handle command: '%s'." % str(cmd))
		if self.validateCommands and not self.validateReference(cmd):
			print("[ServiceList] Service reference did not validate!")
			return
		reference = eServiceReference(cmd)
		if self.commandFunction:
			self.commandFunction(reference)

from Source import Source
from enigma import eServiceCenter, eServiceReference

class ServiceList(Source):
	def __init__(self, root, command_func = None):
		Source.__init__(self)
		self.root = root
		self.command_func = command_func

	def getServicesAsList(self, format = "SN"):
		services = self.getServiceList()
		return services and services.getContent(format, True)

	def getServiceList(self):
		serviceHandler = eServiceCenter.getInstance()
		return serviceHandler.list(self.root)

	def validateReference(self, ref):
		return ref in self.getServicesAsList("S")

	list = property(getServicesAsList)
	lut = {"Reference": 0, "Name": 1}

	def getRoot(self):
		return self.__root

	def setRoot(self, root):
		assert isinstance(root, eServiceReference)
		self.__root = root
		self.changed()
		
	root = property(getRoot, setRoot)

	def handleCommand(self, cmd):
		print "ServiceList handle command"
		
		if not self.validateReference(cmd):
			print "Service reference did not validate!"
			return

		ref = eServiceReference(cmd)
		if self.command_func:
			self.command_func(ref)

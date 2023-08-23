class ResourceManager:
	def __init__(self):
		self.resourceList = {}

	def addResource(self, name, resource):
		print("adding Resource", name)
		self.resourceList[name] = resource
		print("resources:", self.resourceList)

	def getResource(self, name):
		if not self.hasResource(name):
			return None
		return self.resourceList[name]

	def hasResource(self, name):
		return name in self.resourceList

	def removeResource(self, name):
		if self.hasResource(name):
			del self.resourceList[name]


resourcemanager = ResourceManager()

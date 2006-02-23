import os

from Tools.Directories import *
from Plugins.Plugin import PluginDescriptor

def my_import(name):
	print name
	mod = __import__(name)
	components = name.split('.')
	for comp in components[1:]:
		mod = getattr(mod, comp)
	return mod

class PluginComponent:
	def __init__(self):
		self.plugins = {}
		self.pluginList = [ ]
		self.setPluginPrefix("Plugins.")
		
	def setPluginPrefix(self, prefix):
		self.prefix = prefix
	
	def addPlugin(self, plugin):
		self.pluginList.append(plugin)
		for x in plugin.where:
			self.plugins.setdefault(x, []).append(plugin)
			if x == PluginDescriptor.WHERE_AUTOSTART:
				plugin(reason=0)
	
	def removePlugin(self, plugin):
		self.pluginList.remove(plugin)
		for x in plugin.where:
			self.plugins[x].remove(plugin)
			if x == PluginDescriptor.WHERE_AUTOSTART:
				plugin(reason=1)
	
	def readPluginList(self, directory, modules = [], depth = 1):
		"""enumerates plugins"""
		
		directories = os.listdir(directory)
		
		for x in directories:
			path = directory + x + "/"
			if os.path.isdir(path):
				if fileExists(path + "plugin.py"):
					plugin = my_import('.'.join(["Plugins"] + modules + [x, "plugin"]))
					
					if not plugin.__dict__.has_key("Plugins"):
						print "Plugin %s doesn't have 'Plugin'-call." % (x)
						continue
					
					plugins = plugin.Plugins()
					
					# allow single entry not to be a list
					if type(plugins) is not list:
						plugins = [ plugins ]
					
					for p in plugins:
						p.updateIcon(path)
						self.addPlugin(p);
				else:
					open(path + "__init__.py", "w").close()
					self.readPluginList(path, modules + [x], depth - 1)

	def getPlugins(self, where):
		"""Get list of plugins in a specific category"""
		
		if type(where) is not list:
			where = [ where ]
		res = [ ]
		for x in where:
			for p in self.plugins.get(x, [ ]):
				res.append(p)
		return res
	
	def clearPluginList(self):
		self.pluginList = []

	def shutdown(self):
		for p in self.pluginList[:]:
			self.removePlugin(p)

plugins = PluginComponent()

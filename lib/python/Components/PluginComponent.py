import os

from Tools.Directories import *
from Plugins.Plugin import PluginDescriptor

def my_import(name):
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
	
	def readPluginList(self):
		"""enumerates plugins"""

		directories = os.listdir(resolveFilename(SCOPE_PLUGINS))
		
		for x in directories:
			path = resolveFilename(SCOPE_PLUGINS, x) + "/"
			if os.path.exists(path):
				if fileExists(path + "plugin.py"):
					plugin = my_import('.'.join(("Plugins", x, "plugin")))
					
					if not plugin.__dict__.has_key("Plugins"):
						print "Plugin %s doesn't have 'Plugin'-call." % (x)
						continue
					
					print "plugin", plugin
					plugins = plugin.Plugins()
					
					# allow single entry not to be a list
					if type(plugins) is not list:
						plugins = [ plugins ]
					
					for p in plugins:
						p.updateIcon(path)
						self.addPlugin(p);

	def getPlugins(self, where):
		"""Get list of plugins in a specific category"""
		
		if type(where) is not list:
			where = [ where ]
		res = [ ]
		for x in where:
			for p in self.plugins.get(x, [ ]):
				res.append(p)
		return res

	def shutdown(self):
		for p in self.pluginList[:]:
			self.removePlugin(p)

plugins = PluginComponent()

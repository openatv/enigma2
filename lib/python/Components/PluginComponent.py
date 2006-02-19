import os

from Tools.Directories import *

def my_import(name):
	mod = __import__(name)
	components = name.split('.')
	for comp in components[1:]:
		mod = getattr(mod, comp)
	return mod

class PluginComponent:
	def __init__(self):
		self.plugins = {}
		self.setPluginPrefix("Plugins.")
		
	def setPluginPrefix(self, prefix):
		self.prefix = prefix

	def readPluginList(self, runAutostartPlugins=False, runAutoendPlugins=False):
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
						print "imported plugin %s" % (p.name)
						
						for x in p.where:
							self.plugins.setdefault(x, []).append(p)

	def getPlugins(self, where):
		"""Get list of plugins in a specific category"""
		
		if type(where) is not list:
			where = [ where ]
		res = [ ]
		for x in where:
			for p in self.plugins.get(x, [ ]):
				res.append(p)
		return res

plugins = PluginComponent()

import os
import traceback
import sys

from Tools.Directories import *
from Tools.Import import my_import
from Plugins.Plugin import PluginDescriptor

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
	
	def readPluginList(self, directory):
		"""enumerates plugins"""
		
		categories = os.listdir(directory)
		
		new_plugins = [ ]
		
		for c in categories:
			directory_category = directory + c
			if not os.path.isdir(directory_category):
				continue
			open(directory_category + "/__init__.py", "a").close()
			for x in os.listdir(directory_category):
				path = directory_category + "/" + x
				if os.path.isdir(path):
					if fileExists(path + "/plugin.pyc") or fileExists(path + "/plugin.py"):
						try:
							plugin = my_import('.'.join(["Plugins", c, x, "plugin"]))

							if not plugin.__dict__.has_key("Plugins"):
								print "Plugin %s doesn't have 'Plugin'-call." % (x)
								continue

							plugins = plugin.Plugins(path=path)
						except Exception, exc:
							print "Plugin ", path, "failed to load:", exc
							traceback.print_exc(file=sys.stdout)
							print "skipping plugin."
							continue

						# allow single entry not to be a list
						if type(plugins) is not list:
							plugins = [ plugins ]

						for p in plugins:
							p.updateIcon(path)
							new_plugins.append(p)
		
		# build a diff between the old list of plugins and the new one
		# internally, the "fnc" argument will be compared with __eq__
		plugins_added = [p for p in new_plugins if p not in self.pluginList]
		plugins_removed = [p for p in self.pluginList if p not in new_plugins]
		
		for p in plugins_removed:
			self.removePlugin(p)
		
		for p in plugins_added:
			self.addPlugin(p)

	def getPlugins(self, where):
		"""Get list of plugins in a specific category"""
		
		if type(where) is not list:
			where = [ where ]
		res = [ ]
		for x in where:
			for p in self.plugins.get(x, [ ]):
				res.append(p)
		return res

	def getPluginsForMenu(self, menuid):
		res = [ ]
		for p in self.getPlugins(PluginDescriptor.WHERE_SETUP):
			res += p(menuid)
		return res

	def clearPluginList(self):
		self.pluginList = []
		self.plugins = {}

	def shutdown(self):
		for p in self.pluginList[:]:
			self.removePlugin(p)

plugins = PluginComponent()

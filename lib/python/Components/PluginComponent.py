from os import path as os_path, listdir as os_listdir
from traceback import print_exc
from sys import stdout

from Tools.Directories import fileExists
from Tools.Import import my_import
from Plugins.Plugin import PluginDescriptor
import keymapparser

class PluginComponent:
	firstRun = True
	restartRequired = False
	
	def __init__(self):
		self.plugins = {}
		self.pluginList = [ ]
		self.installedPluginList = [ ]
		self.setPluginPrefix("Plugins.")
		self.resetWarnings()

	def setPluginPrefix(self, prefix):
		self.prefix = prefix

	def addPlugin(self, plugin):
		if self.firstRun or plugin.needsRestart is False:
			self.pluginList.append(plugin)
			for x in plugin.where:
				self.plugins.setdefault(x, []).append(plugin)
				if x == PluginDescriptor.WHERE_AUTOSTART:
					plugin(reason=0)
		else:
			self.restartRequired = True
				
	def removePlugin(self, plugin):
		self.pluginList.remove(plugin)
		for x in plugin.where:
			self.plugins[x].remove(plugin)
			if x == PluginDescriptor.WHERE_AUTOSTART:
				plugin(reason=1)

	def readPluginList(self, directory):
		"""enumerates plugins"""

		categories = os_listdir(directory)

		new_plugins = [ ]

		for c in categories:
			directory_category = directory + c
			if not os_path.isdir(directory_category):
				continue
			for pluginname in os_listdir(directory_category):
				path = directory_category + "/" + pluginname
				if os_path.isdir(path):
					if fileExists(path + "/plugin.pyc") or fileExists(path + "/plugin.pyo") or fileExists(path + "/plugin.py"):
						try:
							plugin = my_import('.'.join(["Plugins", c, pluginname, "plugin"]))

							if not plugin.__dict__.has_key("Plugins"):
								print "Plugin %s doesn't have 'Plugin'-call." % (pluginname)
								continue

							plugins = plugin.Plugins(path=path)
						except Exception, exc:
							print "Plugin ", c + "/" + pluginname, "failed to load:", exc
							print_exc(file=stdout)
							print "skipping plugin."
							self.warnings.append( (c + "/" + pluginname, str(exc)) )
							continue

						# allow single entry not to be a list
						if not isinstance(plugins, list):
							plugins = [ plugins ]

						for p in plugins:
							p.path = path
							p.updateIcon(path)
							new_plugins.append(p)

						if fileExists(path + "/keymap.xml"):
							try:
								keymapparser.readKeymap(path + "/keymap.xml")
							except Exception, exc:
								print "keymap for plugin %s/%s failed to load: " % (c, pluginname), exc
								self.warnings.append( (c + "/" + pluginname, str(exc)) )

		# build a diff between the old list of plugins and the new one
		# internally, the "fnc" argument will be compared with __eq__
		plugins_added = [p for p in new_plugins if p not in self.pluginList]
		plugins_removed = [p for p in self.pluginList if not p.internal and p not in new_plugins]
		
		#ignore already installed but reloaded plugins
		for p in plugins_removed: 
			for pa in plugins_added:
				if pa.path == p.path and pa.where == p.where:
					pa.needsRestart = False

		for p in plugins_removed:
			self.removePlugin(p)

		for p in plugins_added:
			if self.firstRun or p.needsRestart is False:
				self.addPlugin(p)
			else:
				for installed_plugin in self.installedPluginList:
					if installed_plugin.path == p.path:
						if installed_plugin.where == p.where:
							p.needsRestart = False
				self.addPlugin(p)
						
		if self.firstRun:
			self.firstRun = False
			self.installedPluginList = self.pluginList

	def getPlugins(self, where):
		"""Get list of plugins in a specific category"""

		if not isinstance(where, list):
			where = [ where ]
		res = [ ]

		for x in where:
			res.extend(self.plugins.get(x, [ ]))
		res.sort(key=lambda x:x.weight)
		return res

	def getPluginsForMenu(self, menuid):
		res = [ ]
		for p in self.getPlugins(PluginDescriptor.WHERE_MENU):
			res += p(menuid)
		return res

	def clearPluginList(self):
		self.pluginList = []
		self.plugins = {}

	def shutdown(self):
		for p in self.pluginList[:]:
			self.removePlugin(p)

	def resetWarnings(self):
		self.warnings = [ ]

	def getNextWakeupTime(self):
		wakeup = -1
		for p in self.pluginList:
			current = p.getWakeupTime()
			if current > -1 and (wakeup > current or wakeup == -1):
				wakeup = current
		return int(wakeup)

plugins = PluginComponent()

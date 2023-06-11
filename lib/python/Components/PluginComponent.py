from bisect import insort
from os import listdir
from os.path import exists, isdir, join
from shutil import rmtree
from traceback import print_exc

from Components.ActionMap import loadKeymap
from Plugins.Plugin import PluginDescriptor
from Tools.Directories import SCOPE_PLUGINS, fileExists, resolveFilename
from Tools.Import import my_import
from Tools.Profile import profile


class PluginComponent:
	firstRun = True
	restartRequired = False

	def __init__(self):
		self.plugins = {}
		self.pluginList = []
		self.installedPluginList = []
		self.setPluginPrefix("Plugins.")
		self.warnings = []

	def setPluginPrefix(self, prefix):
		self.prefix = prefix

	def addPlugin(self, plugin):
		if self.firstRun or not plugin.needsRestart:
			self.pluginList.append(plugin)
			for where in plugin.where:
				insort(self.plugins.setdefault(where, []), plugin)
				if where == PluginDescriptor.WHERE_AUTOSTART:
					plugin(reason=PluginDescriptor.REASON_START)
		else:
			self.restartRequired = True

	def removePlugin(self, plugin):
		if plugin in self.pluginList:
			self.pluginList.remove(plugin)
		for where in plugin.where:
			self.plugins[where].remove(plugin)
			if where == PluginDescriptor.WHERE_AUTOSTART:
				plugin(reason=PluginDescriptor.REASON_STOP)

	def readPluginList(self, directory):
		"""Enumerates plugins."""
		newPlugins = []
		for pluginDirectory in listdir(directory):
			pluginPath = join(directory, pluginDirectory)
			if not isdir(pluginPath):
				continue
			for pluginName in listdir(pluginPath):
				if pluginName == "__pycache__":
					continue
				path = join(pluginPath, pluginName)
				if isdir(path):
					profile("Plugin %s" % pluginName)
					try:
						plugin = my_import(".".join(["Plugins", pluginDirectory, pluginName, "plugin"]))
						plugins = plugin.Plugins(path=path)
					except Exception as err:
						print("[PluginComponent] Error: Plugin '%s/%s' failed to load!  (%s)" % (pluginDirectory, pluginName, str(err)))
						for filename in ("plugin.py", "plugin.pyc", "plugin.pyo"):  # Suppress errors due to missing plugin.py* files (badly removed plugin).
							if exists(join(path, filename)):
								self.warnings.append(("%s/%s" % (pluginDirectory, pluginName), str(err)))
								print_exc()
								break
						else:
							if not pluginName == "WebInterface":
								print("[PluginComponent] Plugin probably removed, but not cleanly, in '%s'; trying to remove it." % path)
								try:
									rmtree(path)
								except OSError as err:
									print("[PluginComponent] Error %d: Unable to remove directory tree '%s'!  (%s)" % (err.errno, path, err.strerror))
						continue
					if not isinstance(plugins, list):
						plugins = [plugins]
					for plugin in plugins:
						plugin.path = path
						plugin.updateIcon(path)
						newPlugins.append(plugin)
					keymap = join(path, "keymap.xml")
					if exists(keymap):
						try:
							loadKeymap(keymap)
						except Exception as err:
							print("[PluginComponent] Error: The keymap file for plugin '%s/%s' failed to load!  (%s)" % (pluginDirectory, pluginName, str(err)))
							self.warnings.append(("%s/%s" % (pluginDirectory, pluginName), str(err)))
		# Build a diff between the old list of plugins and the new one internally, the "fnc" argument will be compared with "__eq__".
		pluginsAdded = [x for x in newPlugins if x not in self.pluginList]
		pluginsRemoved = [x for x in self.pluginList if not x.internal and x not in newPlugins]
		for pluginRemoved in pluginsRemoved:  # Ignore already installed but reloaded plugins.
			for pluginAdded in pluginsAdded:
				if pluginAdded.path == pluginRemoved.path and pluginAdded.where == pluginRemoved.where:
					pluginAdded.needsRestart = False
		for plugin in pluginsRemoved:
			self.removePlugin(plugin)
		for plugin in pluginsAdded:
			if self.firstRun or not plugin.needsRestart:
				self.addPlugin(plugin)
			else:
				for installedPlugin in self.installedPluginList:
					if installedPlugin.path == plugin.path and installedPlugin.where == plugin.where:
						plugin.needsRestart = False
				self.addPlugin(plugin)
		if self.firstRun:
			self.firstRun = False
			self.installedPluginList = self.pluginList

	def getPlugins(self, where):
		"""Get list of plugins in a specific category."""
		if not isinstance(where, list):
			return self.plugins.get(where, [])  # If not a list, we're done quickly, because the lists are already sorted.
		result = []
		for location in where:  # Efficiently merge two sorted lists together, though this appears to never be used in code anywhere.
			for plugin in self.plugins.get(location, []):
				insort(result, plugin)
		return result

	def getPluginsForMenu(self, menuID):
		result = []
		for plugin in self.getPlugins(PluginDescriptor.WHERE_MENU):
			result += plugin(menuID)
		return result

	def getDescriptionForMenuEntryID(self, menuID, entryID):
		for plugin in self.getPlugins(PluginDescriptor.WHERE_MENU):
			if plugin(menuID) and isinstance(plugin(menuID), (list, tuple)):
				if plugin(menuID)[0][2] == entryID:
					return plugin.description

	def clearPluginList(self):
		self.pluginList = []
		self.plugins = {}

	def reloadPlugins(self, dummy=False):
		self.clearPluginList()
		self.readPluginList(resolveFilename(SCOPE_PLUGINS))

	def shutdown(self):
		for plugin in self.pluginList[:]:
			self.removePlugin(plugin)

	def getWarnings(self):
		return self.warnings

	warnings = property(getWarnings)
	
	def resetWarnings(self):
		self.warnings = []

	def getNextWakeupTime(self, getPluginIdent=False):
		wakeUp = -1
		pluginIdentity = ""
		for plugin in self.pluginList:
			current = int(plugin.getWakeupTime())
			if current > -1 and (wakeUp > current or wakeUp == -1):
				wakeUp = current
				pluginIdentity = "%s | %s" % (plugin.name, plugin.path and plugin.path.split("/")[-1])
		if getPluginIdent:
			return wakeUp, pluginIdentity
		return wakeUp


pluginComponent = PluginComponent()
plugins = pluginComponent  # Retain the legacy name until all code is updated.

import os

from Tools.Directories import *
from Screens.Menu import menuupdater

class PluginComponent:
	def __init__(self):
		self.plugins = []
		self.setPluginPrefix("Plugins.")
		self.menuEntries = []
		
	def setPluginPrefix(self, prefix):
		self.prefix = prefix

	def getPluginList(self):
		list = []
		dir = os.listdir(resolveFilename(SCOPE_PLUGINS))
		self.menuDelete()
		self.menuEntries = []

		for x in dir:
			path = resolveFilename(SCOPE_PLUGINS, x) + "/"
			try:
				if os.path.exists(path):
					if fileExists(path + "plugin.py"):
						pluginmodule = self.prefix + x + ".plugin"
						print "trying to import " + pluginmodule
						exec "import " + pluginmodule
						plugin = eval(pluginmodule)
						picturepath = plugin.getPicturePath()
						pluginname = plugin.getPluginName()
						try:
							for menuEntry in plugin.getMenuRegistrationList():
								self.menuEntries.append([menuEntry, pluginmodule])
						except:
							pass
		
						list.append((picturepath, pluginname , x))
			except:
				print "Directory", path, "contains a faulty plugin"
		self.menuUpdate()
		return list
	
	def menuDelete(self):
		for menuEntry in self.menuEntries:
			menuupdater.delMenuItem(menuEntry[0][0], menuEntry[0][2], menuEntry[1], menuEntry[0][3])

	def menuUpdate(self):
		for menuEntry in self.menuEntries:
			menuupdater.addMenuItem(menuEntry[0][0], menuEntry[0][2], menuEntry[1], menuEntry[0][3])
	
	def runPlugin(self, plugin, session):
		try:
			exec "import " + self.prefix + plugin[2] + ".plugin"
			eval(self.prefix + plugin[2] + ".plugin").main(session)
		except:
			print "exec of plugin failed!"

plugins = PluginComponent()

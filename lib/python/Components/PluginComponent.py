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

	def getPluginList(self, runAutostartPlugins=False, runAutoendPlugins=False):
		list = []
		dir = os.listdir(resolveFilename(SCOPE_PLUGINS))
		self.menuDelete()
		self.menuEntries = []

		for x in dir:
			path = resolveFilename(SCOPE_PLUGINS, x) + "/"
			#try:
			if os.path.exists(path):
				if fileExists(path + "plugin.py"):
					pluginmodule = self.prefix + x + ".plugin"
					print "trying to import " + pluginmodule
					exec "import " + pluginmodule
					plugin = eval(pluginmodule)
					picturepaths = plugin.getPicturePaths()
					plugins = plugin.getPlugins()
					try:
						for menuEntry in plugin.getMenuRegistrationList():
							self.menuEntries.append([menuEntry, pluginmodule])
					except:
						pass

					for y in range(len(plugins)):
						list.append((path + picturepaths[y], plugins[y][0] , x, plugins[y][1], plugins[y][2]))
					if runAutostartPlugins:
						try: plugin.autostart()
						except:	pass
					if runAutoendPlugins:
						try: plugin.autoend()
						except:	pass
							
			#except:
			#	print "Directory", path, "contains a faulty plugin"
		self.menuUpdate()
		return list
	
	def menuDelete(self):
		for menuEntry in self.menuEntries:
			menuupdater.delMenuItem(menuEntry[0][0], menuEntry[0][2], menuEntry[1], menuEntry[0][3])

	def menuUpdate(self):
		for menuEntry in self.menuEntries:
			menuupdater.addMenuItem(menuEntry[0][0], menuEntry[0][2], menuEntry[1], menuEntry[0][3])
	
	def runPlugin(self, plugin, session):
		#try:
			exec("import " + self.prefix + plugin[2] + ".plugin")
			print self.prefix + plugin[2] + ".plugin." + plugin[4]
			if plugin[3] == "screen":
				session.open(eval(self.prefix + plugin[2] + ".plugin." + plugin[4]))
			elif plugin[3] == "function":
				eval(self.prefix + plugin[2] + ".plugin." + plugin[4])(session)
		#except:
			#print "exec of plugin failed!"

plugins = PluginComponent()

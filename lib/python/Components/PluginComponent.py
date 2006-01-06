import os

from Tools.Directories import *
from Screens.Menu import menuupdater
#import Plugins

class PluginComponent:
	def __init__(self):
		self.plugins = []
		self.setPluginPrefix("Plugins.")
		self.menuEntries = []
		
	def setPluginPrefix(self, prefix):
		self.prefix = prefix

	def getPluginList(self):
		list = []
		dir = os.listdir("/usr/lib/enigma2/python/Plugins/")
		self.menuDelete()
		self.menuEntries = []
		for x in dir:
			if x[-3:] == ".py" and x[:-3] != "__init__":
				print "trying to import " + self.prefix + x[:-3]
				exec "import " + self.prefix + x[:-3]
				picturepath = eval(self.prefix + x[:-3]).getPicturePath()
				pluginname = eval(self.prefix + x[:-3]).getPluginName()
				try:
					for menuEntry in eval(self.prefix + x[:-3]).getMenuRegistrationList():
						self.menuEntries.append([menuEntry, self.prefix + x[:-3]])
				except:
					pass

				list.append((picturepath, pluginname , x[:-3]))
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
			exec "import " + self.prefix + plugin[2]
			eval(self.prefix + plugin[2]).main(session)
		except:
			print "exec of plugin failed!"

plugins = PluginComponent()

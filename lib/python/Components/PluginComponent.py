import os

from Tools.Directories import *
#import Plugins

class PluginComponent:
	def __init__(self):
		self.plugins = []
		self.setPluginPrefix("Plugins.")
		
	def setPluginPrefix(self, prefix):
		self.prefix = prefix

	def getPluginList(self):
		list = []
		dir = os.listdir("/usr/lib/enigma2/python/Plugins/")
		for x in dir:
			if x[-3:] == ".py" and x[:-3] != "__init__":
				#try:
				print "trying to import " + self.prefix + x[:-3]
				exec "import " + self.prefix + x[:-3]
				picturepath = eval(self.prefix + x[:-3]).getPicturePath()
				pluginname = eval(self.prefix + x[:-3]).getPluginName()
				list.append((picturepath, pluginname , x[:-3]))
				#except:
					#print "Failed to open module - wrong plugin!"
		return list
	
	def runPlugin(self, plugin, session):
		try:
			exec "import " + self.prefix + plugin[2]
			eval(self.prefix + plugin[2]).main(session)
		except:
			print "exec of plugin failed!"

plugins = PluginComponent()

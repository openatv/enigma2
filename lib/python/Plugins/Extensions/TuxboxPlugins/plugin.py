# must be fixed for the new plugin interface
from Tools.BoundFunction import boundFunction
from Tools.Directories import pathExists
from Plugins.Plugin import PluginDescriptor
from pluginrunner import PluginRunner

from os import listdir

TUXBOX_PLUGINS_PATH = "/usr/lib/tuxbox/plugins/"

def getPlugins():
	pluginlist = []

	if pathExists(TUXBOX_PLUGINS_PATH):
		dir = listdir(TUXBOX_PLUGINS_PATH)

		for x in dir:
			if x[-3:] == "cfg":
				params = getPluginParams(x)
				pluginlist.append(PluginDescriptor(name=params["name"], description=params["desc"], where = PluginDescriptor.WHERE_PLUGINMENU, icon="tuxbox.png", needsRestart = True, fnc=boundFunction(main, plugin=x)))

	return pluginlist

def getPluginParams(file):
	params = {}
	try:
		file = open(TUXBOX_PLUGINS_PATH + file, "r")
		for x in file.readlines():
			split = x.split("=")
			params[split[0]] = split[1]
		file.close()
	except IOError:
		print "no tuxbox plugins found"

	return params

def main(session, plugin, **kwargs):
	print "Running plugin " + plugin[:-4] + ".so with config file", plugin
	print getPluginParams(plugin)
	session.open(PluginRunner, plugin[:-4].split(".so")[0])

def Plugins(**kwargs):
	return getPlugins()

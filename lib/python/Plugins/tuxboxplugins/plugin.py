# must be fixed for the new plugin interface
from enigma import *
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.Label import Label

import os

def getPlugins():
	pluginlist = []

	try:
		dir = os.listdir("/usr/lib/tuxbox/plugins/")
	
		for x in dir:
			try:
				if x[-3:] == "cfg":
					params = getPluginParams(x)
					pluginlist.append((params["name"], params["desc"], "function", "main", x))
			except:
				pass
	except:
		print "no tuxbox plugins found"
	return pluginlist

def getPicturePaths():
	list = []
	try:
		dir = os.listdir("/usr/lib/tuxbox/plugins/")
		for x in dir: list.append("tuxbox.png")
	except:
		print "no tuxbox plugins found"
	return list

def getPluginParams(file):
	params = {}
	try:
		file = open("/usr/lib/tuxbox/plugins/" + file, "r")
		for x in file.readlines():
			split = x.split("=")
			params[split[0]] = split[1]
		file.close()
	except:
		print "not tuxbox plugins found"

	return params

def main(session, args):
	print "Running plugin " + args[:-4] + ".so with config file", args
	print getPluginParams(args)
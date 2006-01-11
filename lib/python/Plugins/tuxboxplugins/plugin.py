from enigma import *
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.Label import Label

import os

def getPlugins():
	dir = os.listdir("/usr/lib/tuxbox/plugins/")
	
	pluginlist = []
	for x in dir:
		try:
			if x[-3:] == "cfg":
				params = getPluginParams(x)
				pluginlist.append((params["name"], params["desc"], "function", "main", x))
		except:
			pass
	return pluginlist

def getPluginParams(file):
	params = {}
	file = open("/usr/lib/tuxbox/plugins/" + file, "r")
	for x in file.readlines():
		split = x.split("=")
		params[split[0]] = split[1]
	file.close()

	return params

def main(session, args):
	print "Running plugin " + args[:-4] + ".so with config file", args
	print getPluginParams(args)
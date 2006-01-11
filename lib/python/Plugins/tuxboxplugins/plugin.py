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
				pluginlist.append((getPluginParams(x)["name"], "function", "main", x))
		except:
			pass
	return pluginlist

def getPluginParams(file):
	file = open("/usr/lib/tuxbox/plugins/" + file, "r")
	lines = file.readlines()
	file.close()
	params = {}
	for x in lines:
		split = x.split("=")
		params[split[0]] = split[1]
	return params

def main(session, args):
	print "Running plugin with number", args
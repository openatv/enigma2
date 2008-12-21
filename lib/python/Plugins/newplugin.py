#!/usr/bin/python

import os

name = raw_input("Plugin name: ")

print

dirlist = []
count = 0
print "Plugin categories:"
for dir in os.listdir("."):
	if os.path.isdir(dir):
		count += 1
		dirlist.append(dir)
		print count, dir
		
category = raw_input("Select plugin category: ")
category = dirlist[int(category) - 1]

def add_where_extensionsmenu(name, fnc):
	description = raw_input("Plugin description: ")
	return 'PluginDescriptor(name = "%s", description = _("%s"), where = PluginDescriptor.WHERE_EXTENSIONSMENU, fnc = %s)' % (name, description, fnc) 

def add_where_pluginmenu(name, fnc):
	description = raw_input("Plugin description: ")
	icon = raw_input("Icon (default: 'plugin.png': ")
	if icon == "":
		icon = "plugin.png"
	return 'PluginDescriptor(name = "%s", description = _("%s"), icon = "%s", where = PluginDescriptor.WHERE_PLUGINMENU, fnc = %s)' % (name, description, icon, fnc) 

wherelist = []
wherelist.append(("WHERE_EXTENSIONSMENU", add_where_extensionsmenu))
wherelist.append(("WHERE_PLUGINMENU", add_where_extensionsmenu))

targetlist = []

stop = False

while not stop:
	os.system("clear")
	print "selected targets:"
	for where in targetlist:
		print where[0]
	
	print
	print "available targets:"
	count = 0
	for where in wherelist:
		count += 1
		print count, where[0]
	print "x break"
		
	target = raw_input("Select WHERE-target: ")
	if target == "x":
		stop = True
	else:
		if wherelist[int(target) - 1] not in targetlist:
			targetlist.append(wherelist[int(target) - 1])
		else:
			targetlist.remove(wherelist[int(target) - 1])


file = open("plugin.py", "w")

importlist = []
for where in targetlist:
	importlist.append(where[0])

file.write("""from Screens.Screen import Screen
from Plugins.Plugin import PluginDescriptor, %s
""" % ', '.join(importlist))

mainlist = []
for count in range(len(targetlist)):
	if count == 0:
		mainlist.append("main")
	else:
		mainlist.append("main" + str(count))

for main in mainlist:
	file.write("""
def %s(session, **kwargs):
	pass
""" % main)

descriptorlist = []
for count in range(len(targetlist)):
	os.system("clear")
	where = targetlist[count]
	print "Options for target %s" % where[0]
	descriptorlist.append(where[1](name, mainlist[count]))
	
if len(descriptorlist) == 1:
	descriptorlist = descriptorlist[0]
else:
	descriptorlist = "[" + ', '.join(descriptorlist) + "]"

file.write("""
def Plugins(**kwargs):
	return %s
	""" % descriptorlist)

file.close()
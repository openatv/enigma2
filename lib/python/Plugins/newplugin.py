#!/usr/bin/python

from errno import EEXIST
from os import listdir, mkdir, system
from os.path import isdir, join

system("clear")
internalName = input("Internal plugin name (no whitespaces, plugin directory): ").strip()
if internalName == "":
	print("\nExiting at user request.\n")
	exit(0)
name = input("Visible plugin name: ").strip()
if name == "":
	print("\nExiting at user request.\n")
	exit(0)
system("clear")
print("Plugin categories:")
dirList = [x for x in listdir(".") if isdir(x)]
for count, dir in enumerate(dirList, start=1):
	print("%d:  %s" % (count, dir))
category = input("\nSelect plugin category: ").strip()
if category == "":
	print("\nExiting at user request.\n")
	exit(0)
category = dirList[int(category) - 1]


def addWhereExtensionsMenu(name, fnc):
	description = input("Plugin description: ").strip()
	return "PluginDescriptor(name=\"%s\", description=_(\"%s\"), where=[PluginDescriptor.WHERE_EXTENSIONSMENU], fnc=%s)" % (name, description, fnc)


def addWherePluginMenu(name, fnc):
	description = input("Plugin description: ").strip()
	icon = input("Icon (default: 'plugin.png': ").strip()
	if icon == "":
		icon = "plugin.png"
	return "PluginDescriptor(name=\"%s\", description=_(\"%s\"), where=[PluginDescriptor.WHERE_PLUGINMENU], icon=\"%s\", fnc=%s)" % (name, description, icon, fnc)


whereList = [("WHERE_EXTENSIONSMENU", addWhereExtensionsMenu), ("WHERE_PLUGINMENU", addWherePluginMenu)]
print(whereList)
targetList = []
stop = False
while not stop:
	system("clear")
	print("Selected targets:")
	for where in targetList:
		print(where[0])
	print("\nAvailable targets:")
	for count, where in enumerate(whereList, start=1):
		print("%d:  %s" % (count, where[0]))
	print("x:  Break/Continue")
	target = input("\nSelect WHERE-target: ").strip()
	if target.upper() in ("X", ""):
		stop = True
	else:
		target = int(target) - 1
		if whereList[target] not in targetList:
			targetList.append(whereList[target])
		else:
			targetList.remove(whereList[target])
pluginPath = "%s/%s" % (category, internalName)
try:
	mkdir(pluginPath)
except OSError as err:
	if err.errno == EEXIST:
		print("Note: The plugin directory '%s' already exists." % pluginPath)
		question = input("\nDo you want to continue? ").strip()
		if question.upper() not in ("Y", "YE", "YES"):
			print("\nExiting at user request.\n")
			exit(0)
	else:
		print("Error %d: Unable to create plugin directory '%s'!  (%s)" % (err.errno, pluginPath, err.strerror))
		exit(err.errno)
with open(join(category, "Makefile.am")) as fd:
	lines = fd.read().splitlines()
	lines[-1] = "%s %s" % (lines[-1], internalName)
	lines.append("")
with open(join(category, "Makefile.am"), "w") as fd:
	fd.write("\n".join(lines))
lines = []
print("Updating file 'configure.ac'...")
with open("../../../configure.ac") as fd:
	lines = fd.read().splitlines()
	for count, line in enumerate(lines):
		if line.strip() == "lib/python/Plugins/%s/Makefile" % category:
			lines.insert(count + 1, "lib/python/Plugins/%s/Makefile" % pluginPath)
	lines.append("")
print("Saving file 'configure.ac'...")
with open("../../../configure.ac", "w") as fd:
	fd.write("\n".join(lines))
print("File 'configure.ac' updated.")
with open(join(pluginPath, "plugin.py"), "w") as fd:
	importList = []
	for where in targetList:
		importList.append(where[0])
	fd.write("from Plugins.Plugin import PluginDescriptor\nfrom Screens.Screen import Screen\n")
	mainList = []
	for count in range(len(targetList)):
		mainList.append("main" if count == 0 else "main%d" % count)
	for main in mainList:
		fd.write("\n\ndef %s(session, **kwargs):\n\tpass\n" % main)
	descriptorList = []
	for count in range(len(targetList)):
		system("clear")
		where = targetList[count]
		print("Options for target %s:\n" % where[0])
		descriptorList.append(where[1](name, mainList[count]))
	descriptorList = descriptorList[0] if len(descriptorList) == 1 else "[\n\t\t%s\n\t]" % ",\n\t\t".join(descriptorList)
	fd.write("\n\ndef Plugins(**kwargs):\n\treturn %s\n" % descriptorList)
with open(join(pluginPath, "Makefile.am"), "w") as fd:
	fd.write("installdir = $(pkglibdir)/python/Plugins/%s/%s\n\ninstall_PYTHON = \\\n\t__init__.py \\\n\tplugin.py\n" % (category, internalName))
print("\nPlugin '%s' template created.\n" % internalName)

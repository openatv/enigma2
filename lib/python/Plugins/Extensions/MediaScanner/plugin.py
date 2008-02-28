from Plugins.Plugin import PluginDescriptor
from Components.Scanner import scanDevice

def execute(option):
	print "execute", option
	if option is None:
		return

	(_, scanner, files, session) = option
	scanner.open(files, session)

def mountpoint_choosen(option):
	if option is None:
		return

	from Screens.ChoiceBox import ChoiceBox

	(description, mountpoint, session) = option
	res = scanDevice(mountpoint)

	list = [ (r.description, r, res[r], session) for r in res ]

	if list == [ ]:
		print "nothing found"
		return

	session.openWithCallback(execute, ChoiceBox, 
		title = "The following files were found...",
		list = list)

def scan(session):
	from Screens.ChoiceBox import ChoiceBox

	from Components.Harddisk import harddiskmanager

	parts = [ (r.description, r.mountpoint, session) for r in harddiskmanager.getMountedPartitions(onlyhotplug = False)]
	if len(parts):
		session.openWithCallback(mountpoint_choosen, ChoiceBox, title = _("Please Select Medium to be Scanned"), list = parts)

def main(session, **kwargs):
	scan(session)

def menuEntry(*args):
	mountpoint_choosen(args)

def menuHook(menuid):
	if menuid != "mainmenu": 
		return [ ]

	from Components.Harddisk import harddiskmanager
	from Tools.BoundFunction import boundFunction
	return [(_("Show files from %s") % r.description, boundFunction(menuEntry, r.description, r.mountpoint), "hotplug", None) for r in harddiskmanager.getMountedPartitions(onlyhotplug = True)]

def Plugins(**kwargs):
	return [ PluginDescriptor(name="MediaScanner", description="Scan Files...", where = PluginDescriptor.WHERE_PLUGINMENU, fnc=main),
		PluginDescriptor(where = PluginDescriptor.WHERE_MENU, fnc=menuHook)]

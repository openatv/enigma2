from Plugins.Plugin import PluginDescriptor
from Components.Scanner import scanDevice
from Screens.InfoBar import InfoBar
import os

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

	print "scanning", option
	(description, mountpoint, session) = option
	res = scanDevice(mountpoint)

	list = [ (r.description, r, res[r], session) for r in res ]

	if not list:
		from Screens.MessageBox import MessageBox
		if os.access(mountpoint, os.F_OK|os.R_OK):
			session.open(MessageBox, _("No displayable files on this medium found!"), MessageBox.TYPE_ERROR, simple = True, timeout = 5)
		else:
			print "ignore", mountpoint, "because its not accessible"
		return

	session.openWithCallback(execute, ChoiceBox,
		title = _("The following files were found..."),
		list = list)

def scan(session):
	from Screens.ChoiceBox import ChoiceBox
	parts = [ (r.tabbedDescription(), r.mountpoint, session) for r in harddiskmanager.getMountedPartitions(onlyhotplug = False) if os.access(r.mountpoint, os.F_OK|os.R_OK) ]
	parts.append( (_("Memory") + "\t/tmp", "/tmp", session) )
	session.openWithCallback(mountpoint_choosen, ChoiceBox, title = _("Please select medium to be scanned"), list = parts)

def main(session, **kwargs):
	scan(session)

def menuEntry(*args):
	mountpoint_choosen(args)

from Components.Harddisk import harddiskmanager

def menuHook(menuid):
	if menuid != "mainmenu":
		return [ ]
	from Tools.BoundFunction import boundFunction
	return [("%s (files)" % r.description, boundFunction(menuEntry, r.description, r.mountpoint), "hotplug_%s" % r.mountpoint, None) for r in harddiskmanager.getMountedPartitions(onlyhotplug = True)]

global_session = None

def partitionListChanged(action, device):
	if InfoBar.instance:
		if InfoBar.instance.execing:
			if action == 'add' and device.is_hotplug:
				print "mountpoint", device.mountpoint
				print "description", device.description
				print "force_mounted", device.force_mounted
				mountpoint_choosen((device.description, device.mountpoint, global_session))
		else:
			print "main infobar is not execing... so we ignore hotplug event!"
	else:
			print "hotplug event.. but no infobar"

def sessionstart(reason, session):
	global global_session
	global_session = session

def autostart(reason, **kwargs):
	global global_session
	if reason == 0:
		harddiskmanager.on_partition_list_change.append(partitionListChanged)
	elif reason == 1:
		harddiskmanager.on_partition_list_change.remove(partitionListChanged)
		global_session = None

def movielist_open(list, session, **kwargs):
	from Components.config import config
	if not list:
		# sanity
		return
	from enigma import eServiceReference
	from Screens.InfoBar import InfoBar
	f = list[0]
	if f.mimetype == "video/MP2T":
		stype = 1
	else:
		stype = 4097
	if InfoBar.instance:
		path = os.path.split(f.path)[0]
		if not path.endswith('/'):
			path += '/'
		config.movielist.last_videodir.value = path
		try:
			InfoBar.instance.showMovies(eServiceReference(stype, 0, f.path))
		except:
			pass

def filescan(**kwargs):
	from Components.Scanner import Scanner, ScanPath
	return [
		Scanner(mimetypes = ["video/mpeg", "video/MP2T", "video/x-msvideo", "video/mkv", "video/avi"],
			paths_to_scan =
				[
					ScanPath(path = "", with_subdirs = False),
					ScanPath(path = "movie", with_subdirs = False),
				],
			name = "Movie",
			description = _("View Movies..."),
			openfnc = movielist_open,
		),
		Scanner(mimetypes = ["video/x-vcd"],
			paths_to_scan =
				[
					ScanPath(path = "mpegav", with_subdirs = False),
					ScanPath(path = "MPEGAV", with_subdirs = False),
				],
			name = "Video CD",
			description = _("View Video CD..."),
			openfnc = movielist_open,
		),
		Scanner(mimetypes = ["audio/mpeg", "audio/x-wav", "application/ogg", "audio/x-flac"],
			paths_to_scan =
				[
					ScanPath(path = "", with_subdirs = False),
				],
			name = "Music",
			description = _("Play Music..."),
			openfnc = movielist_open,
		),
		Scanner(mimetypes = ["audio/x-cda"],
			paths_to_scan =
				[
					ScanPath(path = "", with_subdirs = False),
				],
			name = "Audio-CD",
			description = _("Play Audio-CD..."),
			openfnc = movielist_open,
		),
		]

def Plugins(**kwargs):
	return [
		PluginDescriptor(name="Media scanner", description=_("Scan files..."), where = PluginDescriptor.WHERE_PLUGINMENU, icon="MediaScanner.png", needsRestart = True, fnc=main),
#		PluginDescriptor(where = PluginDescriptor.WHERE_MENU, fnc=menuHook),
		PluginDescriptor(name=_("Media scanner"), where = PluginDescriptor.WHERE_FILESCAN, needsRestart = False, fnc = filescan),
		PluginDescriptor(where = PluginDescriptor.WHERE_SESSIONSTART, needsRestart = True, fnc = sessionstart),
		PluginDescriptor(where = PluginDescriptor.WHERE_AUTOSTART, needsRestart = True, fnc = autostart)
		]

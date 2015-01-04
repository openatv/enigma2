import os
from Components.config import config
from Tools.Directories import pathExists, fileExists
from Plugins.Plugin import PluginDescriptor
from Components.Harddisk import harddiskmanager

detected_DVD = None

def main(session, **kwargs):
	from Screens import DVD
	session.open(DVD.DVDPlayer)

def play(session, **kwargs):
	from Screens import DVD
	session.open(DVD.DVDPlayer, dvd_device=harddiskmanager.getAutofsMountpoint(harddiskmanager.getCD()))

def DVDPlayer(*args, **kwargs):
	# for backward compatibility with plugins that do "from DVDPlayer.plugin import DVDPlayer"
	from Screens import DVD
	return DVD.DVDPlayer(*args, **kwargs)

def DVDOverlay(*args, **kwargs):
	# for backward compatibility with plugins that do "from DVDPlayer.plugin import DVDOverlay"
	from Screens import DVD
	return DVD.DVDOverlay(*args, **kwargs)

def filescan_open(list, session, **kwargs):
	from Screens import DVD
	if len(list) == 1 and list[0].mimetype == "video/x-dvd":
		splitted = list[0].path.split('/')
		if len(splitted) > 2:
			if splitted[1] == 'media' and (splitted[2].startswith('sr') or splitted[2] == 'dvd'):
				session.open(DVD.DVDPlayer, dvd_device="/dev/%s" %(splitted[2]))
				return
	else:
		dvd_filelist = []
		for x in list:
			if x.mimetype == "video/x-dvd-iso":
				dvd_filelist.append(x.path)
			if x.mimetype == "video/x-dvd":
				dvd_filelist.append(x.path.rsplit('/',1)[0])
		session.open(DVD.DVDPlayer, dvd_filelist=dvd_filelist)

def filescan(**kwargs):
	from Components.Scanner import Scanner, ScanPath

	# Overwrite checkFile to only detect local
	class LocalScanner(Scanner):
		def checkFile(self, file):
			return fileExists(file.path)

	return [
		LocalScanner(mimetypes = ["video/x-dvd","video/x-dvd-iso"],
			paths_to_scan =
				[
					ScanPath(path = "video_ts", with_subdirs = False),
					ScanPath(path = "VIDEO_TS", with_subdirs = False),
					ScanPath(path = "", with_subdirs = False),
				],
			name = "DVD",
			description = _("Play DVD"),
			openfnc = filescan_open,
		)]

def onPartitionChange(action, partition):
	print "[@] onPartitionChange", action, partition
	if partition != harddiskmanager.getCD():
		global detected_DVD
		if action == 'remove':
			print "[@] DVD removed"
			detected_DVD = False
		elif action == 'add':
			print "[@] DVD Inserted"
			detected_DVD = None

def menu(menuid, **kwargs):
	if menuid == "mainmenu":
		global detected_DVD
		if detected_DVD is None:
			cd = harddiskmanager.getCD()
			if cd and os.path.exists(os.path.join(harddiskmanager.getAutofsMountpoint(harddiskmanager.getCD()), "VIDEO_TS")):
				detected_DVD = True
			else:
				detected_DVD = False
			if onPartitionChange not in harddiskmanager.on_partition_list_change:
				harddiskmanager.on_partition_list_change.append(onPartitionChange)
		if detected_DVD:
			return [(_("DVD player"), play, "dvd_player", 46)]
	return []

def Plugins(**kwargs):
	return [PluginDescriptor(where = PluginDescriptor.WHERE_FILESCAN, needsRestart = False, fnc = filescan),
		PluginDescriptor(name = "DVDPlayer", description = "Play DVDs", where = PluginDescriptor.WHERE_MENU, needsRestart = False, fnc = menu)]

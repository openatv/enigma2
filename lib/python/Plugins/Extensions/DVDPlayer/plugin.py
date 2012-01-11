from Components.config import config
from Tools.Directories import pathExists, fileExists

def main(session, **kwargs):
	from Screens import DVD
	session.open(DVD.DVDPlayer)

from Plugins.Plugin import PluginDescriptor

def filescan_open(list, session, **kwargs):
	from Screens import DVD
	if len(list) == 1 and list[0].mimetype == "video/x-dvd":
		splitted = list[0].path.split('/')
		print "splitted", splitted
		if len(splitted) > 2:
			if splitted[1] == 'autofs':
				session.open(DVD.DVDPlayer, dvd_device="/dev/%s" %(splitted[2]))
				return
			else:
				print "splitted[0]", splitted[1]
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

def Plugins(**kwargs):
	return [PluginDescriptor(where = PluginDescriptor.WHERE_FILESCAN, needsRestart = False, fnc = filescan)]

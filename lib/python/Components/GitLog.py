import urllib, socket
from sys import modules
from os import path
from boxbranding import getImageDistro, getImageType, getImageVersion

def fetchlog(logtype):
	releasenotes = ""
	try:
		if getImageType() == 'release':
			sourceurl = 'http://www.openvix.co.uk/feeds/%s/%s/%s/%s-git.log' % (getImageDistro(), getImageType(), getImageVersion(), logtype)
		else:
			sourceurl = 'http://openvixdev.dyndns.tv/feeds/%s/%s/%s/%s-git.log' % (getImageDistro(), getImageType(), getImageVersion(), logtype)
		print "[GitLog]",sourceurl
		sourcefile,headers = urllib.urlretrieve(sourceurl)
		fd = open(sourcefile, 'r')
		for line in fd.readlines():
			if getImageType() == 'release' and line.startswith('openvix: developer'):
				print '[GitLog] Skipping dev line'
				continue
			elif getImageType() == 'developer' and line.startswith('openvix: release'):
				print '[GitLog] Skipping release line'
				continue
			releasenotes += line
		fd.close()
		releasenotes = releasenotes.replace('\nopenvix: build',"\n\nopenvix: build")
		releasenotes = releasenotes.replace('\nopenvix: %s' % getImageType(),"\n\nopenvix: %s" % getImageType())
	except:
		releasenotes = '404 Not Found'
	return releasenotes

# For modules that do "from GitLog import gitlog"
gitlog = modules[__name__]

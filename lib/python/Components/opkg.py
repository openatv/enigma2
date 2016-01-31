import os
from boxbranding import getImageVersion

def enumFeeds():
	for fn in os.listdir('/etc/opkg'):
		if fn.endswith('-feed.conf'):
			file = open(os.path.join('/etc/opkg', fn))
			feedfile = file.readlines()
			file.close()
			try:
				for feed in feedfile:
					yield feed.split()[1]
			except IndexError:
				pass
			except IOError:
				pass

def enumPlugins(filter_start=''):
	list_dir = listsDirPath()
	for feed in enumFeeds():
		package = None
		try:
			for line in open(os.path.join(list_dir, feed), 'r'):
				if line.startswith('Package:'):
					package = line.split(":",1)[1].strip()
					version = ''
					description = ''
					if package.startswith(filter_start) and not package.endswith('-dev') and not package.endswith('-staticdev') and not package.endswith('-dbg') and not package.endswith('-doc') and not package.endswith('-src'):
						continue
					package = None
				if package is None:
					continue
				if line.startswith('Version:'):
					version = line.split(":",1)[1].strip()
				elif line.startswith('Description:'):
					description = line.split(":",1)[1].strip()
				elif description and line.startswith(' '):
					description += line[:-1]
				elif len(line) <= 1:
					d = description.split(' ',3)
					if len(d) > 3:
						# Get rid of annoying "version" and package repeating strings
						if d[1] == 'version':
							description = d[3]
						if description.startswith('gitAUTOINC'):
							description = description.split(' ',1)[1]
					yield package, version, description.strip()
					package = None
		except IOError:
			pass

def listsDirPath():
	try:
		for line in open('/etc/opkg/opkg.conf', "r"):
			if line.startswith('option'):
				line = line.split(' ', 2)
				if len(line) > 2 and line[1] == ('lists_dir'):
					return line[2].strip()
			elif line.startswith('lists_dir'):
				return line.replace('\n','').split(' ')[2]
	except Exception, ex:
		print "[opkg]", ex
	return '/var/lib/opkg/lists'

if __name__ == '__main__':
	for p in enumPlugins('enigma'):
		print p

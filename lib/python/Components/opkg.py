import os

def enumFeeds():
	for arch in open('/etc/opkg/arch.conf', 'r'):
		if arch.startswith('arch'):
			try:
				arch_name = arch.split()[1]
				for feed in open('/etc/opkg/%s-feed.conf' % arch_name):
					yield feed.split()[1]
			except IOError:
				pass

def enumPlugins(filter_start=''):
	for feed in enumFeeds():
		package = None
		for line in open('/var/lib/opkg/%s' % feed, 'r'):
			if line.startswith('Package:'):
				package = line[8:].strip()
				version = ''
				description = ''
				if package.startswith(filter_start) and not package.endswith('-dev') and not package.endswith('-staticdev') and not package.endswith('-dbg') and not package.endswith('-doc'):
					continue
				package = None
			if package is None:
				continue
			if line.startswith('Version:'):
				version = line[8:].strip()
			elif line.startswith('Description:'):
				description = line[14:-1]
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

if __name__ == '__main__':
	for p in enumPlugins('enigma'):
		print p

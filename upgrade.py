import os

opkgDestinations = ['/']
opkgStatusPath = ''

def findMountPoint(path):
	'Example: findMountPoint("/media/hdd/some/file") returns "/media/hdd"'
	path = os.path.abspath(path)
	while not os.path.ismount(path):
		path = os.path.dirname(path)
	return path

def opkgExtraDestinations():
	global opkgDestinations
	return ''.join([" --add-dest %s:%s" % (i,i) for i in opkgDestinations])

def opkgAddDestination(mountpoint):
	global opkgDestinations
	if mountpoint not in opkgDestinations:
		opkgDestinations.append(mountpoint)
		print "[Ipkg] Added to OPKG destinations:", mountpoint

mounts = os.listdir('/media')
for mount in mounts:
	mount = os.path.join('/media', mount)
	if mount and not mount.startswith('/media/net'):
		if opkgStatusPath == '':
			# recent opkg versions
			opkgStatusPath = 'var/lib/opkg/status'
			if not os.path.exists(os.path.join('/', opkgStatusPath)):
				# older opkg versions
				opkgStatusPath = 'usr/lib/opkg/status'
		if os.path.exists(os.path.join(mount, opkgStatusPath)):
			opkgAddDestination(mount)

import subprocess as sp
process = sp.Popen('opkg ' + opkgExtraDestinations() + ' upgrade 2>&1 /home/root/ipkgupgrade.log && reboot', shell = True, stdout = sp.PIPE, stderr = sp.PIPE)
pid = process.pid
output, error = process.communicate()

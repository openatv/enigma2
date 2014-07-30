import os
from subprocess import Popen, PIPE

opkgDestinations = ['/']
opkgStatusPath = ''
overwriteSettingsFiles = False
overwriteDriversFiles  = True
overwriteEmusFiles     = True
overwritePiconsFiles   = True
overwriteBootlogoFiles = True
overwriteSpinnerFiles  = True

def findMountPoint(path):
	"""Example: findMountPoint("/media/hdd/some/file") returns "/media/hdd\""""
	path = os.path.abspath(path)
	while not os.path.ismount(path):
		path = os.path.dirname(path)
	return path

def opkgExtraDestinations():
	global opkgDestinations
	return ''.join([" --add-dest %s:%s" % (i, i) for i in opkgDestinations])

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

def getValue(line):
	dummy = line.split('=')
	if len(dummy) <> 2:
		print "Error: Wrong formatted settings file"
		exit
	if dummy[1] == "false":
		return False
	elif dummy[1] == "true":
		return True
	else:
		return False

# get list of upgradable packages
p = Popen("opkg list-upgradable", stdout=PIPE, stderr=PIPE, shell=True)
stdout, stderr = p.communicate()

if stderr <> "":
	print "Error occured:", stderr
	exit

# read configuration
try:
	f = open("/etc/enigma2/settings", "r")
	lines = f.readlines()
	f.close()
except:
	print "Error opening /etc/enigma2/settings file"

for line in lines:
	if line.startswith("config.plugins.softwaremanager.overwriteSettingsFiles"):
		overwriteSettingsFiles = getValue(line)
	elif line.startswith("config.plugins.softwaremanager.overwriteDriversFiles"):
		overwriteDriversFiles = getValue(line)
	elif line.startswith("config.plugins.softwaremanager.overwriteEmusFiles"):
		overwriteEmusFiles = getValue(line)
	elif line.startswith("config.plugins.softwaremanager.overwritePiconsFiles"):
		overwritePiconsFiles = getValue(line)
	elif line.startswith("config.plugins.softwaremanager.overwriteBootlogoFiles"):
		overwriteBootlogoFiles = getValue(line)
	elif line.startswith("config.plugins.softwaremanager.overwriteSpinnerFiles"):
		overwriteSpinnerFiles = getValue(line)

# Split lines
packages = stdout.split('\n')
try:
	packages.remove("")
except:
	pass

# Check for packages which should not be upgraded and remove them from list
upgradePackages = []
for package in packages:
	item = package.split(' - ', 2)
	if item[0].find('-settings-') > -1 and not overwriteSettingsFiles:
		continue
	elif item[0].find('kernel-module-') > -1 and not overwriteDriversFiles:
		continue
	elif item[0].find('-softcams-') > -1 and not overwriteEmusFiles:
		continue
	elif item[0].find('-picons-') > -1 and not overwritePiconsFiles:
		continue
	elif item[0].find('-bootlogo') > -1 and not overwriteBootlogoFiles:
		continue
	elif item[0].find('openatv-spinner') > -1 and not overwriteSpinnerFiles:
		continue
	else:
		upgradePackages.append(item[0])

for p in upgradePackages:
	os.system('opkg ' + opkgExtraDestinations() + ' upgrade ' + p + ' 2>&1 | tee /home/root/ipkgupgrade.log')

# Reboot box
os.system('reboot')

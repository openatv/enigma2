from __future__ import print_function
import os
from enigma import eConsoleAppContainer
from Components.Harddisk import harddiskmanager
from Components.config import config, ConfigSubsection, ConfigYesNo
from Tools.Directories import resolveFilename, SCOPE_LIBDIR
from shutil import rmtree
from boxbranding import getImageDistro, getImageVersion
from six import PY3

opkgDestinations = []
opkgStatusPath = ''

def Load_defaults():
	config.plugins.softwaremanager = ConfigSubsection()
	config.plugins.softwaremanager.overwriteSettingsFiles = ConfigYesNo(default=False)
	config.plugins.softwaremanager.overwriteDriversFiles = ConfigYesNo(default=True)
	config.plugins.softwaremanager.overwriteEmusFiles = ConfigYesNo(default=True)
	config.plugins.softwaremanager.overwritePiconsFiles = ConfigYesNo(default=True)
	config.plugins.softwaremanager.overwriteBootlogoFiles = ConfigYesNo(default=True)
	config.plugins.softwaremanager.overwriteSpinnerFiles = ConfigYesNo(default=True)


def opkgExtraDestinations():
	global opkgDestinations
	return ''.join([" --add-dest %s:%s" % (i, i) for i in opkgDestinations])


def opkgAddDestination(mountpoint):
	global opkgDestinations
	if mountpoint not in opkgDestinations:
		opkgDestinations.append(mountpoint)
		print("[Opkg] Added to OPKG destinations:", mountpoint)


def onPartitionChange(why, part):
	global opkgDestinations
	global opkgStatusPath
	mountpoint = os.path.normpath(part.mountpoint)
	if mountpoint and not mountpoint.startswith('/media/net'):
		if why == 'add':
			if opkgStatusPath == '':
				# recent opkg versions
				opkgStatusPath = 'var/lib/opkg/status'
				if not os.path.exists(os.path.join('/', opkgStatusPath)):
					# older opkg versions
					opkgStatusPath = resolveFilename(SCOPE_LIBDIR, 'opkg/status')
			if os.path.exists(os.path.join(mountpoint, opkgStatusPath)):
				opkgAddDestination(mountpoint)
		elif why == 'remove':
			try:
				opkgDestinations.remove(mountpoint)
				print("[Opkg] Removed from OPKG destinations:%s" % mountpoint)
			except:
				pass


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
					package = line.split(":", 1)[1].strip()
					version = ''
					description = ''
					if package.startswith(filter_start) and not package.endswith('-dev') and not package.endswith('-staticdev') and not package.endswith('-dbg') and not package.endswith('-doc') and not package.endswith('-src') and not package.endswith('--pycache--'):
						continue
					package = None
				if package is None:
					continue
				if line.startswith('Version:'):
					version = line.split(":", 1)[1].strip()
				elif line.startswith('Description:'):
					description = line.split(":", 1)[1].strip()
				elif description and line.startswith(' '):
					description += line[:-1]
				elif len(line) <= 1:
					d = description.split(' ', 3)
					if len(d) > 3:
						# Get rid of annoying "version" and package repeating strings
						if d[1] == 'version':
							description = d[3]
						if description.startswith('gitAUTOINC'):
							description = description.split(' ', 1)[1]
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
				return line.replace('\n', '').split(' ')[2]
	except Exception as ex:
		print("[Opkg]", ex)
	return '/var/lib/opkg/lists'


if __name__ == '__main__':
	for p in enumPlugins('enigma'):
		print(p)

harddiskmanager.on_partition_list_change.append(onPartitionChange)
for part in harddiskmanager.getMountedPartitions():
	onPartitionChange('add', part)


class OpkgComponent:
	EVENT_INSTALL = 0
	EVENT_DOWNLOAD = 1
	EVENT_INFLATING = 2
	EVENT_CONFIGURING = 3
	EVENT_REMOVE = 4
	EVENT_UPGRADE = 5
	EVENT_LISTITEM = 9
	EVENT_DONE = 10
	EVENT_ERROR = 11
	EVENT_MODIFIED = 12

	CMD_INSTALL = 0
	CMD_LIST = 1
	CMD_REMOVE = 2
	CMD_UPDATE = 3
	CMD_UPGRADE = 4
	CMD_UPGRADE_LIST = 5

	def __init__(self, opkg='opkg'):
		self.opkg = opkg
		self.cmd = eConsoleAppContainer()
		self.cache = None
		self.callbackList = []
		self.fetchedList = []
		self.excludeList = []
		self.setCurrentCommand()

	def setCurrentCommand(self, command=None):
		self.currentCommand = command

	def runCmdEx(self, cmd):
		self.runCmd("%s %s" % (opkgExtraDestinations(), cmd))

	def runCmd(self, cmd):
		print("[Opkg] executing", self.opkg, cmd)
		self.cmd.appClosed.append(self.cmdFinished)
		self.cmd.dataAvail.append(self.cmdData)
		if self.cmd.execute("%s %s" % (self.opkg, cmd)):
			self.cmdFinished(-1)

	def startCmd(self, cmd, args=None):
		if cmd == self.CMD_UPDATE:
			if getImageVersion() == '4.0':
				if os.path.exists('/var/lib/opkg/lists'):
					rmtree('/var/lib/opkg/lists')
			else:
				for fn in os.listdir('/var/lib/opkg'):
					if fn.startswith(getImageDistro()):
						os.remove('/var/lib/opkg/' + fn)
			self.runCmdEx("update")
		elif cmd == self.CMD_UPGRADE:
			append = ""
			if args["test_only"]:
				append = " -test"
			if len(self.excludeList) > 0:
				for x in self.excludeList:
					print("[Opkg] exclude Package (hold): '%s'" % x[0])
					os.system("opkg flag hold " + x[0])
			self.runCmdEx("upgrade" + append)
		elif cmd == self.CMD_LIST:
			self.fetchedList = []
			self.excludeList = []
			if args['installed_only']:
				self.runCmdEx("list_installed")
			else:
				self.runCmd("list")
		elif cmd == self.CMD_INSTALL:
			self.runCmd("--force-overwrite install %s" % args['package'])
		elif cmd == self.CMD_REMOVE:
			self.runCmd("remove %s" % args['package'])
		elif cmd == self.CMD_UPGRADE_LIST:
			self.fetchedList = []
			self.excludeList = []
			self.runCmd("list-upgradable")
		self.setCurrentCommand(cmd)

	def cmdFinished(self, retval):
		self.callCallbacks(self.EVENT_DONE)
		self.cmd.appClosed.remove(self.cmdFinished)
		self.cmd.dataAvail.remove(self.cmdData)
		if len(self.excludeList) > 0:
			for x in self.excludeList:
				print("[Opkg] restore Package flag (unhold): '%s'" % x[0])
				os.system("opkg flag ok " + x[0])

	def cmdData(self, data):
		if PY3:
			data = data.decode()
		# print("[Opkg] data:", data)
		if self.cache is None:
			self.cache = data
		else:
			self.cache += data

		if '\n' in data:
			splitcache = self.cache.split('\n')
			if self.cache[-1] == '\n':
				iteration = splitcache
				self.cache = None
			else:
				iteration = splitcache[:-1]
				self.cache = splitcache[-1]
			for mydata in iteration:
				if mydata != '':
					self.parseLine(mydata)

	def parseLine(self, data):
		if self.currentCommand in (self.CMD_LIST, self.CMD_UPGRADE_LIST):
			item = data.split(' - ', 2)
			try:
				# workaround when user use update with own button config
				if config.plugins.softwaremanager.overwriteSettingsFiles.value:
					pass
			except:
				Load_defaults()
			if item[0].find('-settings-') > -1 and not config.plugins.softwaremanager.overwriteSettingsFiles.value:
				self.excludeList.append(item)
				return
			elif item[0].find('kernel-module-') > -1 and not config.plugins.softwaremanager.overwriteDriversFiles.value:
				self.excludeList.append(item)
				return
			elif item[0].find('-softcams-') > -1 and not config.plugins.softwaremanager.overwriteEmusFiles.value:
				self.excludeList.append(item)
				return
			elif item[0].find('-picons-') > -1 and not config.plugins.softwaremanager.overwritePiconsFiles.value:
				self.excludeList.append(item)
				return
			elif item[0].find('-bootlogo') > -1 and not config.plugins.softwaremanager.overwriteBootlogoFiles.value:
				self.excludeList.append(item)
				return
			elif item[0].find('openatv-spinner') > -1 and not config.plugins.softwaremanager.overwriteSpinnerFiles.value:
				self.excludeList.append(item)
				return
			else:
				self.fetchedList.append(item)
				self.callCallbacks(self.EVENT_LISTITEM, item)
				return

		try:
			if data.startswith('Downloading'):
				self.callCallbacks(self.EVENT_DOWNLOAD, data.split(' ', 5)[1].strip())
			elif data.startswith('Upgrading'):
				self.callCallbacks(self.EVENT_UPGRADE, data.split(' ', 2)[1])
			elif data.startswith('Installing'):
				self.callCallbacks(self.EVENT_INSTALL, data.split(' ', 2)[1])
			elif data.startswith('Removing'):
				self.callCallbacks(self.EVENT_REMOVE, data.split(' ', 3)[2])
			elif data.startswith('Configuring'):
				self.callCallbacks(self.EVENT_CONFIGURING, data.split(' ', 2)[1])
			elif data.startswith('An error occurred'):
				self.callCallbacks(self.EVENT_ERROR, None)
			elif data.startswith('Failed to download'):
				self.callCallbacks(self.EVENT_ERROR, None)
			elif data.startswith('opkg_download: ERROR:'):
				self.callCallbacks(self.EVENT_ERROR, None)
			elif data.find('Configuration file \'') >= 0:
				# Note: the config file update question doesn't end with a newline, so
				# if we get multiple config file update questions, the next ones
				# don't necessarily start at the beginning of a line
				self.callCallbacks(self.EVENT_MODIFIED, data.split(' \'', 3)[1][:-1])
		except Exception as ex:
			print("[Opkg] Failed to parse: '%s'" % data)
			print("[Opkg]", ex)

	def callCallbacks(self, event, param=None):
		for callback in self.callbackList:
			callback(event, param)

	def addCallback(self, callback):
		self.callbackList.append(callback)

	def removeCallback(self, callback):
		self.callbackList.remove(callback)

	def getFetchedList(self):
		return self.fetchedList

	def getExcludeList(self):
		return self.excludeList

	def stop(self):
		self.cmd.kill()

	def isRunning(self):
		return self.cmd.running()

	def write(self, what):
		if what:
			# We except unterminated commands
			what += "\n"
			self.cmd.write(what, len(what))

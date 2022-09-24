from enigma import eConsoleAppContainer
from os import listdir, readlink, symlink, unlink
from os.path import exists, split as pathsplit


class CamControl:
	'''CAM convention is that a softlink named /etc/init.c/softcam.* points
	to the start/stop script.'''

	def __init__(self, name, callback=None):
		self.name = name
		self.container = eConsoleAppContainer()
		self.callback = callback
		if callback:
			self.container.appClosed.append(self.commandFinished)
		self.link = '/etc/init.d/' + name
		if not exists(self.link):
			print("[CamControl] No softcam link: '%s'" % self.link)

	def getList(self):
		result = []
		prefix = self.name + '.'
		for f in listdir("/etc/init.d"):
			if f.startswith(prefix):
				result.append(f[len(prefix):])
		return result

	def current(self):
		try:
			l = readlink(self.link)
			prefix = self.name + '.'
			return pathsplit(l)[1].split(prefix, 2)[1]
		except OSError:
			pass
		return None

	def command(self, cmd):
		if exists(self.link):
			cmd = "%s %s" % (self.link, cmd)
			print("[CamControl] Executing Command '%s'" % cmd)
			self.container.execute(cmd)

	def commandFinished(self, retval):
		if self.callback:
			self.callback()

	def select(self, which):
		print("[CamControl] Select Cam: %s" % which)
		if not which:
			which = "None"
		dst = "%s.%s" % (self.name, which)
		if not exists('/etc/init.d/%s' % dst):
			print("[CamControl] init script '%s' does not exist" % dst)
			return
		try:
			unlink(self.link)
		except OSError:
			pass
		try:
			symlink(dst, self.link)
		except OSError:
			print("[CamControl] Failed to create symlink for softcam: %s" % dst)
			import sys
			print(sys.exc_info()[:2])

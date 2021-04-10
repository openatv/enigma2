import os
import enigma

class CamControl:
	'''CAM convention is that a softlink named /etc/init.c/softcam.* points
	to the start/stop script.'''
	def __init__(self, name):
		self.name = name
		self.link = '/etc/init.d/' + name
		if not os.path.exists(self.link):
			print "[CamControl] No softcam link?", self.link

	def getList(self):
		result = []
		prefix = self.name + '.'
		for f in os.listdir("/etc/init.d"):
			if f.startswith(prefix):
				result.append(f[len(prefix):])
		return result

	def current(self):
		try:
			l = os.readlink(self.link)
			prefix = self.name + '.'
			return os.path.split(l)[1].split(prefix, 2)[1]
		except:
			pass
		return None

	def command(self, cmd):
		if os.path.exists(self.link):
			print "Executing", self.link + ' ' + cmd
			enigma.eConsoleAppContainer().execute(self.link + ' ' + cmd)

	def select(self, which):
		print "Selecting CAM:", which
		if not which:
			which = "None"
		dst = self.name + '.' + which
		if not os.path.exists('/etc/init.d/' + dst):
			print "[CamControl] init script does not exist:", dst
			return 
		try:
			os.unlink(self.link)
		except:
			pass
		try:
			os.symlink(dst, self.link)
		except:
			print "Failed to create symlink for softcam:", dst
			import sys
			print sys.exc_info()[:2]


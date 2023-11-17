from os import listdir, readlink
from os.path import exists, join, islink, split as pathsplit
from socket import socket, AF_UNIX, SOCK_STREAM


class CamControl:
	'''CAM convention is that a softlink named /etc/init.c/softcam.* points
	to the start/stop script.'''

	def __init__(self, name):
		self.name = name
		self.notFound = None
		self.link = join("/etc/init.d", name)
		if not exists(self.link):
			print(f"[CamControl] No softcam link: '{self.link}'")
			if islink(self.link) and exists("/etc/init.d/softcam.None"):
				target = self.current()
				if target:
					self.notFound = target
					print(f"[CamControl] wrong target '{target}' set to None")
					self.switch("None")  # wrong link target set to None

	def getList(self):
		result = []
		prefix = f"{self.name}."
		for f in listdir("/etc/init.d"):
			if f.startswith(prefix):
				result.append(f[len(prefix):])
		return result

	def current(self):
		try:
			l = readlink(self.link)
			prefix = f"{self.name}."
			return pathsplit(l)[1].split(prefix, 2)[1]
		except OSError:
			pass
		return None

	def switch(self, newcam):
		deamonSocket = socket(AF_UNIX, SOCK_STREAM)
		deamonSocket.connect("/tmp/deamon.socket")
		deamonSocket.send(f"SWITCH_{self.name.upper()},{newcam}".encode())
		deamonSocket.close()

	def restart(self):
		deamonSocket = socket(AF_UNIX, SOCK_STREAM)
		deamonSocket.connect("/tmp/deamon.socket")
		deamonSocket.send(f"RESTART,{self.name}".encode())
		deamonSocket.close()

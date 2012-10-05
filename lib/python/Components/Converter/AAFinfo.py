from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.Harddisk import Harddisk
from re import search

class AAFinfo(Converter, object):

	def __init__(self, type):
		Converter.__init__(self, type)
		if type == "Harddiskspace":
			self.type = 1
		elif type == "HarddiskspaceText":
			self.type = 2
		else:
			self.type = -1

	@cached
	def getValue(self):
		if self.type == 1:
			return (100 - self.Harddiskspace())

	def getText(self):
		if self.type == 2:
			used = str(self.Harddiskspace())
			return (used + " %")

	value = property(getValue)
	text = property(getText)

	def Harddiskspace(self):
		list2 = []
		f = open('/proc/partitions', 'r')
		for line in f.readlines():
			parts = line.strip().split()
			if not parts:
				continue
			device = parts[3]
			if not search('sd[a-z][1-9]',device):
				continue
			if device in list2:
				continue

			mount = '/dev/' + device
			f = open('/proc/mounts', 'r')
			for line in f.readlines():
				if line.find(device) != -1:
					parts = line.strip().split()
					mount = str(parts[1])
					break
					continue
			f.close()

			if mount.startswith('/media/hdd'):
				size = Harddisk(device).diskSize() + 0.0
				free = Harddisk(device).free()
				used = size - free + 0.0
				Pused = int((used / size) * 100)
				return Pused

		return 0


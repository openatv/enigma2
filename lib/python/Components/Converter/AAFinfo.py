from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.Harddisk import Harddisk
from re import search

class AAFinfo(Converter, object):

	def __init__(self, type):
		Converter.__init__(self, type)
		self.usedspace = self.Harddiskspace()
	
		if type == "Harddiskspace":
			self.type = 1
		elif type == "HarddiskspaceText":
			self.type = 2
		else:
			self.type = -1

	@cached
	def getValue(self):
		if self.type == 1:
			return self.scaleValue(self.usedspace)

	def getText(self):
		if self.type == 2:
			used = str(self.usedspace)
			return (used + " %")

	value = property(getValue)
	text = property(getText)

	def scaleValue(self, value):
		if value > 100:
			return 41
		elif value < 0:
			return 59
		elif 0 <= value <= 100:
			# scale to use the upper half of the gauge (0>100 == 58>41)
			tmp = int((value + 0.0)  * 0.83)
			if 0 <= tmp <= 41:
				# 0>41 = 58>100
				return (tmp + 58)
			elif 41 < tmp <= 82:
				# 42>82 = 1>41
				return (tmp - 41)
			else:
				return 0
		else:
			return 0

	def Harddiskspace(self):
		print"Harddiskspace"
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


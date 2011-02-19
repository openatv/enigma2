from Tools.Directories import resolveFilename, SCOPE_SYSETC
from enigma import getEnigmaVersionString
from os import popen

class About:
	def __init__(self):
		pass

	def getVersionString(self):
		return self.getImageVersionString()

	def getImageVersionString(self):
		try:
			fd = open("/proc/stb/info/version","r")
			version = fd.read()
			print 'int val',int(version.split()[0],16)
			if int(version,16) < 0x130000 and int(version,16) > 0x110000:
				box_type="Duo"
			elif int(version,16) > 0x140000:
				box_type="Solo"
			elif int(version,16) > 0x1 and int(version,16) < 0x3:
				box_type="ET9000"
		except:
			box_type=""

		try:
			file = open(resolveFilename(SCOPE_SYSETC, 'image-version'), 'r')
			lines = file.readlines()
			for x in lines:
				splitted = x.split('=')
				if splitted[0] == "version":
					#     YYYY MM DD hh mm
					#0120 2005 11 29 01 16
					#0123 4567 89 01 23 45
					version = splitted[1]
					image_type = version[0] # 0 = release, 1 = experimental
					major = version[1]
					minor = version[2]
					revision = version[3]
					year = version[4:8]
					month = version[8:10]
					day = version[10:12]
					date = '-'.join((year, month, day))
					if image_type == '0':
						image_type = "Release v"
						version = '.'.join((major, minor, revision))
						ver = ''.join((image_type, version))
						return ' '.join((box_type, ver, ' - ', date))
					else:
						image_type = "Experimental"
						return ' '.join((box_type, image_type, ' - ', date))
			file.close()
		except IOError:
			pass

		return "unavailable"

	def getEnigmaVersionString(self):
		return getEnigmaVersionString()

	def getKernelVersionString(self):
		try:
			result = popen("uname -r","r").read().strip("\n").split('-')
			kernel_version = result[0]
			return kernel_version
		except:
			pass

		return "unknown"

about = About()

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
				if splitted[0] == "build_type":
					image_type = splitted[1].replace('\n','') # 0 = release, 1 = experimental
				elif splitted[0] == "version":
					version = splitted[1].replace('\n','')
				elif splitted[0] == "date":
					#YYYY MM DD hh mm
					#2005 11 29 01 16
					date = splitted[1].replace('\n','')
					year = date[0:4]
					month = date[4:6]
					day = date[6:8]
					date = '-'.join((year, month, day))
			file.close()
		except IOError:
			pass

		if image_type == '0':
			image_type = "Release v"
			ver = ''.join((image_type, version))
			return ' '.join((box_type, ver, ' - ', date))
		else:
			image_type = "Experimental"
			return ' '.join((box_type, image_type, ' - ', date))

		return "unavailable"

	def getImageUpdateAvailable(self):
		try:
			file = open(resolveFilename(SCOPE_SYSETC, 'image-version'), 'r')
			lines = file.readlines()
			for x in lines:
				splitted = x.split('=')
				if splitted[0] == "date":
					currentversion = splitted[1].replace('\n','')
			file.close()
			file = open('/tmp/online-image-version', 'r')
			lines = file.readlines()
			for x in lines:
				splitted = x.split('=')
				if splitted[0] == "date":
					onlineversion = splitted[1].replace('\n','')
			file.close()
			if onlineversion > currentversion:
				print '[VersionCheck] New online version found'
				return True
			else:
				return False

		except IOError:
			return False

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

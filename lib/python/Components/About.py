from Tools.Directories import resolveFilename, SCOPE_SYSETC
from enigma import getEnigmaVersionString
from os import popen

class About:
	def __init__(self):
		pass

	def getVersionString(self):
		return self.getImageVersionString()

	def getLastUpdateString(self):
		try:
			file = open(resolveFilename(SCOPE_SYSETC, 'image-version'), 'r')
			lines = file.readlines()
			for x in lines:
				splitted = x.split('=')
				if splitted[0] == "date":
					#YYYY MM DD hh mm
					#2005 11 29 01 16
					date = splitted[1].replace('\n','')
					year = date[0:4]
					month = date[4:6]
					day = date[6:8]
					date = '-'.join((year, month, day))
			file.close()
			return date
		except IOError:
			return "unavailable"

	def getImageVersionString(self):
		try:
			file = open(resolveFilename(SCOPE_SYSETC, 'image-version'), 'r')
			lines = file.readlines()
			for x in lines:
				splitted = x.split('=')
				if splitted[0] == "version":
					version = splitted[1].replace('\n','')
			file.close()
			return version
		except IOError:
			return "unavailable"

	def getImageTypeString(self):
		try:
			file = open(resolveFilename(SCOPE_SYSETC, 'image-version'), 'r')
			lines = file.readlines()
			for x in lines:
				splitted = x.split('=')
				if splitted[0] == "build_type":
					image_type = splitted[1].replace('\n','') # 0 = release, 1 = experimental
			file.close()
			if image_type == '0':
				image_type = "Release"
			else:
				image_type = "Experimental"
			return image_type
		except IOError:
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

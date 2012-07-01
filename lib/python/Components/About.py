from Tools.Directories import resolveFilename, SCOPE_SYSETC
from Tools.HardwareInfo import HardwareInfo
import sys

def getVersionString():
	return getImageVersionString()

def getImageVersionString():
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

def getEnigmaVersionString():
	import enigma
	enigma_version = enigma.getEnigmaVersionString()
	return enigma_version

def getKernelVersionString():
	return HardwareInfo().linux_kernel()

def getBuildVersionString():
	try:
		file = open(resolveFilename(SCOPE_SYSETC, 'image-version'), 'r')
		lines = file.readlines()
		for x in lines:
			splitted = x.split('=')
			if splitted[0] == "build":
				version = splitted[1].replace('\n','')
		file.close()
		return version
	except IOError:
		return "unavailable"

def getLastUpdateString():
	try:
		file = open(resolveFilename(SCOPE_SYSETC, 'image-version'), 'r')
		lines = file.readlines()
		for x in lines:
			splitted = x.split('=')
			if splitted[0] == "date":
				#YYYY MM DD hh mm
				#2005 11 29 01 16
				string = splitted[1].replace('\n','')
				year = string[0:4]
				month = string[4:6]
				day = string[6:8]
				date = '-'.join((year, month, day))
				hour = string[8:10]
				minute = string[10:12]
				time = ':'.join((hour, minute))
				lastupdated = ' '.join((date, time))
		file.close()
		return lastupdated
	except IOError:
		return "unavailable"

def getImageTypeString():
	try:
		file = open(resolveFilename(SCOPE_SYSETC, 'image-version'), 'r')
		lines = file.readlines()
		for x in lines:
			splitted = x.split('=')
			if splitted[0] == "build_type":
				image_type = splitted[1].replace('\n','') # 0 = release, 1 = experimental
		file.close()
		if image_type == '0':
			image_type = _("Release")
		else:
			image_type = _("Experimental")
		return image_type
	except IOError:
		return "unavailable"

# For modules that do "from About import about"
about = sys.modules[__name__]

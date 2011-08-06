import sys
import os
import time

def getVersionString():
	return getImageVersionString()

def getImageVersionString():
	try:
		st = os.stat('/usr/lib/ipkg/status')
		tm = time.localtime(st.st_mtime)
		if tm.tm_year >= 2011:
			return time.strftime("%b %e %Y %H:%M:%S", tm)
	except:
		pass
	return "unavailable"

def getEnigmaVersionString():
	import enigma
	enigma_version = enigma.getEnigmaVersionString()
	if '-(no branch)' in enigma_version:
		enigma_version = enigma_version [:-12]
	return enigma_version

def getKernelVersionString():
	try:
		return open("/proc/version","r").read().split(' ', 4)[2].split('-',2)[0]
	except:
		return "unknown"

def getHardwareTypeString():
	value = "Unavailable"
	if os.path.isfile("/etc/hostname"):
		file = open("/etc/hostname","r")
		value = file.readline().strip().upper()
		file.close()
	return value

def getImageTypeString():
	value="Undefined"
	if os.path.isfile("/etc/issue"):
		file = open("/etc/issue","r")
		while 1:
			line = file.readline()
			if not line:
				break
			if "pli" in line and "\\" in line:
				value = line[:line.index("\\")].strip().capitalize()
				break
		file.close()
	return value

# For modules that do "from About import about"
about = sys.modules[__name__]

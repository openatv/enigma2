from Tools.Directories import resolveFilename, SCOPE_SYSETC
from enigma import getEnigmaVersionString
import os
import time

class About:
	def __init__(self):
		pass

	def getVersionString(self):
		return self.getImageVersionString()

	def getImageVersionString(self):
		try:
			st = os.stat('/usr/lib/ipkg/status')
			tm = time.localtime(st.st_mtime)
			return time.strftime("%b %e %Y %H:%M:%S", tm)
		except:
			pass
		return "unavailable"

	def getEnigmaVersionString(self):
		enigma_version = getEnigmaVersionString()
		if '-(no branch)' in enigma_version:
			enigma_version = enigma_version [:-12]
		return enigma_version

	def getKernelVersionString(self):
		try:
			result = popen("uname -r","r").read().strip("\n").split('-')
			kernel_version = result[0]
			return kernel_version
		except:
			pass

		return "unknown"

about = About()

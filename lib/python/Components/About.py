from Tools.Directories import resolveFilename, SCOPE_SYSETC
from enigma import getEnigmaVersionString
import os 

class About:
	def __init__(self):
		pass

	def getVersionString(self):
		return self.getImageVersionString()

	def getImageVersionString(self):
		try:
			image_status = os.popen('ls -le /usr/lib/ipkg/status').read()
			return  image_status[47:53]+image_status[62:67]+image_status[53:62]
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

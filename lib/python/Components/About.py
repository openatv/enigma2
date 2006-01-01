from Tools.Directories import *

class About:
	def __init__(self):
		pass
	
	def getVersionString(self):
		file = open(resolveFilename(SCOPE_SYSETC, 'image-version'), 'r')
		lines = file.readlines()
		for x in lines:
			splitted = x.split('=')
			if splitted[0] == "version":
				return "2.0-" + str(splitted[1])
		file.close()
		return "2.0b"
	
about = About()
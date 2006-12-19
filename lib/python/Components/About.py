from Tools.Directories import resolveFilename, SCOPE_SYSETC

class About:
	def __init__(self):
		pass
	
	def getVersionString(self):
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
					year = version[4:8]
					month = version[8:10]
					day = version[10:12]
					
					return '-'.join(["2.1", year, month, day])
			file.close()
		except IOError:
			pass

		return "unavailable"
	
about = About()

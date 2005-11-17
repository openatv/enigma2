from xml.sax import make_parser
from xml.sax.handler import ContentHandler

class Timezones:
	class parseTimezones(ContentHandler):
		def __init__(self, timezones):
			self.isPointsElement, self.isReboundsElement = 0, 0
			self.timezones = timezones
	
		def startElement(self, name, attrs):
			print "Name: " + str(name)
			if (name == "zone"):
				self.timezones[attrs.get('name',"")] = attrs.get('zone',"")
				#print "found sat " + attrs.get('name',"") + " " + str(attrs.get('position',""))
				#tpos = attrs.get('position',"")
				#tname = attrs.get('name',"")
				#self.satellites[tpos] = tname
				#self.satList.append( (tname, tpos) )
				#self.parsedSat = int(tpos)
	
	def __init__(self):
		self.timezones = {}
		
		self.readTimezonesFromFile()

	def readTimezonesFromFile(self):
		parser = make_parser()
		timezonesHandler = self.parseTimezones(self.timezones)
		parser.setContentHandler(timezonesHandler)
		parser.parse('/etc/timezone.xml')
		

timezones = Timezones()

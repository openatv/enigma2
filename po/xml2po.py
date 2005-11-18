#!/usr/bin/python
import sys
from xml.sax import make_parser
from xml.sax.handler import ContentHandler

class parseXML(ContentHandler):
	def __init__(self):
		self.isPointsElement, self.isReboundsElement = 0, 0

	def startElement(self, name, attrs):
		if (attrs.has_key('text')):
			print
			print '#: ' + sys.argv[1]
			print 'msgid "' + str(attrs.get('text', "")) + '"'
			print 'msgstr ""'

sys.argv[1]

parser = make_parser()
		
contentHandler = parseXML()
parser.setContentHandler(contentHandler)
parser.parse(sys.argv[1])

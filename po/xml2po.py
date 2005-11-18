#!/usr/bin/python
import sys
from xml.sax import make_parser
from xml.sax.handler import ContentHandler

class parseXML(ContentHandler):
	def __init__(self, attrlist):
		self.isPointsElement, self.isReboundsElement = 0, 0
		self.attrlist = attrlist

	def startElement(self, name, attrs):
		if (attrs.has_key('text')):
			attrlist[attrs.get('text', "")] = "foo"

sys.argv[1]

parser = make_parser()

attrlist = {}		
contentHandler = parseXML(attrlist)
parser.setContentHandler(contentHandler)
parser.parse(sys.argv[1])

for k, v in attrlist.items():
	print
	print '#: ' + sys.argv[1]
	print 'msgid "' + str(k) + '"'
	print 'msgstr ""'


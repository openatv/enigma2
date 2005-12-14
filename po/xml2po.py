#!/usr/bin/python
import sys
import os
import string
from xml.sax import make_parser
from xml.sax.handler import ContentHandler

class parseXML(ContentHandler):
	def __init__(self, attrlist):
		self.isPointsElement, self.isReboundsElement = 0, 0
		self.attrlist = attrlist

	def startElement(self, name, attrs):
		if (attrs.has_key('text')):
			attrlist[attrs.get('text', "")] = "foo"
		if (attrs.has_key('title')):
			attrlist[attrs.get('title', "")] = "foo"
		if (attrs.has_key('value')):
			attrlist[attrs.get('value', "")] = "foo"
		if (attrs.has_key('caption')):
			attrlist[attrs.get('caption', "")] = "foo"

parser = make_parser()

attrlist = {}		

contentHandler = parseXML(attrlist)
parser.setContentHandler(contentHandler)

dir = os.listdir(sys.argv[1])
for x in dir:
	if (str(x[-4:]) == ".xml"):
		parser.parse(sys.argv[1] + str(x))

#parser.parse(sys.argv[1])

for k, v in attrlist.items():
	print
	print '#: ' + sys.argv[1]
	string.replace(k, "\\n", "\"\n\"")
	print 'msgid "' + str(k) + '"'
	print 'msgstr ""'


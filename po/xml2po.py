#!/usr/bin/python
import sys
import os
import string
from xml.sax import make_parser
from xml.sax.handler import ContentHandler, property_lexical_handler
try:
	from _xmlplus.sax.saxlib import LexicalHandler
	no_comments = False
except ImportError:
	class LexicalHandler:
		pass
	no_comments = True

class parseXML(ContentHandler, LexicalHandler):
	def __init__(self, attrlist):
		self.isPointsElement, self.isReboundsElement = 0, 0
		self.attrlist = attrlist
		self.last_comment = None

	def comment(self, comment):
		if comment.find("TRANSLATORS:") != -1:
			self.last_comment = comment

	def startElement(self, name, attrs):
		for x in ["text", "title", "value", "caption"]:
			try:
				attrlist.add((attrs[x], self.last_comment))
				self.last_comment = None
			except KeyError:
				pass

parser = make_parser()

attrlist = set()

contentHandler = parseXML(attrlist)
parser.setContentHandler(contentHandler)
if not no_comments:
	parser.setProperty(property_lexical_handler, contentHandler)
dir = os.listdir(sys.argv[1])
for x in dir:
	if (str(x[-4:]) == ".xml"):
		parser.parse(sys.argv[1] + str(x))

#parser.parse(sys.argv[1])

attrlist = list(attrlist)
attrlist.sort(key=lambda a: a[0])

for (k,c) in attrlist:
	print
	print '#: ' + sys.argv[1]
	string.replace(k, "\\n", "\"\n\"")
	if c:
		for l in c.split('\n'):
			print "#. ", l
	if str(k) != "":
		print 'msgid "' + str(k) + '"'
		print 'msgstr ""'


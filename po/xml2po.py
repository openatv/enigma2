from sys import argv
from os import listdir
from os.path import isdir, join
from re import compile
from xml.sax import make_parser
from xml.sax.handler import ContentHandler, LexicalHandler, property_lexical_handler


class parseXML(ContentHandler, LexicalHandler):
	def __init__(self, attributes):
		self.attributes = attributes
		self.lastComment = None
		self.isHex = compile(r'#[0-9a-fA-F]+\Z')

	def comment(self, comment):
		if "TRANSLATORS:" in comment:
			self.lastComment = comment

	def startElement(self, tag, attribs):
		for attribute in ["text", "title", "value", "caption", "description", "red", "green", "yellow", "blue"]:  # Attributes that need to be translated.
			try:
				value = attribs[attribute]
				if value.strip() != "" and not self.isHex.match(value):
					attributes.add((value, self.lastComment))
					self.lastComment = None
			except KeyError:
				pass


parser = make_parser()
attributes = set()
contentHandler = parseXML(attributes)
parser.setContentHandler(contentHandler)
parser.setProperty(property_lexical_handler, contentHandler)
for arg in argv[1:]:
	if isdir(arg):
		for file in listdir(arg):
			if file.endswith(".xml"):
				parser.parse(join(arg, file))
	else:
		parser.parse(arg)
	attributes = list(attributes)
	attributes.sort(key=lambda x: x[0])
	for (key, value) in attributes:
		print("\n#: %s" % arg)
		key.replace("\\n", "\"\n\"")
		if value:
			for line in value.split("\n"):
				print("#. %s" % line)
		print("msgid \"%s\"" % key)
		print("msgstr \"\"")
	attributes = set()

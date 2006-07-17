#
# OK, this is more a proof of concept
# things to improve:
#  - nicer code
#  - screens need to be defined somehow else. 
#    I don't know how, yet. Probably each in an own file.
#  - more components, like the channellist
#  - better error handling
#  - use namespace parser

from Screens.Screen import Screen
from Tools.Import import my_import

# for our testscreen
from Screens.InfoBarGenerics import InfoBarServiceName, InfoBarEvent
from Components.Sources.Clock import Clock

from xml.sax import make_parser
from xml.sax.handler import ContentHandler, feature_namespaces
from twisted.python import util
import sys
import time

# prototype of the new web frontend template system.

# a test screen
class TestScreen(InfoBarServiceName, InfoBarEvent, Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		InfoBarServiceName.__init__(self)
		InfoBarEvent.__init__(self)
		self["CurrentTime"] = Clock()

# turns .text into __str__ 
class Element:
	def __init__(self, source):
		self.source = source

	def __str__(self):
		return self.source.text

# a to-be-filled list item
class ListItem:
	def __init__(self, name):
		self.name = name

# the performant 'listfiller'-engine (plfe)
class ListFiller(object):
	def __init__(self, arg):
		self.template = arg
		
	def getText(self):
		l = self.source.list
		lut = self.source.lut
		
		# now build a ["string", 1, "string", 2]-styled list, with indices into the 
		# list to avoid lookup of item name for each entry
		lutlist = []
		for element in self.template:
			if isinstance(element, str):
				lutlist.append(element)
			elif isinstance(element, ListItem):
				lutlist.append(lut[element.name])
		
		# now, for the huge list, do:
		res = ""
		for item in l:
			for element in lutlist:
				if isinstance(element, str):
					res += element
				else:
					res += str(item[element])
		# (this will be done in c++ later!)
		return res
		
	text = property(getText)

class webifHandler(ContentHandler):
	def __init__(self, session):
		self.res = [ ]
		self.mode = 0
		self.screen = None
		self.session = session
	
	def startElement(self, name, attrs):
		if name == "e2:screen":
			self.screen = eval(attrs["name"])(self.session) # fixme
			return
	
		if name[:3] == "e2:":
			self.mode += 1
		
		tag = "<" + name + ''.join([' ' + key + '="' + val + '"' for (key, val) in attrs.items()]) + ">"
		tag = tag.encode("UTF-8")
		
		if self.mode == 0:
			self.res.append(tag)
		elif self.mode == 1: # expect "<e2:element>"
			assert name == "e2:element", "found %s instead of e2:element" % name
			self.source = self.screen[attrs["source"]]
		elif self.mode == 2: # expect "<e2:convert>"
			if name[:3] == "e2:":
				assert name == "e2:convert"
				
				ctype = attrs["type"]
				if ctype[:4] == "web:": # for now
					self.converter = eval(ctype[4:])
				else:
					self.converter = my_import('.'.join(["Components", "Converter", ctype])).__dict__.get(ctype)
				self.sub = [ ]
			else:
				self.sub.append(tag)
		elif self.mode == 3:
			assert name == "e2:item", "found %s instead of e2:item!" % name
			self.sub.append(ListItem(attrs["name"]))

	def endElement(self, name):
		if name == "e2:screen":
			self.screen = None
			return

		tag = "</" + name + ">"
		if self.mode == 0:
			self.res.append(tag)
		elif self.mode == 2 and name[:3] != "e2:":
			self.sub.append(tag)
		elif self.mode == 2: # closed 'convert' -> sub
			self.sub = lreduce(self.sub)
			if len(self.sub) == 1:
				self.sub = self.sub[0]
			c = self.converter(self.sub)
			c.connect(self.source)
			self.source = c
			
			del self.sub
		elif self.mode == 1: # closed 'element'
			self.res.append(Element(self.source))
			del self.source

		if name[:3] == "e2:":
			self.mode -= 1

	def processingInstruction(self, target, data):
		self.res.append('<?' + target + ' ' + data + '>')
	
	def characters(self, ch):
		ch = ch.encode("UTF-8")
		if self.mode == 0:
			self.res.append(ch)
		elif self.mode == 2:
			self.sub.append(ch)
	
	def startEntity(self, name):
		self.res.append('&' + name + ';');

def lreduce(list):
	# ouch, can be made better
	res = [ ]
	string = None
	for x in list:
		if isinstance(x, str) or isinstance(x, unicode):
			x = x.encode("UTF-8")
			if string is None:
				string = x
			else:
				string += x
		else:
			if string is not None:
				res.append(string)
				string = None
			res.append(x)
	if string is not None:
		res.append(string)
		string = None
	return res

def renderPage(stream, path, session):
	handler = webifHandler(session)
	parser = make_parser()
	parser.setFeature(feature_namespaces, 0)
	parser.setContentHandler(handler)
	parser.parse(open(util.sibpath(__file__, path)))
	for x in lreduce(handler.res):
		stream.write(str(x))
	stream.finish() # must be done, unless we "callLater"

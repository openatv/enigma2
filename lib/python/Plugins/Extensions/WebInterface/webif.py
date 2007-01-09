#
# OK, this is more than a proof of concept
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
#from Components.Sources.Config import Config
from Components.Sources.ServiceList import ServiceList
from Components.Converter.Converter import Converter
#from Components.config import config
from Components.Element import Element

from xml.sax import make_parser
from xml.sax.handler import ContentHandler, feature_namespaces
from twisted.python import util
import sys
import time

# prototype of the new web frontend template system.

class WebScreen(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.stand_alone = True

# a test screen
class TestScreen(InfoBarServiceName, InfoBarEvent, WebScreen):
	def __init__(self, session):
		WebScreen.__init__(self, session)
		InfoBarServiceName.__init__(self)
		InfoBarEvent.__init__(self)
		self["CurrentTime"] = Clock()
#		self["TVSystem"] = Config(config.av.tvsystem)
#		self["OSDLanguage"] = Config(config.osd.language)
#		self["FirstRun"] = Config(config.misc.firstrun)
		from enigma import eServiceReference
		fav = eServiceReference('1:7:1:0:0:0:0:0:0:0:(type == 1) || (type == 17) || (type == 195) || (type == 25) FROM BOUQUET "userbouquet.favourites.tv" ORDER BY bouquet')
		self["ServiceList"] = ServiceList(fav, command_func = self.zapTo)
		self["ServiceListBrowse"] = ServiceList(fav, command_func = self.browseTo)

	def browseTo(self, reftobrowse):
		self["ServiceListBrowse"].root = reftobrowse

	def zapTo(self, reftozap):
		self.session.nav.playService(reftozap)

class Streaming(WebScreen):
	def __init__(self, session):
		WebScreen.__init__(self, session)
		from Components.Sources.StreamService import StreamService
		self["StreamService"] = StreamService(self.session.nav)

# implements the 'render'-call.
# this will act as a downstream_element, like a renderer.
class OneTimeElement(Element):
	def __init__(self, id):
		Element.__init__(self)
		self.source_id = id

	# CHECKME: is this ok performance-wise?
	def handleCommand(self, args):
		for c in args.get(self.source_id, []):
			self.source.handleCommand(c)

	def render(self, stream):
		t = self.source.getHTML(self.source_id)
		if isinstance(t, unicode):
			t = t.encode("utf-8")
		stream.write(t)

	def execBegin(self):
		pass
	
	def execEnd(self):
		pass
	
	def onShow(self):
		pass

	def onHide(self):
		pass
	
	def destroy(self):
		pass

class StreamingElement(OneTimeElement):
	def __init__(self, id):
		OneTimeElement.__init__(self, id)
		self.stream = None

	def changed(self, what):
		if self.stream:
			self.render(self.stream)

	def setStream(self, stream):
		self.stream = stream

# a to-be-filled list item
class ListItem:
	def __init__(self, name):
		self.name = name

class TextToHTML(Converter):
	def __init__(self, arg):
		Converter.__init__(self, arg)

	def getHTML(self, id):
		return self.source.text # encode & etc. here!

# a null-output. Useful if you only want to issue a command.
class Null(Converter):
	def __init__(self, arg):
		Converter.__init__(self, arg)

	def getHTML(self, id):
		return ""

def escape(s):
	return s.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')

class JavascriptUpdate(Converter):
	def __init__(self, arg):
		Converter.__init__(self, arg)

	def getHTML(self, id):
		return '<script>set("' + id + '", "' + escape(self.source.text) + '");</script>\n'

# the performant 'listfiller'-engine (plfe)
class ListFiller(Converter):
	def __init__(self, arg):
		Converter.__init__(self, arg)

	def getText(self):
		l = self.source.list
		lut = self.source.lut
		
		# now build a ["string", 1, "string", 2]-styled list, with indices into the 
		# list to avoid lookup of item name for each entry
		lutlist = []
		for element in self.converter_arguments:
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
		self.screens = [ ]
	
	def startElement(self, name, attrs):
		if name == "e2:screen":
			self.screen = eval(attrs["name"])(self.session) # fixme
			self.screens.append(self.screen)
			return
	
		if name[:3] == "e2:":
			self.mode += 1
		
		tag = "<" + name + ''.join([' ' + key + '="' + val + '"' for (key, val) in attrs.items()]) + ">"
		tag = tag.encode("UTF-8")
		
		if self.mode == 0:
			self.res.append(tag)
		elif self.mode == 1: # expect "<e2:element>"
			assert name == "e2:element", "found %s instead of e2:element" % name
			source = attrs["source"]
			self.source_id = str(attrs.get("id", source))
			self.source = self.screen[source]
			self.is_streaming = "streaming" in attrs
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
			assert "name" in attrs, "e2:item must have a name= attribute!"
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
			# instatiate either a StreamingElement or a OneTimeElement, depending on what's required.
			if not self.is_streaming:
				c = OneTimeElement(self.source_id)
			else:
				c = StreamingElement(self.source_id)
			
			c.connect(self.source)
			self.res.append(c)
			self.screen.renderer.append(c)
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

	def execBegin(self):
		for screen in self.screens:
			screen.execBegin()

	def cleanup(self):
		print "screen cleanup!"
		for screen in self.screens:
			screen.execEnd()
			screen.doClose()
		self.screens = [ ]

def lreduce(list):
	# ouch, can be made better
	res = [ ]
	string = None
	for x in list:
		if isinstance(x, str) or isinstance(x, unicode):
			if isinstance(x, unicode):
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

def renderPage(stream, path, req, session):
	
	# read in the template, create required screens
	# we don't have persistense yet.
	# if we had, this first part would only be done once.
	handler = webifHandler(session)
	parser = make_parser()
	parser.setFeature(feature_namespaces, 0)
	parser.setContentHandler(handler)
	parser.parse(open(util.sibpath(__file__, path)))
	
	# by default, we have non-streaming pages
	finish = True
	
	# first, apply "commands" (aka. URL argument)
	for x in handler.res:
		if isinstance(x, Element):
			x.handleCommand(req.args)

	handler.execBegin()

	# now, we have a list with static texts mixed
	# with non-static Elements.
	# flatten this list, write into the stream.
	for x in lreduce(handler.res):
		if isinstance(x, Element):
			if isinstance(x, StreamingElement):
				finish = False
				x.setStream(stream)
			x.render(stream)
		else:
			stream.write(str(x))

	def ping(s):
		from twisted.internet import reactor
		s.write("\n");
		reactor.callLater(3, ping, s)

	# if we met a "StreamingElement", there is at least one
	# element which wants to output data more than once,
	# i.e. on host-originated changes.
	# in this case, don't finish yet, don't cleanup yet,
	# but instead do that when the client disconnects.
	if finish:
		handler.cleanup()
		stream.finish()
	else:
		# ok.
		# you *need* something which constantly sends something in a regular interval,
		# in order to detect disconnected clients.
		# i agree that this "ping" sucks terrible, so better be sure to have something 
		# similar. A "CurrentTime" is fine. Or anything that creates *some* output.
		ping(stream)
		stream.closed_callback = lambda: handler.cleanup()

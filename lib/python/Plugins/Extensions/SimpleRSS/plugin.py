# warning, this is work in progress.
# plus, the "global_session" stuff is of course very lame.
# plus, the error handling sucks.
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.GUIComponent import GUIComponent
from Components.Label import Label
from Components.MultiContent import MultiContentEntryText, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_WRAP
from Plugins.Plugin import PluginDescriptor
from enigma import eListboxPythonMultiContent, eListbox, gFont, iServiceInformation

from twisted.web import server
from twisted.web.resource import Resource
from twisted.web.client import getPage
import xml.dom.minidom

from Tools.XMLTools import mergeText, elementsWithTag

from enigma import eTimer
from sets import Set

my_global_session = None

urls = ["http://www.heise.de/newsticker/heise.rdf", "http://rss.slashdot.org/Slashdot/slashdot/to"]

from Components.config import config, ConfigSubsection, ConfigSelection, getConfigListEntry
from Components.ConfigList import ConfigList, ConfigListScreen
config.simpleRSS = ConfigSubsection()
config.simpleRSS.hostname = ConfigSelection(choices = urls)

class SimpleRSS(ConfigListScreen, Screen):
	skin = """
		<screen position="100,100" size="550,400" title="Simple RSS Reader" >
		<widget name="config" position="20,10" size="460,350" scrollbarMode="showOnDemand" />
		</screen>"""

	def __init__(self, session, args = None):
		from Tools.BoundFunction import boundFunction
		
		print "screen init"
		Screen.__init__(self, session)
		self.skin = SimpleRSS.skin
		
		self.onClose.append(self.abort)
		
		# nun erzeugen wir eine liste von elementen fuer die menu liste.
		self.list = [ ]
		self.list.append(getConfigListEntry(_("RSS Feed URI"), config.simpleRSS.hostname))
		
		# die liste selbst
		ConfigListScreen.__init__(self, self.list)

		self["actions"] = ActionMap([ "OkCancelActions" ], 
		{
			"ok": self.close,
#			"cancel": self.close,
		})

		self["setupActions"] = ActionMap(["SetupActions"],
		{
			"save": self.save,
			"cancel": self.close
		}, -1)
	
	def abort(self):
		print "aborting"

	def save(self):
		for x in self["config"].list:
			x[1].save()
		self.close()

	def cancel(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close()

class RSSList(GUIComponent):
	def __init__(self, entries):
		GUIComponent.__init__(self)
		self.l = eListboxPythonMultiContent()
		self.l.setFont(0, gFont("Regular", 22))
		self.l.setFont(1, gFont("Regular", 18))
		self.list = [self.buildListboxEntry(x) for x in entries]
		self.l.setList(self.list)

	GUI_WIDGET = eListbox

	def postWidgetCreate(self, instance):
		instance.setContent(self.l)
		instance.setItemHeight(100)

	def buildListboxEntry(self, rss_entry):
		res = [ rss_entry ]
		res.append(MultiContentEntryText(pos=(0, 0), size=(460, 75), font=0, flags = RT_HALIGN_LEFT|RT_WRAP, text = rss_entry[0]))
		res.append(MultiContentEntryText(pos=(0, 75), size=(460, 20), font=1, flags = RT_HALIGN_LEFT, text = rss_entry[1]))
		return res


	def getCurrentEntry(self):
		return self.l.getCurrentSelection()

class RSSDisplay(Screen):
	skin = """
		<screen position="100,100" size="460,400" title="Simple RSS Reader" >
		<widget name="content" position="0,0" size="460,400" />
		</screen>"""

	def __init__(self, session, data, interactive = False):
		Screen.__init__(self, session)
		self.skin = RSSDisplay.skin
		
		if interactive:
			self["actions"] = ActionMap([ "OkCancelActions" ], 
			{
				"ok": self.showCurrentEntry,
				"cancel": self.close,
			})

		self["content"] = RSSList(data) 

	def showCurrentEntry(self):
		current_entry = self["content"].getCurrentEntry()
		if current_entry is None: # empty list
			return

		(title, link, enclosure) = current_entry[0]
		
		if len(enclosure):
			(url, type) = enclosure[0] # TODO: currently, we used the first enclosure. there can be multiple.
			
			print "enclosure: url=%s, type=%s" % (url, type)
			
			if type in ["video/mpeg", "audio/mpeg"]:
				from enigma import eServiceReference
				# we should better launch a player or so...
				self.session.nav.playService(eServiceReference(4097, 0, url))

class RSSPoller:

	MAX_HISTORY_ELEMENTS = 100

	def __init__(self):
		self.poll_timer = eTimer()
		self.poll_timer.timeout.get().append(self.poll)
		self.poll_timer.start(0, 1)
		self.last_links = Set()
		self.dialog = None
		self.history = [ ]
		
	def error(self, error):
		if not my_global_session:
			print "error polling"
		else:
			my_global_session.open(MessageBox, "Sorry, failed to fetch feed.\n" + error)
	
	def _gotPage(self, data):
		# workaround: exceptions in gotPage-callback were ignored
		try:
			self.gotPage(data)
		except:
			import traceback, sys
			traceback.print_exc(file=sys.stdout)
			raise e
	
	def gotPage(self, data):
		print "parsing.."
		
		new_items = [ ]
		
		dom = xml.dom.minidom.parseString(data)
		for r in elementsWithTag(dom.childNodes, "rss"):
			rss = r

		items = [ ]
		
		# RSS 1.0
		for item in elementsWithTag(r.childNodes, "item"):
			items.append(item)

		# RSS 2.0
		for channel in elementsWithTag(r.childNodes, "channel"):
			for item in elementsWithTag(channel.childNodes, "item"):
				items.append(item)

		for item in items:
			title = None
			link = ""
			enclosure = [ ]
			
			print "got item"

			for s in elementsWithTag(item.childNodes, lambda x: x in ["title", "link", "enclosure"]):
				if s.tagName == "title":
					title = mergeText(s.childNodes)
				elif s.tagName == "link":
					link = mergeText(s.childNodes)
				elif s.tagName == "enclosure":
					enclosure.append((s.getAttribute("url").encode("UTF-8"), s.getAttribute("type").encode("UTF-8")))

			print title, link, enclosure
			if title is None:
				continue

			rss_entry = (title.encode("UTF-8"), link.encode("UTF-8"), enclosure)

			self.history.insert(0, rss_entry)

			if link not in self.last_links:
				self.last_links.add(link)
				new_items.append(rss_entry)
				print "NEW", rss_entry[0], rss_entry[1]

		self.history = self.history[:self.MAX_HISTORY_ELEMENTS]
		
		if len(new_items):
			self.dialog = my_global_session.instantiateDialog(RSSDisplay, new_items)
			self.dialog.show()
			self.poll_timer.start(5000, 1)
		else:
			self.poll_timer.start(60000, 1)

	def poll(self):
		if self.dialog:
			print "hiding"
			self.dialog.hide()
			self.dialog = None
			self.poll_timer.start(60000, 1)
		elif not my_global_session:
			print "no session yet."
			self.poll_timer.start(10000, 1)
		else:
			print "yes, session ok. starting"
			self.d = getPage(config.simpleRSS.hostname.value).addCallback(self._gotPage).addErrback(self.error)

	def shutdown(self):
		self.poll_timer.timeout.get().remove(self.poll)
		self.poll_timer = None

def main(session):
	print "session.open"
	session.open(SimpleRSS)
	print "done"

rssPoller = None

def autostart(reason, **kwargs):
	global rssPoller
	
	print "autostart"

	# ouch, this is a hack	
	if kwargs.has_key("session"):
		global my_global_session
		print "session now available"
		my_global_session = kwargs["session"]
		return
	
	print "autostart"
	if reason == 0:
		rssPoller = RSSPoller()
	elif reason == 1:
		rssPoller.shutdown()
		rssPoller = None

def showCurrent(session, **kwargs):
	global rssPoller
	if rssPoller is None:
		return
	session.open(RSSDisplay, rssPoller.history, interactive = True)

def Plugins(**kwargs):
 	return [ PluginDescriptor(name="RSS Reader", description="A (really) simple RSS reader", where = PluginDescriptor.WHERE_PLUGINMENU, fnc=main),
 		PluginDescriptor(where = [PluginDescriptor.WHERE_SESSIONSTART, PluginDescriptor.WHERE_AUTOSTART], fnc = autostart),
 		PluginDescriptor(name="View RSS", description="Let's you view current RSS entries", where = PluginDescriptor.WHERE_EXTENSIONSMENU, fnc=showCurrent) ]

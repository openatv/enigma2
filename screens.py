from components import *
import sys
from enigma import quitMainloop

import xml.dom.minidom
from xml.dom import EMPTY_NAMESPACE
from skin import elementsWithTag


# some screens
def doGlobal(screen):
	screen["clock"] = Clock()

class Screen(dict, HTMLSkin, GUISkin):
	""" bla """

	def __init__(self, session):
		self.skinName = self.__class__.__name__
		self.session = session
		GUISkin.__init__(self)
		
	def execBegin(self):
#		assert self.session == None, "a screen can only exec one per time"
#		self.session = session
		for (name, val) in self.items():
			val.execBegin()
	
	def execEnd(self):
		for (name, val) in self.items():
			val.execEnd()
#		assert self.session != None, "execEnd on non-execing screen!"
#		self.session = None
	
	# never call this directly - it will be called from the session!
	def doClose(self):
		GUISkin.close(self)
		
		del self.session
		for (name, val) in self.items():
			print "%s -> %d" % (name, sys.getrefcount(val))
			del self[name]
	
	def close(self, retval=None):
		self.session.close()


mdom = xml.dom.minidom.parseString(
        """
	<menu text="Mainmenu" title="the real Mainmenu">
		<item text="TV-Mode">self.setModeTV()</item>
		<item text="Radio-Mode">self.setModeRadio()</item>
		<item text="File-Mode">self.setModeFile()</item>
		<item text="Scart">self.openDialog(ScartLoopThrough)</item>
		<item text="Timer"></item>
		<menu text="Setup">
			<menu text="Service Organising">
				<item text="New Bouquets"></item>
				<item text="Add to Bouquets"></item>
				<item text="Edit Bouquets"></item>
			</menu>
			<menu text="Service Searching">
				<item text="Satelliteconfig"></item>
				<item text="Satfinder"></item>
				<item text="Rotor Control"></item>
				<item text="Edit Transponder"></item>
				<item text="Automatic Scan">self.openDialog(serviceScan)</item>
				<item text="Automatic 'Multisat' Scan"></item>
				<item text="Manual Scan"></item>
			</menu>
			<menu text="System">
				<item text="Time Date"></item>
				<item text="Video Audio"></item>
				<item text="UHF Modulator"></item>
				<item text="Harddisk"></item>
				<item text="Keyboard"></item>
				<item text="OSD">self.openDialog(configOSD)</item>
				<item text="Language"></item>
				<item text="LCD"></item>
			</menu>
			<item text="Common Interface"></item>
			<item text="Parental Control"></item>
			<item text="Expert"></item>
		</menu>
		<item text="Games"></item>
		<item text="Information"></item>
		<menu text="Standby">
			<item text="PowerOff"></item>
			<item text="Restart"></item>
			<item text="Standby"></item>
			<item text="Sleep Timer">self.goSetup()</item>
		</menu>
		<item text="Standby debug">quitMainloop()</item>
	</menu>""")

def getText(nodelist):
	rc = ""
	for node in nodelist:
		if node.nodeType == node.TEXT_NODE:
			rc = rc + node.data
	return rc

def getValbyAttr(x, attr):
	for p in range(x.attributes.length):
		a = x.attributes.item(p)
		attrib = str(a.name)
		value = str(a.value)
		if attrib == attr:
			return value
			
	return ""

class boundFunction:
	def __init__(self, fnc, *args):
		self.fnc = fnc
		self.args = args
	def __call__(self):
		self.fnc(*self.args)

class configOSD(Screen):
	#this needs focus handling - so not useable

	def okbuttonClick(self):
		self.close
 
	def __init__(self, session):
		Screen.__init__(self, session)

		self["actions"] = ActionMap(["OkCancelActions"], 
			{
				"ok": self.okbuttonClick,
				"cancel": self.close
			})

		self["okbutton"] = Button("Save")

		self["txt_alpha"] = Label("Alpha:")
		self["sld_alpha"] = ProgressBar()
		self["sld_alpha"].setValue(50)

		self["txt_brightness"] = Label("Brightness:")
		self["sld_brightness"] = ProgressBar()
		self["sld_brightness"].setValue(50)

		self["txt_gamma"] = Label("Contrast:")
		self["sld_gamma"] = ProgressBar()
		self["sld_gamma"].setValue(50)


class ScartLoopThrough(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		self["actions"] = ActionMap(["OkCancelActions"], 
			{
				"cancel": self.close
			})

class ConfigMenu(Screen):
	#create a generic class for view/edit settings
	#all stuff come from xml file
	#configtype / datasource / validate-call / ...

	def __init__(self, session):
		Screen.__init__(self, session)

		self["actions"] = ActionMap(["OkCancelActions"], 
			{
				#"ok": self.okbuttonClick,
				"cancel": self.close
			})

class configTest(Screen):

	def __init__(self, session):
		Screen.__init__(self, session)
		

		self["config"] = ConfigList(
			[
				configEntry("HKEY_LOCAL_ENIGMA/IMPORTANT/USER_ANNOYING_STUFF/SDTV/FLASHES/GREEN"),
				configEntry("HKEY_LOCAL_ENIGMA/IMPORTANT/USER_ANNOYING_STUFF/HDTV/FLASHES/GREEN"),
			])

		self["actions"] = ActionMap(["OkCancelActions"], 
			{
				"ok": self["config"].toggle,
				"cancel": self.close
			})
		

class Menu(Screen):
	#add file load functions for the xml-file
	#remove old code (i.e. goScan / goClock...)

	def openDialog(self, dialog):
		self.session.open(dialog)

	def goSetup(self):
		self.session.open(configTest)
	
	def setModeTV(self):
		print "set Mode to TV"
		pass

	def setModeRadio(self):
		print "set Mode to Radio"
		pass

	def setModeFile(self):
		print "set Mode to File"
		pass

	def goScan(self):
		self.session.open(serviceScan)
	
	def goClock(self):
		self.session.open(clockDisplay, Clock())

	def okbuttonClick(self):
		selection = self["menu"].getCurrent()
		selection[1]()

	def evalText(self, text):
		eval(text)
		
	def nothing(self):																	#dummy
		pass

	def addMenu(self, destList, node):
		MenuTitle = getValbyAttr(node, "text")
		if MenuTitle != "":																	#check for title
			a = boundFunction(self.session.open, Menu, node, node.childNodes)
			#TODO add check if !empty(node.childNodes)
			destList.append((MenuTitle, a))
		
	def addItem(self, destList, node):
		ItemText = getValbyAttr(node, "text")
		if ItemText != "":																	#check for name
			b = getText(node.childNodes)
			if b != "":																				#check for function
				destList.append((ItemText,boundFunction(self.evalText,b)))
			else:
				destList.append((ItemText,self.nothing))				#use dummy as function

	def __init__(self, session, parent, childNode):
		Screen.__init__(self, session)
		
		list = []

		for x in childNode:							#walk through the actual nodelist
			if x.nodeType != xml.dom.minidom.Element.nodeType:
			    continue
			elif x.tagName == 'item':
				self.addItem(list, x)
			elif x.tagName == 'menu':
				self.addMenu(list, x)

		self["menu"] = MenuList(list)	
							
		self["actions"] = ActionMap(["OkCancelActions"], 
			{
				"ok": self.okbuttonClick,
				"cancel": self.close
			})
		
		a = getValbyAttr(parent, "title")
		if a == "":														#if empty use name
			a = getValbyAttr(parent, "text")
		self["title"] = Header(a)

class channelSelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		self["key_red"] = Button("red")
		self["key_green"] = Button("green")
		self["key_yellow"] = Button("yellow")
		self["key_blue"] = Button("blue")
		
		self["list"] = ServiceList()
		self["list"].setRoot(eServiceReference("""1:0:1:0:0:0:0:0:0:0:(provider=="ARD") && (type == 1)"""))
		
		#self["okbutton"] = Button("ok", [self.channelSelected])
		
		class ChannelActionMap(ActionMap):
			def action(self, contexts, action):
				if action[:7] == "bouquet":
					print "setting root to " + action[8:]
					self.csel["list"].setRoot(eServiceReference("1:0:1:0:0:0:0:0:0:0:" + action[8:]))
				else:
					ActionMap.action(self, contexts, action)

		self["actions"] = ChannelActionMap(["ChannelSelectActions", "OkCancelActions"], 
			{
				"cancel": self.close,
				"ok": self.channelSelected,
				"mark": self.doMark
			})
		self["actions"].csel = self

	def doMark(self):
		ref = self["list"].getCurrent()
		if self["list"].isMarked(ref):
			self["list"].removeMarked(ref)
		else:
			self["list"].addMarked(ref)
		
	def channelSelected(self):
		self.session.nav.playService(self["list"].getCurrent())
		self.close()

	#called from infoBar
	def zapUp(self):
		self["list"].moveUp()
		self.session.nav.playService(self["list"].getCurrent())

	def zapDown(self):
		self["list"].moveDown()
		self.session.nav.playService(self["list"].getCurrent())

class infoBar(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		#instantiate forever
		self["ServiceList"] = self.session.instantiateDialog(channelSelection)
		
		self["actions"] = ActionMap( [ "InfobarActions" ], 
			{
				"switchChannel": self.switchChannel,
				"mainMenu": self.mainMenu,
				"zapUp": self.zapUp,
				"zapDown": self.zapDown
			})
		self["okbutton"] = Button("mainMenu", [self.mainMenu])
		
		self["CurrentTime"] = Clock()
		
		self["ServiceName"] = ServiceName(self.session.nav)
		
		self["Event_Now"] = EventInfo(self.session.nav, EventInfo.Now)
		self["Event_Next"] = EventInfo(self.session.nav, EventInfo.Next)

		self["Event_Now_Duration"] = EventInfo(self.session.nav, EventInfo.Now_Duration)
		self["Event_Next_Duration"] = EventInfo(self.session.nav, EventInfo.Next_Duration)
	
	def mainMenu(self):
		print "loading mainmenu XML..."
		menu = mdom.childNodes[0]
		assert menu.tagName == "menu", "root element in menu must be 'menu'!"
		self.session.open(Menu, menu, menu.childNodes)

	def switchChannel(self):	
		self.session.execDialog(self["ServiceList"])

	def	zapUp(self):
		self["ServiceList"].zapUp()

	def	zapDown(self):
		self["ServiceList"].zapDown()

# a clock display dialog
class clockDisplay(Screen):
	def okbutton(self):
		self.session.close()
	
	def __init__(self, session, clock):
		Screen.__init__(self, session)
		self["theClock"] = clock
		b = Button("bye")
		b.onClick = [ self.okbutton ]
		self["okbutton"] = b
		self["title"] = Header("clock dialog: here you see the current uhrzeit!")

class serviceScan(Screen):
	def ok(self):
		print "ok"
		if self["scan"].isDone():
			self.close()
	
	def cancel(self):
		print "cancel not yet implemented ;)"
	
	def __init__(self, session):
		Screen.__init__(self, session)
		
		self["scan_progress"] = ProgressBar()
		self["scan_state"] = Label("scan state")
		self["scan"] = ServiceScan(self["scan_progress"], self["scan_state"])

		self["actions"] = ActionMap(["OkCancelActions"], 
			{
				"ok": self.ok,
				"cancel": self.cancel
			})


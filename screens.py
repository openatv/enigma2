from components import *
import sys
from enigma import quitMainloop

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

class mainMenu(Screen):
	
	def goEmu(self):
		self["title"].setText("EMUs ARE ILLEGAL AND NOT SUPPORTED!")
	
	def goTimeshift(self):
		self["title"].setText("JUST PRESS THE YELLOW BUTTON!")
	
	def goHDTV(self):
		self["title"].setText("HDTV GREEN FLASHES: ENABLED")
	
	def goScan(self):
		self.session.open(serviceScan)
	
	def goClock(self):
		self.session.open(clockDisplay, Clock())

	def okbuttonClick(self):
		selection = self["menu"].getCurrent()
		selection[1]()
	
	def __init__(self, session):
		Screen.__init__(self, session)
		b = Button("ok")

		self["actions"] = ActionMap(["OkCancelActions"], 
			{
				"ok": self.okbuttonClick,
				"cancel": self.close
			})

		b.onClick = [ self.okbuttonClick ]
		self["okbutton"] = b
		self["title"] = Header("Main Menu! - press ok to leave!")
		self["menu"] = MenuList(
			[
				("Close Main Menu", self.close),
				("Service Scan", self.goScan),
				("Quit", quitMainloop),
				("EMU SETUP", self.goEmu),
				("TIMESHIFT SETUP", self.goTimeshift),
				("HDTV PIP CONFIG", self.goHDTV),
				("wie spaet ists?!", self.goClock)
			])

#class mainMenu(Screen):
#	def __init__(self):
#		GUISkin.__init__(self)
#		
#		self["title"] = Header("this is the\nMAIN MENU !!!");
#		self["okbutton"] = Button("ok")
#		self["okbutton"].onClick = [ self.close ]

class channelSelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		
		self["list"] = ServiceList()
		self["list"].setRoot(eServiceReference("""1:0:1:0:0:0:0:0:0:0:(provider=="ARD") && (type == 1)"""))
		
		self["okbutton"] = Button("ok", [self.channelSelected])
		
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
		pass

class infoBar(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		
		self["actions"] = ActionMap( [ "InfobarActions" ], 
			{
				"switchChannel": self.switchChannel,
				"mainMenu": self.mainMenu
			})
		self["okbutton"] = Button("mainMenu", [self.mainMenu])
		
		self["CurrentTime"] = Clock()
		
		self["ServiceName"] = ServiceName(self.session.nav)
		
		self["Event_Now"] = EventInfo(self.session.nav, EventInfo.Now)
		self["Event_Next"] = EventInfo(self.session.nav, EventInfo.Next)

		self["Event_Now_Duration"] = EventInfo(self.session.nav, EventInfo.Now_Duration)
		self["Event_Next_Duration"] = EventInfo(self.session.nav, EventInfo.Next_Duration)
	
	def mainMenu(self):
		self.session.open(mainMenu)
		
	def switchChannel(self):
		self.session.open(channelSelection)

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
		if self["scan"].isDone():
			self.close()
	
	def __init__(self, session):
		Screen.__init__(self, session)
		
		self["scan_progress"] = ProgressBar()
		self["scan_state"] = Label("scan state")
		self["scan"] = ServiceScan(self["scan_progress"], self["scan_state"])

		self["okbutton"] = Button("ok", [self.ok])
		self["okbutton"].disable()

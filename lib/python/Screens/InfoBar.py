from Screen import Screen
from ChannelSelection import ChannelSelection
from Components.Clock import Clock
from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.ServiceName import ServiceName
from Components.EventInfo import EventInfo

from enigma import *

import time

# hack alert!
from Menu import *

class InfoBar(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		#instantiate forever
		self.servicelist = self.session.instantiateDialog(ChannelSelection)
		
		self["actions"] = ActionMap( [ "InfobarActions" ], 
			{
				"switchChannel": self.switchChannel,
				"mainMenu": self.mainMenu,
				"zapUp": self.zapUp,
				"zapDown": self.zapDown,
				"instantRecord": self.instantRecord
			})
		self["okbutton"] = Button("mainMenu", [self.mainMenu])
		
		self["CurrentTime"] = Clock()
		
		self["ServiceName"] = ServiceName(self.session.nav)
		
		self["Event_Now"] = EventInfo(self.session.nav, EventInfo.Now)
		self["Event_Next"] = EventInfo(self.session.nav, EventInfo.Next)

		self["Event_Now_Duration"] = EventInfo(self.session.nav, EventInfo.Now_Duration)
		self["Event_Next_Duration"] = EventInfo(self.session.nav, EventInfo.Next_Duration)
		
		self.recording = None
	
	def mainMenu(self):
		print "loading mainmenu XML..."
		menu = mdom.childNodes[0]
		assert menu.tagName == "menu", "root element in menu must be 'menu'!"
		self.session.open(Menu, menu, menu.childNodes)

	def switchChannel(self):	
		self.session.execDialog(self.servicelist)

	def	zapUp(self):
		self.servicelist.zapUp()

	def	zapDown(self):
		self.servicelist.zapDown()
		
	def instantRecord(self):
		if self.recording != None:
			print "remove entry"
			self.session.nav.RecordTimer.removeEntry(self.recording)
			self.recording = None
		else:
			serviceref = self.session.nav.getCurrentlyPlayingServiceReference()
			
			# try to get event info
			epg = None
			service = self.session.nav.getCurrentService()
			if service != None:
				info = iServiceInformationPtr()
				if not service.info(info):
					ev = eServiceEventPtr()
					if info.getEvent(ev, 0) == 0:
						epg = ev

			self.recording = self.session.nav.recordWithTimer(time.time(), time.time() + 30, serviceref, epg)
			print "got entry: %s" % (str(self.recording))


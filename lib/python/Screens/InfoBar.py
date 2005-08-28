from Screen import Screen
from ChannelSelection import ChannelSelection
from Components.Clock import Clock
from Components.VolumeBar import VolumeBar
from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.ServiceName import ServiceName
from Components.EventInfo import EventInfo
from Components.ServicePosition import ServicePosition

from Screens.MessageBox import MessageBox
from Screens.MovieSelection import MovieSelection

from enigma import *

import time

# hack alert!
from Menu import MainMenu, mdom

class InfoBar(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		#instantiate forever
		self.servicelist = self.session.instantiateDialog(ChannelSelection)
		self.volumeBar = VolumeBar()		

		self["actions"] = ActionMap( [ "InfobarActions" ], 
			{
				"switchChannelUp": self.switchChannelUp,
				"switchChannelDown": self.switchChannelDown,
				"mainMenu": self.mainMenu,
				"zapUp": self.zapUp,
				"zapDown": self.zapDown,
				"volumeUp": self.volUp,
				"volumeDown": self.volDown,
				"volumeMute": self.volMute,
				"instantRecord": self.instantRecord,
				"hide": self.hide,
				"toggleShow": self.toggleShow,
				"showMovies": self.showMovies,
				"quit": self.quit
			})
#		self["okbutton"] = Button("mainMenu", [self.mainMenu])
		
		self["CurrentTime"] = ServicePosition(self.session.nav, ServicePosition.TYPE_REMAINING)
		# Clock()

		self["Volume"] = self.volumeBar
		
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
		self.session.open(MainMenu, menu, menu.childNodes)

	def switchChannelUp(self):	
		self.servicelist.moveUp()
		self.session.execDialog(self.servicelist)

	def switchChannelDown(self):	
		self.servicelist.moveDown()
		self.session.execDialog(self.servicelist)

	def hide(self):	
		self.instance.hide()

	def toggleShow(self):
		if self.instance.isVisible():
			self.instance.hide()
		else:
			self.instance.show()

	def	zapUp(self):
		self.servicelist.moveUp()
		self.servicelist.zap()

	def	zapDown(self):
		self.servicelist.moveDown()
		self.servicelist.zap()

	def	volUp(self):
		eDVBVolumecontrol.getInstance().volumeUp()
		self.volumeBar.setValue(eDVBVolumecontrol.getInstance().getVolume())

	def	volDown(self):
		eDVBVolumecontrol.getInstance().volumeDown()
		self.volumeBar.setValue(eDVBVolumecontrol.getInstance().getVolume())

	def	volMute(self):
		eDVBVolumecontrol.getInstance().volumeToggleMute()
		self.volumeBar.setValue(eDVBVolumecontrol.getInstance().getVolume())

	def	quit(self):
		quitMainloop()
		
	def instantRecord(self):
		#self.session.open(MessageBox, "this would be an instant recording! do you really know what you're doing?!")
		#return
	
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
			# fix me, description. 
			self.recording = self.session.nav.recordWithTimer(time.time(), time.time() + 30, serviceref, epg, "instant record")
	
	def showMovies(self):
		self.session.open(MovieSelection)


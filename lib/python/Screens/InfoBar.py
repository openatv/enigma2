from Screen import Screen
from ChannelSelection import ChannelSelection
from Components.Clock import Clock
from Components.VolumeBar import VolumeBar
from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.ServiceName import ServiceName
from Components.EventInfo import EventInfo
from Components.ServicePosition import ServicePosition
from Components.config import configfile

from Screens.MessageBox import MessageBox
from Screens.MovieSelection import MovieSelection

from enigma import *

import time

# hack alert!
from Menu import MainMenu, mdom

class InfoBar(Screen):
	STATE_HIDDEN = 0
	STATE_HIDING = 1
	STATE_SHOWING = 2
	STATE_SHOWN = 3
	
	def __init__(self, session):
		Screen.__init__(self, session)

		#instantiate forever
		self.servicelist = self.session.instantiateDialog(ChannelSelection)
		self.volumeBar = VolumeBar()		
		
		self.state = self.STATE_HIDDEN
		
		self.hideTimer = eTimer()
		self.hideTimer.timeout.get().append(self.doTimerHide)
		#self.hideTimer.start(1000)


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
		
		self["CurrentTime"] = Clock()
		# ServicePosition(self.session.nav, ServicePosition.TYPE_REMAINING)
		# Clock()

		self["Volume"] = self.volumeBar
		
		self["ServiceName"] = ServiceName(self.session.nav)
		
		self["Event_Now"] = EventInfo(self.session.nav, EventInfo.Now)
		self["Event_Next"] = EventInfo(self.session.nav, EventInfo.Next)

		self["Event_Now_Duration"] = EventInfo(self.session.nav, EventInfo.Now_Duration)
		self["Event_Next_Duration"] = EventInfo(self.session.nav, EventInfo.Next_Duration)
		
		self.recording = None
		
		self.pos = 0
	
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

	def doTimerHide(self):
		if self.state == self.STATE_SHOWN:
			self.instance.hide()
			self.state = self.STATE_HIDDEN

	def toggleShow(self):
		if self.state == self.STATE_SHOWN:
			self.instance.hide()
			#pls check animation support, sorry
#			self.startHide()
			self.state = self.STATE_HIDDEN
		else:
			self.instance.show()
#			self.startShow()
			self.state = self.STATE_SHOWN
			#TODO: make it customizable
			self.hideTimer.start(5000)

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
		
	def startShow(self):
		self.instance.m_animation.startMoveAnimation(ePoint(0, 600), ePoint(0, 380), 100)
		self.state = self.STATE_SHOWN
	
	def startHide(self):
		self.instance.m_animation.startMoveAnimation(ePoint(0, 380), ePoint(0, 600), 100)
		self.state = self.STATE_HIDDEN

	def	volMute(self):
		eDVBVolumecontrol.getInstance().volumeToggleMute()
		self.volumeBar.setValue(eDVBVolumecontrol.getInstance().getVolume())

	def	quit(self):
		configfile.save()
		quitMainloop()
	
	def stopCurrentRecording(self):	
		print "remove entry"
		self.session.nav.RecordTimer.removeEntry(self.recording)
		self.recording = None
	
	def startInstantRecording(self):
		serviceref = self.session.nav.getCurrentlyPlayingServiceReference()
			
		# try to get event info
		epg = None
		try:
			service = self.session.nav.getCurrentService()
			info = service.info()
			ev = info.getEvent(0)
			epg = ev
		except:
			pass
		
		# fix me, description. 
		self.recording = self.session.nav.recordWithTimer(time.time(), time.time() + 30, serviceref, epg, "instant record")

	def recordQuestionCallback(self, answer):
		if answer == False:
			return
		
		if self.recording != None:
			self.stopCurrentRecording()
		else:
			self.startInstantRecording()

	def instantRecord(self):
		if self.recording != None:
			self.session.openWithCallback(self.recordQuestionCallback, MessageBox, "Do you want to stop the current\n(instant) recording?")
		else:
			self.session.openWithCallback(self.recordQuestionCallback, MessageBox, "Start recording?")

	def showMovies(self):
		self.session.open(MovieSelection)

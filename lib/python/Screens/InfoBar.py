from Screen import Screen
from EpgSelection import EPGSelection
from ChannelSelection import ChannelSelection
from Components.Clock import Clock
from Components.ActionMap import ActionMap
from Components.ActionMap import NumberActionMap
from Components.Button import Button
from Components.ServiceName import ServiceName
from Components.EventInfo import EventInfo
from Components.ServicePosition import ServicePosition
from Components.config import configfile
from Components.Label import Label

from Screens.MessageBox import MessageBox
from Screens.MovieSelection import MovieSelection
from Screens.Volume import Volume
from Screens.Mute import Mute
from Screens.Standby import Standby

from enigma import *

import time

# hack alert!
from Menu import MainMenu, mdom

class NumberZap(Screen):
	def quit(self):
		self.Timer.stop()
		self.close()

	def keyOK(self):
		self.Timer.stop()
		print "do the action here"
		self.close()

	def keyNumberGlobal(self, number):
		self.Timer.start(3000)		#reset timer
		self.field = self.field + str(number)
		self["number"].setText(self.field)
		if len(self.field) >= 4:
			self.keyOK()

	def __init__(self, session, number):
		Screen.__init__(self, session)
		self.field = str(number)
		
		self["number"] = Label(self.field)

		self["actions"] = NumberActionMap( [ "SetupActions" ], 
			{
				"cancel": self.quit,
				"ok": self.keyOK,
				"1": self.keyNumberGlobal,
				"2": self.keyNumberGlobal,
				"3": self.keyNumberGlobal,
				"4": self.keyNumberGlobal,
				"5": self.keyNumberGlobal,
				"6": self.keyNumberGlobal,
				"7": self.keyNumberGlobal,
				"8": self.keyNumberGlobal,
				"9": self.keyNumberGlobal,
				"0": self.keyNumberGlobal
			})

		self.Timer = eTimer()
		self.Timer.timeout.get().append(self.keyOK)
		self.Timer.start(3000)


class InfoBar(Screen):
	STATE_HIDDEN = 0
	STATE_HIDING = 1
	STATE_SHOWING = 2
	STATE_SHOWN = 3
	
	def __init__(self, session):
		Screen.__init__(self, session)

		#instantiate forever
		self.servicelist = self.session.instantiateDialog(ChannelSelection)
		
		self.state = self.STATE_HIDDEN
		
		self.volumeDialog = self.session.instantiateDialog(Volume)
		self.muteDialog = self.session.instantiateDialog(Mute)
		
		self.hideTimer = eTimer()
		self.hideTimer.timeout.get().append(self.doTimerHide)
		#self.hideTimer.start(1000)
		
		self.hideVolTimer = eTimer()
		self.hideVolTimer.timeout.get().append(self.volHide)

		#self["actions"] = ActionMap( [ "InfobarActions" ], 
		self["actions"] = NumberActionMap( [ "InfobarActions" ], 
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
				"quit": self.quit,
				"1": self.keyNumberGlobal,
				"2": self.keyNumberGlobal,
				"3": self.keyNumberGlobal,
				"4": self.keyNumberGlobal,
				"5": self.keyNumberGlobal,
				"6": self.keyNumberGlobal,
				"7": self.keyNumberGlobal,
				"8": self.keyNumberGlobal,
				"9": self.keyNumberGlobal,
				"0": self.keyNumberGlobal,
				"showEPGList": self.showEPGList,
				
				"pauseService": self.pauseService,
				"unPauseService": self.unPauseService,
			})
#		self["okbutton"] = Button("mainMenu", [self.mainMenu])
		
		self["CurrentTime"] = Clock()
		# ServicePosition(self.session.nav, ServicePosition.TYPE_REMAINING)
		# Clock()

		self["ServiceName"] = ServiceName(self.session.nav)
		
		self["Event_Now_StartTime"] = EventInfo(self.session.nav, EventInfo.Now_StartTime)
		self["Event_Next_StartTime"] = EventInfo(self.session.nav, EventInfo.Next_StartTime)
				
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

	def keyNumberGlobal(self, number):
		print "You pressed number " + str(number)
		self.session.open(NumberZap, number)

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
		self.volumeDialog.instance.show()
		self.volumeDialog.setValue(eDVBVolumecontrol.getInstance().getVolume())
		self.hideVolTimer.start(3000)

	def	volDown(self):
		eDVBVolumecontrol.getInstance().volumeDown()
		self.volumeDialog.instance.show()
		self.volumeDialog.setValue(eDVBVolumecontrol.getInstance().getVolume())
		self.hideVolTimer.start(3000)
		
	def volHide(self):
		self.volumeDialog.instance.hide()

	def startShow(self):
		self.instance.m_animation.startMoveAnimation(ePoint(0, 600), ePoint(0, 380), 100)
		self.state = self.STATE_SHOWN
	
	def startHide(self):
		self.instance.m_animation.startMoveAnimation(ePoint(0, 380), ePoint(0, 600), 100)
		self.state = self.STATE_HIDDEN

	def	volMute(self):
		eDVBVolumecontrol.getInstance().volumeToggleMute()
		self.volumeDialog.setValue(eDVBVolumecontrol.getInstance().getVolume())
		
		if (eDVBVolumecontrol.getInstance().isMuted()):
			self.muteDialog.instance.show()
		else:
			self.muteDialog.instance.hide()

	def showEPGList(self):
		self.session.open(EPGSelection, self.session.nav.getCurrentlyPlayingServiceReference())

	def quit(self):
		self.session.open(Standby)
		#configfile.save()
		#quitMainloop()
	
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
		self.recording = self.session.nav.recordWithTimer(time.time(), time.time() + 3600, serviceref, epg, "instant record")

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

	def pauseService(self):
		self.session.nav.pause(1)
		
	def unPauseService(self):
		self.session.nav.pause(0)

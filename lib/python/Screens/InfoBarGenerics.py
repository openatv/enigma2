from Screen import Screen
from Components.ActionMap import ActionMap
from Components.ActionMap import NumberActionMap
from Components.Label import Label
from Components.config import configfile
from ChannelSelection import ChannelSelection

from Components.ServiceName import ServiceName
from Components.EventInfo import EventInfo

from EpgSelection import EPGSelection

from Screens.MessageBox import MessageBox
from Screens.Volume import Volume
from Screens.Mute import Mute
from Screens.Standby import Standby

#from enigma import eTimer, eDVBVolumecontrol, quitMainloop
from enigma import *

import time

# hack alert!
from Menu import MainMenu, mdom

class InfoBarVolumeControl:
	"""Volume control, handles volUp, volDown, volMute actions and display 
	a corresponding dialog"""
	
	def __init__(self):
		self["VolumeActions"] = ActionMap( ["InfobarVolumeActions"] ,
			{
				"volumeUp": self.volUp,
				"volumeDown": self.volDown,
				"volumeMute": self.volMute,
			})

		self.volumeDialog = self.session.instantiateDialog(Volume)
		self.muteDialog = self.session.instantiateDialog(Mute)

		self.hideVolTimer = eTimer()
		self.hideVolTimer.timeout.get().append(self.volHide)
	
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

	def	volMute(self):
		eDVBVolumecontrol.getInstance().volumeToggleMute()
		self.volumeDialog.setValue(eDVBVolumecontrol.getInstance().getVolume())
		
		if (eDVBVolumecontrol.getInstance().isMuted()):
			self.muteDialog.instance.show()
		else:
			self.muteDialog.instance.hide()

class InfoBarShowHide:
	""" InfoBar show/hide control, accepts toggleShow and hide actions, might start
	fancy animations. """
	STATE_HIDDEN = 0
	STATE_HIDING = 1
	STATE_SHOWING = 2
	STATE_SHOWN = 3
	
	def __init__(self):
		self["ShowHideActions"] = ActionMap( ["InfobarShowHideActions"] ,
			{
				"toggleShow": self.toggleShow,
				"hide": self.hide,
			})

		self.state = self.STATE_HIDDEN
		
		self.hideTimer = eTimer()
		self.hideTimer.timeout.get().append(self.doTimerHide)
		#self.hideTimer.start(1000)

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

	def startShow(self):
		self.instance.m_animation.startMoveAnimation(ePoint(0, 600), ePoint(0, 380), 100)
		self.state = self.STATE_SHOWN
	
	def startHide(self):
		self.instance.m_animation.startMoveAnimation(ePoint(0, 380), ePoint(0, 600), 100)
		self.state = self.STATE_HIDDEN

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

class InfoBarPowerKey:
	""" PowerKey stuff - handles the powerkey press and powerkey release actions"""
	
	def __init__(self):
		self.powerKeyTimer = eTimer()
		self.powerKeyTimer.timeout.get().append(self.powertimer)
		self["PowerKeyActions"] = ActionMap( ["PowerKeyActions"],
			{
				"powerdown": self.powerdown,
				"powerup": self.powerup,
			})

	def powertimer(self):	
		print "PowerOff - Now!"
		self.quit()
	
	def powerdown(self):
		self.standbyblocked = 0
		self.powerKeyTimer.start(3000)

	def powerup(self):
		self.powerKeyTimer.stop()
		if self.standbyblocked == 0:
			self.standbyblocked = 1
			self.session.open(Standby, self)

	def quit(self):
		#	self.session.open(Standby, self)
		ref = self.session.nav.getCurrentlyPlayingServiceReference()
		if ref is not None:
			refstr = ref.toString()
		else:
			refstr = ""	
		
		#configfile.save()
		quitMainloop(0)


class InfoBarNumberZap:
	""" Handles an initial number for NumberZapping """
	def __init__(self):
		self["NumberZapActions"] = NumberActionMap( [ "NumberZapActions"],
			{
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
			})

	def keyNumberGlobal(self, number):
		print "You pressed number " + str(number)
		self.session.open(NumberZap, number)

class InfoBarChannelSelection:
	""" ChannelSelection - handles the channelSelection dialog and the initial 
	channelChange actions which open the channelSelection dialog """
	def __init__(self):
		#instantiate forever
		self.servicelist = self.session.instantiateDialog(ChannelSelection)

		self["ChannelSelectActions"] = ActionMap( ["InfobarChannelSelection"],
			{
				"switchChannelUp": self.switchChannelUp,
				"switchChannelDown": self.switchChannelDown,
				"zapUp": self.zapUp,
				"zapDown": self.zapDown,
			})
			
	def switchChannelUp(self):	
		self.servicelist.moveUp()
		self.session.execDialog(self.servicelist)

	def switchChannelDown(self):	
		self.servicelist.moveDown()
		self.session.execDialog(self.servicelist)

	def	zapUp(self):
		self.servicelist.moveUp()
		self.servicelist.zap()

	def	zapDown(self):
		self.servicelist.moveDown()
		self.servicelist.zap()

class InfoBarMenu:
	""" Handles a menu action, to open the (main) menu """
	def __init__(self):
		self["MenuActions"] = ActionMap( [ "InfobarMenuActions" ], 
			{
				"mainMenu": self.mainMenu,
			})

	def mainMenu(self):
		print "loading mainmenu XML..."
		menu = mdom.childNodes[0]
		assert menu.tagName == "menu", "root element in menu must be 'menu'!"
		self.session.open(MainMenu, menu, menu.childNodes)

class InfoBarEPG:
	""" EPG - Opens an EPG list when the showEPGList action fires """
	def __init__(self):
		self["EPGActions"] = ActionMap( [ "InfobarEPGActions" ], 
			{
				"showEPGList": self.showEPGList,
			})

	def showEPGList(self):
		ref=self.session.nav.getCurrentlyPlayingServiceReference()
		ptr=eEPGCache.getInstance()
		if ptr.startTimeQuery(ref) != -1:
			self.session.open(EPGSelection, ref)
		else:
			print 'no epg for service', ref.toString()

class InfoBarEvent:	
	"""provides a current/next event info display"""
	def __init__(self):
		self["Event_Now_StartTime"] = EventInfo(self.session.nav, EventInfo.Now_StartTime)
		self["Event_Next_StartTime"] = EventInfo(self.session.nav, EventInfo.Next_StartTime)
				
		self["Event_Now"] = EventInfo(self.session.nav, EventInfo.Now)
		self["Event_Next"] = EventInfo(self.session.nav, EventInfo.Next)

		self["Event_Now_Duration"] = EventInfo(self.session.nav, EventInfo.Now_Duration)
		self["Event_Next_Duration"] = EventInfo(self.session.nav, EventInfo.Next_Duration)

class InfoBarServiceName:
	def __init__(self):
		self["ServiceName"] = ServiceName(self.session.nav)

class InfoBarPVR:
	"""handles PVR specific actions like seeking, pause"""
	def __init__(self):
		self["PVRActions"] = ActionMap( [ "InfobarPVRActions" ], 
			{
				"pauseService": self.pauseService,
				"unPauseService": self.unPauseService,
				
				"seekFwd": self.seekFwd,
				"seekBack": self.seekBack,
			})
		
	def pauseService(self):
		self.session.nav.pause(1)
		
	def unPauseService(self):
		self.session.nav.pause(0)
	
	def doSeek(self, dir, seektime):
		service = self.session.nav.getCurrentService()
		if service is None:
			return
		
		seekable = service.seek()
		if seekable is None:
			return
		seekable.seekRelative(dir, 90 * seektime)

	def seekFwd(self):
		self.doSeek(+1, 10000)
	
	def seekBack(self):
		self.doSeek(-1, 10000)

class InfoBarInstantRecord:
	"""Instant Record - handles the instantRecord action in order to 
	start/stop instant records"""
	def __init__(self):
		self["InstnantRecordActions"] = ActionMap( [ "InfobarInstantRecord" ],
			{
				"instantRecord": self.instantRecord,
			})
		self.recording = None

	def stopCurrentRecording(self):	
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

from Screens.AudioSelection import AudioSelection

class InfoBarAudioSelection:
	def __init__(self):
		self["AudioSelectionAction"] = ActionMap( [ "InfobarAudioSelectionActions" ], 
			{
				"audioSelection": self.audioSelection,
			})

	def audioSelection(self):
		service = self.session.nav.getCurrentService()
		audio = service.audioTracks()
		n = audio.getNumberOfTracks()
		if n > 0:
			self.session.open(AudioSelection, audio)

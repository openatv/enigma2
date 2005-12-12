from Screen import Screen
from Components.ActionMap import ActionMap, HelpableActionMap
from Components.ActionMap import NumberActionMap
from Components.Label import *
from Components.ProgressBar import *
from Components.config import configfile, configsequencearg
from Components.config import config, configElement, ConfigSubsection, configSequence
from ChannelSelection import ChannelSelection

from Components.Pixmap import Pixmap, PixmapConditional
from Components.BlinkingPixmap import BlinkingPixmapConditional
from Components.ServiceName import ServiceName
from Components.EventInfo import EventInfo

from ServiceReference import ServiceReference
from EpgSelection import EPGSelection

from Screens.MessageBox import MessageBox
from Screens.Volume import Volume
from Screens.Mute import Mute
from Screens.Dish import Dish
from Screens.Standby import Standby
from Screens.EventView import EventView
from Components.Harddisk import harddiskmanager

from Tools import Notifications

#from enigma import eTimer, eDVBVolumecontrol, quitMainloop
from enigma import *

import time
import os

# hack alert!
from Menu import MainMenu, mdom

class InfoBarVolumeControl:
	"""Volume control, handles volUp, volDown, volMute actions and display 
	a corresponding dialog"""
	def __init__(self):
		config.audio = ConfigSubsection()
		config.audio.volume = configElement("config.audio.volume", configSequence, [100], configsequencearg.get("INTEGER", (0, 100)))

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

		vol = config.audio.volume.value[0]
		self.volumeDialog.setValue(vol)
		eDVBVolumecontrol.getInstance().setVolume(vol, vol)
	
	def volSave(self):
		config.audio.volume.value = eDVBVolumecontrol.getInstance().getVolume()
		config.audio.volume.save()
		
	def	volUp(self):
		if (eDVBVolumecontrol.getInstance().isMuted()):
			self.volMute()
		eDVBVolumecontrol.getInstance().volumeUp()
		self.volumeDialog.instance.show()
		self.volumeDialog.setValue(eDVBVolumecontrol.getInstance().getVolume())
		self.volSave()
		self.hideVolTimer.start(3000, True)

	def	volDown(self):
		if (eDVBVolumecontrol.getInstance().isMuted()):
			self.volMute()
		eDVBVolumecontrol.getInstance().volumeDown()
		self.volumeDialog.instance.show()
		self.volumeDialog.setValue(eDVBVolumecontrol.getInstance().getVolume())
		self.volSave()
		self.hideVolTimer.start(3000, True)
		
	def volHide(self):
		self.volumeDialog.instance.hide()

	def	volMute(self):
		eDVBVolumecontrol.getInstance().volumeToggleMute()
		self.volumeDialog.setValue(eDVBVolumecontrol.getInstance().getVolume())
		
		if (eDVBVolumecontrol.getInstance().isMuted()):
			self.muteDialog.instance.show()
		else:
			self.muteDialog.instance.hide()

class InfoBarDish:
	def __init__(self):
		self.dishDialog = self.session.instantiateDialog(Dish)
		self.onShown.append(self.dishDialog.instance.hide)

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

		self.state = self.STATE_SHOWN
		
		self.onExecBegin.append(self.show)
		self.onClose.append(self.delHideTimer)
		
		self.hideTimer = eTimer()
		self.hideTimer.timeout.get().append(self.doTimerHide)
		self.hideTimer.start(5000, True)

	def delHideTimer(self):
		del self.hideTimer

	def hide(self):	
		self.instance.hide()
		
	def show(self):
		self.state = self.STATE_SHOWN
		self.hideTimer.start(5000, True)

	def doTimerHide(self):
		self.hideTimer.stop()
		if self.state == self.STATE_SHOWN:
			self.instance.hide()
			self.state = self.STATE_HIDDEN

	def toggleShow(self):
		if self.state == self.STATE_SHOWN:
			self.instance.hide()
			#pls check animation support, sorry
#			self.startHide()
			self.hideTimer.stop()
			self.state = self.STATE_HIDDEN
		elif self.state == self.STATE_HIDDEN:
			self.instance.show()
			self.show()
			
	def startShow(self):
		self.instance.m_animation.startMoveAnimation(ePoint(0, 600), ePoint(0, 380), 100)
		self.state = self.STATE_SHOWN
	
	def startHide(self):
		self.instance.m_animation.startMoveAnimation(ePoint(0, 380), ePoint(0, 600), 100)
		self.state = self.STATE_HIDDEN

class NumberZap(Screen):
	def quit(self):
		self.Timer.stop()
		self.close(0)

	def keyOK(self):
		self.Timer.stop()
		self.close(int(self["number"].getText()))

	def keyNumberGlobal(self, number):
		self.Timer.start(3000, True)		#reset timer
		self.field = self.field + str(number)
		self["number"].setText(self.field)
		if len(self.field) >= 4:
			self.keyOK()

	def __init__(self, session, number):
		Screen.__init__(self, session)
		self.field = str(number)

		self["channel"] = Label(_("Channel:"))

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
		self.Timer.start(3000, True)

class InfoBarPowerKey:
	""" PowerKey stuff - handles the powerkey press and powerkey release actions"""
	
	def __init__(self):
		self.powerKeyTimer = eTimer()
		self.powerKeyTimer.timeout.get().append(self.powertimer)
		self["PowerKeyActions"] = HelpableActionMap(self, "PowerKeyActions",
			{
				"powerdown": self.powerdown,
				"powerup": self.powerup,
				"discreteStandby": (self.standby, "Go standby"),
				"discretePowerOff": (self.quit, "Go to deep standby"),
			})

	def powertimer(self):	
		print "PowerOff - Now!"
		self.quit()
	
	def powerdown(self):
		self.standbyblocked = 0
		self.powerKeyTimer.start(3000, True)

	def powerup(self):
		self.powerKeyTimer.stop()
		if self.standbyblocked == 0:
			self.standbyblocked = 1
			self.standby()

	def standby(self):
		self.session.open(Standby, self)

	def quit(self):
		# halt
		quitMainloop(1)

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
#		print "You pressed number " + str(number)
		self.session.openWithCallback(self.numberEntered, NumberZap, number)

	def numberEntered(self, retval):
#		print self.servicelist
		if retval > 0:
			self.zapToNumber(retval)

	def searchNumberHelper(self, serviceHandler, num, bouquet):
		servicelist = serviceHandler.list(bouquet)
		if not servicelist is None:
			while num:
				serviceIterator = servicelist.getNext()
				if not serviceIterator.valid(): #check end of list
					break
				if serviceIterator.flags: #assume normal dvb service have no flags set
					continue
				num -= 1;
			if not num: #found service with searched number ?
				return serviceIterator, 0
		return None, num

	def zapToNumber(self, number):
		bouquet = self.servicelist.bouquet_root
		service = None
		serviceHandler = eServiceCenter.getInstance()
		if bouquet.toString().find('FROM BOUQUET "bouquets.') == -1: #FIXME HACK
			service, number = self.searchNumberHelper(serviceHandler, number, bouquet)
		else:
			bouquetlist = serviceHandler.list(bouquet)
			if not bouquetlist is None:
				while number:
					bouquet = bouquetlist.getNext()
					if not bouquet.valid(): #check end of list
						break
					if ((bouquet.flags & eServiceReference.flagDirectory) != eServiceReference.flagDirectory):
						continue
					service, number = self.searchNumberHelper(serviceHandler, number, bouquet)
		if not service is None:
			self.session.nav.playService(service) #play service
			if self.servicelist.getRoot() != bouquet: #already in correct bouquet?
				self.servicelist.setRoot(bouquet)
			self.servicelist.setCurrentSelection(service) #select the service in servicelist

class InfoBarChannelSelection:
	""" ChannelSelection - handles the channelSelection dialog and the initial 
	channelChange actions which open the channelSelection dialog """
	def __init__(self):
		#instantiate forever
		self.servicelist = self.session.instantiateDialog(ChannelSelection)

		self["ChannelSelectActions"] = HelpableActionMap(self, "InfobarChannelSelection",
			{
				"switchChannelUp": self.switchChannelUp,
				"switchChannelDown": self.switchChannelDown,
				"zapUp": (self.zapUp, _("next channel")),
				"zapDown": (self.zapDown, _("previous channel")),
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
		self.instance.show()
		self.show()

	def	zapDown(self):
		self.servicelist.moveDown()
		self.servicelist.zap()
		self.instance.show()
		self.show()
		
class InfoBarMenu:
	""" Handles a menu action, to open the (main) menu """
	def __init__(self):
		self["MenuActions"] = HelpableActionMap(self, "InfobarMenuActions", 
			{
				"mainMenu": (self.mainMenu, "Enter main menu..."),
			})

	def mainMenu(self):
		print "loading mainmenu XML..."
		menu = mdom.childNodes[0]
		assert menu.tagName == "menu", "root element in menu must be 'menu'!"
		self.session.open(MainMenu, menu, menu.childNodes)

class InfoBarEPG:
	""" EPG - Opens an EPG list when the showEPGList action fires """
	def __init__(self):
		self["EPGActions"] = HelpableActionMap(self, "InfobarEPGActions", 
			{
				"showEPGList": (self.showEPGList, _("show EPG...")),
			})

	def showEPGList(self):
		ref=self.session.nav.getCurrentlyPlayingServiceReference()
		ptr=eEPGCache.getInstance()
		if ptr.startTimeQuery(ref) != -1:
			self.session.open(EPGSelection, ref)
		else: # try to show now/next
			print 'no epg for service', ref.toString()
			try:
				self.epglist = [ ]
				service = self.session.nav.getCurrentService()
				info = service.info()
				ptr=info.getEvent(0)
				if ptr:
					self.epglist.append(ptr)
				ptr=info.getEvent(1)
				if ptr:
					self.epglist.append(ptr)
				if len(self.epglist) > 0:
					self.session.open(EventView, self.epglist[0], ServiceReference(ref), self.eventViewCallback)
			except:
				pass

	def eventViewCallback(self, setEvent, val): #used for now/next displaying
		if len(self.epglist) > 1:
			tmp = self.epglist[0]
			self.epglist[0]=self.epglist[1]
			self.epglist[1]=tmp
			setEvent(self.epglist[0])

from math import log

class InfoBarTuner:
	"""provides a snr/agc/ber display"""
	def __init__(self):
		self["snr"] = Label()
		self["agc"] = Label()
		self["ber"] = Label()
		self["snr_percent"] = Label()
		self["agc_percent"] = Label()
		self["ber_count"] = Label()
		self["snr_progress"] = ProgressBar()
		self["agc_progress"] = ProgressBar()
		self["ber_progress"] = ProgressBar()
		self.timer = eTimer()
		self.timer.timeout.get().append(self.updateTunerInfo)
		self.timer.start(1000)

	def calc(self,val):
		if not val:
			return 0
		if val < 2500:
			return (long)(log(val)/log(2))
		return val*100/65535

	def updateTunerInfo(self):
		if self.instance.isVisible():
			service = self.session.nav.getCurrentService()
			snr=0
			agc=0
			ber=0
			if service is not None:
				feinfo = service.frontendStatusInfo()
				if feinfo is not None:
					ber=feinfo.getFrontendInfo(iFrontendStatusInformation.bitErrorRate)
					snr=feinfo.getFrontendInfo(iFrontendStatusInformation.signalPower)*100/65536
					agc=feinfo.getFrontendInfo(iFrontendStatusInformation.signalQuality)*100/65536
			self["snr_percent"].setText("%d%%"%(snr))
			self["agc_percent"].setText("%d%%"%(agc))
			self["ber_count"].setText("%d"%(ber))
			self["snr_progress"].setValue(snr)
			self["agc_progress"].setValue(agc)
			self["ber_progress"].setValue(self.calc(ber))

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

	# ispause, isff, issm, skip
	SEEK_STATE_PLAY = (0, 0, 0, 0)
	SEEK_STATE_PAUSE = (1, 0, 0, 0)
	SEEK_STATE_FF_2X = (0, 2, 0, 0)
	SEEK_STATE_FF_4X = (0, 4, 0, 0)
	SEEK_STATE_FF_8X = (0, 8, 0, 0)
	SEEK_STATE_FF_32X = (0, 0, 0, 32)
	SEEK_STATE_FF_64X = (0, 0, 0, 64)
	
	SEEK_STATE_BACK_4X = (0, 0, 0, -4)
	SEEK_STATE_BACK_32X = (0, 0, 0, -32)
	SEEK_STATE_BACK_64X = (0, 0, 0, -64)
	
	SEEK_STATE_SM_HALF = (0, 0, 2, 0)
	SEEK_STATE_SM_QUARTER = (0, 0, 4, 0)
	SEEK_STATE_SM_EIGHTH = (0, 0, 8, 0)
	
	"""handles PVR specific actions like seeking, pause"""
	def __init__(self):
		self["PVRActions"] = HelpableActionMap(self, "InfobarPVRActions", 
			{
				"pauseService": (self.pauseService, "pause"),
				"unPauseService": (self.unPauseService, "continue"),
				
				"seekFwd": (self.seekFwd, "skip forward"),
				"seekBack": (self.seekBack, "skip backward"),
			})

		self.seekstate = self.SEEK_STATE_PLAY
		self.seekTimer = eTimer()
		self.seekTimer.timeout.get().append(self.seekTimerFired)
		self.skipinterval = 500 # 500ms skip interval
	
	def seekTimerFired(self):
		if self.skipmode > 0:
			self.doSeek(+1, self.skipmode * self.skipinterval)
		else:
			self.doSeek(-1, -self.skipmode * self.skipinterval)

	def setSeekState(self, state):
		oldstate = self.seekstate
		
		self.seekstate = state

		service = self.session.nav.getCurrentService()
		if service is None:
			return
		
		pauseable = service.pause()
		
		for i in range(4):
			if oldstate[i] != self.seekstate[i]:
				(self.session.nav.pause, pauseable.setFastForward, pauseable.setSlowMotion, self.setSkipMode)[i](self.seekstate[i])
		
	def setSkipMode(self, skipmode):
		self.skipmode = skipmode
		if skipmode == 0:
			self.seekTimer.stop()
		else:
			self.seekTimer.start(500)
	
	def pauseService(self):
		self.setSeekState(self.SEEK_STATE_PAUSE);
		
	def unPauseService(self):
		self.setSeekState(self.SEEK_STATE_PLAY);
	
	def doSeek(self, dir, seektime):
		service = self.session.nav.getCurrentService()
		if service is None:
			return
		
		seekable = service.seek()
		if seekable is None:
			return
		seekable.seekRelative(dir, 90 * seektime)

	def seekFwd(self):
		lookup = {
				self.SEEK_STATE_PLAY: self.SEEK_STATE_FF_2X,
				self.SEEK_STATE_PAUSE: self.SEEK_STATE_SM_EIGHTH,
				self.SEEK_STATE_FF_2X: self.SEEK_STATE_FF_4X,
				self.SEEK_STATE_FF_4X: self.SEEK_STATE_FF_8X,
				self.SEEK_STATE_FF_8X: self.SEEK_STATE_FF_32X,
				self.SEEK_STATE_FF_32X: self.SEEK_STATE_FF_64X,
				self.SEEK_STATE_FF_64X: self.SEEK_STATE_FF_64X,
				self.SEEK_STATE_BACK_4X: self.SEEK_STATE_PLAY,
				self.SEEK_STATE_BACK_32X: self.SEEK_STATE_BACK_4X,
				self.SEEK_STATE_BACK_64X: self.SEEK_STATE_BACK_32X,
				self.SEEK_STATE_SM_HALF: self.SEEK_STATE_SM_HALF,
				self.SEEK_STATE_SM_QUARTER: self.SEEK_STATE_SM_HALF,
				self.SEEK_STATE_SM_EIGHTH: self.SEEK_STATE_SM_QUARTER
			}
		self.setSeekState(lookup[self.seekstate]);
	
	def seekBack(self):
		lookup = {
				self.SEEK_STATE_PLAY: self.SEEK_STATE_BACK_4X,
				self.SEEK_STATE_PAUSE: self.SEEK_STATE_PAUSE,
				self.SEEK_STATE_FF_2X: self.SEEK_STATE_PLAY,
				self.SEEK_STATE_FF_4X: self.SEEK_STATE_FF_2X,
				self.SEEK_STATE_FF_8X: self.SEEK_STATE_FF_4X,
				self.SEEK_STATE_FF_32X: self.SEEK_STATE_FF_8X,
				self.SEEK_STATE_FF_64X: self.SEEK_STATE_FF_32X,
				self.SEEK_STATE_BACK_4X: self.SEEK_STATE_BACK_32X,
				self.SEEK_STATE_BACK_32X: self.SEEK_STATE_BACK_64X,
				self.SEEK_STATE_BACK_64X: self.SEEK_STATE_BACK_64X,
				self.SEEK_STATE_SM_HALF: self.SEEK_STATE_SM_QUARTER,
				self.SEEK_STATE_SM_QUARTER: self.SEEK_STATE_SM_EIGHTH,
				self.SEEK_STATE_SM_EIGHTH: self.SEEK_STATE_PAUSE
			}
		self.setSeekState(lookup[self.seekstate]);

class InfoBarInstantRecord:
	"""Instant Record - handles the instantRecord action in order to 
	start/stop instant records"""
	def __init__(self):
		self["InstantRecordActions"] = HelpableActionMap(self, "InfobarInstantRecord",
			{
				"instantRecord": (self.instantRecord, "Instant Record..."),
			})
		self.recording = None
		
		self["BlinkingPoint"] = BlinkingPixmapConditional()
		self.onShown.append(self["BlinkingPoint"].hideWidget)
		self["BlinkingPoint"].setConnect(self.session.nav.RecordTimer.isRecording)
		
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
		self.recording.dontSave = True
		
		#self["BlinkingPoint"].setConnect(lambda: self.recording.isRunning())
		
	def isInstantRecordRunning(self):
		if self.recording != None:
			if self.recording.isRunning():
				return True
		return False

	def recordQuestionCallback(self, answer):
		if answer == False:
			return
		
		if self.isInstantRecordRunning():
			self.stopCurrentRecording()
		else:
			self.startInstantRecording()

	def instantRecord(self):
		try:
			stat = os.stat("/hdd/movies")
		except:
			self.session.open(MessageBox, "No HDD found!")
			return
	
		if self.isInstantRecordRunning():
			self.session.openWithCallback(self.recordQuestionCallback, MessageBox, _("Do you want to stop the current\n(instant) recording?"))
		else:
			self.session.openWithCallback(self.recordQuestionCallback, MessageBox, _("Start recording?"))

from Screens.AudioSelection import AudioSelection

class InfoBarAudioSelection:
	def __init__(self):
		self["AudioSelectionAction"] = HelpableActionMap(self, "InfobarAudioSelectionActions", 
			{
				"audioSelection": (self.audioSelection, "Audio Options..."),
			})

	def audioSelection(self):
		service = self.session.nav.getCurrentService()
		audio = service.audioTracks()
		n = audio.getNumberOfTracks()
		if n > 0:
			self.session.open(AudioSelection, audio)

from Screens.SubserviceSelection import SubserviceSelection

class InfoBarSubserviceSelection:
	def __init__(self):
		self["SubserviceSelectionAction"] = HelpableActionMap(self, "InfobarSubserviceSelectionActions",
			{
				"subserviceSelection": (self.subserviceSelection, "Subservice list..."),
			})

	def subserviceSelection(self):
		service = self.session.nav.getCurrentService()
		subservices = service.subServices()
		n = subservices.getNumberOfSubservices()
		if n > 0:
			self.session.openWithCallback(self.subserviceSelected, SubserviceSelection, subservices)

	def subserviceSelected(self, service):
		if not service is None:
			self.session.nav.playService(service)

class InfoBarAdditionalInfo:
	def __init__(self):
		self["DolbyActive"] = PixmapConditional()
		# TODO: get the info from c++ somehow
		self["DolbyActive"].setConnect(lambda: False)
		
		self["CryptActive"] = PixmapConditional()
		# TODO: get the info from c++ somehow
		self["CryptActive"].setConnect(lambda: False)
		
		self["FormatActive"] = PixmapConditional()
		# TODO: get the info from c++ somehow
		self["FormatActive"].setConnect(lambda: False)
		
		self["ButtonRed"] = PixmapConditional(withTimer = False)
		self["ButtonRed"].setConnect(lambda: harddiskmanager.HDDCount() > 0)
		self.onShown.append(self["ButtonRed"].update)
		self["ButtonRedText"] = LabelConditional(text = _("Record"), withTimer = False)
		self["ButtonRedText"].setConnect(lambda: harddiskmanager.HDDCount() > 0)
		self.onShown.append(self["ButtonRedText"].update)
				
		self["ButtonGreen"] = PixmapConditional()
		self["ButtonGreen"].setConnect(lambda: self.session.nav.getCurrentService().subServices().getNumberOfSubservices() > 0)
		self["ButtonGreenText"] = LabelConditional(text = _("Subservices"))
		self["ButtonGreenText"].setConnect(lambda: self.session.nav.getCurrentService().subServices().getNumberOfSubservices() > 0)

		self["ButtonYellow"] = PixmapConditional()
		self["ButtonYellow"].setConnect(lambda: False)

		self["ButtonBlue"] = PixmapConditional()
		self["ButtonBlue"].setConnect(lambda: False)

class InfoBarNotifications:
	def __init__(self):
		self.onExecBegin.append(self.checkNotifications)
		Notifications.notificationAdded.append(self.checkNotificationsIfExecing)
	
	def checkNotificationsIfExecing(self):
		if self.execing:
			self.checkNotifications()

	def checkNotifications(self):
		if len(Notifications.notifications):
			n = Notifications.notifications[0]
			Notifications.notifications = Notifications.notifications[1:]
			print "open",n
			cb = n[0]
			if cb is not None:
				self.session.openWithCallback(cb, *n[1:])
			else:
				self.session.open(*n[1:])

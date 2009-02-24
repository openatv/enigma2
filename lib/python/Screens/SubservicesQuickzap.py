from Screens.Screen import Screen
from Components.ActionMap import NumberActionMap
from Components.Label import Label

from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from InfoBarGenerics import InfoBarShowHide, InfoBarMenu, InfoBarInstantRecord, InfoBarTimeshift, InfoBarSeek, InfoBarTimeshiftState, InfoBarExtensions, InfoBarSubtitleSupport, InfoBarAudioSelection
from Components.ServiceEventTracker import InfoBarBase

from enigma import eTimer

class SubservicesQuickzap(InfoBarBase, InfoBarShowHide, InfoBarMenu, \
		InfoBarInstantRecord, InfoBarSeek, InfoBarTimeshift, \
		InfoBarTimeshiftState, InfoBarExtensions, InfoBarSubtitleSupport, \
		InfoBarAudioSelection, Screen):

	def __init__(self, session, subservices):
		Screen.__init__(self, session)
		for x in InfoBarBase, InfoBarShowHide, InfoBarMenu, \
				InfoBarInstantRecord, InfoBarSeek, InfoBarTimeshift, \
				InfoBarTimeshiftState, InfoBarSubtitleSupport, \
				InfoBarExtensions, InfoBarAudioSelection:
			x.__init__(self)

		self.restoreService = self.session.nav.getCurrentlyPlayingServiceReference()
		
		self["CurrentSubserviceNumber"] = Label("")
		self.currentSubserviceNumberLabel = self["CurrentSubserviceNumber"]
		
		self.updateSubservices()
		self.currentlyPlayingSubservice = 0

		self.timer = eTimer()
		self.timer.callback.append(self.playSubservice)
		self.onLayoutFinish.append(self.onLayoutFinished)

		self["actions"] = NumberActionMap( [ "InfobarSubserviceQuickzapActions", "NumberActions", "DirectionActions", "ColorActions" ], 
			{
				"up": self.showSelection,
				"down": self.showSelection,
				"right": self.nextSubservice,
				"left": self.previousSubservice,
				"green": self.showSelection,
				"exit": self.quitQuestion,
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
			}, 0)
		
		self.onClose.append(self.__onClose)

	def __onClose(self):
		self.session.nav.playService(self.restoreService, False)

	def onLayoutFinished(self):
		self.timer.start(0,True)

	def updateSubservices(self):
		self.service = self.session.nav.getCurrentService()
		self.subservices = self.service and self.service.subServices()
		self.n = self.subservices and self.subservices.getNumberOfSubservices()
	
	def nextSubservice(self):
		self.updateSubservices()
		if self.n:
			if self.currentlyPlayingSubservice >= self.n - 1:
				self.playSubservice(0)
			else:
				self.playSubservice(self.currentlyPlayingSubservice + 1)
	
	def previousSubservice(self):
		self.updateSubservices()
		if self.n:
			if self.currentlyPlayingSubservice > self.n:
				self.currentlyPlayingSubservice = self.n
			if self.currentlyPlayingSubservice == 0:
				self.playSubservice(self.n - 1)
			else:
				self.playSubservice(self.currentlyPlayingSubservice - 1)

	def getSubserviceIndex(self, service):
		self.updateSubservices()
		if self.n is None:
			return -1
		for x in range(self.n):
			if service == self.subservices.getSubservice(x):
				return x
	
	def keyNumberGlobal(self, number):
		print number, "pressed"
		self.updateSubservices()
		if number == 0:
			self.playSubservice(self.lastservice)
		elif self.n is not None and number <= self.n - 1:
			self.playSubservice(number)
	
	def showSelection(self):
		self.updateSubservices()
		tlist = []
		n = self.n or 0
		if n:
			idx = 0
			while idx < n:
				i = self.subservices.getSubservice(idx)
				tlist.append((i.getName(), idx))
				idx += 1

		keys = [ "", "1", "2", "3", "4", "5", "6", "7", "8", "9" ] + [""] * n
		self.session.openWithCallback(self.subserviceSelected, ChoiceBox, title=_("Please select a subservice..."), list = tlist, selection = self.currentlyPlayingSubservice, keys = keys)
	
	def subserviceSelected(self, service):
		print "playing subservice number", service
		if service is not None:
			self.playSubservice(service[1])
	
	def keyOK(self):
		pass
	
	def quitQuestion(self):
		self.session.openWithCallback(self.quit, MessageBox, _("Really exit the subservices quickzap?"))
	
	def quit(self, answer):
		if answer:
			self.close()
		
	def playSubservice(self, number = 0):
		newservice = self.subservices.getSubservice(number)
		if newservice.valid():
			del self.subservices
			del self.service
			self.lastservice = self.currentlyPlayingSubservice
			self.session.nav.playService(newservice, False)
			self.currentlyPlayingSubservice = number
			self.currentSubserviceNumberLabel.setText(str(number))
			self.doShow()

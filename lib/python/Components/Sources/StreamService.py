from Source import Source
from Components.Element import cached
from Components.SystemInfo import SystemInfo
from enigma import eServiceReference

StreamServiceList = []

class StreamService(Source):
	def __init__(self, navcore):
		Source.__init__(self)
		self.ref = None
		self.__service = None
		self.navcore = navcore

	def serviceEvent(self, event):
		pass

	@cached
	def getService(self):
		return self.__service

	service = property(getService)

	def handleCommand(self, cmd):
		print "[StreamService] handle command", cmd
		self.ref = eServiceReference(cmd)

	def recordEvent(self, service, event):
		if service is self.__service:
			return
		print "[StreamService] RECORD event for us:", service
		self.changed((self.CHANGED_ALL, ))

	def execBegin(self):
		if self.ref is None:
			print "[StreamService] has no service ref set"
			return
		print "[StreamService]e execBegin", self.ref.toString()
		if SystemInfo["CanDoTranscodeAndPIP"]:
			from Screens.InfoBar import InfoBar
			if InfoBar.instance and hasattr(InfoBar.instance.session, 'pipshown') and InfoBar.instance.session.pipshown:
				hasattr(InfoBar.instance, "showPiP") and InfoBar.instance.showPiP()
				print "[StreamService] try to disable pip before start stream"
				if hasattr(InfoBar.instance.session, 'pip'):
					del InfoBar.instance.session.pip
					InfoBar.instance.session.pipshown = False
		self.__service = self.navcore.recordService(self.ref)
		self.navcore.record_event.append(self.recordEvent)
		if self.__service is not None:
			if self.__service.__deref__() not in StreamServiceList:
				StreamServiceList.append(self.__service.__deref__())
			self.__service.prepareStreaming()
			self.__service.start()

	def execEnd(self):
		print "[StreamService] execEnd", self.ref.toString()
		self.navcore.record_event.remove(self.recordEvent)
		if self.__service is not None:
			if self.__service.__deref__() in StreamServiceList:
				StreamServiceList.remove(self.__service.__deref__())
			self.navcore.stopRecordService(self.__service)
			self.__service = None
			self.ref = None

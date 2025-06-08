from enigma import eServiceReference, pNavigation
from Components.Element import cached
from Components.SystemInfo import BoxInfo
from Components.Sources.Source import Source

StreamServiceList = []


class StreamService(Source):
	def __init__(self, navcore):
		Source.__init__(self)
		self.navcore = navcore
		self.ref = None
		self.__service = None

	def serviceEvent(self, event):
		pass

	@cached
	def getService(self):
		return self.__service

	service = property(getService)

	def handleCommand(self, cmd):
		print("[StreamService] Handle command: '%s'." % str(cmd))
		self.ref = eServiceReference(cmd)

	def recordEvent(self, service, event):
		if service is None or service is self.__service:
			return
		print("[StreamService] Record event: '%s'." % str(service))
		self.changed((self.CHANGED_ALL, ))

	def execBegin(self):
		if self.ref is None:
			print("[StreamService] No service ref set!")
			return
		print("[StreamService] execBegin '%s'." % self.ref.toString())
		if BoxInfo.getItem("CanNotDoSimultaneousTranscodeAndPIP"):
			from Screens.InfoBar import InfoBar
			if InfoBar.instance and hasattr(InfoBar.instance.session, 'pipshown') and InfoBar.instance.session.pipshown:
				hasattr(InfoBar.instance, "showPiP") and InfoBar.instance.showPiP()
				print("[StreamService] Try to disable PiP before starting stream.")
				if hasattr(InfoBar.instance.session, 'pip'):
					del InfoBar.instance.session.pip
					InfoBar.instance.session.pipshown = False
		self.__service = self.navcore.recordService(self.ref, False, pNavigation.isStreaming)
		self.navcore.record_event.append(self.recordEvent)
		if self.__service is not None:
			if self.__service.__deref__() not in StreamServiceList:
				StreamServiceList.append(self.__service.__deref__())
			self.__service.prepareStreaming()
			self.__service.start()

	def execEnd(self):
		print("[StreamService] execEnd '%s'." % self.ref.toString())
		self.navcore.record_event.remove(self.recordEvent)
		if self.__service is not None:
			if self.__service.__deref__() in StreamServiceList:
				StreamServiceList.remove(self.__service.__deref__())
			self.navcore.stopRecordService(self.__service)
			self.ref = None
			self.__service = None

from Plugins.Extensions.CutListEditor.plugin import CutListEditor
from Components.ServiceEventTracker import ServiceEventTracker
from enigma import iPlayableService, iServiceInformation

class TitleCutter(CutListEditor):
	def __init__(self, session, t):
		CutListEditor.__init__(self, session, t.source)
		self.skin = CutListEditor.skin
		self.session = session
		self.t = t
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
			{
				iPlayableService.evUpdatedInfo: self.getPMTInfo,
				iPlayableService.evCuesheetChanged: self.refillList
			})
		self.onExecBegin.remove(self.showTutorial)

	def getPMTInfo(self):
		service = self.session.nav.getCurrentService()
		audio = service and service.audioTracks()
		n = audio and audio.getNumberOfTracks() or 0
		if n > 0:
			for x in range(n):
				i = audio.getTrackInfo(x)
				language = i.getLanguage()
				description = i.getDescription()
				if description == "MPEG":
					description = "MP2"
				self.t.audiotracks.append((language, description))
		print "[DVDBurn getAudioTracks]", self.t.audiotracks
		sVideoType = service.info().getInfo(iServiceInformation.sVideoType)
		print "[DVDBurn getVideoType]", sVideoType
		if sVideoType != 0:
			self.close(False)

	def exit(self):
		self.session.nav.stopService()
		self.close(self.cut_list[:])

class CutlistReader(TitleCutter):
	def __init__(self, session, t):
		TitleCutter.__init__(self, session, t)

	def getAudioTracks(self):
		TitleCutter.getAudioTracks()
		self.exit()
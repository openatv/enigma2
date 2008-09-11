from Plugins.Extensions.CutListEditor.plugin import CutListEditor
from Components.ServiceEventTracker import ServiceEventTracker

class TitleCutter(CutListEditor):
	def __init__(self, session, t):
		CutListEditor.__init__(self, session, t.source)
		self.skin = CutListEditor.skin
		self.session = session
		self.t = t
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
			{
				iPlayableService.evUpdatedInfo: self.getAudioTracks,
				iPlayableService.evCuesheetChanged: self.refillList
			})
		self.onExecBegin.remove(self.showTutorial)

	def getAudioTracks(self):
		service = self.session.nav.getCurrentService()
		audio = service and service.audioTracks()
		n = audio and audio.getNumberOfTracks() or 0
		print "self.t", self.t
		print "self.t.audiotracks", self.t.audiotracks
		if n > 0:
			for x in range(n):
				i = audio.getTrackInfo(x)
				language = i.getLanguage()[:2]
				description = i.getDescription()
				if description == "MPEG":
					description = "mp2"
				self.t.audiotracks.append((description, language))
		print "audiotracks", self.t.audiotracks

	def exit(self):
		self.session.nav.stopService()
		self.close(self.cut_list[:])

class CutlistReader(TitleCutter):
	def __init__(self, session, t):
		TitleCutter.__init__(self, session, t)

	def getAudioTracks(self):
		TitleCutter.getAudioTracks()
		self.exit()
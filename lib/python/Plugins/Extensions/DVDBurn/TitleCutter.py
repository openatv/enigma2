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
			from DVDTitle import ConfigFixedText
			from TitleProperties import languageChoices
			from Components.config import config, ConfigSubsection, ConfigSubList, ConfigSelection, ConfigYesNo
			self.t.properties.audiotracks = ConfigSubList()
			for x in range(n):
				i = audio.getTrackInfo(x)
				DVB_lang = i.getLanguage()
				description = i.getDescription()
				pid = str(i.getPID())
				if description == "MPEG":
					description = "MP2"
				print "[audiotrack] pid:", pid, "description:", description, "language:", DVB_lang
				self.t.properties.audiotracks.append(ConfigSubsection())
				self.t.properties.audiotracks[-1].active = ConfigYesNo(default = True)
				self.t.properties.audiotracks[-1].format = ConfigFixedText(description)
				self.t.properties.audiotracks[-1].language = ConfigSelection(choices = languageChoices.choices, default=languageChoices.getLanguage(DVB_lang))
				self.t.properties.audiotracks[-1].pid = ConfigFixedText(pid)
				self.t.properties.audiotracks[-1].DVB_lang = ConfigFixedText(DVB_lang)
		sAspect = service.info().getInfo(iServiceInformation.sAspect)
		if sAspect in ( 1, 2, 5, 6, 9, 0xA, 0xD, 0xE ):
			aspect = "4:3"
		else:
			aspect = "16:9"
		self.t.properties.aspect.setValue(aspect)
		self.t.VideoType = service.info().getInfo(iServiceInformation.sVideoType)

	def exit(self):
		self.session.nav.stopService()
		self.close(self.cut_list[:])

class CutlistReader(TitleCutter):
	def __init__(self, session, t):
		TitleCutter.__init__(self, session, t)

	def getPMTInfo(self):
		TitleCutter.getPMTInfo(self)
		self.close(self.cut_list[:])

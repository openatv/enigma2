from Components.PerServiceDisplay import PerServiceBase
from Components.Element import cached
from enigma import iPlayableService
from Source import Source

class RadioText(PerServiceBase, Source, object):
	def __init__(self, navcore):
		Source.__init__(self)
		PerServiceBase.__init__(self, navcore,
			{
				iPlayableService.evStart: self.gotEvent,
				iPlayableService.evUpdatedRadioText: self.gotEvent,
				iPlayableService.evEnd: self.gotEvent
			}, with_event=True)

	@cached
	def getText(self):
		service = self.navcore.getCurrentService()
		return service and service.radioText()

	radiotext = property(getText)

	def gotEvent(self, what):
		if what in [iPlayableService.evStart, iPlayableService.evEnd]:
			self.changed((self.CHANGED_CLEAR,))
		else:
			self.changed((self.CHANGED_ALL,))

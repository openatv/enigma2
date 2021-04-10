from Components.PerServiceDisplay import PerServiceBase
from Components.Element import cached
from enigma import iPlayableService
from Source import Source


class RdsDecoder(PerServiceBase, Source, object):
	def __init__(self, navcore):
		Source.__init__(self)
		PerServiceBase.__init__(self, navcore,
			{
				iPlayableService.evStart: self.gotEvent,
				iPlayableService.evUpdatedRadioText: self.gotEvent,
				iPlayableService.evUpdatedRtpText: self.gotEvent,
				iPlayableService.evUpdatedRassInteractivePicMask: self.gotEvent,
				iPlayableService.evEnd: self.gotEvent
			}, with_event=True)

	@cached
	def getDecoder(self):
		service = self.navcore.getCurrentService()
		return service and service.rdsDecoder()

	decoder = property(getDecoder)

	def gotEvent(self, what):
		if what in (iPlayableService.evStart, iPlayableService.evEnd):
			self.changed((self.CHANGED_CLEAR,))
		else:
			self.changed((self.CHANGED_SPECIFIC, what))

	def destroy(self):
		PerServiceBase.destroy(self)
		Source.destroy(self)

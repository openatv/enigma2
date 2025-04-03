from enigma import iPlayableService, eServiceCenter

from Components.Element import cached
from Components.PerServiceDisplay import PerServiceBase
from Components.Sources.Source import Source
import NavigationInstance


class CurrentService(PerServiceBase, Source):
	def __init__(self, navcore):
		Source.__init__(self)
		PerServiceBase.__init__(self, navcore, {
			iPlayableService.evStart: self.serviceEvent,
			iPlayableService.evEnd: self.serviceEvent,
			# FIXME: We should check 'interesting_events' which is not always provided.
			iPlayableService.evUpdatedInfo: self.serviceEvent,
			iPlayableService.evUpdatedEventInfo: self.serviceEvent,
			iPlayableService.evNewProgramInfo: self.serviceEvent,
			iPlayableService.evCuesheetChanged: self.serviceEvent,
			iPlayableService.evVideoSizeChanged: self.serviceEvent,
			iPlayableService.evVideoGammaChanged: self.serviceEvent,
			iPlayableService.evHBBTVInfo: self.serviceEvent
		}, with_event=True)
		self.navcore = navcore
		self.info = None
		self.onManualNewService = []

	def serviceEvent(self, event):
		self.info = None
		self.changed((self.CHANGED_SPECIFIC, event))

	@cached
	def getCurrentService(self):
		return self.navcore.getCurrentService()

	def getCurrentServiceReference(self):
		return self.navcore.getCurrentlyPlayingServiceReference()

	service = property(getCurrentService)

	@cached
	def getCurrentServiceRef(self):
		if NavigationInstance.instance is not None:
			return NavigationInstance.instance.getCurrentServiceReferenceOriginal()
		return None

	serviceref = property(getCurrentServiceRef)

	def newService(self, ref):
		if ref and isinstance(ref, bool):
			self.info = None
		elif ref:
			self.info = eServiceCenter.getInstance().info(ref)
		else:
			self.info = None

		for x in self.onManualNewService:
			x()

		self.changed((self.CHANGED_SPECIFIC, iPlayableService.evStart))


	@cached
	def getCurrentBouquetName(self):
		return NavigationInstance.instance.currentBouquetName if NavigationInstance.instance is not None else ""

	currentBouquetName = property(getCurrentBouquetName)

	def destroy(self):
		PerServiceBase.destroy(self)
		Source.destroy(self)

from enigma import eDVBResourceManager
from Components.NimManager import nimmanager
from Components.Sources.Source import Source


class TunerInfo(Source):
	FE_USE_MASK = 0
	TUNER_AVAILABLE = 1

	def __init__(self):
		Source.__init__(self)
		self.tuner_use_mask = 0
		resourceManager = eDVBResourceManager.getInstance()
		if resourceManager:
			resourceManager.frontendUseMaskChanged.get().append(self.tunerUseMaskChanged)
		else:
			print("[TunerInfo] No resource manager!")

	def tunerUseMaskChanged(self, mask):
		self.tuner_use_mask = mask
		self.changed((self.CHANGED_SPECIFIC, self.FE_USE_MASK))

	def getTunerUseMask(self):
		return self.tuner_use_mask

	def getTunerAmount(self):
		return len(nimmanager.nim_slots)

	def destroy(self):
		resourceManager = eDVBResourceManager.getInstance()
		if resourceManager:
			resourceManager.frontendUseMaskChanged.get().remove(self.tunerUseMaskChanged)
		else:
			print("[TunerInfo] No resource manager!")
		Source.destroy(self)

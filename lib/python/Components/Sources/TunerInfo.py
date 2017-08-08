from Source import Source
from Components.NimManager import nimmanager
from enigma import eDVBResourceManager

class TunerInfo(Source):
    FE_USE_MASK = 0
    TUNER_AVAILABLE = 1

    def __init__(self):
        Source.__init__(self)
        self.tuner_use_mask = 0
        res_mgr = eDVBResourceManager.getInstance()
        if res_mgr:
            res_mgr.frontendUseMaskChanged.get().append(self.tunerUseMaskChanged)
        else:
            print 'no res_mgr!!'

    def tunerUseMaskChanged(self, mask):
        self.tuner_use_mask = mask
        self.changed((self.CHANGED_SPECIFIC, self.FE_USE_MASK))

    def getTunerUseMask(self):
        return self.tuner_use_mask

    def getTunerAmount(self):
        return len(nimmanager.nim_slots)

    def destroy(self):
        res_mgr = eDVBResourceManager.getInstance()
        if res_mgr:
            res_mgr.frontendUseMaskChanged.get().remove(self.tunerUseMaskChanged)
        else:
            print 'no res_mgr!!'
        Source.destroy(self)

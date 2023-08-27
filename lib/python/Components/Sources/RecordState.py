from enigma import iRecordableService
from Components.Element import cached
import Components.RecordingConfig
from Components.Sources.Source import Source
from Components.config import config


class RecordState(Source):
	def __init__(self, session):
		Source.__init__(self)
		self.session = session
		self.recordRunning = 0
		session.nav.record_event.append(self.gotRecordEvent)
		self.gotRecordEvent(None, None)  # Get initial state.

	def gotRecordEvent(self, service, event):
		prevRecord = self.recordRunning
		if event in (iRecordableService.evEnd, iRecordableService.evStart, None):
			recordings = self.session.nav.getRecordings(False, Components.RecordingConfig.recType(config.recording.show_rec_symbol_for_rec_types.getValue()))
			self.recordRunning = len(recordings)
			if self.recordRunning != prevRecord:
				self.changed((self.CHANGED_ALL,))

	def destroy(self):
		self.session.nav.record_event.remove(self.gotRecordEvent)
		Source.destroy(self)

	@cached
	def getBoolean(self):
		return self.recordRunning and True or False

	boolean = property(getBoolean)

	@cached
	def getValue(self):
		return self.recordRunning

	value = property(getValue)

from Components.Sources.Source import Source
from Components.Converter.Poll import Poll
from Components.Element import cached
from Components.OnlineUpdateCheck import versioncheck

class OnlineCheckState(Poll, Source, object):
	IMAGEUPDATEAVAILABLE = 1

	def __init__(self):
		Source.__init__(self)
		Poll.__init__(self)
		self.poll_interval = 60000
		self.poll_enabled = True

	@cached
	def getBoolean(self):
		return versioncheck.getImageUpdateAvailable()

	boolean = property(getBoolean)

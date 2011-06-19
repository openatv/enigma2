from Screens.MessageBox import MessageBox
from Components.config import config

class EpgSaveMsg(MessageBox):
	def __init__(self, session):
		MessageBox.__init__(self, session, _("Are you sure you want to save the EPG Cache to:\n" + config.misc.epgcache_filename.value), MessageBox.TYPE_YESNO)
		self.skinName = "MessageBox"

class EpgLoadMsg(MessageBox):
	def __init__(self, session):
		MessageBox.__init__(self, session, _("Are you sure you want to reload the EPG data from:\n" + config.misc.epgcache_filename.value), MessageBox.TYPE_YESNO)
		self.skinName = "MessageBox"

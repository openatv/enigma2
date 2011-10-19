import Components.Task
from Screens.MessageBox import MessageBox
from Components.config import config
from enigma import eTimer

def EpgCacheCheck(session=None, **kwargs):
	global epgcachecheckpoller
	epgcachecheckpoller = EpgCacheCheckPoller()
	print 'config.epg.cachesched.value',config.epg.cachesched.value
	if config.epg.cachesched.value:
		epgcachecheckpoller.start()
	else:
		epgcachecheckpoller.stop()

class EpgCacheCheckPoller:
	def __init__(self):
		self.timer = eTimer()

	def start(self):
		print '[EPGC] Poller enabled.'
		if self.epgcachecheck not in self.timer.callback:
			self.timer.callback.append(self.epgcachecheck)
		self.timer.startLongTimer(0)

	def stop(self):
		print '[EPGC] Poller disabled.'
		if self.epgcachecheck in self.timer.callback:
			self.timer.callback.remove(self.epgcachecheck)
		self.timer.stop()

	def epgcachecheck(self):
		Components.Task.job_manager.AddJob(self.createCheckJob())

	def createCheckJob(self):
		job = Components.Task.Job(_("EPG Cache Check"))
		if config.epg.cachesched.value:
			task = Components.Task.PythonTask(job, _("Reloading EPG Cache..."))
			task.work = self.JobEpgCache
			task.weighting = 1
		task = Components.Task.PythonTask(job, _("Adding schedule..."))
		task.work = self.JobSched
		task.weighting = 1
		return job

	def JobEpgCache(self):
		print '[EPGC] Refreshing EPGCache.'
		from enigma import eEPGCache
		epgcache = eEPGCache.getInstance()
		epgcache.load()

	def JobSched(self):
		self.timer.startLongTimer(int(config.epg.cachetimer.value) * 3600)


class EpgSaveMsg(MessageBox):
	def __init__(self, session):
		MessageBox.__init__(self, session, _("Are you sure you want to save the EPG Cache to:\n" + config.misc.epgcache_filename.value), MessageBox.TYPE_YESNO)
		self.skinName = "MessageBox"

class EpgLoadMsg(MessageBox):
	def __init__(self, session):
		MessageBox.__init__(self, session, _("Are you sure you want to reload the EPG data from:\n" + config.misc.epgcache_filename.value), MessageBox.TYPE_YESNO)
		self.skinName = "MessageBox"

from enigma import eTimer

import Components.Task
from Screens.MessageBox import MessageBox
from Components.config import config


def EpgCacheLoadCheck(session=None, **kwargs):
	global epgcacheloadcheckpoller
	epgcacheloadcheckpoller = EpgCacheLoadCheckPoller()
	if config.epg.cacheloadsched.value:
		epgcacheloadcheckpoller.start()
	else:
		epgcacheloadcheckpoller.stop()

def EpgCacheSaveCheck(session=None, **kwargs):
	global epgcachesavecheckpoller
	epgcachesavecheckpoller = EpgCacheSaveCheckPoller()
	if config.epg.cachesavesched.value:
		epgcachesavecheckpoller.start()
	else:
		epgcachesavecheckpoller.stop()

class EpgCacheLoadCheckPoller:
	def __init__(self):
		self.timer = eTimer()

	def start(self):
		print '[EPGC Loads] Poller enabled.'
		if self.epgcacheloadcheck not in self.timer.callback:
			self.timer.callback.append(self.epgcacheloadcheck)
		self.timer.startLongTimer(0)

	def stop(self):
		print '[EPGC Load] Poller disabled.'
		if self.epgcacheloadcheck in self.timer.callback:
			self.timer.callback.remove(self.epgcacheloadcheck)
		self.timer.stop()

	def epgcacheloadcheck(self):
		Components.Task.job_manager.AddJob(self.createLoadCheckJob())

	def createLoadCheckJob(self):
		job = Components.Task.Job(_("EPG Cache Check"))
		if config.epg.cacheloadsched.value:
			task = Components.Task.PythonTask(job, _("Reloading EPG Cache..."))
			task.work = self.JobEpgCacheLoad
			task.weighting = 1
		task = Components.Task.PythonTask(job, _("Adding schedule..."))
		task.work = self.JobSched
		task.weighting = 1
		return job

	def JobEpgCacheLoad(self):
		print '[EPGC] Refreshing EPGCache.'
		from enigma import eEPGCache
		epgcache = eEPGCache.getInstance()
		epgcache.load()

	def JobSched(self):
		self.timer.startLongTimer(int(config.epg.cacheloadtimer.value) * 3600)

class EpgCacheSaveCheckPoller:
	def __init__(self):
		self.timer = eTimer()

	def start(self):
		print '[EPGC Save] Poller enabled.'
		if self.epgcachesavecheck not in self.timer.callback:
			self.timer.callback.append(self.epgcachesavecheck)
		self.timer.startLongTimer(0)

	def stop(self):
		print '[EPGC Save] Poller disabled.'
		if self.epgcachesavecheck in self.timer.callback:
			self.timer.callback.remove(self.epgcachesavecheck)
		self.timer.stop()

	def epgcachesavecheck(self):
		Components.Task.job_manager.AddJob(self.createSaveCheckJob())

	def createSaveCheckJob(self):
		job = Components.Task.Job(_("EPG Cache Check"))
		if config.epg.cachesavesched.value:
			task = Components.Task.PythonTask(job, _("Saving EPG Cache..."))
			task.work = self.JobEpgCacheSave
			task.weighting = 1
		task = Components.Task.PythonTask(job, _("Adding schedule..."))
		task.work = self.JobSched
		task.weighting = 1
		return job

	def JobEpgCacheSave(self):
		print '[EPGC] Saving EPGCache.'
		from enigma import eEPGCache
		epgcache = eEPGCache.getInstance()
		epgcache.save()

	def JobSched(self):
		self.timer.startLongTimer(int(config.epg.cachesavetimer.value) * 3600)

class EpgSaveMsg(MessageBox):
	def __init__(self, session):
		MessageBox.__init__(self, session, _("Are you sure you want to save the EPG Cache to:\n") + config.misc.epgcache_filename.value, MessageBox.TYPE_YESNO)
		self.skinName = "MessageBox"

class EpgLoadMsg(MessageBox):
	def __init__(self, session):
		MessageBox.__init__(self, session, _("Are you sure you want to reload the EPG data from:\n") + config.misc.epgcache_filename.value, MessageBox.TYPE_YESNO)
		self.skinName = "MessageBox"

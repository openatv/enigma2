from Screen import Screen
from InfoBarGenerics import InfoBarNotifications

class JobView(InfoBarNotifications, Screen):
	def __init__(self, session, job, parent=None, cancelable = True, backgroundable = True, close_on_finish = False):
		from Components.Sources.StaticText import StaticText
		from Components.Sources.Progress import Progress
		from Components.Sources.Boolean import Boolean
		from Components.ActionMap import ActionMap
		Screen.__init__(self, session, parent)
		InfoBarNotifications.__init__(self)
		self.parent = parent
		self.job = job
		self.job.taskview = self
		self.close_on_finish = close_on_finish

		self["job_name"] = StaticText(job.name)
		self["job_progress"] = Progress()
		self["job_status"] = StaticText()
		self["job_task"] = StaticText()
		self["finished"] = Boolean()
		self["cancelable"] = Boolean(cancelable)
		self["backgroundable"] = Boolean(backgroundable)

		self["key_blue"] = StaticText(_("Background"))

		self.onShow.append(self.windowShow)
		self.onHide.append(self.windowHide)

		self["actions"] = ActionMap(["OkCancelActions"], 
			{
				"ok": self.ok,
				"cancel": self.ok
			})
		self["ColorActions"] = ActionMap(["ColorActions"],
			{
				"red": self.abort,
				"green": self.ok,
				"blue": self.background,
			})

	def windowShow(self):
		self.job.state_changed.append(self.state_changed)
		self.state_changed()

	def windowHide(self):
		if len(self.job.state_changed) > 0:
		    self.job.state_changed.remove(self.state_changed)

	def state_changed(self):
		j = self.job
		self["job_progress"].range = j.end
		self["job_progress"].value = j.progress
		#print "JobView::state_changed:", j.end, j.progress
		self["job_status"].text = {j.NOT_STARTED: _("Waiting"), j.IN_PROGRESS: _("In Progress"), j.FINISHED: _("Finished"), j.FAILED: _("Failed")}[j.status]
		if j.status == j.IN_PROGRESS:
			self["job_task"].text = j.tasks[j.current_task].name
		else:
			self["job_task"].text = ""
		if j.status in [j.FINISHED, j.FAILED]:
			if self.close_on_finish:
				self.close()
			self["backgroundable"].boolean = False
			if j.status == j.FINISHED:
				self["finished"].boolean = True
				self["cancelable"].boolean = False
			elif j.status == j.FAILED:
				self["cancelable"].boolean = True

	def background(self):
		print "[background]"
		if self["backgroundable"].boolean == True:
			self.close(True)

	def ok(self):
		if self.job.status in [self.job.FINISHED, self.job.FAILED]:
			self.close(False)

	def abort(self):
		if self.job.status in [self.job.FINISHED, self.job.FAILED]:
			self.close(False)
		if self["cancelable"].boolean == True:
			self.job.cancel()

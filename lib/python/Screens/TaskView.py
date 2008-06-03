from Screen import Screen

class JobView(Screen):
	def __init__(self, session, job, cancelable = True, close_on_finish = False):
		from Components.Sources.StaticText import StaticText
		from Components.Sources.Progress import Progress
		from Components.Sources.Boolean import Boolean
		from Components.ActionMap import ActionMap
		Screen.__init__(self, session)
		self.job = job
		self.close_on_finish = close_on_finish
		self.cancelable = cancelable

		self["job_name"] = StaticText(job.name)
		self["job_progress"] = Progress()
		self["job_status"] = StaticText()
		self["job_task"] = StaticText()
		self["finished"] = Boolean()

		self.onShow.append(self.windowShow)
		self.onHide.append(self.windowHide)

		self["actions"] = ActionMap(["OkCancelActions"], 
			{
				"ok": self.ok,
				"cancel": self.abort
			})

	def windowShow(self):
		self.job.state_changed.append(self.state_changed)
		self.state_changed()

	def windowHide(self):
		self.job.state_changed.remove(self.state_changed)

	def state_changed(self):
		j = self.job
		self["job_progress"].range = j.end
		self["job_progress"].value = j.progress
		print "JobView::state_changed:", j.end, j.progress
		self["job_status"].text = {j.NOT_STARTED: _("Waiting"), j.IN_PROGRESS: _("In Progress"), j.FINISHED: _("Finished"), j.FAILED: _("Failed")}[j.status]
		if j.status == j.IN_PROGRESS:
			self["job_task"].text = j.tasks[j.current_task].name
		else:
			self["job_task"].text = ""
		if j.status in [j.FINISHED, j.FAILED]:
			if self.close_on_finish:
				self.close()
			else:
				self["finished"].boolean = True

	def ok(self):
		if self.job.status in [self.job.FINISHED, self.job.FAILED]:
			self.close()

	def abort(self):
		if self.job.status in [self.job.FINISHED, self.job.FAILED]:
			self.close()
		if self.cancelable:
			self.job.cancel()

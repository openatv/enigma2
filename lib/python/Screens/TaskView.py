from Screen import Screen

class JobView(Screen):
	def __init__(self, session, job, cancelable = True, close_on_finish = False):
		from Components.Sources.StaticText import StaticText
		from Components.Sources.Progress import Progress
		from Components.ActionMap import ActionMap
		Screen.__init__(self, session)
		self.job = job
		self.close_on_finish = close_on_finish

		self["job_name"] = StaticText(job.name)
		self["job_progress"] = Progress()
		self["job_status"] = StaticText()
		self["job_task"] = StaticText()

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
		self["job_progress"].range = len(j.tasks)
		self["job_progress"].value = j.current_task
		self["job_status"].text = {j.NOT_STARTED: _("Waiting"), j.IN_PROGRESS: _("In Progress"), j.FINISHED: _("Finished"), j.FAILED: _("Failed")}[j.status]
		if j.status == j.IN_PROGRESS:
			self["job_task"].text = j.tasks[j.current_task].name
		else:
			self["job_task"].text = ""
		if j.status in [j.FINISHED, j.FAILED] and self.close_on_finish:
			self.close()

	def ok(self):
		if self.job.status in [self.job.FINISHED, self.job.FAILED]:
			self.close()

	def abort(self):
		if self.job.status in [self.job.FINISHED, self.job.FAILED]:
			self.close()
		if self.cancelable:
			self.job.cancel()

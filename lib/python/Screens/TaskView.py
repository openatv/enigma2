from Components.ActionMap import HelpableActionMap
from Components.config import ConfigSubsection, ConfigSelection
from Components.ConfigList import ConfigListScreen
from Components.SystemInfo import BoxInfo, getBoxDisplayName
from Components.Task import job_manager
from Components.Sources.Progress import Progress
from Components.Sources.StaticText import StaticText
from Screens.HelpMenu import HelpableScreen
from Screens.InfoBarGenerics import InfoBarNotifications
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Standby import QUIT_SHUTDOWN, Standby, TryQuitMainloop, inStandby, inTryQuitMainloop
from Tools.Notifications import AddNotification, AddNotificationWithCallback, notifications


class TaskView(Screen, HelpableScreen, ConfigListScreen, InfoBarNotifications):
	skin = """
	<screen name="TaskList" title="Task List" position="center,center" size="930,255" resolution="1280,720">
		<widget source="name" render="Label" position="0,0" size="930,35" font="Regular;25" />
		<widget source="job" render="Label" position="0,35" size="930,35" font="Regular;25" />
		<widget source="progress" render="Progress" position="0,80" size="930,35" backgroundColor="#254f7497" borderWidth="2" />
		<widget source="progress" render="Label" position="0,80" size="930,35" borderColor="#00000000" borderWidth="2" font="Regular;25" foregroundColor="#00ffd700" halign="center" transparent="1" valign="center" zPosition="+1">
			<convert type="ProgressToText" />
		</widget>
		<widget source="status" render="Label" position="0,125" size="930,35" font="Regular;25" />
		<widget name="config" position="0,170" size="930,35" font="Regular;25" itemHeight="35" valueFont="Regular;25" />
		<widget source="key_red" render="Label" position="0,e-40" size="180,40" backgroundColor="key_red" conditional="key_red" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="190,e-40" size="180,40" backgroundColor="key_green" conditional="key_green" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_yellow" render="Label" position="380,e-40" size="180,40" backgroundColor="key_yellow" conditional="key_yellow" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_blue" render="Label" position="570,e-40" size="180,40" backgroundColor="key_blue" conditional="key_blue" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_menu" render="Label" position="e-170,e-40" size="80,40" backgroundColor="key_back" conditional="key_menu" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-80,e-40" size="80,40" backgroundColor="key_back" conditional="key_help" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	def __init__(self, session, job, parent=None, cancelable=True, backgroundable=True, afterEventChangeable=True, afterEvent="nothing"):
		Screen.__init__(self, session, parent)
		HelpableScreen.__init__(self)
		self.config = []
		ConfigListScreen.__init__(self, self.config)
		InfoBarNotifications.__init__(self)
		self.job = job
		self.parent = parent
		self.cancelable = cancelable
		self.backgroundable = backgroundable
		self.afterEventChangeable = afterEventChangeable
		self.skinName = ["TaskView", "JobView"]
		if not self.getTitle():
			self.setTitle(_("Task View"))
		self["name"] = StaticText(job.name)
		self["progress"] = Progress()
		self["task"] = StaticText()
		self["status"] = StaticText()
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Background") if backgroundable else "")
		self["key_yellow"] = StaticText(_("Cancel Task") if cancelable else "")
		self["key_blue"] = StaticText(_("After Event") if afterEventChangeable else "")
		self["summary_job_name"] = StaticText(job.name)  # For front panel screen.
		self["summary_job_progress"] = Progress()  # For front panel screen.
		self["summary_job_task"] = StaticText()  # For front panel screen.
		self["setupActions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions"], {
			"cancel": (self.keyClose, _("Close Task View")),
			"red": (self.keyClose, _("Close Task View"))
		}, prio=0, description=_("Task View Actions"))
		self["backgroundActions"] = HelpableActionMap(self, ["ColorActions"], {
			"green": (self.keyBackground, _("Continue to run the task in the background"))
		}, prio=0, description=_("Task View Actions"))
		self["backgroundActions"].setEnabled(cancelable)
		self["cancelActions"] = HelpableActionMap(self, ["ColorActions"], {
			"yellow": (self.keyCancelTask, _("Cancel the task"))
		}, prio=0, description=_("Task View Actions"))
		self["cancelActions"].setEnabled(cancelable)
		self["selectionActions"] = HelpableActionMap(self, ["OkActions", "ColorActions", "NavigationActions"], {
			"ok": (self.keyMenu, _("Display selection list as a selection menu")),
			"blue": (self.keyMenu, _("Display selection list as a selection menu")),
			"first": (self.keyFirst, _("Select the first item in the list")),
			"left": (self.keyLeft, _("Select the previous item in the list")),
			"right": (self.keyRight, _("Select the next item in the list")),
			"last": (self.keyLast, _("Select the last item in the list"))
		}, prio=0, description=_("Common Setup Actions"))
		self["selectionActions"].setEnabled(afterEventChangeable)
		self["menuConfigActions"].setEnabled(afterEventChangeable)  # Also adjust the ConfigList menu action.
		if "configActions" in self:
			self["configActions"].setEnabled(False)  # Disable the ConfigList select action.
		if "navigationActions" in self:
			self["navigationActions"].setEnabled(False)  # Disable the ConfigList navigation actions.
		if afterEvent:
			self.job.afterEvent = afterEvent
		self.setting = ConfigSubsection()
		shutdownString = _("Go to deep standby") if BoxInfo.getItem("DeepstandbySupport") else _("Shut down")
		self.setting.afterEvent = ConfigSelection(default=self.job.afterEvent or "nothing", choices=[
			("nothing", _("Do nothing")),
			("close", _("Close Task View")),
			("standby", _("Go to standby")),
			("deepstandby", shutdownString)
		])
		self.job.afterEvent = self.setting.afterEvent.value
		self["config"].setList([(_("After event"), self.setting.afterEvent, _("Select an action to perform when the task has completed."))])
		self.onLayoutFinish.append(self.layoutFinished)
		self.onClose.append(self.closed)
		self.job.state_changed.append(self.stateChanged)
		self.updateConfigList()
		self.stateChanged()

	def layoutFinished(self):
		self["config"].instance.enableAutoNavigation(False)

	def closed(self):
		self.job.state_changed.remove(self.stateChanged)

	def keyClose(self):
		self.close(self.job.status not in (self.job.FINISHED, self.job.FAILED))

	def keyBackground(self):
		self.close(True)

	def keyCancelTask(self):
		if self.job.status == self.job.NOT_STARTED:
			job_manager.active_jobs.remove(self.job)
			self.close(False)
		elif self.job.status == self.job.IN_PROGRESS and self.cancelable:
			self.job.cancel()
		else:
			self.close(False)

	def keyMenu(self):
		ConfigListScreen.keyMenu(self)
		self.updateConfigList()

	def keyFirst(self):
		ConfigListScreen.keyFirst(self)
		self.updateConfigList()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.updateConfigList()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.updateConfigList()

	def keyLast(self):
		ConfigListScreen.keyLast(self)
		self.updateConfigList()

	def updateConfigList(self):
		self.job.afterEvent = self.setting.afterEvent.value

	def stateChanged(self):
		job = self.job
		self["progress"].range = job.end
		self["summary_job_progress"].range = job.end  # For front panel screen.
		self["progress"].value = job.progress
		self["summary_job_progress"].value = job.progress  # For front panel screen.
		# print("[TaskView] TaskView stateChanged: %s %s." % (job.end, job.progress))
		self["status"].setText(job.getStatustext())
		if job.status == job.IN_PROGRESS:
			self["task"].setText(job.tasks[job.current_task].name)
			self["summary_job_task"].setText(job.tasks[job.current_task].name)  # For front panel screen.
		else:
			self["task"].setText("")
			self["summary_job_task"].setText(job.getStatustext())  # For front panel screen.
		if job.status in (job.FINISHED, job.FAILED):
			if self.setting.afterEvent.value == "close" and self.job.status == self.job.FINISHED:
				self.close(False)
			self["key_green"].setText("")
			self["backgroundActions"].setEnabled(False)
			self["key_yellow"].setText("")
			self["cancelActions"].setEnabled(False)
			self["key_blue"].setText("")
			self["selectionActions"].setEnabled(False)
			self["menuConfigActions"].setEnabled(False)  # Disable the ConfigList menu action.
			if self.setting.afterEvent.value == "nothing":
				return
			if self.setting.afterEvent.value == "deepstandby":
				if not inTryQuitMainloop:
					AddNotificationWithCallback(self.sendTryQuitMainloopNotification, MessageBox, _("A completed task wants to shut down your %s %s. Shutdown now?") % getBoxDisplayName(), timeout=30)
			elif self.setting.afterEvent.value == "standby":
				if not inStandby:
					AddNotificationWithCallback(self.sendStandbyNotification, MessageBox, _("A completed task wants to set your %s %s to standby. Do that now?") % getBoxDisplayName(), timeout=30)

	def sendTryQuitMainloopNotification(self, answer):
		if answer:
			AddNotification(TryQuitMainloop, QUIT_SHUTDOWN)

	def sendStandbyNotification(self, answer):
		if answer:
			AddNotification(Standby)

	def checkNotifications(self):
		InfoBarNotifications.checkNotifications(self)
		if not notifications:
			if self.setting.afterEvent.value == "close" and self.job.status == self.job.FAILED:
				self.close(False)


class JobView(TaskView):
	pass

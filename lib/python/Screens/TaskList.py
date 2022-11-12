from enigma import eTimer

from Components.ActionMap import HelpableActionMap
from Components.Task import job_manager
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Screens.HelpMenu import HelpableScreen
from Screens.Screen import Screen
from Screens.TaskView import TaskView


class TaskList(Screen, HelpableScreen):
	skin = ["""
	<screen name="TaskList" title="Task List" position="center,center" size="700,350" resolution="1280,720">
		<widget source="tasklist" render="Listbox" position="0,0" size="700,300">
			<convert type="TemplatedMultiContent">
				{
				"template":
					[
					MultiContentEntryText(pos=(%d, %d), size=(%d, %d), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=1),  # Name.
					MultiContentEntryText(pos=(%d, %d), size=(%d, %d), font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER, text=2),  # State.
					MultiContentEntryProgress(pos=(%d, %d), size=(%d, %d), percent=-3),  # Progress.
					MultiContentEntryText(pos=(%d, %d), size=(%d, %d), font=0, flags=RT_HALIGN_RIGHT | RT_VALIGN_CENTER, text=4),  # Percentage.
					],
				"fonts": [parseFont("Regular;%d")],
				"itemHeight": %d
				}
			</convert>
		</widget>
		<widget source="key_red" render="Label" position="0,e-40" size="180,40" backgroundColor="key_red" conditional="key_red" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="190,e-40" size="180,40" backgroundColor="key_green" conditional="key_green" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-80,e-40" size="80,40" backgroundColor="key_back" conditional="key_help" font="Regular;20" foregroundColor="key_text" halign="center" valign="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>""",
		15, 0, 700, 25,  # Name.
		15, 25, 155, 25,  # State.
		190, 28, 400, 19,  # Progress.
		600, 25, 80, 25,  # Percentage.
		20,  # Font.
		50  # ItemHeight.
	]

	def __init__(self, session, tasklist):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		self.tasklist = tasklist
		self.skinName = ["TaskList", "TaskListScreen"]
		if not self.getTitle():
			self.setTitle(_("Task List"))
		self["tasklist"] = List(self.tasklist)
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions", "NavigationActions"], {
			"cancel": (self.keyCancel, _("Close Task List")),
			"red": (self.keyCancel, _("Close Task List")),
			"top": (self["tasklist"].goTop, _("Move to first line / screen")),
			"pageUp": (self["tasklist"].goPageUp, _("Move up a screen")),
			"up": (self["tasklist"].goLineUp, _("Move up a line")),
			"down": (self["tasklist"].goLineDown, _("Move down a line")),
			"pageDown": (self["tasklist"].goPageDown, _("Move down a screen")),
			"bottom": (self["tasklist"].goBottom, _("Move to last line / screen"))
		}, prio=0, description=_("Task List Actions"))
		self["detailAction"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions"], {
			"ok": (self.keyOK, _("Show details of highlighted task")),
			"green": (self.keyOK, _("Show details of highlighted task"))
		}, prio=0, description=_("Task List Actions"))
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText()
		self.timer = eTimer()
		self.timer.callback.append(self.timerFire)
		self.onLayoutFinish.append(self.layoutFinished)
		self.timerFire()

	def layoutFinished(self):
		self["tasklist"].downstream_elements.downstream_elements.instance.enableAutoNavigation(False)

	def keyCancel(self):
		self.timer.stop()
		self.close()

	def keyOK(self):
		def TaskViewCallback(result):
			print("[TaskList] TaskView returned: '%s'." % result)
			self.timerFire()

		self.timer.stop()
		current = self["tasklist"].getCurrent()
		if current:
			self.session.openWithCallback(TaskViewCallback, TaskView, current[0])

	def timerFire(self):
		self.timer.stop()
		index = self["tasklist"].getIndex()
		self.tasklist = []
		for job in job_manager.getPendingJobs():
			# self.tasklist.append((job, job.name, job.getStatustext(), int(100 * job.progress / float(job.end)), str(100 * job.progress / float(job.end)) + "%"))
			progress = job.getProgress()
			if job.name.startswith(_("Run script")) and job.status == job.IN_PROGRESS:  # Fake progress for scripts.
				if progress >= 99:
					job.tasks[job.current_task].setProgress(51)
				else:
					job.tasks[job.current_task].setProgress(progress + 1)
			self.tasklist.append((job, job.name, job.getStatustext(), progress, "%d %%" % progress))
		self["tasklist"].updateList(self.tasklist)
		self["tasklist"].setIndex(index)
		if self.tasklist:
			self["key_green"].setText(_("Details"))
			self["detailAction"].setEnabled(True)
		else:
			self["key_green"].setText("")
			self["detailAction"].setEnabled(False)
		self.timer.startLongTimer(1)


class TaskListScreen(TaskList):
	pass

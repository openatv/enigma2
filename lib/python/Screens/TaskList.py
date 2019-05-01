# -*- coding: utf-8 -*-
# taken from mytube plugin

from enigma import eTimer
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.Label import Label
from Components.Sources.List import List
from Components.MultiContent import MultiContentEntryText
from Components.Task import job_manager


class TaskListScreen(Screen):
	skin = """
		<screen name="TaskListScreen" position="center,center" size="720,576" title="Task list" >
			<widget source="tasklist" render="Listbox" position="10,10" size="690,490" zPosition="7" scrollbarMode="showOnDemand">
				<convert type="TemplatedMultiContent">
					{"template": [
							MultiContentEntryText(pos = (5, 1), size = (675, 24), font=1, flags = RT_HALIGN_LEFT, text = 1), # name
							MultiContentEntryText(pos = (5, 25), size = (150, 24), font=1, flags = RT_HALIGN_LEFT, text = 2), # state
							MultiContentEntryProgress(pos = (160, 25), size = (390, 20), percent = -3), # progress
							MultiContentEntryText(pos = (560, 25), size = (100, 24), font=1, flags = RT_HALIGN_RIGHT, text = 4), # percentage
						],
					"fonts": [gFont("Regular", 22),gFont("Regular", 18)],
					"itemHeight": 50
					}
				</convert>
			</widget>
			<ePixmap position="10,530" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
			<widget name="key_red" position="10,530" zPosition="5" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1"/>
		</screen>"""

	def __init__(self, session, tasklist):
		Screen.__init__(self, session)
		self.session = session
		self.tasklist = tasklist
		self["tasklist"] = List(self.tasklist)

		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions", "MediaPlayerActions"],
		{
			"ok": self.keyOK,
			"back": self.keyCancel,
			"red": self.keyCancel,
		}, -1)

		self["key_red"] = Button(_("Close"))

		self.onLayoutFinish.append(self.layoutFinished)
		self.onShown.append(self.setWindowTitle)
		self.onClose.append(self.__onClose)
		self.Timer = eTimer()
		self.Timer.callback.append(self.TimerFire)

	def __onClose(self):
		del self.Timer

	def layoutFinished(self):
		self.Timer.startLongTimer(1)

	def TimerFire(self):
		self.Timer.stop()
		self.rebuildTaskList()

	def rebuildTaskList(self):
		idx = self['tasklist'].getIndex()
		self.tasklist = []
		for job in job_manager.getPendingJobs():
			#self.tasklist.append((job,job.name,job.getStatustext(),int(100*job.progress/float(job.end)) ,str(100*job.progress/float(job.end)) + "%" ))
			progress = job.getProgress()
			if job.name.startswith(_('Run script')) and job.status == job.IN_PROGRESS: #fake progress for scripts
				if progress >= 99:
					job.tasks[job.current_task].setProgress(51)
				else:
					job.tasks[job.current_task].setProgress(progress + 1)
			self.tasklist.append((job,job.name,job.getStatustext(),progress,str(progress) + " %" ))
		self['tasklist'].setList(self.tasklist)
		self['tasklist'].updateList(self.tasklist)
		self['tasklist'].setIndex(idx)
		self.Timer.startLongTimer(1)

	def setWindowTitle(self):
		self.setTitle(_("Task list"))

	def keyOK(self):
		current = self["tasklist"].getCurrent()
		print current
		if current:
			job = current[0]
			from Screens.TaskView import JobView
			self.session.openWithCallback(self.JobViewCB, JobView, job)

	def JobViewCB(self, why):
		print "WHY---",why

	def keyCancel(self):
		self.close()

	def keySave(self):
		self.close()
 
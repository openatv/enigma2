from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.HelpMenu import HelpableScreen
from Components.ActionMap import HelpableActionMap, ActionMap
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Components.Sources.Progress import Progress
from Components.Task import Task, Job, job_manager, Condition
from Components.ScrollLabel import ScrollLabel

class DVDToolbox(Screen):
	skin = """
		<screen position="90,83" size="560,445" title="DVD media toolbox" >
		    <ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
		    <ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
		    <ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
		    <ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" alphatest="on" />
		    <widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		    <widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		    <widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
		    <widget source="key_blue" render="Label" position="420,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" />
		    <widget source="info" render="Label" position="20,60" size="520,100" font="Regular;20" />
		    <widget name="details" position="20,200" size="520,200" font="Regular;16" />
		    <widget source="space_bar" render="Progress" position="10,410" size="540,26" borderWidth="1" backgroundColor="#254f7497" />
		    <widget source="space_label" render="Label" position="20,414" size="520,22" zPosition="2" font="Regular;18" halign="center" transparent="1" foregroundColor="#000000" />
		</screen>"""

	def __init__(self, session, project = None):
		Screen.__init__(self, session)
		self.project = project
		
		self["key_red"] = StaticText(_("Exit"))
		self["key_green"] = StaticText(_("Update"))
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		
		self["space_label"] = StaticText()
		self["space_bar"] = Progress()
		
		self.mediuminfo = [ ]
		self.formattable = False
		self["details"] = ScrollLabel()
		self["info"] = StaticText()

		self["toolboxactions"] = ActionMap(["ColorActions", "DVDToolbox"],
		{
		    "red": self.close,
		    "green": self.update,
		    "yellow": self.format,
		    #"blue": self.eject,
		    "cancel": self.close,
		    "pageUp": self.pageUp,
		    "pageDown": self.pageDown
		})
		self.update()
		
	def pageUp(self):
		self["details"].pageUp()

	def pageDown(self):
		self["details"].pageDown()

	def update(self):
		self["space_label"].text = _("Please wait... Loading list...")
		self["info"].text = ""
		self["details"].setText("")
		self.mediuminfo = [ ]
		job = DVDinfoJob(self)
		job_manager.AddJob(job)
		
	def infoJobCB(self):
		capacity = 1
		used = 0
		infotext = ""
		mediatype = ""
		for line in self.mediuminfo:
			if line.find("Mounted Media:") > -1:
				mediatype = line.rsplit(',',1)[1][1:-1]
				if mediatype.find("RW") > 0:
					self.formattable = True
				else:
					self.formattable = False
			if line.find("Legacy lead-out at:") > -1:
				used = int(line.rsplit('=',1)[1]) / 1048576.0
				print "[lead out] used =", used
			elif line.find("formatted:") > -1:
				capacity = int(line.rsplit('=',1)[1]) / 1048576.0
				print "[formatted] capacity =", capacity
			elif capacity == 1 and line.find("READ CAPACITY:") > -1:
				capacity = int(line.rsplit('=',1)[1]) / 1048576.0
				print "[READ CAP] capacity =", capacity
			elif line.find("Disc status:") > -1:
				if line.find("blank") > -1:
					print "[Disc status] capacity=%d, used=0" % (capacity)
					capacity = used
					used = 0
			infotext += line
		self["details"].setText(infotext)
		if self.formattable:
			self["key_yellow"].text = _("Format")
		else:
			self["key_yellow"].text = ""
		percent = 100 * used / capacity
		if capacity > 4600:
			self["space_label"].text = "%d / %d MB" % (used, capacity) + " (%.2f%% " % percent + _("of a DUAL layer medium used.") + ")"
			self["space_bar"].value = int(percent)
		elif capacity > 1:
			self["space_label"].text = "%d / %d MB" % (used, capacity) + " (%.2f%% " % percent + _("of a SINGLE layer medium used.") + ")"
			self["space_bar"].value = int(percent)
		elif capacity == 1 and used > 0:
			self["space_label"].text = "%d MB " % (used) + _("on READ ONLY medium.")
			self["space_bar"].value = int(percent)
		else:
			self["space_label"].text = _("Medium is not a writeable DVD!")
			self["space_bar"].value = 0
		free = capacity-used
		if free < 2:
			free = 0
		self["info"].text = "Media-Type:\t\t%s\nFree capacity:\t\t%d MB" % (mediatype or "NO DVD", free)

	def format(self):
		if self.formattable:
			job = DVDformatJob(self)
			job_manager.AddJob(job)
			from Screens.TaskView import JobView
			self.session.openWithCallback(self.infoJobCB, JobView, job)

class DVDformatJob(Job):
	def __init__(self, toolbox):
		Job.__init__(self, _("DVD media toolbox"))
		self.toolbox = toolbox
		DVDformatTask(self)
		
	def retry(self):
		self.tasks[0].args += [ "-force" ]
		Job.retry(self)

class DVDformatTaskPostcondition(Condition):
	RECOVERABLE = True
	def check(self, task):
		return task.error is None

	def getErrorMessage(self, task):
		return {
			task.ERROR_ALREADYFORMATTED: _("This DVD RW medium is already formatted - reformatting will erase all content on the disc."),
			task.ERROR_NOTWRITEABLE: _("Medium is not a writeable DVD!"),
			task.ERROR_UNKNOWN: _("An unknown error occured!")
		}[task.error]

class DVDformatTask(Task):
	ERROR_ALREADYFORMATTED, ERROR_NOTWRITEABLE, ERROR_UNKNOWN = range(3)
	def __init__(self, job, extra_args=[]):
		Task.__init__(self, job, ("RW medium format"))
		self.toolbox = job.toolbox
		self.postconditions.append(DVDformatTaskPostcondition())
		self.setTool("/bin/dvd+rw-format")
		self.args += [ "/dev/cdroms/cdrom0" ]
		self.end = 1100

	def prepare(self):
		self.error = None

	def processOutputLine(self, line):
		if line.startswith("- media is already formatted"):
			self.error = self.ERROR_ALREADYFORMATTED
			self.force = True
		if line.startswith(":-( mounted media doesn't appear to be"):
			self.error = self.ERROR_NOTWRITEABLE

	def processOutput(self, data):
		print "[DVDformatTask processOutput]  ", data
		if data.endswith('%'):
			data= data.replace('\x08','')
			self.progress = int(float(data[:-1])*10)
		else:
			Task.processOutput(self, data)

class DVDinfoJob(Job):
	def __init__(self, toolbox):
		Job.__init__(self, "DVD media toolbox")
		self.toolbox = toolbox
		DVDinfoTask(self)

class DVDinfoTaskPostcondition(Condition):
	RECOVERABLE = True
	def check(self, task):
		return task.error is None

	def getErrorMessage(self, task):
		return {
			task.ERROR_UNKNOWN: _("An unknown error occured!")
		}[task.error]

class DVDinfoTask(Task):
	ERROR_UNKNOWN = range(1)
	def __init__(self, job, extra_args=[]):
		Task.__init__(self, job, ("mediainfo"))
		self.toolbox = job.toolbox
		self.postconditions.append(DVDinfoTaskPostcondition())
		self.setTool("/bin/dvd+rw-mediainfo")
		self.args += [ "/dev/cdroms/cdrom0" ]

	def prepare(self):
		self.error = None

	def processOutputLine(self, line):
		print "[DVDinfoTask]", line[:-1]
		self.toolbox.mediuminfo.append(line)

	def processFinished(self, returncode):
		Task.processFinished(self, returncode)
		self.toolbox.infoJobCB()

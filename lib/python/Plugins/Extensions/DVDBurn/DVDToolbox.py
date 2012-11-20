from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.HelpMenu import HelpableScreen
from Components.ActionMap import HelpableActionMap, ActionMap
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Components.Sources.Progress import Progress
from Components.Task import Task, Job, job_manager, Condition
from Components.ScrollLabel import ScrollLabel
from Components.Harddisk import harddiskmanager
from Components.Console import Console
from Plugins.SystemPlugins.Hotplug.plugin import hotplugNotifier

class DVDToolbox(Screen):
	skin = """
		<screen name="DVDToolbox" position="center,center"  size="560,445" title="DVD media toolbox" >
		    <ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
		    <ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
		    <ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
		    <widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		    <widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		    <widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
		    <widget source="info" render="Label" position="20,60" size="520,100" font="Regular;20" />
		    <widget name="details" position="20,200" size="520,200" font="Regular;16" />
		    <widget source="space_bar" render="Progress" position="10,410" size="540,26" borderWidth="1" backgroundColor="#254f7497" />
		    <widget source="space_label" render="Label" position="20,414" size="520,22" zPosition="2" font="Regular;18" halign="center" transparent="1" foregroundColor="#000000" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)

		self["key_red"] = StaticText(_("Exit"))
		self["key_green"] = StaticText(_("Update"))
		self["key_yellow"] = StaticText()

		self["space_label"] = StaticText()
		self["space_bar"] = Progress()

		self.mediuminfo = [ ]
		self.formattable = False
		self["details"] = ScrollLabel()
		self["info"] = StaticText()

		self["toolboxactions"] = ActionMap(["ColorActions", "DVDToolbox", "OkCancelActions"],
		{
		    "red": self.exit,
		    "green": self.update,
		    "yellow": self.format,
		    "cancel": self.exit,
		    "pageUp": self.pageUp,
		    "pageDown": self.pageDown
		})
		self.update()
		hotplugNotifier.append(self.update)
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(_("DVD media toolbox"))

	def pageUp(self):
		self["details"].pageUp()

	def pageDown(self):
		self["details"].pageDown()

	def update(self, dev="", action=""):
		self["space_label"].text = _("Please wait... Loading list...")
		self["info"].text = ""
		self["details"].setText("")
		self.Console = Console()
		cmd = "dvd+rw-mediainfo /dev/" + harddiskmanager.getCD()
		self.Console.ePopen(cmd, self.mediainfoCB)

	def format(self):
		if self.formattable:
			job = DVDformatJob(self)
			job_manager.AddJob(job)
			from Screens.TaskView import JobView
			self.session.openWithCallback(self.formatCB, JobView, job)

	def formatCB(self, in_background):
		self.update()

	def mediainfoCB(self, mediuminfo, retval, extra_args):
		formatted_capacity = 0
		read_capacity = 0
		capacity = 0
		used = 0
		infotext = ""
		mediatype = ""
		for line in mediuminfo.splitlines():
			if line.find("Mounted Media:") > -1:
				mediatype = line.rsplit(',',1)[1][1:]
				if mediatype.find("RW") > 0 or mediatype.find("RAM") > 0:
					self.formattable = True
				else:
					self.formattable = False
			elif line.find("Legacy lead-out at:") > -1:
				used = int(line.rsplit('=',1)[1]) / 1048576.0
				print "[dvd+rw-mediainfo] lead out used =", used
			elif line.find("formatted:") > -1:
				formatted_capacity = int(line.rsplit('=',1)[1]) / 1048576.0
				print "[dvd+rw-mediainfo] formatted capacity =", formatted_capacity
			elif formatted_capacity == 0 and line.find("READ CAPACITY:") > -1:
				read_capacity = int(line.rsplit('=',1)[1]) / 1048576.0
				print "[dvd+rw-mediainfo] READ CAPACITY =", read_capacity
		for line in mediuminfo.splitlines():
			if line.find("Free Blocks:") > -1:
				try:
					size = eval(line[14:].replace("KB","*1024"))
				except:
					size = 0
				if size > 0:
					capacity = size / 1048576
					if used:
						used = capacity-used
					print "[dvd+rw-mediainfo] free blocks capacity=%d, used=%d" % (capacity, used)
			elif line.find("Disc status:") > -1:
				if line.find("blank") > -1:
					print "[dvd+rw-mediainfo] Disc status blank capacity=%d, used=0" % (capacity)
					capacity = used
					used = 0
				elif line.find("complete") > -1 and formatted_capacity == 0:
					print "[dvd+rw-mediainfo] Disc status complete capacity=0, used=%d" % (capacity)
					used = read_capacity
					capacity = 1
				else:
					capacity = formatted_capacity
			infotext += line+'\n'
		if capacity and used > capacity:
			used = read_capacity or capacity
			capacity = formatted_capacity or capacity
		self["details"].setText(infotext)
		if self.formattable:
			self["key_yellow"].text = _("Format")
		else:
			self["key_yellow"].text = ""
		percent = 100 * used / (capacity or 1)
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

	def exit(self):
		del self.Console
		hotplugNotifier.remove(self.update)
		self.close()

class DVDformatJob(Job):
	def __init__(self, toolbox):
		Job.__init__(self, _("DVD media toolbox"))
		self.toolbox = toolbox
		DVDformatTask(self)

	def retry(self):
		self.tasks[0].args += self.tasks[0].retryargs
		Job.retry(self)

class DVDformatTaskPostcondition(Condition):
	RECOVERABLE = True
	def check(self, task):
		return task.error is None

	def getErrorMessage(self, task):
		return {
			task.ERROR_ALREADYFORMATTED: _("This DVD RW medium is already formatted - reformatting will erase all content on the disc."),
			task.ERROR_NOTWRITEABLE: _("Medium is not a writeable DVD!"),
			task.ERROR_UNKNOWN: _("An unknown error occurred!")
		}[task.error]

class DVDformatTask(Task):
	ERROR_ALREADYFORMATTED, ERROR_NOTWRITEABLE, ERROR_UNKNOWN = range(3)
	def __init__(self, job, extra_args=[]):
		Task.__init__(self, job, ("RW medium format"))
		self.toolbox = job.toolbox
		self.postconditions.append(DVDformatTaskPostcondition())
		self.setTool("dvd+rw-format")
		self.args += [ "/dev/" + harddiskmanager.getCD() ]
		self.end = 1100
		self.retryargs = [ ]

	def prepare(self):
		self.error = None

	def processOutputLine(self, line):
		if line.startswith("- media is already formatted"):
			self.error = self.ERROR_ALREADYFORMATTED
			self.retryargs = [ "-force" ]
		if line.startswith("- media is not blank") or line.startswith("  -format=full  to perform full (lengthy) reformat;"):
			self.error = self.ERROR_ALREADYFORMATTED
			self.retryargs = [ "-blank" ]
		if line.startswith(":-( mounted media doesn't appear to be"):
			self.error = self.ERROR_NOTWRITEABLE

	def processOutput(self, data):
		print "[DVDformatTask processOutput]  ", data
		if data.endswith('%'):
			data= data.replace('\x08','')
			self.progress = int(float(data[:-1])*10)
		else:
			Task.processOutput(self, data)

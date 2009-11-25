import DVDProject, TitleList, TitleCutter, TitleProperties, ProjectSettings, DVDToolbox, Process
from Screens.Screen import Screen
from Screens.ChoiceBox import ChoiceBox
from Screens.InputBox import InputBox
from Screens.MessageBox import MessageBox
from Screens.HelpMenu import HelpableScreen
from Screens.TaskView import JobView
from Components.Task import job_manager
from Components.ActionMap import HelpableActionMap, ActionMap
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Components.Sources.Progress import Progress
from Components.MultiContent import MultiContentEntryText
from enigma import gFont, RT_HALIGN_LEFT, RT_HALIGN_RIGHT
from Tools.Directories import resolveFilename, SCOPE_PLUGINS

class TitleList(Screen, HelpableScreen):
	skin = """
		<screen name="TitleList" position="center,center" size="560,445" title="DVD Tool" >
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
			<widget source="key_blue" render="Label" position="420,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" />
			<widget source="title_label" render="Label" position="10,48" size="540,38" font="Regular;18" transparent="1" />
			<widget source="error_label" render="Label" position="10,48" size="540,395" zPosition="3" font="Regular;20" transparent="1" />
			<widget source="titles" render="Listbox" scrollbarMode="showOnDemand" position="10,86" size="540,312" zPosition="3" transparent="1" >
				<convert type="TemplatedMultiContent">
					{"template": [
							MultiContentEntryText(pos = (0, 0), size = (420, 20), font = 0, flags = RT_HALIGN_LEFT, text = 1), # index 1 Title,
							MultiContentEntryText(pos = (0, 20), size = (328, 17), font = 1, flags = RT_HALIGN_LEFT, text = 2), # index 2 description,
							MultiContentEntryText(pos = (420, 6), size = (120, 20), font = 1, flags = RT_HALIGN_RIGHT, text = 3), # index 3 begin time,
							MultiContentEntryText(pos = (328, 20), size = (154, 17), font = 1, flags = RT_HALIGN_RIGHT, text = 4), # index 4 channel,
						],
					"fonts": [gFont("Regular", 20), gFont("Regular", 14)],
					"itemHeight": 37
					}
				</convert>
			</widget>
			<widget source="space_bar" render="Progress" position="10,410" size="540,26" borderWidth="1" backgroundColor="#254f7497" />
			<widget source="space_label" render="Label" position="40,414" size="480,22" zPosition="2" font="Regular;18" halign="center" transparent="1" foregroundColor="#000000" />
		</screen>"""

	def __init__(self, session, project = None):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		
		self["titleactions"] = HelpableActionMap(self, "DVDTitleList",
			{
				"addTitle": (self.addTitle, _("Add a new title"), _("Add title")),
				"titleProperties": (self.titleProperties, _("Properties of current title"), _("Title properties")),
				"removeCurrentTitle": (self.removeCurrentTitle, _("Remove currently selected title"), _("Remove title")),
				"settings": (self.settings, _("Collection settings"), _("Settings")),
				"burnProject": (self.askBurnProject, _("Burn DVD"), _("Burn DVD")),
			})

		self["MovieSelectionActions"] = HelpableActionMap(self, "MovieSelectionActions",
			{
				"contextMenu": (self.showMenu, _("menu")),
			})

		self["actions"] = ActionMap(["OkCancelActions"],
			{
				"cancel": self.leave
			})

		self["key_red"] = StaticText()
		self["key_green"] = StaticText(_("Add title"))
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText(_("Settings"))

		self["title_label"] = StaticText()
		self["error_label"] = StaticText()
		self["space_label"] = StaticText()
		self["space_bar"] = Progress()

		if project is not None:
			self.project = project
		else:
			self.newProject()

		self["titles"] = List([])
		self.updateTitleList()
		self.previous_size = 0
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(_("DVD Titlelist"))

	def checkBackgroundJobs(self):
		for job in job_manager.getPendingJobs():
			print "type(job):", type(job)
			print "Process.DVDJob:", Process.DVDJob
			if type(job) == Process.DVDJob:
				self.backgroundJob = job
				return
		self.backgroundJob = None

	def showMenu(self):
		menu = []
		self.checkBackgroundJobs()
		if self.backgroundJob:
			j = self.backgroundJob
			menu.append(("%s: %s (%d%%)" % (j.getStatustext(), j.name, int(100*j.progress/float(j.end))), self.showBackgroundJob))
		menu.append((_("DVD media toolbox"), self.toolbox))
		menu.append((_("Preview menu"), self.previewMenu))
		if self.project.settings.output.getValue() == "dvd":
			if len(self["titles"].list):
				menu.append((_("Burn DVD"), self.burnProject))
		elif self.project.settings.output.getValue() == "iso":
			menu.append((_("Create DVD-ISO"), self.burnProject))
		menu.append((_("Burn existing image to DVD"), self.selectImage))
		menu.append((_("Edit chapters of current title"), self.editTitle))
		menu.append((_("Reset and renumerate title names"), self.resetTitles))
		menu.append((_("Exit"), self.leave))
		self.session.openWithCallback(self.menuCallback, ChoiceBox, title="", list=menu)

	def menuCallback(self, choice):
		if choice:
			choice[1]()

	def showBackgroundJob(self):
		job_manager.in_background = False
		self.session.openWithCallback(self.JobViewCB, JobView, self.backgroundJob)
		self.backgroundJob = None
	
	def titleProperties(self):
		if self.getCurrentTitle():
			self.session.openWithCallback(self.updateTitleList, TitleProperties.TitleProperties, self, self.project, self["titles"].getIndex())

	def selectImage(self):
		self.session.openWithCallback(self.burnISO, ProjectSettings.FileBrowser, "image", self.project.settings)

	def newProject(self):
		self.project = DVDProject.DVDProject()
		if self.loadTemplate():
			self.project.session = self.session
			self.settingsCB()

	def addTitle(self):
		from Screens.MovieSelection import MovieSelection
		from Components.ActionMap import HelpableActionMap
		class DVDMovieSelection(MovieSelection):
			skin = """<screen name="DVDMovieSelection" position="center,center" size="560,445" title="Select a movie">
				<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
				<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
				<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
				<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
				<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
				<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
				<widget name="waitingtext" position="0,45" size="560,395" zPosition="4" font="Regular;22" halign="center" valign="center" />
				<widget name="list" position="5,40" size="550,375" zPosition="2" scrollbarMode="showOnDemand" />
				<widget name="DescriptionBorder" pixmap="skin_default/border_eventinfo.png" position="0,316" zPosition="1" size="560,103" transparent="1" alphatest="on" />
				<widget source="Service" render="Label" position="5,318" zPosition="1" size="480,35" font="Regular;17" foregroundColor="#cccccc">
					<convert type="MovieInfo">ShortDescription</convert>
				</widget>
				<widget source="Service" render="Label" position="495,318" zPosition="1" size="60,22" font="Regular;17" halign="right">
					<convert type="ServiceTime">Duration</convert>
					<convert type="ClockToText">AsLength</convert>
				</widget>
				<widget source="Service" render="Label" position="380,337" zPosition="2" size="175,22" font="Regular;17" halign="right">
					<convert type="MovieInfo">RecordServiceName</convert>
				</widget>
				<widget source="Service" render="Label" position="5,357" zPosition="1" size="550,58" font="Regular;19">
					<convert type="EventName">ExtendedDescription</convert>
				</widget>
				<widget name="freeDiskSpace" position="10,425" size="540,20" font="Regular;19" valign="center" halign="right" />
			</screen>"""
			def __init__(self, session):
				MovieSelection.__init__(self, session)
				self["key_red"] = StaticText(_("Close"))
				self["key_green"] = StaticText(_("Add"))
				self["key_yellow"] = StaticText(_("Edit title"))
				self["ColorActions"] = HelpableActionMap(self, "ColorActions",
				{
					"red": (self.close, _("Close title selection")),
					"green": (self.insertWithoutEdit, ("insert without cutlist editor")),
					"yellow": (self.movieSelected, _("Add a new title"))
				})
			def updateTags(self):
				pass
			def doContext(self):
				print "context menu forbidden inside DVDBurn to prevent calling multiple instances"
			def insertWithoutEdit(self):
				current = self.getCurrent()
				if current is not None:
					current.edit = False
					self.close(current)
			def movieSelected(self):
				current = self.getCurrent()
				if current is not None:
					current.edit = True
					self.close(current)
		self.session.openWithCallback(self.selectedSource, DVDMovieSelection)

	def selectedSource(self, source):
		if source is None:
			return None
		t = self.project.addService(source)
		try:
			editor = source.edit
		except AttributeError:
			editor = True
		self.editTitle(t, editor)

	def removeCurrentTitle(self):
		title = self.getCurrentTitle()
		self.removeTitle(title)
	
	def removeTitle(self, title):
		if title is not None:
			self.project.titles.remove(title)
			self.updateTitleList()

	def toolbox(self):
		self.session.open(DVDToolbox.DVDToolbox)

	def settings(self):
		self.session.openWithCallback(self.settingsCB, ProjectSettings.ProjectSettings, self.project)

	def settingsCB(self, update=True):
		if not update:
			return
		self["title_label"].text = _("Table of content for collection") + " \"" + self.project.settings.name.getValue() + "\":"

	def loadTemplate(self):
		filename = resolveFilename(SCOPE_PLUGINS)+"Extensions/DVDBurn/DreamboxDVD.ddvdp.xml"
		if self.project.load(filename):
			self["error_label"].setText("")
			return True
		else:
			self["error_label"].setText(self.project.error)
			return False

	def askBurnProject(self):
		if len(self["titles"].list):
			self.session.openWithCallback(self.burnProject,MessageBox,text = _("Do you want to burn this collection to DVD medium?"), type = MessageBox.TYPE_YESNO)

	def burnProject(self, answer=True):
		if not answer:
			return
		if self.project.settings.authormode.getValue() == "data_ts":
			job = Process.DVDdataJob(self.project)
			job_manager.AddJob(job)
			job_manager.in_background = False
			self.session.openWithCallback(self.JobViewCB, JobView, job)
		else:
			job = Process.DVDJob(self.project)
			job_manager.AddJob(job)
			job_manager.in_background = False
			self.session.openWithCallback(self.JobViewCB, JobView, job)

	def burnISO(self, path, scope, configRef):
		if path:
			job = Process.DVDisoJob(self.project, path)
			job_manager.AddJob(job)
			job_manager.in_background = False
			self.session.openWithCallback(self.JobViewCB, JobView, job)

	def JobViewCB(self, in_background):
		job_manager.in_background = in_background

	def previewMenu(self):
		job = Process.DVDJob(self.project, menupreview=True)
		job_manager.in_background = False
		job_manager.AddJob(job)

	def updateTitleList(self):
		list = [ ]
		for title in self.project.titles:
			list.append((title, title.properties.menutitle.getValue(), title.properties.menusubtitle.getValue(), title.DVBchannel, title.formatDVDmenuText("$D.$M.$Y, $T", 0)))
		self["titles"].list = list
		self.updateSize()
		if len(list):
			self["key_red"].text = _("Remove title")
			self["key_yellow"].text = _("Title properties")
		else:
			self["key_red"].text = ""
			self["key_yellow"].text = ""

	def updateSize(self):
		size = self.project.size/(1024*1024)
		MAX_DL = self.project.MAX_DL-100
		MAX_SL = self.project.MAX_SL-100
		print "updateSize:", size, "MAX_DL:", MAX_DL, "MAX_SL:", MAX_SL
		if size > MAX_DL:
			percent = 100 * size / float(MAX_DL)
			self["space_label"].text = "%d MB - " % size + _("exceeds dual layer medium!") + " (%.2f%% " % (100-percent) + _("free") + ")"
			self["space_bar"].value = int(percent)
			if self.previous_size < MAX_DL:
				self.session.open(MessageBox,text = _("exceeds dual layer medium!"), type = MessageBox.TYPE_ERROR)
		elif size > MAX_SL:
			percent = 100 * size / float(MAX_DL)
			self["space_label"].text = "%d MB  " % size + _("of a DUAL layer medium used.") + " (%.2f%% " % (100-percent) + _("free") + ")"
			self["space_bar"].value = int(percent)
			if self.previous_size < MAX_SL:
				self.session.open(MessageBox,text = _("Your collection exceeds the size of a single layer medium, you will need a blank dual layer DVD!"), type = MessageBox.TYPE_INFO)
		elif size < MAX_SL:
			percent = 100 * size / float(MAX_SL)
			self["space_label"].text = "%d MB " % size + _("of a SINGLE layer medium used.") + " (%.2f%% " % (100-percent) + _("free") + ")"
			self["space_bar"].value = int(percent)
		self.previous_size = size

	def getCurrentTitle(self):
		t = self["titles"].getCurrent()
		return t and t[0]

	def editTitle(self, title = None, editor = True):
		t = title or self.getCurrentTitle()
		if t is not None:
			self.current_edit_title = t
			if editor:
				self.session.openWithCallback(self.titleEditDone, TitleCutter.TitleCutter, t)
			else:
				self.session.openWithCallback(self.titleEditDone, TitleCutter.CutlistReader, t)

	def titleEditDone(self, cutlist):
		t = self.current_edit_title
		t.initDVDmenuText(self.project,len(self.project.titles))
		t.cuesheet = cutlist
		t.produceFinalCuesheet()
		if t.VideoType != 0:
			self.session.openWithCallback(self.DVDformatCB,MessageBox,text = _("The DVD standard doesn't support H.264 (HDTV) video streams. Do you want to create a Dreambox format data DVD (which will not play in stand-alone DVD players) instead?"), type = MessageBox.TYPE_YESNO)
		else:
			self.updateTitleList()

	def resetTitles(self):
		count = 0
		for title in self.project.titles:
			count += 1
			title.initDVDmenuText(self.project,count)
		self.updateTitleList()

	def DVDformatCB(self, answer):
		t = self.current_edit_title
		if answer == True:
			self.project.settings.authormode.setValue("data_ts")
			self.updateTitleList()
		else:
			self.removeTitle(t)

	def leave(self):
		self.close()

import Project, TitleCutter, TitleProperties, ProjectSettings, MediumToolbox, Process, Bludisc
from Screens.Screen import Screen
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.HelpMenu import HelpableScreen
from Screens.TaskView import JobView
from Components.Task import job_manager
from Components.ActionMap import HelpableActionMap, ActionMap
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Components.Sources.Progress import Progress
from Components.MultiContent import MultiContentEntryText
from Components.Label import MultiColorLabel
from enigma import gFont, RT_HALIGN_LEFT, RT_HALIGN_RIGHT
from Tools.Directories import resolveFilename, SCOPE_PLUGINS

MODE_DVD, MODE_BLUDISC = range(2)

class TitleList(Screen, HelpableScreen):
	skin = """
		<screen name="TitleList" position="center,center" size="560,470" title="Burn Tool" >
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;19" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;19" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;19" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
			<widget source="key_blue" render="Label" position="420,0" zPosition="1" size="140,40" font="Regular;19" halign="center" valign="center" backgroundColor="#18188b" transparent="1" />
			<widget source="title_label" render="Label" position="10,48" size="540,38" font="Regular;18" transparent="1" />
			<widget source="error_label" render="Label" position="10,48" size="540,296" zPosition="3" font="Regular;20" transparent="1" />
			<widget source="titles" render="Listbox" scrollbarMode="showOnDemand" position="10,86" size="546,296" zPosition="3" transparent="1" >
				<convert type="TemplatedMultiContent">
					{"template": [
							MultiContentEntryText(pos = (0, 0), size = (360, 20), font = 0, flags = RT_HALIGN_LEFT, text = 1), # index 1 Title,
							MultiContentEntryText(pos = (0, 20), size = (360, 17), font = 1, flags = RT_HALIGN_LEFT, text = 2), # index 2 description,
							MultiContentEntryText(pos = (366, 6), size = (152, 20), font = 1, flags = RT_HALIGN_RIGHT, text = 3), # index 3 channel,
							MultiContentEntryText(pos = (366, 20), size = (102, 17), font = 1, flags = RT_HALIGN_RIGHT, text = 4), # index 4 begin time,
							MultiContentEntryText(pos = (470, 20), size = (48, 20), font = 1, flags = RT_HALIGN_RIGHT, text = 5), # index 5 duration,
						],
					"fonts": [gFont("Regular", 20), gFont("Regular", 14)],
					"itemHeight": 37
					}
				</convert>
			</widget>
			<ePixmap pixmap="skin_default/div-h.png" position="0,390" zPosition="10" size="560,2" />
			<ePixmap pixmap="skin_default/buttons/key_menu.png" position="10,392" size="35,25" alphatest="on" />
			<widget source="hint" render="Label" position="50,394" size="540,22" font="Regular;18" halign="left" />
			<widget name="medium_label" position="10,416" size="540,22" font="Regular;18" halign="left" foregroundColors="#FFFFFF,#FFFF00,#FF0000" />
			<widget source="space_bar_single" render="Progress" position="100,436" size="1,24" borderWidth="1" zPosition="3" backgroundColor="#254f7497" />
			<widget source="space_bar_dual" render="Progress" position="190,436" size="1,24" borderWidth="1" zPosition="2" backgroundColor="#254f7497" />
			<widget source="space_bar_bludisc" render="Progress" position="10,436" size="540,24" borderWidth="1" zPosition="1" backgroundColor="#254f7497" />
			<widget source="space_label" render="Label" position="10,439" size="540,22" zPosition="4" font="Regular;18" halign="center" transparent="1" foregroundColor="#000000" />
			<widget source="marker_single" render="Label" position="78,460" size="44,12" zPosition="1" font="Regular;11" halign="center" foregroundColor="#FFFFFF" />
			<widget source="marker_dvd" render="Label" position="123,460" size="44,12" zPosition="1" font="Regular;11" halign="center" foregroundColor="#FFFFFF" />
			<widget source="marker_dual" render="Label" position="168,460" size="44,12" zPosition="1" font="Regular;11" halign="center" foregroundColor="#FFFFFF" />
			<widget source="marker_bludisc" render="Label" position="508,460" size="44,12" zPosition="1" font="Regular;11" halign="right" foregroundColor="#FFFFFF" />
		</screen>"""

	def __init__(self, session, project = None):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		
		self["titleactions"] = HelpableActionMap(self, "TitleList",
			{
				"addTitle": (self.addTitle, _("Add a new title"), _("Add title")),
				"titleProperties": (self.titleProperties, _("Properties of current title"), _("Title properties")),
				"removeCurrentTitle": (self.removeCurrentTitle, _("Remove currently selected title"), _("Remove title")),
				"settings": (self.settings, _("Collection settings"), _("Settings")),
				"burnProject": (self.askBurnProject, _("Burn to medium"), _("Burn to medium")),
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
		self["hint"] = StaticText(_("Advanced Options"))
		self["medium_label"] = MultiColorLabel()
		self["space_bar_single"] = Progress()
		self["space_bar_dual"] = Progress()
		self["space_bar_bludisc"] = Progress()
		self["marker_single"] = StaticText(("SINGLE"))
		self["marker_dvd"] = StaticText(("DVD"))
		self["marker_dual"] = StaticText(("DUAL"))
		self["marker_bludisc"] = StaticText(("BLUDISC"))

		self["titles"] = List([])
		self.previous_size = 0
		if project is not None:
			self.project = project
		else:
			self.newProject()
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
		menu.append((_("Medium toolbox"), self.toolbox))
		if self.project.settings.output.getValue() == "medium":
			if len(self["titles"].list):
				menu.append((_("Burn to medium"), self.burnProject))
		elif self.project.settings.output.getValue() == "iso":
			menu.append((_("Create ISO"), self.burnProject))
		menu.append((_("Burn existing image to medium"), self.selectImage))
		if len(self["titles"].list):
			menu.append((_("Preview menu"), self.previewMenu))
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
		#if self.getCurrentTitle():
			self.session.openWithCallback(self.updateTitleList, TitleProperties.TitleProperties, self, self.project, self["titles"].getIndex())

	def selectImage(self):
		self.session.openWithCallback(self.burnISO, ProjectSettings.FileBrowser, "image", self.project.settings)

	def newProject(self):
		self.project = Project.Project()
		if self.loadTemplate():
			self.project.session = self.session
			self.settingsCB()

	def addTitle(self):
		from Screens.MovieSelection import MovieSelection
		from Components.ActionMap import HelpableActionMap
		from Components.Button import Button
		class DVDMovieSelection(MovieSelection):
			def __init__(self, session):
				MovieSelection.__init__(self, session)
				self.skinName = ["MovieSelection"]
				self["key_red"] = Button(_("Close"))
				self["key_green"] = Button(_("Add"))
				self["key_yellow"] = Button(_("Edit title"))
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

	def selectedSource(self, source = None):
		if source is None:
			return None
		if not source.getPath().endswith(".ts"):
			self.session.open(MessageBox,text = _("You can only burn Dreambox recordings!"), type = MessageBox.TYPE_ERROR)
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
		self.session.open(MediumToolbox.MediumToolbox)

	def settings(self):
		self.session.openWithCallback(self.settingsCB, ProjectSettings.ProjectSettings, self.project)

	def settingsCB(self, update=True):
		if not update:
			return
		self.updateTitleList()

	def loadTemplate(self, mode=MODE_DVD):
		if mode == MODE_BLUDISC:
			filename = resolveFilename(SCOPE_PLUGINS)+"Extensions/DVDBurn/DreamboxBludisc.ddvdp.xml"
		else:
			filename = resolveFilename(SCOPE_PLUGINS)+"Extensions/DVDBurn/DreamboxDVD.ddvdp.xml"
		if self.project.load(filename):
			self["error_label"].setText("")
			return True
		else:
			self["error_label"].setText(self.project.error)
			return False

	def askBurnProject(self):
		if len(self["titles"].list):
			self.session.openWithCallback(self.burnProject,MessageBox,text = _("Do you want to produce this collection?"), type = MessageBox.TYPE_YESNO)

	def burnProject(self, answer=True):
		if not answer:
			return
		if self.project.settings.authormode.value == "data_ts":
			job = Process.DVDdataJob(self.project)
			job_manager.AddJob(job)
			job_manager.in_background = False
			self.session.openWithCallback(self.JobViewCB, JobView, job)
		elif self.project.settings.authormode.value == "bdmv":
			job = Bludisc.BDMVJob(self.project)
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
			list.append((title, title.properties.menutitle.getValue(), title.properties.menusubtitle.getValue(), title.DVBchannel, title.formatDVDmenuText("$D.$M.$Y, $T", 0), title.formatDVDmenuText("$l", 0)))
		self["titles"].list = list
		self.updateSize()
		if len(list):
			self["key_red"].text = _("Remove title")
			self["key_yellow"].text = _("Title properties")
			self["title_label"].text = _("Table of content for collection") + " \"" + self.project.settings.name.getValue() + "\":"
		else:
			self["key_red"].text = ""
			self["key_yellow"].text = ""
			self["title_label"].text = _("Please add titles to the compilation.")
		self.project.finished_burning = False

	def updateSize(self):
		size = self.project.size/(1024*1024)
		MAX_DL = self.project.MAX_DL-100
		MAX_SL = self.project.MAX_SL-100
		MAX_BD = self.project.MAX_BD-200
		self["space_bar_bludisc"].value = 100 * size / (MAX_BD)

		if self.project.settings.authormode.value == "bdmv":
			percent = 100 * size / float(MAX_BD)
			self["space_label"].text = "%d MB (%.2f%%)" % (size, percent)
			
			if size > MAX_BD:
				self["medium_label"].setText(_("Exceeds Bludisc medium!"))
				self["medium_label"].setForegroundColorNum(2)
				if self.previous_size < MAX_BD:
					self.session.open(MessageBox,text = _("Exceeds Bludisc medium!"), type = MessageBox.TYPE_ERROR)
			elif size < MAX_BD:
				self["medium_label"].setText(_("Required medium type:") + " " + _("BLUDISC RECORDABLE") + ", %d MB " % (MAX_BD - size) + _("free"))
				self["medium_label"].setForegroundColorNum(1)
		else:
			if size > MAX_DL:
				percent = 100 * size / float(MAX_DL)
				self["space_label"].text = "%d MB (%.2f%%)" % (size, percent)
				self["medium_label"].setText(_("Exceeds dual layer medium!"))
				self["medium_label"].setForegroundColorNum(2)
				if self.previous_size < MAX_DL:
					self.session.open(MessageBox,text = _("Exceeds dual layer medium!"), type = MessageBox.TYPE_ERROR)
			elif size > MAX_SL:
				percent = 100 * size / float(MAX_DL)
				self["space_label"].text = "%d MB (%.2f%%)" % (size, percent)
				self["medium_label"].setText(_("Required medium type:") + " " + _("DUAL LAYER DVD") + ", %d MB " % (MAX_DL - size) + _("free"))
				self["medium_label"].setForegroundColorNum(1)
				if self.previous_size < MAX_SL:
					self.session.open(MessageBox, text = _("Your collection exceeds the size of a single layer medium, you will need a blank dual layer DVD!"), timeout = 10, type = MessageBox.TYPE_INFO)
			elif size < MAX_SL:
				percent = 100 * size / float(MAX_SL)
				self["space_label"].text = "%d MB (%.2f%%)" % (size, percent)
				self["medium_label"].setText(_("Required medium type:") + " " + _("SINGLE LAYER DVD") + ", %d MB " % (MAX_SL - size) + _("free"))
				self["medium_label"].setForegroundColorNum(0)
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
		t.titleEditDone(cutlist)
		all_hd = True
		all_sd = True
		for title in self.project.titles:
			if title != self.current_edit_title and title.VideoType == 0:
				all_hd = False
			if title != self.current_edit_title and title.VideoType == 1:
				all_sd = False

		choices = []

		if t.VideoType != 0 and self.project.settings.authormode.value not in ("data_ts", "bdmv"):
			text = _("The DVD standard doesn't support H.264 (HDTV) video streams.")
			
			if all_hd == True:
				choices.append((_("BDMV Bludisc (HDTV titles only)"),"bdmv"))
			
			choices.append((_("Dreambox format data DVD (won't work in other DVD players)"),"data_ts"))
			choices.append((_("Don't add this recording"),None))
			self.session.openWithCallback(self.formatCB, ChoiceBox, title=text, list=choices)

		#elif t.VideoType != 1 and self.project.settings.authormode.value == "bdmv":
			#text = _("The Bludisc standard doesn't support MPEG-2 (SDTV) video streams.")

			#if all_sd == True:
				#choices.append((_("Linked titles with a DVD menu"),"menu_linked"))

			#choices.append((_("Dreambox format data DVD (won't work in other DVD players)"),"data_ts"))
			#choices.append((_("Don't add this recording"),None))
			#self.session.openWithCallback(self.formatCB, ChoiceBox, title=text, list=choices)

		else:
			self.updateTitleList()

	def formatCB(self, answer):
		t = self.current_edit_title
		if isinstance(answer, tuple) and answer[1]:
			if answer[1] in ("menu_linked", "data_ts"):
				self.loadTemplate(MODE_DVD)
			if answer[1] == "bdmv":
				self.loadTemplate(MODE_BLUDISC)
			self.project.settings.authormode.setValue(answer[1])
			self.updateTitleList()
		else:
			self.removeTitle(t)

	def resetTitles(self):
		count = 0
		for title in self.project.titles:
			count += 1
			title.initDVDmenuText(count)
		self.updateTitleList()

	def leave(self, close = False):
		if not len(self["titles"].list) or close or self.project.finished_burning:
			self.close()
		else:
			self.session.openWithCallback(self.exitCB, MessageBox,text = _("Your current collection will get lost!") + "\n" + _("Do you really want to exit?"), type = MessageBox.TYPE_YESNO)

	def exitCB(self, answer):
		print "exitCB", answer
		if answer is not None and answer:
			self.close()

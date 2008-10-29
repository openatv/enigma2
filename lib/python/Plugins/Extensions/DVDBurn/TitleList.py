import DVDProject, TitleList, TitleCutter, ProjectSettings, DVDToolbox, Process
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
from Components.Label import Label
from enigma import eListboxPythonMultiContent, gFont, RT_HALIGN_LEFT
from Tools.Directories import resolveFilename, SCOPE_PLUGINS

class TitleList(Screen, HelpableScreen):
	skin = """
		<screen position="90,83" size="560,445" title="DVD Tool" >
		    <ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
		    <ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
		    <ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
		    <ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" alphatest="on" />
		    <widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		    <widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		    <widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
		    <widget source="key_blue" render="Label" position="420,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" />
		    <widget source="title_label" render="Label" position="10,48" size="540,38" font="Regular;18" />
		    <widget name="error_label" position="10,48" size="540,395" zPosition="3" font="Regular;20" />
		    <widget source="titles" render="Listbox" scrollbarMode="showOnDemand" position="10,86" size="540,312">
			<convert type="StaticMultiList" />
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
				"editTitle": (self.editTitle, _("Edit chapters of current title"), _("Edit title")),
				"removeCurrentTitle": (self.removeCurrentTitle, _("Remove currently selected title"), _("Remove title")),
				"settings": (self.settings, _("Collection settings"), _("Settings")),
				"burnProject": (self.burnProject, _("Burn DVD"), _("Burn DVD")),
			})

		self["MovieSelectionActions"] = HelpableActionMap(self, "MovieSelectionActions",
			{
				"contextMenu": (self.showMenu, _("menu")),
			})

		self["actions"] = ActionMap(["OkCancelActions"],
			{
				"cancel": self.leave
			})

		self["key_red"] = StaticText(_("Remove title"))
		self["key_green"] = StaticText(_("Add title"))
		self["key_yellow"] = StaticText(_("Edit title"))
		self["key_blue"] = StaticText(_("Settings"))

		self["title_label"] = StaticText()
		self["error_label"] = Label("")
		self["space_label"] = StaticText()
		self["space_bar"] = Progress()

		if project is not None:
			self.project = project
		else:
			self.newProject()

		self["titles"] = List(list = [ ], enableWrapAround = True, item_height=30, fonts = [gFont("Regular", 20)])
		self.updateTitleList()
		
	def showMenu(self):
		menu = []
		if self.project.settings.output.getValue() == "dvd":
			menu.append((_("Burn DVD"), "burn"));
		elif self.project.settings.output.getValue() == "iso":
			menu.append((_("Create DVD-ISO"), "burn"));
		menu.append((_("Preview menu"), "previewMenu"));
		menu.append((_("DVD media toolbox"), "toolbox"));
		menu.append((_("Collection settings"), "settings"));
		menu.append((_("Add a new title"), "addtitle"));
		menu.append((_("Remove title"), "removetitle"));
		menu.append((_("Edit chapters of current title"), "edittitle"));
		menu.append((_("Burn existing image to DVD"), "burniso"));
		menu.append((_("Exit"), "exit"));
		self.session.openWithCallback(self.menuCallback, ChoiceBox, title="", list=menu)

	def menuCallback(self, choice):
		if choice is None:
			return
		if choice[1] == "removetitle":
			self.removeCurrentTitle()
		elif choice[1] == "addtitle":
			self.addTitle()
		elif choice[1] == "edittitle":
			self.editTitle()
		elif choice[1] == "toolbox":
			self.toolbox()
		elif choice[1] == "settings":
			self.settings()
		elif choice[1] == "previewMenu":
			self.previewMenu()
		elif choice[1] == "burn":
			self.burnProject()
		elif choice[1] == "burniso":
			self.session.openWithCallback(self.burnISO, ProjectSettings.FileBrowser, "image", self.project.settings)
		elif choice[1] == "exit":
			self.leave()

	def newProject(self):
		self.project = DVDProject.DVDProject()
		if self.loadTemplate():
			self.project.session = self.session
			self.settingsCB()

	def addTitle(self):
		from Screens.MovieSelection import MovieSelection
		from Components.Button import Button
		from Components.ActionMap import HelpableActionMap
		class MovieSelectionNoMenu(MovieSelection):
			def __init__(self, session):
				MovieSelection.__init__(self, session)
				self.skinName = "MovieSelection"
				self["key_red"] = Button(_("Edit title"))
				self["key_green"] = Button(_("Add"))
				self["ColorActions"] = HelpableActionMap(self, "ColorActions",
				{
					"red": (self.movieSelected, _("Add a new title")),
					"green": (self.insertWithoutEdit, ("insert without cutlist editor"))
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
		self.session.openWithCallback(self.selectedSource, MovieSelectionNoMenu)

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
		filename = resolveFilename(SCOPE_PLUGINS)+"Extensions/DVDBurn/DreamboxDVDtemplate.ddvdp.xml"
		if self.project.loadProject(filename):
			self["error_label"].hide()
			return True
		else:
			self["error_label"].text = self.project.error
			self["error_label"].show()
			return False

	def burnProject(self):
		if self.project.settings.authormode.getValue() == "data_ts":
			job = Process.DVDdataJob(self.project)
			job_manager.AddJob(job)
			job_manager.in_background = False
			self.session.openWithCallback(self.JobViewCB, JobView, job)
		else:
			autochapter = self.project.settings.autochapter.getValue()
			if autochapter > 0:
				for title in self.project.titles:
					title.produceAutoChapter(autochapter)
			job = Process.DVDJob(self.project)
			job_manager.AddJob(job)
			job_manager.in_background = False
			self.session.openWithCallback(self.JobViewCB, JobView, job)

	def burnISO(self, path, scope):
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
		res = [ ]
		totalsize = 0
		for title in self.project.titles:
			a = [ title, (eListboxPythonMultiContent.TYPE_TEXT, 0, 10, 500, 50, 0, RT_HALIGN_LEFT, title.name)  ]
			res.append(a)
			totalsize += title.estimatedDiskspace
		self["titles"].list = res
		self.updateSize(totalsize)
		
	def updateSize(self, totalsize):
		size = int((totalsize/1024)/1024)
		max_SL = 4370
		max_DL = 7950
		if size > max_DL:
			percent = 100 * size / float(max_DL)
			self["space_label"].text = "%d MB - " % size + _("exceeds dual layer medium!") + " (%.2f%% " % (100-percent) + _("free") + ")"
			self["space_bar"].value = int(percent)
		elif size > max_SL:
			percent = 100 * size / float(max_DL)
			self["space_label"].text = "%d MB  " % size + _("of a DUAL layer medium used.") + " (%.2f%% " % (100-percent) + _("free") + ")"
			self["space_bar"].value = int(percent)
		elif size < max_SL:
			percent = 100 * size / float(max_SL)
			self["space_label"].text = "%d MB " % size + _("of a SINGLE layer medium used.") + " (%.2f%% " % (100-percent) + _("free") + ")"
			self["space_bar"].value = int(percent)

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
		t.cuesheet = cutlist
		t.produceFinalCuesheet()
		if t.sVideoType != 0:
			self.session.openWithCallback(self.DVDformatCB,MessageBox,text = _("The DVD standard doesn't support H.264 (HDTV) video streams. Do you want to create a Dreambox format data DVD (which will not play in stand-alone DVD players) instead?"), type = MessageBox.TYPE_YESNO)
		else:
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

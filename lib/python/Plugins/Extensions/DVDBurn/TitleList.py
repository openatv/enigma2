import DVDProject, DVDTitle, TitleList, TitleCutter

from Screens.Screen import Screen
from Components.ActionMap import HelpableActionMap, ActionMap
from Components.Sources.List import List
from enigma import eListboxPythonMultiContent, gFont, RT_HALIGN_LEFT

class TitleList(Screen):

	skin = """
		<screen position="100,100" size="550,400" title="DVD Tool" >
			<widget source="titles" render="Listbox" scrollbarMode="showOnDemand" position="0,0" size="400,400">
				<convert type="StaticMultiList" />
			</widget>
		</screen>"""

	def __init__(self, session, project = None):
		Screen.__init__(self, session)

		if project is not None:
			self.project = project
		else:
			self.newProject()

		self["titleactions"] = HelpableActionMap(self, "DVDTitleList",
			{
				"addTitle": (self.addTitle, _("Add a new title"), _("Add title...")),
				"editTitle": (self.editTitle, _("Edit current title"), _("Edit title...")),
				"removeCurrentTitle": (self.removeCurrentTitle, _("Remove currently selected title"), _("Remove title")),
				"saveProject": (self.saveProject, _("Save current project to disk"), _("Save...")),
				"burnProject": (self.burnProject, _("Burn DVD"), _("Burn")),
			})

		self["actions"] = ActionMap(["OkCancelActions"],
			{
				"cancel": self.leave
			})

		#Action("addTitle", self.addTitle)

		self["titles"] = List(list = [ ], enableWrapAround = True, item_height=50, fonts = [gFont("Regular", 20)])
		self.updateTitleList()

		#self["addTitle"] = ActionButton("titleactions", "addTitle")
		#self["editTitle"] = ActionButton("titleactions", "editTitle")
		#self["removeCurrentTitle"] = ActionButton("titleactions", "removeCurrentTitle")
		#self["saveProject"] = ActionButton("titleactions", "saveProject")
		#self["burnProject"] = ActionButton("titleactions", "burnProject")

	def newProject(self):
		self.project = DVDProject.DVDProject()
		self.project.titles = [ ]

	def addTitle(self):
		from Screens.MovieSelection import MovieSelection
		self.session.openWithCallback(self.selectedSource, MovieSelection)

	def selectedSource(self, source):
		if source is None:
			return None
		t = self.project.addService(source)
		self.updateTitleList()

		self.editTitle(t)

	def removeCurrentTitle(self):
		title = self.getCurrentTitle()
		if title is not None:
			self.project.titles.remove(title)
			self.updateTitleList()

	def saveProject(self):
		pass

	def burnProject(self):
		print "producing final cue sheet:"
		cue = self.produceFinalCuesheet()
		import Process
		job = Process.Burn(self.session, cue)
		print cue
		from Screens.TaskView import JobView
		self.session.open(JobView, job)

	def updateTitleList(self):
		res = [ ]
		for title in self.project.titles:
			a = [ title, (eListboxPythonMultiContent.TYPE_TEXT, 0, 10, 400, 50, 0, RT_HALIGN_LEFT, title.name)  ]
			res.append(a)

		self["titles"].list = res

	def getCurrentTitle(self):
		t = self["titles"].getCurrent()
		return t and t[0]

	def editTitle(self, title = None):
		t = title or self.getCurrentTitle()
		if t is not None:
			self.current_edit_title = t
			self.session.openWithCallback(self.titleEditDone, TitleCutter.TitleCutter, t)

	def titleEditDone(self, cutlist):
		t = self.current_edit_title
		t.cutlist = cutlist
		print "title edit of %s done, resulting cutlist:" % (t.source.toString()), t.cutlist

	def leave(self):
		self.close()

	def produceFinalCuesheet(self):
		res = [ ]
		for title in self.project.titles:
			path = title.source.getPath()
			print ">>> path:", path
			cutlist = title.cutlist

			# our demuxer expects *stricly* IN,OUT lists.
			first = True
			currently_in = False
			CUT_TYPE_IN = 0
			CUT_TYPE_OUT = 1
			CUT_TYPE_MARK = 2
			CUT_TYPE_LAST = 3

			accumulated_in = 0
			accumulated_at = 0
			last_in = 0

			res_cutlist = [ ]

			res_chaptermarks = [0]

			for (pts, type) in cutlist:
				if first and type == CUT_TYPE_OUT: # first mark is "out"
					res_cutlist.append(0) # emulate "in" at first
					currently_in = True

				first = False

				if type == CUT_TYPE_IN and not currently_in:
					res_cutlist.append(pts)
					last_in = pts
					currently_in = True

				if type == CUT_TYPE_OUT and currently_in:
					res_cutlist.append(pts)

					# accumulate the segment
					accumulated_in += pts - last_in 
					accumulated_at = pts
					currently_in = False

				if type == CUT_TYPE_MARK and currently_in:
					# relocate chaptermark against "in" time. This is not 100% accurate,
					# as the in/out points are not.
					res_chaptermarks.append(pts - accumulated_at + accumulated_in)

			res.append( (path, res_cutlist, res_chaptermarks) )

		return res

from enigma import *
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Sources.List import List
from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN,  SCOPE_PLUGINS
from Tools.LoadPixmap import LoadPixmap
from Components.Label import Label

def MessageBoxEntry(name, picture):
	pixmap = LoadPixmap(cached = True, path = resolveFilename(SCOPE_PLUGINS, "Extensions/Infopanel/icons/" + picture));
	if not pixmap:
		pixmap = LoadPixmap(cached = True, path = resolveFilename(SCOPE_PLUGINS, "Extensions/Infopanel/icons/empty.png"));
		
	return (pixmap, name)
	
class ExtraMessageBox(Screen):
	skin = """
	<screen position="center,center" size="560,120" title=" ">
		<widget font="Regular;20" halign="center" name="message" position="50,10" size="490,48" valign="center"/>
		<widget source="menu" render="Listbox" position="10,60" size="560,50" font="Regular;16" scrollbarMode="showOnDemand" >
			<convert type="TemplatedMultiContent">
				{"template": [
				MultiContentEntryPixmapAlphaBlend(pos = (0, 0), size = (80, 80), png = 0),
				MultiContentEntryText(pos = (80, 0), size = (600, 50), font=0, text = 1),
				],
				"fonts": [gFont("Regular", 24),gFont("Regular", 18)],
				"itemHeight": 50
				}
			</convert>
		</widget>
	</screen>"""
	def __init__(self, session, message = "", title = "", menulist = [], type = 0, exitid = -1, default = 0, timeout = 0):
		# type exist for compability... will be ignored
		Screen.__init__(self, session)
		self.session = session
		self.ctitle = title
		self.exitid = exitid
		self.default = default
		self.timeout = timeout
		self.elapsed = 0
		
		self.list = []
		for item in menulist:
			self.list.append(MessageBoxEntry(item[0], item[1]))
		
		self['menu'] = List(self.list)
		self["menu"].onSelectionChanged.append(self.selectionChanged)

		self["message"] = Label(message)
		self["actions"] = ActionMap(["SetupActions"],
		{
			"ok": self.ok,
			"cancel": self.cancel
		}, -2)
		
		self.onLayoutFinish.append(self.layoutFinished)
		
		self.timer = eTimer()
		self.timer.callback.append(self.timeoutStep)
		if self.timeout > 0:
			self.timer.start(1000, 1)

	def selectionChanged(self):
		self.timer.stop()
		self.setTitle(self.ctitle)

	def timeoutStep(self):
		self.elapsed += 1
		if self.elapsed == self.timeout:
			self.ok()
		else:
			self.setTitle("%s - %d" % (self.ctitle, self.timeout - self.elapsed))
			self.timer.start(1000, 1)

	def layoutFinished(self):
		if self.timeout > 0:
			self.setTitle("%s - %d" % (self.ctitle, self.timeout))
		else:
			self.setTitle(self.ctitle)
		self['menu'].setCurrentIndex(self.default)
		
	def ok(self):
		index = self['menu'].getIndex()
		self.close(index)
		
	def cancel(self):
		if self.exitid > -1:
			self.close(self.exitid)

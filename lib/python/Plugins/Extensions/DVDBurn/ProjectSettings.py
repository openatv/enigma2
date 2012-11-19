from Screens.Screen import Screen
from Screens.ChoiceBox import ChoiceBox
from Screens.InputBox import InputBox
from Screens.MessageBox import MessageBox
from Screens.HelpMenu import HelpableScreen
from Components.ActionMap import HelpableActionMap, ActionMap
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Components.Sources.Progress import Progress
from Components.FileList import FileList
from Tools.Directories import fileExists, resolveFilename, SCOPE_PLUGINS, SCOPE_FONTS, SCOPE_HDD
from Components.config import config, getConfigListEntry
from Components.ConfigList import ConfigListScreen

class FileBrowser(Screen, HelpableScreen):

	def __init__(self, session, scope, configRef):
		Screen.__init__(self, session)
		# for the skin: first try FileBrowser_DVDBurn, then FileBrowser, this allows individual skinning
		self.skinName = ["FileBrowser_DVDBurn", "FileBrowser" ]

		HelpableScreen.__init__(self)
		self.scope = scope
		pattern = ""
		self.configRef = configRef
		currDir = "/"
		if self.scope == "project":
			currDir = self.getDir()
			pattern = "(?i)^.*\.(ddvdp\.xml)"
		elif self.scope == "menutemplate":
			currDir = self.getDir()
			pattern = "(?i)^.*\.(ddvdm\.xml)"
		if self.scope == "menubg":
			currDir = self.getDir(configRef.getValue())
			pattern = "(?i)^.*\.(jpeg|jpg|jpe|png|bmp)"
		elif self.scope == "menuaudio":
			currDir = self.getDir(configRef.getValue())
			pattern = "(?i)^.*\.(mp2|m2a|ac3)"
		elif self.scope == "vmgm":
			currDir = self.getDir(configRef.getValue())
			pattern = "(?i)^.*\.(mpg|mpeg)"
		elif self.scope == "font_face":
			currDir = self.getDir(configRef.getValue(), resolveFilename(SCOPE_FONTS))
			pattern = "(?i)^.*\.(ttf)"
		elif self.scope == "isopath":
			currDir = configRef.getValue()
		elif self.scope == "image":
			currDir = resolveFilename(SCOPE_HDD)
			pattern = "(?i)^.*\.(iso)"

		self.filelist = FileList(currDir, matchingPattern=pattern)
		self["filelist"] = self.filelist

		self["FilelistActions"] = ActionMap(["SetupActions"],
			{
				"save": self.ok,
				"ok": self.ok,
				"cancel": self.exit
			})
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(_("DVD file browser"))

	def getDir(self, currentVal=None, defaultDir=None):
		if currentVal:
			return (currentVal.rstrip("/").rsplit("/",1))[0]
		return defaultDir or (resolveFilename(SCOPE_PLUGINS)+"Extensions/DVDBurn/")

	def ok(self):
		if self.filelist.canDescent():
			self.filelist.descent()
			if self.scope == "image":
				path = self["filelist"].getCurrentDirectory() or ""
				if fileExists(path+"VIDEO_TS"):
					self.close(path,self.scope,self.configRef)
		else:
			ret = self["filelist"].getCurrentDirectory() + '/' + self["filelist"].getFilename()
			self.close(ret,self.scope,self.configRef)

	def exit(self):
		if self.scope == "isopath":
			self.close(self["filelist"].getCurrentDirectory(),self.scope,self.configRef)
		self.close(None,False,None)

class ProjectSettings(Screen,ConfigListScreen):
	skin = """
		<screen name="ProjectSettings" position="center,center" size="560,440" title="Collection settings" >
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;19" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;19" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;19" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
			<widget source="key_blue" render="Label" position="420,0" zPosition="1" size="140,40" font="Regular;19" halign="center" valign="center" backgroundColor="#18188b" transparent="1" />
			<widget name="config" position="5,50" size="550,276" scrollbarMode="showOnDemand" />
			<ePixmap pixmap="skin_default/div-h.png" position="0,350" zPosition="1" size="560,2" />
			<widget source="info" render="Label" position="10,360" size="550,80" font="Regular;18" halign="center" valign="center" />
		</screen>"""

	def __init__(self, session, project = None):
		Screen.__init__(self, session)
		self.project = project

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self["key_yellow"] = StaticText(_("Load"))
		if config.usage.setup_level.index >= 2: # expert+
			self["key_blue"] = StaticText(_("Save"))
		else:
			self["key_blue"] = StaticText()

		if config.usage.setup_level.index >= 2: # expert+
			infotext = _("Available format variables") + ":\n$i=" + _("Track") + ", $t=" + _("Title") + ", $d=" + _("Description") + ", $l=" + _("length") + ", $c=" + _("chapters") + ",\n" + _("Record") + " $T=" + _("Begin time") + ", $Y=" + _("Year") + ", $M=" + _("month") + ", $D=" + _("day") + ",\n$A=" + _("audio tracks") + ", $C=" + _("Channel") + ", $f=" + _("filename")
		else:
			infotext = ""
		self["info"] = StaticText(infotext)

		self.keydict = {}
		self.settings = project.settings
		ConfigListScreen.__init__(self, [])
		self.initConfigList()

		self["setupActions"] = ActionMap(["SetupActions", "ColorActions"],
		{
		    "green": self.exit,
		    "red": self.cancel,
		    "blue": self.saveProject,
		    "yellow": self.loadProject,
		    "cancel": self.cancel,
		    "ok": self.ok,
		}, -2)
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(_("Collection settings"))

	def changedConfigList(self):
		key = self.keydict[self["config"].getCurrent()[1]]
		if key == "authormode" or key == "output":
			self.initConfigList()

	def initConfigList(self):
		authormode = self.settings.authormode.getValue()
		output = self.settings.output.getValue()
		self.list = []
		self.list.append(getConfigListEntry(_("Collection name"), self.settings.name))
		self.list.append(getConfigListEntry(_("Authoring mode"), self.settings.authormode))
		self.list.append(getConfigListEntry(_("Output"), self.settings.output))
		if output == "iso":
			self.list.append(getConfigListEntry(_("ISO path"), self.settings.isopath))
		if authormode.startswith("menu"):
			self.list.append(getConfigListEntry(_("Menu")+' '+_("template file"), self.settings.menutemplate))
			if config.usage.setup_level.index >= 2: # expert+
				self.list.append(getConfigListEntry(_("Menu")+' '+_("Title"), self.project.menutemplate.settings.titleformat))
				self.list.append(getConfigListEntry(_("Menu")+' '+_("Subtitles"), self.project.menutemplate.settings.subtitleformat))
				self.list.append(getConfigListEntry(_("Menu")+' '+_("background image"), self.project.menutemplate.settings.menubg))
				self.list.append(getConfigListEntry(_("Menu")+' '+_("Language selection"), self.project.menutemplate.settings.menulang))
			#self.list.append(getConfigListEntry(_("Menu")+' '+_("headline")+' '+_("color"), self.settings.color_headline))
			#self.list.append(getConfigListEntry(_("Menu")+' '+_("text")+' '+_("color"), self.settings.color_button))
			#self.list.append(getConfigListEntry(_("Menu")+' '+_("highlighted button")+' '+_("color"), self.settings.color_highlight))
			#self.list.append(getConfigListEntry(_("Menu")+' '+_("font face"), self.settings.font_face))
			#self.list.append(getConfigListEntry(_("Font size")+' ('+_("headline")+', '+_("Title")+', '+_("Subtitles")+')', self.settings.font_size))
			#self.list.append(getConfigListEntry(_("Menu")+' '+_("spaces (top, between rows, left)"), self.settings.space))
			#self.list.append(getConfigListEntry(_("Menu")+' '+_("Audio"), self.settings.menuaudio))
		if config.usage.setup_level.index >= 2: # expert+
			if authormode != "data_ts":
				self.list.append(getConfigListEntry(_("Titleset mode"), self.settings.titlesetmode))
				if self.settings.titlesetmode.getValue() == "single" or authormode == "just_linked":
					self.list.append(getConfigListEntry(_("VMGM (intro trailer)"), self.settings.vmgm))
			else:
				self.list.append(getConfigListEntry(_("DVD data format"), self.settings.dataformat))

		self["config"].setList(self.list)
		self.keydict = {}
		for key, val in self.settings.dict().iteritems():
			self.keydict[val] = key
		for key, val in self.project.menutemplate.settings.dict().iteritems():
			self.keydict[val] = key

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		key = self.keydict[self["config"].getCurrent()[1]]
		if key == "authormode" or key == "output" or key=="titlesetmode":
			self.initConfigList()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		key = self.keydict[self["config"].getCurrent()[1]]
		if key == "authormode" or key == "output" or key=="titlesetmode":
			self.initConfigList()

	def exit(self):
		self.applySettings()
		self.close(True)

	def applySettings(self):
		for x in self["config"].list:
			x[1].save()

	def ok(self):
		key = self.keydict[self["config"].getCurrent()[1]]
		from DVDProject import ConfigFilename
		if type(self["config"].getCurrent()[1]) == ConfigFilename:
			self.session.openWithCallback(self.FileBrowserClosed, FileBrowser, key, self["config"].getCurrent()[1])

	def cancel(self):
		self.close(False)

	def loadProject(self):
		self.session.openWithCallback(self.FileBrowserClosed, FileBrowser, "project", self.settings)

	def saveProject(self):
		if config.usage.setup_level.index >= 2: # expert+
			self.applySettings()
			ret = self.project.saveProject(resolveFilename(SCOPE_PLUGINS)+"Extensions/DVDBurn/")
			if ret.startswith:
				text = _("Save")+' '+_('OK')+':\n'+ret
				self.session.open(MessageBox,text,type = MessageBox.TYPE_INFO)
			else:
				text = _("Save")+' '+_('Error')
				self.session.open(MessageBox,text,type = MessageBox.TYPE_ERROR)

	def FileBrowserClosed(self, path, scope, configRef):
		if scope == "menutemplate":
			if self.project.menutemplate.loadTemplate(path):
				print "[ProjectSettings] menu template loaded"
				configRef.setValue(path)
				self.initConfigList()
			else:
				self.session.open(MessageBox,self.project.error,MessageBox.TYPE_ERROR)
		elif scope == "project":
			self.path = path
			print "len(self.titles)", len(self.project.titles)
			if len(self.project.titles):
				self.session.openWithCallback(self.askLoadCB, MessageBox,text = _("Your current collection will get lost!") + "\n" + _("Do you want to restore your settings?"), type = MessageBox.TYPE_YESNO)
			else:
				self.askLoadCB(True)
		elif scope:
			configRef.setValue(path)
			self.initConfigList()

	def askLoadCB(self, answer):
		if answer is not None and answer:
			if self.project.loadProject(self.path):
				self.initConfigList()
			else:
				self.session.open(MessageBox,self.project.error,MessageBox.TYPE_ERROR)

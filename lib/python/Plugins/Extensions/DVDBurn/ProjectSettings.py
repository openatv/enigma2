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
from enigma import eListboxPythonMultiContent, gFont, RT_HALIGN_LEFT
from Tools.Directories import resolveFilename, SCOPE_PLAYLIST, SCOPE_SKIN, SCOPE_FONTS
from Components.config import config, getConfigListEntry
from Components.ConfigList import ConfigListScreen

class WaitBox(MessageBox):
	def __init__(self, session, callback):
		MessageBox.__init__(self, session, text=_("please wait, loading picture..."), type = MessageBox.TYPE_INFO)
		self.skinName = "MessageBox"
		self.CB = callback
		self.onShown.append(self.runCB)

	def ok(self):
		pass

	def runCB(self):
		from enigma import eTimer
		self.delayTimer = eTimer()
		self.delayTimer.callback.append(self.CB)
		self.delayTimer.start(10,1)

class FileBrowser(Screen, HelpableScreen):
	skin = """
	<screen name="FileBrowser" position="100,100" size="520,376" title="DVD File Browser" >
		<widget name="filelist" position="0,0" size="520,376" scrollbarMode="showOnDemand" />
	</screen>"""
	def __init__(self, session, scope, settings):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		self.scope = scope
		pattern = ""
		currDir = "/"
		if self.scope == "project":
			currDir = resolveFilename(SCOPE_PLAYLIST)
			pattern = "(?i)^.*\.(ddvdp\.xml)"		
		if self.scope == "menubg":
			currDir = self.getDir(settings.menubg, resolveFilename(SCOPE_SKIN))
			pattern = "(?i)^.*\.(jpeg|jpg|jpe|png|bmp)"
		elif self.scope == "menuaudio":
			currDir = self.getDir(settings.menuaudio, resolveFilename(SCOPE_SKIN))
			pattern = "(?i)^.*\.(mp2|m2a|ac3)"
		elif self.scope == "vmgm":
			currDir = self.getDir(settings.vmgm, resolveFilename(SCOPE_SKIN))
			pattern = "(?i)^.*\.(mpg|mpeg)"
		elif self.scope == "font_face":
			currDir = self.getDir(settings.font_face, resolveFilename(SCOPE_FONTS))
			pattern = "(?i)^.*\.(ttf)"

		self.filelist = FileList(currDir, matchingPattern=pattern)
		self["filelist"] = self.filelist

		self["FilelistActions"] = ActionMap(["OkCancelActions"],
			{
				"ok": self.ok,
				"cancel": self.exit
			})

	def getDir(self, key, defaultDir):
		settingDir = key.getValue()
		if len(settingDir) > 1:
			return (settingDir.rstrip("/").rsplit("/",1))[0]
		else:
			return defaultDir

	def ok(self):
		if self.filelist.canDescent():
			self.filelist.descent()
		else:
			ret = self["filelist"].getCurrentDirectory() + '/' + self["filelist"].getFilename()
			self.close(ret,self.scope)

	def exit(self):
		self.close(None,False)

class ProjectSettings(Screen,ConfigListScreen):
	skin = """
		<screen position="90,83" size="560,445" title="Collection settings" >
		    <ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
		    <ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
		    <ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
		    <ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" alphatest="on" />
		    <widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		    <widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		    <widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
		    <widget source="key_blue" render="Label" position="420,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" />
		    <widget name="config" position="10,50" size="540,276" scrollbarMode="showOnDemand" />
		    <widget source="info" render="Label" position="20,350" size="520,90" font="Regular;16" />
		</screen>"""

	def __init__(self, session, project = None):
		Screen.__init__(self, session)
		self.project = project
		
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self["key_yellow"] = StaticText(_("Load"))
		self["key_blue"] = StaticText(_("Save"))
		
		infotext = _("Available format variables") + ":\n%i=" + _("Track") + ", %t=" + _("Title") + ", %d=" + _("Description") + ", %l=" + _("length") + ", %c=" + _("chapters") + ",\n" + _("Record") + " %T=" + _("Begin time") + ", %Y=" + _("year") + ", %M=" + _("month") + ", %D=" + _("day") + ",\n%C=" + _("Channel") + ", %f=" + _("filename")
		self["info"] = StaticText(infotext)

		self.settings = project.settings
		self.list = []
		self.list.append(getConfigListEntry(_("Collection name"), self.settings.name))
		self.list.append(getConfigListEntry(_("Authoring mode"), self.settings.authormode))
		self.list.append(getConfigListEntry(_("Menu")+' '+_("background image"), self.settings.menubg))
		self.list.append(getConfigListEntry(_("Menu")+' '+_("Title"), self.settings.titleformat))
		self.list.append(getConfigListEntry(_("Menu")+' '+_("Subtitles"), self.settings.subtitleformat))
		self.list.append(getConfigListEntry(_("Menu")+' '+_("headline")+' '+_("color"), self.settings.color_headline))
		self.list.append(getConfigListEntry(_("Menu")+' '+_("text")+' '+_("color"), self.settings.color_button))
		self.list.append(getConfigListEntry(_("Menu")+' '+_("highlighted button")+' '+_("color"), self.settings.color_highlight))
		self.list.append(getConfigListEntry(_("Menu")+' '+_("font face"), self.settings.font_face))
		self.list.append(getConfigListEntry(_("Font size")+' ('+_("headline")+', '+_("Title")+', '+_("Subtitles")+')', self.settings.font_size))
		self.list.append(getConfigListEntry(_("Menu")+' '+_("spaces (top, between rows, left)"), self.settings.space))
		self.list.append(getConfigListEntry(_("Menu")+' '+_("Audio"), self.settings.menuaudio))
		self.list.append(getConfigListEntry(_("VMGM (intro trailer)"), self.settings.vmgm))
		ConfigListScreen.__init__(self, self.list)
		
		self.keydict = {}
		for key, val in self.settings.dict().iteritems():
			self.keydict[val] = key
		
		self["setupActions"] = ActionMap(["SetupActions", "ColorActions"],
		{
		    "green": self.exit,
		    "red": self.cancel,
		    "blue": self.saveProject,
		    "yellow": self.loadProject,
		    "cancel": self.cancel,
		    "ok": self.ok,
		}, -2)
	
	def exit(self):
		self.applySettings()
		self.close(True)

	def applySettings(self):
		for x in self["config"].list:
			x[1].save()
		
	def ok(self):
		key = self.keydict[self["config"].getCurrent()[1]]
		browseKeys = ["menubg", "menuaudio", "vmgm", "font_face"]
		if key in browseKeys:
			self.session.openWithCallback(self.FileBrowserClosed, FileBrowser, key, self.settings)

	def cancel(self):
		self.close(False)

	def loadProject(self):
		self.session.openWithCallback(self.FileBrowserClosed, FileBrowser, "project", self.settings)

	def saveProject(self):
		self.applySettings()
		ret = self.project.saveProject(resolveFilename(SCOPE_PLAYLIST))
		if ret.startswith:
			text = _("Save")+' '+_('OK')+':\n'+ret
			self.session.open(MessageBox,text,type = MessageBox.TYPE_INFO)
		else:
			text = _("Save")+' '+_('Error')
			self.session.open(MessageBox,text,type = MessageBox.TYPE_ERROR)

	def FileBrowserClosed(self, path, scope):
		if scope == "project":
			if not self.project.loadProject(path):
				self.session.open(MessageBox,self.project.error,MessageBox.TYPE_ERROR)
		elif scope:
			self.settings.dict()[scope].setValue(path)

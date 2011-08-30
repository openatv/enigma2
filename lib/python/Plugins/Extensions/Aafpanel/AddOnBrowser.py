from Screens.Screen import Screen
from enigma import eConsoleAppContainer
from Components.ActionMap import ActionMap
from Components.PluginComponent import plugins
from Components.PluginList import *
from Components.Label import Label
from Screens.MessageBox import MessageBox
from Screens.Console import Console
from Plugins.Plugin import PluginDescriptor
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_SKIN_IMAGE
from Tools.LoadPixmap import LoadPixmap

from Components.Pixmap import Pixmap
from Components.Sources.StaticText import StaticText
from Components.MenuList import MenuList


def AddOnCategoryComponent(name, png):
	res = [ name ]
	
	res.append(MultiContentEntryText(pos=(130, 20), size=(300, 25), font=0, text=name))
	res.append(MultiContentEntryPixmapAlphaTest(pos=(5, 20), size=(25,25), png = png))
	
	return res


def AddOnDownloadComponent(plugin, name):
	res = [ plugin ]
	text = ""
	if plugin.installed_version and plugin.installed_version != plugin.version:
		text = "%s -> updatable to %s" % (plugin.installed_version, plugin.version)
	elif plugin.installed_version:
		text = "Installed package version: %s" % (plugin.installed_version)
	else:
		text = "Package version: %s" % (plugin.version)
	
	res.append(MultiContentEntryText(pos=(70, 5), size=(640, 25), font=0, text = name))
	res.append(MultiContentEntryText(pos=(70, 30), size=(640, 17), font=1, text=plugin.description))
	res.append(MultiContentEntryText(pos=(70, 46), size=(640, 17), font=1, text=text))

	if plugin.statusicon is None:
		png1 = LoadPixmap(resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/icons/plugin.png"))
	else:
		png1 = plugin.statusicon

	res.append(MultiContentEntryPixmapAlphaTest(pos=(20,12), size=(48,48), png = png1))
	
	return res

class AddOnDescriptor:
	def __init__(self, name = "", what = "", description = "", status = 0, version = "", icon = None, statusicon = None, installed_version = ""):
		self.name = name
		self.what = what
		self.description = description
		self.status = status
		self.version = version
		if icon is None:
			self.icon = None
		else:
			self.icon = icon
		
		if statusicon is None:
			self.statusicon = None
		else:
			self.statusicon = statusicon
		self.installed_version = installed_version

class AddOn:
	def __init__(self, name = "", version = "", description = "", status = 0, installed_version = ""):
		self.name = name
		self.version = version
		self.description = description
		self.status = status
		self.installed_version = installed_version

class DownloadBrowser(Screen):

	skin = """
		<screen name="DownloadBrowser" position="center,center" size="660,475" title="Addon Browser">
			<widget font="Regular;20" halign="center" name="text" position="10,10" size="640,455" valign="center" zPosition="1"/>
			<widget name="list" position="10,10" scrollbarMode="showOnDemand" size="640,455" zPosition="2"/>
		</screen>"""
		

	def __init__(self, session, args = None):
		Screen.__init__(self, session)
		
		self.container = eConsoleAppContainer()
		self.container.appClosed.append(self.runFinished)
		self.container.dataAvail.append(self.dataAvail)
		self.onLayoutFinish.append(self.startRun)
		self.onShown.append(self.setWindowTitle)
		
		self.list = []
		self["list"] = PluginList(self.list)
		self.pluginlist = []
		self.expanded = []
		self.addoninstalled = []
		self.found = 0
		
		self["text"] = Label(_("Downloading addon information. Please wait..."))
		
		self.run = 0

		self.remainingdata = ""

		self["actions"] = ActionMap(["WizardActions"], 
		{
			"ok": self.go,
			"back": self.close,
		})

	def go(self):
		sel = self["list"].l.getCurrentSelection()

		if sel is None:
			return

		if type(sel[0]) is str: # category
			if sel[0] in self.expanded:
				self.expanded.remove(sel[0])
			else:
				self.expanded.append(sel[0])
			self.updateList()
		else:
			if sel[0].status == 0:
				self.session.openWithCallback(self.runInstall, MessageBox, _("Do you really want to download\nthe addon \"%s\"?") % sel[0].name)
			elif sel[0].status == 1:
				self.session.openWithCallback(self.runInstall, MessageBox, _("Do you really want to REMOVE\nthe addon \"%s\"?") % sel[0].name)
			elif sel[0].status == 2:
				self.session.openWithCallback(self.runDeleteUpdateCallBack, DialogUpdateDelete, _("The addon \"%s\" is already installed and an update is available.\nWhat do you want to do?") % sel[0].name)

	def runInstall(self, val):
		if val:
			if self["list"].l.getCurrentSelection()[0].status != 1:
				self.session.openWithCallback(self.installFinished, Console, cmdlist = ["opkg install " + self["list"].l.getCurrentSelection()[0].name])
			else:
				self.session.openWithCallback(self.installFinished, Console, cmdlist = ["opkg remove " + self["list"].l.getCurrentSelection()[0].name])
	
	def runDeleteUpdateCallBack(self, answer):
		print "answer:", answer
		if answer == 1:
			self.session.openWithCallback(self.installFinished, Console, cmdlist = ["opkg install " + self["list"].l.getCurrentSelection()[0].name])
		elif answer == 0:
			self.session.openWithCallback(self.installFinished, Console, cmdlist = ["opkg remove " + self["list"].l.getCurrentSelection()[0].name])


	def setWindowTitle(self):
		self.setTitle(_("OpenAAF AddOn Browser"))

	def startRun(self):
		print "startRun(self):"
		self["list"].instance.hide()
		self.container.execute("opkg update")

	def installFinished(self):
		# was ist eigentlich passiert? Aktualisiere...
		self["list"].instance.hide()
		try:
			f = open("/usr/lib/opkg/info/"+self["list"].l.getCurrentSelection()[0].name+".control", "r")
			addoncontent = f.read()
			f.close()
		except:
			addoncontent = ""
		name = ""
		version = ""
		description = ""
		addoncontentInfo = addoncontent.split("\n")
		for line in addoncontentInfo:
			if line.startswith("Package: "):
				name = line[9:]
			if line.startswith("Version: "):
				version = line[9:]
			if line.startswith("Description: "):
				description = line[13:]
		if name != "" and version != "":
			for aa in self.pluginlist:
				if aa.name == name:
					if version == self["list"].l.getCurrentSelection()[0].version:
						aa.status = 1
						aa.installed_version = aa.version
					else:
						aa.status = 2
		else:
			for aa in self.pluginlist:
				if aa.name == self["list"].l.getCurrentSelection()[0].name:
					aa.status = 0
		self.updateList()
		plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))
		self["list"].instance.show()

	def runFinished(self, retval):
		self.remainingdata = ""
		if self.run == 0:
			self.run = 1
			self.container.execute("opkg list-installed enigma2-*")
		elif self.run == 1:
			self.run = 2
			self.container.execute("opkg list enigma2-*")
		elif self.run == 2:
			if len(self.pluginlist) > 0:
				self.updateList()
				self["list"].instance.show()
			else:
				self["text"].setText("No new plugins found")

	def dataAvail(self, str):
		#prepend any remaining data from the previous call
		str = self.remainingdata + str
		#split in lines
		lines = str.split('\n')
		#'str' should end with '\n', so when splitting, the last line should be empty. If this is not the case, we received an incomplete line
		if len(lines[-1]):
			#remember this data for next time
			self.remainingdata = lines[-1]
			lines = lines[0:-1]
		else:
			self.remainingdata = ""
		for x in lines:
			plugin = x.split(" - ")
			if len(plugin) >= 2 and self.run == 1:
				self.addoninstalled.append(AddOn(name = plugin[0], version = plugin[1], status = 1))
			elif len(plugin) == 3 and self.run == 2:
				flagStatus = 0 # nicht installiert
				installedVersion = ""
				for cb in self.addoninstalled:
					if plugin[0] == cb.name:
						if plugin[1] == cb.version:
							if cb.status != 2:
								flagStatus = 1 # installiert
								installedVersion = cb.version
							else:
								flagStatus = -1 # brauchen wir nicht, da schon als update gekennzeichnet
						else:
							cb.status = 2
							flagStatus = 2 # update
							installedVersion = cb.version
				if flagStatus != -1:
					self.pluginlist.append(AddOn(name = plugin[0], version = plugin[1], description = plugin[2], status = flagStatus, installed_version = installedVersion))

	def updateList(self):
		self.list = []
		expandableIcon = LoadPixmap(resolveFilename(SCOPE_PLUGINS, "Extensions/Aafpanel/icons/folder.png"))
		expandedIcon = LoadPixmap(resolveFilename(SCOPE_PLUGINS, "Extensions/Aafpanel/icons/lock_on.png"))
		verticallineIcon = LoadPixmap(resolveFilename(SCOPE_SKIN_IMAGE, "skin_default/verticalline-plugins.png"))
		installedIcon = LoadPixmap(resolveFilename(SCOPE_PLUGINS, "Extensions/Aafpanel/icons/installed.png"))
		notinstalledIcon = LoadPixmap(resolveFilename(SCOPE_PLUGINS, "Extensions/Aafpanel/icons/installable.png"))
		updateIcon = LoadPixmap(resolveFilename(SCOPE_PLUGINS, "Extensions/Aafpanel/icons/upgradeable.png"))
		self.plugins = {}
		for x in self.pluginlist:
			temp = ""
			temp1 = x.name
			if x.name.startswith('enigma2-skin-') or x.name.startswith('enigma2-cams-') or x.name.startswith('enigma2-configs-') or x.name.startswith('enigma2-picons-') or x.name.startswith('enigma2-languages-'):
				temp = x.name[8:]
			elif x.name.startswith('enigma2-plugin-'):
				temp = x.name[15:]
			else:
				continue
			split = temp.split('-')
			if len(split) < 2:
				continue
			if split[0] == "skin":
				split[0] = "skins" # manuelle Korrektur, damit ich die CVS Skins nicht neu erstellen muss...
			if not self.plugins.has_key(split[0]):
				self.plugins[split[0]] = []
			if x.status == 0:			
				pngstatus = notinstalledIcon
			elif x.status == 1:
				pngstatus = installedIcon
			elif x.status == 2:
				pngstatus = updateIcon
			else:
				pngstatus = None
			self.plugins[split[0]].append((AddOnDescriptor(name = x.name, what = split[0], description = x.description, icon = verticallineIcon, status = x.status, version = x.version, statusicon = pngstatus, installed_version = x.installed_version), split[1]))
		for x in self.plugins.keys():
			if x in self.expanded:
				self.list.append(AddOnCategoryComponent(x, expandedIcon))
				for plugin in self.plugins[x]:
					self.list.append(AddOnDownloadComponent(plugin[0], plugin[1]))
			else:
				self.list.append(AddOnCategoryComponent(x, expandableIcon))
		self["list"].l.setItemHeight(65)
		self["list"].l.setList(self.list)

class DialogUpdateDelete(Screen):

	skin = """
		<screen name="DialogUpdateDelete" position="center,center" size="600,10" title="AddOnBrowser">
		<widget name="text" position="65,8" size="520,0" font="Regular;22" />
		<widget name="QuestionPixmap" pixmap="skin_default/icons/input_question.png" position="5,5" size="53,53" alphatest="on" />
		<widget name="list" position="100,100" size="480,375" />
		<applet type="onLayoutFinish">
# this should be factored out into some helper code, but currently demonstrates applets.
from enigma import eSize, ePoint

orgwidth = self.instance.size().width()
orgpos = self.instance.position()
textsize = self[&quot;text&quot;].getSize()

# y size still must be fixed in font stuff...
textsize = (textsize[0] + 50, textsize[1] + 50)
offset = 0
offset = 60
wsizex = textsize[0] + 60
wsizey = textsize[1] + offset
if (280 &gt; wsizex):
	wsizex = 280
wsize = (wsizex, wsizey)


# resize
self.instance.resize(eSize(*wsize))

# resize label
self[&quot;text&quot;].instance.resize(eSize(*textsize))

# move list
listsize = (wsizex, 50)
self[&quot;list&quot;].instance.move(ePoint(0, textsize[1]))
self[&quot;list&quot;].instance.resize(eSize(*listsize))

# center window
newwidth = wsize[0]
self.instance.move(ePoint(orgpos.x() + (orgwidth - newwidth)/2, orgpos.y()))
		</applet>
	</screen>"""

	def __init__(self, session, text,):
		Screen.__init__(self, session)
 		self["text"] = Label(text)
		self["Text"] = StaticText(text)
		self.text = text
		self["QuestionPixmap"] = Pixmap()
		self.list = []
		self.list = [ (_("Update Addon"), 0), (_("Delete Addon"), 1) ]
		self["list"] = MenuList(self.list)
		self["actions"] = ActionMap(["MsgBoxActions", "DirectionActions"], 
			{
				"cancel": self.cancel,
				"ok": self.ok,
				"up": self.up,
				"down": self.down,
				"left": self.left,
				"right": self.right,
				"upRepeated": self.up,
				"downRepeated": self.down,
				"leftRepeated": self.left,
				"rightRepeated": self.right
			}, -1)

	def __onShown(self):
		self.onShown.remove(self.__onShown)
	def cancel(self):
		self.close(-1)
	def ok(self):
		self.close(self["list"].getCurrent()[1] == 0)
	def up(self):
		self.move(self["list"].instance.moveUp)
	def down(self):
		self.move(self["list"].instance.moveDown)
	def left(self):
		self.move(self["list"].instance.pageUp)
	def right(self):
		self.move(self["list"].instance.pageDown)
	def move(self, direction):
		self["list"].instance.moveSelection(direction)
	def __repr__(self):
		return str(type(self)) + "(" + self.text + ")"


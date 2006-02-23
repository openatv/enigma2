from Screen import Screen

from enigma import eConsoleAppContainer

from Components.MenuList import MenuList
from Components.ActionMap import ActionMap
from Components.PluginComponent import plugins
from Components.PluginList import *
from Components.config import config
from Components.Label import Label
from Screens.MessageBox import MessageBox
from Screens.Console import Console
from Plugins.Plugin import PluginDescriptor
from Tools.Directories import resolveFilename, SCOPE_PLUGINS

class PluginBrowser(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		
		self["red"] = Label(_("Delete"))
		self["green"] = Label(_("Download Plugins"))
		
		self.list = []
		self["list"] = PluginList(self.list)
		self.updateList()
		
		self["actions"] = ActionMap(["WizardActions", "ColorActions"],
		{
			"ok": self.save,
			"back": self.close,
			"red": self.delete,
			"green": self.download
		})
		
	def save(self):
		#self.close()
		self.run()
	
	def run(self):
		plugin = self["list"].l.getCurrentSelection()[0]
		
		plugin(session=self.session)
		
	def updateList(self):
		self.list = [ ]
		self.pluginlist = plugins.getPlugins(PluginDescriptor.WHERE_PLUGINMENU)
		for plugin in self.pluginlist:
			self.list.append(PluginEntryComponent(plugin))
		
		self["list"].l.setList(self.list)

	def delete(self):
		pass
	
	def download(self):
		self.session.openWithCallback(self.updateList, PluginDownloadBrowser)

class PluginDownloadBrowser(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		
		self.container = eConsoleAppContainer()
		self.container.appClosed.get().append(self.runFinished)
		self.container.dataAvail.get().append(self.dataAvail)
		self.onLayoutFinish.append(self.startRun)
		
		self.list = []
		self["list"] = PluginList(self.list)
		self.pluginlist = []
		
		self["text"] = Label(_("Downloading plugin information. Please wait..."))
		
		self.run = 0
				
		self["actions"] = ActionMap(["WizardActions"], 
		{
			"ok": self.go,
			"back": self.close,
		})
		
	def go(self):
		print "plugin: installing:", self.pluginlist[self["list"].l.getCurrentSelectionIndex()]
		self.session.openWithCallback(self.runInstall, MessageBox, _("Do you really want to download\nthe plugin \"" + self.pluginlist[self["list"].l.getCurrentSelectionIndex()][3] + "\"?"))
		
	def runInstall(self, val):
		if val:
			self.session.openWithCallback(self.installFinished, Console, ["ipkg install " + self.pluginlist[self["list"].l.getCurrentSelectionIndex()][0]])

	def startRun(self):
		self["list"].instance.hide()
		self.container.execute("ipkg update")
		
	def installFinished(self):
		plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))
		
	def runFinished(self, retval):
		if self.run == 0:
			self.run = 1
			self.container.execute("ipkg list enigma2-plugin-*")
		else:
			if len(self.pluginlist) > 0:
				self.updateList()
				self["list"].instance.show()
			else:
				self["text"].setText("No plugins found")

	def dataAvail(self, str):
		for x in str.split('\n'):
			plugin = x.split(" - ")
			if len(plugin) == 3:
				plugin.append(plugin[0][15:])

				self.pluginlist.append(plugin)
	
	def updateList(self):
		for x in self.pluginlist:
			plugin = PluginDescriptor(name = x[3], description = x[2])
			self.list.append(PluginEntryComponent(plugin))
		
		self["list"].l.setList(self.list)


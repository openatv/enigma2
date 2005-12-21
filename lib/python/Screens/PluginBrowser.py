from Screen import Screen

from Components.MenuList import MenuList
from Components.ActionMap import ActionMap
from Components.PluginComponent import plugins
from Components.PluginList import *
from Components.config import config


class PluginBrowser(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		
		self.list = []
		self["list"] = PluginList(self.list)
		self.updateList()
		
		self["actions"] = ActionMap(["WizardActions"], 
		{
			"ok": self.save,
			"back": self.close,
			"up": self.up,
			"down": self.down
		}, -1)
		
	def save(self):
		#self.close()
		self.run()
	
	def run(self):
		plugin = self.pluginlist[self["list"].l.getCurrentSelectionIndex()]
		plugins.runPlugin(plugin, self.session)
		
	def updateList(self):
		self.list = []
		self.pluginlist = plugins.getPluginList()
		for x in self.pluginlist:
			self.list.append(PluginEntryComponent(x[0], x[1]))
		
		self["list"].l.setList(self.list)

	def up(self):
		self["list"].instance.moveSelection(self["list"].instance.moveUp)
		
	def down(self):
		self["list"].instance.moveSelection(self["list"].instance.moveDown)

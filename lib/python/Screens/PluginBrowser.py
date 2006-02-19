from Screen import Screen

from Components.MenuList import MenuList
from Components.ActionMap import ActionMap
from Components.PluginComponent import plugins
from Components.PluginList import *
from Components.config import config
from Plugins.Plugin import PluginDescriptor

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

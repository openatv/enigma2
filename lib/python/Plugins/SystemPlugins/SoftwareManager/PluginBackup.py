from enigma import *
from Screens.Screen import Screen
from Components.Button import Button
from Components.Label import Label
from Components.ActionMap import ActionMap
from Screens.Console import Console

class PluginBackup(Screen):
	skin = """
	<screen position="center,center" size="560,400" title="Plugin Backup">
		<ePixmap position="0,360"   zPosition="1" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
		<ePixmap position="140,360" zPosition="1" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />
		<widget name="key_red" position="0,360" zPosition="2" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
		<widget name="key_green" position="140,360" zPosition="2" size="140,40" valign="center" halign="center" font="Regular;21" transparent="1" shadowColor="black" shadowOffset="-1,-1" />
		<widget name="info-pluginbackup" position="10,30" zPosition="1" size="550,100" font="Regular;20" halign="left" valign="top" transparent="1" />
	</screen>"""
		
	def __init__(self, session, args = 0):
		Screen.__init__(self, session)
		self.session = session
		
		self["key_green"] = Button("Backup Plugins")
		self["key_red"] = Button("Exit")
		self["info-pluginbackup"] = Label(_("Installed Plugins will be written to:\n/etc/enigma2/installed-list.txt\nMake sure you include that file into settings backup."))
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], 
		{
			"green": self.green,
			"red": self.quit,
			"cancel": self.quit,
		}, -2)

	def quit(self):
		self.close()

	def green(self):
		self.session.open(Console, title = "Plugin Backup", cmdlist = ["sh '/usr/lib/enigma2/python/Plugins/SystemPlugins/SoftwareManager/PluginBackup.sh'"])


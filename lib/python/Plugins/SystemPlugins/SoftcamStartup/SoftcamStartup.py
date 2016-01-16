from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.FileList import FileEntryComponent, FileList
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import ActionMap, NumberActionMap
from Components.Button import Button
from Components.Label import Label
from Components.config import config, ConfigElement, ConfigSubsection, ConfigSelection, ConfigSubList, getConfigListEntry, KEY_LEFT, KEY_RIGHT, KEY_OK
from Components.ConfigList import ConfigList
from Components.Pixmap import Pixmap
from Components.ScrollLabel import ScrollLabel
from Tools.Directories import fileExists

import os
from camcontrol import CamControl
from enigma import eTimer, eDVBCI_UI, eListboxPythonStringContent, eListboxPythonConfigContent

NoneData = "#!/bin/sh\n"

if not fileExists('/etc/init.d/softcam.None'):
	fd = file('/etc/init.d/softcam.None', 'w')
	fd.write(NoneData)
	fd.close()
	os.chmod("/etc/init.d/softcam.None", 0755)
else:
	pass

if not fileExists('/etc/init.d/cardserver.None'):
	fd = file('/etc/init.d/cardserver.None', 'w')
	fd.write(NoneData)
	fd.close()
	os.chmod("/etc/init.d/cardserver.None", 0755)
else:
	pass

class ConfigAction(ConfigElement):
	def __init__(self, action, *args):
		ConfigElement.__init__(self)
		self.value = "(OK)"
		self.action = action
		self.actionargs = args 
	def handleKey(self, key):
		if (key == KEY_OK):
			self.action(*self.actionargs)
	def getMulti(self, dummy):
		pass

class SoftcamStartup(Screen, ConfigListScreen):
	skin = """
	<screen name="SoftcamStartup" position="center,center" size="560,350" >
		<widget name="config" position="5,10" size="550,200"/>
		<ePixmap name="red" position="5,310" zPosition="1" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on"/>
		<ePixmap name="green" position="185,310" zPosition="1" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on"/>
		<widget name="key_red" position="45,310" zPosition="2" size="140,40" valign="center" halign="left" font="Regular;21" transparent="1"/>
		<widget name="key_green" position="225,310" zPosition="2" size="140,40" valign="center" halign="left" font="Regular;21" transparent="1"/>
	</screen>"""
	def __init__(self, session, showExtentionMenuOption):
		Screen.__init__(self, session)

		self.setup_title = _("Softcam startup")

		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "CiSelectionActions"],
			{
				"cancel": self.cancel,
				"red": self.cancel,
				"green": self.save,
			},-1)

		self.list = [ ]
		ConfigListScreen.__init__(self, self.list, session = session)

		self.softcam1 = CamControl('softcam')
		self.softcam2 = CamControl('cardserver')

		softcamlistprimary = self.softcam1.getList()
		softcamlistsecondary = self.softcam2.getList()

		self.softcamlistprimary = ConfigSelection(choices = softcamlistprimary)
		self.softcamlistprimary.value = self.softcam1.current()
		self.softcamlistsecondary = ConfigSelection(choices = softcamlistsecondary)
		self.softcamlistsecondary.value = self.softcam2.current()

		self.list.append(getConfigListEntry(_("Select primary softcam"), self.softcamlistprimary))
		self.list.append(getConfigListEntry(_("Select secondary softcam"), self.softcamlistsecondary))
		self.list.append(getConfigListEntry(_("Restart primary softcam"), ConfigAction(self.restart, "s")))
		self.list.append(getConfigListEntry(_("Restart secondary softcam"), ConfigAction(self.restart, "c"))) 
		self.list.append(getConfigListEntry(_("Restart both"), ConfigAction(self.restart, "sc")))

		if showExtentionMenuOption:
			self.list.append(getConfigListEntry(_("Show softcam startup in extensions menu"), config.misc.softcam_startup.extension_menu))

		self["key_red"] = Label(_("Cancel"))
		self["key_green"] = Label(_("OK"))

		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(self.setup_title)

	def restart(self, what):
		self.what = what
		if "s" in what:
			if "c" in what:
				msg = _("Please wait, restarting primary and secondary softcam.")
			else:
				msg  = _("Please wait, restarting primary softcam.")
		elif "c" in what:
			msg = _("Please wait, restarting secondary softcam.")
		self.mbox = self.session.open(MessageBox, msg, MessageBox.TYPE_INFO)
		self.activityTimer = eTimer()
		self.activityTimer.timeout.get().append(self.doStop)
		self.activityTimer.start(100, False)

	def doStop(self):
		self.activityTimer.stop()
		if "c" in self.what:
			self.softcam2.command('stop')
		if "s" in self.what:
			self.softcam1.command('stop')
		self.oldref = self.session.nav.getCurrentlyPlayingServiceReference()
		self.session.nav.stopService()
		self.activityTimer = eTimer()
		self.activityTimer.timeout.get().append(self.doStart)
		self.activityTimer.start(1000, False)

	def doStart(self):
		self.activityTimer.stop()
		del self.activityTimer 
		if "s" in self.what:
			self.softcam1.select(self.softcamlistprimary.value)
			self.softcam1.command('start')
		if "c" in self.what:
			self.softcam2.select(self.softcamlistsecondary.value)
			self.softcam2.command('start')
		if self.mbox:
			self.mbox.close()
		self.close()
		self.session.nav.playService(self.oldref)
		del self.oldref

	def save(self):
		what = ''
		if (self.softcamlistsecondary.value != self.softcam2.current()) and (self.softcamlistprimary.value != self.softcam1.current()):
			what = 'sc'
		elif (self.softcamlistsecondary.value != self.softcam2.current()):
			what = 'c'
		elif (self.softcamlistprimary.value != self.softcam1.current()):
			what = 's'
		else:
			what = ''
		if what:
			self.restart(what)
		else:
			from Components.PluginComponent import plugins
			plugins.reloadPlugins()
			config.misc.softcam_startup.extension_menu.save()
			self.close()

	def cancel(self):
		self.close()
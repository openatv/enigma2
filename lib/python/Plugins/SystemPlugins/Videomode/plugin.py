from Screens.Screen import Screen
from Plugins.Plugin import PluginDescriptor

from enigma import eTimer

from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Screens.MessageBox import MessageBox
from Screens.Setup import SetupSummary
from Components.ConfigList import ConfigListScreen
from Components.config import getConfigListEntry, config, ConfigNothing, ConfigSelection, ConfigSubDict
from VideoWizard import VideoWizard
from Components.config import config

from Tools.CList import CList

from VideoHardware import video_hw

class VideoSetup(Screen, ConfigListScreen):
	def __init__(self, session, hw):
		Screen.__init__(self, session)
		self.skinName = "Setup"
		self.setup_title = "Videomode Setup"
		self.hw = hw
		self.onChangedEntry = [ ]

		# handle hotplug by re-creating setup
		self.onShow.append(self.startHotplug)
		self.onHide.append(self.stopHotplug)

		self.list = [ ]
		ConfigListScreen.__init__(self, self.list, session = session, on_change = self.changedEntry)

		self["actions"] = ActionMap(["SetupActions"], 
			{
				"cancel": self.keyCancel,
				"save": self.apply,
			}, -2)

		self["title"] = Label(_("Video-Setup"))

		self["oktext"] = Label(_("OK"))
		self["canceltext"] = Label(_("Cancel"))
		self["ok"] = Pixmap()
		self["cancel"] = Pixmap()

		self.createSetup()
		self.grabLastGoodMode()

	def startHotplug(self):
		self.hw.on_hotplug.append(self.createSetup)

	def stopHotplug(self):
		self.hw.on_hotplug.remove(self.createSetup)

	def createSetup(self):
		self.list = [ ]
		self.list.append(getConfigListEntry(_("Output Type"), config.av.videoport))

		# if we have modes for this port:
		if config.av.videoport.value in config.av.videomode:
			# add mode- and rate-selection:
			self.list.append(getConfigListEntry(_("Mode"), config.av.videomode[config.av.videoport.value]))
			self.list.append(getConfigListEntry(_("Rate"), config.av.videorate[config.av.videomode[config.av.videoport.value].value]))

		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.createSetup()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.createSetup()

	def confirm(self, confirmed):
		if not confirmed:
			self.hw.setMode(*self.last_good)
		else:
			self.keySave()

	def grabLastGoodMode(self):
		port = config.av.videoport.value
		mode = config.av.videomode[port].value
		rate = config.av.videorate[mode].value
		self.last_good = (port, mode, rate)

	def apply(self):
		port = config.av.videoport.value
		mode = config.av.videomode[port].value
		rate = config.av.videorate[mode].value
		if (port, mode, rate) != self.last_good or True:
			self.hw.setMode(port, mode, rate)
			self.session.openWithCallback(self.confirm, MessageBox, "Is this videomode ok?", MessageBox.TYPE_YESNO, timeout = 5, default = False)
		else:
			self.keySave()

	# for summary:
	def changedEntry(self):
		for x in self.onChangedEntry:
			x()

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())

	def createSummary(self):
		return SetupSummary

#class VideomodeHotplug:
#	def __init__(self, hw):
#		self.hw = hw
#		self.hw.on_hotplug.append(self.hotplug)
#
#	def hotplug(self, what):
#		print "hotplug detected on port '%s'" % (what)
# ...
#
#hotplug = None
#
#def startHotplug(self):
#	global hotplug
#	hotplug = VideomodeHotplug()
#	hotplug.start()
#
#def stopHotplug(self):
#	global hotplug
#	hotplug.stop()
#
#
#def autostart(reason, session = None, **kwargs):
#	if session is not None:
#		global my_global_session
#		my_global_session = session
#		return
#
#	if reason == 0:
#		startHotplug()
#	elif reason == 1:
#		stopHotplug()

def videoSetupMain(session, **kwargs):
	session.open(VideoSetup, video_hw)

def startSetup(menuid):
	if menuid != "system": 
		return [ ]

	return [(_("Video Setup"), videoSetupMain, "video_setup", None)]

def Plugins(**kwargs):
	list = []
	list.append(PluginDescriptor(name=_("Video Setup"), description=_("Advanced Video Setup"), where = PluginDescriptor.WHERE_MENU, fnc=startSetup))
	if config.misc.firstrun.value:
		list.append(PluginDescriptor(name=_("Video Wizard"), where = PluginDescriptor.WHERE_WIZARD, fnc=VideoWizard))
 	return list

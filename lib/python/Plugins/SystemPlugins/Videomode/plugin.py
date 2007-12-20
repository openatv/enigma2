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

from Tools.CList import CList

# The "VideoHardware" is the interface to /proc/stb/video.
# It generates hotplug events, and gives you the list of 
# available and preferred modes, as well as handling the currently
# selected mode. No other strict checking is done.
class VideoHardware:
	rates = { } # high-level, use selectable modes.

	modes = { }  # a list of (high-level) modes for a certain port.

	rates["PAL"] =			{ "50Hz":		{ 50: "pal", 60: "pal"},
												"60Hz":		{ 50: "pal60", 60: "pal60"},
												"multi":	{ 50: "pal", 60: "pal60"} }
	rates["NTSC"] =			{ "60Hz": 	{ 50: "ntsc", 60: "ntsc"} }
	rates["Multi"] =		{ "multi": 	{ 50: "pal", 60: "ntsc"} }
	rates["720p"] =			{	"50Hz": 	{ 50: "720p50", 60: "720p50"},
												"60Hz": 	{ 50: "720p", 60: "720p"},
												"multi": 	{ 50: "720p50", 60: "720p"} }
	rates["1080i"] =		{ "50Hz":		{ 50: "1080i50", 60: "1080i50"},
												"60Hz":		{ 50: "1080i", 60: "1080i"},
												"multi":	{ 50: "1080i50", 60: "1080i"} }
	rates["PC"] = { 
		"1024x768": { 60: "1024x768"}, # not possible on DM7025
		"800x600" : { 60: "800x600"},  # also not possible
		"720x480" : { 60: "720x480"},
		"720x576" : { 60: "720x576"},
		"1280x720": { 60: "1280x720"},
		"1280x720 multi": { 50: "1280x720_50", 60: "1280x720"},
		"1920x1080": { 60: "1920x1080"},
		"1920x1080 multi": { 50: "1920x1080", 60: "1920x1080_50"},
		"1280x1024" : { 60: "1280x1024"},
		"640x480" : { 60: "640x480"} 
	}

	modes["Scart"] = ["PAL", "NTSC", "Multi"]
	modes["YPrPb"] = ["720p", "1080i"]
	modes["DVI"] = ["720p", "1080i", "PC"]

	def __init__(self):
		self.last_modes_preferred =  [ ]
		self.on_hotplug = CList()

		self.on_hotplug.append(self.createConfig)
		self.ignore_preferred = False   # "edid override"

		self.readAvailableModes()
		self.readPreferredModes()

		# until we have the hotplug poll socket
		self.timer = eTimer()
		self.timer.timeout.get().append(self.readAvailableModes)
		self.timer.start(1000)

	def readAvailableModes(self):
		try:
			modes = open("/proc/stb/video/videomode_choices").read()[:-1]
		except IOError:
			print "couldn't read available videomodes."
			self.modes_available = [ ]
			return
		self.modes_available = modes.split(' ')

	def readPreferredModes(self):
		try:
			modes = open("/proc/stb/video/videomode_preferred").read()[:-1]
			self.modes_preferred = modes.split(' ')
		except IOError:
			print "reading preferred modes failed, using all modes"
			self.modes_preferred = self.modes_available

		if self.modes_preferred != self.last_modes_preferred:
			self.last_modes_preferred = self.modes_preferred
			self.on_hotplug("DVI") # must be DVI

	# check if a high-level mode with a given rate is available.
	def isModeAvailable(self, port, mode, rate):
		rate = self.rates[mode][rate]
		for mode in rate.values():
			# DVI modes must be in "modes_preferred"
			if port == "DVI":
				if mode not in self.modes_preferred and not self.ignore_preferred:
					return False
			if mode not in self.modes_available:
				return False
		return True

	def setMode(self, port, mode, rate):
		# we can ignore "port"
		self.current_mode = mode
		modes = self.rates[mode][rate]

		mode_50 = modes.get(50)
		mode_60 = modes.get(60)
		if mode_50 is None:
			mode_50 = mode_60
		if mode_60 is None:
			mode_60 = mode_50

		try:
			open("/proc/stb/video/videomode_60hz", "w").write(mode_50)
			open("/proc/stb/video/videomode_50hz", "w").write(mode_60)
		except IOError:
			try:
				# fallback if no possibility to setup 50/60 hz mode
				open("/proc/stb/video/videomode", "w").write(mode_50)
			except IOError:
				print "setting videomode failed."

	def isPortAvailable(self, port):
		# fixme
		return True

	def getPortList(self):
		return [port for port in self.modes if self.isPortAvailable(port)]

	# get a list with all modes, with all rates, for a given port.
	def getModeList(self, port):
		res = [ ]
		for mode in self.modes[port]:
			# list all rates which are completely valid
			rates = [rate for rate in self.rates[mode] if self.isModeAvailable(port, mode, rate)]

			# if at least one rate is ok, add this mode
			if len(rates):
				res.append( (mode, rates) )
		return res

	def createConfig(self, *args):
		# create list of output ports
		portlist = self.getPortList()

		# create list of available modes
		config.av.videoport = ConfigSelection(choices = [(port, _(port)) for port in portlist])
		config.av.videomode = ConfigSubDict()
		config.av.videorate = ConfigSubDict()

		for port in portlist:
			modes = self.getModeList(port)
			if len(modes):
				config.av.videomode[port] = ConfigSelection(choices = [mode for (mode, rates) in modes])
			for (mode, rates) in modes:
				config.av.videorate[mode] = ConfigSelection(choices = rates)

video_hw = VideoHardware()

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
 	return [ 
# 		PluginDescriptor(where = [PluginDescriptor.WHERE_SESSIONSTART, PluginDescriptor.WHERE_AUTOSTART], fnc = autostart),
 		PluginDescriptor(name=_("Video Setup"), description=_("Advanced Video Setup"), where = PluginDescriptor.WHERE_MENU, fnc=startSetup) 
	]

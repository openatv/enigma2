from Components.Label import Label
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.AVSwitch import iAVSwitch
from Components.config import config, configfile

from Screens.Screen import Screen

from GlobalActions import globalActionMap

from bisect import insort
from enigma import eTimer

class VideoResolutionKey:
	def __init__(self, session):
		self.actionPending = False
		self.session = session

		globalActionMap.actions["videomode_down"] = self.videomodeDown
		globalActionMap.actions["videomode_up"] = self.vresSelection
		globalActionMap.actions["videomode_long"] = self.vresSelectionReset

	# Manage short/long button press, because the
	# InfoBarLongKeyDetection mechanism isn't necessarily available

	def videomodeDown(self):
		self.actionPending = True

	def vresSelection(self):
		if self.actionPending:
			self.session.open(VideoResolution)
			self.actionPending = False

	def vresSelectionReset(self):
		if self.actionPending:
			self.session.open(VideoResolution, reset=True)
			self.actionPending = False

class VideoResolution(Screen):

	videoResChoices = (
		("HDMI", "480p", "60Hz"),
		("HDMI", "576p", "50Hz"),
		("HDMI", "720p", "60Hz"),
		("HDMI", "1080i", "50Hz"),
		("HDMI", "1080p", "50Hz"),
		("HDMI", "2160p", "50Hz"),
	)

	def __init__(self, session, reset=False, save=False):
		Screen.__init__(self, session)

		self.save = save
		self.actionPending = False

		self["resolution"] = Label()
		self["summary_resolution"] = StaticText()

		self["actions"] = ActionMap(["VideoResolutionButtonActions", "OkCancelActions"], {
			"videomode_down": self.videomodeDown,
			"videomode_up": self.videomodeUp,
			"ok": self.choose,
			"cancel": self.cancel,
			"videomode_long": self.videomodeLong,
		}, prio=-1)

		def sortKey(port, mode, rate):
			return (port, int(mode[0:-1]), mode[-1], int(rate[0:-2]))

		ports = [p[0] for p in config.av.videoport.choices[:]]
		modes = config.av.videomode
		rates = config.av.videorate

		self.timeout = 8000

		self.choices = []
		for choice in self.videoResChoices:
			if iAVSwitch.isModeAvailable(*choice):
				insort(self.choices, (sortKey(*choice),) + choice)

		port = iAVSwitch.current_port
		mode = iAVSwitch.current_mode
		rate = iAVSwitch.current_rate

		currentChoice = (port, mode, rate)
		currentChoice = (sortKey(*currentChoice),) + currentChoice

		if currentChoice not in self.choices:
			insort(self.choices, currentChoice)

		port = config.av.videoport.value
		mode = config.av.videomode[port].value
		rate = config.av.videorate[mode].value

		prefChoice = (port, mode, rate)
		prefChoice = (sortKey(*prefChoice),) + prefChoice

		if prefChoice not in self.choices:
			insort(self.choices, prefChoice)

		self.orig = self.choices.index(currentChoice)
		self.pref = self.choices.index(prefChoice)

		self.Timer = eTimer()
		self.Timer.callback.append(self.choose)

		self.pos = self.orig
		if reset:
			self.prefMode()
		else:
			self.origMode()

	# Manage short/long button press, because the
	# InfoBarLongKeyDetection mechanism isn't necessarily available

	def videomodeDown(self):
		self.actionPending = True

	def videomodeUp(self):
		if self.actionPending:
			self.nextMode()
			self.actionPending = False

	def videomodeLong(self):
		if self.actionPending:
			self.prefMode()
			self.actionPending = False

	def vresSelection(self):
		if self.actionPending:
			self.session.open(VideoResolution)
			self.actionPending = False

	def nextMode(self):
		self.setMode((self.pos + 1) % len(self.choices))

	def cancel(self):
		if self.pos != self.orig:
			self.origMode()
		else:
			self.choose()

	def origMode(self):
		self.setMode(self.orig)

	def prefMode(self):
		self.setMode(self.pref)

	def setMode(self, newpos):
		self.pos = max(min(newpos, len(self.choices) - 1), 0)
		self.showChoice()
		choice = self.choices[self.pos]
		if (iAVSwitch.current_port, iAVSwitch.current_mode, iAVSwitch.current_rate) != choice[1:]:
			iAVSwitch.setMode(*choice[1:])
		self.Timer.start(self.timeout, True)

	def showChoice(self):
		if self.pos == self.pref:
			self["resolution"].text = _("%s/%s/%s (pref)") % (self.choices[self.pos][1:])
		elif self.pos == self.orig:
			self["resolution"].text = _("%s/%s/%s (orig)") % (self.choices[self.pos][1:])
		else:
			self["resolution"].text = _("%s/%s/%s") % (self.choices[self.pos][1:])
		self["summary_resolution"].text = _("%s/%s/%s") % (self.choices[self.pos][1:])

	def choose(self):
		self.Timer.stop()
		if self.save:
			port = config.av.videoport.value
			mode = config.av.videomode[port].value
			rate = config.av.videorate[mode].value
			choice = self.choices[self.pos]
			if (port, mode, rate) != choice[1:]:
				iAVSwitch.saveMode(*choice[1:])
				configfile.save()
		self.close()

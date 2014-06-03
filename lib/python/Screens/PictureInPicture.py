from Screens.Screen import Screen
from enigma import ePoint, eSize, eServiceCenter, getBestPlayableServiceReference, eServiceReference
from Components.SystemInfo import SystemInfo
from Components.VideoWindow import VideoWindow
from Components.config import config, ConfigPosition, ConfigYesNo, ConfigSelection
from Tools import Notifications
from Screens.MessageBox import MessageBox
from os import access, W_OK

pip_config_initialized = False
MAX_X = 720
MAX_Y = 576

class PictureInPictureZapping(Screen):
	skin = """<screen name="PictureInPictureZapping" flags="wfNoBorder" position="50,50" size="90,26" title="PiPZap" zPosition="-1">
			<eLabel text="PiP-Zap" position="0,0" size="90,26" foregroundColor="#00ff66" font="Regular;26" />
		</screen>"""

class PictureInPicture(Screen):
	def __init__(self, session):
		global pip_config_initialized
		Screen.__init__(self, session)
		self["video"] = VideoWindow()
		self.pipActive = session.instantiateDialog(PictureInPictureZapping)
		self.currentService = None
		self.currentServiceReference = None
		if not pip_config_initialized:
			choicelist = ["standard"]
			if SystemInfo["VideoDestinationConfigurable"]:
				choicelist.append("cascade")
				choicelist.append("split")
				choicelist.append("bigpig")
			if SystemInfo["HasExternalPIP"]:
				choicelist.append("external")
			config.av.pip = ConfigPosition(default=[-1, -1, -1, -1], args = (MAX_X, MAX_Y, MAX_X, MAX_Y))
			config.av.pip_mode = ConfigSelection(default="standard", choices=choicelist)
			pip_config_initialized = True
		self.onLayoutFinish.append(self.LayoutFinished)

	def __del__(self):
		del self.pipservice
		self.setExternalPiP(False)
		self.setSizePosMainWindow()

	def relocate(self):
		x = config.av.pip.value[0]
		y = config.av.pip.value[1]
		w = config.av.pip.value[2]
		h = config.av.pip.value[3]
		if x != -1 and y != -1 and w != -1 and h != -1:
			self.move(x, y)
			self.resize(w, h)

	def LayoutFinished(self):
		self.onLayoutFinish.remove(self.LayoutFinished)
		self.relocate()
		self.setExternalPiP(config.av.pip_mode.value == "external")

	def move(self, x, y):
		config.av.pip.value[0] = x
		config.av.pip.value[1] = y
		w = config.av.pip.value[2]
		h = config.av.pip.value[3]
		if config.av.pip_mode.value == "cascade":
			x = MAX_X - w
			y = 0
		elif config.av.pip_mode.value == "split":
			x = MAX_X / 2
			y = 0
		elif config.av.pip_mode.value == "bigpig":
			x = 0
			y = 0
		config.av.pip.save()
		self.instance.move(ePoint(x, y))

	def resize(self, w, h):
		config.av.pip.value[2] = w
		config.av.pip.value[3] = h
		config.av.pip.save()
		if config.av.pip_mode.value == "standard" or config.av.pip_mode.value == "external":
			self.instance.resize(eSize(*(w, h)))
			self["video"].instance.resize(eSize(*(w, h)))
			self.setSizePosMainWindow()
		elif config.av.pip_mode.value == "cascade":
			self.instance.resize(eSize(*(w, h)))
			self["video"].instance.resize(eSize(*(w, h)))
			self.setSizePosMainWindow(0, h, MAX_X - w, MAX_Y - h)
		elif config.av.pip_mode.value == "split":
			self.instance.resize(eSize(*(MAX_X/2, MAX_Y )))
			self["video"].instance.resize(eSize(*(MAX_X/2, MAX_Y)))
			self.setSizePosMainWindow(0, 0, MAX_X/2, MAX_Y)
		elif config.av.pip_mode.value == "bigpig":
			self.instance.resize(eSize(*(MAX_X, MAX_Y)))
			self["video"].instance.resize(eSize(*(MAX_X, MAX_Y)))

	def setSizePosMainWindow(self, x = 0, y = 0, w = MAX_X, h = MAX_Y):
		if SystemInfo["VideoDestinationConfigurable"]:
			open("/proc/stb/vmpeg/0/dst_left", "w").write("%x" % x)
			open("/proc/stb/vmpeg/0/dst_top", "w").write("%x" % y)
			open("/proc/stb/vmpeg/0/dst_width", "w").write("%x" % w)
			open("/proc/stb/vmpeg/0/dst_height", "w").write("%x" % h)
			open("/proc/stb/vmpeg/0/dst_apply", "w").write("%x" % 1)

	def setExternalPiP(self, onoff):
		if SystemInfo["HasExternalPIP"]:
			open(SystemInfo["HasExternalPIP"], "w").write(onoff and "on" or "off")

	def active(self):
		self.pipActive.show()

	def inactive(self):
		self.pipActive.hide()

	def getPosition(self):
		return self.instance.position().x(), self.instance.position().y()

	def getSize(self):
		return self.instance.size().width(), self.instance.size().height()

	def togglePiPMode(self):
		self.setMode(config.av.pip_mode.choices[(config.av.pip_mode.index + 1) % len(config.av.pip_mode.choices)])

	def setMode(self, mode):
		config.av.pip_mode.value = mode
		config.av.pip_mode.save()
		self.setExternalPiP(config.av.pip_mode.value == "external")
		self.relocate()

	def getMode(self):
		return config.av.pip_mode.value

	def playService(self, service):
		if service is None:
			return False
		ref = self.resolveAlternatePipService(service)
		if ref:
			if self.isPlayableForPipService(ref):
				print "playing pip service", ref and ref.toString()
			else:
				if not config.usage.hide_zap_errors.value:
					Notifications.AddPopup(text = _("No free tuner!"), type = MessageBox.TYPE_ERROR, timeout = 5, id = "ZapPipError")
				return False
			self.pipservice = eServiceCenter.getInstance().play(ref)
			if self.pipservice and not self.pipservice.setTarget(1):
				self.pipservice.start()
				self.currentService = service
				self.currentServiceReference = ref
				return True
			else:
				self.pipservice = None
				self.currentService = None
				self.currentServiceReference = None
				if not config.usage.hide_zap_errors.value:
					Notifications.AddPopup(text = _("Incorrect type service for PiP!"), type = MessageBox.TYPE_ERROR, timeout = 5, id = "ZapPipError")
		return False

	def getCurrentService(self):
		return self.currentService

	def getCurrentServiceReference(self):
		return self.currentServiceReference

	def isPlayableForPipService(self, service):
		playingref = self.session.nav.getCurrentlyPlayingServiceReference()
		if playingref is None or service == playingref:
			return True
		info = eServiceCenter.getInstance().info(service)
		oldref = self.currentServiceReference or eServiceReference()
		if info and info.isPlayable(service, oldref):
			return True
		return False

	def resolveAlternatePipService(self, service):
		if service and (service.flags & eServiceReference.isGroup):
			oldref = self.currentServiceReference or eServiceReference()
			return getBestPlayableServiceReference(service, oldref)
		return service

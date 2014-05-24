from Screens.Screen import Screen
from enigma import ePoint, eSize, eServiceCenter, getBestPlayableServiceReference, eServiceReference
from Components.VideoWindow import VideoWindow
from Components.config import config, ConfigPosition, ConfigYesNo, ConfigInteger
from Tools import Notifications
from Screens.MessageBox import MessageBox
from os import access, W_OK

pip_config_initialized = False

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
		self.has_external_pip = access("/proc/stb/vmpeg/1/external", W_OK)
		if not pip_config_initialized:
			config.av.pip = ConfigPosition(default=[-1, -1, -1, -1], args = (719, 567, 720, 568))
			config.av.pip_mode = ConfigInteger(default=0)  # 0 picture over picture, 1 picture beside picture, 2 splitscreen
			config.av.external_pip = ConfigYesNo(default = False)
			pip_config_initialized = True
		self.onLayoutFinish.append(self.LayoutFinished)

	def __del__(self):
		del self.pipservice
		self.setExternalPiP(False)
		self.setSizePosMainWindow()

	def LayoutFinished(self):
		self.onLayoutFinish.remove(self.LayoutFinished)
		x = config.av.pip.value[0]
		y = config.av.pip.value[1]
		w = config.av.pip.value[2]
		h = config.av.pip.value[3]
		if x != -1 and y != -1 and w != -1 and h != -1:
			if config.av.pip_mode.value == 0:
				self.move(x, y)
				self.resize(w, h)
			elif config.av.pip_mode.value == 1:
				self.move(720 - w, 0)
				self.resize(w, h)
			elif config.av.pip_mode.value == 2:
				self.move(360, 142)
				self.resize(360, 284)
		self.setExternalPiP(config.av.external_pip.value)

	def move(self, x, y):
		if config.av.pip_mode.value == 2:
			self.instance.move(ePoint(370, 152))
			return
		w = config.av.pip.value[2]
		if config.av.pip_mode.value == 1:
			x = 720 - w
			y = 0
		config.av.pip.value[0] = x
		config.av.pip.value[1] = y
		config.av.pip.save()
		self.instance.move(ePoint(x, y))

	def resize(self, w, h):
		if config.av.pip_mode.value == 2:
			self.instance.resize(eSize(*(340, 264)))
			self["video"].instance.resize(eSize(*(340, 264)))
			self.setSizePosMainWindow(0, 142, 360, 284)
			return
		config.av.pip.value[2] = w
		config.av.pip.value[3] = h
		config.av.pip.save()
		if config.av.pip_mode.value == 0:
			self.instance.resize(eSize(*(w, h)))
			self["video"].instance.resize(eSize(*(w, h)))
			self.setSizePosMainWindow()
		elif config.av.pip_mode.value == 1:
			self.instance.resize(eSize(*(w, h)))
			self["video"].instance.resize(eSize(*(w, h)))
			self.setSizePosMainWindow(0, h, 720 - w - 2 , 568 - h - 2)

	def setSizePosMainWindow(self, x = 0, y = 0, w = 720, h = 568):
		try:
			f = open("/proc/stb/vmpeg/0/dst_left","w")
			f.write("%x" % x)
			f.close()
			f = open("/proc/stb/vmpeg/0/dst_top","w")
			f.write("%x" % y)
			f.close()
			f = open("/proc/stb/vmpeg/0/dst_width","w")
			f.write("%x" % w)
			f.close()
			f = open("/proc/stb/vmpeg/0/dst_height","w")
			f.write("%x" % h)
			f.close()
			f = open("/proc/stb/vmpeg/0/dst_apply","w")
			f.write("1")
			f.close()
		except:
			pass

	def setExternalPiP(self, onoff):
		if self.has_external_pip:
			procentry = open("/proc/stb/vmpeg/1/external", "w")
			if onoff:
				procentry.write("on")
			else:
				procentry.write("off")

	def toggleExternalPiP(self):
		config.av.external_pip.value = not config.av.external_pip.value
		config.av.external_pip.save()
		self.setExternalPiP(config.av.external_pip.value)

	def active(self):
		self.pipActive.show()

	def inactive(self):
		self.pipActive.hide()

	def getPosition(self):
		return self.instance.position().x(), self.instance.position().y()

	def getSize(self):
		return self.instance.size().width(), self.instance.size().height()

	def setMode(self, mode):
		config.av.pip_mode.value = mode
		config.av.pip_mode.save()

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

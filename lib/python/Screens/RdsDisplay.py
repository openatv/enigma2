from os import stat
from os.path import isfile
from struct import unpack

from enigma import ePicLoad, ePoint, eServiceReference, eSize, getDesktop, iPlayableService, iRdsDecoder, iServiceInformation

from ServiceReference import isRadioServiceReference
from skin import applyAllAttributes
from Components.ActionMap import NumberActionMap
from Components.config import config
from Components.Element import Element
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.ServiceEventTracker import ServiceEventTracker
from Components.SystemInfo import BoxInfo
from Components.Converter.ServiceInfo import ServiceInfo
from Components.Sources.StaticText import StaticText
from Screens.Screen import Screen
from Tools.Directories import SCOPE_GUISKIN, SCOPE_SKINS, resolveFilename
from Tools.LoadPixmap import LoadPixmap


class DABSlideDisplay(Screen):
	"""Shared GUI radio background and DAB slideshow (public skin name retained)."""
	# Geometry of the bundled artwork, not HD/FHD screen coordinates. Fit the
	# cabinet and its display together so neither can move independently.
	RADIO_IMAGE_SIZE = (1672, 941)
	RADIO_DISPLAY = (400, 140, 868, 632)

	def __init__(self, session):
		desktopSize = getDesktop(0).size()
		width, height = desktopSize.width(), desktopSize.height()
		self.desktopWidth = width
		self.desktopHeight = height
		self.pictureAreaHeight = height
		self.radioDisplay = None
		self.rassActive = False
		self.radioFramePath = resolveFilename(SCOPE_SKINS, "icons/dab_radio.png")
		self.hasRadioFrame = isfile(self.radioFramePath)
		self.radioFrameLoader = None
		self.radioFrameLoading = None
		self.radioFrameLoaded = None
		self.radioFrameFailed = None
		self.radioFrameSize = None
		self.radioFrameKey = None
		self.radioFrameWidget = "radioFrame"
		self.radioPictureArea = None
		self.technicalInfoHeight = max(20, height * 32 // 720)
		self.technicalConverter = None
		self.technicalFrontend = None
		self.technicalFrontendFresh = False
		self.defaultRadioImage = resolveFilename(SCOPE_GUISKIN, "icons/default_dab.png")
		if not isfile(self.defaultRadioImage):
			self.defaultRadioImage = resolveFilename(SCOPE_GUISKIN, "picon_default.png")
		if not isfile(self.defaultRadioImage):
			self.defaultRadioImage = resolveFilename(SCOPE_SKINS, "skin_default/picon_default.png")
		self.defaultDVBImage = resolveFilename(SCOPE_GUISKIN, "icons/default_radio.png")
		self.skin = """
			<screen name="DABSlideDisplay" position="0,0" size="%d,%d" zPosition="-20" backgroundColor="black" flags="wfNoBorder">
				<widget name="radioFrame" position="0,0" size="%d,%d" zPosition="0" alphatest="off" />
				<widget name="picture" position="0,0" size="%d,%d" zPosition="1" alphatest="blend" scaleFlags="centerScaled" />
				<widget name="technicalInfo" position="0,0" size="%d,%d" zPosition="2" font="Regular;%d" halign="center" valign="center" noWrap="1" foregroundColor="#00c0c0c0" backgroundColor="#00000000" />
			</screen>""" % (width, height, width, height, width, height, width, self.technicalInfoHeight, max(14, height * 20 // 720))
		Screen.__init__(self, session)
		self["radioFrame"] = Pixmap()
		self["radioFrame"].hide()
		self.ignoreWidgets.append("radioFrame")
		self["picture"] = Pixmap()
		self["technicalInfo"] = Label()
		self["technicalInfo"].hide()
		self.ignoreWidgets.append("technicalInfo")
		self.slidePath = ""
		self.slideSignature = None
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
			iPlayableService.evStart: self.serviceStarted,
			iPlayableService.evUpdatedInfo: self.updateSlide,
			iPlayableService.evUpdatedRassSlidePic: self.rassPictureAvailable,
			iPlayableService.evEnd: self.hideSlide
		})
		self.onLayoutFinish.append(self.layoutFinished)
		self.onClose.append(self.removeNotifier)
		config.dab.slideshow.addNotifier(self.slideshowChanged, initial_call=False)
		config.misc.showradiopic.addNotifier(self.slideshowChanged, initial_call=False)
		config.dab.technicalInfo.addNotifier(self.slideshowChanged, initial_call=False)

	def serviceStarted(self):
		self.rassActive = False
		self.technicalFrontendFresh = False
		self.slideSignature = None
		self.updateSlide()

	def rassPictureAvailable(self):
		reference = self.session.nav.getCurrentlyPlayingServiceReference()
		if reference and reference.type != eServiceReference.idServiceDAB:
			# RASS contains broadcast MPEG still frames, not PNG/JPEG slides.
			self.rassActive = True
			self.hideSlide()

	def layoutFinished(self):
		self.hide()
		self.updateSlide()

	def slideshowChanged(self, configElement=None):
		# Background changes also change the available area for the same slide.
		self.slideSignature = None
		self.updateSlide()

	def updateTechnicalInfo(self, reference):
		widget = self["technicalInfo"]
		if config.dab.technicalInfo.value and reference and reference.type == eServiceReference.idServiceDAB and widget.instance is not None:
			if self.technicalConverter is None:
				# Read the existing converter on service events; no extra poller.
				self.technicalConverter = ServiceInfo("DABTechnical")
				self.technicalConverter.source = self.session.screen["CurrentService"]
				# Share the existing frontend poller, keeping it active even when
				# the InfoBar's own signal widgets are hidden.
				self.technicalFrontend = Element()
				self.technicalFrontend.connect(self.session.screen["FrontendStatus"])
				self.technicalFrontendFresh = False
				self.technicalFrontend.onChanged.append(self.technicalFrontendChanged)
				self.technicalFrontend.suspended = False
			widget.instance.move(ePoint(0, max(0, self.pictureAreaHeight - self.technicalInfoHeight)))
			widget.instance.resize(eSize(self.desktopWidth, self.technicalInfoHeight))
			self.updateTechnicalText()
			widget.show()
		else:
			self.hideTechnicalInfo()

	def technicalFrontendChanged(self):
		self.technicalFrontendFresh = True
		self.updateTechnicalText()

	def updateTechnicalText(self):
		if self.technicalConverter is None:
			return
		text = self.technicalConverter.text
		# FrontendStatus already polls for the InfoBar. Read its cached value,
		# and wait for its first update after a zap to avoid the previous tuner.
		if text and self.technicalFrontendFresh:
			snr = self.technicalFrontend.source.snr_db
			if snr is not None and snr >= 0:
				text = f"{text} | SNR {snr / 100.0:.1f} dB"
		if self["technicalInfo"].getText() != text:
			self["technicalInfo"].setText(text)

	def hideTechnicalInfo(self):
		self["technicalInfo"].hide()
		if self.technicalFrontend is not None:
			self.technicalFrontend.onChanged.remove(self.technicalFrontendChanged)
			self.technicalFrontend.suspended = True
			self.technicalFrontend.disconnectAll()
			self.technicalFrontend = None
		if self.technicalConverter is not None:
			self.technicalConverter.source = None
			self.technicalConverter = None

	def imageAreaHeight(self):
		return max(1, self.pictureAreaHeight - (self.technicalInfoHeight if self["technicalInfo"].visible else 0))

	def reserveRadioTextArea(self, radioDisplay):
		"""Keep the complete 4:3 slide above the skin's RDS text band."""
		self.radioDisplay = radioDisplay
		try:
			displayTop = radioDisplay.instance.position().y()
			textTops = [displayTop + radioDisplay[x].instance.position().y() for x in ("RadioText", "RtpText") if radioDisplay[x].instance is not None]
			pictureHeight = min((x for x in textTops if x > 0), default=self.desktopHeight)
		except (AttributeError, KeyError):
			pictureHeight = self.desktopHeight
		self.pictureAreaHeight = min(pictureHeight, self.desktopHeight)
		if self["picture"].instance is not None:
			self.slideSignature = None
			self.updateSlide()

	def imageSize(self, path):
		try:
			with open(path, "rb") as image:
				header = image.read(24)
				if header.startswith(b"\x89PNG\r\n\x1a\n") and len(header) >= 24:
					return unpack(">II", header[16:24])
				if not header.startswith(b"\xff\xd8"):
					return 0, 0
				image.seek(2)
				while True:
					marker = image.read(1)
					if not marker:
						break
					if marker != b"\xff":
						continue
					while marker == b"\xff":
						marker = image.read(1)
					if not marker or marker in (b"\xd8", b"\xd9"):
						continue
					lengthData = image.read(2)
					if len(lengthData) != 2:
						break
					length = unpack(">H", lengthData)[0]
					if length < 2:
						break
					if marker[0] in (0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7, 0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf):
						frame = image.read(5)
						if len(frame) == 5:
							height, width = unpack(">HH", frame[1:5])
							return width, height
						break
					image.seek(length - 2, 1)
		except (OSError, ValueError):
			pass
		return 0, 0

	def layoutPicture(self, path):
		width, height = self.imageSize(path)
		if width <= 0 or height <= 0:
			width, height = 320, 240
		if self.radioPictureArea is not None:
			areaLeft, areaTop, areaWidth, areaHeight = self.radioPictureArea
			scale = min(areaWidth / width, areaHeight / height)
		else:
			areaLeft, areaTop, areaWidth, areaHeight = 0, 0, self.desktopWidth, self.imageAreaHeight()
			# Keep the legacy layout if the artwork is absent or skin-owned.
			scale = min(2.0, areaWidth / width, areaHeight / height)
		targetWidth = max(1, int(width * scale))
		targetHeight = max(1, int(height * scale))
		left = areaLeft + (areaWidth - targetWidth) // 2
		top = areaTop + (areaHeight - targetHeight) // 2
		self["picture"].instance.move(ePoint(left, top))
		self["picture"].instance.resize(eSize(targetWidth, targetHeight))

	def layoutRadioFrame(self, isDAB=True):
		if isDAB:
			width, height = self.RADIO_IMAGE_SIZE
			pictureHeight = self.imageAreaHeight()
			scale = min(self.desktopWidth * 0.90 / width, pictureHeight * 0.94 / height)
			frameWidth, frameHeight = max(1, int(width * scale)), max(1, int(height * scale))
			left, top = (self.desktopWidth - frameWidth) // 2, (pictureHeight - frameHeight) // 2
			xPos, yPos, areaWidth, areaHeight = self.RADIO_DISPLAY
			self.radioPictureArea = (left + xPos * frameWidth // width, top + yPos * frameHeight // height, max(1, areaWidth * frameWidth // width), max(1, areaHeight * frameHeight // height))
			path = self.radioFramePath
		else:
			# Preserve the full-screen DVB radio artwork, without a video decoder.
			frameWidth, frameHeight = self.desktopWidth, self.desktopHeight
			left, top = 0, 0
			self.radioPictureArea = None
			path = self.defaultDVBImage
		self.radioFrameSize = (frameWidth, frameHeight)
		self.radioFrameKey = (path, self.radioFrameSize)
		# Older custom DABSlideDisplay skins only provide the picture widget.
		self.radioFrameWidget = "radioFrame" if self["radioFrame"].instance is not None else "picture"
		frameWidget = self[self.radioFrameWidget]
		frame = frameWidget.instance
		frame.move(ePoint(left, top))
		frame.resize(eSize(frameWidth, frameHeight))
		if self.radioFrameKey == self.radioFrameLoaded:
			frameWidget.show()
		else:
			frameWidget.hide()
		if self.radioFrameKey != self.radioFrameLoaded and self.radioFrameLoading is None and self.radioFrameKey != self.radioFrameFailed:
			if self.radioFrameLoader is None:
				self.radioFrameLoader = ePicLoad()
				self.radioFrameLoader.PictureData.get().append(self.radioFrameDecoded)
			self.radioFrameLoading = self.radioFrameKey
			# The aspect fit is already done above. Fill the exact integer size;
			# a second aspect calculation can leave an unpainted one-pixel edge.
			self.radioFrameLoader.setPara((frameWidth, frameHeight, 0, 1, False, 1, "#00000000"))
			if self.radioFrameLoader.startDecode(path):
				self.radioFrameFailed = self.radioFrameLoading
				self.radioFrameLoading = None

	def radioFrameDecoded(self, pictureInfo=None):
		pixmap = self.radioFrameLoader.getData()
		loadedKey = self.radioFrameLoading
		self.radioFrameLoading = None
		frameWidget = self[self.radioFrameWidget]
		if loadedKey == self.radioFrameKey and frameWidget.instance is not None:
			if pixmap is not None:
				frameWidget.instance.setPixmap(pixmap.__deref__())
				self.radioFrameLoaded = loadedKey
			else:
				self.radioFrameFailed = loadedKey
		# Recheck the service: a completed decode must not reappear over TV.
		self.updateSlide()

	def isEnabled(self, reference):
		return config.dab.slideshow.value

	def useGUIRadioPicture(self, info):
		# Keep the callable for skins/plugins; all audio modes now share the GUI.
		return True

	def updateSlide(self):
		reference = self.session.nav.getCurrentlyPlayingServiceReference()
		if self.radioDisplay is not None:
			self.radioDisplay.setDABBackground(bool(reference and reference.type == eServiceReference.idServiceDAB))
		if not reference or not isRadioServiceReference(reference) or self.rassActive:
			self.hideSlide()
			return
		self.updateTechnicalInfo(reference)
		isDAB = reference.type == eServiceReference.idServiceDAB
		showBackground = config.misc.showradiopic.value
		if not isDAB:
			self["picture"].hide()
			if self.radioDisplay is not None:
				self.radioDisplay["DabImage"].hide()
			self.slideSignature = None
			if showBackground and isfile(self.defaultDVBImage) and (self["radioFrame"].instance is not None or self["picture"].instance is not None):
				self.layoutRadioFrame(False)
				self.slidePath = self.defaultDVBImage
			else:
				self.hideSlide()
			self.show()
			return
		service = self.session.nav.getCurrentService()
		info = service and service.info()
		guiBackground = self.useGUIRadioPicture(info)
		embeddedImage = self.radioDisplay["DabImage"] if isDAB and self.radioDisplay is not None else None
		if embeddedImage is not None and not embeddedImage.skinAttributes:
			embeddedImage = None
		useRadioFrame = showBackground and embeddedImage is None and self.hasRadioFrame and self["radioFrame"].instance is not None
		if useRadioFrame:
			self.layoutRadioFrame()
		else:
			self["radioFrame"].hide()
			self.radioPictureArea = None
		path = info and isDAB and self.isEnabled(reference) and info.getInfoString(iServiceInformation.sTagPreviewImage) or ""
		if showBackground and not (path and isfile(path)):
			path = self.defaultRadioImage
		if not path or not isfile(path):
			self.hideSlide(hideTechnicalInfo=False)
			if guiBackground:
				self.show()
			return
		try:
			status = stat(path)
			signature = (path, status.st_mtime_ns, status.st_size)
		except OSError:
			self.hideSlide()
			return
		picture = embeddedImage if embeddedImage is not None else self["picture"]
		if picture.instance is not None:
			if signature != self.slideSignature:
				if embeddedImage is None:
					self.layoutPicture(path)
				picture.instance.setPixmapFromFile(path, True)
				self.slidePath = path
				self.slideSignature = signature
			picture.show()
			if embeddedImage is not None:
				self["picture"].hide()
				self.radioDisplay.show()
				if guiBackground:
					self.show()
				else:
					self.hide()
			else:
				self.show()

	def hideSlide(self, hideTechnicalInfo=True):
		if hideTechnicalInfo:
			self.hideTechnicalInfo()
		self["picture"].hide()
		self["radioFrame"].hide()
		if self.radioDisplay is not None:
			self.radioDisplay["DabImage"].hide()
		self.slidePath = ""
		self.slideSignature = None
		self.hide()

	def removeNotifier(self):
		self.hideTechnicalInfo()
		config.dab.slideshow.removeNotifier(self.slideshowChanged)
		config.misc.showradiopic.removeNotifier(self.slideshowChanged)
		config.dab.technicalInfo.removeNotifier(self.slideshowChanged)
		if self.radioFrameLoader is not None:
			self.radioFrameLoader.PictureData.get().remove(self.radioFrameDecoded)


class RdsInfoDisplaySummary(Screen):
	# Fallback for third-party display skins without an RDS summary.
	skin = """
		<screen position="0,0" size="132,64" zPosition="1" backgroundColor="#000000" flags="wfNoBorder">
			<widget source="station" render="Label" position="0,0" size="132,20" font="Regular;16" noWrap="1" />
			<widget source="message" render="RunningText" position="0,22" size="132,42" font="Regular;16" options="movetype=running,direction=top,wrap=1,always=0,startdelay=2000,steptime=80" />
		</screen>"""

	def __init__(self, session, parent):
		Screen.__init__(self, session, parent=parent)
		self["message"] = StaticText("")
		self["station"] = StaticText("")
		self["combined"] = StaticText("")
		self["picture"] = Pixmap()
		self["picture"].hide()
		self.ignoreWidgets.append("picture")
		self.slideSignature = None
		self.slidePath = ""
		self.colorDisplay = BoxInfo.getItem("ColorFrontpanelDisplay")
		self.pictureLoader = None
		self.loadingPicture = None
		self.failedPicture = None
		self.serviceGeneration = 0
		self.defaultImage = resolveFilename(SCOPE_GUISKIN, "icons/default_dab.png")
		self.eventTracker = ServiceEventTracker(screen=self, eventmap={
			iPlayableService.evStart: self.updateDisplay,
			iPlayableService.evUpdatedInfo: self.updateDisplay,
			iPlayableService.evUpdatedRadioText: self.updateDisplay,
			iPlayableService.evUpdatedRtpText: self.updateDisplay,
			iPlayableService.evEnd: self.clearDisplay
		})
		if hasattr(self.parent, "onText"):
			self.parent.onText.append(self.onText)
		self.onLayoutFinish.append(self.hide)
		self.onClose.append(self.removeCallback)
		config.dab.frontDisplay.addNotifier(self.updateDisplay, initial_call=False)

	def removeCallback(self):
		if hasattr(self.parent, "onText") and self.onText in self.parent.onText:
			self.parent.onText.remove(self.onText)
		config.dab.frontDisplay.removeNotifier(self.updateDisplay)
		if self.pictureLoader is not None:
			self.pictureLoader.PictureData.get().remove(self.pictureDecoded)

	def onText(self, message):
		# Read both fields: a bitrate/RTP update must not replace the DLS text.
		self.updateDisplay()

	def updateDisplay(self, configElement=None):
		if not self.parent.shown or not self.parent.alreadyShown:
			self.hide()
			return
		reference = self.session.nav.getCurrentlyPlayingServiceReference()
		if not reference or not isRadioServiceReference(reference):
			self.clearDisplay()
			return
		service = self.session.nav.getCurrentService()
		info = service and service.info()
		decoder = service and service.rdsDecoder()
		message = decoder and (decoder.getText(iRdsDecoder.RadioText) or decoder.getText(iRdsDecoder.RtpText)) or ""
		isDAB = reference.type == eServiceReference.idServiceDAB
		if not isDAB and not message:
			# Ordinary radio without RDS retains its usual EPG display.
			self.clearDisplay()
			return
		station = info and info.getName() or reference.getName() or ""
		station = station.replace("\x86", "").replace("\x87", "")
		showPicture = self.updatePicture(info) if isDAB else False
		if not showPicture:
			self["picture"].hide()
		# Do not restart a running-text animation on every metadata event.
		for name, text in (("station", station), ("message", "" if showPicture else message), ("combined", f"{station} - {message}" if message else station)):
			if self[name].text != text:
				self[name].text = text
		self.show()

	def updatePicture(self, info):
		picture = self["picture"]
		displayMode = config.dab.frontDisplay.value
		if not (self.colorDisplay and displayMode in ("slideshow", "logo") and picture.skinAttributes and picture.instance is not None):
			return False
		path = info and displayMode == "slideshow" and info.getInfoString(iServiceInformation.sTagPreviewImage) or ""
		if not (path and isfile(path)):
			path = info and info.getInfoString(iServiceInformation.sTagImage) or ""
		if not (path and isfile(path)):
			path = self.defaultImage
		try:
			status = stat(path)
		except OSError:
			return False
		signature = (path, status.st_mtime_ns, status.st_size)
		if signature != self.slideSignature:
			if self.loadingPicture is None and signature != self.failedPicture:
				if self.pictureLoader is None:
					self.pictureLoader = ePicLoad()
					self.pictureLoader.PictureData.get().append(self.pictureDecoded)
				reference = self.session.nav.getCurrentlyPlayingServiceReference()
				self.loadingPicture = (signature, reference.toString(), self.serviceGeneration)
				pictureSize = picture.instance.size()
				# Like LcdPicon: 101 forces RGB for 16-bit LCDs. Decode and fit in
				# the worker thread; scaled blits are not supported on every LCD.
				self.pictureLoader.setPara((pictureSize.width(), pictureSize.height(), 1, 1, False, 101, "#FF000000"))
				if self.pictureLoader.startDecode(path):
					self.failedPicture = signature
					self.loadingPicture = None
			return False
		picture.show()
		return True

	def pictureDecoded(self, pictureInfo=None):
		pixmap = self.pictureLoader.getData()
		pending = self.loadingPicture
		self.loadingPicture = None
		if pending is None:
			return
		signature, referenceString, generation = pending
		reference = self.session.nav.getCurrentlyPlayingServiceReference()
		if generation == self.serviceGeneration and reference and reference.toString() == referenceString:
			picture = self["picture"]
			if pixmap is not None and picture.instance is not None:
				picture.instance.setScale(0)
				picture.instance.setPixmap(pixmap.__deref__())
				self.slideSignature = signature
				self.slidePath = signature[0]
			else:
				self.failedPicture = signature
		self.updateDisplay()

	def clearDisplay(self):
		self.serviceGeneration += 1
		self.failedPicture = None
		for name in ("message", "station", "combined"):
			if self[name].text:
				self[name].text = ""
		self["picture"].hide()
		self.slideSignature = None
		self.slidePath = ""
		self.hide()


class RdsInfoDisplay(Screen):

	def __init__(self, session):
		Screen.__init__(self, session)

		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
				iPlayableService.evEnd: self.__serviceStopped,
				iPlayableService.evUpdatedRadioText: self.RadioTextChanged,
				iPlayableService.evUpdatedRtpText: self.RtpTextChanged,
				iPlayableService.evUpdatedRassInteractivePicMask: self.RassInteractivePicMaskChanged,
			})

		self["RadioText"] = Label()
		self["RtpText"] = Label()
		self["RassLogo"] = Pixmap()
		# Optional: existing skins keep DABSlideDisplay; new skins may place
		# this image inside their existing RdsInfoDisplay screen instead.
		self["DabImage"] = Pixmap()
		self["DabImage"].hide()
		self.ignoreWidgets.append("DabImage")
		self.dabBackground = False
		self.backgroundAttributes = []

		self.onLayoutFinish.append(self.layoutFinished)
		self.rassInteractivePossible = False
		self.onRassInteractivePossibilityChanged = []
		self.onText = []

	def createSummary(self):
		return RdsInfoDisplaySummary

	def layoutFinished(self):
		for name in ("RadioText", "RtpText"):
			widget = self[name]
			attributes = dict(widget.skinAttributes or [])
			if widget.instance is not None and not widget.instance.getWrap() and not any(x in attributes for x in ("fontScale", "scrollText")):
				# Use native font fitting for single-line radio text. Keep the
				# skin's font and HD/FHD scale, with a readable half-size floor.
				widget.instance.setFontScale(1, max(1, widget.instance.getFont().pointSize // 2))
		self.hideWidgets()

	def setDABBackground(self, enabled):
		if enabled == self.dabBackground or self.instance is None:
			return
		if enabled:
			self.backgroundAttributes = []
			for widget in (self, self["RadioText"], self["RtpText"]):
				if widget.instance is not None:
					attributes = [x for x in widget.skinAttributes or [] if x[0] in ("backgroundColor", "backgroundGradient", "transparent")]
					self.backgroundAttributes.append((widget.instance, attributes, widget.instance.isTransparent()))
					applyAllAttributes(widget.instance, getDesktop(0), [("backgroundColor", "#00000000"), ("transparent", "0")])
		else:
			# Restore the skin's original DVB-radio styling when leaving DAB.
			for instance, attributes, transparent in self.backgroundAttributes:
				instance.clearBackgroundColor()
				instance.setTransparent(transparent)
				applyAllAttributes(instance, getDesktop(0), attributes)
			self.backgroundAttributes = []
		self.dabBackground = enabled

	def hideWidgets(self):
		for name in ("RadioText", "RtpText", "RassLogo"):
			self[name].hide()
		for callback in self.onText:
			callback("")

	def RadioTextChanged(self):
		service = self.session.nav.getCurrentService()
		decoder = service and service.rdsDecoder()
		radioText = decoder and decoder.getText(iRdsDecoder.RadioText)
		if radioText:
			self.show()
			self["RadioText"].setText(radioText)
			self["RadioText"].show()
		else:
			self["RadioText"].hide()
		for callback in self.onText:
			callback(radioText)

	def RtpTextChanged(self):
		service = self.session.nav.getCurrentService()
		decoder = service and service.rdsDecoder()
		rtpText = decoder and decoder.getText(iRdsDecoder.RtpText)
		if rtpText:
			self.show()
			self["RtpText"].setText(rtpText)
			self["RtpText"].show()
		else:
			self["RtpText"].hide()
		for callback in self.onText:
			callback(rtpText)

	def RassInteractivePicMaskChanged(self):
		if not self.rassInteractivePossible:
			service = self.session.nav.getCurrentService()
			decoder = service and service.rdsDecoder()
			mask = decoder and decoder.getRassInteractiveMask()
			if mask and mask[0] & 1:  # RASS interactive index page available.
				self["RassLogo"].show()
				self.rassInteractivePossible = True
				for x in self.onRassInteractivePossibilityChanged:
					x(True)

	def __serviceStopped(self):
		self.hideWidgets()
		if self.rassInteractivePossible:
			self.rassInteractivePossible = False
			for x in self.onRassInteractivePossibilityChanged:
				x(False)


class RassInteractive(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		self["actions"] = NumberActionMap(["NumberActions", "RassInteractiveActions"],
			{
				"exit": self.close,
				"0": lambda x: self.numPressed(0),
				"1": lambda x: self.numPressed(1),
				"2": lambda x: self.numPressed(2),
				"3": lambda x: self.numPressed(3),
				"4": lambda x: self.numPressed(4),
				"5": lambda x: self.numPressed(5),
				"6": lambda x: self.numPressed(6),
				"7": lambda x: self.numPressed(7),
				"8": lambda x: self.numPressed(8),
				"9": lambda x: self.numPressed(9),
				"nextPage": self.nextPage,
				"prevPage": self.prevPage,
				"nextSubPage": self.nextSubPage,
				"prevSubPage": self.prevSubPage
			})

		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
				iPlayableService.evUpdatedRassInteractivePicMask: self.recvRassInteractivePicMaskChanged
			})

		self["subpages_1"] = Pixmap()
		self["subpages_2"] = Pixmap()
		self["subpages_3"] = Pixmap()
		self["subpages_4"] = Pixmap()
		self["subpages_5"] = Pixmap()
		self["subpages_6"] = Pixmap()
		self["subpages_7"] = Pixmap()
		self["subpages_8"] = Pixmap()
		self["subpages_9"] = Pixmap()
		self["Marker"] = Label(">")

		self.subpage = {
			1: self["subpages_1"],
			2: self["subpages_2"],
			3: self["subpages_3"],
			4: self["subpages_4"],
			5: self["subpages_5"],
			6: self["subpages_6"],
			7: self["subpages_7"],
			8: self["subpages_8"],
			9: self["subpages_9"]}

		self.subpage_png = {
			1: LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/rass_page1.png")),
			2: LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/rass_page2.png")),
			3: LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/rass_page3.png")),
			4: LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/rass_page4.png"))}

		self.current_page = 0
		self.current_subpage = 0
		self.showRassPage(0, 0)
		self.onLayoutFinish.append(self.updateSubPagePixmaps)

	def updateSubPagePixmaps(self):
		service = self.session.nav.getCurrentService()
		decoder = service and service.rdsDecoder()
		if decoder:
			mask = decoder.getRassInteractiveMask()
			for page in range(1, 10):
				subPageCount = self.countAvailSubpages(page, mask)
				subPage = self.subpage[page]
				if subPageCount:
					if subPage.instance:
						pixmap = self.subpage_png[subPageCount]
						if pixmap:
							subPage.instance.setPixmap(pixmap)
							subPage.show()
						else:
							print("[RdsDisplay] Error: RASS pixmap missing!")
				else:
					subPage.hide()
		else:
			print("[RdsDisplay] Error: No RDS decoder in updateSubPagePixmaps!")

	def recvRassInteractivePicMaskChanged(self):
		self.updateSubPagePixmaps()

	def showRassPage(self, page, subpage):
		service = self.session.nav.getCurrentService()
		decoder = service and service.rdsDecoder()
		if decoder:
			decoder.showRassInteractivePic(page, subpage)
			pageDifference = page - self.current_page
			self.current_page = page
			if pageDifference:
				currentPosition = self["Marker"].getPosition()
				yPos = currentPosition[1] + pageDifference * 25
				self["Marker"].setPosition(currentPosition[0], yPos)
		else:
			print("[RdsDisplay] Error: No RDS decoder in showRassPage!")

	def getMaskForPage(self, page, masks=None):
		if masks is None:
			service = self.session.nav.getCurrentService()
			decoder = service and service.rdsDecoder()
			masks = decoder and decoder.getRassInteractiveMask()
		mask = 0
		if masks and 0 <= page < 10 and page // 2 < len(masks):
			mask = masks[page // 2]
			if page % 2:
				mask >>= 4
			else:
				mask &= 0xF
		return mask

	def countAvailSubpages(self, page, masks):
		mask = self.getMaskForPage(page, masks)
		cnt = 0
		while mask:
			if mask & 1:
				cnt += 1
			mask >>= 1
		return cnt

	def nextPage(self):
		for offset in range(1, 11):
			page = (self.current_page + offset) % 10
			if self.getMaskForPage(page):
				self.numPressed(page)
				break

	def prevPage(self):
		for offset in range(1, 11):
			page = (self.current_page - offset) % 10
			if self.getMaskForPage(page):
				self.numPressed(page)
				break

	def nextSubPage(self):
		self.numPressed(self.current_page)

	def prevSubPage(self):
		num = self.current_page
		mask = self.getMaskForPage(num)
		cur_bit = 1 << self.current_subpage
		tmp = cur_bit
		while True:
			if tmp == 1:
				tmp = 8
			else:
				tmp >>= 1
			if tmp == cur_bit:  # no other subpage avail
				return
			if mask & tmp:  # next subpage found
				subpage = 0
				while tmp > 1:  # convert bit to subpage
					subpage += 1
					tmp >>= 1
				self.current_subpage = subpage
				self.showRassPage(num, subpage)
				return

	def numPressed(self, num):
		mask = self.getMaskForPage(num)
		if self.current_page == num:
			self.skip = 0
			cur_bit = 1 << self.current_subpage
			tmp = cur_bit
		else:
			self.skip = 1
			cur_bit = 16
			tmp = 1
		while True:
			if not self.skip:
				if tmp == 8 and cur_bit < 16:
					tmp = 1
				else:
					tmp <<= 1
			else:
				self.skip = 0
			if tmp == cur_bit:  # no other subpage avail
				return
			if mask & tmp:  # next subpage found
				subpage = 0
				while tmp > 1:  # convert bit to subpage
					subpage += 1
					tmp >>= 1
				self.current_subpage = subpage
				self.showRassPage(num, subpage)
				return

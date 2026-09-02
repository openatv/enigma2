from os import stat
from os.path import exists

from struct import unpack

from enigma import ePoint, eServiceReference, eSize, getDesktop, iPlayableService, iRdsDecoder, iServiceInformation
from Screens.Screen import Screen
from Components.ActionMap import NumberActionMap
from Components.ServiceEventTracker import ServiceEventTracker
from Components.Pixmap import Pixmap
from Components.config import config
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Tools.Directories import resolveFilename, SCOPE_GUISKIN
from Tools.LoadPixmap import LoadPixmap


class DABSlideDisplay(Screen):
	"""Display triggered DAB SLS images behind the existing radio UI."""

	def __init__(self, session):
		desktopSize = getDesktop(0).size()
		width, height = desktopSize.width(), desktopSize.height()
		self.desktopWidth = width
		self.desktopHeight = height
		self.pictureAreaHeight = height
		self.skin = """
			<screen name="DABSlideDisplay" position="0,0" size="%d,%d" zPosition="-20" backgroundColor="black" flags="wfNoBorder">
				<widget name="picture" position="0,0" size="%d,%d" zPosition="0" alphatest="blend" scaleFlags="centerScaled" />
			</screen>""" % (width, height, width, height)
		Screen.__init__(self, session)
		self["picture"] = Pixmap()
		self.slidePath = ""
		self.slideSignature = None
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
			iPlayableService.evStart: self.updateSlide,
			iPlayableService.evUpdatedInfo: self.updateSlide,
			iPlayableService.evEnd: self.hideSlide
		})
		self.onLayoutFinish.append(self.layoutFinished)
		self.onClose.append(self.removeNotifier)
		config.dab.rtlsdr.slideshow.addNotifier(self.slideshowChanged, initial_call=False)

	def layoutFinished(self):
		self.hide()
		self.updateSlide()

	def slideshowChanged(self, configElement=None):
		self.updateSlide()

	def reserveRadioTextArea(self, radioDisplay):
		"""Keep the complete 4:3 slide above the skin's RDS text band."""
		try:
			displayTop = radioDisplay.instance.position().y()
			textTop = radioDisplay["RadioText"].instance.position().y()
			pictureHeight = displayTop + textTop
		except (AttributeError, KeyError):
			return
		if pictureHeight <= 0 or pictureHeight >= self.desktopHeight:
			return
		self.pictureAreaHeight = pictureHeight
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
		# Avoid turning a typical 320x240 SLS bitmap into a visibly pixelated
		# full-screen image. Higher-resolution slides may use more of the area.
		scale = min(2.0, float(self.desktopWidth) / width, float(self.pictureAreaHeight) / height)
		targetWidth = max(1, int(width * scale))
		targetHeight = max(1, int(height * scale))
		left = (self.desktopWidth - targetWidth) // 2
		top = (self.pictureAreaHeight - targetHeight) // 2
		self["picture"].instance.move(ePoint(left, top))
		self["picture"].instance.resize(eSize(targetWidth, targetHeight))

	def isEnabled(self, reference):
		# The setting belongs to the optional USB receiver.  Satellite DAB uses
		# the normal DAB radio behaviour and remains enabled.
		return not reference.getPath().startswith("dab://rtlsdr/") or config.dab.rtlsdr.slideshow.value

	def updateSlide(self):
		reference = self.session.nav.getCurrentlyPlayingServiceReference()
		if not reference or reference.type != eServiceReference.idServiceDAB or not self.isEnabled(reference):
			self.hideSlide()
			return
		service = self.session.nav.getCurrentService()
		info = service and service.info()
		path = info and info.getInfoString(iServiceInformation.sTagPreviewImage) or ""
		if not path or not exists(path):
			self.hideSlide()
			return
		try:
			status = stat(path)
			signature = (path, status.st_mtime_ns, status.st_size)
		except OSError:
			self.hideSlide()
			return
		if signature != self.slideSignature or not self.shown:
			if self["picture"].instance is not None:
				self.layoutPicture(path)
				self["picture"].instance.setPixmapFromFile(path, True)
				self.slidePath = path
				self.slideSignature = signature
				self.show()

	def hideSlide(self):
		self.hide()

	def removeNotifier(self):
		config.dab.rtlsdr.slideshow.removeNotifier(self.slideshowChanged)


class RdsInfoDisplaySummary(Screen):
	def __init__(self, session, parent):
		Screen.__init__(self, session, parent=parent)
		self["message"] = StaticText("")
		self.parent.onText.append(self.onText)

	def onText(self, message):
		self["message"].text = message
		if message and len(message):
			self.show()
		else:
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

		self.onLayoutFinish.append(self.hideWidgets)
		self.rassInteractivePossible = False
		self.onRassInteractivePossibilityChanged = []
		self.onText = []

	def createSummary(self):
		return RdsInfoDisplaySummary

	def hideWidgets(self):
		for x in (self["RadioText"], self["RtpText"], self["RassLogo"]):
			x.hide()
		for x in self.onText:
			x('')

	def RadioTextChanged(self):
		service = self.session.nav.getCurrentService()
		decoder = service and service.rdsDecoder()
		rdsText = decoder and decoder.getText(iRdsDecoder.RadioText)
		if rdsText and len(rdsText):
			self["RadioText"].setText(rdsText)
			self["RadioText"].show()
		else:
			self["RadioText"].hide()
		for x in self.onText:
			x(rdsText)

	def RtpTextChanged(self):
		service = self.session.nav.getCurrentService()
		decoder = service and service.rdsDecoder()
		rtpText = decoder and decoder.getText(iRdsDecoder.RtpText)
		if rtpText and len(rtpText):
			self["RtpText"].setText(rtpText)
			self["RtpText"].show()
		else:
			self["RtpText"].hide()
		for x in self.onText:
			x(rtpText)

	def RassInteractivePicMaskChanged(self):
		if not self.rassInteractivePossible:
			service = self.session.nav.getCurrentService()
			decoder = service and service.rdsDecoder()
			mask = decoder and decoder.getRassInteractiveMask()
			if mask[0] & 1:  # rass interactive index page available
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
		if not decoder:  # this should never happen
			print("NO RDS DECODER in showRassPage")
		else:
			mask = decoder.getRassInteractiveMask()
			page = 1
			while page < 10:
				subpage_cnt = self.countAvailSubpages(page, mask)
				subpage = self.subpage[page]
				if subpage_cnt > 0:
					if subpage.instance:
						png = self.subpage_png[subpage_cnt]
						if png:
							subpage.instance.setPixmap(png)
							subpage.show()
						else:
							print("rass png missing")
				else:
					subpage.hide()
				page += 1

	def recvRassInteractivePicMaskChanged(self):
		self.updateSubPagePixmaps()

	def showRassPage(self, page, subpage):
		service = self.session.nav.getCurrentService()
		decoder = service and service.rdsDecoder()
		if not decoder:  # this should never happen
			print("NO RDS DECODER in showRassPage")
		else:
			decoder.showRassInteractivePic(page, subpage)
			page_diff = page - self.current_page
			self.current_page = page
			if page_diff:
				current_pos = self["Marker"].getPosition()
				y = current_pos[1]
				y += page_diff * 25
				self["Marker"].setPosition(current_pos[0], y)

	def getMaskForPage(self, page, masks=None):
		if not masks:
			service = self.session.nav.getCurrentService()
			decoder = service and service.rdsDecoder()
			if not decoder:  # this should never happen
				print("NO RDS DECODER in getMaskForPage")
			masks = decoder.getRassInteractiveMask()
		mask = 0
		if masks:
			mask = masks[(page * 4) / 8]
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
		mask = 0
		page = self.current_page
		while mask == 0:
			page += 1
			if page > 9:
				page = 0
			mask = self.getMaskForPage(page)
		self.numPressed(page)

	def prevPage(self):
		mask = 0
		page = self.current_page
		while mask == 0:
			if page > 0:
				page -= 1
			else:
				page = 9
			mask = self.getMaskForPage(page)
		self.numPressed(page)

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

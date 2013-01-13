from enigma import iPlayableService, iRdsDecoder
from Screens.Screen import Screen
from Components.ActionMap import NumberActionMap
from Components.ServiceEventTracker import ServiceEventTracker
from Components.Pixmap import Pixmap
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN
from Tools.LoadPixmap import LoadPixmap

class RdsInfoDisplaySummary(Screen):
	def __init__(self, session, parent):
		Screen.__init__(self, session, parent = parent)
		self["message"] = StaticText("")
		self.parent.onText.append(self.onText)

	def onText(self, message):
		self["message"].text = message
		if message and len(message):
			self.show()
		else:
			self.hide()

class RdsInfoDisplay(Screen):
	ALLOW_SUSPEND = True

	def __init__(self, session):
		Screen.__init__(self, session)

		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
			{
				iPlayableService.evEnd: self.__serviceStopped,
				iPlayableService.evUpdatedRadioText: self.RadioTextChanged,
				iPlayableService.evUpdatedRtpText: self.RtpTextChanged,
				iPlayableService.evUpdatedRassInteractivePicMask: self.RassInteractivePicMaskChanged,
			})

		self["RadioText"] = Label()
		self["RtpText"] = Label()
		self["RassLogo"] = Pixmap()

		self.onLayoutFinish.append(self.hideWidgets)
		self.rassInteractivePossible=False
		self.onRassInteractivePossibilityChanged = [ ]
		self.onText = [ ]

	def createSummary(self):
		return RdsInfoDisplaySummary

	def hideWidgets(self):
		for x in (self["RadioText"],self["RtpText"],self["RassLogo"]):
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
			if mask[0] & 1: #rass interactive index page available
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

		self["actions"] = NumberActionMap( [ "NumberActions", "RassInteractiveActions" ],
			{
				"exit": self.close,
				"0": lambda x : self.numPressed(0),
				"1": lambda x : self.numPressed(1),
				"2": lambda x : self.numPressed(2),
				"3": lambda x : self.numPressed(3),
				"4": lambda x : self.numPressed(4),
				"5": lambda x : self.numPressed(5),
				"6": lambda x : self.numPressed(6),
				"7": lambda x : self.numPressed(7),
				"8": lambda x : self.numPressed(8),
				"9": lambda x : self.numPressed(9),
				"nextPage": self.nextPage,
				"prevPage": self.prevPage,
				"nextSubPage": self.nextSubPage,
				"prevSubPage": self.prevSubPage
			})

		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=
			{
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
			1 : self["subpages_1"],
			2 : self["subpages_2"],
			3 : self["subpages_3"],
			4 : self["subpages_4"],
			5 : self["subpages_5"],
			6 : self["subpages_6"],
			7 : self["subpages_7"],
			8 : self["subpages_8"],
			9 : self["subpages_9"] }

		self.subpage_png = {
			1 : LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/rass_page1.png")),
			2 : LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/rass_page2.png")),
			3 : LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/rass_page3.png")),
			4 : LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "icons/rass_page4.png")) }

		self.current_page=0
		self.current_subpage=0
		self.showRassPage(0,0)
		self.onLayoutFinish.append(self.updateSubPagePixmaps)

	def updateSubPagePixmaps(self):
		service = self.session.nav.getCurrentService()
		decoder = service and service.rdsDecoder()
		if not decoder: # this should never happen
			print "NO RDS DECODER in showRassPage"
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
							print "rass png missing"
				else:
					subpage.hide()
				page += 1

	def recvRassInteractivePicMaskChanged(self):
		self.updateSubPagePixmaps()

	def showRassPage(self, page, subpage):
		service = self.session.nav.getCurrentService()
		decoder = service and service.rdsDecoder()
		if not decoder: # this should never happen
			print "NO RDS DECODER in showRassPage"
		else:
			decoder.showRassInteractivePic(page, subpage)
			page_diff = page - self.current_page
			self.current_page = page
			if page_diff:
				current_pos = self["Marker"].getPosition()
				y = current_pos[1]
				y += page_diff * 25
				self["Marker"].setPosition(current_pos[0],y)

	def getMaskForPage(self, page, masks=None):
		if not masks:
			service = self.session.nav.getCurrentService()
			decoder = service and service.rdsDecoder()
			if not decoder: # this should never happen
				print "NO RDS DECODER in getMaskForPage"
			masks = decoder.getRassInteractiveMask()
		if masks:
			mask = masks[(page*4)/8]
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
			if tmp == cur_bit: # no other subpage avail
				return
			if mask & tmp: # next subpage found
				subpage = 0
				while tmp > 1: # convert bit to subpage
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
			if tmp == cur_bit: # no other subpage avail
				return
			if mask & tmp: # next subpage found
				subpage = 0
				while tmp > 1: # convert bit to subpage
					subpage += 1
					tmp >>= 1
				self.current_subpage = subpage
				self.showRassPage(num, subpage)
				return

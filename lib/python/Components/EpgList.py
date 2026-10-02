import datetime
import re
from time import localtime, mktime, strftime, time

from enigma import BT_KEEP_ASPECT_RATIO, BT_SCALE, RT_HALIGN_CENTER, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_CENTER, RT_WRAP, eEPGCache, eListbox, eListboxPythonMultiContent, eRect, eServiceReference, eSize, gFont, loadPNG

from Components.GUIComponent import GUIComponent
from Components.MultiContent import MultiContentEntryPixmapAlphaBlend, MultiContentEntryPixmapAlphaTest, MultiContentEntryText
from Components.Renderer.Picon import getChannelSelectionPiconName
from Components.config import config
from ServiceReference import ServiceReference
from Tools.Alternatives import CompareWithAlternatives
from Tools.Directories import SCOPE_GUISKIN, resolveFilename
from Tools.LoadPixmap import LoadPixmap
from Tools.TextBoundary import getTextBoundarySize
from skin import getSkinFactor, parameters as skinparameter, parseColor, parseFont, parseScale

EPG_TYPE_SINGLE = 0
EPG_TYPE_MULTI = 1
EPG_TYPE_SIMILAR = 2
EPG_TYPE_ENHANCED = 3
EPG_TYPE_INFOBAR = 4
EPG_TYPE_GRAPH = 5
EPG_TYPE_INFOBARGRAPH = 7
EPG_TYPE_VERTICAL = 8

MAX_TIMELINES = 6


class EPGListBase(GUIComponent):
	def __init__(self, session, selChangedCB=None):
		GUIComponent.__init__(self)

		self.session = session
		self.onSelChanged = []
		if selChangedCB is not None:
			self.onSelChanged.append(selChangedCB)

		self.l = eListboxPythonMultiContent()  # noqa: E741
		self.epgcache = eEPGCache.getInstance()

		# Clock icon index comes from RecordTimer.isInTimer() and must not be reordered.
		self.clocks = [
			LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock_add.png")),
			LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock_pre.png")),
			LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock.png")),
			LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock_prepost.png")),
			LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock_post.png")),
			LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock_add.png")),
			LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock_pre.png")),
			LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock_zap.png")),
			LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock_prepost.png")),
			LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock_post.png")),
			LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock_add.png")),
			LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock_pre.png")),
			LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock_zaprec.png")),
			LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock_prepost.png")),
			LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock_post.png")),
			LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock_disabled.png")),
			LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock_fallback.png")),
		]
		self.selclocks = [
			LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock_add.png")),
			LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock_selpre.png")),
			LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock.png")),
			LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock_selprepost.png")),
			LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock_selpost.png")),
			LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock_add.png")),
			LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock_selpre.png")),
			LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock_zap.png")),
			LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock_selprepost.png")),
			LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock_selpost.png")),
			LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock_add.png")),
			LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock_selpre.png")),
			LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock_zaprec.png")),
			LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock_selprepost.png")),
			LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock_selpost.png")),
			LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock_disabled.png")),
			LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock_fallback.png")),
		]
		self.autotimericon = LoadPixmap(
			cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock_autotimer.png"))
		self.icetvicon = LoadPixmap(
			cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock_icetv.png"))
		self.catchupicon = LoadPixmap(
			cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/catchup.png"))

		self.wasEntryAutoTimer = False
		self.wasEntryIceTV = False

		self.listHeight = 0
		self.listWidth = 0
		# Skin-provided item height (from itemHeight attribute).
		self.skinItemHeight = 0
		# Skin-provided row count (from NumberOfRows attribute).
		self.numberOfRows = 0
		# Stored on applySkin before setItemsPerPage adjusts the height.
		self.skinListHeight = 0
		# Opt-in minimum row height (from MinimumItemHeight attribute).
		self.minimumItemHeight = 0

	def applySkin(self, desktop, screen):
		if self.skinAttributes is not None:
			attribs = []
			for (attrib, value) in self.skinAttributes:
				if attrib == "itemHeight":
					self.skinItemHeight = parseScale(value)
				elif attrib == "NumberOfRows":
					# Row count specified directly by the skin.
					self.numberOfRows = int(value)
				elif attrib == "MinimumItemHeight":
					self.minimumItemHeight = max(0, int(value))
				else:
					attribs.append((attrib, value))
			self.skinAttributes = attribs
		rc = GUIComponent.applySkin(self, desktop, screen)
		self.skinListHeight = self.listHeight = self.instance.size().height()
		self.listWidth = self.instance.size().width()
		self.setFontsize()
		self.setItemsPerPage()
		return rc

	def setItemsPerPage(self, defaultItemHeight=54):
		ipp = self.epgConfig.itemsperpage.value
		if ipp:
			# Config explicitly sets the number of rows.
			itemHeight = (self.skinListHeight // ipp) if self.skinListHeight > 0 else defaultItemHeight
		elif self.numberOfRows:
			# Fall back to the row count baked into the skin.
			itemHeight = (self.skinListHeight // self.numberOfRows) if self.skinListHeight > 0 else defaultItemHeight
		elif self.skinItemHeight:
			itemHeight = self.skinItemHeight
		else:
			itemHeight = defaultItemHeight

		if itemHeight <= 0:
			itemHeight = defaultItemHeight

		# Opt-in readable rows: enforce a minimum height while keeping only fully visible rows.
		if self.minimumItemHeight and self.skinListHeight > 0:
			itemHeight = min(self.skinListHeight, max(self.minimumItemHeight, itemHeight))

		self.l.setItemHeight(itemHeight)
		self.instance.resize(eSize(self.listWidth, self.skinListHeight // itemHeight * itemHeight))
		self.listHeight = self.instance.size().height()
		self.listWidth = self.instance.size().width()
		self.itemHeight = itemHeight

	def setFontsize(self):
		# Concrete classes implement font setup for their specific columns.
		pass


	def queryEPG(self, queryList):
		try:
			return self.epgcache.lookupEvent(queryList)
		except Exception:
			import traceback
			traceback.print_exc()
			return []

	def getEventFromId(self, service, eventId):
		if self.epgcache is not None and eventId is not None:
			return self.epgcache.lookupEventId(service.ref, eventId)
		return None


	def connectSelectionChanged(self, func):
		if not self.onSelChanged.count(func):
			self.onSelChanged.append(func)

	def disconnectSelectionChanged(self, func):
		self.onSelChanged.remove(func)

	def selectionChanged(self):
		for x in self.onSelChanged:
			if x is not None:
				x()

	def selectionEnabled(self, enabled):
		if self.instance is not None:
			self.instance.setSelectionEnable(enabled)

	def getCurrentIndex(self):
		return self.instance.getCurrentIndex()

	def setCurrentIndex(self, index):
		if self.instance is not None:
			self.instance.moveSelectionTo(index)

	def moveTo(self, direction):
		if self.instance is not None:
			self.instance.moveSelection(direction)

	def getSelectionPosition(self, serviceref=None, activeList=None):
		rowCount = max(self.listHeight // self.itemHeight, 1)
		index = self.l.getCurrentSelectionIndex() % rowCount
		position = self.instance.position()
		return position.x() + self.getSelectionRight(), position.y() + self.itemHeight * index

	def getSelectionRight(self):
		return self.listWidth

	def getIndexFromService(self, serviceref):
		if serviceref is not None:
			refstr = serviceref if isinstance(serviceref, str) else serviceref.toString()
			for index, entry in enumerate(self.list):
				if any(isinstance(x, str) and CompareWithAlternatives(x, refstr) for x in entry[:2]):
					return index
		return None

	def moveToService(self, serviceref):
		if not serviceref:
			return
		newIdx = self.getIndexFromService(serviceref)
		if newIdx is None:
			newIdx = 0
		self.setCurrentIndex(newIdx)

	def getSelectedEventId(self):
		# Single, similar and vertical lists keep the event id in field 1.
		x = self.l.getCurrentSelection()
		return x and x[1]

	def moveToEventId(self, eventId):
		if not eventId:
			return
		for index, x in enumerate(self.list):
			if x[1] == eventId:
				self.instance.moveSelectionTo(index)
				break

	def getCurrent(self):
		# Returns (event, service) for the currently highlighted row.
		tmp = self.l.getCurrentSelection()
		if tmp is None:
			return None, None
		service = ServiceReference(tmp[0])
		eventId = tmp[1]
		event = self.getEventFromId(service, eventId)
		return event, service

	GUI_WIDGET = eListbox


	def getPixmapForEntry(self, service, eventId, beginTime, duration):
		if not beginTime:
			return None
		rec = self.session.nav.RecordTimer.isInTimer(
			eventId, beginTime, duration, eServiceReference(service).toCompareString())
		if rec is not None:
			self.wasEntryAutoTimer = bool(rec[2] & 1)
			self.wasEntryIceTV = bool(rec[2] & 2)
			return rec[1]
		self.wasEntryAutoTimer = False
		self.wasEntryIceTV = False
		return None

	def getIcons(self, clock_types, service, beginTime):
		icons = []
		if clock_types and clock_types in (2, 7, 12):
			if self.wasEntryAutoTimer and self.autotimericon:
				icons.append(self.autotimericon)
			if self.wasEntryIceTV and self.icetvicon:
				icons.append(self.icetvicon)
		if self.detectCatchupAvailable(beginTime, service):
			return [self.catchupicon]
		return icons

	def isIceTV(self, service):
		if hasattr(config.plugins, "icetv"):
			try:
				from enigma import eServiceReference
				from Plugins.SystemPlugins.IceTV.plugin import fetcher
				return fetcher is not None and fetcher.isIceTVEpgChannel(eServiceReference(service))
			except ImportError:
				pass
		return False

	def detectCatchupAvailable(self, stime, service):
		# Returns True if the event is within the catch-up window defined
		# in the service reference string (e.g. "catchupdays=7").
		sref = service.toString() if isinstance(service, eServiceReference) else service
		now = time()
		if stime and "catchupdays=" in sref and stime < now:
			match = re.search(r"catchupdays=(\d*)", sref)
			if match:
				catchup_days = int(match.groups(1)[0])
				if now - stime <= datetime.timedelta(days=catchup_days).total_seconds():
					return True
		return False
class Rect:
	__slots__ = ("x", "y", "w", "h")

	def __init__(self, x, y, width, height):
		self.x = x
		self.y = y
		self.w = width
		self.h = height

	def left(self):
		return self.x

	def top(self):
		return self.y

	def width(self):
		return self.w

	def height(self):
		return self.h


class EPGListGrid(EPGListBase):
	"""EPG list for graphical timeline mode (EPG_TYPE_GRAPH / EPG_TYPE_INFOBARGRAPH)."""

	def __init__(self, session, epgConfig, epgType=EPG_TYPE_GRAPH,
					selChangedCB=None, graphic=False, overjump_empty=False, time_epoch=120):
		EPGListBase.__init__(self, session, selChangedCB)

		sf = getSkinFactor()
		self.type = epgType
		self.epgConfig = epgConfig
		self.graphic = graphic
		self.overjump_empty = overjump_empty

		self.posx, self.posy, self.picx, self.picy, self.gap = skinparameter.get(
			"EpgListIcon", (2, 13, 25, 25, 2) if sf == 1.5 else (1, 11, 23, 23, 1))

		self.cur_event = None
		self.cur_service = None
		self.offs = 0
		self.time_base = None
		self.time_epoch = int(time_epoch)
		self.select_rect = None
		self.event_rect = None
		self.service_rect = None
		self.listSizeWidth = None
		self.currentlyPlaying = None
		self.showPicon = False
		self.showServiceTitle = True
		self.showServiceNumber = False
		self.listRows = 8
		self.listFirstServiceIndex = 0
		self.serviceList = ()
		self.listHeight = 0
		self.listWidth = 0
		self.skinItemHeight = 0
		self.numberOfRows = 0
		self.skinListHeight = 0

		# Colour defaults.
		self.foreColor = 0xffffff
		self.foreColorSelected = 0xffffff
		self.backColor = 0x2D455E
		self.backColorSelected = 0xd69600
		self.foreColorNow = 0xffffff
		self.foreColorNowSelected = 0xffffff
		self.backColorNow = 0x00825F
		self.backColorNowSelected = 0xd69600
		self.foreColorServiceNow = 0xffffff
		self.backColorServiceNow = 0x00825F
		self.foreColorService = 0xffffff
		self.backColorService = 0x2D455E
		self.foreColorRecord = 0xffffff
		self.backColorRecord = 0xd13333
		self.foreColorRecordSelected = 0xffffff
		self.backColorRecordSelected = 0x9e2626
		self.foreColorZap = 0xffffff
		self.backColorZap = 0x669466
		self.foreColorZapSelected = 0xffffff
		self.backColorZapSelected = 0x436143
		self.borderColor = 0xC0C0C0
		self.borderColorService = 0xC0C0C0
		self.skinUsingForeColorByTime = False
		self.skinUsingBackColorByTime = False

		self.serviceFontNameGraph = "Regular"
		self.eventFontNameGraph = "Regular"
		self.serviceFontSizeGraph = int(20 * sf)
		self.eventFontSizeGraph = int(18 * sf)
		self.serviceFontNameInfobar = "Regular"
		self.eventFontNameInfobar = "Regular"
		self.serviceFontSizeInfobar = int(20 * sf)
		self.eventFontSizeInfobar = int(22 * sf)

		self.serviceBorderWidth = 1
		self.serviceNamePadding = 3
		self.serviceNumberPadding = 9
		self.eventBorderWidth = 1
		self.eventNamePadding = 3
		self.eventNameAlign = "left"
		self.eventNameWrap = "yes"

		# Lazy-loaded graphic pixmaps.
		self.nowEvPix = None
		self.nowSelEvPix = None
		self.othEvPix = None
		self.selEvPix = None
		self.othServPix = None
		self.nowServPix = None
		self.recEvPix = None
		self.recSelEvPix = None
		self.recordingEvPix = None
		self.zapEvPix = None
		self.zapSelEvPix = None
		self.borderTopPix = None
		self.borderBottomPix = None
		self.borderLeftPix = None
		self.borderRightPix = None
		self.borderSelectedTopPix = None
		self.borderSelectedBottomPix = None
		self.borderSelectedLeftPix = None
		self.borderSelectedRightPix = None
		self.InfoPix = None
		self.selInfoPix = None
		self.graphicsloaded = False
		self.picon_size = eSize(0, 0)

		self.list = []

		self.l.setBuildFunc(self.buildGraphEntry)


	GUI_WIDGET = eListbox

	def postWidgetCreate(self, instance):
		self.setOverjump_Empty(self.overjump_empty)
		instance.setWrapAround(True)
		instance.selectionChanged.get().append(self.serviceChanged)
		instance.setContent(self.l)
		self.l.setSelectionClip(eRect(0, 0, 0, 0), False)

	def preWidgetRemove(self, instance):
		instance.selectionChanged.get().remove(self.serviceChanged)
		instance.setContent(None)

	def selectionEnabled(self, enabled):
		if self.instance is not None:
			self.instance.setSelectionEnable(enabled)

	def isSelectable(self, service, service_name, events, picon, channel):
		return bool(events and len(events))

	def setOverjump_Empty(self, overjump_empty):
		if overjump_empty:
			self.l.setSelectableFunc(self.isSelectable)
		else:
			self.l.setSelectableFunc(None)


	def applySkin(self, desktop, screen):
		if self.skinAttributes is not None:
			attribs = []
			self.skinUsingForeColorByTime = False
			self.skinUsingBackColorByTime = False
			for (attrib, value) in self.skinAttributes:
				if attrib == "ServiceFontGraphical":
					font = parseFont(value, ((1, 1), (1, 1)))
					self.serviceFontNameGraph = font.family
					self.serviceFontSizeGraph = font.pointSize
				elif attrib == "EntryFontGraphical":
					font = parseFont(value, ((1, 1), (1, 1)))
					self.eventFontNameGraph = font.family
					self.eventFontSizeGraph = font.pointSize
				elif attrib == "ServiceFontInfobar":
					font = parseFont(value, ((1, 1), (1, 1)))
					self.serviceFontNameInfobar = font.family
					self.serviceFontSizeInfobar = font.pointSize
				elif attrib == "EventFontInfobar":
					font = parseFont(value, ((1, 1), (1, 1)))
					self.eventFontNameInfobar = font.family
					self.eventFontSizeInfobar = font.pointSize
				elif attrib == "EntryFontAlignment":
					self.eventNameAlign = value
				elif attrib == "EntryFontWrap":
					self.eventNameWrap = value
				elif attrib == "ServiceForegroundColor":
					self.foreColorService = parseColor(value).argb()
				elif attrib == "ServiceForegroundColorNow":
					self.foreColorServiceNow = parseColor(value).argb()
				elif attrib == "ServiceBackgroundColor":
					self.backColorService = parseColor(value).argb()
				elif attrib == "ServiceBackgroundColorNow":
					self.backColorServiceNow = parseColor(value).argb()
				elif attrib == "EntryForegroundColor":
					self.foreColor = parseColor(value).argb()
				elif attrib == "EntryForegroundColorSelected":
					self.foreColorSelected = parseColor(value).argb()
				elif attrib == "EntryBackgroundColor":
					self.backColor = parseColor(value).argb()
				elif attrib == "EntryBackgroundColorSelected":
					self.backColorSelected = parseColor(value).argb()
				elif attrib == "EntryBackgroundColorNow":
					self.backColorNow = parseColor(value).argb()
					self.skinUsingBackColorByTime = True
				elif attrib == "EntryBackgroundColorNowSelected":
					self.backColorNowSelected = parseColor(value).argb()
					self.skinUsingBackColorByTime = True
				elif attrib == "EntryForegroundColorNow":
					self.foreColorNow = parseColor(value).argb()
					self.skinUsingForeColorByTime = True
				elif attrib == "EntryForegroundColorNowSelected":
					self.foreColorNowSelected = parseColor(value).argb()
					self.skinUsingForeColorByTime = True
				elif attrib == "RecordForegroundColor":
					self.foreColorRecord = parseColor(value).argb()
				elif attrib == "RecordForegroundColorSelected":
					self.foreColorRecordSelected = parseColor(value).argb()
				elif attrib == "RecordBackgroundColor":
					self.backColorRecord = parseColor(value).argb()
				elif attrib == "RecordBackgroundColorSelected":
					self.backColorRecordSelected = parseColor(value).argb()
				elif attrib == "ZapForegroundColor":
					self.foreColorZap = parseColor(value).argb()
				elif attrib == "ZapBackgroundColor":
					self.backColorZap = parseColor(value).argb()
				elif attrib == "ZapForegroundColorSelected":
					self.foreColorZapSelected = parseColor(value).argb()
				elif attrib == "ZapBackgroundColorSelected":
					self.backColorZapSelected = parseColor(value).argb()
				elif attrib == "ServiceBorderColor":
					self.borderColorService = parseColor(value).argb()
				elif attrib == "ServiceBorderWidth":
					self.serviceBorderWidth = int(value)
				elif attrib == "ServiceNamePadding":
					self.serviceNamePadding = int(value)
				elif attrib == "ServiceNumberPadding":
					self.serviceNumberPadding = int(value)
				elif attrib == "EntryBorderColor":
					self.borderColor = parseColor(value).argb()
				elif attrib == "EventBorderWidth":
					self.eventBorderWidth = int(value)
				elif attrib == "EventNamePadding":
					self.eventNamePadding = int(value)
				elif attrib == "NumberOfRows":
					self.numberOfRows = int(value)
				elif attrib == "itemHeight":
					self.skinItemHeight = int(value)
				elif attrib == "MinimumItemHeight":
					self.minimumItemHeight = max(0, int(value))
				else:
					attribs.append((attrib, value))
			self.skinAttributes = attribs
		rc = GUIComponent.applySkin(self, desktop, screen)
		self.skinListHeight = self.listHeight = self.instance.size().height()
		self.listWidth = self.instance.size().width()
		self.setFontsize()
		self.setItemsPerPage()
		return rc


	def setFontsize(self):
		if self.type == EPG_TYPE_INFOBARGRAPH:
			self.l.setFont(0, gFont(self.serviceFontNameInfobar,
									self.serviceFontSizeInfobar + self.epgConfig.servfs.value))
			self.l.setFont(1, gFont(self.eventFontNameInfobar,
									self.eventFontSizeInfobar + self.epgConfig.eventfs.value))
		else:
			self.l.setFont(0, gFont(self.serviceFontNameGraph,
									self.serviceFontSizeGraph + self.epgConfig.servfs.value))
			self.l.setFont(1, gFont(self.eventFontNameGraph,
									self.eventFontSizeGraph + self.epgConfig.eventfs.value))

	def setItemsPerPage(self, defaultItemHeight=None):
		sf = getSkinFactor()
		if defaultItemHeight is None:
			defaultItemHeight = int(54 * sf)

		ipp = self.epgConfig.itemsperpage.value
		if ipp and self.skinListHeight > 0:
			itemHeight = self.skinListHeight // ipp
		elif self.numberOfRows:
			itemHeight = (self.skinListHeight // self.numberOfRows) if self.skinListHeight > 0 else defaultItemHeight
		elif self.skinItemHeight:
			itemHeight = self.skinItemHeight
		else:
			itemHeight = defaultItemHeight
		if itemHeight <= 0:
			itemHeight = defaultItemHeight

		# Height switch: shrink rows if the configured height allows three or two sub-rows.
		# Only applies to GRAPH mode, not INFOBARGRAPH.
		if (self.type == EPG_TYPE_GRAPH
				and self.epgConfig.heightswitch.value
				and ipp and self.skinListHeight > 0):
			base = self.skinListHeight // ipp
			if (base // 3) >= 27:
				candidate = base // 3
			elif (base // 2) >= 27:
				candidate = base // 2
			else:
				candidate = int(27 * sf)
			if candidate < itemHeight:
				itemHeight = candidate
			else:
				if (base * 3) <= 45:
					itemHeight = base * 3
				elif (base * 2) <= 45:
					itemHeight = base * 2
				else:
					itemHeight = int(45 * sf)

		if self.numberOfRows:
			itemHeight = self.skinListHeight // self.numberOfRows

		itemHeight = int(itemHeight)

		# Opt-in readable rows: enforce a minimum height while keeping only fully visible rows.
		if self.minimumItemHeight and self.skinListHeight > 0:
			itemHeight = min(self.skinListHeight, max(self.minimumItemHeight, itemHeight))

		self.l.setItemHeight(itemHeight)
		self.instance.resize(eSize(self.listWidth, self.skinListHeight // itemHeight * itemHeight))
		self.listHeight = self.instance.size().height()
		self.listWidth = self.instance.size().width()
		self.itemHeight = itemHeight
		self.listRows = self.listHeight // itemHeight

	def recalcEntrySize(self):
		esize = self.l.getItemSize()
		width = esize.width()
		height = esize.height()
		self.listSizeWidth = width

		servicew = 0
		piconw = 0
		if self.showServiceTitle:
			servicew = self.epgConfig.servicewidth.value
		if self.showPicon:
			piconw = self.epgConfig.piconwidth.value

		w = piconw + servicew
		self.service_rect = Rect(0, 0, w, height)
		self.event_rect = Rect(w, 0, width - w, height)
		piconHeight = height - 2 * self.serviceBorderWidth
		piconWidth = min(piconw, w - 2 * self.serviceBorderWidth)
		self.picon_size = eSize(piconWidth, piconHeight)

	def setShowServiceMode(self, value):
		self.showServiceNumber = "servicenumber" in value
		self.showServiceTitle = "servicename" in value
		self.showPicon = "picon" in value
		self.recalcEntrySize()
		self.selEntry(0)

	def setEpoch(self, epoch):
		self.offs = 0
		self.time_epoch = epoch
		self.fillGraphEPG(None)

	def resetOffset(self):
		self.offs = 0

	def getSelectionRight(self):
		return self.select_rect.x + self.select_rect.w if self.select_rect else self.listWidth

	def getChannelNumber(self, service):
		if hasattr(service, "ref") and service.ref and '0:0:0:0:0:0:0:0:0' not in service.ref.toString():
			num = service.ref.getChannelNum()
			if num is not None:
				return num
		return None

	def setCurrentlyPlaying(self, serviceref):
		self.currentlyPlaying = serviceref


	def getEventRect(self):
		rc = self.event_rect
		if rc:
			return Rect(
				rc.left() + (self.instance and self.instance.position().x() or 0),
				rc.top(), rc.width(), rc.height())

	def getServiceRect(self):
		rc = self.service_rect
		if rc:
			return Rect(
				rc.left() + (self.instance and self.instance.position().x() or 0),
				rc.top(), rc.width(), rc.height())

	def getTimeEpoch(self):
		return self.time_epoch

	def getTimeBase(self):
		try:
			return int(self.time_base) + int(self.offs) * int(self.time_epoch) * 60
		except Exception:
			return self.time_base


	def calcEntryPosAndWidthHelper(self, stime, duration, start, end, width):
		xpos = (stime - start) * width // (end - start)
		ewidth = (stime + duration - start) * width // (end - start)
		ewidth -= xpos
		if xpos < 0:
			ewidth += xpos
			xpos = 0
		if (xpos + ewidth) > width:
			ewidth = width - xpos
		return xpos, ewidth

	def calcEntryPosAndWidth(self, event_rect, time_base, time_epoch, ev_start, ev_duration):
		xpos, width = self.calcEntryPosAndWidthHelper(
			ev_start, ev_duration, time_base, time_base + time_epoch * 60, event_rect.width())
		return xpos + event_rect.left(), width


	def buildGraphEntry(self, service, service_name, events, picon, channel):
		if self.listSizeWidth != self.l.getItemSize().width():
			self.recalcEntrySize()
		r1 = self.service_rect
		r2 = self.event_rect
		left = r2.x
		top = r2.y
		width = r2.w
		height = r2.h
		selected = self.cur_service is not None and self.cur_service[0] == service
		res = [None]

		serviceForeColor = self.foreColorService
		serviceBackColor = self.backColorService
		bgpng = self.othServPix
		if CompareWithAlternatives(service, self.currentlyPlaying and self.currentlyPlaying.toString()):
			serviceForeColor = self.foreColorServiceNow
			serviceBackColor = self.backColorServiceNow
			bgpng = self.nowServPix

		if bgpng is not None and self.graphic:
			serviceBackColor = None
			res.append(MultiContentEntryPixmapAlphaBlend(
				pos=(r1.x + self.serviceBorderWidth, r1.y + self.serviceBorderWidth),
				size=(r1.w - 2 * self.serviceBorderWidth, r1.h - 2 * self.serviceBorderWidth),
				png=bgpng, flags=BT_SCALE))
		else:
			res.append(MultiContentEntryText(
				pos=(r1.x, r1.y), size=(r1.w, r1.h),
				font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
				text="",
				color=serviceForeColor, color_sel=serviceForeColor,
				backcolor=serviceBackColor, backcolor_sel=serviceBackColor,
				border_width=self.serviceBorderWidth, border_color=self.borderColorService))

		displayPicon = None
		piconWidth = 0
		if self.showPicon:
			if picon is None:
				picon = getChannelSelectionPiconName(service)
				curIdx = self.l.getCurrentSelectionIndex()
				self.list[curIdx] = (service, service_name, events, picon, channel)
			if picon != "":
				displayPicon = loadPNG(picon)
			if displayPicon is not None:
				piconWidth = self.picon_size.width()
				res.append(MultiContentEntryPixmapAlphaBlend(
					pos=(r1.x + self.serviceBorderWidth, r1.y + self.serviceBorderWidth),
					size=(piconWidth, self.picon_size.height()),
					png=displayPicon,
					backcolor=None, backcolor_sel=None,
					flags=BT_SCALE | BT_KEEP_ASPECT_RATIO))
			elif not self.showServiceTitle:
				piconWidth = self.picon_size.width()

		channelWidth = 0
		if self.showServiceNumber:
			if not isinstance(channel, int):
				channel = self._getChannelNumber(channel)
			if channel:
				namefontflag = RT_HALIGN_CENTER | RT_VALIGN_CENTER
				font = gFont(self.serviceFontNameGraph,
								self.serviceFontSizeGraph + self.epgConfig.servfs.value)
				channelWidth = getTextBoundarySize(
					self.instance, font, self.instance.size(),
					(channel < 10000) and "0000" or str(channel)).width()
				res.append(MultiContentEntryText(
					pos=(r1.x + self.serviceNamePadding + piconWidth + self.serviceNamePadding,
							r1.y + self.serviceBorderWidth),
					size=(channelWidth, r1.h - 2 * self.serviceBorderWidth),
					font=0, flags=namefontflag,
					text=str(channel),
					color=serviceForeColor, color_sel=serviceForeColor,
					backcolor=serviceBackColor, backcolor_sel=serviceBackColor))

		if self.showServiceTitle or displayPicon is None:
			namefont = 0
			namefontflag = int(config.epgselection.grid.servicename_alignment.value)
			namewidth = r1.w - channelWidth - piconWidth
			res.append(MultiContentEntryText(
				pos=(r1.x + self.serviceNamePadding + piconWidth + self.serviceNamePadding
						+ channelWidth + self.serviceNumberPadding,
						r1.y + self.serviceBorderWidth),
				size=(namewidth - 3 * (self.serviceBorderWidth + self.serviceNamePadding),
						r1.h - 2 * self.serviceBorderWidth),
				font=namefont, flags=namefontflag,
				text=service_name,
				color=serviceForeColor, color_sel=serviceForeColor,
				backcolor=serviceBackColor, backcolor_sel=serviceBackColor))

		if self.isIceTV(service) and config.epg.eit.value and self.icetvicon:
			iceicon_size = self.icetvicon.size()
			res.append(MultiContentEntryPixmapAlphaBlend(
				pos=(r1.x + r1.w - self.serviceBorderWidth - iceicon_size.width(),
						r1.y + r1.h - self.serviceBorderWidth - iceicon_size.height()),
				size=(iceicon_size.width(), iceicon_size.height()),
				png=self.icetvicon, backcolor=None, backcolor_sel=None))

		# Service borders (graphic mode).
		for (pixmap, pos, size) in (
				(self.borderTopPix, (r1.x, r1.y), (r1.w, self.serviceBorderWidth)),
				(self.borderTopPix, (r2.x, r2.y), (r2.w, self.eventBorderWidth)),
				(self.borderBottomPix, (r1.x, r1.h - self.serviceBorderWidth), (r1.w, self.serviceBorderWidth)),
				(self.borderBottomPix, (r2.x, r2.h - self.eventBorderWidth), (r2.w, self.eventBorderWidth)),
				(self.borderLeftPix, (r1.x, r1.y), (self.serviceBorderWidth, r1.h)),
				(self.borderLeftPix, (r2.x, r2.y), (self.eventBorderWidth, r2.h)),
				(self.borderRightPix, (r1.w - self.serviceBorderWidth, r1.x), (self.serviceBorderWidth, r1.h)),
				(self.borderRightPix, (r2.x + r2.w - self.eventBorderWidth, r2.y), (self.eventBorderWidth, r2.h)),
		):
			if pixmap is not None and self.graphic:
				res.append(MultiContentEntryPixmapAlphaTest(
					pos=pos, size=size, png=pixmap, flags=BT_SCALE))

		# Default event area background.
		if self.graphic:
			areaPix = self.selEvPix if selected else self.othEvPix
			if areaPix:
				res.append(MultiContentEntryPixmapAlphaTest(
					pos=(r2.x + self.eventBorderWidth, r2.y + self.eventBorderWidth),
					size=(r2.w - 2 * self.eventBorderWidth, r2.h - 2 * self.eventBorderWidth),
					png=areaPix, flags=BT_SCALE))
		else:
			res.append(MultiContentEntryText(
				pos=(left, top), size=(width, height),
				font=1, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
				text="", color=None, color_sel=None,
				backcolor=self.backColor, backcolor_sel=self.backColorSelected,
				border_width=self.eventBorderWidth, border_color=self.borderColor))

		if events:
			start = self.time_base + self.offs * self.time_epoch * 60
			end = start + self.time_epoch * 60
			now = time()
			infowidth = self.epgConfig.infowidth.value

			for ev in events:
				stime = ev[2]
				duration = ev[3]
				xpos, ewidth = self.calcEntryPosAndWidthHelper(stime, duration, start, end, width)
				clock_types = self.getPixmapForEntry(service, ev[0], stime, duration)

				isNow = stime <= now < (stime + duration)
				isRec = clock_types is not None and clock_types in (2, 12)
				isZap = clock_types is not None and clock_types == 7

				if isNow:
					if isRec:
						foreColor, backColor = self.foreColorRecord, self.backColorRecord
						foreColorSel, backColorSel = self.foreColorRecordSelected, self.backColorRecordSelected
					else:
						foreColor, backColor = self.foreColorNow, self.backColorNow
						foreColorSel, backColorSel = self.foreColorNowSelected, self.backColorNowSelected
				elif isRec:
					foreColor, backColor = self.foreColorRecord, self.backColorRecord
					foreColorSel, backColorSel = self.foreColorRecordSelected, self.backColorRecordSelected
				elif isZap:
					foreColor, backColor = self.foreColorZap, self.backColorZap
					foreColorSel, backColorSel = self.foreColorZapSelected, self.backColorZapSelected
				else:
					foreColor, backColor = self.foreColor, self.backColor
					foreColorSel, backColorSel = self.foreColorSelected, self.backColorSelected

				isSelected = selected and self.select_rect is not None and self.select_rect.x == xpos + left

				if isSelected:
					clocks = self.selclocks[clock_types] if clock_types is not None else None
					bTopPix = self.borderSelectedTopPix
					bLeftPix = self.borderSelectedLeftPix
					bBottomPix = self.borderSelectedBottomPix
					bRightPix = self.borderSelectedRightPix
					infoPix = self.selInfoPix
					if isRec:
						bgpng = self.recSelEvPix
					elif isNow:
						bgpng = self.nowSelEvPix
					else:
						bgpng = self.selEvPix
				else:
					clocks = self.clocks[clock_types] if clock_types is not None else None
					bTopPix = self.borderTopPix
					bLeftPix = self.borderLeftPix
					bBottomPix = self.borderBottomPix
					bRightPix = self.borderRightPix
					infoPix = self.InfoPix
					if isNow:
						if clock_types is not None and clock_types in (2, 12):
							bgpng = self.recordingEvPix
						else:
							bgpng = self.nowEvPix
					else:
						if isRec:
							bgpng = self.recEvPix
						elif isZap:
							bgpng = self.zapEvPix
						else:
							bgpng = self.othEvPix

				# Event background.
				if bgpng is not None and self.graphic:
					backColor = backColorSel = None
					res.append(MultiContentEntryPixmapAlphaTest(
						pos=(left + xpos + self.eventBorderWidth, top + self.eventBorderWidth),
						size=(ewidth - 2 * self.eventBorderWidth, height - 2 * self.eventBorderWidth),
						png=bgpng, flags=BT_SCALE))
				else:
					res.append(MultiContentEntryText(
						pos=(left + xpos, top), size=(ewidth, height),
						font=1, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
						text="", color=None, color_sel=None,
						backcolor=backColor, backcolor_sel=backColorSel,
						border_width=self.eventBorderWidth, border_color=self.borderColor))

				# Event text.
				evX = left + xpos + self.eventBorderWidth + self.eventNamePadding
				evY = top + self.eventBorderWidth
				evW = ewidth - 2 * (self.eventBorderWidth + self.eventNamePadding)
				evH = height - 2 * self.eventBorderWidth
				if evW < infowidth and infoPix is not None:
					res.append(MultiContentEntryPixmapAlphaBlend(
						pos=(evX, evY), size=(evW, evH), png=infoPix))
				else:
					res.append(MultiContentEntryText(
						pos=(evX, evY), size=(evW, evH),
						font=1, flags=int(config.epgselection.grid.event_alignment.value),
						text=ev[1],
						color=foreColor, color_sel=foreColorSel,
						backcolor=backColor, backcolor_sel=backColorSel))

				# Event borders (graphic mode).
				for (pixmap, pos, size) in (
						(bTopPix, (left + xpos, top), (ewidth, self.eventBorderWidth)),
						(bBottomPix, (left + xpos, height - self.eventBorderWidth), (ewidth, self.eventBorderWidth)),
						(bLeftPix, (left + xpos, top), (self.eventBorderWidth, height)),
						(bRightPix, (left + xpos + ewidth - self.eventBorderWidth, top), (self.eventBorderWidth, height)),
				):
					if pixmap is not None and self.graphic:
						res.append(MultiContentEntryPixmapAlphaTest(
							pos=pos, size=size, png=pixmap, flags=BT_SCALE))

				# Recording icon.
				rec_icon_height_cfg = config.epgselection.grid.rec_icon_height.value
				if ewidth > 23 and rec_icon_height_cfg != "hide":
					if rec_icon_height_cfg == "middle":
						RecIconY = top + height // 2 - self.posy
					elif rec_icon_height_cfg == "top":
						RecIconY = top + self.gap
					else:
						RecIconY = top + height - self.picy - self.gap

					if clocks is not None:
						if clock_types in (1, 6, 11):
							pos = (left + xpos + ewidth - self.picx, RecIconY)
						elif clock_types in (5, 10, 15):
							pos = (left + xpos - self.picx - self.posx, RecIconY)
						else:
							pos = (left + xpos + ewidth - self.picx - self.posx, RecIconY)
						res.append(MultiContentEntryPixmapAlphaBlend(
							pos=pos, size=(self.picx, self.picy), png=clocks))
					else:
						pos = (left + xpos + ewidth - self.picx - self.posx, RecIconY)

					for typeIcon in self.getIcons(clock_types, service, ev[0]):
						res.append(MultiContentEntryPixmapAlphaBlend(
							pos=(pos[0] - self.picx - self.gap, pos[1]),
							size=(self.picx, self.picy), png=typeIcon))

		return res


	def getCurrent(self):
		if self.cur_service is None:
			return None, None
		events = self.cur_service[2]
		refstr = self.cur_service[0]
		try:
			if self.cur_event is None or not events or self.cur_event > len(events) - 1:
				return None, ServiceReference(refstr)
			ev = events[self.cur_event]
			service = ServiceReference(refstr)
			event = self.getEventFromId(service, ev[0])
			return event, service
		except Exception:
			return None, ServiceReference(refstr)

	def serviceChanged(self):
		cur_sel = self.l.getCurrentSelection()
		if cur_sel:
			self.findBestEvent()

	def findBestEvent(self, getnow=False):
		old_service = self.cur_service
		cur_service = self.cur_service = self.l.getCurrentSelection()
		time_base = self.getTimeBase()
		now = last_time = time()
		if old_service and self.cur_event is not None:
			try:
				events = old_service[2]
				cur_event = events[self.cur_event]
				last_time = cur_event[2]
			except Exception:
				pass
		if cur_service:
			self.cur_event = 0
			events = cur_service[2]
			best = None
			if events and len(events):
				best_diff = 0
				for idx, event in enumerate(events):
					ev_time = event[2]
					ev_end_time = event[2] + event[3]
					if ev_time < time_base:
						ev_time = time_base
					diff = abs(ev_time - last_time)
					if best is None or diff < best_diff:
						best = idx
						best_diff = diff
					if ev_end_time < now and getnow:
						best = idx + 1
					if best is not None and ev_end_time > now and (ev_time > last_time or (getnow and ev_time < now)):
						break
			self.cur_event = best
		self.selEntry(0)

	def selEntry(self, dir, visible=True):
		cur_service = self.cur_service
		self.recalcEntrySize()
		valid_event = self.cur_event is not None
		now = time() - int(config.epg.histminutes.value) * 60

		if cur_service:
			update = True
			entries = cur_service[2]
			if dir == 0:
				update = False
			elif dir == +1:
				if valid_event and self.cur_event + 1 < len(entries):
					self.cur_event += 1
				else:
					self.offs += 1
					self.fillGraphEPG(None)
					return True
			elif dir == -1:
				if valid_event and self.cur_event - 1 >= 0:
					self.cur_event -= 1
				elif self.offs > 0:
					self.offs -= 1
					self.fillGraphEPG(None)
					return True
				elif self.time_base > time():
					self.time_base -= self.time_epoch * 60
					self.fillGraphEPG(None)
					return True
				elif self.time_base > now and valid_event and cur_service[2][0][2] <= self.time_base:
					self.time_base -= self.time_epoch * 60
					self.fillGraphEPG(None, self.time_base)
					return True
			elif dir == +2:
				self.offs += 1
				self.fillGraphEPG(None)
				return True
			elif dir == -2:
				if self.offs > 0:
					self.offs -= 1
					self.fillGraphEPG(None)
					return True
				elif self.time_base > time():
					self.time_base -= self.time_epoch * 60
					self.fillGraphEPG(None)
					return True
				elif self.time_base > now and valid_event and cur_service[2][0][2] <= self.time_base:
					self.time_base -= self.time_epoch * 60
					self.fillGraphEPG(None, self.time_base)
					return True
			elif dir == +24:
				self.time_base += 86400
				self.fillGraphEPG(None, self.time_base)
				return True
			elif dir == -24:
				if (self.time_base - 86400) > now - now % (int(self.epgConfig.roundto.value) * 60):
					self.time_base -= 86400
					getnow = False
				else:
					self.offs = 0
					self.time_base = now - now % (int(self.epgConfig.roundto.value) * 60)
					getnow = True
				self.fillGraphEPG(None, self.time_base, getnow)
				return True

		if cur_service and valid_event and (self.cur_event + 1 <= len(entries)):
			entry = entries[self.cur_event]
			time_base = self.time_base + self.offs * self.time_epoch * 60
			xpos, width = self.calcEntryPosAndWidth(
				self.event_rect, time_base, self.time_epoch, entry[2], entry[3])
			self.select_rect = Rect(xpos, 0, width, self.event_rect.height())
			self.l.setSelectionClip(eRect(xpos, 0, width, self.event_rect.h), visible and update)
		else:
			self.select_rect = self.event_rect
			self.l.setSelectionClip(
				eRect(self.event_rect.x, self.event_rect.y, self.event_rect.w, self.event_rect.h), False)
		self.selectionChanged()
		return False

	def getIndexFromService(self, serviceref):
		if serviceref is not None:
			for x in range(len(self.list)):
				if CompareWithAlternatives(self.list[x][0], serviceref.toString()):
					return x
				if CompareWithAlternatives(self.list[x][1], serviceref.toString()):
					return x
		return 0

	def moveToService(self, serviceref):
		if not serviceref:
			return
		self.setCurrentIndex(self.getIndexFromService(serviceref))


	def nextPage(self, selectFirstService=False):
		if self.listFirstServiceIndex + self.listRows < len(self.serviceList):
			self.listFirstServiceIndex += self.listRows
		else:
			self.listFirstServiceIndex = 0
		self.fillGraphEPG(None)
		if selectFirstService:
			self.setCurrentIndex(0)

	def prevPage(self, selectLastService=False):
		if self.listFirstServiceIndex - self.listRows >= 0:
			self.listFirstServiceIndex -= self.listRows
		else:
			self.listFirstServiceIndex = int(len(self.serviceList) / self.listRows) * self.listRows
		self.fillGraphEPG(None)
		if selectLastService:
			if self.listFirstServiceIndex + self.listRows <= len(self.serviceList):
				self.setCurrentIndex(self.listRows - 1)
			else:
				self.setCurrentIndex(len(self.serviceList) - self.listFirstServiceIndex - 1)

	def moveUp(self):
		idx = self.getCurrentIndex() - 1
		if idx < 0:
			self.prevPage(True)
		else:
			self.setCurrentIndex(idx)

	def moveDown(self):
		idx = self.getCurrentIndex() + 1
		if idx >= self.listRows or self.listFirstServiceIndex + idx >= len(self.serviceList):
			self.nextPage(True)
		else:
			self.setCurrentIndex(idx)


	def fillGraphEPG(self, services, stime=None, getnow=False, current_service=None):
		if not self.graphicsloaded and self.graphic:
			self.nowEvPix = loadPNG(resolveFilename(SCOPE_GUISKIN, "epg/CurrentEvent.png"))
			self.nowSelEvPix = loadPNG(resolveFilename(SCOPE_GUISKIN, "epg/SelectedCurrentEvent.png"))
			self.othEvPix = loadPNG(resolveFilename(SCOPE_GUISKIN, "epg/OtherEvent.png"))
			self.selEvPix = loadPNG(resolveFilename(SCOPE_GUISKIN, "epg/SelectedEvent.png"))
			self.othServPix = loadPNG(resolveFilename(SCOPE_GUISKIN, "epg/OtherService.png"))
			self.nowServPix = loadPNG(resolveFilename(SCOPE_GUISKIN, "epg/CurrentService.png"))
			self.recEvPix = loadPNG(resolveFilename(SCOPE_GUISKIN, "epg/RecordEvent.png"))
			self.recSelEvPix = loadPNG(resolveFilename(SCOPE_GUISKIN, "epg/SelectedRecordEvent.png"))
			self.recordingEvPix = loadPNG(resolveFilename(SCOPE_GUISKIN, "epg/RecordingEvent.png"))
			self.zapEvPix = loadPNG(resolveFilename(SCOPE_GUISKIN, "epg/ZapEvent.png"))
			self.zapSelEvPix = loadPNG(resolveFilename(SCOPE_GUISKIN, "epg/SelectedZapEvent.png"))
			self.borderTopPix = loadPNG(resolveFilename(SCOPE_GUISKIN, "epg/BorderTop.png"))
			self.borderBottomPix = loadPNG(resolveFilename(SCOPE_GUISKIN, "epg/BorderBottom.png"))
			self.borderLeftPix = loadPNG(resolveFilename(SCOPE_GUISKIN, "epg/BorderLeft.png"))
			self.borderRightPix = loadPNG(resolveFilename(SCOPE_GUISKIN, "epg/BorderRight.png"))
			self.borderSelectedTopPix = loadPNG(resolveFilename(SCOPE_GUISKIN, "epg/SelectedBorderTop.png"))
			self.borderSelectedBottomPix = loadPNG(resolveFilename(SCOPE_GUISKIN, "epg/SelectedBorderBottom.png"))
			self.borderSelectedLeftPix = loadPNG(resolveFilename(SCOPE_GUISKIN, "epg/SelectedBorderLeft.png"))
			self.borderSelectedRightPix = loadPNG(resolveFilename(SCOPE_GUISKIN, "epg/SelectedBorderRight.png"))
		if not self.graphicsloaded:
			self.InfoPix = loadPNG(resolveFilename(SCOPE_GUISKIN, "epg/information.png"))
			self.selInfoPix = loadPNG(resolveFilename(SCOPE_GUISKIN, "epg/SelectedInformation.png"))
			self.graphicsloaded = True

		test = ["XRnITBD"]

		if stime is not None:
			self.time_base = int(stime)
		if services is None:
			time_base = self.time_base + self.offs * self.time_epoch * 60
			self.time_base = time_base
			self.offs = 0
			endRow = min(self.listFirstServiceIndex + self.listRows, len(self.serviceList))
			for i in range(self.listFirstServiceIndex, endRow):
				test.append((self.serviceList[i].ref.toString(), 0, self.time_base, self.time_epoch))
		else:
			self.cur_event = None
			self.cur_service = None
			self.listFirstServiceIndex = 0
			self.serviceList = services
			if current_service is not None:
				for i in range(len(self.serviceList)):
					if self.serviceList[i].ref == current_service:
						self.listFirstServiceIndex = int(i / self.listRows) * self.listRows
						break
			endRow = min(self.listFirstServiceIndex + self.listRows, len(self.serviceList))
			for i in range(self.listFirstServiceIndex, endRow):
				test.append((self.serviceList[i].ref.toString(), 0, self.time_base, self.time_epoch))

		epg_data = self.queryEPG(test)
		self.list = []
		tmp_list = None
		service = ""
		sname = ""
		serviceIdx = self.listFirstServiceIndex

		for x in epg_data:
			if service != x[0]:
				if tmp_list is not None:
					self.list.append((
						service, sname,
						tmp_list[0][0] is not None and tmp_list or None,
						None, self.serviceList[serviceIdx]))
					serviceIdx += 1
				service = x[0]
				sname = x[1]
				tmp_list = []
			tmp_list.append((x[2], x[3], x[4], x[5]))

		if tmp_list and len(tmp_list):
			self.list.append((
				service, sname,
				tmp_list[0][0] is not None and tmp_list or None,
				None, self.serviceList[serviceIdx]))
			serviceIdx += 1

		# Fill rows with empty entries for services without EPG data.
		while serviceIdx < endRow:
			self.list.append((
				self.serviceList[serviceIdx].ref.toString(),
				self.serviceList[serviceIdx].getServiceName(),
				None, None, self.serviceList[serviceIdx]))
			serviceIdx += 1

		self.l.setList(self.list)
		self.findBestEvent(getnow)


	def _getChannelNumber(self, service):
		if hasattr(service, "ref") and service.ref and "0:0:0:0:0:0:0:0:0" not in service.ref.toString():
			num = service.ref.getChannelNum()
			if num is not None:
				return num
		return None


class TimelineText(GUIComponent):
	"""Timeline ruler widget for the graph EPG screen.

	Accepts the same skin attributes as the original in EpgListNEW.py.
	"""

	def __init__(self, epgType=EPG_TYPE_GRAPH, graphic=False):
		GUIComponent.__init__(self)
		self.type = epgType
		self.graphic = graphic
		self.l = eListboxPythonMultiContent()
		self.l.setSelectionClip(eRect(0, 0, 0, 0))
		self.itemHeight = 30
		self.TlDate = None
		self.TlTime = None
		self.foreColor = 0xffc000
		self.borderColor = 0x000000
		self.backColor = 0x000000
		self.borderWidth = 1
		self.time_base = 0
		self.time_epoch = 0
		self.timelineFontName = "Regular"
		self.timelineFontSize = int(20 * getSkinFactor())
		self.timelineAlign = "left"

	GUI_WIDGET = eListbox

	def applySkin(self, desktop, screen):
		if self.skinAttributes is not None:
			attribs = []
			for (attrib, value) in self.skinAttributes:
				if attrib == "foregroundColor":
					self.foreColor = parseColor(value).argb()
				elif attrib == "borderColor":
					self.borderColor = parseColor(value).argb()
				elif attrib == "backgroundColor":
					self.backColor = parseColor(value).argb()
				elif attrib == "font":
					self.l.setFont(0, parseFont(value, ((1, 1), (1, 1))))
				elif attrib == "borderWidth":
					self.borderWidth = int(value)
				elif attrib == "TimelineFont":
					font = parseFont(value, ((1, 1), (1, 1)))
					self.timelineFontName = font.family
					self.timelineFontSize = font.pointSize
				elif attrib == "TimelineAlignment":
					self.timelineAlign = value
				elif attrib == "itemHeight":
					self.itemHeight = int(value)
				else:
					attribs.append((attrib, value))
			self.skinAttributes = attribs
		rc = GUIComponent.applySkin(self, desktop, screen)
		self.listHeight = self.instance.size().height()
		self.listWidth = self.instance.size().width()
		self.l.setItemHeight(self.itemHeight)
		if self.graphic:
			self.TlDate = loadPNG(resolveFilename(SCOPE_GUISKIN, "epg/TimeLineDate.png"))
			self.TlTime = loadPNG(resolveFilename(SCOPE_GUISKIN, "epg/TimeLineTime.png"))
		self._setFont()
		return rc

	def _setFont(self):
		if self.type == EPG_TYPE_GRAPH:
			fs = self.timelineFontSize + config.epgselection.grid.timelinefs.value
		else:
			fs = self.timelineFontSize + config.epgselection.infobar.timelinefs.value
		self.l.setFont(0, gFont(self.timelineFontName, fs))

	def postWidgetCreate(self, instance):
		instance.setContent(self.l)

	def setEntries(self, epgList, timeline_now, time_lines, force):
		event_rect = epgList.getEventRect()
		time_epoch = epgList.getTimeEpoch()
		time_base = epgList.getTimeBase()

		if event_rect is None or time_epoch is None or time_base is None:
			return

		alignment = (RT_HALIGN_RIGHT if self.timelineAlign.lower() == "right" else RT_HALIGN_LEFT) | RT_VALIGN_CENTER

		eventLeft = event_rect.left()
		res = [None]

		if self.time_base != time_base or self.time_epoch != time_epoch or force:
			service_rect = epgList.getServiceRect()
			time_steps = 60 if time_epoch > 180 else 30
			num_lines = time_epoch // time_steps
			incWidth = event_rect.width() / num_lines
			timeStepsCalc = time_steps * 60

			nowTime = localtime(time())
			begTime = localtime(time_base)
			ServiceWidth = service_rect.width()
			if nowTime[2] != begTime[2]:
				if ServiceWidth > 179:
					datestr = strftime(_("%A %d %B"), localtime(time_base))
				elif ServiceWidth > 139:
					datestr = strftime(_("%a %d %B"), localtime(time_base))
				elif ServiceWidth > 129:
					datestr = strftime(_("%a %d %b"), localtime(time_base))
				elif ServiceWidth > 119:
					datestr = strftime(_("%a %d"), localtime(time_base))
				elif ServiceWidth > 109:
					datestr = strftime(_("%A"), localtime(time_base))
				else:
					datestr = strftime(_("%a"), localtime(time_base))
			else:
				datestr = str(_("Today"))

			foreColor = self.foreColor
			backColor = self.backColor
			bgpng = self.TlDate
			if bgpng is not None and self.graphic:
				backColor = None
				res.append(MultiContentEntryPixmapAlphaTest(
					pos=(0, 0), size=(service_rect.width(), self.listHeight),
					png=bgpng, flags=BT_SCALE))
			else:
				res.append(MultiContentEntryText(
					pos=(0, 0), size=(service_rect.width(), self.listHeight),
					color=foreColor, backcolor=backColor,
					border_width=self.borderWidth, border_color=self.borderColor))

			res.append(MultiContentEntryText(
				pos=(5, 0), size=(service_rect.width() - 15, self.listHeight),
				font=0, flags=alignment,
				text=_(datestr), color=foreColor, backcolor=backColor))

			bgpng = self.TlTime
			xpos = 0
			if bgpng is not None and self.graphic:
				backColor = None
				res.append(MultiContentEntryPixmapAlphaTest(
					pos=(service_rect.width(), 0),
					size=(event_rect.width(), self.listHeight),
					png=bgpng, flags=BT_SCALE))
			else:
				res.append(MultiContentEntryText(
					pos=(service_rect.width(), 0),
					size=(event_rect.width(), self.listHeight),
					color=foreColor, backcolor=backColor,
					border_width=self.borderWidth, border_color=self.borderColor))

			use24h = (
				(self.type == EPG_TYPE_GRAPH and config.epgselection.grid.timeline24h.value) or
				(self.type == EPG_TYPE_INFOBARGRAPH and config.epgselection.infobar.timeline24h.value)
			)
			for x in range(num_lines):
				ttime = localtime(time_base + x * timeStepsCalc)
				if use24h:
					timetext = strftime("%H:%M", ttime)
				else:
					h = int(strftime("%H", ttime))
					timetext = strftime("%-I:%M", ttime) + (_("pm") if h > 12 else _("am"))
				res.append(MultiContentEntryText(
					pos=(service_rect.width() + xpos, 0),
					size=(incWidth, self.listHeight),
					font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
					text=timetext, color=foreColor, backcolor=backColor))
				line = time_lines[x]
				old_pos = line.position
				line.setPosition(xpos + eventLeft, old_pos[1])
				line.visible = True
				xpos += incWidth
			for x in range(num_lines, MAX_TIMELINES):
				time_lines[x].visible = False
			self.l.setList([res])
			self.time_base = time_base
			self.time_epoch = time_epoch

		now = time()
		if time_base <= now < (time_base + time_epoch * 60):
			xpos = int((((now - time_base) * event_rect.width()) / (time_epoch * 60))
						- (timeline_now.instance.size().width() / 2))
			old_pos = timeline_now.position
			new_pos = (xpos + eventLeft, old_pos[1])
			if old_pos != new_pos:
				timeline_now.setPosition(new_pos[0], new_pos[1])
			timeline_now.visible = True
		else:
			timeline_now.visible = False
class EPGListMulti(EPGListBase):
	"""EPG list for multi-channel now/next mode (EPG_TYPE_MULTI)."""

	def __init__(self, session, epgConfig, selChangedCB=None):
		EPGListBase.__init__(self, session, selChangedCB)

		sf = getSkinFactor()
		self.type = EPG_TYPE_MULTI
		self.epgConfig = epgConfig

		self.posx, self.posy, self.picx, self.picy, self.gap = skinparameter.get(
			"EpgListIcon", (2, 13, 25, 25, 2) if sf == 1.5 else (1, 11, 23, 23, 1))
		self.column_service, self.column_time, self.column_remaining, self.column_gap = \
			skinparameter.get("EpgListMulti",
								(240, 180, 120, 30) if sf == 1.5 else (160, 120, 80, 20))
		self.progress_width, self.progress_height, self.progress_borderwidth = \
			skinparameter.get("EpgListMultiProgressBar",
								(120, 15, 1) if sf == 1.5 else (80, 10, 1))

		self.listSizeWidth = None

		# Colour defaults.
		self.foreColor = 0xffffff
		self.foreColorSelected = 0xffffff
		self.backColor = 0x2D455E
		self.backColorSelected = 0xd69600

		self.eventFontNameMulti = "Regular"
		self.eventFontSizeMulti = int(22 * sf)

		self.list = []

		self.l.setBuildFunc(self.buildMultiEntry)


	GUI_WIDGET = eListbox

	def postWidgetCreate(self, instance):
		instance.setWrapAround(False)
		instance.selectionChanged.get().append(self.selectionChanged)
		instance.setContent(self.l)

	def preWidgetRemove(self, instance):
		instance.selectionChanged.get().remove(self.selectionChanged)
		instance.setContent(None)

	def selectionEnabled(self, enabled):
		if self.instance is not None:
			self.instance.setSelectionEnable(enabled)


	def applySkin(self, desktop, screen):
		if self.skinAttributes is not None:
			attribs = []
			for (attrib, value) in self.skinAttributes:
				if attrib == "EventFontMulti":
					font = parseFont(value, ((1, 1), (1, 1)))
					self.eventFontNameMulti = font.family
					self.eventFontSizeMulti = font.pointSize
				elif attrib == "EntryForegroundColor":
					self.foreColor = parseColor(value).argb()
				elif attrib == "EntryForegroundColorSelected":
					self.foreColorSelected = parseColor(value).argb()
				elif attrib == "EntryBackgroundColor":
					self.backColor = parseColor(value).argb()
				elif attrib == "EntryBackgroundColorSelected":
					self.backColorSelected = parseColor(value).argb()
				elif attrib == "NumberOfRows":
					self.numberOfRows = int(value)
				elif attrib == "itemHeight":
					self.skinItemHeight = int(value)
				elif attrib == "MinimumItemHeight":
					self.minimumItemHeight = max(0, int(value))
				else:
					attribs.append((attrib, value))
			self.skinAttributes = attribs
		rc = GUIComponent.applySkin(self, desktop, screen)
		self.skinListHeight = self.listHeight = self.instance.size().height()
		self.listWidth = self.instance.size().width()
		self.setFontsize()
		self.setItemsPerPage()
		return rc


	def setFontsize(self):
		fs = self.eventFontSizeMulti + self.epgConfig.eventfs.value
		self.l.setFont(0, gFont(self.eventFontNameMulti, fs))
		self.l.setFont(1, gFont(self.eventFontNameMulti, fs - 4))

	def setItemsPerPage(self, defaultItemHeight=None):
		sf = getSkinFactor()
		if defaultItemHeight is None:
			defaultItemHeight = int(32 * sf)
		ipp = self.epgConfig.itemsperpage.value
		if ipp and self.skinListHeight > 0:
			itemHeight = self.skinListHeight // ipp
		elif self.numberOfRows and self.skinListHeight > 0:
			itemHeight = self.skinListHeight // self.numberOfRows
		elif self.skinItemHeight:
			itemHeight = self.skinItemHeight
		else:
			itemHeight = defaultItemHeight
		if itemHeight < int(25 * sf):
			itemHeight = int(25 * sf)
		# Opt-in readable rows: enforce a minimum height while keeping only fully visible rows.
		if self.minimumItemHeight and self.skinListHeight > 0:
			itemHeight = min(self.skinListHeight, max(self.minimumItemHeight, itemHeight))
		self.l.setItemHeight(itemHeight)
		self.instance.resize(eSize(self.listWidth, self.skinListHeight // itemHeight * itemHeight))
		self.listHeight = self.instance.size().height()
		self.listWidth = self.instance.size().width()
		self.itemHeight = itemHeight

	def recalcEntrySize(self):
		esize = self.l.getItemSize()
		width = esize.width()
		height = esize.height()
		self.listSizeWidth = width
		xpos = 0
		w = self.column_service
		self.service_rect = Rect(xpos, 0, w, height)
		xpos += w + self.column_gap
		w = self.column_time
		self.start_end_rect = Rect(xpos, 0, w, height)
		p = w - self.progress_width
		self.progress_rect = Rect(
			xpos + int(p / 2),
			int((height - self.progress_height) / 2),
			w - p,
			self.progress_height)
		xpos += w + int(self.column_gap / 2)
		w = self.column_remaining
		self.remaining_rect = Rect(xpos, 0, w, height)
		xpos += w + self.column_gap
		self.descr_rect = Rect(xpos, 0, width - xpos, height)


	# Detect whether the entry is from IceTV.
	def buildMultiEntry(self, changecount, service, eventId, beginTime, duration,
						EventName, nowTime, service_name):
		if self.listSizeWidth != self.l.getItemSize().width():
			self.recalcEntrySize()
		r1 = self.service_rect
		r2 = self.progress_rect
		r3 = self.descr_rect
		r4 = self.start_end_rect
		r5 = self.remaining_rect
		borderw = self.progress_borderwidth

		if self.isIceTV(service) and self.icetvicon:
			from Components.config import config as _cfg
			if _cfg.epg.eit.value:
				iceicon_size = self.icetvicon.size()
				r_ice_w = iceicon_size.width()
				r_ice_h = iceicon_size.height()
			else:
				r_ice_w = r_ice_h = 0
		else:
			r_ice_w = r_ice_h = 0

		res = [
			None,
			(eListboxPythonMultiContent.TYPE_TEXT, r1.x, r1.y,
				r1.w - r_ice_w, r1.h, 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, service_name),
		]

		if r_ice_w > 0 and r_ice_h > 0:
			from Components.MultiContent import MultiContentEntryPixmapAlphaBlend
			res.append(MultiContentEntryPixmapAlphaBlend(
				pos=(r1.x + r1.w - r_ice_w, r1.y),
				size=(r_ice_w, r_ice_h),
				png=self.icetvicon,
				backcolor=None, backcolor_sel=None))

		if beginTime is not None:
			clock_types = self.getPixmapForEntry(service, eventId, beginTime, duration)
			if nowTime < beginTime:
				from time import localtime
				begin = localtime(beginTime)
				end = localtime(beginTime + duration)
				res.extend((
					(eListboxPythonMultiContent.TYPE_TEXT, r4.x, r4.y, r4.w, r4.h,
						1, RT_HALIGN_CENTER | RT_VALIGN_CENTER,
						_("%02d:%02d - %02d:%02d") % (begin[3], begin[4], end[3], end[4])),
					(eListboxPythonMultiContent.TYPE_TEXT, r5.x, r5.y, r5.w, r5.h,
						1, RT_HALIGN_RIGHT | RT_VALIGN_CENTER,
						_("%d min") % (duration / 60)),
				))
			else:
				percent = int((nowTime - beginTime) * 100 / duration)
				prefix = "+"
				remaining = ((beginTime + duration) - int(time())) / 60
				if remaining <= 0:
					prefix = ""
				res.extend((
					(eListboxPythonMultiContent.TYPE_PROGRESS,
						r2.x, r2.y + borderw, r2.w, r2.h, percent, borderw),
					(eListboxPythonMultiContent.TYPE_TEXT, r5.x, r5.y, r5.w, r5.h,
						1, RT_HALIGN_RIGHT | RT_VALIGN_CENTER,
						_("%s%d min") % (prefix, remaining)),
				))

			pos = r3.x + r3.w
			for typeIcon in self.getIcons(clock_types, service, beginTime):
				res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND,
							pos - self.picx * 2 - self.gap - self.posx,
							r3.h // 2 - self.posy, self.picx, self.picy, typeIcon))

			if clock_types:
				res.extend((
					(eListboxPythonMultiContent.TYPE_TEXT,
						r3.x, r3.y, r3.w - self.picx - (self.gap * 2) - self.posx, r3.h,
						1, RT_HALIGN_LEFT | RT_VALIGN_CENTER, EventName),
					(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND,
						pos - self.picx - self.posx, r3.h // 2 - self.posy,
						self.picx, self.picy, self.clocks[clock_types]),
				))
			else:
				res.append((eListboxPythonMultiContent.TYPE_TEXT,
							r3.x, r3.y, r3.w, r3.h,
							1, RT_HALIGN_LEFT | RT_VALIGN_CENTER, EventName))
		return res


	def getCurrentChangeCount(self):
		if self.l.getCurrentSelection() is not None:
			return self.l.getCurrentSelection()[0]
		return 0

	def getCurrent(self):
		tmp = self.l.getCurrentSelection()
		if tmp is None:
			return None, None
		# Multi list tuple: (changecount, service_ref, event_id, ...)
		service = ServiceReference(tmp[1])
		eventId = tmp[2]
		event = self.getEventFromId(service, eventId)
		return event, service


	def fillMultiEPG(self, services, stime=None):
		test = [(service.ref.toString(), 0, int(stime)) for service in services]
		test.insert(0, "X0RIBDTCn")
		self.list = self.queryEPG(test)
		self.l.setList(self.list)
		self.selectionChanged()

	def updateMultiEPG(self, direction):
		test = [x[3] and (x[1], direction, x[3]) or (x[1], direction, 0) for x in self.list]
		test.insert(0, "XRIBDTCn")
		epg_data = self.queryEPG(test)
		cnt = 0
		for x in epg_data:
			changecount = self.list[cnt][0] + direction
			if changecount >= 0:
				if x[2] is not None:
					self.list[cnt] = (changecount, x[0], x[1], x[2], x[3], x[4], x[5], x[6])
			cnt += 1
		self.l.setList(self.list)
		self.selectionChanged()
class EPGListSingle(EPGListBase):
	"""EPG list for single-channel, enhanced, infobar-text and similar modes.

	``epgType`` determines which fill method is used and which config subsection
	applies (single / infobar).  The column layout is the same for all four.
	"""

	def __init__(self, session, epgConfig, epgType=EPG_TYPE_SINGLE, selChangedCB=None):
		EPGListBase.__init__(self, session, selChangedCB)

		sf = getSkinFactor()
		self.type = epgType
		self.epgConfig = epgConfig

		self.posx, self.posy, self.picx, self.picy, self.gap = skinparameter.get(
			"EpgListIcon", (2, 13, 25, 25, 2) if sf == 1.5 else (1, 11, 23, 23, 1))
		self.column_weekday, self.column_datetime = skinparameter.get(
			"EpgListSingle", (75, 225) if sf == 1.5 else (50, 150))

		self.listSizeWidth = None
		self.skinUsingForeColorByTime = False
		self.skinUsingBackColorByTime = False

		# Colour defaults, overridden by skin attributes.
		self.foreColor = 0xffffff
		self.foreColorSelected = 0xffffff
		self.backColor = 0x2D455E
		self.backColorSelected = 0xd69600
		self.foreColorNow = 0xffffff
		self.foreColorNowSelected = 0xffffff
		self.backColorNow = 0x00825F
		self.backColorNowSelected = 0xd69600
		self.foreColorPast = 0x808080
		self.foreColorPastSelected = 0x808080
		self.backColorPast = 0x2D455E
		self.backColorPastSelected = 0xd69600

		self.eventFontNameSingle = "Regular"
		self.eventFontSizeSingle = int(22 * sf)
		self.eventFontNameInfobar = "Regular"
		self.eventFontSizeInfobar = int(22 * sf)

		self.list = []

		if epgType == EPG_TYPE_SIMILAR:
			self.l.setBuildFunc(self.buildSimilarEntry)
		else:
			self.l.setBuildFunc(self.buildSingleEntry)


	GUI_WIDGET = eListbox

	def postWidgetCreate(self, instance):
		instance.setWrapAround(False)
		instance.selectionChanged.get().append(self.selectionChanged)
		instance.setContent(self.l)

	def preWidgetRemove(self, instance):
		instance.selectionChanged.get().remove(self.selectionChanged)
		instance.setContent(None)

	def selectionEnabled(self, enabled):
		if self.instance is not None:
			self.instance.setSelectionEnable(enabled)


	def applySkin(self, desktop, screen):
		if self.skinAttributes is not None:
			attribs = []
			self.skinUsingForeColorByTime = False
			self.skinUsingBackColorByTime = False
			for (attrib, value) in self.skinAttributes:
				if attrib == "EventFontSingle":
					font = parseFont(value, ((1, 1), (1, 1)))
					self.eventFontNameSingle = font.family
					self.eventFontSizeSingle = font.pointSize
				elif attrib == "EventFontInfobar":
					font = parseFont(value, ((1, 1), (1, 1)))
					self.eventFontNameInfobar = font.family
					self.eventFontSizeInfobar = font.pointSize
				elif attrib == "EntryForegroundColor":
					self.foreColor = parseColor(value).argb()
				elif attrib == "EntryForegroundColorSelected":
					self.foreColorSelected = parseColor(value).argb()
				elif attrib == "EntryBackgroundColor":
					self.backColor = parseColor(value).argb()
				elif attrib == "EntryBackgroundColorSelected":
					self.backColorSelected = parseColor(value).argb()
				elif attrib == "EntryBackgroundColorNow":
					self.backColorNow = parseColor(value).argb()
					self.skinUsingBackColorByTime = True
				elif attrib == "EntryBackgroundColorNowSelected":
					self.backColorNowSelected = parseColor(value).argb()
					self.skinUsingBackColorByTime = True
				elif attrib == "EntryForegroundColorNow":
					self.foreColorNow = parseColor(value).argb()
					self.skinUsingForeColorByTime = True
				elif attrib == "EntryForegroundColorNowSelected":
					self.foreColorNowSelected = parseColor(value).argb()
					self.skinUsingForeColorByTime = True
				elif attrib == "EntryBackgroundColorPast":
					self.backColorPast = parseColor(value).argb()
					self.skinUsingBackColorByTime = True
				elif attrib == "EntryBackgroundColorPastSelected":
					self.backColorPastSelected = parseColor(value).argb()
					self.skinUsingBackColorByTime = True
				elif attrib == "EntryForegroundColorPast":
					self.foreColorPast = parseColor(value).argb()
					self.skinUsingForeColorByTime = True
				elif attrib == "EntryForegroundColorPastSelected":
					self.foreColorPastSelected = parseColor(value).argb()
					self.skinUsingForeColorByTime = True
				elif attrib == "NumberOfRows":
					self.numberOfRows = int(value)
				elif attrib == "itemHeight":
					self.skinItemHeight = int(value)
				elif attrib == "MinimumItemHeight":
					self.minimumItemHeight = max(0, int(value))
				else:
					attribs.append((attrib, value))
			self.skinAttributes = attribs
		rc = GUIComponent.applySkin(self, desktop, screen)
		self.skinListHeight = self.listHeight = self.instance.size().height()
		self.listWidth = self.instance.size().width()
		self.setFontsize()
		self.setItemsPerPage()
		return rc


	def setFontsize(self):
		if self.type == EPG_TYPE_INFOBAR:
			fs = self.eventFontSizeInfobar + self.epgConfig.eventfs.value
			self.l.setFont(0, gFont(self.eventFontNameInfobar, fs))
		else:
			fs = self.eventFontSizeSingle + self.epgConfig.eventfs.value
			self.l.setFont(0, gFont(self.eventFontNameSingle, fs))

	def setItemsPerPage(self, defaultItemHeight=None):
		sf = getSkinFactor()
		if defaultItemHeight is None:
			defaultItemHeight = int(32 * sf)
		ipp = self.epgConfig.itemsperpage.value
		if ipp and self.skinListHeight > 0:
			itemHeight = self.skinListHeight // ipp
		elif self.numberOfRows and self.skinListHeight > 0:
			itemHeight = self.skinListHeight // self.numberOfRows
		elif self.skinItemHeight:
			itemHeight = self.skinItemHeight
		else:
			itemHeight = defaultItemHeight
		if itemHeight < int(15 * sf):
			itemHeight = int(15 * sf)
		# Opt-in readable rows: enforce a minimum height while keeping only fully visible rows.
		if self.minimumItemHeight and self.skinListHeight > 0:
			itemHeight = min(self.skinListHeight, max(self.minimumItemHeight, itemHeight))
		self.l.setItemHeight(itemHeight)
		self.instance.resize(eSize(self.listWidth, self.skinListHeight // itemHeight * itemHeight))
		self.listHeight = self.instance.size().height()
		self.listWidth = self.instance.size().width()
		self.itemHeight = itemHeight

	def recalcEntrySize(self):
		esize = self.l.getItemSize()
		width = esize.width()
		height = esize.height()
		self.listSizeWidth = width
		self.weekday_rect = Rect(0, 0, self.column_weekday, height)
		self.datetime_rect = Rect(self.column_weekday, 0, self.column_datetime, height)
		self.descr_rect = Rect(
			self.column_weekday + self.column_datetime,
			0,
			width - (self.column_weekday + self.column_datetime),
			height)


	def buildSingleEntry(self, service, eventId, beginTime, duration, EventName):
		if self.listSizeWidth != self.l.getItemSize().width():
			self.recalcEntrySize()

		now = time()
		if beginTime is not None and (beginTime + duration < now):
			foreColor, backColor = self.foreColorPast, self.backColorPast
			foreColorSel, backColorSel = self.foreColorPastSelected, self.backColorPastSelected
		elif beginTime is not None and beginTime < now:
			foreColor, backColor = self.foreColorNow, self.backColorNow
			foreColorSel, backColorSel = self.foreColorNowSelected, self.backColorNowSelected
		else:
			foreColor, backColor = self.foreColor, self.backColor
			foreColorSel, backColorSel = self.foreColorSelected, self.backColorSelected

		# Colour-by-time only applies when the skin explicitly sets those attributes
		# to avoid changing the look of skins that do not declare them.
		if not self.skinUsingForeColorByTime:
			foreColor = foreColorSel = None
		if not self.skinUsingBackColorByTime:
			backColor = backColorSel = None

		clock_types = self.getPixmapForEntry(service, eventId, beginTime, duration)
		r1 = self.weekday_rect
		r2 = self.datetime_rect
		r3 = self.descr_rect
		t = localtime(beginTime)
		datetime_str = "%s, %s" % (
			strftime(config.usage.date.short.value, t),
			strftime(config.usage.time.short.value, t))
		res = [
			None,
			(eListboxPythonMultiContent.TYPE_TEXT, r1.x, r1.y, r1.w, r1.h,
				0, RT_HALIGN_LEFT | RT_VALIGN_CENTER,
				_(strftime(_("%a"), t)), foreColor, foreColorSel, backColor, backColorSel),
			(eListboxPythonMultiContent.TYPE_TEXT, r2.x, r2.y, r2.w, r1.h,
				0, RT_HALIGN_LEFT | RT_VALIGN_CENTER,
				datetime_str, foreColor, foreColorSel, backColor, backColorSel),
		]

		offset = 0
		for typeIcon in self.getIcons(clock_types, service, beginTime):
			offset += self.picx * 2 + self.gap
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND,
						r3.x + r3.w - self.picx * 2 - self.gap - self.posx,
						r3.h // 2 - self.posy, self.picx, self.picy, typeIcon))

		if clock_types:
			res.extend((
				(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND,
					r3.x + r3.w - self.picx - self.posx, r3.h // 2 - self.posy,
					self.picx, self.picy, self.clocks[clock_types]),
				(eListboxPythonMultiContent.TYPE_TEXT,
					r3.x, r3.y, r3.w - self.picx - self.posx - offset, r3.h,
					0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, EventName,
					foreColor, foreColorSel, backColor, backColorSel),
			))
		else:
			res.append((eListboxPythonMultiContent.TYPE_TEXT,
						r3.x, r3.y, r3.w - offset, r3.h,
						0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, EventName,
						foreColor, foreColorSel, backColor, backColorSel))
		return res

	def buildSimilarEntry(self, service, eventId, beginTime, service_name, duration):
		if self.listSizeWidth != self.l.getItemSize().width():
			self.recalcEntrySize()
		clock_types = self.getPixmapForEntry(service, eventId, beginTime, duration)
		r1 = self.weekday_rect
		r2 = self.datetime_rect
		r3 = self.descr_rect
		t = localtime(beginTime)
		res = [
			None,
			(eListboxPythonMultiContent.TYPE_TEXT, r1.x, r1.y, r1.w, r1.h,
				0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, _(strftime(_("%a"), t))),
			(eListboxPythonMultiContent.TYPE_TEXT, r2.x, r2.y, r2.w, r1.h,
				0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, strftime(_("%e/%m, %-H:%M"), t)),
		]
		offset = 0
		for typeIcon in self.getIcons(clock_types, service, beginTime):
			offset += self.picx * 2 + self.gap
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND,
						r3.x + r3.w - self.picx * 2 - self.gap - self.posx,
						r3.h // 2 - self.posy, self.picx, self.picy, typeIcon))
		if clock_types:
			res.extend((
				(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND,
					r3.x + r3.w - self.picx - self.posx, r3.h // 2 - self.posy,
					self.picx, self.picy, self.clocks[clock_types]),
				(eListboxPythonMultiContent.TYPE_TEXT,
					r3.x, r3.y, r3.w - self.picx - (self.gap * 2) - self.posx - offset, r3.h,
					0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, service_name),
			))
		else:
			res.append((eListboxPythonMultiContent.TYPE_TEXT,
						r3.x, r3.y, r3.w - offset, r3.h,
						0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, service_name))
		return res


	def getCurrent(self):
		tmp = self.l.getCurrentSelection()
		if tmp is None:
			return None, None
		service = ServiceReference(tmp[0])
		eventId = tmp[1]
		event = self.getEventFromId(service, eventId)
		return event, service

	def getIndexFromService(self, serviceref):
		if serviceref is not None:
			for x in range(len(self.list)):
				if CompareWithAlternatives(self.list[x][0], serviceref.toString()):
					return x
		return 0

	def moveToService(self, serviceref):
		if not serviceref:
			return
		self.setCurrentIndex(self.getIndexFromService(serviceref))


	def fillSingleEPG(self, service, stime=None):
		if stime is not None:
			t = epg_time = int(stime)
		else:
			t = time()
			epg_time = t - config.epg.histminutes.value * 60
		test = ["RIBDT", (service.ref.toString(), 0, int(epg_time), -1)]
		self.list = self.queryEPG(test)
		self.l.setList(self.list)
		if t != epg_time:
			idx = 0
			for x in self.list:
				idx += 1
				if t < x[2] + x[3]:
					break
			self.instance.moveSelectionTo(idx - 1)
		else:
			self.instance.moveSelectionTo(0)
		self.selectionChanged()

	def fillSimilarList(self, refstr, event_id):
		if event_id is None:
			return
		self.list = self.epgcache.search(
			("RIBND", 1024, eEPGCache.SIMILAR_BROADCASTINGS_SEARCH, refstr, event_id))
		if self.list and len(self.list):
			self.list.sort(key=lambda x: x[2])
		self.l.setList(self.list)
		self.selectionChanged()

	def sortSingleEPG(self, sort_type):
		if self.list:
			event_id = self.getSelectedEventId()
			if sort_type == 1:
				self.list.sort(key=lambda x: (x[4] and x[4].lower(), x[2]))
			else:
				self.list.sort(key=lambda x: x[2])
			self.l.invalidate()
			self.moveToEventId(event_id)

class EPGList(EPGListSingle):
	"""Old EPGList API for plugins like EPGSearch (single EPG only)."""

	def __init__(self, type=EPG_TYPE_SINGLE, selChangedCB=None, timer=None, time_epoch=120, overjump_empty=False, graphic=False):
		if type not in (EPG_TYPE_SINGLE, EPG_TYPE_ENHANCED, EPG_TYPE_INFOBAR, EPG_TYPE_SIMILAR):
			print(f"[EPGList] Warning: Type {type} is not supported, using single EPG.")
			type = EPG_TYPE_SINGLE
		from Screens.InfoBar import InfoBar
		EPGListSingle.__init__(self, InfoBar.instance.session, config.epgselection.single, type, selChangedCB)


class EPGListVertical(EPGListBase):
	"""EPG list for one column of the vertical multi-day EPG (EPG_TYPE_VERTICAL)."""

	def __init__(self, session, epgConfig, selChangedCB=None):
		EPGListBase.__init__(self, session, selChangedCB)

		sf = getSkinFactor()
		self.type = EPG_TYPE_VERTICAL
		self.epgConfig = epgConfig

		self.posx, self.posy, self.picx, self.picy, self.gap = skinparameter.get(
			"EpgListIcon", (2, 13, 25, 25, 2) if sf == 1.5 else (1, 11, 23, 23, 1))

		self.listSizeWidth = None
		self.skinUsingForeColorByTime = False
		self.skinUsingBackColorByTime = False

		# Colour defaults.
		self.foreColor = 0xffffff
		self.foreColorSelected = 0xffffff
		self.backColor = 0x2D455E
		self.backColorSelected = 0xd69600
		self.foreColorNow = 0xffffff
		self.foreColorNowSelected = 0xffffff
		self.backColorNow = 0x00825F
		self.backColorNowSelected = 0xd69600
		self.foreColorPast = 0x808080
		self.foreColorPastSelected = 0x808080
		self.backColorPast = 0x2D455E
		self.backColorPastSelected = 0xd69600
		self.foreColorTime = 0xF0A30A
		self.backColorTime = 0x2D455E
		self.foreColorPrimeTime = 0xffffff
		self.backColorPrimeTime = 0x704A05
		self.borderColor = 0xC0C0C0

		self.eventFontNameVertical = "Regular"
		self.timeFontNameVertical = "Regular"
		self.eventFontSizeVertical = int(18 * sf)
		self.timeFontSizeVertical = int(20 * sf)

		# Localised short day names for the time header.
		self.days = (_("Mon"), _("Tue"), _("Wed"), _("Thu"), _("Fri"), _("Sat"), _("Sun"))

		self.primetimeicon = LoadPixmap(
			cached=True, path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock_primetime.png"))
		self.list = []

		self.l.setBuildFunc(self.buildVerticalEntry)


	GUI_WIDGET = eListbox

	def postWidgetCreate(self, instance):
		instance.setWrapAround(False)
		instance.selectionChanged.get().append(self.selectionChanged)
		instance.setContent(self.l)

	def preWidgetRemove(self, instance):
		instance.selectionChanged.get().remove(self.selectionChanged)
		instance.setContent(None)

	def selectionEnabled(self, enabled):
		if self.instance is not None:
			self.instance.setSelectionEnable(enabled)


	def applySkin(self, desktop, screen):
		if self.skinAttributes is not None:
			attribs = []
			self.skinUsingForeColorByTime = False
			self.skinUsingBackColorByTime = False
			for (attrib, value) in self.skinAttributes:
				if attrib == "EventFontVertical":
					font = parseFont(value, ((1, 1), (1, 1)))
					self.eventFontNameVertical = font.family
					self.eventFontSizeVertical = font.pointSize
				elif attrib == "TimeFontVertical":
					font = parseFont(value, ((1, 1), (1, 1)))
					self.timeFontNameVertical = font.family
					self.timeFontSizeVertical = font.pointSize
				elif attrib == "EntryForegroundColor":
					self.foreColor = parseColor(value).argb()
				elif attrib == "EntryForegroundColorSelected":
					self.foreColorSelected = parseColor(value).argb()
				elif attrib == "EntryBackgroundColor":
					self.backColor = parseColor(value).argb()
				elif attrib == "EntryBackgroundColorSelected":
					self.backColorSelected = parseColor(value).argb()
				elif attrib == "EntryBackgroundColorNow":
					self.backColorNow = parseColor(value).argb()
					self.skinUsingBackColorByTime = True
				elif attrib == "EntryBackgroundColorNowSelected":
					self.backColorNowSelected = parseColor(value).argb()
					self.skinUsingBackColorByTime = True
				elif attrib == "EntryForegroundColorNow":
					self.foreColorNow = parseColor(value).argb()
					self.skinUsingForeColorByTime = True
				elif attrib == "EntryForegroundColorNowSelected":
					self.foreColorNowSelected = parseColor(value).argb()
					self.skinUsingForeColorByTime = True
				elif attrib == "EntryBackgroundColorPast":
					self.backColorPast = parseColor(value).argb()
					self.skinUsingBackColorByTime = True
				elif attrib == "EntryBackgroundColorPastSelected":
					self.backColorPastSelected = parseColor(value).argb()
					self.skinUsingBackColorByTime = True
				elif attrib == "EntryForegroundColorPast":
					self.foreColorPast = parseColor(value).argb()
					self.skinUsingForeColorByTime = True
				elif attrib == "EntryForegroundColorPastSelected":
					self.foreColorPastSelected = parseColor(value).argb()
					self.skinUsingForeColorByTime = True
				elif attrib == "TimeForegroundColor":
					self.foreColorTime = parseColor(value).argb()
				elif attrib == "TimeBackgroundColor":
					self.backColorTime = parseColor(value).argb()
				elif attrib == "PrimeTimeForegroundColor":
					self.foreColorPrimeTime = parseColor(value).argb()
				elif attrib == "PrimeTimeBackgroundColor":
					self.backColorPrimeTime = parseColor(value).argb()
				elif attrib == "NumberOfRows":
					self.numberOfRows = int(value)
				elif attrib == "itemHeight":
					self.skinItemHeight = int(value)
				elif attrib == "MinimumItemHeight":
					self.minimumItemHeight = max(0, int(value))
				else:
					attribs.append((attrib, value))
			self.skinAttributes = attribs
		rc = GUIComponent.applySkin(self, desktop, screen)
		self.skinListHeight = self.listHeight = self.instance.size().height()
		self.listWidth = self.instance.size().width()
		self.setFontsize()
		self.setItemsPerPage()
		return rc


	def setFontsize(self):
		fs = self.epgConfig.eventfs.value
		self.l.setFont(0, gFont(self.timeFontNameVertical, self.timeFontSizeVertical + fs))
		self.l.setFont(1, gFont(self.eventFontNameVertical, self.eventFontSizeVertical + fs))

	def setItemsPerPage(self, defaultItemHeight=None):
		sf = getSkinFactor()
		if defaultItemHeight is None:
			defaultItemHeight = int(90 * sf)
		ipp = self.epgConfig.itemsperpage.value
		if ipp and self.skinListHeight > 0:
			itemHeight = self.skinListHeight // ipp
		elif self.numberOfRows and self.skinListHeight > 0:
			itemHeight = self.skinListHeight // self.numberOfRows
		elif self.skinItemHeight:
			itemHeight = self.skinItemHeight
		else:
			itemHeight = defaultItemHeight
		if itemHeight <= 0:
			itemHeight = defaultItemHeight
		# Opt-in readable rows: enforce a minimum height while keeping only fully visible rows.
		if self.minimumItemHeight and self.skinListHeight > 0:
			itemHeight = min(self.skinListHeight, max(self.minimumItemHeight, itemHeight))
		self.l.setItemHeight(itemHeight)
		self.instance.resize(eSize(self.listWidth, self.skinListHeight // itemHeight * itemHeight))
		self.listHeight = self.instance.size().height()
		self.listWidth = self.instance.size().width()
		self.itemHeight = itemHeight

	def recalcEntrySize(self):
		esize = self.l.getItemSize()
		width = esize.width()
		height = esize.height()
		self.listSizeWidth = width
		dh = self.picy if self.picy > self.timeFontSizeVertical else self.timeFontSizeVertical
		self.line_rect = Rect(0, 0, width, int(self.epgConfig.showlines.value))
		self.datetime_rect = Rect(0, 0, width, dh)
		self.descr_rect = Rect(0, dh, width, height - dh)


	def buildVerticalEntry(self, service, eventId, beginTime, duration, EventName):
		if self.listSizeWidth != self.l.getItemSize().width():
			self.recalcEntrySize()

		now = time()
		if beginTime is not None and (beginTime + duration < now):
			foreColor, backColor = self.foreColorPast, self.backColorPast
			foreColorSel, backColorSel = self.foreColorPastSelected, self.backColorPastSelected
		elif beginTime is not None and beginTime < now:
			foreColor, backColor = self.foreColorNow, self.backColorNow
			foreColorSel, backColorSel = self.foreColorNowSelected, self.backColorNowSelected
		else:
			foreColor, backColor = self.foreColor, self.backColor
			foreColorSel, backColorSel = self.foreColorSelected, self.backColorSelected

		if not self.skinUsingForeColorByTime:
			foreColor = foreColorSel = None
		if not self.skinUsingBackColorByTime:
			backColor = backColorSel = None

		foreColorTime = self.foreColorTime
		foreColorPrimeTime = self.foreColorPrimeTime
		backColorTime = self.backColorTime
		backColorPrimeTime = self.backColorPrimeTime
		borderColor = self.borderColor

		r1 = self.line_rect
		r2 = self.datetime_rect
		r3 = self.descr_rect

		clock_types = self.getPixmapForEntry(service, eventId, beginTime, duration)

		if beginTime is None:
			beginTime = now
			duration = 3600
		elif duration is None:
			duration = 3600

		t = localtime(beginTime)
		vpt = self.epgConfig.primetime.value
		primetime = mktime((t[0], t[1], t[2], vpt[0], vpt[1], 0, t[6], t[7], t[8]))
		is_primetime = primetime >= beginTime and primetime < beginTime + duration
		if is_primetime:
			foreColor = foreColorPrimeTime
			backColor = backColorPrimeTime

		res = [
			None,
			# Background for event description area.
			(eListboxPythonMultiContent.TYPE_TEXT, r3.x, r3.y, r3.w, r3.h,
				0, RT_HALIGN_LEFT, " ", foreColor, foreColorSel, backColor, backColorSel),
			# Background for time header area.
			(eListboxPythonMultiContent.TYPE_TEXT, r2.x, r2.y, r2.w, r2.h,
				0, RT_HALIGN_LEFT, " ", foreColorTime, foreColorSel, backColorTime, backColorSel),
		]

		date_str = "%02d.%02d %s %02d:%02d" % (
			t[2], t[1], self.days[t[6]], t[3], t[4])

		if is_primetime and self.primetimeicon:
			res.extend((
				(eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND,
					r2.x + self.posx, r2.h // 2 - self.posy, self.picx, self.picy, self.primetimeicon),
				(eListboxPythonMultiContent.TYPE_TEXT,
					r2.x + self.posx * 3 + self.picx, r2.y,
					r2.w - (self.posx * 3 + self.picx), r2.h,
					0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, date_str,
					foreColorTime, foreColorSel, backColorTime, backColorSel),
			))
		else:
			res.append((eListboxPythonMultiContent.TYPE_TEXT,
						r2.x + self.posx, r2.y, r2.w - self.posx, r2.h,
						0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, date_str,
						foreColorTime, foreColorSel, backColorTime, backColorSel))

		for typeIcon in self.getIcons(clock_types, service, beginTime):
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND,
						r2.w - self.picx * 2 - self.posx * 2, r2.h // 2 - self.posy,
						self.picx, self.picy, typeIcon))

		if clock_types:
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND,
						r2.w - self.picx - self.posx, r2.h // 2 - self.posy,
						self.picx, self.picy, self.clocks[clock_types]))

		res.extend((
			# Horizontal dividing line between list entries.
			(eListboxPythonMultiContent.TYPE_TEXT, r1.x, r1.y, r1.w, r1.h,
				0, RT_HALIGN_LEFT, " ", foreColor, foreColorSel, borderColor, borderColor),
			# Event name.
			(eListboxPythonMultiContent.TYPE_TEXT, r3.x + self.posx, r3.y, r3.w - self.posx, r3.h,
				1, RT_HALIGN_LEFT | RT_WRAP, EventName,
				foreColor, foreColorSel, backColor, backColorSel),
		))
		return res


	def getCurrent(self):
		tmp = self.l.getCurrentSelection()
		if tmp is None:
			return None, None
		service = ServiceReference(tmp[0])
		eventId = tmp[1]
		event = self.getEventFromId(service, eventId)
		return event, service


	def fillVerticalEPG(self, service, stime=None):
		"""Fill this column with events for the given service starting at stime."""
		if stime is not None:
			t = epg_time = int(stime)
		else:
			t = time()
			epg_time = t - self.epgConfig.histminutes.value * 60 if hasattr(self.epgConfig, "histminutes") else t
		test = ["RIBDT", (service.ref.toString(), 0, int(epg_time), -1)]
		self.list = self.queryEPG(test)
		self.l.setList(self.list)
		if t != epg_time:
			idx = 0
			for x in self.list:
				idx += 1
				if t < x[2] + x[3]:
					break
			self.instance.moveSelectionTo(idx - 1)
		else:
			self.instance.moveSelectionTo(0)
		self.selectionChanged()


class EPGBouquetList(GUIComponent):
	def __init__(self, graphic=False):
		GUIComponent.__init__(self)
		self.graphic = graphic
		self.l = eListboxPythonMultiContent()
		self.l.setBuildFunc(self.buildEntry)

		self.onSelChanged = []

		self.foreColor = 0xffffff
		self.foreColorSelected = 0xffffff
		self.backColor = 0x2D455E
		self.backColorSelected = 0xd69600

		self.borderColor = 0xC0C0C0
		self.BorderWidth = 1

		self.othPix = None
		self.selPix = None
		self.graphicsloaded = False

		self.bouquetFontName = "Regular"
		self.bouquetFontSize = int(20 * getSkinFactor())

		self.itemHeight = 31
		self.listHeight = None
		self.listWidth = None

		self.bouquetNamePadding = 3
		self.bouquetNameAlign = 'left'
		self.bouquetNameWrap = 'no'

	def applySkin(self, desktop, screen):
		if self.skinAttributes is not None:
			attribs = []
			for (attrib, value) in self.skinAttributes:
				if attrib == "font":
					font = parseFont(value, ((1, 1), (1, 1)))
					self.bouquetFontName = font.family
					self.bouquetFontSize = font.pointSize
				elif attrib == "foregroundColor":
					self.foreColor = parseColor(value).argb()
				elif attrib == "backgroundColor":
					self.backColor = parseColor(value).argb()
				elif attrib == "foregroundColorSelected":
					self.foreColorSelected = parseColor(value).argb()
				elif attrib == "backgroundColorSelected":
					self.backColorSelected = parseColor(value).argb()
				elif attrib == "borderColor":
					self.borderColor = parseColor(value).argb()
				elif attrib == "borderWidth":
					self.BorderWidth = int(value)
				elif attrib == "itemHeight":
					self.itemHeight = int(value)
				else:
					attribs.append((attrib, value))
			self.skinAttributes = attribs
		rc = GUIComponent.applySkin(self, desktop, screen)
		self.listHeight = self.instance.size().height()
		self.listWidth = self.instance.size().width()
		self.l.setItemHeight(self.itemHeight)
		self.setBouquetFontsize()
		return rc

	GUI_WIDGET = eListbox

	def getCurrentBouquet(self):
		return self.l.getCurrentSelection()[0]

	def getCurrentBouquetService(self):
		return self.l.getCurrentSelection()[1]

	def setCurrentBouquet(self, CurrentBouquetService):
		self.CurrentBouquetService = CurrentBouquetService

	def selectionChanged(self):
		for x in self.onSelChanged:
			if x is not None:
				x()

	def getIndexFromService(self, serviceref):
		if serviceref is not None:
			for x in list(range(len(self.bouquetslist))):
				if CompareWithAlternatives(self.bouquetslist[x][1].toString(), serviceref.toString()):
					return x
		return 0

	def moveToService(self, serviceref):
		newIdx = self.getIndexFromService(serviceref)
		self.setCurrentIndex(newIdx)

	def setCurrentIndex(self, index):
		if self.instance is not None:
			self.instance.moveSelectionTo(index)

	def moveTo(self, dir):
		if self.instance is not None:
			self.instance.moveSelection(dir)

	def setBouquetFontsize(self):
		self.l.setFont(0, gFont(self.bouquetFontName, self.bouquetFontSize))

	def postWidgetCreate(self, instance):
		self.l.setSelectableFunc(True)
		instance.setWrapAround(True)
		instance.selectionChanged.get().append(self.selectionChanged)
		instance.setContent(self.l)

	def preWidgetRemove(self, instance):
		instance.selectionChanged.get().append(self.selectionChanged)
		instance.setContent(None)

	def selectionEnabled(self, enabled):
		if self.instance is not None:
			self.instance.setSelectionEnable(enabled)

	def recalcEntrySize(self):
		esize = self.l.getItemSize()
		width = esize.width()
		height = esize.height()
		self.bouquet_rect = Rect(0, 0, width, height)

	def getBouquetRect(self):
		rc = self.bouquet_rect
		return Rect(rc.left() + (self.instance and self.instance.position().x() or 0), rc.top(), rc.width(), rc.height())

	def buildEntry(self, name, func):
		r1 = self.bouquet_rect
		left = r1.x
		top = r1.y
		width = r1.w
		height = r1.h
		selected = self.CurrentBouquetService == func

		if self.bouquetNameAlign.lower() == 'left':
			if self.bouquetNameWrap.lower() == 'yes':
				alignnment = RT_HALIGN_LEFT | RT_VALIGN_CENTER | RT_WRAP
			else:
				alignnment = RT_HALIGN_LEFT | RT_VALIGN_CENTER
		else:
			if self.bouquetNameWrap.lower() == 'yes':
				alignnment = RT_HALIGN_CENTER | RT_VALIGN_CENTER | RT_WRAP
			else:
				alignnment = RT_HALIGN_CENTER | RT_VALIGN_CENTER

		res = [None]

		if selected:
			if self.graphic:
				borderTopPix = self.borderSelectedTopPix
				borderLeftPix = self.borderSelectedLeftPix
				borderBottomPix = self.borderSelectedBottomPix
				borderRightPix = self.borderSelectedRightPix
			foreColor = self.foreColor
			backColor = self.backColor
			foreColorSel = self.foreColorSelected
			backColorSel = self.backColorSelected
			bgpng = self.selPix
			if bgpng is not None and self.graphic:
				backColor = None
				backColorSel = None
		else:
			if self.graphic:
				borderTopPix = self.borderTopPix
				borderLeftPix = self.borderLeftPix
				borderBottomPix = self.borderBottomPix
				borderRightPix = self.borderRightPix
			backColor = self.backColor
			foreColor = self.foreColor
			foreColorSel = self.foreColorSelected
			backColorSel = self.backColorSelected
			bgpng = self.othPix
			if bgpng is not None and self.graphic:
				backColor = None
				backColorSel = None

		# box background
		if bgpng is not None and self.graphic:
			res.append(MultiContentEntryPixmapAlphaTest(
				pos=(left + self.BorderWidth, top + self.BorderWidth),
				size=(width - 2 * self.BorderWidth, height - 2 * self.BorderWidth),
				png=bgpng,
				flags=BT_SCALE))
		else:
			res.append(MultiContentEntryText(
				pos=(left, top), size=(width, height),
				font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
				text="", color=None, color_sel=None,
				backcolor=backColor, backcolor_sel=backColorSel,
				border_width=self.BorderWidth, border_color=self.borderColor))

		evX = left + self.BorderWidth + self.bouquetNamePadding
		evY = top + self.BorderWidth
		evW = width - 2 * (self.BorderWidth + self.bouquetNamePadding)
		evH = height - 2 * self.BorderWidth

		res.append(MultiContentEntryText(
			pos=(evX, evY), size=(evW, evH),
			font=0, flags=alignnment,
			text=name,
			color=foreColor, color_sel=foreColorSel,
			backcolor=backColor, backcolor_sel=backColorSel))

		# Borders
		if self.graphic:
			if borderTopPix is not None:
				res.append(MultiContentEntryPixmapAlphaTest(
						pos=(left, r1.y),
						size=(r1.w, self.BorderWidth),
						png=borderTopPix,
						flags=BT_SCALE))
			if borderBottomPix is not None:
				res.append(MultiContentEntryPixmapAlphaTest(
						pos=(left, r1.h - self.BorderWidth),
						size=(r1.w, self.BorderWidth),
						png=borderBottomPix,
						flags=BT_SCALE))
			if borderLeftPix is not None:
				res.append(MultiContentEntryPixmapAlphaTest(
						pos=(left, r1.y),
						size=(self.BorderWidth, r1.h),
						png=borderLeftPix,
						flags=BT_SCALE))
			if borderRightPix is not None:
				res.append(MultiContentEntryPixmapAlphaTest(
						pos=(r1.w - self.BorderWidth, left),
						size=(self.BorderWidth, r1.h),
						png=borderRightPix,
						flags=BT_SCALE))

		return res

	def fillBouquetList(self, bouquets):
		if self.graphic and not self.graphicsloaded:
			self.othPix = loadPNG(resolveFilename(SCOPE_GUISKIN, 'epg/OtherEvent.png'))
			self.selPix = loadPNG(resolveFilename(SCOPE_GUISKIN, 'epg/SelectedCurrentEvent.png'))

			self.borderTopPix = loadPNG(resolveFilename(SCOPE_GUISKIN, 'epg/BorderTop.png'))
			self.borderBottomPix = loadPNG(resolveFilename(SCOPE_GUISKIN, 'epg/BorderLeft.png'))
			self.borderLeftPix = loadPNG(resolveFilename(SCOPE_GUISKIN, 'epg/BorderBottom.png'))
			self.borderRightPix = loadPNG(resolveFilename(SCOPE_GUISKIN, 'epg/BorderRight.png'))
			self.borderSelectedTopPix = loadPNG(resolveFilename(SCOPE_GUISKIN, 'epg/SelectedBorderTop.png'))
			self.borderSelectedLeftPix = loadPNG(resolveFilename(SCOPE_GUISKIN, 'epg/SelectedBorderLeft.png'))
			self.borderSelectedBottomPix = loadPNG(resolveFilename(SCOPE_GUISKIN, 'epg/SelectedBorderBottom.png'))
			self.borderSelectedRightPix = loadPNG(resolveFilename(SCOPE_GUISKIN, 'epg/SelectedBorderRight.png'))

			self.graphicsloaded = True
		self.bouquetslist = bouquets
		self.l.setList(self.bouquetslist)
		self.selectionChanged()
		self.CurrentBouquetService = self.getCurrentBouquetService()

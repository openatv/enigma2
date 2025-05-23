#Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License
#
#Copyright (c) 2024-2025 jbleyel

#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#1. Non-Commercial Use: You may not use the Software or any derivative works
#   for commercial purposes without obtaining explicit permission from the
#   copyright holder.
#2. Share Alike: If you distribute or publicly perform the Software or any
#   derivative works, you must do so under the same license terms, and you
#   must make the source code of any derivative works available to the
#   public.
#3. Attribution: You must give appropriate credit to the original author(s)
#   of the Software by including a prominent notice in your derivative works.
#THE SOFTWARE IS PROVIDED "AS IS," WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE, AND NONINFRINGEMENT. IN NO EVENT SHALL
#THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES, OR
#OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT, OR OTHERWISE,
#ARISING FROM, OUT OF, OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
#OTHER DEALINGS IN THE SOFTWARE.
#
#For more details about the CC BY-NC-SA 4.0 License, please visit:
#https://creativecommons.org/licenses/by-nc-sa/4.0/

# This file also contains the previous code of ServiceList ( ServiceListLegacy ) based on multiple authors.

from os.path import exists
from time import time, localtime
from enigma import eLabel, eRect, eSize, eServiceReference, gFont, eListbox, eServiceCenter, eListboxPythonMultiContent, eListboxPythonServiceContent, eListboxServiceContent, eEPGCache, getDesktop, eTimer, loadPNG

from Components.GUIComponent import GUIComponent
from Components.config import config
from Components.MultiContent import MultiContentEntryProgress, MultiContentEntryText, MultiContentEntryRectangle, MultiContentEntryLinearGradient, MultiContentEntryLinearGradientAlphaBlend
from Components.Renderer.Picon import getPiconName
import NavigationInstance
from ServiceReference import ServiceReference
from skin import componentTemplates, getcomponentTemplate, parseColor, parseFont, parseListOrientation, reloadSkinTemplates, SizeTuple, SkinContext, SkinContextStack, TemplateParser
from timer import TimerEntry
from Tools.Directories import resolveFilename, SCOPE_GUISKIN
from Tools.LoadPixmap import LoadPixmap
from Tools.TextBoundary import getTextBoundarySize


class ServiceListTemplateParser(TemplateParser):
	def __init__(self, debug=False):
		TemplateParser.__init__(self, debug=debug)
		self.listHeight = 0
		self.listWidth = 0
		self.recordIndicatorMode = config.channelSelection.recordIndicatorMode.value
		self.widgetAttributes = {}
		self.widgetColors = ("recordColor", "streamColor", "pseudoColor", "serviceNotAvailColor", "fallbackColor", "recordColorSelected", "streamColorSelected", "pseudoColorSelected", "serviceNotAvailColorSelected", "fallbackColorSelected")

	def collectColors(self, attributes, widgetColors=None):
		return TemplateParser.collectColors(self, attributes, self.widgetColors)

	def collectAttributes(self, node, context, ignore=(), excludeItemIndexes=None, includeItemIndexes=None):
		attibutes = TemplateParser.collectAttributes(self, node=node, context=context, ignore=ignore, excludeItemIndexes=excludeItemIndexes, includeItemIndexes=includeItemIndexes)
		if config.channelSelection.showPicon.value:  # Calculatate Picon size based on the piconRatio setting
			ratio = config.channelSelection.piconRatio.value
			for attribute in attibutes:
				if attribute.get("index") == "Picon":
					size = attribute.get("size")
					if size and isinstance(size, tuple):
						size = (int(size[1] * ratio / 100), size[1])
						attribute["size"] = SizeTuple(size)
		return attibutes

	def readTemplate(self, templateName):
		indexMapping = {
			"Number": 0,
			"ServiceName": 1,
			"EntryName": 1,
			"MarkerName": 1,
			"FolderName": 1,
			"Picon": 2,
			"ServiceTypeImage": 3,
			"ServiceTypeName": 4,
			"RecordingIndicator": 5,
			"CryptoImage": 6,
			"ProviderName": 7,
			"FolderImage": 8,
			"MarkerImage": 9,
			"ServiceResolutionImage": 10,
			"IsInBouquetImage": 11,
			"Progress": 50,
			"ProgressText": 51,
			"Remain": 52,
			"RemainDuration": 53,
			"Elapsed": 54,
			"ElapsedDuration": 55,
			"ElapsedRemainDuration": 56
		}

		eventIndexMapping = {
			"Title": 1,
			"ShortDescription": 2,
			"ExtendedDescription": 3,
			"StartTime": 4,
			"EndTime": 5,
			"StartEndTime": 6,
			"Duration": 7,
			"StartTimeDuration": 8,
			"StartTimeEndTimeDuration": 9,
			"CoverImage": 10
		}

		def parseTemplateModes(template):
			modes = {}
			modesItems = {}
			maxEvents = 0
			excludeItemIndexes = []

			if not config.channelSelection.showPicon.value:
				excludeItemIndexes.append("Picon")
			if not config.channelSelection.showNumber.value:
				excludeItemIndexes.append("Number")
			if not config.channelSelection.showServiceTypeIcon.value:
				excludeItemIndexes.append("ServiceTypeImage")
			if not config.channelSelection.showCryptoIcon.value:
				excludeItemIndexes.append("CryptoImage")
			if self.recordIndicatorMode != 1:
				excludeItemIndexes.append("RecordingIndicator")

			for subMode in ("", "Marker", "Folder"):

				for mode in template.findall("mode"):

					modeName = mode.get("name")
					serviceName = "EntryName" if modeName == "other" else "ServiceName"
					subModeName = f"{subMode}Name" if subMode else ""

					includeItemIndexes = []
					optionalExcludeItemIndexes = ["MarkerName", "FolderName"]

					if subMode == "Marker":
						includeItemIndexes.append(serviceName)
						includeItemIndexes.append("MarkerImage")
					elif subMode == "Folder":
						includeItemIndexes.append(serviceName)
						includeItemIndexes.append("FolderImage")
					else:
						optionalExcludeItemIndexes.append("MarkerImage")
						optionalExcludeItemIndexes.append("FolderImage")

					items = []
					if modeName == "services":
						if config.channelSelection.showNumber.value and config.usage.numberMode.value != 2:
							optionalExcludeItemIndexes.append("Number")
						if subMode:
							continue
					else:
						modeName = f"{modeName}{subMode}"
						if subModeName and mode.findall(f".//text[@index='{subModeName}']"):
							includeItemIndexes.remove(serviceName)
							includeItemIndexes.append(subModeName)
							optionalExcludeItemIndexes.remove(subModeName)

					itemHeight = int(mode.get("itemHeight", self.listHeight))
					itemWidth = int(mode.get("itemWidth", self.listWidth))
					attibutes = self.widgetAttributes.copy()
					for name, value in mode.items():
						attibutes[name] = value
					modes[modeName] = attibutes
					context = SkinContextStack()
					context.x = 0
					context.y = 0
					context.w = itemWidth
					context.h = itemHeight
					context = SkinContext(context, "0,0", f"{itemWidth},{itemHeight}")
					for element in list(mode):
						processor = self.processors.get(element.tag, self.processNone)
						newitems = processor(element, context, excludeItemIndexes=excludeItemIndexes + optionalExcludeItemIndexes, includeItemIndexes=includeItemIndexes)
						if newitems:
							items += newitems

					newitems = []
					if self.debug:
						print("[ServiceListTemplateParser] DEBUG newitems")
						print(items)
					for item in items:
						itemsAttibutes = {}
						for name, value in item.items():
							eventIndex = 0
							if name in "font":
								itemsAttibutes[name] = int(value)
								continue
							if name in ("index", "autoFit"):
								eventIndexValue = value[-1:]
								if eventIndexValue.isdigit():
									eventIndex = int(eventIndexValue) * 100
									if eventIndex > maxEvents:
										maxEvents = eventIndex
									value = value[:-1]
							if name == "index":
								if self.debug:
									print(f"[ServiceListTemplateParser] DEBUG name {name} / eventIndex {eventIndex}")
								if eventIndex:
									itemsAttibutes["index"] = eventIndexMapping.get(value, -1) + eventIndex
								else:
									itemsAttibutes["index"] = indexMapping.get(value, -1)
							elif name == "autoFit":
								if eventIndex:
									itemsAttibutes["autoFitIndex"] = eventIndexMapping.get(value, -1) + eventIndex
								else:
									itemsAttibutes["autoFitIndex"] = indexMapping.get(value, -1)
							else:
								itemsAttibutes[name] = value
						newitems.append(itemsAttibutes)

					modesItems[modeName] = newitems
					attibutes["maxevents"] = maxEvents / 100
					modes[modeName] = attibutes
					if self.debug:
						print(f"[ServiceListTemplateParser] DEBUG ITEMS {modeName}")
						print(modesItems[modeName])
			return modes, modesItems

		templatemodes = {}
		templatemodesitems = {}
		selectedtemplate = getcomponentTemplate("serviceList", templateName)

		if selectedtemplate is not None:
			self.fonts = {}
			try:
				for index, font in enumerate(selectedtemplate.get("fonts", "").split(",")):
					self.fonts[index] = parseFont(font)
					self.l.setFont(index, self.fonts.get(index))

				# Calculate serviceNumber Size
				try:
					serviceNumberObjects = selectedtemplate.findall(".//text[@value='Number']")
					for serviceNumberObject in serviceNumberObjects:
						serviceNumberFont = int(serviceNumberObject.get("font"))
						serviceNumberWidth = config.usage.alternative_number_mode.value and getTextBoundarySize(self.instance, self.fonts.get(serviceNumberFont), self.instance.size(), "0" * config.usage.numberZapDigits.value).width() or getTextBoundarySize(self.instance, self.fonts.get(serviceNumberFont), self.instance.size(), "00000").width()
						size = serviceNumberObject.attrib["size"].split(",")
						if int(size[0]) < serviceNumberWidth:
							serviceNumberObject.attrib["size"] = f"{serviceNumberWidth},{size[1]}"
				except Exception as err:
					print(f"[ServiceListTemplateParser] ERROR setting serviceNumberWidth. {err}")

				# Calculate servicelist column Size
				try:
					serviceNameWidth = int(config.usage.servicelist_column.value)
					if serviceNameWidth != -1:
						bouquets = selectedtemplate.findall(".//mode[@value='bouquets']")
						if bouquets:
							serviceNameObjects = bouquets.findall(".//text[@value='ServiceName']")
							for serviceNameObject in serviceNameObjects:
								size = serviceNameObject.attrib["size"].split(",")
								serviceNameObject.attrib["size"] = f"{serviceNameWidth},{size[1]}"
								serviceNameObject.attrib["autoFit"] = ""
				except Exception as err:
					print(f"[ServiceListTemplateParser] ERROR setting serviceNameWidth. {err}")

				templatemodes, templatemodesitems = parseTemplateModes(selectedtemplate)

				# self.orientation = selectedtemplate.get("orientation", "vertical")
				self.templateDefaultsServices = templatemodes.get("services")
				self.templateDefaultsBouquets = templatemodes.get("bouquets")
				self.templateDefaultsOther = templatemodes.get("other")
				self.templateDataServices = templatemodesitems.get("services")
				self.templateDataBouquets = templatemodesitems.get("bouquets")
				self.templateDataBouquetsMarker = templatemodesitems.get("bouquetsMarker")
				self.templateDataBouquetsFolder = templatemodesitems.get("bouquetsFolder")
				self.templateDataOther = templatemodesitems.get("other")
				self.templateDataOtherMarker = templatemodesitems.get("otherMarker")
				self.templateDataOtherFolder = templatemodesitems.get("otherFolder")
			except Exception as err:
				print(f"[ServiceListTemplateParser] ERROR parsing Template. {err}")

		else:
			print(f"[ServiceListTemplateParser] ERROR Template '{templateName}' not found")


def refreshServiceList(configElement=None):
	from Screens.InfoBar import InfoBar
	InfoBarInstance = InfoBar.instance
	if InfoBarInstance is not None:
		servicelist = InfoBarInstance.servicelist
		if servicelist:
			servicelist.setMode()


class ServiceListBase(GUIComponent):
	MODE_NORMAL = 0
	MODE_FAVOURITES = 1
	MODE_ALL = 2

	MODE_OTHER = 0
	MODE_BOUQUETS = 1
	MODE_SERVICES = 2

	GUI_WIDGET = eListbox

	def __init__(self, serviceList):
		self.serviceList = serviceList
		GUIComponent.__init__(self)
		self.onSelectionChanged = []
		self.root = None
		self.mode = self.MODE_OTHER
		self.picFolder = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "icons/folder.png"))
		self.picMarker = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "icons/marker.png"))
		self.picDVB_S = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "icons/ico_dvb-s.png"))
		self.picDVB_C = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "icons/ico_dvb-c.png"))
		self.picDVB_T = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "icons/ico_dvb-t.png"))
		self.picServiceGroup = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "icons/ico_service_group.png"))
		self.picCrypto = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "icons/icon_crypt.png"))
		self.picRecord = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "icons/record.png"))
		self.picFavorites = LoadPixmap(path=resolveFilename(SCOPE_GUISKIN, "icons/epgclock_primetime.png"))  # TODO

	def connectSelChanged(self, fnc):
		if fnc not in self.onSelectionChanged:
			self.onSelectionChanged.append(fnc)

	def disconnectSelChanged(self, fnc):
		if fnc in self.onSelectionChanged:
			self.onSelectionChanged.remove(fnc)

	def selectionChanged(self):
		for x in self.onSelectionChanged:
			x()

	def isVertical(self):
		return self.l.getOrientation() == eListbox.orVertical

	def isHorizontal(self):
		return self.l.getOrientation() == eListbox.orHorizontal

	def isGrid(self):
		return self.l.getOrientation() == eListbox.orGrid

	def sort(self):
		self.l.sort()

	def fillFinished(self):
		self.l.FillFinished()

	def getNext(self):
		r = eServiceReference()
		self.l.getNext(r)
		return r

	def getPrev(self):
		r = eServiceReference()
		self.l.getPrev(r)
		return r

	def selectionEnabled(self, enabled):
		if self.instance is not None:
			self.instance.setSelectionEnable(enabled)

	def setCurrentMarked(self, state):  # Just for movemode / only one marked entry
		self.l.setCurrentMarked(state)

	def getMarked(self):
		i = self.l
		i.markedQueryStart()
		ref = eServiceReference()
		marked = []
		while i.markedQueryNext(ref) == 0:
			marked.append(ref.toString())
			ref = eServiceReference()
		return marked

	def addService(self, service, beforeCurrent=False):
		self.l.addService(service, beforeCurrent)

	def finishFill(self):
		self.l.FillFinished()
		self.l.sort()

	def clearMarks(self):  # Stuff for multiple marks (edit mode / later multiepg)
		self.l.initMarked()

	def isMarked(self, ref):
		return self.l.isMarked(ref)

	def addMarked(self, ref):
		self.l.addMarked(ref)

	def removeMarked(self, ref):
		self.l.removeMarked(ref)

	def setRoot(self, root, justSet=False):
		self.root = root
		self.l.setRoot(root, justSet)
		if not justSet:
			self.l.sort()
		self.selectionChanged()

	def resetRoot(self):
		index = self.instance.getCurrentIndex()
		self.l.setRoot(self.root, False)
		self.l.sort()
		self.instance.moveSelectionTo(index)

	def removeCurrent(self):
		self.l.removeCurrent()

	def getRoot(self):
		return self.root

	def getRootServices(self):
		serviceHandler = eServiceCenter.getInstance()
		items = serviceHandler.list(self.root)
		dest = []
		if items is not None:
			while True:
				s = items.getNext()
				if s.valid():
					dest.append(s.toString())
				else:
					break
		return dest

	def preWidgetRemove(self, instance):
		instance.setContent(None)
		instance.selectionChanged.get().remove(self.selectionChanged)

	def getCurrent(self):
		r = eServiceReference()
		self.l.getCurrent(r)
		return r

	def getList(self):
		return self.l.getList()

	def atBegin(self):
		return self.instance.atBegin()

	def atEnd(self):
		return self.instance.atEnd()

	def moveToChar(self, char):
		# TODO fill with life
		print("Next char: ")
		index = self.l.getNextBeginningWithChar(char)
		indexup = self.l.getNextBeginningWithChar(char.upper())
		if indexup != 0 and (index > indexup or index == 0):
			index = indexup

		self.instance.moveSelectionTo(index)
		print("Moving to character %s" % str(char))

	def moveToNextMarker(self):
		idx = self.l.getNextMarkerPos()
		self.instance.moveSelectionTo(idx)

	def moveToPrevMarker(self):
		idx = self.l.getPrevMarkerPos()
		self.instance.moveSelectionTo(idx)

	def moveToIndex(self, index):
		self.instance.moveSelectionTo(index)

	def getCurrentIndex(self):
		return self.instance.getCurrentIndex()

	def setCurrent(self, ref, adjust=True):
		if self.l.setCurrent(ref):
			return None
		from Components.ServiceEventTracker import InfoBarCount
		if adjust and config.usage.multibouquet.value and InfoBarCount == 1 and ref and ref.type != 8192:
			print("[servicelist] search for service in userbouquets")
			isRadio = ref.toString().startswith("1:0:2:") or ref.toString().startswith("1:0:A:")
			if self.serviceList:
				revert_mode = config.servicelist.lastmode.value
				revert_root = self.getRoot()
				if not isRadio:
					self.serviceList.setModeTv()
					revert_tv_root = self.getRoot()
					bouquets = self.serviceList.getBouquetList()
					for bouquet in bouquets:
						self.serviceList.enterUserbouquet(bouquet[1])
						if self.l.setCurrent(ref):
							config.servicelist.lastmode.save()
							self.serviceList.saveChannel(ref)
							return True
					self.serviceList.enterUserbouquet(revert_tv_root)
				else:
					self.serviceList.setModeRadio()
					revert_radio_root = self.getRoot()
					bouquets = self.serviceList.getBouquetList()
					for bouquet in bouquets:
						self.serviceList.enterUserbouquet(bouquet[1])
						if self.l.setCurrent(ref):
							config.servicelist.lastmode.save()
							self.serviceList.saveChannel(ref)
							return True
					self.serviceList.enterUserbouquet(revert_radio_root)
				print("[servicelist] service not found in any userbouquets")
				if revert_mode == "tv":
					self.serviceList.setModeTv()
				elif revert_mode == "radio":
					self.serviceList.setModeRadio()
				self.serviceList.enterUserbouquet(revert_root)
		return False

	def setHideNumberMarker(self, value):
		self.l.setHideNumberMarker(value)

	# Navigation Actions
	def goTop(self):
		self.instance.goTop()

	def goPageUp(self):
		self.instance.goPageUp()

	def goLineUp(self):
		self.instance.goLineUp()

	def goFirst(self):
		self.instance.goFirst()

	def goLeft(self):
		self.instance.goLeft()

	def goRight(self):
		self.instance.goRight()

	def goLast(self):
		self.instance.goLast()

	def goLineDown(self):
		self.instance.goLineDown()

	def goPageDown(self):
		self.instance.goPageDown()

	def goBottom(self):
		self.instance.goBottom()

	# Old method names. This methods should be found and removed from all code.
	#

	def moveUp(self):
		self.instance.goLineUp()

	def moveDown(self):
		self.instance.goLineDown()

	def moveTop(self):
		self.instance.goTop()

	def moveEnd(self):
		self.instance.goBottom()


class ServiceListLegacy(ServiceListBase):

	def __init__(self, serviceList):
		ServiceListBase.__init__(self, serviceList)
		self.l = eListboxServiceContent()

		if self.picFolder:
			self.l.setPixmap(self.l.picFolder, self.picFolder)

		if self.picMarker:
			self.l.setPixmap(self.l.picMarker, self.picMarker)

		if self.picDVB_S:
			self.l.setPixmap(self.l.picDVB_S, self.picDVB_S)

		if self.picDVB_C:
			self.l.setPixmap(self.l.picDVB_C, self.picDVB_C)

		if self.picDVB_C:
			self.l.setPixmap(self.l.picDVB_T, self.picDVB_T)

		if self.picServiceGroup:
			self.l.setPixmap(self.l.picServiceGroup, self.picServiceGroup)

		pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/ico_stream.png"))
		if pic:
			self.l.setPixmap(self.l.picStream, pic)

		pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/icon_crypt.png"))
		if pic:
			self.l.setPixmap(self.l.picCrypto, pic)

		pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/record.png"))
		if pic:
			self.l.setPixmap(self.l.picRecord, pic)

		self.listHeight = 0
		self.listWidth = 0
		self.ServiceNumberFontName = "Regular"
		self.ServiceNumberFontSize = 20
		self.ServiceNameFontName = "Regular"
		self.ServiceNameFontSize = 22
		self.ServiceInfoFontName = "Regular"
		self.ServiceInfoFontSize = 18
		self.progressInfoFontName = "Regular"
		self.progressInfoFontSize = -1
		self.progressBarWidth = 52
		self.fieldMargins = 10
		self.itemsDistances = 8
		self.listMarginRight = 25  # scrollbar is fixed 20 + 5 Extra marge
		self.listMarginLeft = 5

	def reloadSkin(self):
		pass

	def applySkin(self, desktop, parent):
		def foregroundColorMarked(value):
			self.l.setColor(eListboxServiceContent.markedForeground, parseColor(value))

		def foregroundColorMarkedSelected(value):
			self.l.setColor(eListboxServiceContent.markedForegroundSelected, parseColor(value))

		def backgroundColorMarked(value):
			self.l.setColor(eListboxServiceContent.markedBackground, parseColor(value))

		def backgroundColorMarkedSelected(value):
			self.l.setColor(eListboxServiceContent.markedBackgroundSelected, parseColor(value))

		def foregroundColorServiceNotAvail(value):
			self.l.setColor(eListboxServiceContent.serviceNotAvail, parseColor(value))

		def foregroundColorEvent(value):
			self.l.setColor(eListboxServiceContent.eventForeground, parseColor(value))

		def colorServiceDescription(value):
			self.l.setColor(eListboxServiceContent.serviceDescriptionColor, parseColor(value))

		def foregroundColorEventSelected(value):
			self.l.setColor(eListboxServiceContent.eventForegroundSelected, parseColor(value))

		def colorServiceDescriptionSelected(value):
			self.l.setColor(eListboxServiceContent.serviceDescriptionColorSelected, parseColor(value))

		def foregroundColorEventborder(value):
			self.l.setColor(eListboxServiceContent.eventborderForeground, parseColor(value))

		def foregroundColorEventborderSelected(value):
			self.l.setColor(eListboxServiceContent.eventborderForegroundSelected, parseColor(value))

		def colorEventProgressbar(value):
			self.l.setColor(eListboxServiceContent.serviceEventProgressbarColor, parseColor(value))

		def colorEventProgressbarSelected(value):
			self.l.setColor(eListboxServiceContent.serviceEventProgressbarColorSelected, parseColor(value))

		def colorEventProgressbarBorder(value):
			self.l.setColor(eListboxServiceContent.serviceEventProgressbarBorderColor, parseColor(value))

		def colorEventProgressbarBorderSelected(value):
			self.l.setColor(eListboxServiceContent.serviceEventProgressbarBorderColorSelected, parseColor(value))

		def colorServiceRecorded(value):
			self.l.setColor(eListboxServiceContent.serviceRecorded, parseColor(value))

		def colorServicePseudoRecorded(value):
			self.l.setColor(eListboxServiceContent.servicePseudoRecorded, parseColor(value))

		def colorServiceStreamed(value):
			self.l.setColor(eListboxServiceContent.serviceStreamed, parseColor(value))

		def colorFallbackItem(value):
			self.l.setColor(eListboxServiceContent.serviceItemFallback, parseColor(value))

		def colorServiceSelectedFallback(value):
			self.l.setColor(eListboxServiceContent.serviceSelectedFallback, parseColor(value))

		def colorServiceDescriptionFallback(value):
			self.l.setColor(eListboxServiceContent.eventForegroundFallback, parseColor(value))

		def colorServiceDescriptionSelectedFallback(value):
			self.l.setColor(eListboxServiceContent.eventForegroundSelectedFallback, parseColor(value))

		def colorServiceRecording(value):
			self.l.setColor(eListboxServiceContent.serviceRecordingColor, parseColor(value))

		def colorServiceWithAdvertisment(value):
			self.l.setColor(eListboxServiceContent.serviceAdvertismentColor, parseColor(value))

		def picServiceEventProgressbar(value):
			pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, value))
			pic and self.l.setPixmap(self.l.picServiceEventProgressbar, pic)

		def serviceItemHeight(value):
			self.ItemHeight = int(value)

		def serviceNameFont(value):
			font = parseFont(value, ((1, 1), (1, 1)))
			self.ServiceNameFontName = font.family
			self.ServiceNameFontSize = font.pointSize

		def serviceInfoFont(value):
			font = parseFont(value, ((1, 1), (1, 1)))
			self.ServiceInfoFontName = font.family
			self.ServiceInfoFontSize = font.pointSize

		def serviceNumberFont(value):
			font = parseFont(value, ((1, 1), (1, 1)))
			self.ServiceNumberFontName = font.family
			self.ServiceNumberFontSize = font.pointSize

		def progressInfoFont(value):
			font = parseFont(value, ((1, 1), (1, 1)))
			self.progressInfoFontName = font.family
			self.progressInfoFontSize = font.pointSize

		def progressbarHeight(value):
			self.l.setProgressbarHeight(int(value))

		def progressbarBorderWidth(value):
			self.l.setProgressbarBorderWidth(int(value))

		def progressBarWidth(value):
			self.progressBarWidth = int(value)

		def fieldMargins(value):
			self.fieldMargins = int(value)

		def listMarginRight(value):
			self.listMarginRight = int(value)

		def listMarginLeft(value):
			self.listMarginLeft = int(value)

		def nonplayableMargins(value):
			self.l.setNonplayableMargins(int(value))

		def itemsDistances(value):
			self.itemsDistances = int(value)
			self.l.setItemsDistances(self.itemsDistances)
		if self.skinAttributes is not None:
			for (attrib, value) in list(self.skinAttributes):
				try:
					locals().get(attrib)(value)
					self.skinAttributes.remove((attrib, value))
				except Exception:
					pass
		rc = GUIComponent.applySkin(self, desktop, parent)
		self.listHeight = self.instance.size().height()
		self.listWidth = self.instance.size().width()
		self.setItemsPerPage()
		self.setFontsize()
		return rc

	def isVertical(self):
		return True

	def isHorizontal(self):
		return False

	def isGrid(self):
		return False

	def setItemsPerPage(self):
		if self.listHeight > 0:
			itemHeight = self.listHeight // (config.usage.serviceitems_per_page_twolines.value if config.usage.servicelist_twolines.value else config.usage.serviceitems_per_page.value)
		else:
			itemHeight = 28
		self.ItemHeight = itemHeight
		self.l.setItemHeight(itemHeight)
		if self.listHeight:
			self.instance.resize(eSize(self.listWidth, self.listHeight // itemHeight * itemHeight))

	def setFontsize(self):
		self.ServiceNumberFont = gFont(self.ServiceNumberFontName, self.ServiceNumberFontSize + config.usage.servicenum_fontsize.value)
		self.ServiceNameFont = gFont(self.ServiceNameFontName, self.ServiceNameFontSize + config.usage.servicename_fontsize.value)
		self.ServiceInfoFont = gFont(self.ServiceInfoFontName, self.ServiceInfoFontSize + config.usage.serviceinfo_fontsize.value)
		if self.progressInfoFontSize == -1:  # font in skin not defined
			self.ProgressInfoFont = gFont(self.ServiceInfoFontName, self.ServiceInfoFontSize + config.usage.progressinfo_fontsize.value)
		else:
			self.ProgressInfoFont = gFont(self.progressInfoFontName, self.progressInfoFontSize + config.usage.progressinfo_fontsize.value)

		self.l.setElementFont(self.l.celServiceName, self.ServiceNameFont)
		self.l.setElementFont(self.l.celServiceNumber, self.ServiceNumberFont)
		self.l.setElementFont(self.l.celServiceInfo, self.ServiceInfoFont)

	def postWidgetCreate(self, instance):
		instance.setContent(self.l)
		instance.selectionChanged.get().append(self.selectionChanged)
		self.setFontsize()
		self.setMode(self.mode)

	def setPlayableIgnoreService(self, ref):
		self.l.setIgnoreService(ref)

	def setMode(self, mode):
		self.mode = mode
		if mode == self.MODE_SERVICES:  # Mode all is not supported in legacy mode
			self.mode = self.MODE_OTHER
		self.setItemsPerPage()
		self.l.setItemHeight(self.ItemHeight)
		self.l.setVisualMode(eListboxServiceContent.visModeComplex)
		self.l.setServicePiconDownsize(int(config.usage.servicelist_picon_downsize.value))
		self.l.setServicePiconRatio(int(config.usage.servicelist_picon_ratio.value))

		twoLines = config.usage.servicelist_twolines.value
		self.l.setShowTwoLines(twoLines)

		if config.usage.service_icon_enable.value:
			self.l.setGetPiconNameFunc(getPiconName)
		else:
			self.l.setGetPiconNameFunc(None)

		rowWidth = self.instance.size().width() - self.listMarginRight

		if mode != self.MODE_BOUQUETS or not config.usage.show_channel_numbers_in_servicelist.value:
			channelNumberWidth = 0
			channelNumberSpace = self.listMarginLeft
		else:
			channelNumberWidth = config.usage.alternative_number_mode.value and getTextBoundarySize(self.instance, self.ServiceNumberFont, self.instance.size(), "0" * config.usage.numberZapDigits.value).width() or getTextBoundarySize(self.instance, self.ServiceNumberFont, self.instance.size(), "00000").width()
			channelNumberSpace = self.fieldMargins + self.listMarginLeft

		numberHeight = self.ItemHeight // 2 if twoLines and config.usage.servicelist_servicenumber_valign.value == "1" else self.ItemHeight
		self.l.setElementPosition(self.l.celServiceNumber, eRect(self.listMarginLeft, 0, channelNumberWidth, numberHeight))

		#progress view modes for two lines
		#  0 - single, centered
		# 10 - single, upper line
		#  1 - dual, bar upper line, value lower line
		#  2 - dual, value upper line, bar lower line
		# 11 - dual, bar and value upper line
		# 12 - dual, value and bar upper line
		if twoLines:
			viewMode, viewType = (config.usage.servicelist_eventprogress_valign.value + config.usage.servicelist_eventprogress_view_mode.value).split('_')
			viewMode = int(viewMode)
		else:
			viewType = config.usage.show_event_progress_in_servicelist.value
			viewMode = 0

		self.l.setProgressViewMode(viewMode)

		minuteUnit = _("min")
		self.l.setProgressUnit(minuteUnit if "mins" in viewType else "%")

		progressHeight = self.ItemHeight // 2 if viewMode else self.ItemHeight
		progressTextWidth = getTextBoundarySize(self.instance, self.ProgressInfoFont, self.instance.size(), "+000 %s" % minuteUnit).width() if "mins" in viewType else getTextBoundarySize(self.instance, self.ProgressInfoFont, self.instance.size(), "100 %").width()
		self.l.setProgressTextWidth(progressTextWidth)

		if "bar" in viewType:
			if viewMode and viewMode < 10:
				progressWidth = max(self.progressBarWidth, progressTextWidth)
			elif viewMode > 10:
				progressWidth = self.progressBarWidth + progressTextWidth + self.itemsDistances
			else:
				progressWidth = self.progressBarWidth
		else:
			progressWidth = progressTextWidth

		if "left" in viewType:
			self.l.setElementPosition(self.l.celServiceEventProgressbar, eRect(channelNumberWidth + channelNumberSpace, 0, progressWidth, progressHeight))
			self.l.setElementPosition(self.l.celServiceName, eRect(channelNumberWidth + channelNumberSpace + progressWidth + self.fieldMargins, 0, rowWidth - (channelNumberWidth + channelNumberSpace + progressWidth + self.fieldMargins), self.ItemHeight))
		elif "right" in viewType:
			self.l.setElementPosition(self.l.celServiceEventProgressbar, eRect(rowWidth - progressWidth, 0, progressWidth, progressHeight))
			self.l.setElementPosition(self.l.celServiceName, eRect(channelNumberWidth + channelNumberSpace, 0, rowWidth - (channelNumberWidth + channelNumberSpace + progressWidth + self.fieldMargins), self.ItemHeight))
		else:
			self.l.setElementPosition(self.l.celServiceEventProgressbar, eRect(0, 0, 0, 0))
			self.l.setElementPosition(self.l.celServiceName, eRect(channelNumberWidth + channelNumberSpace, 0, rowWidth - (channelNumberWidth + channelNumberSpace), self.ItemHeight))
		if "perc" in viewType or "mins" in viewType:
			self.l.setElementFont(self.l.celServiceEventProgressbar, self.ProgressInfoFont)

		self.l.setElementFont(self.l.celServiceName, self.ServiceNameFont)
		self.l.setElementFont(self.l.celServiceNumber, self.ServiceNumberFont)
		self.l.setElementFont(self.l.celServiceInfo, self.ServiceInfoFont)

		self.l.setHideNumberMarker(config.usage.hide_number_markers.value)
		self.l.setServiceTypeIconMode(int(config.usage.servicetype_icon_mode.value))
		self.l.setCryptoIconMode(int(config.usage.crypto_icon_mode.value))
		self.l.setRecordIndicatorMode(int(config.usage.record_indicator_mode.value))
		self.l.setColumnWidth(-1 if twoLines else int(config.usage.servicelist_column.value))


class ServiceList(ServiceListBase, ServiceListTemplateParser):

	def __init__(self, serviceList):
		ServiceListBase.__init__(self, serviceList)
		ServiceListTemplateParser.__init__(self, config.crash.debugScreens.value)

		self.session = serviceList.session
		self.l = eListboxPythonServiceContent()
		self.l.setBuildFunc(self.buildEntry)
		self.list = []
		self.size = 0
		self.ItemHeight = 20
		self.service_center = eServiceCenter.getInstance()
		self.numberoffset = 0
		self.PlayableIgnoreService = eServiceReference()
		self.recordingList = {}
		if self.session:
			self.session.nav.RecordTimer.on_state_change.append(self.onTimerEntryStateChange)
		config.channelSelection.showTimers.addNotifier(self.getRecordingList, initial_call=True)

		self.desktopWidth = getDesktop(0).size().width()
		self.reloadTimer = eTimer()
		self.reloadTimer.callback.append(self.doReload)
		self.skinAttributes = None

	def getRecordingList(self, configElement=None):
		self.recordingList = {}
		if config.channelSelection.showTimers.value:
			if NavigationInstance.instance.getAnyRecordingsCount():
				for timer in NavigationInstance.instance.RecordTimer.timer_list:
					if timer.state == TimerEntry.StateRunning and not timer.justplay and hasattr(timer, "Filename"):
						self.recordingList[str(timer.service_ref)] = 1

	def onTimerEntryStateChange(self, timer):
		if config.channelSelection.showTimers.value:
			if hasattr(timer, "Filename") and not timer.justplay and timer.state == TimerEntry.StateRunning:
				self.recordingList[str(timer.service_ref)] = 1
			else:
				if str(timer.service_ref) in self.recordingList:
					del self.recordingList[str(timer.service_ref)]

	def setItemSize(self, configElement=None):
		try:
			if self.mode == self.MODE_BOUQUETS:
				template = self.templateDefaultsBouquets
			elif self.mode == self.MODE_SERVICES:
				template = self.templateDefaultsServices
			else:
				template = self.templateDefaultsOther
			self.ItemHeight = int(template.get("itemHeight", 20))
			self.ItemWidth = int(template.get("itemWidth", 20))
			orientation = template.get("orientation", "vertical")
			self.l.setOrientation(parseListOrientation(orientation))
			self.l.setItemHeight(int(template.get("itemHeight", 20)))
			self.l.setItemWidth(int(template.get("itemWidth", 20)))
		except Exception:
			pass

	def buildOptionEntryDisplay(self, event, isPlayable, mode):
		# Current
		# 50 # Progress
		# 51 # ProgressText
		# 52 # Remain
		# 53 # Remain / Duration
		# 54 # Elapsed
		# 55 # Elapsed / Duration
		# 56 # Elapsed / Remain / Duration

		# EPG
		# 101 = Title
		# 102 = ShortDescription
		# 103 = ExtendedDescription
		# 104 = StartTime
		# 105 = EndTime
		# 106 = StartEndTime
		# 107 = Duration
		# 108 = StartTime+duration
		# 109 = StartTime+endTime+duration
		# 110 = CoverImage # TODO

		# 20X -> second event
		# 30X -> 3rd event
		# 40X -> 4rd event
		# 50X -> 5th event
		# 90X -> 9th event
		# XXX -> primetime event # TODO

		if not (event and isPlayable):
			return "", 0

		def _calcTextWidth(text, font, size):
			if size:
				self.textRenderer.resize(size)
			if font:
				self.textRenderer.setFont(font)
			self.textRenderer.setText(text)
			return self.textRenderer.calculateSize().width()

		addtimedisplayWidth = 0
		addtimedisplay = ""
		# textTpl = ""
		# maxTimeValue = 9999

		match mode:
			case 1:  # Title
				addtimedisplay = event[2]
			case 2:  # ShortDescription
				addtimedisplay = event[3].replace("\n", " ")
			case 3:  # ExtendedDescription
				addtimedisplay = event[4]
			case 4:  # StartTime
				beginTime = localtime(event[0])
				addtimedisplay = "%02d:%02d" % (beginTime[3], beginTime[4])
			case 5:  # EndTime
				endTime = localtime(event[0] + event[1])
				addtimedisplay = "%02d:%02d" % (endTime[3], endTime[4])
			case 6:  # StartEndTime
				beginTime = localtime(event[0])
				endTime = localtime(event[0] + event[1])
				addtimedisplay = "%02d:%02d - %02d:%02d" % (beginTime[3], beginTime[4], endTime[3], endTime[4])
			case 7:  # Duration
				duration = int(event[1] // 60)
				addtimedisplay = f"{duration} min"
			case 8:  # StartTime+duration
				beginTime = localtime(event[0])
				duration = int(event[1] // 60)
				addtimedisplay = "%02d:%02d / %d min" % (beginTime[3], beginTime[4], duration)
			case 9:  # StartTime+endTime+duration
				beginTime = localtime(event[0])
				endTime = localtime(event[0] + event[1])
				duration = int(event[1] // 60)
				addtimedisplay = "%02d:%02d - %02d:%02d / %d min" % (beginTime[3], beginTime[4], endTime[3], endTime[4], duration)
			case 51:  # Percent text
				now = int(time())
				percent = 100 * (now - event[0]) // event[1]
				addtimedisplay = "%d%%" % percent
			case 52:  # Remain
				now = int(time())
				remain = int((event[0] + event[1] - now) // 60)
				addtimedisplay = "+%d min" % remain
			case 53:  # Remain / Duration
				now = int(time())
				remain = int((event[0] + event[1] - now) // 60)
				duration = int(event[1] // 60)
				addtimedisplay = "+%d/%d min" % (remain, duration)
			case 54:  # Elapsed
				now = int(time())
				elapsed = int((now - event[0]) // 60)
				addtimedisplay = "%d min" % (elapsed,)
			case 55:  # Elapsed / Duration
				now = int(time())
				elapsed = int((now - event[0]) // 60)
				duration = int(event[1] // 60)
				addtimedisplay = "%d/%d min" % (elapsed, duration)
			case 56:  # Elapsed / Remain / Duration
				now = int(time())
				elapsed = int((now - event[0]) // 60)
				remain = int((event[0] + event[1] - now) // 60)
				duration = int(event[1] // 60)
				addtimedisplay = "%d/+%d/%d min" % (elapsed, remain, duration)

		# addtimedisplayWidth = self._calcTextWidth(textTpl, font=self.additionalInfoFont, size=eSize(self.desktopWidth // 3, 0))
		return addtimedisplay, addtimedisplayWidth

	def buildOptionEntryServicePicon(self, service):
		if service.flags & eServiceReference.mustDescent:
			alist = ServiceReference(service).list()
			first_in_alternative = alist and alist.getNext()
			service_str = first_in_alternative.toString() if first_in_alternative else service.toString()
		else:
			service_str = service.toString()
		picon = getPiconName(service_str)
		if exists(picon):
			return loadPNG(picon)
		return None

	def buildOptionEntryServicePixmap(self, service):
		pixmap = None
		if service.flags & eServiceReference.isMarker:
			pixmap = self.picMarker
		elif service.flags & eServiceReference.isGroup:
			pixmap = self.picServiceGroup
		elif service.flags & eServiceReference.isDirectory:
			pixmap = self.picFolder
		else:
			orbpos = service.getUnsignedData(4) >> 16
			if orbpos == 0xFFFF:
				pixmap = self.picDVB_C
			elif orbpos == 0xEEEE:
				pixmap = self.picDVB_T
			else:
				pixmap = self.picDVB_S
		return pixmap

	def buildOptionEntryServiceResolutionPixmap(self, service):  # TODO Resolution type icon
		pixmap = None
		# resolutionType = service.getUnsignedData(2)
		return pixmap

	def buildOptioncheckHasRecordings(self, service, isPlayable):
		if config.channelSelection.showTimers.value:
			if service.toString() in self.recordingList:
				return True
			if isPlayable and len(self.recordingList) and service.flags & eServiceReference.mustDescent:
				alist = ServiceReference(service).list()
				while True:
					aservice = alist.getNext()
					if not aservice.valid():
						break
					if aservice.toString() in self.recordingList:
						return True
		return False

	def reloadSkin(self):
		if componentTemplates.isChanged():
			reloadSkinTemplates(clear=True)
			self.readTemplate(config.channelSelection.widgetStyle.value)

	def applySkin(self, desktop, parent):
		attribs = []

		attributeMapping = {
			"foregroundColorServiceNotAvail": "serviceNotAvailColor",
			"colorServiceRecording": "recordColor",
			"colorServiceRecorded": "recordColor",
			"colorServicePseudoRecorded": "pseudoColor",
			"colorServiceStreamed": "streamColor",
			"colorFallbackItem": "fallbackColor",
			"colorServiceSelectedFallback": "fallbackColorSelected"
		}

		self.widgetAttributes["recordColor"] = "#00b40431"
		self.widgetAttributes["streamColor"] = "#00f56712"
		self.widgetAttributes["pseudoColor"] = "#0041b1ec"
		self.widgetAttributes["serviceNotAvailColor"] = "#00bbbbbb"

		self.widgetAttributes["recordColorSelected"] = "#00b40431"
		self.widgetAttributes["streamColorSelected"] = "#00f56712"
		self.widgetAttributes["pseudoColorSelected"] = "#0041b1ec"
		self.widgetAttributes["serviceNotAvailColorSelected"] = "#00bbbbbb"

		for (attrib, value) in self.skinAttributes:
			# Color attributes
			newattrib = attributeMapping.get(attrib, attrib)

			if newattrib in ("foregroundColorMarked", "foregroundColorMarkedSelected", "backgroundColorMarked", "backgroundColorMarkedSelected") + self.widgetColors:
				self.widgetAttributes[newattrib] = value
				continue

			# LEGACY attributes will be ignored
			if attrib.startswith("colorEventProgressbar"):
				continue

			if attrib.startswith("progressBar"):
				continue

			if attrib.startswith("foregroundColorEvent"):
				continue

			if attrib.startswith("colorServiceDescription"):
				continue

			if attrib.endswith("Font"):
				continue

			if attrib in ("listMarginLeft", "listMarginRight", "fieldMargins", "itemsDistances", "nonplayableMargins", "serviceItemHeight", "picServiceEventProgressbar", "colorServiceWithAdvertisment"):
				continue
			else:
				attribs.append((attrib, value))

		self.skinAttributes = attribs
		rc = GUIComponent.applySkin(self, desktop, parent)
		self.listHeight = self.instance.size().height()
		self.listWidth = self.instance.size().width()
		self.readTemplate(config.channelSelection.widgetStyle.value)
		return rc

	def onShow(self):
		GUIComponent.onShow(self)
		self.resetReloadTimer()

	def onHide(self):
		GUIComponent.onHide(self)
		self.reloadTimer.stop()

	def doReload(self):
		self.l.refresh()
		self.resetReloadTimer()

	def resetReloadTimer(self):
		self.reloadTimer.stop()
		# TODO enable this if code is finshed
		#self.reloadTimer.startLongTimer(60 - datetime.now().second)

	def postWidgetCreate(self, instance):
		instance.setContent(self.l)
		instance.selectionChanged.get().append(self.selectionChanged)
		self.setMode(self.mode)
		self.l.setHideNumberMarker(config.usage.hide_number_markers.value)
		self.textRenderer = eLabel(self.instance)
		self.textRenderer.resize(eSize(self.desktopWidth // 3, 0))
		self.textRenderer.hide()

	def setNumberOffset(self, offset):
		self.numberoffset = offset

	def setPlayableIgnoreService(self, ref):
		self.PlayableIgnoreService = ref

	def setMode(self, mode):
		self.mode = mode
		self.setItemSize()
		self.l.setRecordIndicatorMode(self.recordIndicatorMode)
		self.l.setHideNumberMarker(config.usage.hide_number_markers.value)

	def setFontsize(self):  # This is a dummy function and not used for new servicelist
		pass

	def setItemsPerPage(self):  # This is currently not implemented and will maybe never be implemented
		pass

	def buildEntry(self, service, status):
		# Status bitmask
		# 1 isSlected
		# 2 isMarked
		# 4 isMarker
		# 8 isPlayable
		# 16 isRecorded
		# 32 isStreamed
		# 64 isPseudoRecorded
		# 128 isFolder
		# 256 isInBouquet

		def resolveColor(color):
			if isinstance(color, str):
				try:
					return parseColor(color).argb()
				except Exception as err:
					print(f"[ServiceList] Error: Resolve color '{err}'")
				return None
			return color

		def getRecordColors(foreColor, foreColorSelected, status, defaults, attributes):
			if self.recordIndicatorMode == 2 and (status & 2) == 0:  # don't set extra colors if marked
				isRecorded = status & 16
				isStreamed = status & 32
				isPseudoRecorded = status & 64
				if isRecorded:
					foreColor = attributes.get("recordColor", defaults.get("recordColor", foreColor))
					foreColorSelected = attributes.get("recordColorSelected", defaults.get("recordColorSelected", foreColorSelected))
				if isStreamed:
					foreColor = attributes.get("streamColor", defaults.get("streamColor", foreColor))
					foreColorSelected = attributes.get("streamColorSelected", defaults.get("streamColorSelected", foreColorSelected))
				if isPseudoRecorded:
					foreColor = attributes.get("pseudoColor", defaults.get("pseudoColor", foreColor))
					foreColorSelected = attributes.get("pseudoColorSelected", defaults.get("pseudoColorSelected", foreColorSelected))
			return foreColor, foreColorSelected

		def getColor(defaults, attributes, serviceAvail, marked):
			if marked:
				foregroundColor = attributes.get("foregroundColorMarked", defaults.get("foregroundColorMarked"))
				backgroundColor = attributes.get("backgroundColorMarked", defaults.get("backgroundColorMarked"))
				foregroundColorSelected = attributes.get("foregroundColorMarkedAndSelected", defaults.get("foregroundColorMarkedAndSelected"))
				backgroundColorSelected = attributes.get("backgroundColorMarkedAndSelected", defaults.get("backgroundColorMarkedAndSelected"))
			else:
				foregroundColor = attributes.get("foregroundColor", defaults.get("foregroundColor"))
				backgroundColor = attributes.get("backgroundColor", defaults.get("backgroundColor"))
				foregroundColorSelected = attributes.get("foregroundColorSelected", defaults.get("foregroundColorSelected"))
				backgroundColorSelected = attributes.get("backgroundColorSelected", defaults.get("backgroundColorSelected"))

				if serviceAvail == 1:
					foregroundColor = defaults.get("serviceNotAvailColor", foregroundColor)
					foregroundColorSelected = defaults.get("serviceNotAvailColorSelected", foregroundColor)
				elif serviceAvail == 2:
					foregroundColor = defaults.get("fallbackColor", foregroundColor)
					foregroundColorSelected = defaults.get("fallbackColorSelected", foregroundColor)

			return foregroundColor, backgroundColor, foregroundColorSelected, backgroundColorSelected

		# selected = status & 1
		marked = status & 2
		isMarker = status & 4
		isPlayable = status & 8
		isFolder = status & 128

		# rowwidth = self.l.getItemSize().width()
		# rowheight = self.l.getItemSize().height()
		res = [None]

		info = self.service_center.info(service)
		crypted = not isMarker and not isFolder and info and info.isCrypted()
		serviceName = info and info.getName(service) or "<n/a>"

		isPlayableValue = 0
		serviceAvail = 0
		if not marked and isPlayable and info:
			oldref = self.PlayableIgnoreService or eServiceReference()
			isPlayableValue = info.isPlayable(service, oldref)
			if isPlayableValue == 0:
				serviceAvail = 1
			elif isPlayableValue == 2:
				serviceAvail = 2

		events = []
		serviceNumber = ""
		if self.mode == self.MODE_BOUQUETS:
			if isMarker:
				templateItems = self.templateDataBouquetsMarker
			elif isFolder:
				templateItems = self.templateDataBouquetsFolder
			else:
				templateItems = self.templateDataBouquets
			defaults = self.templateDefaultsBouquets
			maxEvents = defaults.get("maxevents")
			if not isMarker and maxEvents:
				events = eEPGCache.getInstance().lookupEvent(["BDTS%d" % maxEvents, (service.toString(), 0, -1, 360)])
				serviceNumber = service.getChannelNum()
		elif self.mode == self.MODE_SERVICES:
			events = eEPGCache.getInstance().lookupEvent(["BDTS1", (service.toString(), 0, -1, 360)])
			defaults = self.templateDefaultsServices
			templateItems = self.templateDataServices
			serviceNumber = service.getChannelNum()
		else:
			defaults = self.templateDefaultsOther
			if isMarker:
				templateItems = self.templateDataOtherMarker
			elif isFolder:
				templateItems = self.templateDataOtherFolder
			else:
				templateItems = self.templateDataOther

		autoFitData = {}

		try:
			for item in templateItems:
				itemType = item.get("type", "")
				itemIndex = item.get("index", -1)
				if itemIndex == 11 and not status & 256:  # IsInBouquetImage
					continue
				if itemIndex == 5 and not status & 112:  # RecordingIndicator
					continue
				if itemIndex == 6 and not crypted:
					continue
				if itemIndex > 0:
					eventIndex = itemIndex // 100
					if eventIndex > 0:
						eventIndex -= 1
					currentEvent = events[eventIndex] if eventIndex < len(events) else None
				else:
					currentEvent = None
				font = item.get("font", 0)
				size = item.get("size")
				pos = item.get("position")
				flags = item.get("_flags", 0)
				foregroundColor, backgroundColor, foregroundColorSelected, backgroundColorSelected = getColor(defaults, item, serviceAvail, marked)
				cornerRadius, cornerEdges = item.get("_radius", (0, 0))

				if itemType == "rect":
					gradientDirection, gradientAlpha, gradientStart, gradientEnd, gradientMid, gradientStartSelected, gradientEndSelected, gradientMidSelected = item.get("_gradient", (0, 0, None, None, None, None, None, None))
					if gradientDirection:
						if gradientAlpha:
							res.append((MultiContentEntryLinearGradientAlphaBlend(pos=pos, size=size, direction=gradientDirection, startColor=gradientStart, midColor=gradientMid, endColor=gradientEnd, startColorSelected=gradientStartSelected, midColorSelected=gradientMidSelected, endColorSelected=gradientEndSelected, cornerRadius=cornerRadius, cornerEdges=cornerEdges)))
						else:
							res.append((MultiContentEntryLinearGradient(pos=pos, size=size, direction=gradientDirection, startColor=gradientStart, midColor=gradientMid, endColor=gradientEnd, startColorSelected=gradientStartSelected, midColorSelected=gradientMidSelected, endColorSelected=gradientEndSelected, cornerRadius=cornerRadius, cornerEdges=cornerEdges)))
					else:
						borderColor = item.get("borderColor", defaults.get("borderColor"))
						borderColorSelected = item.get("borderColorSelected", defaults.get("borderColorSelected"))
						res.append((MultiContentEntryRectangle(pos=pos, size=size, backgroundColor=foregroundColor, backgroundColorSelected=foregroundColorSelected, borderWidth=borderWidth, borderColor=borderColor, borderColorSelected=borderColorSelected, cornerRadius=cornerRadius, cornerEdges=cornerEdges)))

				elif itemType == "text":
					autoFit = item.get("autoFitIndex", -1)
					if autoFit > -1:
						w = getTextBoundarySize(None, font=self.fonts.get(font), targetSize=eSize(size[0], size[1]), text=serviceName, nowrap=True).width()
						# print("autoFit serviceName %s %s -> %s" % (serviceName, size[0], w))
						if w < size[0]:
							autoFitData[autoFit] = size[0] - w
						elif size[0] < w:
							diff = w - size[0]
							size = (w, size[1])
							autoFitData[autoFit] = 0 - diff
					elif autoFitData.get(itemIndex):
						w = autoFitData.get(itemIndex)
						pos = (pos[0] - w, pos[1])
						size = (size[0] + w, size[1])
					foregroundColorRecord, foregroundColorSelected = getRecordColors(foregroundColor, foregroundColorSelected, status, defaults, item)

					if itemIndex == 0 and serviceNumber:  # Number
						res.append((MultiContentEntryText(pos=pos, size=size, font=font, flags=flags, text=str(serviceNumber), color=foregroundColorRecord, color_sel=foregroundColorSelected, backcolor=backgroundColor, backcolor_sel=backgroundColorSelected)))
					if itemIndex == 1 and serviceName:  # ServiceName
						res.append((MultiContentEntryText(pos=pos, size=size, font=font, flags=flags, text=serviceName, color=foregroundColorRecord, color_sel=foregroundColorSelected, backcolor=backgroundColor, backcolor_sel=backgroundColorSelected)))

					if itemIndex > 49 and currentEvent and isPlayable:
						if itemIndex > 100:
							itemIndex -= (itemIndex // 100) * 100
						addtimedisplay, addtimedisplayWidth = self.buildOptionEntryDisplay(currentEvent, isPlayable, itemIndex)
						res.append((MultiContentEntryText(pos=pos, size=size, font=font, flags=flags, text=addtimedisplay, color=foregroundColor, color_sel=foregroundColorSelected, backcolor=backgroundColor, backcolor_sel=backgroundColorSelected)))

					if item.get("text", ""):  # Any other text
						res.append((MultiContentEntryText(pos=pos, size=size, font=font, flags=flags, text=item.get("text", ""), color=foregroundColor, color_sel=foregroundColorSelected, backcolor=backgroundColor, backcolor_sel=backgroundColorSelected)))

				elif itemType == "pixmap":

					pixmapType = item.get("pixmapType", eListboxPythonMultiContent.TYPE_PIXMAP)
					pixmapFlags = item.get("pixmapFlags", 0)

					if backgroundColor:
						backgroundColor = resolveColor(backgroundColor)
					if backgroundColorSelected:
						backgroundColorSelected = resolveColor(backgroundColorSelected)

					if itemIndex == 2:  # Picon
						picon = self.buildOptionEntryServicePicon(service)
						if picon:
							res.append((pixmapType, pos[0], pos[1], size[0], size[1], picon, backgroundColor, backgroundColorSelected, pixmapFlags, cornerRadius, cornerEdges))
					elif itemIndex == 3:  # ServiceTypeImage
						pixmap = self.buildOptionEntryServicePixmap(service)
						if pixmap:
							res.append((pixmapType, pos[0], pos[1], size[0], size[1], pixmap, backgroundColor, backgroundColorSelected, pixmapFlags, cornerRadius, cornerEdges))
					elif itemIndex == 10:  # ServiceResolutionImage
						pixmap = self.buildOptionEntryServiceResolutionPixmap(service)
						if pixmap:
							res.append((pixmapType, pos[0], pos[1], size[0], size[1], pixmap, backgroundColor, backgroundColorSelected, pixmapFlags, cornerRadius, cornerEdges))
					else:
						pixmaps = {
							5: self.picRecord,  # RecordingIndicator
							6: self.picCrypto,  # CryptoImage
							8: self.picFolder,  # FolderImage
							9: self.picMarker,  # MarkerImage
							11: self.picFavorites  # IsInBouquetImage
						}
						picon = pixmaps.get(itemIndex, None)
						if picon:
							res.append((pixmapType, pos[0], pos[1], size[0], size[1], picon, backgroundColor, backgroundColorSelected, pixmapFlags, cornerRadius, cornerEdges))

				elif itemType == "progress" and itemIndex == 50 and currentEvent and isPlayable:
					if currentEvent[1]:
						gradientDirection, gradientAlpha, gradientStart, gradientEnd, gradientMid, gradientStartSelected, gradientEndSelected, gradientMidSelected = item.get("_gradient", (0, 0, None, None, None, None, None, None))
						now = int(time())
						percent = 100 * (now - currentEvent[0]) // currentEvent[1]
						borderWidth = int(item.get("borderWidth", 0))
						borderColor = item.get("borderColor", defaults.get("borderColor")) if borderWidth else None
						borderColorSelected = item.get("borderColorSelected", defaults.get("borderColorSelected")) if borderWidth else None
						res.append((MultiContentEntryProgress(pos=pos, size=size, percent=percent, borderWidth=borderWidth, foreColor=foregroundColor, foreColorSelected=foregroundColorSelected, backColor=backgroundColor, backColorSelected=backgroundColor, borderColor=borderColor, borderColorSelected=borderColorSelected, startColor=gradientStart, midColor=gradientMid, endColor=gradientEnd, startColorSelected=gradientStartSelected, midColorSelected=gradientMidSelected, endColorSelected=gradientEndSelected, cornerRadius=cornerRadius, cornerEdges=cornerEdges)))

		except Exception:
			import traceback
			traceback.print_exc()

		return res

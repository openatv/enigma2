from enigma import eListbox, eListboxPythonMultiContent, BT_ALIGN_CENTER, iPlayableService, iRecordableService, eServiceReference, iServiceInformation, gFont, RT_HALIGN_LEFT, RT_VALIGN_CENTER, RT_VALIGN_TOP, RT_HALIGN_CENTER, eTimer, getDesktop, eSize, eStreamServer
from skin import parseScale, applySkinFactor, parseColor, parseFont, parameters

from Components.Addons.GUIAddon import GUIAddon
from Components.Converter.ServiceInfo import getVideoHeight
from Components.Converter.VAudioInfo import StdAudioDesc
from Components.Label import Label
from Components.MultiContent import MultiContentEntryPixmapAlphaBlend, MultiContentEntryText
from Components.ServiceEventTracker import ServiceEventTracker
from Components.Sources.StreamService import StreamServiceList
from Components.NimManager import nimmanager
from Screens.InfoBarGenerics import hasActiveSubservicesForCurrentChannel
from Tools.Directories import resolveFilename, SCOPE_GUISKIN
from Tools.GetEcmInfo import createCurrentCaidLabel
from Tools.LoadPixmap import LoadPixmap
from Tools.Hex2strColor import Hex2strColor

import NavigationInstance
import re


class ServiceInfoBar(GUIAddon):
	def __init__(self):
		GUIAddon.__init__(self)
		self.nav = NavigationInstance.instance
		self.nav.record_event.append(self.gotRecordEvent)
		self.refreshCryptoInfo = eTimer()
		self.refreshCryptoInfo.callback.append(self.checkCrypto_update)
		self.refreshAddon = eTimer()
		self.refreshAddon.callback.append(self.updateAddon)
		self.elements = []
		self.l = eListboxPythonMultiContent()  # noqa: E741
		self.l.setBuildFunc(self.buildEntry)
		self.l.setItemHeight(36)
		self.l.setItemWidth(36)
		self.spacing = applySkinFactor(10)
		self.orientations = {"orHorizontal": eListbox.orHorizontal, "orVertical": eListbox.orVertical}
		self.orientation = eListbox.orHorizontal
		self.alignment = "left"
		self.pixmaps = {}
		self.pixmapsDisabled = {}
		self.separatorLineColor = 0xC0C0C0
		self.foreColor = 0xFFFFFF
		self.textBackColor = None
		self.separatorLineThickness = 0
		self.autoresizeMode = "auto"  # possible values: auto, fixed, condensed
		self.font = gFont("Regular", 18)
		self.__event_tracker = None
		self.currentCrypto = ""
		self.tuner_string = ""
		self.textRenderer = Label("")
		self.permanentIcons = []
		self.records_running = 0
		self.streamServer = eStreamServer.getInstance()
		self.currentServiceSource = None
		self.frontendInfoSource = None
		self.isCryptedDetected = False
		self.tunerColors = parameters.get("FrontendInfoColors", (0x0000FF00, 0x00FFFF00, 0x007F7F7F))  # tuner active, busy, available colors

	def onContainerShown(self):
		self.textRenderer.GUIcreate(self.relatedScreen.instance)
		self.l.setItemHeight(self.instance.size().height())
		self.l.setItemWidth(self.instance.size().width())
		self.updateAddon()
		if not self.__event_tracker:
			self.__event_tracker = ServiceEventTracker(screen=self.relatedScreen,
				eventmap={
					iPlayableService.evStart: self.scheduleAddonUpdate,
					iPlayableService.evEnd: self.scheduleAddonUpdate,
					iPlayableService.evUpdatedInfo: self.scheduleAddonUpdate,
					iPlayableService.evVideoSizeChanged: self.updateAddon,
					iPlayableService.evHBBTVInfo: self.scheduleAddonUpdate,
					iPlayableService.evNewProgramInfo: self.scheduleAddonUpdate,
					iPlayableService.evCuesheetChanged: self.scheduleAddonUpdate,
					iPlayableService.evTunedIn: self.scheduleAddonUpdate,
				}
			)
		self.currentServiceSource = self.source.screen["CurrentService"]
		if self.currentServiceSource and self.updateAddon not in self.currentServiceSource.onManualNewService:
			self.currentServiceSource.onManualNewService.append(self.scheduleAddonUpdate)
		self.frontendInfoSource = self.source.screen["FrontendInfo"]

	def destroy(self):
		self.nav.record_event.remove(self.gotRecordEvent)
		self.refreshCryptoInfo.stop()
		self.refreshAddon.stop()
		self.refreshCryptoInfo.callback.remove(self.checkCrypto_update)
		self.refreshAddon.callback.remove(self.updateAddon)
		GUIAddon.destroy(self)

	GUI_WIDGET = eListbox

	def remove_doubles(self, a_list):
		duplicate = None
		for item in a_list:
			if duplicate != item:
				duplicate = item
				yield item

	def gotRecordEvent(self, service, event):
		prevRecords = self.records_running
		if event in (iRecordableService.evEnd, iRecordableService.evStart, None):
			recs = self.nav.getRecordings()
			self.records_running = len(recs)
			if self.records_running != prevRecords:
				self.updateAddon()

	def scheduleAddonUpdate(self):
		if hasattr(self, "refreshAddon"):
			self.refreshAddon.stop()
			self.refreshAddon.start(200)

	def checkCrypto_update(self):
		if NavigationInstance.instance is not None:
			service = NavigationInstance.instance.getCurrentService()
			info = service and service.info()
			if info:
				newCrypto = createCurrentCaidLabel(info)
				if newCrypto != self.currentCrypto and self.isCryptedDetected:
					self.currentCrypto = newCrypto
					self.updateAddon()

	def updateAddon(self):
		self.refreshAddon.stop()

		filteredElements = []

		for x in self.elements:
			enabledKey = self.detectVisible(x) if x != "separator" else "separator"
			is_off = enabledKey and "_off" in enabledKey
			enabledKey = enabledKey and enabledKey.replace("_off", "")
			if enabledKey:
				if not is_off:
					filteredElements.append(enabledKey)
			elif self.autoresizeMode in ["auto", "fixed"] or (x in self.permanentIcons and not is_off):
				filteredElements.append(x + "!")

		filteredElements = list(self.remove_doubles(filteredElements))

		if filteredElements[-1] == "separator" and len(filteredElements) > 1 and filteredElements[len(filteredElements) - 2] != "currentCrypto":
			del filteredElements[-1]

		l_list = []
		l_list.append((filteredElements,))
		self.l.setList(l_list)

	def detectVisible(self, key):
		if self.nav is not None:
			service = self.nav.getCurrentService()
			pending_service_ref = self.nav.getCurrentServiceReferenceOriginal()
			pending_sref = pending_service_ref and pending_service_ref.toString() or ""
			info = service and service.info()
			isRef = isinstance(service, eServiceReference)
			# self.current_info = info
			if not info:
				return None

			if "%3a//" in pending_sref and pending_service_ref and not pending_service_ref.getStreamRelay():
				self.isCryptedDetected = False

			video_height = None
			# video_aspect = None
			video_height = getVideoHeight(info)
			if key == "videoRes":
				if video_height >= 720 and video_height < 1500:
					return "IS_HD"
				elif video_height >= 1500:
					return "IS_4K"
				else:
					return "IS_SD"
			elif key == "txt":
				tpid = info.getInfo(iServiceInformation.sTXTPID)
				if tpid > 0 and tpid < 100000:
					return key
			elif key == "dolby" and not isRef:
				audio = service.audioTracks()
				if audio:
					n = audio.getNumberOfTracks()
					idx = 0
					while idx < n:
						i = audio.getTrackInfo(idx)
						description = StdAudioDesc(i.getDescription())
						if description and description.split()[0] in ("AC4", "AAC+", "AC3", "AC3+", "Dolby", "DTS", "DTS-HD", "HE-AAC", "IPCM", "LPCM", "WMA Pro"):
							return key
						idx += 1
			elif key == "crypt" and not isRef:
				if "%3a//" in pending_sref and pending_service_ref and not pending_service_ref.getStreamRelay():
					return key + "_off"
				if info.getInfo(iServiceInformation.sIsCrypted) == 1:
					self.isCryptedDetected = True
					return key
			elif key == "audiotrack" and not isRef:
				audio = service.audioTracks()
				if bool(audio) and audio.getNumberOfTracks() > 1:
					return key
			elif key == "subtitletrack" and not isRef:
				subtitle = service and service.subtitle()
				subtitlelist = subtitle and subtitle.getSubtitleList()
				if subtitlelist and len(subtitlelist) > 0:
					return key
			elif key == "hbbtv" and not isRef:
				if info.getInfoString(iServiceInformation.sHBBTVUrl) != "":
					return key
			elif key == "subservices" and not isRef:
				if hasActiveSubservicesForCurrentChannel(service):
					return key
			elif key == "stream" and not isRef:
				if self.streamServer is None:
					return None
				if service.streamed() is not None and ((self.streamServer.getConnectedClients() or StreamServiceList) and True or False):
					return key
			elif key == "currentCrypto":
				if "%3a//" in pending_sref and pending_service_ref and not pending_service_ref.getStreamRelay():
					self.refreshCryptoInfo.stop()
					self.currentCrypto = ""
					return key + "_off"
				if not isRef:
					self.currentCrypto = createCurrentCaidLabel(info)
				self.refreshCryptoInfo.start(1000)
				return key
			elif key == "record":
				self.gotRecordEvent(None, None)
				if self.records_running > 0:
					return key
			elif key == "gamma" and not isRef:
				if info.getInfo(iServiceInformation.sGamma) == 1:
					return "IS_HDR"
				if info.getInfo(iServiceInformation.sGamma) == 2:
					return "IS_HDR10"
				if info.getInfo(iServiceInformation.sGamma) == 3:
					return "IS_HLG"
			elif key == "tuners":
				string = ""
				if self.frontendInfoSource:
					for n in nimmanager.nim_slots:
						if n.enabled:
							if n.slot == self.frontendInfoSource.slot_number:
								color = Hex2strColor(self.tunerColors[0])
							elif self.frontendInfoSource.tuner_mask & 1 << n.slot:
								color = Hex2strColor(self.tunerColors[1])
							else:
								continue
							if string:
								string += " "
							string += color + chr(ord("A") + n.slot)
					self.tuner_string = string
				if string:
					return key
			elif key == "catchup":
				match = re.search(r"catchupdays=(\d*)", pending_sref)
				if match and int(match.group(1)) > 0:
					return key
			elif key == "servicetype":
				if "%3a//" in pending_sref.lower() and pending_service_ref and not pending_service_ref.getStreamRelay():
					return "iptv"
				elif not isRef:
					if self.frontendInfoSource:
						tuner_system = self.frontendInfoSource.frontend_type
						if tuner_system:
							if "DVB-S" in tuner_system:
								return "sat"
							elif "DVB-C" in tuner_system:
								return "cable"
							elif "DVB-T" in tuner_system:
								return "terestrial"

		return None

	def buildEntry(self, sequence):
		xPos = self.instance.size().width() if self.alignment == "right" else 0
		yPos = 0

		res = [None]

		for x in sequence:
			enabledKey = x
			isOn = True
			if x[-1] == "!":
				enabledKey = enabledKey.rstrip("!")
				isOn = False

			pic = None
			if isOn:
				if enabledKey in self.pixmaps:
					pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, self.pixmaps[enabledKey]))
			else:
				if enabledKey == "videoRes":
					enabledKey = "IS_HD"
				if enabledKey in self.pixmaps:
					pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, self.pixmaps[enabledKey]))
				if enabledKey in self.pixmapsDisabled:
					pic = LoadPixmap(resolveFilename(SCOPE_GUISKIN, self.pixmapsDisabled[enabledKey]))

			if enabledKey != "separator" and enabledKey != "currentCrypto" and enabledKey != "tuners":
				if pic:
					pixd_size = pic.size()
					pixd_width = pixd_size.width()
					pixd_height = pixd_size.height()
					pic_x_pos = (xPos - pixd_width) if self.alignment == "right" else xPos
					pic_y_pos = yPos + (self.instance.size().height() - pixd_height) // 2
					res.append(MultiContentEntryPixmapAlphaBlend(
						pos=(pic_x_pos, pic_y_pos),
						size=(pixd_width, pixd_height),
						png=pic,
						backcolor=None, backcolor_sel=None, flags=BT_ALIGN_CENTER))
					if self.alignment == "right":
						xPos -= pixd_width + self.spacing
					else:
						xPos += pixd_width + self.spacing
			else:
				if enabledKey == "separator":
					res.append(MultiContentEntryText(
						pos=(xPos - self.separatorLineThickness, yPos), size=(self.separatorLineThickness, self.instance.size().height()),
						font=0, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
						text="",
						color=self.separatorLineColor, color_sel=self.separatorLineColor,
						backcolor=self.separatorLineColor, backcolor_sel=self.separatorLineColor))
					if self.alignment == "right":
						xPos -= self.separatorLineThickness + self.spacing
					else:
						xPos += self.separatorLineThickness + self.spacing
				else:
					res_string = ""
					if enabledKey == "tuners":
						res_string = self.tuner_string
					else:
						res_string = self.currentCrypto
					if res_string:
						textWidth = self._calcTextWidth(res_string, font=self.font, size=eSize(self.getDesktopWith() // 3, 0))
						res.append(MultiContentEntryText(
							pos=(xPos - textWidth - 2, yPos - 2), size=(textWidth + 2, self.instance.size().height()),
							font=0, flags=RT_HALIGN_CENTER | RT_VALIGN_TOP,
							text=res_string,
							color=self.foreColor, color_sel=self.foreColor,
							textBWidth=1, textBColor=0x000000,
							backcolor=self.textBackColor, backcolor_sel=self.textBackColor))
						if self.alignment == "right":
							xPos -= textWidth + self.spacing
						else:
							xPos += textWidth + self.spacing
		return res

	def getDesktopWith(self):
		return getDesktop(0).size().width()

	def _calcTextWidth(self, text, font=None, size=None):
		if size:
			self.textRenderer.instance.resize(size)
		if font:
			self.textRenderer.instance.setFont(font)
		self.textRenderer.text = text
		return self.textRenderer.instance.calculateSize().width()

	def postWidgetCreate(self, instance):
		instance.setSelectionEnable(False)
		instance.setContent(self.l)
		instance.allowNativeKeys(False)

	def applySkin(self, desktop, parent):
		attribs = []
		for (attrib, value) in self.skinAttributes[:]:
			if attrib == "pixmaps":
				self.pixmaps = {k: v for k, v in (item.split(':') for item in value.split(','))}
			if attrib == "pixmapsDisabled":
				self.pixmapsDisabled = {k: v for k, v in (item.split(':') for item in value.split(','))}
			elif attrib == "spacing":
				self.spacing = parseScale(value)
			elif attrib == "alignment":
				self.alignment = value
			elif attrib == "orientation":
				self.orientation = self.orientations.get(value, self.orientations["orHorizontal"])
				if self.orientation == eListbox.orHorizontal:
					self.instance.setOrientation(eListbox.orVertical)
					self.l.setOrientation(eListbox.orVertical)
				else:
					self.instance.setOrientation(eListbox.orHorizontal)
					self.l.setOrientation(eListbox.orHorizontal)
			elif attrib == "elements":
				self.elements = value.split(",")
			elif attrib == "separatorLineColor":
				self.foreColor = parseColor(value).argb()
			elif attrib == "separatorLineThickness":
				self.separatorLineThickness = parseScale(value)
			elif attrib == "autoresizeMode":
				self.autoresizeMode = value
			elif attrib == "font":
				self.font = parseFont(value, parent.scale)
			elif attrib == "foregroundColor":
				self.foreColor = parseColor(value).argb()
			elif attrib == "textBackColor":
				self.textBackColor = parseColor(value).argb()
			elif attrib == "permanent":
				self.permanentIcons = value.split(",")
			else:
				attribs.append((attrib, value))
		self.skinAttributes = attribs
		self.l.setFont(0, self.font)
		return GUIAddon.applySkin(self, desktop, parent)

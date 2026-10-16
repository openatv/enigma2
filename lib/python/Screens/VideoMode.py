from os.path import exists

from enigma import eAVControl, eDVBDB, eServiceCenter, eServiceReference, eTimer, iPlayableService, iServiceInformation

import NavigationInstance
from Components.AVSwitch import avSwitch
from Components.config import ConfigNothing, config, configfile
from Components.ConfigList import ConfigListScreen
from Components.Converter.PliExtraInfo import CODEC_NAMES
from Components.Label import Label
from Components.ServiceEventTracker import ServiceEventTracker
from Components.SystemInfo import BoxInfo
from Screens.ChannelSelection import FLAG_IS_DEDICATED_3D
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Setup import Setup
from Tools.Directories import fileReadLine, fileWriteLine, isPluginInstalled

MODULE_NAME = __name__.split(".")[-1]

resolutionlabel = None


def getAutoresPluginEnabled():
	try:
		return config.plugins.autoresolution.enable.value
	except Exception:
		return False


class VideoSettings(Setup):
	def __init__(self, session):
		config.av.autores_preview.value = False
		self.currentMode = None
		Setup.__init__(self, session, "Video")
		# Handle hot-plug by re-creating setup.
		self.onShow.append(self.startHotplug)
		self.onHide.append(self.stopHotplug)
		self.grabLastGoodMode()

	def startHotplug(self):
		avSwitch.on_hotplug.append(self.hotplug)

	def stopHotplug(self):
		avSwitch.on_hotplug.remove(self.hotplug)

	def hotplug(self, what):
		self.createSetup()

	def createSetup(self, appendItems=None, prependItems=None):
		level = config.usage.setup_level.index
		port = config.av.videoport.value
		items = [
			(_("Video output"), config.av.videoport, _("Configures which video output connector will be used."))
		]
		if port in ("HDMI", "YPbPr", "Scart-YPbPr") and not getAutoresPluginEnabled():
			modes = avSwitch.readAvailableModes()
			items.append((_("Automatic resolution"), config.av.autores, _("If enabled the output resolution of the receiver will try to match the resolution of the video contents resolution.")))
			if config.av.autores.value in ("all", "hd"):
				items.extend((
					(_("Delay time"), config.av.autores_delay, _("Set the time before checking video source for resolution information.")),
					(_("Automatic resolution label"), config.av.autores_label_timeout, _("Allows you to adjust the amount of time the resolution information display on screen.")),
					(_("Force de-interlace"), config.av.autores_deinterlace, _("If enabled the video will always be de-interlaced.")),
					(_("Always use smart1080p mode"), config.av.smart1080p, _("This option allows you to always use e.g. 1080p50 for TV/.ts, and 1080p24/p50/p60 for videos"))
				))
				if config.av.autores.value == "hd":
					items.append((_("Show SD as"), config.av.autores_sd, _("This option allows you to choose how to display standard definition video on your TV.")))
				items.extend((
					(_("Show 480/576p 24fps as"), config.av.autores_480p24, _("This option allows you to choose how to display SD progressive 24Hz on your TV. (as not all TV's support these resolutions)")),
					(_("Show 720p 24fps as"), config.av.autores_720p24, _("This option allows you to choose how to display 720p 24Hz on your TV. (as not all TV's support these resolutions)")),
					(_("Show 1080p 24fps as"), config.av.autores_1080p24, _("This option allows you to choose how to display 1080p 24Hz on your TV. (as not all TV's support these resolutions)")),
					(_("Show 1080p 25fps as"), config.av.autores_1080p25, _("This option allows you to choose how to display 1080p 25Hz on your TV. (as not all TV's support these resolutions)")),
					(_("Show 1080p 30fps as"), config.av.autores_1080p30, _("This option allows you to choose how to display 1080p 30Hz on your TV. (as not all TV's support these resolutions)"))
				))
				if "2160p24" in modes:
					items.extend((
						(_("Show 2160p 24fps as"), config.av.autores_2160p24, _("This option allows you to choose how to display 2160p 24Hz on your TV. (as not all TV's support these resolutions)")),
						(_("Show 2160p 25fps as"), config.av.autores_2160p25, _("This option allows you to choose how to display 2160p 25Hz on your TV. (as not all TV's support these resolutions)")),
						(_("Show 2160p 30fps as"), config.av.autores_2160p30, _("This option allows you to choose how to display 2160p 30Hz on your TV. (as not all TV's support these resolutions)"))
					))
			elif config.av.autores.value == "simple":
				items.extend((
					(_("Delay time"), config.av.autores_delay, _("Set the time before checking video source for resolution information.")),
					(_("Automatic resolution label"), config.av.autores_label_timeout, _("Allows you to adjust the amount of time the resolution information display on screen."))
				))
				self.prevSd = self.prevHd = self.prevFhd = self.prevUhd = ""
				service = self.session.nav.getCurrentService()
				info = service and service.info()
				if info:
					videoHeight = int(info.getInfo(iServiceInformation.sVideoHeight))
					if videoHeight <= 576:
						self.prevSd = "* "
					elif videoHeight <= 720:
						self.prevHd = "* "
					elif videoHeight <= 1080:
						self.prevFhd = "* "
					elif videoHeight <= 2160:
						self.prevUhd = "* "
					else:
						config.av.autores_preview.value = False
					items.append((_("Enable preview"), config.av.autores_preview, _("Show preview of current mode (*)."), "check"))
				else:
					config.av.autores_preview.value = False
				self.getVerifyVideomode(config.av.autores_mode_sd, config.av.autores_rate_sd)
				items.extend((
					(pgettext(_("Video output mode for SD"), _("%sMode for SD (up to 576p)") % self.prevSd), config.av.autores_mode_sd[port], _("This option configures the video output mode (or resolution)."), "check_sd"),
					(_("%sRefresh rate for SD") % self.prevSd, config.av.autores_rate_sd[config.av.autores_mode_sd[port].value], _("Configure the refresh rate of the screen."), "check_sd")
				))
				if "720p" in modes:
					self.getVerifyVideomode(config.av.autores_mode_hd, config.av.autores_rate_hd)
					items.extend((
						(pgettext(_("Video output mode for HD"), _("%sMode for HD (up to 720p)") % self.prevHd), config.av.autores_mode_hd[port], _("This option configures the video output mode (or resolution)."), "check_hd"),
						(_("%sRefresh rate for HD") % self.prevHd, config.av.autores_rate_hd[config.av.autores_mode_hd[port].value], _("Configure the refresh rate of the screen."), "check_hd")
					))
				if "1080i" in modes or "1080p" in modes:
					self.getVerifyVideomode(config.av.autores_mode_fhd, config.av.autores_rate_fhd)
					items.extend((
						(pgettext(_("Video output mode for FHD"), _("%sMode for FHD (up to 1080p)") % self.prevFhd), config.av.autores_mode_fhd[port], _("This option configures the video output mode (or resolution)."), "check_fhd"),
						(_("%sRefresh rate for FHD") % self.prevFhd, config.av.autores_rate_fhd[config.av.autores_mode_fhd[port].value], _("Configure the refresh rate of the screen."), "check_fhd")
					))
					if config.av.autores_mode_fhd[port].value == '1080p' and ('1080p' in modes or "1080p50" in modes):
						items.append((_("%sShow 1080i as 1080p") % self.prevFhd, config.av.autores_1080i_deinterlace, _("Use Deinterlacing for 1080i Videosignal?"), "check_fhd"))
					elif "1080p" not in modes and "1080p50" not in modes:
						config.av.autores_1080i_deinterlace.value = False
				if "2160p" in modes or "2160p30" in modes:
					self.getVerifyVideomode(config.av.autores_mode_uhd, config.av.autores_rate_uhd)
					items.extend((
						(pgettext(_("Video output mode for UHD"), _("%sMode for UHD (up to 2160p)") % self.prevUhd), config.av.autores_mode_uhd[port], _("This option configures the video output mode (or resolution)."), "check_uhd"),
						(_("%sRefresh rate for UHD") % self.prevUhd, config.av.autores_rate_uhd[config.av.autores_mode_uhd[port].value], _("Configure the refresh rate of the screen."), "check_uhd")
					))
				items.extend((
					(_("Show 24p up to 720p / higher than 720p as"), config.av.autores_24p, _("Show 24p up to resolution 720p or higher than 720p as a different Framerate.")),
					(_("Show 25p up to 720p / higher than 720p as"), config.av.autores_25p, _("Show 25p up to resolution 720p or higher than 720p as a different Framerate.")),
					(_("Show 30p up to 720p / higher than 720p as"), config.av.autores_30p, _("Show 30p up to resolution 720p or higher than 720p as a different Framerate."))
				))
			elif config.av.autores.value == "native":
				items.extend((
					(_("Delay time"), config.av.autores_delay, _("Set the time before checking video source for resolution information.")),
					(_("Automatic resolution label"), config.av.autores_label_timeout, _("Allows you to adjust the amount of time the resolution information display on screen."))
				))
				self.getVerifyVideomode(config.av.autores_mode_sd, config.av.autores_rate_sd)
				items.extend((
					(pgettext(_("Lowest Video output mode"), _("Lowest Mode")), config.av.autores_mode_sd[port], _("This option configures the video output mode (or resolution).")),
					(_("Refresh rate for 'Lowest Mode'"), config.av.autores_rate_sd[config.av.autores_mode_sd[port].value], _("Configure the refresh rate of the screen.")),
					(_("Show 24p up to 720p / higher than 720p as"), config.av.autores_24p, _("Show 24p up to resolution 720p or higher than 720p as a different Framerate.")),
					(_("Show 25p up to 720p / higher than 720p as"), config.av.autores_25p, _("Show 25p up to resolution 720p or higher than 720p as a different Framerate.")),
					(_("Show 30p up to 720p / higher than 720p as"), config.av.autores_30p, _("Show 30p up to resolution 720p or higher than 720p as a different Framerate.")),
					(_("Show unknown video format as"), config.av.autores_unknownres, _("Show unknown Videoresolution as next higher or as highest screen resolution."))
				))
			if config.av.autores.value != "disabled":
				items.append((_("Force progressive for streams and files"), config.av.autores_force_progressive, _("Select 'Yes' to treat interlaced streams and media files as progressive. DVB services and recordings are not affected. This helps with streams that are wrongly flagged as interlaced.")))
		# If we have modes for this port.
		if (port in config.av.videomode and config.av.autores.value == "disabled") or port == "Scart":
			# Add mode and rate selection.
			items.append((pgettext(_("Video output mode"), _("Mode")), config.av.videomode[port], _("This option configures the video output mode (or resolution).")))
			if config.av.videomode[port].value == "PC":
				items.append((_("Resolution"), config.av.videorate[config.av.videomode[port].value], _("This option configures the screen resolution in PC output mode.")))
			elif port != "Scart":
				items.append((_("Refresh rate"), config.av.videorate[config.av.videomode[port].value], _("Configure the refresh rate of the screen.")))
		mode = config.av.videomode[port].value if port in config.av.videomode else None
		# Some modes (720p, 1080i) are always wide screen. Don't let the user select something here, "auto" is not what they want.
		forceWide = avSwitch.isWidescreenMode(port, mode)
		if not forceWide:
			items.append((_("Aspect ratio"), config.av.aspect, _("Configure the aspect ratio of the screen.")))
		if forceWide or config.av.aspect.value in ("16:9", "16:10"):
			items.extend((
				(_("Display 4:3 content as"), config.av.policy_43, _("When the content has an aspect ratio of 4:3, choose whether to scale/stretch the picture.")),
				(_("Display >16:9 content as"), config.av.policy_169, _("When the content has an aspect ratio of 16:9, choose whether to scale/stretch the picture."))
			))
		elif config.av.aspect.value == "4:3":
			items.append((_("Display 16:9 content as"), config.av.policy_169, _("When the content has an aspect ratio of 16:9, choose whether to scale/stretch the picture.")))
		if port == "HDMI":
			if not eAVControl.getInstance().hasVideoAxis():
				items.append((_("Aspect switch"), config.av.aspectswitch.enabled, _("This option allows you to set offset values for different Letterbox resolutions.")))
				if config.av.aspectswitch.enabled.value:
					for aspect in range(5):
						items.append((f" -> {avSwitch.ASPECT_SWITCH_MSG[aspect]}", config.av.aspectswitch.offsets[str(aspect)]))
			items.append((_("Allow unsupported modes"), config.av.edid_override, _("This option allows you to use all HDMI Modes.")))
		if port == "Scart":
			items.append((_("Color format"), config.av.colorformat, _("Configure which color format should be used on the SCART output.")))
			if level >= 1:
				items.append((_("WSS on 4:3"), config.av.wss, _("When enabled, content with an aspect ratio of 4:3 will be stretched to fit the screen.")))
				if BoxInfo.getItem("ScartSwitch"):
					items.append((_("Auto SCART switching"), config.av.vcrswitch, _("When enabled, your receiver will detect activity on the VCR SCART input.")))
		if not isinstance(config.av.scaler_sharpness, ConfigNothing) and not isPluginInstalled("VideoEnhancement"):
			items.append((_("Scaler sharpness"), config.av.scaler_sharpness, _("This option configures the picture sharpness.")))
		Setup.createSetup(self, prependItems=items)

	def getVerifyVideomode(self, setmode, setrate):
		configPort, configMode, configRes, configPol, configRate = AutoVideoMode.getConfigVideomode(config.av.videomode, config.av.videorate)
		mode = setmode[configPort].value
		res = mode.replace("p30", "p")[:-1]
		pol = mode.replace("p30", "p")[-1:]
		rate = setrate[mode].value.replace("Hz", "")
		if int(res) > int(configRes) or (int(res) == int(configRes) and ((pol == "p" and configPol == "i") or (configMode == "2160p30" and mode == "2160p"))):
			setmode[configPort].value = configMode
		if configRate not in ("auto", "multi") and (rate in ("auto", "multi") or int(configRate) < int(rate)):
			setrate[configMode].value = configRate

	def confirm(self, confirmed):
		if not confirmed:
			if self.resetMode == 1:
				config.av.videoport.value = self.lastGood[0]
				config.av.videomode[self.lastGood[0]].value = self.lastGood[1]
				config.av.videorate[self.lastGood[1]].value = self.lastGood[2]
				config.av.autores_sd.value = self.lastGoodExtra[0]
				config.av.smart1080p.value = self.lastGoodExtra[1]
				avSwitch.setMode(*self.lastGood)
			elif self.resetMode == 2:
				for key, (port, mode, rate) in self.lastGoodAutoresModes.items():
					getattr(config.av, f"autores_mode_{key}")[port].value = mode
					getattr(config.av, f"autores_rate_{key}")[mode].value = rate
				config.av.autores_24p.value = self.lastGoodAutoresExtra[0]
				config.av.autores_1080i_deinterlace.value = self.lastGoodAutoresExtra[1]
				config.av.autores_unknownres.value = self.lastGoodAutoresUnknownres
				if self.currentMode in avSwitch.readAvailableModes():
					avSwitch.setVideoModeDirect(self.currentMode)
				else:
					avSwitch.setMode(*self.lastGood)
			self.createSetup()
		else:
			Setup.keySave(self)

	def getAutoresModes(self, port):  # Port, mode and rate for each automatic resolution class.
		result = {}
		for key in ("sd", "hd", "fhd", "uhd"):
			mode = getattr(config.av, f"autores_mode_{key}")[port].value
			result[key] = (port, mode, getattr(config.av, f"autores_rate_{key}")[mode].value)
		return result

	def grabLastGoodMode(self):
		self.resetMode = 0
		port = config.av.videoport.value
		mode = config.av.videomode[port].value
		rate = config.av.videorate[mode].value
		self.lastGood = (port, mode, rate)
		autoresSd = config.av.autores_sd.value
		smart1080p = config.av.smart1080p.value
		self.lastGoodExtra = (autoresSd, smart1080p)
		self.lastGoodAutoresModes = self.getAutoresModes(port)
		autores24p = config.av.autores_24p.value
		autores1080i = config.av.autores_1080i_deinterlace.value
		self.lastGoodAutoresExtra = (autores24p, autores1080i)
		self.lastGoodAutoresUnknownres = config.av.autores_unknownres.value
		self.lastGoodAutores = config.av.autores.value

	def saveAll(self):
		if config.av.videoport.value == "Scart":
			config.av.autores.value = "disabled"
		return Setup.saveAll(self)

	def keySave(self):
		port = config.av.videoport.value
		mode = config.av.videomode[port].value
		rate = config.av.videorate[mode].value
		autoresSd = config.av.autores_sd.value
		smart1080p = config.av.smart1080p.value
		autores24p = config.av.autores_24p.value
		autores1080i = config.av.autores_1080i_deinterlace.value
		if config.av.autores.value in ("all", "hd") and ((port, mode, rate) != self.lastGood or (autoresSd, smart1080p) != self.lastGoodExtra):
			self.resetMode = 1
			# The "true" value is for compatibility with old ConfigEnableDisable.
			smartMode = "1080p" if "1080" in autoresSd else {"1080p50": "1080p", "true": "1080p", "2160p50": "2160p", "1080i50": "1080i", "720p50": "720p"}.get(smart1080p)
			if smartMode:
				avSwitch.setMode(port, smartMode, "50Hz")
			else:
				avSwitch.setMode(port, mode, rate)
		elif (port, mode, rate) != self.lastGood or (config.av.autores.value == "disabled" and self.lastGoodAutores != "disabled"):
			self.resetMode = 1
			avSwitch.setMode(port, mode, rate)
		elif config.av.autores.value in ("native", "simple") and (self.getAutoresModes(port) != self.lastGoodAutoresModes or (autores24p, autores1080i) != self.lastGoodAutoresExtra
			or self.lastGoodAutores != config.av.autores.value or self.resetMode == 1 or (self.lastGoodAutoresUnknownres != config.av.autores_unknownres.value and config.av.autores.value == "native")):
			self.resetMode = 2
			if self.currentMode is None:
				self.currentMode = self.getCurrentMode()
			AutoVideoMode(None).VideoChangeDetect()
		else:
			self.resetMode = 0
			Setup.keySave(self)
			return
		if BoxInfo.getItem("machinebuild") == "gbquad4kpro" and mode.startswith("2160p"):  # Hack for GB QUAD 4K Pro!
			config.av.hdmicolordepth.value = "10bit"
			config.av.hdmicolordepth.save()
		self.session.openWithCallback(self.confirm, MessageBox, _("Is this video mode ok?"), MessageBox.TYPE_YESNO, timeout=20, default=False)

	def getCurrentMode(self):
		return eAVControl.getInstance().getVideoMode("") or None

	def changedEntry(self):
		if config.av.autores_preview.value:
			ConfigListScreen.changedEntry(self)
			cur = self["config"].getCurrent()
			cur = cur and len(cur) > 3 and cur[3]
			if cur and cur.startswith("check"):
				if self.currentMode is None:
					self.currentMode = self.getCurrentMode()
				key = cur[6:]  # Empty for the preview switch itself, which checks all classes.
				for x in ("sd", "hd", "fhd", "uhd"):
					if key in ("", x):
						self.getVerifyVideomode(getattr(config.av, f"autores_mode_{x}"), getattr(config.av, f"autores_rate_{x}"))
				if not key or getattr(self, f"prev{key.title()}"):
					AutoVideoMode(None).VideoChangeDetect()
		else:
			Setup.changedEntry(self)


VideoSetup = VideoSettings  # Fallback for code that still uses the old class name.


class AutoVideoModeLabel(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self["content"] = Label()
		self["restxt"] = Label()
		self.hideTimer = eTimer()
		self.hideTimer.callback.append(self.hide)
		self.onShow.append(self.hideMe)

	def hideMe(self):
		value = config.av.autores_label_timeout.value
		if value:
			self.hideTimer.start(value * 1000, True)


previous = None
isDedicated3D = False


def applySettings(mode=config.osd.threeDmode.value, znorm=int(config.osd.threeDznorm.value)):
	global previous, isDedicated3D
	mode = isDedicated3D and mode == "auto" and "sidebyside" or mode
	if not BoxInfo.getItem("3DMode"):
		return
	if previous != (mode, znorm):
		try:
			previous = (mode, znorm)
			if BoxInfo.getItem("CanUse3DModeChoices"):
				f = open("/proc/stb/fb/3dmode_choices")
				choices = f.readlines()[0].split()
				f.close()
				if mode not in choices:
					if mode == "sidebyside":
						mode = "sbs"
					elif mode == "topandbottom":
						mode = "tab"
					elif mode == "auto":
						mode = "off"
			open(BoxInfo.getItem("3DMode"), "w").write(mode)
			open(BoxInfo.getItem("3DZNorm"), "w").write(f"{znorm}")
		except Exception:
			return


class AutoVideoMode(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		if session is not None:
			self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
				iPlayableService.evStart: self.__evStart,
				iPlayableService.evVideoSizeChanged: self.VideoChanged,
				iPlayableService.evVideoProgressiveChanged: self.VideoChanged,
				iPlayableService.evVideoFramerateChanged: self.VideoChanged,
				iPlayableService.evVideoGammaChanged: self.gammaChanged,
				# iPlayableService.evBuffering: self.BufferInfo,  # Currently disabled, is this really needed? - With some streams will this permanently called? (e.g. #SERVICE 4097:0:1:0:0:0:0:0:0:0:rtmp%3a//62.113.210.250/medienasa-live playpath=ok-wernigerode_high swfUrl=http%3a//www.blitzvideoserver06.de/blitzvideoplayer6.swf live=1 pageUrl=http%3a//iphonetv.in/#stream-id=45:Offener Kanal Wernigerode rtmp).
				# iPlayableService.evStopped: self.BufferInfoStop,  # Sometimes not called or called before evBuffering -> if bufferfull = False (when evBuffering permanently called and buffer < 98%) will auto resolution not longer working.
				# iPlayableService.evEnd: self.BufferInfoStop  # Alternative for 'evStopped'.
			})
		self.firstrun = True
		self.delay = False
		self.bufferfull = True
		self.detecttimer = eTimer()
		self.detecttimer.callback.append(self.VideoChangeDetect)

	def checkIfDedicated3D(self):
		service = self.session.nav.getCurrentlyPlayingServiceReference()
		servicepath = service and service.getPath()
		if servicepath and servicepath.startswith("/"):
				if service.toString().startswith("1:"):
					info = eServiceCenter.getInstance().info(service)
					service = info and info.getInfoString(service, iServiceInformation.sServiceref)
					return service and eDVBDB.getInstance().getFlag(eServiceReference(service)) & FLAG_IS_DEDICATED_3D == FLAG_IS_DEDICATED_3D and "sidebyside"
				else:
					return ".3d." in servicepath.lower() and "sidebyside" or ".tab." in servicepath.lower() and "topandbottom"
		service = self.session.nav.getCurrentService()
		info = service and service.info()
		return info and info.getInfo(iServiceInformation.sIsDedicated3D) == 1 and "sidebyside"

	def __evStart(self):
		self.gammaChanged(reset=True)  # Not every service sends a gamma event, so don't keep the HDR type of the previous one.
		if config.osd.threeDmode.value == "auto":
			global isDedicated3D
			isDedicated3D = self.checkIfDedicated3D()
			if isDedicated3D:
				applySettings(isDedicated3D)
			else:
				applySettings()

	def gammaChanged(self, reset=False):  # Switch the HDMI HDR type to match the content when the HDR type is set to "auto".
		if config.av.hdmihdrtype_switch.value and config.av.hdmihdrtype.value == "auto":
			gamma = -1
			if not reset:
				service = self.session.nav.getCurrentService()
				info = service and service.info()
				if info:
					gamma = info.getInfo(iServiceInformation.sGamma)
			# Gamma values: 0 = SDR, 1 = traditional gamma with HDR luminance range, 2 = SMPTE ST2084 (HDR10), 3 = Hybrid Log-Gamma.
			hdrType = {2: "hdr10", 3: "hlg"}.get(gamma, "auto")
			if hdrType in config.av.hdmihdrtype.choices:
				self.writeVideoSetting("/proc/stb/video/hdmi_hdrtype", hdrType)
				if config.av.hdmicolorimetry.value == "auto":
					self.writeVideoSetting("/proc/stb/video/hdmi_colorimetry", "auto" if hdrType == "auto" else config.av.hdmicolorimetry_hdr.value)

	def writeVideoSetting(self, path, value):  # Only write if the value has changed.
		if fileReadLine(path, default="", source=MODULE_NAME) != value:
			fileWriteLine(path, value, source=MODULE_NAME)
			print(f"[VideoMode] Set '{path}' to '{value}'.")

	def BufferInfo(self):
		bufferInfo = self.session.nav.getCurrentService().streamed().getBufferCharge()
		if bufferInfo[0] > 98:
			self.bufferfull = True
			self.VideoChanged()
		else:
			self.bufferfull = False
		# print(f"[VideoMode] {"+" * 30} BufferInfo {bufferInfo[0]} {self.bufferfull}.")

	def BufferInfoStop(self):
		self.bufferfull = True
		# print(f"[VideoMode] {"-" * 30} BufferInfoStop.")

	def VideoChanged(self):
		if config.av.autores.value == "disabled" or getAutoresPluginEnabled():
			# print("[VideoMode] Auto resolution is disabled - resolution not changed.")
			return
		if self.session.nav.getCurrentlyPlayingServiceReference() and not self.session.nav.getCurrentlyPlayingServiceReference().toString().startswith("4097:"):
			delay = config.av.autores_delay.value
		else:
			delay = config.av.autores_delay.value * 2
		if not self.detecttimer.isActive() and not self.delay:
			self.delay = True
			self.detecttimer.start(delay)
		else:
			self.delay = True
			self.detecttimer.stop()
			self.detecttimer.start(delay)

	@staticmethod
	def getConfigVideomode(getmode, getrate):
		port = config.av.videoport.value
		mode = getmode[port].value
		res = mode.replace("p30", "p")[:-1]
		pol = mode.replace("p30", "p")[-1:]
		rate = getrate[mode].value.replace("Hz", "")
		return port, mode, res, pol, rate

	def setProgressiveRate(self, vidRate, newRate, newRes, configRes, configRate):
		if vidRate == 24:
			if int(newRes) <= 720:
				newRate = config.av.autores_24p.value.split(",")[0]
			else:
				newRate = config.av.autores_24p.value.split(",")[1]
		elif vidRate == 25:
			if int(newRes) <= 720:
				newRate = config.av.autores_25p.value.split(",")[0]
			else:
				newRate = config.av.autores_25p.value.split(",")[1]
		elif vidRate == 30:
			if int(newRes) <= 720:
				newRate = config.av.autores_30p.value.split(",")[0]
			else:
				newRate = config.av.autores_30p.value.split(",")[1]
		if int(newRes) >= int(configRes) and configRate not in ("auto", "multi") and int(configRate) < int(newRate):
			newRate = configRate
		return newRate

	def mapAutoresMode(self, mode):  # Replace a mode by the selected output mode. The order matters because a replaced mode can be replaced again.
		for modes, setting in (
			(("480p24", "576p24"), config.av.autores_480p24),
			(("720p24",), config.av.autores_720p24),
			(("1080p24",), config.av.autores_1080p24),
			(("1080p25",), config.av.autores_1080p25),
			(("1080p30",), config.av.autores_1080p30),
			(("2160p24",), config.av.autores_2160p24),
			(("2160p25", "2160p50"), config.av.autores_2160p25),
			(("2160p30", "2160p60", "2160p"), config.av.autores_2160p30)
		):
			if mode in modes:
				mode = setting.value
		return mode

	def VideoChangeDetect(self):
		# Info: Auto resolution preview or save settings call this function with session = None / ~338, ~374.
		global resolutionlabel
		avControl = eAVControl.getInstance()
		configPort, configMode, configRes, configPol, configRate = self.getConfigVideomode(config.av.videomode, config.av.videorate)
		configMode = configMode.replace("p30", "p")
		currentMode = avControl.getVideoMode("")
		if currentMode.upper() in ("PAL", "NTSC"):
			currentMode = currentMode.upper()
		currentPol = ""
		if "i" in currentMode:
			currentPol = "i"
		elif "p" in currentMode:
			currentPol = "p"
		currentRes = currentPol and currentMode.split(currentPol)[0].replace("\n", "") or ""  # noqa F841
		currentRate = currentPol and currentMode.split(currentPol)[0].replace("\n", "") and currentMode.split(currentPol)[1].replace("\n", "") or ""  # noqa F841
		writeMode = None
		newMode = None
		videoRate = avControl.getFrameRate(0)
		videoPol = "p" if avControl.getProgressive() else "i"
		videoWidth = avControl.getResolutionX(0)
		videoHeight = avControl.getResolutionY(0)
		if not videoHeight or not videoWidth or not videoPol or not videoRate:
			service = self.session and self.session.nav.getCurrentService()
			if service is not None:
				info = service.info()
			else:
				info = None
			if info:
				videoHeight = int(info.getInfo(iServiceInformation.sVideoHeight))
				videoWidth = int(info.getInfo(iServiceInformation.sVideoWidth))
				videoPol = ("i", "p")[info.getInfo(iServiceInformation.sProgressive)]
				videoRate = int(info.getInfo(iServiceInformation.sFrameRate))
		contentPol = videoPol
		if videoPol == "i" and config.av.autores_force_progressive.value:
			service = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
			if service and service.type != eServiceReference.idDVB:  # Not for DVB services and recordings, they are really interlaced.
				videoPol = "p"
		print(f"[VideoMode] detect video height: {videoHeight}, width: {videoWidth}, pol: {videoPol}, rate: {videoRate} (current video mode: {currentMode})")
		if videoHeight and videoWidth and videoPol and videoRate:
			labelRate = (videoRate + 500) // 1000
			if contentPol == "i":
				labelRate *= 2
			content = _("Video content: %ix%i%s %iHz") % (videoWidth, videoHeight, contentPol, labelRate)
			service = NavigationInstance.instance.getCurrentService()
			info = service and service.info()
			if info:
				codec = CODEC_NAMES.get(info.getInfo(iServiceInformation.sVideoType), "")
				gamma = {1: "HDR", 2: "HDR10", 3: "HLG"}.get(info.getInfo(iServiceInformation.sGamma), "")
				content = " ".join(x for x in (content, codec, gamma) if x and x != "N/A")
			resolutionlabel["content"].setText(content)
			if videoHeight != -1:
				if videoHeight > 720 or videoWidth > 1280:
					newRes = "1080"
				elif (576 < videoHeight <= 720) or videoWidth > 1024:
					newRes = "720"
				elif (480 < videoHeight <= 576) or videoWidth > 720 or videoRate in (25000, 23976, 24000):
					newRes = "576"
				else:
					newRes = "480"
			else:
				newRes = configRes
			if videoRate != -1:
				if videoRate == 25000 and videoPol == "i":
					newRate = 50000
				elif videoRate == 59940 or (videoRate == 29970 and videoPol == "i"):
					newRate = 60000
				elif videoRate == 23976:
					newRate = 24000
				elif videoRate == 29970:
					newRate = 30000
				else:
					newRate = videoRate
				newRate = str((newRate + 500) // 1000)
			else:
				newRate = configRate
			newPol = str(videoPol) if videoPol != -1 else configPol
			autorestyp = ""
			if configMode in ("PAL", "NTSC"):
				autorestyp = "PAL or NTSC"
				writeMode = configMode
			elif config.av.autores.value == "simple":
				autorestyp = "simple"
				newRate = (videoRate + 500) // 1000
				if videoHeight <= 576 and int(configRes) >= 576:  # SD.
					if config.av.autores_rate_sd[config.av.autores_mode_sd[config.av.videoport.value].value].value in ("auto", "multi"):
						if videoPol == "i":
							newRate *= 2
					else:
						newRate = config.av.autores_rate_sd[config.av.autores_mode_sd[config.av.videoport.value].value].value.replace("Hz", "")
					newMode = config.av.autores_mode_sd[configPort].value.replace("p30", "p")
				elif videoHeight <= 720 and int(configRes) >= 720:  # HD.
					if config.av.autores_rate_hd[config.av.autores_mode_hd[config.av.videoport.value].value].value in ("auto", "multi"):
						if videoPol == "i":
							newRate *= 2
					else:
						newRate = config.av.autores_rate_hd[config.av.autores_mode_hd[config.av.videoport.value].value].value.replace("Hz", "")
					newMode = config.av.autores_mode_hd[configPort].value.replace("p30", "p")
				elif videoHeight <= 1080 and int(configRes) >= 1080:  # FHD.
					if config.av.autores_rate_fhd[config.av.autores_mode_fhd[config.av.videoport.value].value].value in ("auto", "multi"):
						if videoPol == "i":
							newRate *= 2
					else:
						newRate = config.av.autores_rate_fhd[config.av.autores_mode_fhd[config.av.videoport.value].value].value.replace("Hz", "")
					newMode = config.av.autores_mode_fhd[configPort].value.replace("p30", "p")
					if newMode == "1080p" and not config.av.autores_1080i_deinterlace.value and videoHeight == 1080 and videoPol == "i":
						newMode = "1080i"
				elif videoHeight <= 2160 and int(configRes) >= 2160:  # UHD.
					if config.av.autores_rate_uhd[config.av.autores_mode_uhd[config.av.videoport.value].value].value in ("auto", "multi"):
						if videoPol == "i":
							newRate *= 2
					else:
						newRate = config.av.autores_rate_uhd[config.av.autores_mode_uhd[config.av.videoport.value].value].value.replace("Hz", "")
					newMode = config.av.autores_mode_uhd[configPort].value.replace("p30", "p")
				else:
					if configRate not in ("auto", "multi"):
						newRate = configRate
					newMode = configMode
				newRate = str(int(newRate))
				if newMode.endswith("p"):
					newRate = self.setProgressiveRate((videoRate + 500) // 1000 * (int(videoPol == "i") + 1), newRate, newMode[:-1], configRes, configRate)
				if newMode + newRate in avSwitch.readAvailableModes():
					writeMode = newMode + newRate
				elif newMode in avSwitch.readAvailableModes():
					writeMode = newMode
				else:
					if configRate not in ("auto", "multi") and int(newRate) > int(configRate):
						newRate = configRate
					if configMode + newRate in avSwitch.readAvailableModes():
						writeMode = configMode + newRate
					else:
						writeMode = configMode
			elif config.av.autores.value == "native":
				autorestyp = "native"
				newRate = (videoRate + 500) // 1000
				newPol = videoPol
				newRes = str(videoHeight)
				if videoPol == "i":
					newRate *= 2
				minPort, minMode, minRes, minPol, minRate = self.getConfigVideomode(config.av.autores_mode_sd, config.av.autores_rate_sd)
				if videoHeight <= int(minRes):
					if newPol == "i" and minPol == "p":
						newPol = minPol
					if minRate not in ("auto", "multi") and newRate < int(minRate):
						newRate = int(minRate)
					newRes = minRes
				if videoHeight >= int(configRes) or int(newRes) >= int(configRes):
					newRes = configRes
					if videoPol == "p" and configPol == "i":
						newPol = configPol
					if configRate not in ("auto", "multi") and int(configRate) < int(newRate):
						newRate = int(configRate)
				newRate = str(int(newRate))
				if newPol == "p":
					newRate = self.setProgressiveRate((videoRate + 500) // 1000 * (int(videoPol == "i") + 1), newRate, newRes, configRes, configRate)
				if newRes + newPol + newRate in avSwitch.readAvailableModes():
					writeMode = newRes + newPol + newRate
				elif newRes + newPol in avSwitch.readAvailableModes():
					writeMode = newRes + newPol
				elif newRes + minPol + newRate in avSwitch.readAvailableModes():
					writeMode = newRes + minPol + newRate
				elif newRes + minPol in avSwitch.readAvailableModes():
					writeMode = newRes + minPol
				else:
					if config.av.autores_unknownres.value == "next":
						if videoHeight <= 576 and int(configRes) >= 576:
							newRes = "576"
						elif videoHeight <= 720 and int(configRes) >= 720:
							newRes = "720"
						elif videoHeight <= 1080 and int(configRes) >= 1080:
							newRes = "1080"
						elif videoHeight <= 2160 and int(configRes) >= 2160:
							newRes = "2160"
					elif config.av.autores_unknownres.value == "highest":
						newRes = configRes
					if newPol == "p":
						newRate = self.setProgressiveRate((videoRate + 500) // 1000 * (int(videoPol == "i") + 1), newRate, newRes, configRes, configRate)
					if newRes + newPol + newRate in avSwitch.readAvailableModes():
						writeMode = newRes + newPol + newRate
					elif newRes + newPol in avSwitch.readAvailableModes():
						writeMode = newRes + newPol
					elif newRes + minPol + newRate in avSwitch.readAvailableModes():
						writeMode = newRes + minPol + newRate
					elif newRes + minPol in avSwitch.readAvailableModes():
						writeMode = newRes + minPol
					else:
						if configRate not in ("auto", "multi") and int(newRate) > int(configRate):
							newRate = configRate
						if configMode + newRate in avSwitch.readAvailableModes():
							writeMode = configMode + newRate
						else:
							writeMode = configMode
			elif config.av.autores.value == "all" or (config.av.autores.value == "hd" and int(newRes) >= 720):
				autorestyp = "all or hd"
				if config.av.autores_deinterlace.value:
					newPol = newPol.replace("i", "p")
				if newRes + newPol + newRate in avSwitch.readAvailableModes():
					newMode = newRes + newPol + newRate
					newMode = self.mapAutoresMode(newMode)
				elif newRes + newPol in avSwitch.readAvailableModes():
					newMode = self.mapAutoresMode(newRes + newPol)
				else:
					newMode = configMode + newRate
				writeMode = newMode
			elif config.av.autores.value == "hd" and int(newRes) <= 576:
				autorestyp = "hd"
				if newPol == "p":
					newMode = config.av.autores_sd.value.replace("i", "p") + newRate
				else:
					newMode = config.av.autores_sd.value + newRate
					if config.av.autores_deinterlace.value:
						testNewMode = config.av.autores_sd.value.replace("i", "p") + newRate
						if testNewMode in avSwitch.readAvailableModes():
							newMode = testNewMode
				writeMode = self.mapAutoresMode(newMode)
			else:
				autorestyp = "no match"
				multiVideomode = ""
				f = None
				if configRate in ("auto", "multi"):
					if eAVControl.getInstance().hasVideoAxis():
						multiVideomode = avControl.getVideoMode("")
					elif exists(f"/proc/stb/video/videomode_{newRate}hz"):
						f = open(f"/proc/stb/video/videomode_{newRate}hz")
				if f:
					multiVideomode = f.read().replace("\n", "")
					f.close()
				if multiVideomode and (currentMode != multiVideomode):
					writeMode = multiVideomode
				else:
					writeMode = configMode + newRate
			# Workaround for bug, see https://www.opena.tv/forum/showthread.php?1642-Autoresolution-Plugin&p=38836&viewfull=1#post38836
			# Always use a fixed resolution and frame rate.   (e.g. 1080p50 if supported) for TV or .ts files.
			# Always use a fixed resolution and correct rate. (e.g. 1080p24/p50/p60) for all other videos.
			if config.av.smart1080p.value != "false" and config.av.autores.value in ("all", "hd"):
				autorestyp = "smart1080p mode"
				ref = self.session and self.session.nav.getCurrentlyPlayingServiceReference()
				if ref is not None:
					try:
						mypath = ref.getPath()
					except Exception:
						mypath = ""
				else:
					mypath = ""
				# No frame rate information available, check if filename (or directory name) contains a hint.
				# (Allow user to force a frame rate this way).
				if (mypath.find("p24.") >= 0) or (mypath.find("24p.") >= 0):
					newRate = "24"
				elif (mypath.find("p25.") >= 0) or (mypath.find("25p.") >= 0):
					newRate = "25"
				elif (mypath.find("p30.") >= 0) or (mypath.find("30p.") >= 0):
					newRate = "30"
				elif (mypath.find("p50.") >= 0) or (mypath.find("50p.") >= 0):
					newRate = "50"
				elif (mypath.find("p60.") >= 0) or (mypath.find("60p.") >= 0):
					newRate = "60"
				elif newRate in ("auto", "multi"):
					newRate = ""  # Omit frame rate specifier, e.g. "1080p" instead of "1080p50" if there is no clue.
				if mypath != "":
					if mypath.endswith(".ts"):
						print("[VIDEOMODE] playing .ts file")
						newRate = "50"  # For .ts files.
					else:
						print("[VIDEOMODE] playing other (non .ts) file")
						# Use 'newRate', from above, for all other videos.
				else:
					print("[VIDEOMODE] no path or no service reference, presumably live TV")
					newRate = "50"  # For TV / or no service reference, then stay at 1080p50.
				newRate = newRate.replace("25", "50").replace("30", "60")
				if (config.av.smart1080p.value == "1080p50") or (config.av.smart1080p.value == "true"):  # For compatibility with old ConfigEnableDisable.
					writeMode = "1080p" + newRate
				elif config.av.smart1080p.value == "2160p50":
					writeMode = "2160p" + newRate
				elif config.av.smart1080p.value == "1080i50":
					if newRate == "24":
						writeMode = "1080p24"  # Instead of 1080i24.
					else:
						writeMode = "1080i" + newRate
				elif config.av.smart1080p.value == "720p50":
					writeMode = "720p" + newRate
				# print(f"[VideoMode] smart1080p mode, selecting {writeMode}.")
			if writeMode and currentMode != writeMode and self.bufferfull or self.firstrun:
				values = avSwitch.readAvailableModes()
				if writeMode not in values:
					if writeMode in ("1080p24", "1080p30", "1080p60"):
						writeMode = "1080p"
					elif writeMode in ("2160p24", "2160p30", "2160p60"):
						writeMode = "2160p"
				if writeMode in values:
					avSwitch.setVideoModeDirect(writeMode)
					print(f"[VideoMode] setMode - port: {configPort}, mode: {writeMode} (autoresTyp: '{autorestyp}')")
					resolutionlabel["restxt"].setText(_("Video mode: %s") % writeMode)
				else:
					print(f"[VideoMode] setMode - port: {configPort}, mode: {writeMode} is not available")
					resolutionlabel["restxt"].setText(_("Video mode: %s not available") % writeMode)
				if config.av.autores_label_timeout.value:
					resolutionlabel.show()
			elif writeMode and currentMode != writeMode:
				# The resolution remained stuck at a wrong setting after streaming when self.bufferfull was False (should be fixed now after adding BufferInfoStop).
				print(f"[VideoMode] not changing from {currentMode} to {writeMode} as self.bufferfull is {self.bufferfull}")
		if writeMode and writeMode != currentMode or self.firstrun:
			avControl.setAspect(config.av.aspect.value, 1)
			avControl.setWSS(config.av.wss.value, 1)
			avControl.setPolicy43(config.av.policy_43.value, 1)
			avControl.setPolicy169(config.av.policy_169.value, 1)
		self.firstrun = False
		self.delay = False
		self.detecttimer.stop()


def manualResolution(session):  # Ad hoc video mode selection from the extensions menu.
	def manualResolutionCallback(choice):
		if choice and choice[1] != oldMode:
			avSwitch.setVideoModeDirect(choice[1])
			session.openWithCallback(confirmCallback, MessageBox, _("Is this video mode ok?"), MessageBox.TYPE_YESNO, timeout=10, default=False)

	def confirmCallback(answer):
		if not answer:
			avSwitch.setVideoModeDirect(oldMode)

	avControl = eAVControl.getInstance()
	oldMode = avControl.getVideoMode("")
	modes = [(x, x) for x in avSwitch.readAvailableModes() if x not in ("auto", "pal", "ntsc") and not x.startswith("3d")]
	if modes:
		pol = "p" if avControl.getProgressive() else "i"
		rate = (avControl.getFrameRate(0) + 500) // 1000 * (2 if pol == "i" else 1)
		text = _("Video content: %ix%i%s %iHz") % (avControl.getResolutionX(0), avControl.getResolutionY(0), pol, rate)
		selection = next((index for index, x in enumerate(modes) if x[1] == oldMode), 0)
		session.openWithCallback(manualResolutionCallback, ChoiceBox, text=text, choiceList=modes, selection=selection, windowTitle=_("Manual resolution"))


def autostart(session):
	global resolutionlabel
	if getAutoresPluginEnabled():
		config.av.autores.value = False
		config.av.autores.save()
		configfile.save()
	else:
		if resolutionlabel is None:
			resolutionlabel = session.instantiateDialog(AutoVideoModeLabel)
		AutoVideoMode(session)

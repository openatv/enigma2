from os.path import exists

from enigma import eAVControl, eDVBDB, eServiceCenter, eServiceReference, eTimer, iPlayableService, iServiceInformation

from Components.AVSwitch import avSwitch
from Components.config import ConfigNothing, config, configfile
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.ServiceEventTracker import ServiceEventTracker
from Components.SystemInfo import BoxInfo
from Screens.ChannelSelection import FLAG_IS_DEDICATED_3D
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Setup import Setup
from Tools.Directories import isPluginInstalled

resolutionlabel = None


def getAutoresPlugin_enabled():
	try:
		return config.plugins.autoresolution.enable.value
	except Exception:
		return False


def getConfig_videomode(getmode, getrate):
	port = config.av.videoport.value
	mode = getmode[port].value
	res = mode.replace("p30", "p")[:-1]
	pol = mode.replace("p30", "p")[-1:]
	rate = getrate[mode].value.replace("Hz", "")
	return port, mode, res, pol, rate


def setProgressiveRate(vid_rate, new_rate, new_res, config_res, config_rate):
	if vid_rate == 24:
		if int(new_res) <= 720:
			new_rate = config.av.autores_24p.value.split(",")[0]
		else:
			new_rate = config.av.autores_24p.value.split(",")[1]
	elif vid_rate == 25:
		if int(new_res) <= 720:
			new_rate = config.av.autores_25p.value.split(",")[0]
		else:
			new_rate = config.av.autores_25p.value.split(",")[1]
	elif vid_rate == 30:
		if int(new_res) <= 720:
			new_rate = config.av.autores_30p.value.split(",")[0]
		else:
			new_rate = config.av.autores_30p.value.split(",")[1]
	if int(new_res) >= int(config_res) and config_rate not in ("auto", "multi") and int(config_rate) < int(new_rate):
		new_rate = config_rate
	return new_rate


class VideoSetup(Setup):
	def __init__(self, session):
		config.av.autores_preview.value = False
		self.current_mode = None
		Setup.__init__(self, session, "video_setup")
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
		if port in ("HDMI", "YPbPr", "Scart-YPbPr") and not getAutoresPlugin_enabled():
			modes = avSwitch.readAvailableModes()
			items.append((_("Automatic resolution"), config.av.autores, _("If enabled the output resolution of the receiver will try to match the resolution of the video contents resolution.")))
			if config.av.autores.value in ("all", "hd"):
				items.append((_("Delay time"), config.av.autores_delay, _("Set the time before checking video source for resolution information.")))
				items.append((_("Automatic resolution label"), config.av.autores_label_timeout, _("Allows you to adjust the amount of time the resolution information display on screen.")))
				items.append((_("Force de-interlace"), config.av.autores_deinterlace, _("If enabled the video will always be de-interlaced.")))
				items.append((_("Always use smart1080p mode"), config.av.smart1080p, _("This option allows you to always use e.g. 1080p50 for TV/.ts, and 1080p24/p50/p60 for videos")))
				if config.av.autores.value == "hd":
					items.append((_("Show SD as"), config.av.autores_sd, _("This option allows you to choose how to display standard definition video on your TV.")))
				items.append((_("Show 480/576p 24fps as"), config.av.autores_480p24, _("This option allows you to choose how to display SD progressive 24Hz on your TV. (as not all TV's support these resolutions)")))
				items.append((_("Show 720p 24fps as"), config.av.autores_720p24, _("This option allows you to choose how to display 720p 24Hz on your TV. (as not all TV's support these resolutions)")))
				items.append((_("Show 1080p 24fps as"), config.av.autores_1080p24, _("This option allows you to choose how to display 1080p 24Hz on your TV. (as not all TV's support these resolutions)")))
				items.append((_("Show 1080p 25fps as"), config.av.autores_1080p25, _("This option allows you to choose how to display 1080p 25Hz on your TV. (as not all TV's support these resolutions)")))
				items.append((_("Show 1080p 30fps as"), config.av.autores_1080p30, _("This option allows you to choose how to display 1080p 30Hz on your TV. (as not all TV's support these resolutions)")))
				if "2160p24" in modes:
					items.append((_("Show 2160p 24fps as"), config.av.autores_2160p24, _("This option allows you to choose how to display 2160p 24Hz on your TV. (as not all TV's support these resolutions)")))
					items.append((_("Show 2160p 25fps as"), config.av.autores_2160p25, _("This option allows you to choose how to display 2160p 25Hz on your TV. (as not all TV's support these resolutions)")))
					items.append((_("Show 2160p 30fps as"), config.av.autores_2160p30, _("This option allows you to choose how to display 2160p 30Hz on your TV. (as not all TV's support these resolutions)")))
			elif config.av.autores.value == "simple":
				items.append((_("Delay time"), config.av.autores_delay, _("Set the time before checking video source for resolution information.")))
				items.append((_("Automatic resolution label"), config.av.autores_label_timeout, _("Allows you to adjust the amount of time the resolution information display on screen.")))
				self.prev_sd = self.prev_hd = self.prev_fhd = self.prev_uhd = ""
				service = self.session.nav.getCurrentService()
				info = service and service.info()
				if info:
					video_height = int(info.getInfo(iServiceInformation.sVideoHeight))
					if video_height <= 576:
						self.prev_sd = "* "
					elif video_height <= 720:
						self.prev_hd = "* "
					elif video_height <= 1080:
						self.prev_fhd = "* "
					elif video_height <= 2160:
						self.prev_uhd = "* "
					else:
						config.av.autores_preview.value = False
					items.append((_("Enable preview"), config.av.autores_preview, _("Show preview of current mode (*)."), "check"))
				else:
					config.av.autores_preview.value = False
				self.getVerify_videomode(config.av.autores_mode_sd, config.av.autores_rate_sd)
				items.append((pgettext(_("Video output mode for SD"), _("%sMode for SD (up to 576p)") % self.prev_sd), config.av.autores_mode_sd[port], _("This option configures the video output mode (or resolution)."), "check_sd"))
				items.append((_("%sRefresh rate for SD") % self.prev_sd, config.av.autores_rate_sd[config.av.autores_mode_sd[port].value], _("Configure the refresh rate of the screen."), "check_sd"))
				if "720p" in modes:
					self.getVerify_videomode(config.av.autores_mode_hd, config.av.autores_rate_hd)
					items.append((pgettext(_("Video output mode for HD"), _("%sMode for HD (up to 720p)") % self.prev_hd), config.av.autores_mode_hd[port], _("This option configures the video output mode (or resolution)."), "check_hd"))
					items.append((_("%sRefresh rate for HD") % self.prev_hd, config.av.autores_rate_hd[config.av.autores_mode_hd[port].value], _("Configure the refresh rate of the screen."), "check_hd"))
				if "1080i" in modes or "1080p" in modes:
					self.getVerify_videomode(config.av.autores_mode_fhd, config.av.autores_rate_fhd)
					items.append((pgettext(_("Video output mode for FHD"), _("%sMode for FHD (up to 1080p)") % self.prev_fhd), config.av.autores_mode_fhd[port], _("This option configures the video output mode (or resolution)."), "check_fhd"))
					items.append((_("%sRefresh rate for FHD") % self.prev_fhd, config.av.autores_rate_fhd[config.av.autores_mode_fhd[port].value], _("Configure the refresh rate of the screen."), "check_fhd"))
					if config.av.autores_mode_fhd[port].value == '1080p' and ('1080p' in modes or "1080p50" in modes):
						items.append((_("%sShow 1080i as 1080p") % self.prev_fhd, config.av.autores_1080i_deinterlace, _("Use Deinterlacing for 1080i Videosignal?"), "check_fhd"))
					elif "1080p" not in modes and "1080p50" not in modes:
						config.av.autores_1080i_deinterlace.value = False
				if "2160p" in modes or "2160p30" in modes:
					self.getVerify_videomode(config.av.autores_mode_uhd, config.av.autores_rate_uhd)
					items.append((pgettext(_("Video output mode for UHD"), _("%sMode for UHD (up to 2160p)") % self.prev_uhd), config.av.autores_mode_uhd[port], _("This option configures the video output mode (or resolution)."), "check_uhd"))
					items.append((_("%sRefresh rate for UHD") % self.prev_uhd, config.av.autores_rate_uhd[config.av.autores_mode_uhd[port].value], _("Configure the refresh rate of the screen."), "check_uhd"))
				items.append((_("Show 24p up to 720p / higher than 720p as"), config.av.autores_24p, _("Show 24p up to resolution 720p or higher than 720p as a different Framerate.")))
				items.append((_("Show 25p up to 720p / higher than 720p as"), config.av.autores_25p, _("Show 25p up to resolution 720p or higher than 720p as a different Framerate.")))
				items.append((_("Show 30p up to 720p / higher than 720p as"), config.av.autores_30p, _("Show 30p up to resolution 720p or higher than 720p as a different Framerate.")))
			elif config.av.autores.value == "native":
				items.append((_("Delay time"), config.av.autores_delay, _("Set the time before checking video source for resolution information.")))
				items.append((_("Automatic resolution label"), config.av.autores_label_timeout, _("Allows you to adjust the amount of time the resolution information display on screen.")))
				self.getVerify_videomode(config.av.autores_mode_sd, config.av.autores_rate_sd)
				items.append((pgettext(_("Lowest Video output mode"), _("Lowest Mode")), config.av.autores_mode_sd[port], _("This option configures the video output mode (or resolution).")))
				items.append((_("Refresh rate for 'Lowest Mode'"), config.av.autores_rate_sd[config.av.autores_mode_sd[port].value], _("Configure the refresh rate of the screen.")))
				items.append((_("Show 24p up to 720p / higher than 720p as"), config.av.autores_24p, _("Show 24p up to resolution 720p or higher than 720p as a different Framerate.")))
				items.append((_("Show 25p up to 720p / higher than 720p as"), config.av.autores_25p, _("Show 25p up to resolution 720p or higher than 720p as a different Framerate.")))
				items.append((_("Show 30p up to 720p / higher than 720p as"), config.av.autores_30p, _("Show 30p up to resolution 720p or higher than 720p as a different Framerate.")))
				items.append((_("Show unknown video format as"), config.av.autores_unknownres, _("Show unknown Videoresolution as next higher or as highest screen resolution.")))
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
		force_wide = avSwitch.isWidescreenMode(port, mode)
		if not force_wide:
			items.append((_("Aspect ratio"), config.av.aspect, _("Configure the aspect ratio of the screen.")))
		if force_wide or config.av.aspect.value in ("16:9", "16:10"):
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

	def getVerify_videomode(self, setmode, setrate):
		config_port, config_mode, config_res, config_pol, config_rate = getConfig_videomode(config.av.videomode, config.av.videorate)
		mode = setmode[config_port].value
		res = mode.replace("p30", "p")[:-1]
		pol = mode.replace("p30", "p")[-1:]
		rate = setrate[mode].value.replace("Hz", "")
		if int(res) > int(config_res) or (int(res) == int(config_res) and ((pol == "p" and config_pol == "i") or (config_mode == "2160p30" and mode == "2160p"))):
			setmode[config_port].value = config_mode
		if config_rate not in ("auto", "multi") and (rate in ("auto", "multi") or int(config_rate) < int(rate)):
			setrate[config_mode].value = config_rate

	def confirm(self, confirmed):
		if not confirmed:
			if self.reset_mode == 1:
				config.av.videoport.value = self.last_good[0]
				config.av.videomode[self.last_good[0]].value = self.last_good[1]
				config.av.videorate[self.last_good[1]].value = self.last_good[2]
				config.av.autores_sd.value = self.last_good_extra[0]
				config.av.smart1080p.value = self.last_good_extra[1]
				avSwitch.setMode(*self.last_good)
			elif self.reset_mode == 2:
				for key, (port, mode, rate) in self.last_good_autores_modes.items():
					getattr(config.av, f"autores_mode_{key}")[port].value = mode
					getattr(config.av, f"autores_rate_{key}")[mode].value = rate
				config.av.autores_24p.value = self.last_good_autores_extra[0]
				config.av.autores_1080i_deinterlace.value = self.last_good_autores_extra[1]
				config.av.autores_unknownres.value = self.last_good_autores_unknownres
				if self.current_mode in avSwitch.readAvailableModes():
					avSwitch.setVideoModeDirect(self.current_mode)
				else:
					avSwitch.setMode(*self.last_good)
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
		self.reset_mode = 0
		port = config.av.videoport.value
		mode = config.av.videomode[port].value
		rate = config.av.videorate[mode].value
		self.last_good = (port, mode, rate)
		autores_sd = config.av.autores_sd.value
		smart1080p = config.av.smart1080p.value
		self.last_good_extra = (autores_sd, smart1080p)
		self.last_good_autores_modes = self.getAutoresModes(port)
		autores_24p = config.av.autores_24p.value
		autores_1080i = config.av.autores_1080i_deinterlace.value
		self.last_good_autores_extra = (autores_24p, autores_1080i)
		self.last_good_autores_unknownres = config.av.autores_unknownres.value
		self.last_good_autores = config.av.autores.value

	def saveAll(self):
		if config.av.videoport.value == "Scart":
			config.av.autores.value = "disabled"
		return Setup.saveAll(self)

	def keySave(self):
		port = config.av.videoport.value
		mode = config.av.videomode[port].value
		rate = config.av.videorate[mode].value
		autores_sd = config.av.autores_sd.value
		smart1080p = config.av.smart1080p.value
		autores_24p = config.av.autores_24p.value
		autores_1080i = config.av.autores_1080i_deinterlace.value
		if config.av.autores.value in ("all", "hd") and ((port, mode, rate) != self.last_good or (autores_sd, smart1080p) != self.last_good_extra):
			self.reset_mode = 1
			# The "true" value is for compatibility with old ConfigEnableDisable.
			smartMode = "1080p" if "1080" in autores_sd else {"1080p50": "1080p", "true": "1080p", "2160p50": "2160p", "1080i50": "1080i", "720p50": "720p"}.get(smart1080p)
			if smartMode:
				avSwitch.setMode(port, smartMode, "50Hz")
			else:
				avSwitch.setMode(port, mode, rate)
		elif (port, mode, rate) != self.last_good or (config.av.autores.value == "disabled" and self.last_good_autores != "disabled"):
			self.reset_mode = 1
			avSwitch.setMode(port, mode, rate)
		elif config.av.autores.value in ("native", "simple") and (self.getAutoresModes(port) != self.last_good_autores_modes or (autores_24p, autores_1080i) != self.last_good_autores_extra
			or self.last_good_autores != config.av.autores.value or self.reset_mode == 1 or (self.last_good_autores_unknownres != config.av.autores_unknownres.value and config.av.autores.value == "native")):
			self.reset_mode = 2
			if self.current_mode is None:
				self.current_mode = self.getCurrent_mode()
			AutoVideoMode(None).VideoChangeDetect()
		else:
			self.reset_mode = 0
			Setup.keySave(self)
			return
		if BoxInfo.getItem("machinebuild") == "gbquad4kpro" and mode.startswith("2160p"):  # Hack for GB QUAD 4K Pro!
			config.av.hdmicolordepth.value = "10bit"
			config.av.hdmicolordepth.save()
		self.session.openWithCallback(self.confirm, MessageBox, _("Is this video mode ok?"), MessageBox.TYPE_YESNO, timeout=20, default=False)

	def getCurrent_mode(self):
		return eAVControl.getInstance().getVideoMode("") or None

	def changedEntry(self):
		if config.av.autores_preview.value:
			ConfigListScreen.changedEntry(self)
			cur = self["config"].getCurrent()
			cur = cur and len(cur) > 3 and cur[3]
			if cur and cur.startswith("check"):
				if self.current_mode is None:
					self.current_mode = self.getCurrent_mode()
				key = cur[6:]  # Empty for the preview switch itself, which checks all classes.
				for x in ("sd", "hd", "fhd", "uhd"):
					if key in ("", x):
						self.getVerify_videomode(getattr(config.av, f"autores_mode_{x}"), getattr(config.av, f"autores_rate_{x}"))
				if not key or getattr(self, f"prev_{key}"):
					AutoVideoMode(None).VideoChangeDetect()
		else:
			Setup.changedEntry(self)


class AutoVideoModeLabel(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self["content"] = Label()
		self["restxt"] = Label()
		self.hideTimer = eTimer()
		self.hideTimer.callback.append(self.hide)
		self.onShow.append(self.hide_me)

	def hide_me(self):
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
		if config.osd.threeDmode.value == "auto":
			global isDedicated3D
			isDedicated3D = self.checkIfDedicated3D()
			if isDedicated3D:
				applySettings(isDedicated3D)
			else:
				applySettings()

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
		if config.av.autores.value == "disabled" or getAutoresPlugin_enabled():
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

	def VideoChangeDetect(self):
		# Info: Auto resolution preview or save settings call this function with session = None / ~338, ~374.
		global resolutionlabel
		avControl = eAVControl.getInstance()
		config_port, config_mode, config_res, config_pol, config_rate = getConfig_videomode(config.av.videomode, config.av.videorate)
		config_mode = config_mode.replace("p30", "p")
		current_mode = avControl.getVideoMode("")
		if current_mode.upper() in ("PAL", "NTSC"):
			current_mode = current_mode.upper()
		current_pol = ""
		if "i" in current_mode:
			current_pol = "i"
		elif "p" in current_mode:
			current_pol = "p"
		current_res = current_pol and current_mode.split(current_pol)[0].replace("\n", "") or ""  # noqa F841
		current_rate = current_pol and current_mode.split(current_pol)[0].replace("\n", "") and current_mode.split(current_pol)[1].replace("\n", "") or ""  # noqa F841
		write_mode = None
		new_mode = None
		video_rate = avControl.getFrameRate(0)
		video_pol = "p" if avControl.getProgressive() else "i"
		video_width = avControl.getResolutionX(0)
		video_height = avControl.getResolutionY(0)
		if not video_height or not video_width or not video_pol or not video_rate:
			service = self.session and self.session.nav.getCurrentService()
			if service is not None:
				info = service.info()
			else:
				info = None
			if info:
				video_height = int(info.getInfo(iServiceInformation.sVideoHeight))
				video_width = int(info.getInfo(iServiceInformation.sVideoWidth))
				video_pol = ("i", "p")[info.getInfo(iServiceInformation.sProgressive)]
				video_rate = int(info.getInfo(iServiceInformation.sFrameRate))
		print(f"[VideoMode] detect video height: {video_height}, width: {video_width}, pol: {video_pol}, rate: {video_rate} (current video mode: {current_mode})")
		if video_height and video_width and video_pol and video_rate:
			label_rate = (video_rate + 500) // 1000
			if video_pol == "i":
				label_rate *= 2
			resolutionlabel["content"].setText(_("Video content: %ix%i%s %iHz") % (video_width, video_height, video_pol, label_rate))
			if video_height != -1:
				if video_height > 720 or video_width > 1280:
					new_res = "1080"
				elif (576 < video_height <= 720) or video_width > 1024:
					new_res = "720"
				elif (480 < video_height <= 576) or video_width > 720 or video_rate in (25000, 23976, 24000):
					new_res = "576"
				else:
					new_res = "480"
			else:
				new_res = config_res
			if video_rate != -1:
				if video_rate == 25000 and video_pol == "i":
					new_rate = 50000
				elif video_rate == 59940 or (video_rate == 29970 and video_pol == "i"):
					new_rate = 60000
				elif video_rate == 23976:
					new_rate = 24000
				elif video_rate == 29970:
					new_rate = 30000
				else:
					new_rate = video_rate
				new_rate = str((new_rate + 500) // 1000)
			else:
				new_rate = config_rate
			new_pol = str(video_pol) if video_pol != -1 else config_pol
			autorestyp = ""
			if config_mode in ("PAL", "NTSC"):
				autorestyp = "PAL or NTSC"
				write_mode = config_mode
			elif config.av.autores.value == "simple":
				autorestyp = "simple"
				new_rate = (video_rate + 500) // 1000
				if video_height <= 576 and int(config_res) >= 576:  # SD.
					if config.av.autores_rate_sd[config.av.autores_mode_sd[config.av.videoport.value].value].value in ("auto", "multi"):
						if video_pol == "i":
							new_rate *= 2
					else:
						new_rate = config.av.autores_rate_sd[config.av.autores_mode_sd[config.av.videoport.value].value].value.replace("Hz", "")
					new_mode = config.av.autores_mode_sd[config_port].value.replace("p30", "p")
				elif video_height <= 720 and int(config_res) >= 720:  # HD.
					if config.av.autores_rate_hd[config.av.autores_mode_hd[config.av.videoport.value].value].value in ("auto", "multi"):
						if video_pol == "i":
							new_rate *= 2
					else:
						new_rate = config.av.autores_rate_hd[config.av.autores_mode_hd[config.av.videoport.value].value].value.replace("Hz", "")
					new_mode = config.av.autores_mode_hd[config_port].value.replace("p30", "p")
				elif video_height <= 1080 and int(config_res) >= 1080:  # FHD.
					if config.av.autores_rate_fhd[config.av.autores_mode_fhd[config.av.videoport.value].value].value in ("auto", "multi"):
						if video_pol == "i":
							new_rate *= 2
					else:
						new_rate = config.av.autores_rate_fhd[config.av.autores_mode_fhd[config.av.videoport.value].value].value.replace("Hz", "")
					new_mode = config.av.autores_mode_fhd[config_port].value.replace("p30", "p")
					if new_mode == "1080p" and not config.av.autores_1080i_deinterlace.value and video_height == 1080 and video_pol == "i":
						new_mode = "1080i"
				elif video_height <= 2160 and int(config_res) >= 2160:  # UHD.
					if config.av.autores_rate_uhd[config.av.autores_mode_uhd[config.av.videoport.value].value].value in ("auto", "multi"):
						if video_pol == "i":
							new_rate *= 2
					else:
						new_rate = config.av.autores_rate_uhd[config.av.autores_mode_uhd[config.av.videoport.value].value].value.replace("Hz", "")
					new_mode = config.av.autores_mode_uhd[config_port].value.replace("p30", "p")
				else:
					if config_rate not in ("auto", "multi"):
						new_rate = config_rate
					new_mode = config_mode
				new_rate = str(int(new_rate))
				if new_mode[-1:] == "p":
					new_rate = setProgressiveRate((video_rate + 500) // 1000 * (int(video_pol == "i") + 1), new_rate, new_mode[:-1], config_res, config_rate)
				if new_mode + new_rate in avSwitch.readAvailableModes():
					write_mode = new_mode + new_rate
				elif new_mode in avSwitch.readAvailableModes():
					write_mode = new_mode
				else:
					if config_rate not in ("auto", "multi") and int(new_rate) > int(config_rate):
						new_rate = config_rate
					if config_mode + new_rate in avSwitch.readAvailableModes():
						write_mode = config_mode + new_rate
					else:
						write_mode = config_mode
			elif config.av.autores.value == "native":
				autorestyp = "native"
				new_rate = (video_rate + 500) // 1000
				new_pol = video_pol
				new_res = str(video_height)
				if video_pol == "i":
					new_rate *= 2
				min_port, min_mode, min_res, min_pol, min_rate = getConfig_videomode(config.av.autores_mode_sd, config.av.autores_rate_sd)
				if video_height <= int(min_res):
					if new_pol == "i" and min_pol == "p":
						new_pol = min_pol
					if min_rate not in ("auto", "multi") and new_rate < int(min_rate):
						new_rate = int(min_rate)
					new_res = min_res
				if video_height >= int(config_res) or int(new_res) >= int(config_res):
					new_res = config_res
					if video_pol == "p" and config_pol == "i":
						new_pol = config_pol
					if config_rate not in ("auto", "multi") and int(config_rate) < int(new_rate):
						new_rate = int(config_rate)
				new_rate = str(int(new_rate))
				if new_pol == "p":
					new_rate = setProgressiveRate((video_rate + 500) // 1000 * (int(video_pol == "i") + 1), new_rate, new_res, config_res, config_rate)
				if new_res + new_pol + new_rate in avSwitch.readAvailableModes():
					write_mode = new_res + new_pol + new_rate
				elif new_res + new_pol in avSwitch.readAvailableModes():
					write_mode = new_res + new_pol
				elif new_res + min_pol + new_rate in avSwitch.readAvailableModes():
					write_mode = new_res + min_pol + new_rate
				elif new_res + min_pol in avSwitch.readAvailableModes():
					write_mode = new_res + min_pol
				else:
					if config.av.autores_unknownres.value == "next":
						if video_height <= 576 and int(config_res) >= 576:
							new_res = "576"
						elif video_height <= 720 and int(config_res) >= 720:
							new_res = "720"
						elif video_height <= 1080 and int(config_res) >= 1080:
							new_res = "1080"
						elif video_height <= 2160 and int(config_res) >= 2160:
							new_res = "2160"
					elif config.av.autores_unknownres.value == "highest":
						new_res = config_res
					if new_pol == "p":
						new_rate = setProgressiveRate((video_rate + 500) // 1000 * (int(video_pol == "i") + 1), new_rate, new_res, config_res, config_rate)
					if new_res + new_pol + new_rate in avSwitch.readAvailableModes():
						write_mode = new_res + new_pol + new_rate
					elif new_res + new_pol in avSwitch.readAvailableModes():
						write_mode = new_res + new_pol
					elif new_res + min_pol + new_rate in avSwitch.readAvailableModes():
						write_mode = new_res + min_pol + new_rate
					elif new_res + min_pol in avSwitch.readAvailableModes():
						write_mode = new_res + min_pol
					else:
						if config_rate not in ("auto", "multi") and int(new_rate) > int(config_rate):
							new_rate = config_rate
						if config_mode + new_rate in avSwitch.readAvailableModes():
							write_mode = config_mode + new_rate
						else:
							write_mode = config_mode
			elif config.av.autores.value == "all" or (config.av.autores.value == "hd" and int(new_res) >= 720):
				autorestyp = "all or hd"
				if config.av.autores_deinterlace.value:
					new_pol = new_pol.replace("i", "p")
				if new_res + new_pol + new_rate in avSwitch.readAvailableModes():
					new_mode = new_res + new_pol + new_rate
					if new_mode == "480p24" or new_mode == "576p24":
						new_mode = config.av.autores_480p24.value
					if new_mode == "720p24":
						new_mode = config.av.autores_720p24.value
					if new_mode == "1080p24":
						new_mode = config.av.autores_1080p24.value
					if new_mode == "1080p25":
						new_mode = config.av.autores_1080p25.value
					if new_mode == "1080p30":
						new_mode = config.av.autores_1080p30.value
					if new_mode == "2160p24":
						new_mode = config.av.autores_2160p24.value
					if new_mode == "2160p25" or new_mode == "2160p50":
						new_mode = config.av.autores_2160p25.value
					if new_mode == "2160p30" or new_mode == "2160p60" or new_mode == "2160p":
						new_mode = config.av.autores_2160p30.value
				elif new_res + new_pol in avSwitch.readAvailableModes():
					new_mode = new_res + new_pol
					if new_mode == "2160p30" or new_mode == "2160p60" or new_mode == "2160p":
						new_mode = config.av.autores_2160p30.value
				else:
					new_mode = config_mode + new_rate
				write_mode = new_mode
			elif config.av.autores.value == "hd" and int(new_res) <= 576:
				autorestyp = "hd"
				if new_pol == "p":
					new_mode = config.av.autores_sd.value.replace("i", "p") + new_rate
				else:
					new_mode = config.av.autores_sd.value + new_rate
					if config.av.autores_deinterlace.value:
						test_new_mode = config.av.autores_sd.value.replace("i", "p") + new_rate
						if test_new_mode in avSwitch.readAvailableModes():
							new_mode = test_new_mode
				if new_mode == "720p24":
					new_mode = config.av.autores_720p24.value
				if new_mode == "1080p24":
					new_mode = config.av.autores_1080p24.value
				if new_mode == "1080p25":
					new_mode = config.av.autores_1080p25.value
				if new_mode == "1080p30":
					new_mode = config.av.autores_1080p30.value
				if new_mode == "2160p24":
					new_mode = config.av.autores_2160p24.value
				if new_mode == "2160p25":
					new_mode = config.av.autores_2160p25.value
				if new_mode == "2160p30":
					new_mode = config.av.autores_2160p30.value
				write_mode = new_mode
			else:
				autorestyp = "no match"
				multi_videomode = ""
				f = None
				if config_rate in ("auto", "multi"):
					if eAVControl.getInstance().hasVideoAxis():
						multi_videomode = avControl.getVideoMode("")
					elif exists(f"/proc/stb/video/videomode_{new_rate}hz"):
						f = open(f"/proc/stb/video/videomode_{new_rate}hz")
				if f:
					multi_videomode = f.read().replace("\n", "")
					f.close()
				if multi_videomode and (current_mode != multi_videomode):
					write_mode = multi_videomode
				else:
					write_mode = config_mode + new_rate
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
					new_rate = "24"
				elif (mypath.find("p25.") >= 0) or (mypath.find("25p.") >= 0):
					new_rate = "25"
				elif (mypath.find("p30.") >= 0) or (mypath.find("30p.") >= 0):
					new_rate = "30"
				elif (mypath.find("p50.") >= 0) or (mypath.find("50p.") >= 0):
					new_rate = "50"
				elif (mypath.find("p60.") >= 0) or (mypath.find("60p.") >= 0):
					new_rate = "60"
				elif new_rate in ("auto", "multi"):
					new_rate = ""  # Omit frame rate specifier, e.g. "1080p" instead of "1080p50" if there is no clue.
				if mypath != "":
					if mypath.endswith(".ts"):
						print("[VIDEOMODE] playing .ts file")
						new_rate = "50"  # For .ts files.
					else:
						print("[VIDEOMODE] playing other (non .ts) file")
						# Use 'new_rate', from above, for all other videos.
				else:
					print("[VIDEOMODE] no path or no service reference, presumably live TV")
					new_rate = "50"  # For TV / or no service reference, then stay at 1080p50.
				new_rate = new_rate.replace("25", "50").replace("30", "60")
				if (config.av.smart1080p.value == "1080p50") or (config.av.smart1080p.value == "true"):  # For compatibility with old ConfigEnableDisable.
					write_mode = "1080p" + new_rate
				elif config.av.smart1080p.value == "2160p50":
					write_mode = "2160p" + new_rate
				elif config.av.smart1080p.value == "1080i50":
					if new_rate == "24":
						write_mode = "1080p24"  # Instead of 1080i24.
					else:
						write_mode = "1080i" + new_rate
				elif config.av.smart1080p.value == "720p50":
					write_mode = "720p" + new_rate
				# print(f"[VideoMode] smart1080p mode, selecting {write_mode}.")
			if write_mode and current_mode != write_mode and self.bufferfull or self.firstrun:
				values = avSwitch.readAvailableModes()
				if write_mode not in values:
					if write_mode in ("1080p24", "1080p30", "1080p60"):
						write_mode = "1080p"
					elif write_mode in ("2160p24", "2160p30", "2160p60"):
						write_mode = "2160p"
				if write_mode in values:
					avSwitch.setVideoModeDirect(write_mode)
					print(f"[VideoMode] setMode - port: {config_port}, mode: {write_mode} (autoresTyp: '{autorestyp}')")
					resolutionlabel["restxt"].setText(_("Video mode: %s") % write_mode)
				else:
					print(f"[VideoMode] setMode - port: {config_port}, mode: {write_mode} is not available")
					resolutionlabel["restxt"].setText(_("Video mode: %s not available") % write_mode)
				if config.av.autores_label_timeout.value:
					resolutionlabel.show()
			elif write_mode and current_mode != write_mode:
				# The resolution remained stuck at a wrong setting after streaming when self.bufferfull was False (should be fixed now after adding BufferInfoStop).
				print(f"[VideoMode] not changing from {current_mode} to {write_mode} as self.bufferfull is {self.bufferfull}")
		if write_mode and write_mode != current_mode or self.firstrun:
			avSwitch.setAspect(config.av.aspect)
			avSwitch.setWss(config.av.wss)
			avSwitch.setPolicy43(config.av.policy_43)
			avSwitch.setPolicy169(config.av.policy_169)
		self.firstrun = False
		self.delay = False
		self.detecttimer.stop()


def autostart(session):
	global resolutionlabel
	if getAutoresPlugin_enabled():
		config.av.autores.value = False
		config.av.autores.save()
		configfile.save()
	else:
		if resolutionlabel is None:
			resolutionlabel = session.instantiateDialog(AutoVideoModeLabel)
		AutoVideoMode(session)

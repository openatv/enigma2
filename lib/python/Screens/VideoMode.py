from os.path import exists

from enigma import eAVControl, iPlayableService, iServiceInformation, eTimer, eServiceCenter, eServiceReference, eDVBDB

from Components.ActionMap import HelpableActionMap
from Components.AVSwitch import avSwitch
from Components.ConfigList import ConfigListScreen
from Components.config import config, configfile, getConfigListEntry, ConfigNothing
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.ServiceEventTracker import ServiceEventTracker
from Screens.Setup import SetupSummary
from Components.Sources.Boolean import Boolean
from Components.Sources.StaticText import StaticText
from Components.SystemInfo import BoxInfo
from Screens.ChannelSelection import FLAG_IS_DEDICATED_3D
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
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


class VideoSetup(ConfigListScreen, Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		# for the skin: first try VideoSetup, then Setup, this allows individual skinning
		self.skinName = ["VideoSetup", "Setup"]
		self.setTitle(_("Video Settings"))
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["VKeyIcon"] = Boolean(False)
		self["footnote"] = Label()

		self.onChangedEntry = []

		# handle hotplug by re-creating setup
		self.onShow.append(self.startHotplug)
		self.onHide.append(self.stopHotplug)

		self.list = []
		ConfigListScreen.__init__(self, self.list, session=session, on_change=self.changedEntry)

		self["actions"] = HelpableActionMap(self, ["SetupActions", "MenuActions", "ColorActions"],
			{
				"cancel": self.keyCancel,
				"save": self.apply,
			}, -2)

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self["description"] = Label("")

		config.av.autores_preview.value = False
		self.current_mode = None
		self.createSetup()
		self.grabLastGoodMode()
		self["config"].onSelectionChanged.append(self.selectionChanged)

	def startHotplug(self):
		avSwitch.on_hotplug.append(self._createSetup)

	def stopHotplug(self):
		avSwitch.on_hotplug.remove(self._createSetup)

	# FIXME
	def _createSetup(self, what):
		self.createSetup()

	def createSetup(self):
		level = config.usage.setup_level.index

		self.list = [
			getConfigListEntry(_("Video output"), config.av.videoport, _("Configures which video output connector will be used."))
		]
		if config.av.videoport.value in ("HDMI", "YPbPr", "Scart-YPbPr") and not getAutoresPlugin_enabled():
			self.list.append(getConfigListEntry(_("Automatic resolution"), config.av.autores, _("If enabled the output resolution of the box will try to match the resolution of the video contents resolution")))
			if config.av.autores.value in ("all", "hd"):
				self.list.append(getConfigListEntry(_("Delay time"), config.av.autores_delay, _("Set the time before checking video source for resolution information.")))
				self.list.append(getConfigListEntry(_("Automatic resolution label"), config.av.autores_label_timeout, _("Allows you to adjust the amount of time the resolution information display on screen.")))
				self.list.append(getConfigListEntry(_("Force de-interlace"), config.av.autores_deinterlace, _("If enabled the video will always be de-interlaced.")))
				self.list.append(getConfigListEntry(_("Always use smart1080p mode"), config.av.smart1080p, _("This option allows you to always use e.g. 1080p50 for TV/.ts, and 1080p24/p50/p60 for videos")))
				if config.av.autores.value == "hd":
					self.list.append(getConfigListEntry(_("Show SD as"), config.av.autores_sd, _("This option allows you to choose how to display standard definition video on your TV.")))
				self.list.append(getConfigListEntry(_("Show 480/576p 24fps as"), config.av.autores_480p24, _("This option allows you to choose how to display SD progressive 24Hz on your TV. (as not all TV's support these resolutions)")))
				self.list.append(getConfigListEntry(_("Show 720p 24fps as"), config.av.autores_720p24, _("This option allows you to choose how to display 720p 24Hz on your TV. (as not all TV's support these resolutions)")))
				self.list.append(getConfigListEntry(_("Show 1080p 24fps as"), config.av.autores_1080p24, _("This option allows you to choose how to display 1080p 24Hz on your TV. (as not all TV's support these resolutions)")))
				self.list.append(getConfigListEntry(_("Show 1080p 25fps as"), config.av.autores_1080p25, _("This option allows you to choose how to display 1080p 25Hz on your TV. (as not all TV's support these resolutions)")))
				self.list.append(getConfigListEntry(_("Show 1080p 30fps as"), config.av.autores_1080p30, _("This option allows you to choose how to display 1080p 30Hz on your TV. (as not all TV's support these resolutions)")))
				if "2160p24" in avSwitch.readAvailableModes():
					self.list.append(getConfigListEntry(_("Show 2160p 24fps as"), config.av.autores_2160p24, _("This option allows you to choose how to display 2160p 24Hz on your TV. (as not all TV's support these resolutions)")))
					self.list.append(getConfigListEntry(_("Show 2160p 25fps as"), config.av.autores_2160p25, _("This option allows you to choose how to display 2160p 25Hz on your TV. (as not all TV's support these resolutions)")))
					self.list.append(getConfigListEntry(_("Show 2160p 30fps as"), config.av.autores_2160p30, _("This option allows you to choose how to display 2160p 30Hz on your TV. (as not all TV's support these resolutions)")))

			elif config.av.autores.value == "simple":
				self.list.append(getConfigListEntry(_("Delay time"), config.av.autores_delay, _("Set the time before checking video source for resolution information.")))
				self.list.append(getConfigListEntry(_("Automatic resolution label"), config.av.autores_label_timeout, _("Allows you to adjust the amount of time the resolution information display on screen.")))
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
					self.list.append(getConfigListEntry(_("Enable preview"), config.av.autores_preview, _("Show preview of current mode (*)."), "check"))
				else:
					config.av.autores_preview.value = False
				self.getVerify_videomode(config.av.autores_mode_sd, config.av.autores_rate_sd)
				self.list.append(getConfigListEntry(pgettext(_("Video output mode for SD"), _("%sMode for SD (up to 576p)") % self.prev_sd), config.av.autores_mode_sd[config.av.videoport.value], _("This option configures the video output mode (or resolution)."), "check_sd"))
				self.list.append(getConfigListEntry(_("%sRefresh rate for SD") % self.prev_sd, config.av.autores_rate_sd[config.av.autores_mode_sd[config.av.videoport.value].value], _("Configure the refresh rate of the screen."), "check_sd"))
				modelist = avSwitch.getModeList(config.av.videoport.value)
				if "720p" in avSwitch.readAvailableModes():
					self.getVerify_videomode(config.av.autores_mode_hd, config.av.autores_rate_hd)
					self.list.append(getConfigListEntry(pgettext(_("Video output mode for HD"), _("%sMode for HD (up to 720p)") % self.prev_hd), config.av.autores_mode_hd[config.av.videoport.value], _("This option configures the video output mode (or resolution)."), "check_hd"))
					self.list.append(getConfigListEntry(_("%sRefresh rate for HD") % self.prev_hd, config.av.autores_rate_hd[config.av.autores_mode_hd[config.av.videoport.value].value], _("Configure the refresh rate of the screen."), "check_hd"))
				if "1080i" in avSwitch.readAvailableModes() or "1080p" in avSwitch.readAvailableModes():
					self.getVerify_videomode(config.av.autores_mode_fhd, config.av.autores_rate_fhd)
					self.list.append(getConfigListEntry(pgettext(_("Video output mode for FHD"), _("%sMode for FHD (up to 1080p)") % self.prev_fhd), config.av.autores_mode_fhd[config.av.videoport.value], _("This option configures the video output mode (or resolution)."), "check_fhd"))
					self.list.append(getConfigListEntry(_("%sRefresh rate for FHD") % self.prev_fhd, config.av.autores_rate_fhd[config.av.autores_mode_fhd[config.av.videoport.value].value], _("Configure the refresh rate of the screen."), "check_fhd"))
					if config.av.autores_mode_fhd[config.av.videoport.value].value == '1080p' and ('1080p' in avSwitch.readAvailableModes() or "1080p50" in avSwitch.readAvailableModes()):
						self.list.append(getConfigListEntry(_("%sShow 1080i as 1080p") % self.prev_fhd, config.av.autores_1080i_deinterlace, _("Use Deinterlacing for 1080i Videosignal?"), "check_fhd"))
					elif "1080p" not in avSwitch.readAvailableModes() and "1080p50" not in avSwitch.readAvailableModes():
						config.av.autores_1080i_deinterlace.value = False
				if "2160p" in avSwitch.readAvailableModes() or "2160p30" in avSwitch.readAvailableModes():
					self.getVerify_videomode(config.av.autores_mode_uhd, config.av.autores_rate_uhd)
					self.list.append(getConfigListEntry(pgettext(_("Video output mode for UHD"), _("%sMode for UHD (up to 2160p)") % self.prev_uhd), config.av.autores_mode_uhd[config.av.videoport.value], _("This option configures the video output mode (or resolution)."), "check_uhd"))
					self.list.append(getConfigListEntry(_("%sRefresh rate for UHD") % self.prev_uhd, config.av.autores_rate_uhd[config.av.autores_mode_uhd[config.av.videoport.value].value], _("Configure the refresh rate of the screen."), "check_uhd"))
				self.list.append(getConfigListEntry(_("Show 24p up to 720p / higher than 720p as"), config.av.autores_24p, _("Show 24p up to resolution 720p or higher than 720p as a different Framerate.")))
				self.list.append(getConfigListEntry(_("Show 25p up to 720p / higher than 720p as"), config.av.autores_25p, _("Show 25p up to resolution 720p or higher than 720p as a different Framerate.")))
				self.list.append(getConfigListEntry(_("Show 30p up to 720p / higher than 720p as"), config.av.autores_30p, _("Show 30p up to resolution 720p or higher than 720p as a different Framerate.")))
			elif config.av.autores.value == "native":
				self.list.append(getConfigListEntry(_("Delay time"), config.av.autores_delay, _("Set the time before checking video source for resolution information.")))
				self.list.append(getConfigListEntry(_("Automatic resolution label"), config.av.autores_label_timeout, _("Allows you to adjust the amount of time the resolution information display on screen.")))
				self.getVerify_videomode(config.av.autores_mode_sd, config.av.autores_rate_sd)
				self.list.append(getConfigListEntry(pgettext(_("Lowest Video output mode"), _("Lowest Mode")), config.av.autores_mode_sd[config.av.videoport.value], _("This option configures the video output mode (or resolution).")))
				self.list.append(getConfigListEntry(_("Refresh rate for 'Lowest Mode'"), config.av.autores_rate_sd[config.av.autores_mode_sd[config.av.videoport.value].value], _("Configure the refresh rate of the screen.")))
				self.list.append(getConfigListEntry(_("Show 24p up to 720p / higher than 720p as"), config.av.autores_24p, _("Show 24p up to resolution 720p or higher than 720p as a different Framerate.")))
				self.list.append(getConfigListEntry(_("Show 25p up to 720p / higher than 720p as"), config.av.autores_25p, _("Show 25p up to resolution 720p or higher than 720p as a different Framerate.")))
				self.list.append(getConfigListEntry(_("Show 30p up to 720p / higher than 720p as"), config.av.autores_30p, _("Show 30p up to resolution 720p or higher than 720p as a different Framerate.")))
				self.list.append(getConfigListEntry(_("Show unknown video format as"), config.av.autores_unknownres, _("Show unknown Videoresolution as next higher or as highest screen resolution.")))

		# if we have modes for this port:
		if (config.av.videoport.value in config.av.videomode and config.av.autores.value == "disabled") or config.av.videoport.value == "Scart":
			# add mode- and rate-selection:
			self.list.append(getConfigListEntry(pgettext(_("Video output mode"), _("Mode")), config.av.videomode[config.av.videoport.value], _("This option configures the video output mode (or resolution).")))
			if config.av.videomode[config.av.videoport.value].value == "PC":
				self.list.append(getConfigListEntry(_("Resolution"), config.av.videorate[config.av.videomode[config.av.videoport.value].value], _("This option configures the screen resolution in PC output mode.")))
			elif config.av.videoport.value != "Scart":
				self.list.append(getConfigListEntry(_("Refresh rate"), config.av.videorate[config.av.videomode[config.av.videoport.value].value], _("Configure the refresh rate of the screen.")))

		port = config.av.videoport.value
		mode = config.av.videomode[port].value if port in config.av.videomode else None

		# some modes (720p, 1080i) are always widescreen. Don't let the user select something here, "auto" is not what he wants.
		force_wide = avSwitch.isWidescreenMode(port, mode)

		if not force_wide:
			self.list.append(getConfigListEntry(_("Aspect ratio"), config.av.aspect, _("Configure the aspect ratio of the screen.")))

		if force_wide or config.av.aspect.value in ("16:9", "16:10"):
			self.list.extend((
				getConfigListEntry(_("Display 4:3 content as"), config.av.policy_43, _("When the content has an aspect ratio of 4:3, choose whether to scale/stretch the picture.")),
				getConfigListEntry(_("Display >16:9 content as"), config.av.policy_169, _("When the content has an aspect ratio of 16:9, choose whether to scale/stretch the picture."))
			))
		elif config.av.aspect.value == "4:3":
			self.list.append(getConfigListEntry(_("Display 16:9 content as"), config.av.policy_169, _("When the content has an aspect ratio of 16:9, choose whether to scale/stretch the picture.")))

		if config.av.videoport.value == "HDMI":
			if not BoxInfo.getItem("AmlogicFamily"):
				self.list.append(getConfigListEntry(_("Aspect switch"), config.av.aspectswitch.enabled, _("This option allows you to set offset values for different Letterbox resolutions.")))
				if config.av.aspectswitch.enabled.value:
					for aspect in range(5):
						self.list.append(getConfigListEntry(f" -> {avSwitch.ASPECT_SWITCH_MSG[aspect]}", config.av.aspectswitch.offsets[str(aspect)]))

			self.list.append(getConfigListEntry(_("Allow unsupported modes"), config.av.edid_override, _("This option allows you to use all HDMI Modes")))

		if config.av.videoport.value == "Scart":
			self.list.append(getConfigListEntry(_("Color format"), config.av.colorformat, _("Configure which color format should be used on the SCART output.")))
			if level >= 1:
				self.list.append(getConfigListEntry(_("WSS on 4:3"), config.av.wss, _("When enabled, content with an aspect ratio of 4:3 will be stretched to fit the screen.")))
				if BoxInfo.getItem("ScartSwitch"):
					self.list.append(getConfigListEntry(_("Auto SCART switching"), config.av.vcrswitch, _("When enabled, your receiver will detect activity on the VCR SCART input.")))

		if not isinstance(config.av.scaler_sharpness, ConfigNothing) and not isPluginInstalled("VideoEnhancement"):
			self.list.append(getConfigListEntry(_("Scaler sharpness"), config.av.scaler_sharpness, _("This option configures the picture sharpness.")))

		if BoxInfo.getItem("havecolorspace"):
			self.list.append(getConfigListEntry(_("HDMI color space"), config.av.hdmicolorspace, _("This option allows you can config the Colorspace from Auto to RGB")))

		if BoxInfo.getItem("havecolorimetry"):
			self.list.append(getConfigListEntry(_("HDMI Colorimetry"), config.av.hdmicolorimetry, _("This option allows you can config the Colorimetry for HDR")))

		if BoxInfo.getItem("havehdmicolordepth"):
			self.list.append(getConfigListEntry(_("HDMI color depth"), config.av.hdmicolordepth, _("This option allows you can config the Colordepth for UHD")))

		if BoxInfo.getItem("havehdmihdrtype"):
			self.list.append(getConfigListEntry(_("HDMI HDR Type"), config.av.hdmihdrtype, _("This option allows you can force the HDR Modes for UHD")))

		if BoxInfo.getItem("Canedidchecking"):
			self.list.append(getConfigListEntry(_("Bypass HDMI EDID Check"), config.av.bypass_edid_checking, _("This option allows you to bypass HDMI EDID check")))

		if BoxInfo.getItem("haveboxmode"):
			self.list.append(getConfigListEntry(_("Change Boxmode to control Hardware Chip Modes*"), config.av.boxmode, _("Switch Mode to enable HDR Modes or PiP Functions")))

		if BoxInfo.getItem("HDRSupport"):
			self.list.append(getConfigListEntry(_("HLG Support"), config.av.hlg_support, _("This option allows you can force the HLG Modes for UHD")))
			self.list.append(getConfigListEntry(_("HDR10 Support"), config.av.hdr10_support, _("This option allows you can force the HDR10 Modes for UHD")))
			self.list.append(getConfigListEntry(_("Allow 12bit"), config.av.allow_12bit, _("This option allows you can enable or disable the 12 Bit Color Mode")))
			self.list.append(getConfigListEntry(_("Allow 10bit"), config.av.allow_10bit, _("This option allows you can enable or disable the 10 Bit Color Mode")))

		if BoxInfo.getItem("havesyncmode"):
			self.list.append(getConfigListEntry(_("Sync mode"), config.av.sync_mode, _("Setup how to control the channel changing.")))

		if BoxInfo.getItem("haveamlhdrsupport"):
			self.list.append(getConfigListEntry(_("HLG Support"), config.av.amlhlg_support, _("This option allows you can force the HLG Modes for UHD")))
			self.list.append(getConfigListEntry(_("HDR10 Support"), config.av.amlhdr10_support, _("This option allows you can force the HDR10 Modes for UHD")))

		self["config"].list = self.list
		self["config"].l.setList(self.list)
		if config.usage.sort_settings.value:
			self["config"].list.sort()

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

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.createSetup()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.createSetup()

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
				config.av.autores_mode_sd[self.last_good_autores_sd[0]].value = self.last_good_autores_sd[1]
				config.av.autores_rate_sd[self.last_good_autores_sd[1]].value = self.last_good_autores_sd[2]
				config.av.autores_mode_hd[self.last_good_autores_hd[0]].value = self.last_good_autores_hd[1]
				config.av.autores_rate_hd[self.last_good_autores_hd[1]].value = self.last_good_autores_hd[2]
				config.av.autores_mode_fhd[self.last_good_autores_fhd[0]].value = self.last_good_autores_fhd[1]
				config.av.autores_rate_fhd[self.last_good_autores_fhd[1]].value = self.last_good_autores_fhd[2]
				config.av.autores_mode_uhd[self.last_good_autores_uhd[0]].value = self.last_good_autores_uhd[1]
				config.av.autores_rate_uhd[self.last_good_autores_uhd[1]].value = self.last_good_autores_uhd[2]
				config.av.autores_24p.value = self.last_good_autores_extra[0]
				config.av.autores_1080i_deinterlace.value = self.last_good_autores_extra[1]
				config.av.autores_unknownres.value = self.last_good_autores_unknownres
				if self.current_mode in avSwitch.readAvailableModes():
					avSwitch.setVideoModeDirect(self.current_mode)
				else:
					avSwitch.setMode(*self.last_good)
			self.createSetup()
		else:
			self.keySave()

	def grabLastGoodMode(self):
		self.reset_mode = 0
		port = config.av.videoport.value
		mode = config.av.videomode[port].value
		rate = config.av.videorate[mode].value
		self.last_good = (port, mode, rate)
		autores_sd = config.av.autores_sd.value
		smart1080p = config.av.smart1080p.value
		self.last_good_extra = (autores_sd, smart1080p)

		mode = config.av.autores_mode_sd[port].value
		rate = config.av.autores_rate_sd[mode].value
		self.last_good_autores_sd = (port, mode, rate)
		mode = config.av.autores_mode_hd[port].value
		rate = config.av.autores_rate_hd[mode].value
		self.last_good_autores_hd = (port, mode, rate)
		mode = config.av.autores_mode_fhd[port].value
		rate = config.av.autores_rate_fhd[mode].value
		self.last_good_autores_fhd = (port, mode, rate)
		mode = config.av.autores_mode_uhd[port].value
		rate = config.av.autores_rate_uhd[mode].value
		self.last_good_autores_uhd = (port, mode, rate)
		autores_24p = config.av.autores_24p.value
		autores_1080i = config.av.autores_1080i_deinterlace.value
		self.last_good_autores_extra = (autores_24p, autores_1080i)
		self.last_good_autores_unknownres = config.av.autores_unknownres.value
		self.last_good_autores = config.av.autores.value

	def saveAll(self):
		if config.av.videoport.value == "Scart":
			config.av.autores.value = "disabled"
		for x in self["config"].list:
			x[1].save()
		configfile.save()

	def apply(self):
		port = config.av.videoport.value
		mode = config.av.videomode[port].value
		rate = config.av.videorate[mode].value
		autores_sd = config.av.autores_sd.value
		smart1080p = config.av.smart1080p.value

		mode_sd = config.av.autores_mode_sd[port].value
		rate_sd = config.av.autores_rate_sd[mode_sd].value
		mode_hd = config.av.autores_mode_hd[port].value
		rate_hd = config.av.autores_rate_hd[mode_hd].value
		mode_fhd = config.av.autores_mode_fhd[port].value
		rate_fhd = config.av.autores_rate_fhd[mode_fhd].value
		mode_uhd = config.av.autores_mode_uhd[port].value
		rate_uhd = config.av.autores_rate_uhd[mode_uhd].value
		autores_24p = config.av.autores_24p.value
		autores_1080i = config.av.autores_1080i_deinterlace.value

		if config.av.autores.value in ("all", "hd") and ((port, mode, rate) != self.last_good or (autores_sd, smart1080p) != self.last_good_extra):
			self.reset_mode = 1
			if autores_sd.find("1080") >= 0:
				avSwitch.setMode(port, "1080p", "50Hz")
			elif (smart1080p == "1080p50") or (smart1080p == "true"):  # for compatibility with old ConfigEnableDisable
				avSwitch.setMode(port, "1080p", "50Hz")
			elif smart1080p == "2160p50":
				avSwitch.setMode(port, "2160p", "50Hz")
			elif smart1080p == "1080i50":
				avSwitch.setMode(port, "1080i", "50Hz")
			elif smart1080p == "720p50":
				avSwitch.setMode(port, "720p", "50Hz")
			else:
				avSwitch.setMode(port, mode, rate)
		elif (port, mode, rate) != self.last_good or (config.av.autores.value == "disabled" and self.last_good_autores != "disabled"):
			self.reset_mode = 1
			avSwitch.setMode(port, mode, rate)
		elif config.av.autores.value in ("native", "simple") and ((port, mode_sd, rate_sd) != self.last_good_autores_sd or (port, mode_hd, rate_hd) != self.last_good_autores_hd or (port, mode_fhd, rate_fhd) != self.last_good_autores_fhd
			or (port, mode_uhd, rate_uhd) != self.last_good_autores_uhd or (autores_24p, autores_1080i) != self.last_good_autores_extra or self.last_good_autores != config.av.autores.value or self.reset_mode == 1
			or (self.last_good_autores_unknownres != config.av.autores_unknownres.value and config.av.autores.value == "native")):
			self.reset_mode = 2
			if self.current_mode is None:
				self.current_mode = self.getCurrent_mode()
			AutoVideoMode(None).VideoChangeDetect()
		else:
			self.reset_mode = 0
			self.keySave()
			return

		if BoxInfo.getItem("machinebuild") == "gbquad4kpro" and mode.startswith("2160p"):  # Hack for GB QUAD 4K Pro
			config.av.hdmicolordepth.value = "10bit"
			config.av.hdmicolordepth.save()

		self.session.openWithCallback(self.confirm, MessageBox, _("Is this video mode ok?"), MessageBox.TYPE_YESNO, timeout=20, default=False)

	def getCurrent_mode(self):
		mode = eAVControl.getInstance().getVideoMode("")
		return mode or None

	# for summary:
	def changedEntry(self):
		for x in self.onChangedEntry:
			x()
		if config.av.autores_preview.value:
			cur = self["config"].getCurrent()
			cur = cur and len(cur) > 3 and cur[3]
			if cur in ("check", "check_sd", "check_hd", "check_fhd", "check_uhd"):
				if self.current_mode is None:
					self.current_mode = self.getCurrent_mode()
				if cur in ("check", "check_sd"):
					self.getVerify_videomode(config.av.autores_mode_sd, config.av.autores_rate_sd)
				if cur in ("check", "check_hd"):
					self.getVerify_videomode(config.av.autores_mode_hd, config.av.autores_rate_hd)
				if cur in ("check", "check_fhd"):
					self.getVerify_videomode(config.av.autores_mode_fhd, config.av.autores_rate_fhd)
				if cur in ("check", "check_uhd"):
					self.getVerify_videomode(config.av.autores_mode_uhd, config.av.autores_rate_uhd)
				if cur == "check" or (cur == "check_sd" and self.prev_sd) or (cur == "check_hd" and self.prev_hd) or (cur == "check_fhd" and self.prev_fhd) or (cur == "check_uhd" and self.prev_uhd):
					AutoVideoMode(None).VideoChangeDetect()

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())

	def getCurrentDescription(self):
		return self["config"].getCurrent() and len(self["config"].getCurrent()) > 2 and self["config"].getCurrent()[2] or ""

	def createSummary(self):
		return SetupSummary

	def selectionChanged(self):
		self["description"].text = self.getCurrentDescription() if self["config"] else _("There are no items currently available for this screen.")


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
			open(BoxInfo.getItem("3DZNorm"), "w").write("%d" % znorm)
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
				#iPlayableService.evBuffering: self.BufferInfo, # currently disabled, does this really need? - with some streams will this permanently called (e.g. #SERVICE 4097:0:1:0:0:0:0:0:0:0:rtmp%3a//62.113.210.250/medienasa-live playpath=ok-wernigerode_high swfUrl=http%3a//www.blitzvideoserver06.de/blitzvideoplayer6.swf live=1 pageUrl=http%3a//iphonetv.in/#stream-id=45:Offener Kanal Wernigerode rtmp)
				#iPlayableService.evStopped: self.BufferInfoStop # sometimes not called or called before evBuffering -> if bufferfull = False (when evBuffering permanetly called and buffer < 98%) will autoresolution not longer working
				#iPlayableService.evEnd: self.BufferInfoStop # alternative for 'evStopped'
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
		#print '+'*50, 'BufferInfo',bufferInfo[0],self.bufferfull

	def BufferInfoStop(self):
		self.bufferfull = True
		#print '-'*50, 'BufferInfoStop'

	def VideoChanged(self):
		if config.av.autores.value == "disabled" or getAutoresPlugin_enabled():
			#print "[VideoMode] autoresolution is disabled - resolution not changed!"
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
		# info: autoresolution preview or save settings call this function with session = None / ~338, ~374
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
		current_res = current_pol and current_mode.split(current_pol)[0].replace("\n", "") or ""
		current_rate = current_pol and current_mode.split(current_pol)[0].replace("\n", "") and current_mode.split(current_pol)[1].replace("\n", "") or ""

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
				if video_height <= 576 and int(config_res) >= 576:  # sd
					if config.av.autores_rate_sd[config.av.autores_mode_sd[config.av.videoport.value].value].value in ("auto", "multi"):
						if video_pol == "i":
							new_rate *= 2
					else:
						new_rate = config.av.autores_rate_sd[config.av.autores_mode_sd[config.av.videoport.value].value].value.replace("Hz", "")
					new_mode = config.av.autores_mode_sd[config_port].value.replace("p30", "p")
				elif video_height <= 720 and int(config_res) >= 720:  # hd
					if config.av.autores_rate_hd[config.av.autores_mode_hd[config.av.videoport.value].value].value in ("auto", "multi"):
						if video_pol == "i":
							new_rate *= 2
					else:
						new_rate = config.av.autores_rate_hd[config.av.autores_mode_hd[config.av.videoport.value].value].value.replace("Hz", "")
					new_mode = config.av.autores_mode_hd[config_port].value.replace("p30", "p")
				elif video_height <= 1080 and int(config_res) >= 1080:  # fhd
					if config.av.autores_rate_fhd[config.av.autores_mode_fhd[config.av.videoport.value].value].value in ("auto", "multi"):
						if video_pol == "i":
							new_rate *= 2
					else:
						new_rate = config.av.autores_rate_fhd[config.av.autores_mode_fhd[config.av.videoport.value].value].value.replace("Hz", "")
					new_mode = config.av.autores_mode_fhd[config_port].value.replace("p30", "p")
					if new_mode == "1080p" and not config.av.autores_1080i_deinterlace.value and video_height == 1080 and video_pol == "i":
						new_mode = "1080i"
				elif video_height <= 2160 and int(config_res) >= 2160:  # uhd
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
						new_rate = min_rate
					new_res = min_res
				if video_height >= int(config_res) or int(new_res) >= int(config_res):
					new_res = config_res
					if video_pol == "p" and config_pol == "i":
						new_pol = config_pol
					if config_rate not in ("auto", "multi") and int(config_rate) < new_rate:
						new_rate = config_rate
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
				if exists("/sys/class/display/mode") and config_rate in ("auto", "multi"):
					f = open("/sys/class/display/mode")
				elif exists(f"/proc/stb/video/videomode_{new_rate}hz") and config_rate in ("auto", "multi"):
					f = open(f"/proc/stb/video/videomode_{new_rate}hz")
				if f:
					multi_videomode = f.read().replace("\n", "")
					f.close()
					if multi_videomode and (current_mode != multi_videomode):
						write_mode = multi_videomode
					else:
						write_mode = config_mode + new_rate

			# workaround for bug, see https://www.opena.tv/forum/showthread.php?1642-Autoresolution-Plugin&p=38836&viewfull=1#post38836
			# always use a fixed resolution and frame rate   (e.g. 1080p50 if supported) for TV or .ts files
			# always use a fixed resolution and correct rate (e.g. 1080p24/p50/p60 for all other videos
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
				# no frame rate information available, check if filename (or directory name) contains a hint
				# (allow user to force a frame rate this way):
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
					new_rate = ""  # omit frame rate specifier, e.g. "1080p" instead of "1080p50" if there is no clue
				if mypath != "":
					if mypath.endswith(".ts"):
						print("[VIDEOMODE] playing .ts file")
						new_rate = "50"  # for .ts files
					else:
						print("[VIDEOMODE] playing other (non .ts) file")
						# new_rate from above for all other videos
				else:
					print("[VIDEOMODE] no path or no service reference, presumably live TV")
					new_rate = "50"  # for TV / or no service reference, then stay at 1080p50

				new_rate = new_rate.replace("25", "50").replace("30", "60")

				if (config.av.smart1080p.value == "1080p50") or (config.av.smart1080p.value == "true"):  # for compatibility with old ConfigEnableDisable
					write_mode = "1080p" + new_rate
				elif config.av.smart1080p.value == "2160p50":
					write_mode = "2160p" + new_rate
				elif config.av.smart1080p.value == "1080i50":
					if new_rate == "24":
						write_mode = "1080p24"  # instead of 1080i24
					else:
						write_mode = "1080i" + new_rate
				elif config.av.smart1080p.value == "720p50":
					write_mode = "720p" + new_rate
				#print("[VideoMode] smart1080p mode, selecting %s" % write_mode)

			if write_mode and current_mode != write_mode and self.bufferfull or self.firstrun:
				values = avSwitch.readAvailableModes()
				if write_mode not in values:
					if write_mode in ("1080p24", "1080p30", "1080p60"):
						write_mode = "1080p"
					elif write_mode in ("2160p24", "2160p30", "2160p60"):
						write_mode = "2160p"
				if BoxInfo.getItem("AmlogicFamily"):
					if write_mode[-1] == "p" or write_mode[-1] == "i":
						write_mode += "60hz"
					else:
						write_mode += "hz"
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
				# the resolution remained stuck at a wrong setting after streaming when self.bufferfull was False (should be fixed now after adding BufferInfoStop)
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

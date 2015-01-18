from os import path

from enigma import iPlayableService, iServiceInformation, eTimer

from Screens.Screen import Screen
from Components.SystemInfo import SystemInfo
from Components.ConfigList import ConfigListScreen
from Components.config import config, configfile, getConfigListEntry
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Components.Pixmap import Pixmap
from Components.Sources.Boolean import Boolean
from Components.ServiceEventTracker import ServiceEventTracker
from Tools.Directories import resolveFilename, SCOPE_PLUGINS
from Components.AVSwitch import iAVSwitch

resolutionlabel = None

class VideoSetup(Screen, ConfigListScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = ["Setup"]
		self.setup_title = _("A/V settings")
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["VKeyIcon"] = Boolean(False)
		self['footnote'] = Label()

		self.hw = iAVSwitch
		self.onChangedEntry = []

		# handle hotplug by re-creating setup
		self.onShow.append(self.startHotplug)
		self.onHide.append(self.stopHotplug)

		self.list = []
		ConfigListScreen.__init__(self, self.list, session=session, on_change=self.changedEntry)

		from Components.ActionMap import ActionMap
		self["actions"] = ActionMap(["SetupActions", "MenuActions"], {
			"cancel": self.keyCancel,
			"save": self.apply,
			"menu": self.closeRecursive,
		}, -2)

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self["description"] = Label("")

		self.createSetup()
		self.grabLastGoodMode()
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(self.setup_title)

	def startHotplug(self):
		self.hw.on_hotplug.append(self.createSetup)

	def stopHotplug(self):
		self.hw.on_hotplug.remove(self.createSetup)

	def createSetup(self):
		level = config.usage.setup_level.index

		self.list = [
			getConfigListEntry(
				_("Video output"), config.av.videoport,
				_("Configures which video output connector will be used."))
		]
		if config.av.videoport.value in ('HDMI', 'YPbPr', 'Scart-YPbPr') and not path.exists(resolveFilename(SCOPE_PLUGINS) + 'SystemPlugins/AutoResolution'):
			self.list.append(getConfigListEntry(
				_("Automatic resolution"), config.av.autores,
				_("If enabled the output resolution will try to match the resolution of the video content.")))
			if config.av.autores.value:
				self.list.append(getConfigListEntry(
					_("Delay time"), config.av.autores_delay,
					_("Set the time before checking video source for resolution information.")))
				self.list.append(getConfigListEntry(
					_("Automatic resolution label"), config.av.autores_label_timeout,
					_("Allows you to adjust the amount of time the resolution information display stays on screen.")))

				self.list.append(getConfigListEntry(
					_("Show 480 24Hz as"), config.av.autores_sd24,
					_("This option allows you to choose how to display 480 24Hz content.")))
				self.list.append(getConfigListEntry(
					_("Show 576 25Hz as"), config.av.autores_sd25,
					_("This option allows you to choose how to display 576 25Hz content.")))
				self.list.append(getConfigListEntry(
					_("Show 480 30Hz as"), config.av.autores_sd30,
					_("This option allows you to choose how to display 480 30Hz content.")))
				self.list.append(getConfigListEntry(
					_("Show 576i 50Hz as"), config.av.autores_sd50i,
					_("This option allows you to choose how to display 576i 50Hz content.")))
				self.list.append(getConfigListEntry(
					_("Show 576p 50Hz as"), config.av.autores_sd50p,
					_("This option allows you to choose how to display 576p 50Hz content.")))
				self.list.append(getConfigListEntry(
					_("Show 480i 60Hz as"), config.av.autores_sd60i,
					_("This option allows you to choose how to display 480i 60Hz content.")))
				self.list.append(getConfigListEntry(
					_("Show 480p 60Hz as"), config.av.autores_sd60p,
					_("This option allows you to choose how to display 480p 60Hz content.")))

				self.list.append(getConfigListEntry(
					_("Show 720 24Hz as"), config.av.autores_ed24,
					_("This option allows you to choose how to display 720 24Hz content.")))
				self.list.append(getConfigListEntry(
					_("Show 720 25Hz as"), config.av.autores_ed25,
					_("This option allows you to choose how to display 720 25Hz content.")))
				self.list.append(getConfigListEntry(
					_("Show 720 30Hz as"), config.av.autores_ed30,
					_("This option allows you to choose how to display 720 30Hz content.")))
				self.list.append(getConfigListEntry(
					_("Show 720 50Hz as"), config.av.autores_ed50,
					_("This option allows you to choose how to display 720 50Hz content.")))
				self.list.append(getConfigListEntry(
					_("Show 720 60Hz as"), config.av.autores_ed60,
					_("This option allows you to choose how to display 720 60Hz content.")))

				self.list.append(getConfigListEntry(
					_("Show 1080 24Hz as"), config.av.autores_hd24,
					_("This option allows you to choose how to display 1080 24Hz content.")))
				self.list.append(getConfigListEntry(
					_("Show 1080 25Hz as"), config.av.autores_hd25,
					_("This option allows you to choose how to display 1080 25Hz content.")))
				self.list.append(getConfigListEntry(
					_("Show 1080 30Hz as"), config.av.autores_hd30,
					_("This option allows you to choose how to display 1080 30Hz content.")))
				self.list.append(getConfigListEntry(
					_("Show 1080 50Hz as"), config.av.autores_hd50,
					_("This option allows you to choose how to display 1080 50Hz content.")))
				self.list.append(getConfigListEntry(
					_("Show 1080 60Hz as"), config.av.autores_hd60,
					_("This option allows you to choose how to display 1080 60Hz content.")))

		# if we have modes for this port:
		if (config.av.videoport.value in config.av.videomode and not config.av.autores.value) or config.av.videoport.value == 'Scart':
			# add mode- and rate-selection:
			self.list.append(getConfigListEntry(pgettext("Video output mode", "Mode"), config.av.videomode[config.av.videoport.value], _("This option configures the video output mode (or resolution).")))
			if config.av.videomode[config.av.videoport.value].value == 'PC':
				self.list.append(getConfigListEntry(_("Resolution"), config.av.videorate[config.av.videomode[config.av.videoport.value].value], _("This option configures the screen resolution in PC output mode.")))
			elif config.av.videoport.value != 'Scart':
				self.list.append(getConfigListEntry(_("Refresh rate"), config.av.videorate[config.av.videomode[config.av.videoport.value].value], _("Configure the refresh rate of the screen.")))

		port = config.av.videoport.value
		if port not in config.av.videomode:
			mode = None
		else:
			mode = config.av.videomode[port].value

		# some modes (720p, 1080i) are always widescreen. Don't let the user select something here, "auto" is not what he wants.
		force_wide = self.hw.isWidescreenMode(port, mode)

		if not force_wide:
			self.list.append(getConfigListEntry(_("Aspect ratio"), config.av.aspect, _("Configure the aspect ratio of the screen.")))

		if force_wide or config.av.aspect.value in ("16:9", "16:10"):
			self.list.extend((
				getConfigListEntry(_("Display 4:3 content as"), config.av.policy_43, _("When the content has an aspect ratio of 4:3, choose whether to scale/stretch the picture.")),
				getConfigListEntry(_("Display >16:9 content as"), config.av.policy_169, _("When the content has an aspect ratio of 16:9, choose whether to scale/stretch the picture."))
			))
		elif config.av.aspect.value == "4:3":
			self.list.append(getConfigListEntry(_("Display 16:9 content as"), config.av.policy_169, _("When the content has an aspect ratio of 16:9, choose whether to scale/stretch the picture.")))

		if config.av.videoport.value == "Scart":
			self.list.append(getConfigListEntry(_("Color format"), config.av.colorformat, _("Configure which color format should be used on the SCART output.")))
			if level >= 1:
				self.list.append(getConfigListEntry(_("WSS on 4:3"), config.av.wss, _("When enabled, content with an aspect ratio of 4:3 will be stretched to fit the screen.")))
				if SystemInfo["ScartSwitch"]:
					self.list.append(getConfigListEntry(_("Auto scart switching"), config.av.vcrswitch, _("When enabled, your receiver will detect activity on the VCR SCART input.")))

		if level >= 1:
			if SystemInfo["CanDownmixAC3"]:
				self.list.append(getConfigListEntry(_("Dolby Digital / DTS downmix"), config.av.downmix_ac3, _("Choose whether multi-channel sound tracks should be down-mixed to stereo.")))
			if SystemInfo["CanDownmixAAC"]:
				self.list.append(getConfigListEntry(_("AAC downmix"), config.av.downmix_aac, _("Choose whether multi-channel sound tracks should be down-mixed to stereo.")))
			if SystemInfo["CanAACTranscode"]:
				self.list.append(getConfigListEntry(_("AAC transcoding"), config.av.transcodeaac, _("Choose whether AAC sound tracks should be transcoded.")))
			if SystemInfo["CanPcmMultichannel"]:
				self.list.append(getConfigListEntry(_("PCM Multichannel"), config.av.pcm_multichannel, _("Choose whether multi-channel sound tracks should be output as PCM.")))
			self.list.extend((
				getConfigListEntry(_("General AC3 delay"), config.av.generalAC3delay, _("This option configures the general audio delay of Dolby Digital (AC3) sound tracks.")),
				getConfigListEntry(_("General PCM delay"), config.av.generalPCMdelay, _("This option configures the general audio delay of stereo sound tracks."))
			))

			if SystemInfo["Can3DSurround"]:
				self.list.append(getConfigListEntry(_("3D Surround"), config.av.surround_3d,_("This option allows you to enable 3D Surround Sound for an output.")))

			if SystemInfo["Can3DSpeaker"] and config.av.surround_3d.value != "none":
				self.list.append(getConfigListEntry(_("3D Surround Speaker Position"), config.av.surround_3d_speaker,_("This option allows you to change the virtuell loadspeaker position.")))

			if SystemInfo["CanAutoVolume"]:
				self.list.append(getConfigListEntry(_("Auto Volume Level"), config.av.autovolume,_("This option configures output for Auto Volume Level.")))

			if SystemInfo["CanAutoVolume"]:
				self.list.append(getConfigListEntry(_("Audio Auto Volume Level"), config.av.autovolume, _("This option configures you can set Auto Volume Level.")))

			if SystemInfo["Canedidchecking"]:
				self.list.append(getConfigListEntry(_("Bypass HDMI EDID Check"), config.av.bypass_edid_checking, _("This option allows you to bypass HDMI EDID check")))

		# if not isinstance(config.av.scaler_sharpness, ConfigNothing):
		# 	self.list.append(getConfigListEntry(_("Scaler sharpness"), config.av.scaler_sharpness, _("This option configures the picture sharpness.")))

		self["config"].list = self.list
		self["config"].l.setList(self.list)
		if config.usage.sort_settings.value:
			self["config"].list.sort()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.createSetup()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.createSetup()

	def confirm(self, confirmed):
		if not confirmed:
			config.av.videoport.setValue(self.last_good[0])
			config.av.videomode[self.last_good[0]].setValue(self.last_good[1])
			config.av.videorate[self.last_good[1]].setValue(self.last_good[2])
			self.hw.setMode(*self.last_good)
		else:
			self.keySave()

	def grabLastGoodMode(self):
		port = config.av.videoport.value
		mode = config.av.videomode[port].value
		rate = config.av.videorate[mode].value
		self.last_good = (port, mode, rate)

	def saveAll(self):
		if config.av.videoport.value == 'Scart':
			config.av.autores.setValue(False)
		for x in self["config"].list:
			x[1].save()
		configfile.save()

	def apply(self):
		port = config.av.videoport.value
		mode = config.av.videomode[port].value
		rate = config.av.videorate[mode].value
		if (port, mode, rate) != self.last_good:
			self.hw.setMode(port, mode, rate)
			from Screens.MessageBox import MessageBox
			self.session.openWithCallback(self.confirm, MessageBox, _("Is this video mode OK?"), MessageBox.TYPE_YESNO, timeout=20, default=False)
		else:
			self.keySave()

	# for summary:
	def changedEntry(self):
		for x in self.onChangedEntry:
			x()

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())

	def getCurrentDescription(self):
		return self["config"].getCurrent() and len(self["config"].getCurrent()) > 2 and self["config"].getCurrent()[2] or ""

	def createSummary(self):
		from Screens.Setup import SetupSummary
		return SetupSummary

class AutoVideoModeLabel(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		self["content"] = Label()
		self["restxt"] = Label()

		self.hideTimer = eTimer()
		self.hideTimer.callback.append(self.hide)

		self.onShow.append(self.hide_me)

	def hide_me(self):
		idx = config.av.autores_label_timeout.index
		if idx:
			idx += 4
			self.hideTimer.start(idx * 1000, True)

class AutoVideoMode(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
				iPlayableService.evVideoSizeChanged: self.VideoChanged,
				iPlayableService.evVideoProgressiveChanged: self.VideoChanged,
				iPlayableService.evVideoFramerateChanged: self.VideoChanged,
				iPlayableService.evBuffering: self.BufferInfo,
			})

		self.delay = False
		self.bufferfull = True
		self.detecttimer = eTimer()
		self.detecttimer.callback.append(self.VideoChangeDetect)

	def BufferInfo(self):
		bufferInfo = self.session.nav.getCurrentService().streamed().getBufferCharge()
		if bufferInfo[0] > 98:
			self.bufferfull = True
			self.VideoChanged()
		else:
			self.bufferfull = False

	def VideoChanged(self):
		if self.session.nav.getCurrentlyPlayingServiceReference() and not self.session.nav.getCurrentlyPlayingServiceReference().toString().startswith('4097:'):
			delay = config.av.autores_delay.value
		else:
			delay = config.av.autores_delay.value * 2
		if not self.detecttimer.isActive() and not self.delay:
			self.delay = True
			self.detecttimer.start(delay, True)
		else:
			self.delay = True
			self.detecttimer.stop()
			self.detecttimer.start(delay, True)

	def VideoChangeDetect(self):
		self.delay = False

		config_port = config.av.videoport.value
		config_mode = str(config.av.videomode[config_port].value).strip()
		config_res = str(config.av.videomode[config_port].value).strip()[:-1]
		config_rate = str(config.av.videorate[config_mode].value).strip().replace('Hz', '')

		if not (config_rate == "multi" or config.av.autores.value):
			return

		if config_mode.upper() == 'PAL':
			config_mode = "576i"
		if config_mode.upper() == 'NTSC':
			config_mode = "480i"

		f = open("/proc/stb/video/videomode")
		current_mode = f.read().strip()
		f.close()
		if current_mode.upper() == 'PAL':
			current_mode = "576i"
		if current_mode.upper() == 'NTSC':
			current_mode = "480i"

		service = self.session.nav.getCurrentService()
		if not service:
			return

		info = service.info()
		if not info:
			return

		video_height = int(info.getInfo(iServiceInformation.sVideoHeight))
		video_width = int(info.getInfo(iServiceInformation.sVideoWidth))
		video_framerate = int(info.getInfo(iServiceInformation.sFrameRate))
		video_progressive = int(info.getInfo(iServiceInformation.sProgressive))

		if not ((0 < video_height <= 2160) and (0 < video_width <= 4096)):

			def _fromProc(pathname, base=10):
				res = None
				if path.exists(pathname):
					f = open(pathname, "r")
					try:
						val = int(f.read(), base)
						if val >= 0:
							res = val
					except:
						pass
					f.close()
				return res

			video_height = _fromProc("/proc/stb/vmpeg/0/yres", 16)
			video_width = _fromProc("/proc/stb/vmpeg/0/xres", 16)
			video_framerate = _fromProc("/proc/stb/vmpeg/0/framerate")
			video_progressive = _fromProc("/proc/stb/vmpeg/0/progressive")

		if not ((0 < video_height <= 2160) and (0 < video_width <= 4096)):
			print "[VideoMode] Can not determine video characteristics from service or /proc - do nothing"
			return

		if video_progressive == 0:
			video_fieldrate = 2 * video_framerate
		else:
			video_fieldrate = video_framerate

#		print "[VideoMode] VideoChangeDetect current_mode: %s, new width: %d, height: %d, framerate: %d, progressive: %d" % (
#			current_mode, video_width, video_height, video_framerate, video_progressive)

		p_string = ""
		if video_progressive == 0:
			p_string = "i"
		elif video_progressive == 1:
			p_string = "p"

		global resolutionlabel
		resolutionlabel["content"].setText("%s %ix%i%s %iHz" % (_("Video content:"), video_width, video_height, p_string, (video_fieldrate + 500) / 1000))

		if (700 < video_width <= 720) and video_height <= 480 and video_framerate in (23976, 24000, 29970, 30000, 59940, 60000):
			new_res = "480"
		elif (700 < video_width <= 720) and video_height <= 576 and video_framerate in (25000, 50000):
			new_res = "576"
		elif (video_width == 1280) and video_height <=720:
			new_res = "720"
		else:
			new_res = config_res

		new_rate = config_rate

		if config.av.autores.value and video_framerate > 0:
			new_rate = str((video_fieldrate + 500) / 1000)

		if new_rate == "multi":
			if video_framerate in (25000, 50000):
				new_rate = "50"
			else:
				new_rate = "60"

		new_mode = None
		if config.av.autores.value:
			if new_res == "480" and new_rate == "24":
				new_mode = config.av.autores_sd24.value
			elif new_res == "576" and new_rate == "25":
				new_mode = config.av.autores_sd25.value
			elif new_res == "480" and new_rate == "30":
				new_mode = config.av.autores_sd30.value
			elif new_res == "576" and new_rate == "50" and video_progressive == 0:
				new_mode = config.av.autores_sd50i.value
			elif new_res == "576" and new_rate == "50" and video_progressive == 1:
				new_mode = config.av.autores_sd50p.value
			elif new_res == "480" and new_rate == "60" and video_progressive == 0:
				new_mode = config.av.autores_sd60i.value
			elif new_res == "480" and new_rate == "60" and video_progressive == 1:
				new_mode = config.av.autores_sd60p.value
			elif new_res == "720" and new_rate == "24":
				new_mode = config.av.autores_ed24.value
			elif new_res == "720" and new_rate == "25":
				new_mode = config.av.autores_ed25.value
			elif new_res == "720" and new_rate == "30":
				new_mode = config.av.autores_ed30.value
			elif new_res == "720" and new_rate == "50":
				new_mode = config.av.autores_ed50.value
			elif new_res == "720" and new_rate == "60":
				new_mode = config.av.autores_ed60.value
			elif new_res == "1080" and new_rate == "24":
				new_mode = config.av.autores_hd24.value
			elif new_res == "1080" and new_rate == "25":
				new_mode = config.av.autores_hd25.value
			elif new_res == "1080" and new_rate == "30":
				new_mode = config.av.autores_hd30.value
			elif new_res == "1080" and new_rate == "50":
				new_mode = config.av.autores_hd50.value
			elif new_res == "1080" and new_rate == "60":
				new_mode = config.av.autores_hd60.value
			else:
				print "[VideoMode] autores could not find a mode for res=%s, rate=%s" % (new_res, new_rate)
		elif config_rate == 'multi' and path.exists('/proc/stb/video/videomode_%shz' % new_rate):
			try:
				f = open("/proc/stb/video/videomode_%shz" % new_rate, "r")
				multi_videomode = f.read().strip()
				f.close()
				if multi_videomode:
					new_mode = multi_videomode
			except:
				print "[VideoMode] exception when trying to find multi mode for", new_rate

		if not new_mode:
			print "[VideoMode] still don't have a new_mode making one from config_mode=%s, newrate=%s" % (config_mode, new_rate)
			new_mode = config_mode + new_rate

		if new_mode != current_mode:
			try:
				f = open("/proc/stb/video/videomode", "w")
				f.write(new_mode)
				f.close()

				resolutionlabel["restxt"].setText(_("Video mode: %s") % new_mode)
				resolutionlabel.hide()  # Need to hide then show to restart the timer
				if config.av.autores.value and int(config.av.autores_label_timeout.value) > 0:
					resolutionlabel.show()
			except:
				print "[VideoMode] FAILED to setMode - port: %s, mode: %s" % (config_port, new_mode)

		iAVSwitch.setAspect(config.av.aspect)
		iAVSwitch.setWss(config.av.wss)
		iAVSwitch.setPolicy43(config.av.policy_43)
		iAVSwitch.setPolicy169(config.av.policy_169)

def autostart(session):
	global resolutionlabel
	if not path.exists(resolveFilename(SCOPE_PLUGINS) + 'SystemPlugins/AutoResolution'):
		if resolutionlabel is None:
			resolutionlabel = session.instantiateDialog(AutoVideoModeLabel)
		AutoVideoMode(session)
	else:
		config.av.autores.setValue(False)
		config.av.autores.save()
		configfile.save()

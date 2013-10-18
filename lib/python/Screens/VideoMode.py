from Screens.Screen import Screen
from Components.SystemInfo import SystemInfo
from Components.ConfigList import ConfigListScreen
from Components.config import getConfigListEntry, config, ConfigBoolean, ConfigNothing, ConfigSlider
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Components.Pixmap import Pixmap
from Components.Sources.Boolean import Boolean
from os import path

from Components.AVSwitch import iAVSwitch

class VideoSetup(Screen, ConfigListScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = ["Setup" ]
		self.setup_title = _("A/V settings")
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["VKeyIcon"] = Boolean(False)
		self['footnote'] = Label()

		self.hw = iAVSwitch
		self.onChangedEntry = [ ]

		# handle hotplug by re-creating setup
		self.onShow.append(self.startHotplug)
		self.onHide.append(self.stopHotplug)

		self.list = [ ]
		ConfigListScreen.__init__(self, self.list, session = session, on_change = self.changedEntry)

		from Components.ActionMap import ActionMap
		self["actions"] = ActionMap(["SetupActions", "MenuActions"],
			{
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
			getConfigListEntry(_("Video output"), config.av.videoport, _("Configures which video output connector will be used."))
		]
		if config.av.videoport.getValue() in ('HDMI', 'YPbPr', 'Scart-YPbPr'):
			self.list.append(getConfigListEntry(_("Automatic resolution"), config.av.autores,_("If enabled the output resolution of the box will try to match the resolution of the video contents resolution")))
		# if we have modes for this port:
		if config.av.videoport.getValue() in config.av.videomode and not config.av.autores.getValue():
			# add mode- and rate-selection:
			self.list.append(getConfigListEntry(pgettext("Video output mode", "Mode"), config.av.videomode[config.av.videoport.getValue()], _("This option configures the video output mode (or resolution).")))
			if config.av.videomode[config.av.videoport.getValue()].getValue() == 'PC':
				self.list.append(getConfigListEntry(_("Resolution"), config.av.videorate[config.av.videomode[config.av.videoport.getValue()].getValue()], _("This option configures the screen resolution in PC output mode.")))
			else:
				self.list.append(getConfigListEntry(_("Refresh rate"), config.av.videorate[config.av.videomode[config.av.videoport.getValue()].getValue()], _("Configure the refresh rate of the screen.")))

		port = config.av.videoport.getValue()
		if port not in config.av.videomode:
			mode = None
		else:
			mode = config.av.videomode[port].getValue()

		# some modes (720p, 1080i) are always widescreen. Don't let the user select something here, "auto" is not what he wants.
		force_wide = self.hw.isWidescreenMode(port, mode)

		# if not force_wide:
			# self.list.append(getConfigListEntry(_("Aspect ratio"), config.av.aspect, _("Configure the aspect ratio of the screen.")))

		if force_wide or config.av.aspect.getValue() in ("16:9", "16:10"):
			self.list.extend((
				getConfigListEntry(_("Display 4:3 content as"), config.av.policy_43, _("When the content has an aspect ratio of 4:3, choose whether to scale/stretch the picture.")),
				getConfigListEntry(_("Display >16:9 content as"), config.av.policy_169, _("When the content has an aspect ratio of 16:9, choose whether to scale/stretch the picture."))
			))
		elif config.av.aspect.getValue() == "4:3":
			self.list.append(getConfigListEntry(_("Display 16:9 content as"), config.av.policy_169, _("When the content has an aspect ratio of 16:9, choose whether to scale/stretch the picture.")))

#		if config.av.videoport.getValue() == "HDMI":
#			self.list.append(getConfigListEntry(_("Allow unsupported modes"), config.av.edid_override))
		if config.av.videoport.getValue() == "Scart":
			self.list.append(getConfigListEntry(_("Color format"), config.av.colorformat, _("Configure which color format should be used on the SCART output.")))
			if level >= 1:
				self.list.append(getConfigListEntry(_("WSS on 4:3"), config.av.wss, _("When enabled, content with an aspect ratio of 4:3 will be stretched to fit the screen.")))
				if SystemInfo["ScartSwitch"]:
					self.list.append(getConfigListEntry(_("Auto scart switching"), config.av.vcrswitch, _("When enabled, your receiver will detect activity on the VCR SCART input.")))

		if level >= 1:
			if SystemInfo["CanDownmixAC3"]:
				self.list.append(getConfigListEntry(_("Digital downmix"), config.av.downmix_ac3, _("Choose whether multi channel sound tracks should be downmixed to stereo.")))
			self.list.extend((
				getConfigListEntry(_("General AC3 delay"), config.av.generalAC3delay, _("This option configures the general audio delay of Dolby Digital sound tracks.")),
				getConfigListEntry(_("General PCM delay"), config.av.generalPCMdelay, _("This option configures the general audio delay of stereo sound tracks."))
			))

			if SystemInfo["Can3DSurround"]:
				self.list.append(getConfigListEntry(_("3D Surround"), config.av.surround_3d,_("This option configures you can enable 3D Surround Sound.")))

			if SystemInfo["Canedidchecking"]:
				self.list.append(getConfigListEntry(_("Bypass HDMI EDID Check"), config.av.bypass_edid_checking,_("This option configures you can Bypass HDMI EDID check")))

#		if not isinstance(config.av.scaler_sharpness, ConfigNothing):
#			self.list.append(getConfigListEntry(_("Scaler sharpness"), config.av.scaler_sharpness, _("This option configures the picture sharpness.")))

		self["config"].list = self.list
		self["config"].l.setList(self.list)
		if config.usage.sort_settings.getValue():
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
		port = config.av.videoport.getValue()
		mode = config.av.videomode[port].getValue()
		rate = config.av.videorate[mode].getValue()
		self.last_good = (port, mode, rate)

	def apply(self):
		port = config.av.videoport.getValue()
		mode = config.av.videomode[port].getValue()
		rate = config.av.videorate[mode].getValue()
		if (port, mode, rate) != self.last_good:
			self.hw.setMode(port, mode, rate)
			from Screens.MessageBox import MessageBox
			self.session.openWithCallback(self.confirm, MessageBox, _("Is this video mode ok?"), MessageBox.TYPE_YESNO, timeout = 20, default = False)
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

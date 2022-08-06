# -*- coding: utf-8 -*-

from . import _
from enigma import getDesktop
from Screens.Screen import Screen
from Components.ScrollLabel import ScrollLabel
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Components.config import config, getConfigListEntry

VERSION = "1.34"


class VPS_Setup(Screen, ConfigListScreen):

	if getDesktop(0).size().width() <= 1280:
		skin = """<screen name="vpsConfiguration" title="VPS-Plugin" position="center,center" size="600,370">
			<ePixmap position="5,5" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
			<ePixmap position="155,5" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />
			<ePixmap position="305,5" size="140,40" pixmap="skin_default/buttons/yellow.png" transparent="1" alphatest="on" />
			<ePixmap position="455,5" size="140,40" pixmap="skin_default/buttons/blue.png" transparent="1" alphatest="on" />
			<widget source="key_red" render="Label" position="5,5" zPosition="1" size="140,40" valign="center" halign="center" font="Regular;20" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget source="key_green" render="Label" position="155,5" zPosition="1" size="140,40" valign="center" halign="center" font="Regular;20" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget source="key_blue" render="Label" position="455,5" zPosition="1" size="140,40" valign="center" halign="center" font="Regular;20" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget name="config" position="5,50" size="590,185" scrollbarMode="showOnDemand" />
			<ePixmap pixmap="skin_default/div-h.png" position="0,236" zPosition="1" size="600,2" />
			<widget source="help" render="Label" position="5,245" size="590,125" font="Regular;21" />
		</screen>"""
	else:
		skin = """<screen name="vpsConfiguration" title="VPS-Plugin" position="center,center" size="990,590">
			<ePixmap position="5,5" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
			<ePixmap position="285,5" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />
			<ePixmap position="565,5" size="140,40" pixmap="skin_default/buttons/yellow.png" transparent="1" alphatest="on" />
			<ePixmap position="845,5" size="140,40" pixmap="skin_default/buttons/blue.png" transparent="1" alphatest="on" />
			<widget source="key_red" render="Label" position="5,5" zPosition="1" size="140,40" valign="center" halign="center" font="Regular;22" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget source="key_green" render="Label" position="285,5" zPosition="1" size="140,40" valign="center" halign="center" font="Regular;22" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget source="key_blue" render="Label" position="845,5" zPosition="1" size="140,40" valign="center" halign="center" font="Regular;22" transparent="1" foregroundColor="white" shadowColor="black" shadowOffset="-1,-1" />
			<widget name="config" position="5,60" size="980,275" scrollbarMode="showOnDemand" font="Regular;32" itemHeight="34" />
			<ePixmap pixmap="skin_default/div-h.png" position="center,497" zPosition="1" size="600,2" />
			<widget source="help" render="Label" position="5,512" size="980,210" font="Regular;33" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)

		#Summary
		self.setup_title = _("VPS Setup Version %s") % VERSION

		self.vps_enabled = getConfigListEntry(_("Enable VPS-Plugin"), config.plugins.vps.enabled)
		self.vps_do_PDC_check = getConfigListEntry(_("Check for PDC"), config.plugins.vps.do_PDC_check)
		self.vps_initial_time = getConfigListEntry(_("Starting time"), config.plugins.vps.initial_time)
		self.vps_allow_wakeup = getConfigListEntry(_("Wakeup from Deep-Standby is allowed"), config.plugins.vps.allow_wakeup)
		self.vps_allow_seeking_multiple_pdc = getConfigListEntry(_("Seeking connected events"), config.plugins.vps.allow_seeking_multiple_pdc)
		self.vps_default = getConfigListEntry(_("VPS enabled by default"), config.plugins.vps.vps_default)
		self.vps_instanttimer = getConfigListEntry(_("Enable VPS on instant records"), config.plugins.vps.instanttimer)

		self.list = []
		self.list.append(self.vps_enabled)
		self.list.append(self.vps_do_PDC_check)
		self.list.append(self.vps_initial_time)
		self.list.append(self.vps_allow_wakeup)
		self.list.append(self.vps_allow_seeking_multiple_pdc)
		self.list.append(self.vps_default)
		self.list.append(self.vps_instanttimer)

		ConfigListScreen.__init__(self, self.list, session=session)
		self["config"].onSelectionChanged.append(self.updateHelp)

		# Initialize Buttons
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self["key_blue"] = StaticText(_("Information"))

		self["description"] = self["help"] = StaticText()

		# Define Actions
		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
			{
				"cancel": self.keyCancel,
				"save": self.keySave,
				"blue": self.show_info,
			}
		)

		self.onLayoutFinish.append(self.setCustomTitle)

	def setCustomTitle(self):
		self.setTitle(self.setup_title)

	def updateHelp(self):
		cur = self["config"].getCurrent()
		if cur == self.vps_enabled:
			self["help"].text = _("This plugin can determine whether a programme begins earlier or lasts longer. The channel has to provide reliable data.")
		elif cur == self.vps_do_PDC_check:
			self["help"].text = _("Check for PDC availability on each service")
		elif cur == self.vps_initial_time:
			self["help"].text = _("If possible, x minutes before a timer starts VPS-Plugin will control whether the programme begins earlier. (0 disables feature)")
		elif cur == self.vps_default:
			self["help"].text = _("Enable VPS by default (new timers)")
		elif cur == self.vps_allow_wakeup:
			self["help"].text = _("If enabled and necessary, the plugin will wake up the Receiver from Deep-Standby for the defined starting time to control whether the programme begins earlier.")
		elif cur == self.vps_allow_seeking_multiple_pdc:
			self["help"].text = _("If a programme is interrupted and divided into separate events, the plugin will search for the connected events.")
		elif cur == self.vps_instanttimer:
			self["help"].text = _("When yes, VPS will be enabled on instant records (stop after current event), if the channel supports VPS.")

	def show_info(self):
		VPS_show_info(self.session)

	def cancelConfirm(self, result):
		if not result:
			return

		for x in self["config"].list:
			x[1].cancel()

		self.close(self.session)

	def keyCancel(self):
		if self["config"].isChanged():
			from Screens.MessageBox import MessageBox

			self.session.openWithCallback(
				self.cancelConfirm,
				MessageBox,
				_("Really close without saving settings?")
			)
		else:
			self.close(self.session)

	def keySave(self):
		for x in self["config"].list:
			x[1].save()

		self.close(self.session)


class VPS_Screen_Info(Screen):
	if getDesktop(0).size().width() <= 1280:
		skin = """<screen name="vpsInfo" position="center,center" size="550,400" title="VPS-Plugin Information">
			<widget name="text" position="10,10" size="540,390" font="Regular;22" />
		</screen>"""
	else:
		skin = """<screen name="vpsInfo" position="center,center" size="1050,700" title="VPS-Plugin Information">
			<widget name="text" position="10,10" size="1040,690" font="Regular;32" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)

		#Summary
		self.info_title = _("VPS-Plugin Information")

		self["text"] = ScrollLabel(_("VPS-Plugin can react on delays arising in the startTime or endTime of a programme. VPS is only supported by certain channels!\n\nIf you enable VPS, the recording will only start, when the channel flags the programme as running.\n\nIf you select \"yes (safe mode)\", the recording is definitely starting at the latest at the startTime you defined. The recording may start earlier or last longer.\n\n\nSupported channels\n\nGermany:\n ARD and ZDF\n\nAustria:\n ORF\n\nSwitzerland:\n SF\n\nCzech Republic:\n CT\n\nIf a timer is programmed manually (not via EPG), it is necessary to set a VPS-Time to enable VPS. VPS-Time (also known as PDC) is the first published start time, e.g. given in magazines. If you set a VPS-Time, you have to leave timer name empty."))

		self["actions"] = ActionMap(["OkCancelActions", "DirectionActions"],
			{
				"cancel": self.close,
				"ok": self.close,
				"up": self["text"].pageUp,
				"down": self["text"].pageDown,
			}, -1)

		self.onLayoutFinish.append(self.setCustomTitle)

	def setCustomTitle(self):
		self.setTitle(self.info_title)


def VPS_show_info(session):
	session.open(VPS_Screen_Info)

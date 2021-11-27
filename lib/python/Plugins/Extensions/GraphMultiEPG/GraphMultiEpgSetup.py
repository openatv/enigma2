#!/usr/bin/python
# -*- coding: utf-8 -*-
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Pixmap import Pixmap
from Components.Label import Label
from Components.PluginComponent import plugins
from Components.config import config, getConfigListEntry
from Components.ConfigList import ConfigListScreen

addnotifier = None


class GraphMultiEpgSetup(Screen, ConfigListScreen):
	skin = """
		<screen name="GraphMultiEPGSetup" position="center,center" size="560,490" title="Electronic Program Guide Setup">
			<ePixmap pixmap="buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<widget name="key_red" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget name="key_green" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="config" position="10,50" size="550,430" />
		</screen>"""

	def __init__(self, session, args=None):
		Screen.__init__(self, session)
		self.setTitle(_("GraphMultiEpg Settings"))
		self.skinName = ["GraphMultiEpgSetup", "Setup"]

		self["key_red"] = Label(_("Cancel"))
		self["key_green"] = Label(_("Save"))

		self["actions"] = ActionMap(["SetupActions", "MenuActions", "ColorActions"],
		{
			"ok": self.keySave,
			"save": self.keySave,
			"green": self.keySave,
			"cancel": self.keyCancel,
			"red": self.keyCancel,
			"menu": self.closeRecursive,
		}, -1)

		global addnotifier
		self.list = []
		self.list.append(getConfigListEntry(_("Event font size (relative to skin size)"), config.misc.graph_mepg.ev_fontsize))
		self.list.append(getConfigListEntry(_("Time scale"), config.misc.graph_mepg.prev_time_period))
		self.list.append(getConfigListEntry(_("Prime time"), config.misc.graph_mepg.prime_time))
		self.list.append(getConfigListEntry(_("Items per page "), config.misc.graph_mepg.items_per_page))
		self.list.append(getConfigListEntry(_("Items per page for list screen"), config.misc.graph_mepg.items_per_page_listscreen))
		self.list.append(getConfigListEntry(_("Start with list screen"), config.misc.graph_mepg.default_mode))
		self.list.append(getConfigListEntry(_("Skip empty services"), config.misc.graph_mepg.overjump))
		self.list.append(getConfigListEntry(_("Service title mode"), config.misc.graph_mepg.servicetitle_mode))
		self.list.append(getConfigListEntry(_("Round start time on"), config.misc.graph_mepg.roundTo))
		self.list.append(getConfigListEntry(_("Function of OK button"), config.misc.graph_mepg.OKButton))
		self.list.append(getConfigListEntry(_("Alignment of service names"), config.misc.graph_mepg.servicename_alignment))
		self.list.append(getConfigListEntry(_("Alignment of events"), config.misc.graph_mepg.event_alignment))
		self.list.append(getConfigListEntry(_("Show vertical timelines"), config.misc.graph_mepg.show_timelines))
		self.list.append(getConfigListEntry(_("Center time-labels and remove date"), config.misc.graph_mepg.center_timeline))
		self.list.append(getConfigListEntry(_("Show in extensions menu"), config.misc.graph_mepg.extension_menu))
		self.list.append(getConfigListEntry(_("Show record clock icons"), config.misc.graph_mepg.show_record_clocks))
		self.list.append(getConfigListEntry(_("Zap bouquets blindly on zap buttons"), config.misc.graph_mepg.zap_blind_bouquets))
		if addnotifier is None:
			addnotifier = config.misc.graph_mepg.extension_menu.addNotifier(plugins.reloadPlugins, initial_call=False)

		ConfigListScreen.__init__(self, self.list, session)

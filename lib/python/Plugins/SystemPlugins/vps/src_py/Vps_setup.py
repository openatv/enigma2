from enigma import getDesktop
from Screens.Screen import Screen
from Screens.Setup import Setup
from Components.ScrollLabel import ScrollLabel
from Components.ActionMap import ActionMap


class VPS_Setup(Setup):
	def __init__(self, session):
		Setup.__init__(self, session, "vps", plugin="SystemPlugins/vps")


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

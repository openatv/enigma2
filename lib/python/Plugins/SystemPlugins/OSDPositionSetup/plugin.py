from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.config import config, ConfigSubsection, ConfigInteger, ConfigSlider, getConfigListEntry

config.plugins.OSDPositionSetup = ConfigSubsection()
config.plugins.OSDPositionSetup.dst_left = ConfigInteger(default = 0)
config.plugins.OSDPositionSetup.dst_width = ConfigInteger(default = 720)
config.plugins.OSDPositionSetup.dst_top = ConfigInteger(default = 0)
config.plugins.OSDPositionSetup.dst_height = ConfigInteger(default = 576)

class OSDScreenPosition(Screen, ConfigListScreen):
	skin = """
	<screen position="0,0" size="e,e" title="OSD position setup" backgroundColor="blue">
		<widget name="config" position="c-175,c-75" size="350,150" foregroundColor="black" backgroundColor="blue" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="c-145,e-100" zPosition="0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/red.png" position="c+5,e-100" zPosition="0" size="140,40" alphatest="on" />
		<widget name="ok" position="c-145,e-100" size="140,40" valign="center" halign="center" zPosition="1" font="Regular;20" transparent="1" backgroundColor="green" />
		<widget name="cancel" position="c+5,e-100" size="140,40" valign="center" halign="center" zPosition="1" font="Regular;20" transparent="1" backgroundColor="red" />
	</screen>"""

	def __init__(self, session):
		self.skin = OSDScreenPosition.skin
		Screen.__init__(self, session)

		from Components.ActionMap import ActionMap
		from Components.Button import Button

		self["ok"] = Button(_("OK"))
		self["cancel"] = Button(_("Cancel"))

		self["actions"] = ActionMap(["SetupActions", "ColorActions", "MenuActions"],
		{
			"ok": self.keyGo,
			"save": self.keyGo,
			"cancel": self.keyCancel,
			"green": self.keyGo,
			"red": self.keyCancel,
			"menu": self.closeRecursive,
		}, -2)

		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session)

		left = config.plugins.OSDPositionSetup.dst_left.value
		width = config.plugins.OSDPositionSetup.dst_width.value
		top = config.plugins.OSDPositionSetup.dst_top.value
		height = config.plugins.OSDPositionSetup.dst_height.value

		self.dst_left = ConfigSlider(default = left, increment = 1, limits = (0, 720))
		self.dst_width = ConfigSlider(default = width, increment = 1, limits = (0, 720))
		self.dst_top = ConfigSlider(default = top, increment = 1, limits = (0, 576))
		self.dst_height = ConfigSlider(default = height, increment = 1, limits = (0, 576))
		self.list.append(getConfigListEntry(_("left"), self.dst_left))
		self.list.append(getConfigListEntry(_("width"), self.dst_width))
		self.list.append(getConfigListEntry(_("top"), self.dst_top))
		self.list.append(getConfigListEntry(_("height"), self.dst_height))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.setPreviewPosition()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.setPreviewPosition()

	def setPreviewPosition(self):
		setPosition(int(self.dst_left.value), int(self.dst_width.value), int(self.dst_top.value), int(self.dst_height.value))

	def keyGo(self):
		config.plugins.OSDPositionSetup.dst_left.value = self.dst_left.value
		config.plugins.OSDPositionSetup.dst_width.value = self.dst_width.value
		config.plugins.OSDPositionSetup.dst_top.value = self.dst_top.value
		config.plugins.OSDPositionSetup.dst_height.value = self.dst_height.value
		config.plugins.OSDPositionSetup.save()
		self.close()

	def keyCancel(self):
		setConfiguredPosition()
		self.close()

def setPosition(dst_left, dst_width, dst_top, dst_height):
	if dst_left + dst_width > 720:
		dst_width = 720 - dst_left
	if dst_top + dst_height > 576:
		dst_height = 576 - dst_top
	try:
		file = open("/proc/stb/fb/dst_left", "w")
		file.write('%X' % dst_left)
		file.close()
		file = open("/proc/stb/fb/dst_width", "w")
		file.write('%X' % dst_width)
		file.close()
		file = open("/proc/stb/fb/dst_top", "w")
		file.write('%X' % dst_top)
		file.close()
		file = open("/proc/stb/fb/dst_height", "w")
		file.write('%X' % dst_height)
		file.close()
	except:
		return

def setConfiguredPosition():
	setPosition(int(config.plugins.OSDPositionSetup.dst_left.value), int(config.plugins.OSDPositionSetup.dst_width.value), int(config.plugins.OSDPositionSetup.dst_top.value), int(config.plugins.OSDPositionSetup.dst_height.value))

def main(session, **kwargs):
	session.open(OSDScreenPosition)

def startup(reason, **kwargs):
	setConfiguredPosition()

def Plugins(**kwargs):
	from os import path
	if path.exists("/proc/stb/fb/dst_left"):
		from Plugins.Plugin import PluginDescriptor
		return [PluginDescriptor(name = "OSD position setup", description = "Compensate for overscan", where = PluginDescriptor.WHERE_PLUGINMENU, fnc = main),
					PluginDescriptor(name = "OSD position setup", description = "", where = PluginDescriptor.WHERE_SESSIONSTART, fnc = startup)]
	return []
